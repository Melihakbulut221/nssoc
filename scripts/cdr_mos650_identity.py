#!/usr/bin/env python3
"""Read complete real650 LVS identities for subsequent geometry/RC binding."""
import copy,hashlib,json,os,shutil,subprocess,sys,tarfile,traceback
from collections import Counter
from pathlib import Path,PurePosixPath
import cdr_mos650_geometry as original
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"mos650-identity";NATIVE=OUT/"native";DERIVED=OUT/"derived"
CFG="scripts/cdr-mos650-identity-inputs.json";PINS="scripts/cdr-mos650-identity-pins.json"
BRANCH="codex/cdr-mos650-identity";REPO="Melihakbulut221/nssoc";TOP=original.TOP
FLAGS=dict(fresh_rc_executed=False,full_canonical_wire_view=False,electrical_accepted=False,full_phy_accepted=False,final_timing_complete=False)
def need(ok,msg):
 if not ok:raise ValueError(msg)
def read(p):return json.loads(Path(p).read_bytes())
def enc(d):return(json.dumps(d,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
def pin(p):
 p=Path(p)
 with p.open("rb")as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,"sha256").hexdigest())
def save(n,d):
 p=DERIVED/n;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open("xb")as f:f.write(enc(d))
def api(path):return json.loads(subprocess.check_output(["gh","api","repos/"+REPO+"/"+path],timeout=180))
def gate():
 e=os.environ
 need(e.get("GITHUB_ACTIONS")=="true"and e.get("RUNNER_ENVIRONMENT")=="github-hosted","hosted only")
 need(e["GITHUB_REPOSITORY"]==REPO and e["GITHUB_REF"]=="refs/heads/"+BRANCH,"owned branch")
 need(e["GITHUB_EVENT_NAME"]=="workflow_dispatch"and e["GITHUB_RUN_ATTEMPT"]=="1","first explicit dispatch")
 need(e["GITHUB_SHA"]==e["APPROVED_SOURCE"]==subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),"exact source")
 for n,p in read(ROOT/PINS)["files"].items():need(pin(ROOT/n)==p,"source "+n)
 return dict(run=int(e["GITHUB_RUN_ID"]),source=e["GITHUB_SHA"],attempt=1)
def expected():
 m=read(ROOT/original.MAP);plan=read(ROOT/original.PLAN)["plan"];original.validate_plan(plan,m)
 byid={p["native_id"]:p for p in plan};result={}
 for p in m["pairs"]:
  ref=p["schematic"];model=ref["model"].lower();name=ref["expanded_name"]
  terminals={k.upper():v["expanded_name"].upper()for k,v in ref["terminals"].items()}
  specs=byid[p["layout"]["id"]]["units"]if model=="sg13_lv_nmos"else[None]
  for i,u in enumerate(specs):
   key=name+("_U"+str(i)if u is not None else"")
   q=dict(p["layout"]["parameters"]);rq=dict(ref["parameters"])
   if u is not None:
    w=float(original.um(u["parameters"]["w"]));l=float(original.um(u["parameters"]["l"]))
    q.update(W=w,L=l,AD=w*.34,AS=w*.34,PD=2*(w+.34),PS=2*(w+.34))
    rq.update(W=w,L=l)
   need(key not in result,"unique independent reference")
   result[key]=dict(model=model,origin_native_id=p["layout"]["id"],loaded_instance=u["instance"]if u is not None else p["loaded_instance"],
     layout_parameters=q,schematic_parameters=rq,terminals=terminals,unit_index=i if u is not None else None)
 need(len(result)==650 and Counter(r["model"]for r in result.values())==dict(sg13_lv_nmos=200,npn13g2=124,rppd=98,cap_cmim=7,ptap1=221),"entire independent650 reference")
 return result
def close(a,b):
 return isinstance(a,(int,float))and abs(a-b)<=max(1e-9,abs(b)*1e-9)
def params(actual,wanted,label):
 need(set(actual)==set(wanted),label+" complete parameter names")
 for k,v in wanted.items():need(close(actual[k],v),label+" parameter "+k)
