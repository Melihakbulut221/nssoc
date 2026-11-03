#!/usr/bin/env python3
"""Inspect exact compact-model gate controls and actual gate access geometry in cloud."""
import hashlib,json,os,re,subprocess,sys,tarfile,traceback
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"mos650-gate-model";NATIVE=OUT/"native";DERIVED=OUT/"derived"
CFG="scripts/cdr-mos650-gate-model-inputs.json";PINS="scripts/cdr-mos650-gate-model-pins.json"
REPO="Melihakbulut221/nssoc";BRANCH="codex/cdr-mos650-gate-model"
FLAGS=dict(gate_poly_RC_extracted=False,mim_intrinsic_composition_qualified=False,substrate_r_modeled=False,
 full_pex_qualified=False,electrical_accepted=False,full_phy_accepted=False,final_timing_complete=False)
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
 need(sys.flags.optimize==0 and e["GITHUB_SHA"]==e["APPROVED_SOURCE"]==subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),"exact source and enabled assertions")
 for n,p in read(ROOT/PINS)["files"].items():need(pin(ROOT/n)==p,"source "+n)
 return dict(run=int(e["GITHUB_RUN_ID"]),source=e["GITHUB_SHA"],attempt=1)
def fetch(a,path):
 with path.open("xb")as f:subprocess.run(["gh","api","repos/"+REPO+"/releases/assets/"+str(a["id"]),"-H","Accept: application/octet-stream"],stdout=f,check=True,timeout=600)
 need(pin(path)=={k:a[k]for k in("bytes","sha256")},"whole asset content")
def acquire(prod,dest,selector):
 r=api("actions/runs/"+str(prod["run"]));rel=api("releases/"+str(prod["release"]))
 need(r["head_sha"]==prod["source"]and r["status"]=="completed"and r["conclusion"]=="success"and r["run_attempt"]==1,"actual qualified producer")
 need(rel["target_commitish"]==prod["source"]and rel["tag_name"]==prod["tag"]and api("git/ref/tags/"+prod["tag"])["object"]["sha"]==prod["source"],"qualified release/tag identity")
 actual={a["name"]:a for a in rel["assets"]};need(set(actual)==set(prod["assets"]),"complete producer assets")
 cache=NATIVE/("producer-"+str(prod["run"]));cache.mkdir()
 for n,a in prod["assets"].items():
  need(actual[n]["id"]==a["id"]and actual[n]["size"]==a["bytes"]and actual[n]["digest"]=="sha256:"+a["sha256"],"immutable asset metadata")
  fetch(a,cache/n)
 index=read(cache/"complete-output-index.json")
 need(index["context"]==dict(run=prod["run"],source=prod["source"],attempt=1),"complete index context")
 selected={n:p for n,p in index["files"].items()if selector(n)}
 need(selected==prod["selected"],"complete independently bound selection")
 seen=set()
 with tarfile.open(cache/prod["archive"],"r|gz")as tar:
  for m in tar:
   prefix=prod["archive_root"]+"/";need(m.isfile()and m.name.startswith(prefix),"regular archive member")
   n=m.name[len(prefix):];path=PurePosixPath(n)
   need(n in index["files"]and n not in seen and not path.is_absolute()and ".."not in path.parts,"unique indexed member");seen.add(n)
   stream=tar.extractfile(m);h=hashlib.sha256();size=0;output=None
   if n in selected:
    p=dest/n;p.parent.mkdir(parents=True,exist_ok=True);output=p.open("xb")
   try:
    for b in iter(lambda:stream.read(1024*1024),b""):
     size+=len(b);h.update(b)
     if output:output.write(b)
   finally:
    if output:output.close();os.chmod(dest/n,m.mode&0o777)
   need(dict(bytes=size,sha256=h.hexdigest())==index["files"][n],"every indexed archive member authenticated")
 need(seen==set(index["files"]),"whole producer archive coverage")
 save("acquisition-"+str(prod["run"])+".json",dict(producer=prod,members=len(seen),selected=selected,**FLAGS))
 return selected
def publish():
 ctx=gate();tag="cloud-results-"+str(ctx["run"])+"-1-cdr-mos650-gate-model";rel=api("releases/tags/"+tag)
 need(rel["target_commitish"]==ctx["source"]and not rel["assets"]and api("git/ref/tags/"+tag)["object"]["sha"]==ctx["source"],"independent empty release")
 dest=OUT/"publication";dest.mkdir()
 paths=[p for p in OUT.rglob("*")if p.is_file()and dest not in p.parents]
 # The authenticated current view is preserved in its immutable producer release.
 rows={str(p.relative_to(OUT)):pin(p)for p in sorted(paths)}
 index=dest/"complete-output-index.json";index.write_bytes(enc(dict(context=ctx,files=rows,**FLAGS)))
 archive=dest/"native-gate-model.tar.gz"
 with tarfile.open(archive,"w:gz",compresslevel=1)as tar:
  for n in rows:tar.add(OUT/n,arcname="mos650-gate-model/"+n,recursive=False)
 for p in(index,archive):subprocess.run(["gh","release","upload",tag,str(p),"--repo",REPO],check=True,timeout=1200)
 assets=api("releases/"+str(rel["id"]))["assets"]
 for p in(index,archive):
  a=next(a for a in assets if a["name"]==p.name);need(a["size"]==p.stat().st_size and a["digest"]=="sha256:"+pin(p)["sha256"],"exact published output")
 save("publication.json",dict(release=rel["id"],assets=assets,**FLAGS))

