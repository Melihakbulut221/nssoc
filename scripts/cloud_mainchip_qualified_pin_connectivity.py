#!/usr/bin/env python3
"""Cloud-only full828 validation of an explicit independently GDS-qualified pin-conductor model."""
import copy,hashlib,io,json,os,re,subprocess,sys,traceback,zipfile
from pathlib import Path
import cloud_mainchip_connectivity_diagnosis as original
import cloud_mainchip_pin_gds as gds
import mainchip_targeted_counterpart_routing as scope_core
import mainchip_qualified_pin_connectivity as core
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"qualified-pin-evidence"
RUN=original.RUN;SOURCE=original.SOURCE;RELEASE=original.RELEASE
FLAGS=core.FLAGS
PROOF="docs/evidence/restored-pin-gds-terminal-41314829887/derived/"
api=original.api;blob=original.blob;digest=original.digest;enc=original.enc
def save(name,value):
 p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(enc(value))
def source_gate():
 assert os.environ.get("GITHUB_ACTIONS")=="true"and os.environ["GITHUB_RUN_ATTEMPT"]=="1"
 assert os.environ["GITHUB_REPOSITORY"]=="Melihakbulut221/nssoc"and os.environ["GITHUB_EVENT_NAME"]=="workflow_dispatch"
 assert os.environ["GITHUB_REF"]=="refs/heads/codex/mainchip-qualified-pin-connectivity"
 assert subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()==os.environ["GITHUB_SHA"]
 pins=json.loads((ROOT/"scripts/mainchip-qualified-pin-pins.json").read_bytes())
 for name,pin in pins.items():assert digest((ROOT/name).read_bytes())==pin,("source",name)
 assert gds.importlib.metadata.version("klayout")=="0.30.2"and gds.importlib.metadata.version("zstandard")=="0.23.0"
 return pins
def fixture():
 observe,gate=original.functions()
 shapes=[dict(kind="wire",layer="Metal1",box=[0,0,2,2]),dict(kind="wire",layer="Metal1",box=[8,0,10,2])]
 p=dict(kind="iterm",scoped_identity=["iterm","diode","A"],geometries=[["Metal1",[0,0,10,2]]])
 obs={"n":{m:observe(shapes,[p],m)for m in ["positive_area","closed_boundary"]}}
 plan=dict(mutable_nets=["n"],attachments=dict(diode="n"))
 rows=[dict(pin=p["scoped_identity"],net="n",master=["lib","cell"],passed=True,exact_master_to_observed_pin_transform=True,master_pin_gds_lef_passed=True,
 observed_rectangles=[dict(pin=p["scoped_identity"],geometry_index=0,layer="Metal1",box=[0,0,10,2])])]
 report=dict(status=core.GDS_STATUS,all_observed_pin_rectangles_verified=True,missing_or_mismatched_pins=0,
 original_failed_nets=1,observed_pin_count=1,unique_master_pins=1,original_connectivity_gate_modified=False,**FLAGS)
 return obs,plan,rows,report,observe,gate