def mapping_for(row,wanted,netmap):
 lt=row["layout"]["terminals"];rt=row["schematic"]["terminals"]
 need(set(lt)==set(rt)==set(wanted["terminals"]),"complete model terminals")
 need({k:t["name"].upper()for k,t in rt.items()}==wanted["terminals"],"independent original schematic owners")
 actual={k:netmap[t["cluster"]]for k,t in lt.items()}
 permutations=[{k:k for k in lt}]
 if wanted["model"]=="sg13_lv_nmos":
  permutations.append({k:{"D":"S","S":"D"}.get(k,k)for k in lt})
 elif wanted["model"]=="rppd":
  permutations.append({k:{"RPPD_1":"RPPD_2","RPPD_2":"RPPD_1"}.get(k,k)for k in lt})
 valid=[p for p in permutations if all(actual[p[k]]==wanted["terminals"][k]for k in p)]
 need(valid,"actual native terminals match independent semantic owners")
 return valid[0]
def validate(report,wanted):
 rows=report["pairs"];need(len(rows)==650,"all650 actual pairs")
 need(len({r["layout"]["id"]for r in rows})==650 and len({r["schematic"]["id"]for r in rows})==650,"unique native/reference devices")
 need({r["schematic"]["expanded_name"]for r in rows}==set(wanted),"all independent650 schematic instances")
 nets=report["nets"];need(len(nets)==len({r["layout"]["cluster"]for r in nets})==len({r["schematic"]["name"].upper()for r in nets}),"one-to-one complete net mapping")
 netmap={r["layout"]["cluster"]:r["schematic"]["name"].upper()for r in nets}
 need(set(netmap.values())=={v for x in wanted.values()for v in x["terminals"].values()},"all and only schematic connected nets")
 for n in nets:need(n["status"]=="Match","each actual net matched")
 terminal_count=0
 for r in rows:
  name=r["schematic"]["expanded_name"];w=wanted[name]
  need(r["status"]=="Match"and r["layout"]["model"]==r["schematic"]["model"]==w["model"],"actual model match")
  params(r["layout"]["parameters"],w["layout_parameters"],"layout "+name)
  params(r["schematic"]["parameters"],w["schematic_parameters"],"reference "+name)
  mapping_for(r,w,netmap)
  for t in r["layout"]["terminals"].values():
   need(t["cluster"]in netmap and t["native_layers"],"each terminal has actual ownership and geometry")
   need(all(x["polygons"]and x["area_dbu2"]>0 for x in t["native_layers"]),"nonempty actual terminal shapes")
  terminal_count+=len(r["layout"]["terminals"])
 ports=report["ports"];names=read(ROOT/CFG)["semantic_ports"]
 need(len(ports)==25 and {p["name"].upper()for p in ports}==set(names)and len({p["native_pin_id"]for p in ports})==25,"all25 actual port identities")
 for p in ports:need(netmap[p["cluster"]]==p["name"].upper(),"actual port semantic net")
 need(terminal_count==report["terminal_count"]==2046,"all2046 actual terminals")
 return netmap
def controls_on_actual(report,wanted):
 refused=[]
 def check(label,fn):
  bad=copy.deepcopy(report);fn(bad)
  try:validate(bad,wanted)
  except (ValueError,KeyError):refused.append(label)
  else:raise ValueError("accepted corrupt actual identity "+label)
 check("missing device",lambda r:r["pairs"].pop())
 check("duplicate device",lambda r:r["pairs"].__setitem__(-1,copy.deepcopy(r["pairs"][0])))
 check("wrong model",lambda r:r["pairs"][0]["layout"].__setitem__("model","wrong"))
 def mos(r):return next(x for x in r["pairs"]if x["layout"]["model"]=="sg13_lv_nmos")
 check("wrong actual unit width",lambda r:mos(r)["layout"]["parameters"].__setitem__("W",54))
 check("wrong actual unit length",lambda r:mos(r)["layout"]["parameters"].__setitem__("L",.5))
 check("wrong diffusion area",lambda r:mos(r)["layout"]["parameters"].__setitem__("AD",999))
 check("missing terminal",lambda r:mos(r)["layout"]["terminals"].pop("G"))
 check("wrong terminal owner",lambda r:mos(r)["layout"]["terminals"]["G"].__setitem__("cluster",-1))
 check("missing terminal geometry",lambda r:mos(r)["layout"]["terminals"]["G"].__setitem__("native_layers",[]))
 check("wrong semantic instance",lambda r:r["pairs"][0]["schematic"].__setitem__("expanded_name","wrong"))
 check("missing net",lambda r:r["nets"].pop())
 check("unmatched net",lambda r:r["nets"][0].__setitem__("status","NoMatch"))
 check("missing public port",lambda r:r["ports"].pop())
 check("wrong port owner",lambda r:r["ports"][0].__setitem__("cluster",-1))
 check("stale1446 terminal count",lambda r:r.__setitem__("terminal_count",1446))
 need(len(refused)==15,"all actual-identity refusal controls")
 return refused
