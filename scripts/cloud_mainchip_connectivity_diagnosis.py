#!/usr/bin/env python3
"""Cloud-only readout of actual failed restored-route connectivity; no layout edit."""
import ast,base64,copy,hashlib,io,json,os,re,subprocess,sys,zipfile
from pathlib import Path
import mainchip_targeted_counterpart_routing as scope_core
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"connectivity-diagnosis"
RUN=41308526628
SOURCE="05d336a1b1b681c9d96b71d464c5ea430835e438"
RELEASE=430583367
REPO="repos/Melihakbulut221/nssoc/"
FLAGS=dict(physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
def digest(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def enc(v):return (json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
def save(name,v):
 p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(enc(v))
def api(path):
 return json.loads(subprocess.check_output(["gh","api",REPO+path]))
def blob(path):
 return subprocess.check_output(["gh","api",REPO+path,"-H","Accept: application/octet-stream"])
def source_gate():
 assert os.environ.get("GITHUB_ACTIONS")=="true"
 assert os.environ["GITHUB_REPOSITORY"]=="Melihakbulut221/nssoc"
 assert os.environ["GITHUB_EVENT_NAME"]=="workflow_dispatch"and os.environ["GITHUB_RUN_ATTEMPT"]=="1"
 assert os.environ["GITHUB_REF"]=="refs/heads/codex/mainchip-connectivity-diagnosis"
 assert subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()==os.environ["GITHUB_SHA"]
 pins=json.loads((ROOT/"scripts/mainchip-connectivity-diagnosis-pins.json").read_bytes())
 for name,pin in pins.items():assert digest((ROOT/name).read_bytes())==pin,name
 return pins
def original_functions(path,names,constants):
 tree=ast.parse((ROOT/path).read_bytes())
 selected=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in names or isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id in constants for t in n.targets)]
 assert {n.name for n in selected if isinstance(n,ast.FunctionDef)}==set(names)
 namespace=dict(json=json)
 exec(compile(ast.Module(body=selected,type_ignores=[]),path,"exec"),namespace)
 return namespace
def functions():
 graph=original_functions("scripts/mainchip_net459_connectivity.py",["require","box","overlap","observe"],["METALS","FLAGS"])
 gate=original_functions("scripts/mainchip_bulk_postdrt_antenna.py",["require","exact","validate_connectivity"],["FLAGS"])
 gate["encode"]=original_functions("scripts/mainchip_single_antenna_trial.py",["encode"],[])["encode"]
 return graph["observe"],gate["validate_connectivity"]
def controls():
 observe,gate=functions()
 shapes=[dict(kind="wire",layer="Metal1",box=[0,0,5,2]),dict(kind="wire",layer="Metal1",box=[4,0,10,2])]
 pins=[dict(kind="iterm",scoped_identity=["iterm",n,"A"],geometries=[["Metal1",b]])for n,b in [("drv",[0,0,1,1]),("diode",[9,0,10,1])]]
 modes={m:observe(shapes,pins,m)for m in ["positive_area","closed_boundary"]}
 plan=dict(mutable_nets=["n"],attachments=dict(diode="n"))
 gate(dict(n=modes),plan);passed=["original overlapping graph and original diode gate"]
 for m in modes:
  for key in ["all_pins_share_one_wire_component","all_wire_material_one_component"]:
   bad=copy.deepcopy(modes);bad[m][key]=False
   try:gate(dict(n=bad),plan)
   except AssertionError:passed.append("reject "+m+"/"+key)
   else:raise AssertionError("accepted failed graph")
 for label,bad in [
  ("missing mode",dict(positive_area=modes["positive_area"])),
  ("duplicate pin",copy.deepcopy(modes)),
  ("missing diode",copy.deepcopy(modes))]:
  if label=="duplicate pin":bad["positive_area"]["pins"].append(copy.deepcopy(bad["positive_area"]["pins"][0]))
  if label=="missing diode":bad["positive_area"]["pins"]=bad["positive_area"]["pins"][:1]
  try:gate(dict(n=bad),plan)
  except AssertionError:passed.append("reject "+label)
  else:raise AssertionError("accepted "+label)
 touching=copy.deepcopy(shapes);touching[1]["box"][0]=5
 assert not observe(touching,pins,"positive_area")["all_pins_share_one_wire_component"]
 assert observe(touching,pins,"closed_boundary")["all_pins_share_one_wire_component"]
 passed.append("edge contact remains distinct from positive area")
 try:gate({},plan)
 except AssertionError:passed.append("reject missing net")
 else:raise AssertionError("accepted missing net")
 assert len(passed)==10
 save("controls.json",dict(source=os.environ["GITHUB_SHA"],run=int(os.environ["GITHUB_RUN_ID"]),count=10,passed=passed,**FLAGS))
def analyze():
 inputs=json.loads((ROOT/"scripts/mainchip-connectivity-diagnosis-inputs.json").read_bytes())
 run=api("actions/runs/"+str(RUN));assert run["head_sha"]==SOURCE and run["status"]=="completed"and run["conclusion"]=="failure"and run["run_attempt"]==1
 release=api("releases/"+str(RELEASE));assert release["target_commitish"]==SOURCE
 assert api("git/ref/tags/"+release["tag_name"])["object"]["sha"]==SOURCE
 assets={a["name"]:a for a in release["assets"]}
 assert set(assets)==set(inputs["assets"])
 for name,p in inputs["assets"].items():
  a=assets[name];assert a["id"]==p["id"]and a["size"]==p["bytes"]and a["digest"]=="sha256:"+p["sha256"]
 index_raw=blob("releases/assets/"+str(assets["candidate-outputs.json"]["id"]))
 assert digest(index_raw)=={k:inputs["assets"]["candidate-outputs.json"][k]for k in ["bytes","sha256"]}
 index=json.loads(index_raw);assert index["source"]==SOURCE and int(index["run"])==RUN
 a=next(a for a in api("actions/runs/"+str(RUN)+"/artifacts?per_page=100")["artifacts"]if a["name"]=="scoped-restoration-derived-"+str(RUN))
 assert not a["expired"]and a["id"]==inputs["artifact"]["id"]and a["digest"]=="sha256:"+inputs["artifact"]["sha256"]and a["size_in_bytes"]==inputs["artifact"]["bytes"]
 raw=blob("actions/artifacts/"+str(a["id"])+"/zip");assert digest(raw)=={k:inputs["artifact"][k]for k in ["bytes","sha256"]}
 z=zipfile.ZipFile(io.BytesIO(raw));assert len(z.namelist())==len(set(z.namelist()))==1726
 authenticated={}
 for i in z.infolist():
  n=i.filename;assert not i.is_dir()and not n.startswith("/")and ".."not in n.split("/")and ((i.external_attr>>16)&0o170000)!=0o120000
  h=hashlib.sha256();size=0
  with z.open(i)as f:
   for b in iter(lambda:f.read(65536),b""):h.update(b);size+=len(b)
  pin=dict(bytes=size,sha256=h.hexdigest());assert size==i.file_size
  if n.startswith("native/bulk-postdrt-antenna/"):assert index["files"][n.removeprefix("native/")]==pin,n
  authenticated[n]=pin
 def read(name):return json.loads(z.read("native/bulk-postdrt-antenna/"+name))
 plan=read("insertion-plan.json");scope=read("targeted-routing-scope.json")
 antenna,extra,protected,routing=scope_core.validate_scope(scope,plan)
 paths=[n for n in z.namelist()if re.fullmatch(r"native/bulk-postdrt-antenna/connectivity-[0-9a-f]{64}\.json",n)]
 assert len(paths)==len(routing)==828
 observe,gate=functions();observed=set();rows=[];failures=[]
 for path in sorted(paths):
  d=json.loads(z.read(path));name=d["net"]
  assert name not in observed and name in routing;observed.add(name)
  assert path.endswith(hashlib.sha256(name.encode()).hexdigest()+".json")
  modes=d["modes"];assert set(modes)=={"positive_area","closed_boundary"}
  local_plan=dict(mutable_nets=[name],attachments={i:n for i,n in plan["attachments"].items()if n==name})
  rejection=None
  try:gate({name:modes},local_plan)
  except AssertionError as e:rejection=str(e)
  result=dict(net=name,ownership="antenna"if name in antenna else"counterpart",gate_passed=rejection is None,rejection=rejection,modes={})
  for mode,m in modes.items():
   assert m["mode"]==mode
   result["modes"][mode]=dict(pins_share=m["all_pins_share_one_wire_component"],wire_connected=m["all_wire_material_one_component"],
    component_count=len(m["wire_components"]),pin_count=len(m["pins"]),
    no_wire_access=[p["scoped_identity"]for p in m["pins"]if p["no_wire_access"]],
    ambiguous_pins=[p["scoped_identity"]for p in m["pins"]if p["ambiguous_multiple_wire_components"]],
    pin_component_memberships=[dict(pin=p["scoped_identity"],components=p["wire_components"])for p in m["pins"]])
  rows.append(result)
  if rejection:
   for mode,m in modes.items():
    actual=observe(m["source_shapes"],m["source_pins"],mode)
    assert actual==m,("full failed graph replay",name,mode)
   failure=dict(summary=result,original_report=d,full_original_graph_replayed=True,**FLAGS)
   save("failed/"+hashlib.sha256(name.encode()).hexdigest()+".json",failure);failures.append(result)
 assert observed==routing
 save("all-net-summary.json",rows);save("failed-net-summary.json",failures)
 save("authentication.json",dict(run=run,artifact=a,release=release,complete_derived_members=authenticated,native_archive_downloaded=False))
 save("result.json",dict(status="COMPLETE_ACTUAL_CONNECTIVITY_DIAGNOSIS_NOT_REPAIR",source=os.environ["GITHUB_SHA"],run=int(os.environ["GITHUB_RUN_ID"]),
  producer_run=RUN,producer_source=SOURCE,producer_release=RELEASE,observed_nets=len(rows),failed_nets=len(failures),
  failed_antenna_nets=sum(r["ownership"]=="antenna"for r in failures),failed_counterpart_nets=sum(r["ownership"]=="counterpart"for r in failures),
  all_failed_original_graphs_replayed=True,clock_gate=read("original-clock-gate.json"),no_layout_or_gate_changes=True,**FLAGS))
def main():
 before=source_gate();OUT.mkdir(exist_ok=False)
 assert sys.argv[1:]in [["controls"],["analyze"]]
 controls()if sys.argv[1]=="controls"else analyze()
 assert source_gate()==before
if __name__=="__main__":
 try:main()
 except BaseException:
  import traceback
  OUT.mkdir(exist_ok=True);save("failure.json",dict(traceback=traceback.format_exc(),**FLAGS));raise