def acquire_models(cfg):
 p=cfg["producer"];r=api("actions/runs/"+str(p["run_id"]));rel=api("releases/"+str(p["release_id"]))
 need(r["status"]=="completed"and r["conclusion"]==p["conclusion"]=="failure"and r["head_sha"]==p["source"]and r["run_attempt"]==1,"preserve historical measurement failure; runtime only")
 need(rel["target_commitish"]==p["actual_target_commitish"]and api("git/ref/tags/"+p["tag"])["object"]["sha"]==p["source"],"exact historical runtime release")
 actual={a["name"]:a for a in rel["assets"]}
 need(set(actual)=={a["name"]for a in p["assets"]},"all runtime assets")
 for a in p["assets"]:
  need(actual[a["name"]]["id"]==a["id"]and actual[a["name"]]["size"]==a["bytes"]and actual[a["name"]]["digest"]=="sha256:"+a["sha256"],"runtime asset metadata")
 for n,expected in cfg["records"].items():need(pin(ROOT/n)==expected,"runtime record "+n)
 summary=read(ROOT/"docs/evidence/cdr-via2-m3-loaded-runtime-inputs/pump-summary.json")
 expected=dict(summary["outputs"]);expected["result.json"]=pin(ROOT/"docs/evidence/cdr-via2-m3-loaded-runtime-inputs/pump-summary.json")["sha256"]
 selected={n for n in expected if n.startswith("source/model-sources/")or n in("source-pin.json","source/runtime/patched-ngspice","result.json")}
 need(len(expected)==120 and len(selected)==40,"complete known runtime selection")
 a=next(a for a in p["assets"]if ".tar.gz.part"in a["name"]);archive=NATIVE/"model-runtime.tar.gz";fetch(a,archive)
 dest=NATIVE/"models";dest.mkdir();seen={}
 with tarfile.open(archive,"r|gz")as tar:
  for member in tar:
   if member.name==p["archive_root"]and member.isdir():continue
   prefix=p["archive_root"]+"/";need(member.name.startswith(prefix),"runtime archive root")
   n=member.name[len(prefix):];path=PurePosixPath(n)
   need(n and not path.is_absolute()and ".."not in path.parts,"runtime member path")
   if member.isdir():continue
   need(member.isfile()and n in expected and n not in seen,"unique runtime member")
   stream=tar.extractfile(member);h=hashlib.sha256();size=0;output=None
   if n in selected:
    target=dest/n;target.parent.mkdir(parents=True,exist_ok=True);output=target.open("xb")
   try:
    for b in iter(lambda:stream.read(1024*1024),b""):
     size+=len(b);h.update(b)
     if output:output.write(b)
   finally:
    if output:output.close()
   need(size==member.size and h.hexdigest()==expected[n],"every original runtime member")
   seen[n]=dict(bytes=size,sha256=h.hexdigest())
 need(set(seen)==set(expected),"complete120 member coverage")
 need(pin(dest/"source/runtime/patched-ngspice")["sha256"]==p["engine_sha256"]and pin(dest/"source-pin.json")["sha256"]==p["model_pin_sha256"],"exact loaded engine/model provenance")
 save("model-runtime-acquisition.json",dict(producer=p,all_members=seen,selected=sorted(selected),historical_failed_measurement_preserved=True,**FLAGS))
 return dest/"source/model-sources"

def logical_lines(text):
 out=[]
 for number,line in enumerate(text.splitlines(),1):
  value=line.strip()
  if value.startswith("+")and out:out[-1]["text"]+=" "+value[1:].strip();out[-1]["end_line"]=number
  else:out.append(dict(line=number,end_line=number,text=value))
 return out