def fetch(a,path):
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open("xb")as f:subprocess.run(["gh","api","repos/"+REPO+"/releases/assets/"+str(a["id"]),"-H","Accept: application/octet-stream"],stdout=f,check=True,timeout=600)
 need(pin(path)=={k:a[k]for k in("bytes","sha256")},"whole downloaded asset")
def acquire(cfg):
 r=api("actions/runs/"+str(cfg["run"]));rel=api("releases/"+str(cfg["release"]))
 need(r["head_sha"]==cfg["source"]and r["status"]=="completed"and r["conclusion"]=="success"and r["run_attempt"]==1,"actual passed physical run")
 need(rel["target_commitish"]==cfg["source"]and rel["tag_name"]==cfg["tag"]and api("git/ref/tags/"+cfg["tag"])["object"]["sha"]==cfg["source"],"physical release source")
 live={a["name"]:a for a in rel["assets"]};need(set(live)==set(cfg["assets"]),"complete physical assets")
 for n,a in cfg["assets"].items():
  need(live[n]["id"]==a["id"]and live[n]["size"]==a["bytes"]and live[n]["digest"]=="sha256:"+a["sha256"],"actual immutable asset metadata")
  fetch(a,NATIVE/n)
 index=read(NATIVE/"complete-output-index.json");need(index==cfg["index"],"independent complete index")
 selected=set(cfg["selected"]);seen=set()
 with tarfile.open(NATIVE/"native-physical.tar.gz","r|gz")as tar:
  for m in tar:
   prefix="wire-shortcuts-physical/";need(m.isfile()and m.name.startswith(prefix),"regular physical member")
   n=m.name[len(prefix):];path=PurePosixPath(n);need(not path.is_absolute()and ".."not in path.parts and n in index["files"]and n not in seen,"unique indexed member")
   seen.add(n);h=hashlib.sha256();size=0;dest=None
   if n in selected:
    p=NATIVE/"selected"/n;p.parent.mkdir(parents=True,exist_ok=True);dest=p.open("xb")
   try:
    stream=tar.extractfile(m)
    for b in iter(lambda:stream.read(1024*1024),b""):
     size+=len(b);h.update(b)
     if dest:dest.write(b)
   finally:
    if dest:dest.close()
   need(dict(bytes=size,sha256=h.hexdigest())==index["files"][n],"every complete archive member")
 need(seen==set(index["files"])and selected<=seen,"all physical members and selections")
 q=read(NATIVE/"selected/physical/result.json")
 need(q["status"]=="PASS_NATIVE_PDK_CDR_PD650_DRC_LVS_AND_FAULT_CONTROLS"and len(q["steps"])==16,"complete physical qualification")
 need(q["steps"]["drc"]["measurement"]["markers"]==0 and q["steps"]["drc"]["measurement"]["category_count"]==560,"full zero-marker DRC")
 need(sum(s["status"]=="REJECTED_EXPECTED_FAULT"for s in q["steps"].values())==13,"all original physical faults")
 need(pin(NATIVE/"selected/layout"/(TOP+".gds"))==cfg["candidate"],"exact qualified GDS")
 save("acquisition.json",dict(run=cfg["run"],source=cfg["source"],members=len(seen),selected=cfg["selected"],**FLAGS))