def controls():
 gds.OUT=OUT;gds.controls();inherited=json.loads((OUT/"gds-controls.json").read_bytes());assert inherited["count"]==52
 obs,plan,rows,report,observe,gate=fixture()
 before=enc([obs,plan,rows,report])
 result,details=core.audit(obs,plan,rows,report,observe,gate,(1,1,1,1))
 assert result["both_modes_complete"]and result["original_wire_only_failed_nets"]==1 and result["original_graphs_replayed"]==2
 assert all(len(d["added_pin_rectangles"])==1 for d in details[0]["modes"].values())
 passed=["both original graphs replayed and actual rectangle joins conductor islands"]
 assert before==enc([obs,plan,rows,report]);passed.append("every source observation and qualification record unchanged")
 def reject(label,mutate):
  a,b,c,d=copy.deepcopy([obs,plan,rows,report]);mutate(a,b,c,d)
  try:core.audit(a,b,c,d,observe,gate,(1,1,1,1))
  except (AssertionError,KeyError,ValueError):passed.append("reject "+label)
  else:raise AssertionError("accepted "+label)
 reject("forged original connectivity flag",lambda a,b,c,d:a["n"]["positive_area"].__setitem__("all_wire_material_one_component",True))
 reject("missing mode",lambda a,b,c,d:a["n"].pop("closed_boundary"))
 reject("changed qualified rectangle",lambda a,b,c,d:c[0]["observed_rectangles"][0]["box"].__setitem__(2,9))
 reject("changed qualified layer",lambda a,b,c,d:c[0]["observed_rectangles"][0].__setitem__("layer","Metal2"))
 reject("missing GDS-qualified pin",lambda a,b,c,d:c.clear())
 reject("duplicate GDS-qualified pin",lambda a,b,c,d:c.append(copy.deepcopy(c[0])))
 reject("changed qualified owner",lambda a,b,c,d:c[0].__setitem__("net","other"))
 reject("failed GDS correspondence",lambda a,b,c,d:c[0].__setitem__("master_pin_gds_lef_passed",False))
 reject("failed native transform",lambda a,b,c,d:c[0].__setitem__("exact_master_to_observed_pin_transform",False))
 reject("false complete GDS result",lambda a,b,c,d:d.__setitem__("all_observed_pin_rectangles_verified",False))
 reject("changed qualification census",lambda a,b,c,d:d.__setitem__("observed_pin_count",2))
 reject("missing diode connection",lambda a,b,c,d:b["attachments"].__setitem__("missing","n"))
 def disconnected(a,b,c,d):
  for m in list(a["n"]):
   r=a["n"][m];a["n"][m]=observe(r["source_shapes"]+[dict(kind="wire",layer="Metal1",box=[20,20,22,22])],r["source_pins"],m)
 reject("additional disconnected material survives pin supplementation",disconnected)
 assert len(passed)==15,len(passed)
 save("qualified-controls.json",dict(status="PASS_QUALIFIED_PIN_CONNECTIVITY_SOURCE_CONTROLS_ONLY",count=67,inherited=52,added=15,checks=passed,
 synthetic_fixture=True,native_execution=False,**FLAGS))
def acquire():
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

 observations={}
 for path in paths:
  d=json.loads(z.read(path));name=d["net"]
  assert name not in observations and name in routing and path.endswith(hashlib.sha256(name.encode()).hexdigest()+".json")
  observations[name]=d["modes"]
 assert set(observations)==routing
 assert index["files"]["work/bulk-postdrt-antenna/candidate.odb"]==core.CANDIDATE
 save("authentication.json",dict(run=run,artifact=a,release=release,complete_derived_members=authenticated,native_archive_downloaded=False,candidate=core.CANDIDATE))
 return observations,scope_core.observation_scope(plan,scope)

def analyze():
 run=api("actions/runs/41314829887")
 assert run["head_sha"]=="b0cc820906e9cc75c3a7d55fce11297a8e4f1da1"and run["status"]=="completed"and run["conclusion"]=="success"and run["run_attempt"]==1
 rows=json.loads((ROOT/(PROOF+"placed-pin-correspondence.json")).read_bytes())
 result=json.loads((ROOT/(PROOF+"result.json")).read_bytes())
 assert result["context"]==dict(run=41314829887,source=run["head_sha"])
 observations,plan=acquire()
 assert len(plan["mutable_nets"])==828 and len(plan["attachments"])==1351
 observe,gate=original.functions()
 outcome,per_net=core.audit(observations,plan,rows,result,observe,gate)
 save("per-net-conductor-results.json",per_net)
 save("gds-qualification-binding.json",dict(run=run,result=result,candidate=core.CANDIDATE,
 records=digest((ROOT/(PROOF+"placed-pin-correspondence.json")).read_bytes())))
 save("result.json",dict(status="PASS_COMPLETE_828_QUALIFIED_PHYSICAL_CONNECTIVITY_MODEL_NOT_NATIVE_ADAPTER",
 context=dict(run=int(os.environ["GITHUB_RUN_ID"]),source=os.environ["GITHUB_SHA"]),
 candidate=core.CANDIDATE,connectivity=outcome,native_adapter_executed=False,
 original_graphs_preserved_in_release=430583367,new_full_graph_bodies_not_duplicated=True,
 new_graphs_reconstructible_from_original_full_graphs_qualified_pin_records_and_pinned_source=True,
 original_pin_rectangles_GDS_verified=True,**FLAGS))
def main():
 before=source_gate();OUT.mkdir(exist_ok=False)
 assert sys.argv[1:]in [["controls"],["analyze"]]
 controls()if sys.argv[1]=="controls"else analyze()
 assert source_gate()==before
if __name__=="__main__":
 try:main()
 except BaseException:
  OUT.mkdir(exist_ok=True);save("failure.json",dict(traceback=traceback.format_exc(),**FLAGS));raise