def model_report(lib):
 # Read actual frozen model cards only in the hosted job. Export a derived
 # report of relevant controls, with source hashes and exact locations.
 pattern=re.compile(r"\b(?:rfmode|rgatemod|rshg|rgsh|rgate|rg0|rge|rgo|rsh|ng|psp|pspnqs|nqs|swrg|swnqs|rg|rpoly|rcontact)\b",re.I)
 report={}
 for p in sorted(lib.rglob("*")):
  if not p.is_file():continue
  raw=p.read_bytes()
  if p.suffix==".osdi":
   need(raw.startswith(b"\x7fELF"),"actual compiled OSDI model")
   report[str(p.relative_to(lib))]=dict(source=pin(p),kind="compiled_osdi_model",controls=[],includes_and_subcircuits=[])
   continue
  need(p.suffix in(".cir",".spice",".lib"),"declared textual model format")
  try:text=raw.decode("utf-8");encoding="utf-8"
  except UnicodeDecodeError:text=raw.decode("latin-1");encoding="latin-1"
  need(text.encode(encoding)==raw,"lossless model report decoding")
  lines=logical_lines(text)
  hits=[r for r in lines if pattern.search(r["text"])and not r["text"].lstrip().startswith("*")]
  # .model statements can be very long: retain model type and individual
  # relevant assignments, never disguise the complete model deck as a report.
  rows=[]
  for r in hits:
   value=r["text"]
   if value.lower().startswith(".model"):
    tokens=value.split();assignments=re.findall(r"([A-Za-z_]\w*)\s*=\s*(\{[^}]*\}|'[^']*'|[^\s)]+)",value)
    rows.append(dict(line=r["line"],end_line=r["end_line"],kind="model",name=tokens[1],model_type=tokens[2],
      parameters=[dict(name=k,value=v)for k,v in assignments if pattern.fullmatch(k)]))
   else:rows.append(r)
  includes=[r for r in lines if r["text"].lower().startswith((".include ",".lib ",".subckt "))]
  report[str(p.relative_to(lib))]=dict(source=pin(p),text_encoding=encoding,controls=rows,includes_and_subcircuits=includes)
 need(any(v["controls"]for v in report.values()),"actual MOS model control evidence")
 save("compact-model-gate-controls.json",dict(files=report,interpretation_pending=True,**FLAGS))

def tech_report(runtime):
 report={}
 for p in sorted(runtime.rglob("*.tech")):
  lines=p.read_text().splitlines();hits=[]
  section=None
  for i,line in enumerate(lines,1):
   s=line.strip()
   if s and not s.startswith("#")and not line[0].isspace():section=s.split()[0]
   if re.search(r"\b(?:poly|polysilicon|gate|polycont|pc|nsc|psc|nfet|pfet|nsd|psd|rppd)\b",s,re.I):
    hits.append(dict(line=i,section=section,text=s))
  if hits:report[str(p.relative_to(runtime))]=dict(source=pin(p),matches=hits)
 save("technology-poly-contact-controls.json",dict(files=report,numerical_interpretation_pending=True,**FLAGS))

def geometry_report(physical):
 data=read(physical/"derived/gate-poly-access.json")
 groups={}
 for row in data["gates"]:
  key=json.dumps([row["access_poly_polygons"],row["contact_polygons"]],sort_keys=True)
  groups.setdefault(key,[]).append(row)
 need(len(data["gates"])==200 and len(groups)==50,"all physical gate groups")
 result=[]
 for rows in groups.values():
  result.append(dict(devices=[r["device"]for r in rows],native_clusters=sorted({r["native_cluster"]for r in rows}),
   access_poly_polygons=rows[0]["access_poly_polygons"],contact_polygons=rows[0]["contact_polygons"],
   terminal_polygons={str(r["device"]):r["terminal_polygons"]for r in rows}))
 save("gate-geometry-inputs.json",dict(groups=result,physical_groups=len(result),devices=200,derived_from_current_native_flat_LVS=True,**FLAGS))

def main():
 ctx=gate()
 if sys.argv[1:]==["--publish"]:publish();return
 OUT.mkdir();NATIVE.mkdir();DERIVED.mkdir()
 try:
  cfg=read(ROOT/CFG)
  if sys.argv[1:]==["--controls"]:
   need(cfg["runtime"]["producer"]["run_id"]==39029337682,"frozen model runtime")
   need(cfg["view"]["run"]==41690238100 and cfg["magic"]["run"]==41547492718,"exact actual geometry and native tech")
   save("source-controls.json",dict(context=ctx,source_files_verified=True,**FLAGS));return
  need(sys.argv[1:]==["--extract"],"explicit cloud audit")
  models=acquire_models(cfg["runtime"]);model_report(models)
  magic=NATIVE/"magic";magic.mkdir()
  acquire(cfg["magic"],magic,lambda n:n.startswith("wire-stage/magic-cloud/"))
  tech_report(magic/"wire-stage/magic-cloud/tech")
  physical=NATIVE/"physical";physical.mkdir()
  acquire(cfg["view"],physical,lambda n:n=="derived/gate-poly-access.json")
  geometry_report(physical)
  gate();save("result.json",dict(status="ACTUAL_FROZEN_MODEL_AND_POLY_GEOMETRY_REPORT_REQUIRES_RC_INTERPRETATION",context=ctx,
   physical_gate_groups=50,actual_mos_units=200,gate_resistance_qualified=False,**FLAGS))
 except BaseException as e:
  save("failure.json",dict(error_type=type(e).__name__,error=str(e),traceback=traceback.format_exc(),**FLAGS));raise
if __name__=="__main__":main()