def native_side(mode,wanted):
 import klayout.db as db
 base=NATIVE/"selected";p=base/"physical"/mode
 lvs=db.LayoutVsSchematic();lvs.read(str(p/"result.lvsdb"))
 need(not list(lvs.each_log_entry()),"no native extraction diagnostics")
 x=lvs.xref();need(x is not None,"native comparison cross reference")
 cps=list(x.each_circuit_pair());need(len(cps)==1 and str(cps[0].status())=="Match","one fully matched circuit")
 cp=cps[0];lc,sc=cp.first(),cp.second()
 need(lc.name==TOP and sc.name.casefold()==TOP.casefold(),"actual top")
 need("INFO : Congratulations! Netlists match."in(p/"deck.log").read_text()and "ERROR : Netlists don't match"not in(p/"deck.log").read_text(),"explicit actual deck success")
 def net(n):
  need(n is not None,"connected native net")
  return dict(cluster=n.cluster_id,name=n.expanded_name())
 def device(d,physical):
  need(d is not None,"two-sided device match");cls=d.device_class();ts={}
  for td in cls.terminal_definitions():
   t=net(d.net_for_terminal(td.id()))
   if physical:
    shapes=lvs.shapes_of_terminal(d.terminal_ref(td.id()))
    t["native_layers"]=[dict(layer=i,bbox_dbu=str(r.bbox()),area_dbu2=r.area(),polygons=[str(p)for p in r.each()])for i,r in shapes.items()]
   ts[td.name.upper()]=t
  return dict(id=d.id(),expanded_name=d.expanded_name(),model=cls.name.lower(),parameters={p.name:d.parameter(p.id())for p in cls.parameter_definitions()},terminals=ts)
 pairs=[dict(status=str(p.status()),layout=device(p.first(),True),schematic=device(p.second(),False))for p in x.each_device_pair(cp)]
 nets=[dict(status=str(n.status()),layout=net(n.first()),schematic=net(n.second()))for n in x.each_net_pair(cp)]
 ports=[dict(native_pin_id=p.id(),name=p.name(),cluster=lc.net_for_pin(p.id()).cluster_id)for p in lc.each_pin()]
 report=dict(mode=mode,pairs=pairs,nets=nets,ports=ports,terminal_count=sum(len(p["layout"]["terminals"])for p in pairs),lvsdb=pin(p/"result.lvsdb"),deck_log=pin(p/"deck.log"),**FLAGS)
 save(mode+"-observed.json",report)
 nm=validate(report,wanted)
 for r in report["pairs"]:
  w=wanted[r["schematic"]["expanded_name"]]
  r["original_source"]=w
  r["reference_to_layout_terminal"]=mapping_for(r,w,nm)
 refused=controls_on_actual(report,wanted)
 save(mode+"-identity.json",report);save(mode+"-controls.json",dict(refused=refused,count=len(refused),**FLAGS))
 return report
def publish():
 ctx=gate();tag="cloud-results-"+str(ctx["run"])+"-1-cdr-mos650-identity";rel=api("releases/tags/"+tag)
 need(rel["target_commitish"]==ctx["source"]and not rel["assets"]and api("git/ref/tags/"+tag)["object"]["sha"]==ctx["source"],"independent empty release")
 dest=OUT/"publication";dest.mkdir();rows={str(p.relative_to(OUT)):pin(p)for p in sorted(OUT.rglob("*"))if p.is_file()and dest not in p.parents}
 idx=dest/"complete-output-index.json";idx.write_bytes(enc(dict(context=ctx,files=rows,**FLAGS)))
 tarpath=dest/"native-identity.tar.gz"
 with tarfile.open(tarpath,"w:gz",compresslevel=1)as tar:
  for n in rows:tar.add(OUT/n,arcname="mos650-identity/"+n,recursive=False)
 for p in(idx,tarpath):subprocess.run(["gh","release","upload",tag,str(p),"--repo",REPO],check=True,timeout=600)
 assets=api("releases/"+str(rel["id"]))["assets"]
 for p in(idx,tarpath):
  a=next(a for a in assets if a["name"]==p.name);need(a["size"]==p.stat().st_size and a["digest"]=="sha256:"+pin(p)["sha256"],"exact uploaded output")
 save("publication.json",dict(release=rel["id"],assets=assets,**FLAGS))
def main():
 ctx=gate()
 if sys.argv[1:]==["--publish"]:publish();return
 OUT.mkdir();NATIVE.mkdir();DERIVED.mkdir()
 try:
  wanted=expected();save("source-controls.json",dict(context=ctx,expected_census=dict(Counter(r["model"]for r in wanted.values())),expected_devices=650,**FLAGS))
  if sys.argv[1:]==["--controls"]:return
  need(sys.argv[1:]==["--extract"],"explicit mode")
  cfg=read(ROOT/CFG);acquire(cfg);deep=native_side("lvs",wanted);flat=native_side("lvs_flat",wanted)
  # Native IDs may differ between modes. Compare complete semantic ownership and parameters.
  def semantic(r):
   return {p["schematic"]["expanded_name"]:dict(model=p["layout"]["model"],parameters=p["layout"]["parameters"],source=p["original_source"])for p in r["pairs"]}
  need(semantic(deep)==semantic(flat),"both independent modes bind identical complete650 semantic devices")
  gate();save("result.json",dict(status="PASS_ACTUAL650_DUAL_LVS_IDENTITY_REQUIRES_FULL_GEOMETRY_WIRE_RC",context=ctx,devices=650,terminals=2046,ports=25,refusals_per_mode=15,physical_run=cfg["run"],**FLAGS))
 except BaseException as e:save("failure.json",dict(error=repr(e),traceback=traceback.format_exc(),**FLAGS));raise
if __name__=="__main__":main()
