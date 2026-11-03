#!/usr/bin/env python3
"""Inspect exact compact-model gate controls and actual gate access geometry in cloud."""
import hashlib,json,os,re,subprocess,sys,tarfile,traceback,time,signal,math
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"mos650-gate-ac";NATIVE=OUT/"native";DERIVED=OUT/"derived"
CFG="scripts/cdr-mos650-gate-ac-inputs.json";PINS="scripts/cdr-mos650-gate-ac-pins.json"
REPO="Melihakbulut221/nssoc";BRANCH="codex/cdr-mos650-full-composition-n2"
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
 need(e["GATE_PARTITION"]=="2"and e["LOADED_CASE"]=="nominal_late","exact independently dispatched comparison")
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
 ctx=gate();tag="cloud-results-"+str(ctx["run"])+"-1-cdr-mos650-gate-ac";rel=api("releases/tags/"+tag)
 need(rel["target_commitish"]==ctx["source"]and not rel["assets"]and api("git/ref/tags/"+tag)["object"]["sha"]==ctx["source"],"independent empty release")
 dest=OUT/"publication";dest.mkdir()
 paths=[p for p in OUT.rglob("*")if p.is_file()and dest not in p.parents]
 # The authenticated current view is preserved in its immutable producer release.
 rows={str(p.relative_to(OUT)):pin(p)for p in sorted(paths)}
 index=dest/"complete-output-index.json";index.write_bytes(enc(dict(context=ctx,files=rows,**FLAGS)))
 archive=dest/"native-gate-ac.tar.gz"
 with tarfile.open(archive,"w:gz",compresslevel=1)as tar:
  for n in rows:tar.add(OUT/n,arcname="mos650-gate-ac/"+n,recursive=False)
 from cdr_mos650_archive_transport import partition
 parts,transport=partition(archive)
 outputs=[index,*parts]
 if transport is not None:
  manifest=dest/"archive-parts.json";manifest.write_bytes(enc(dict(context=ctx,transport=transport,**FLAGS)));outputs.append(manifest)
 for p in outputs:subprocess.run(["gh","release","upload",tag,str(p),"--repo",REPO],check=True,timeout=1200)
 assets=api("releases/"+str(rel["id"]))["assets"]
 for p in outputs:
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
 pattern=re.compile(r"\b(?:rfmode|pre_layout|rgatemod|rshg|rgsh|rgate|rg0|rge|rgo|rsh|ng|ngcon|psp|pspnqs|nqs|swrg|swgeo|swnqs|rg|rpoly|rcontact)\b",re.I)
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
   if re.search(r"\b(?:poly|allpoly|polysilicon|gate|polycont|pc|nsc|psc|nfet|pfet|nsd|psd|rppd|resist|style|variants)\b",s,re.I):
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

def execute(argv,label,seconds=1200,cwd=None):
 so=NATIVE/(label+".stdout");se=NATIVE/(label+".stderr");begin=time.monotonic();proc=None;error=None
 env={k:v for k,v in os.environ.items()if k not in("GH_TOKEN","GITHUB_TOKEN","PYTHONOPTIMIZE","LD_PRELOAD","PYTHONPATH","PYTHONHOME")}
 if cwd is not None:
  need((Path(cwd)/"spinit").is_file(),"explicit native startup configuration")
  env["SPICE_SCRIPTS"]=str(cwd)
 try:
  with so.open("xb")as stdout,se.open("xb")as stderr:
   proc=subprocess.Popen(list(map(str,argv)),stdout=stdout,stderr=stderr,env=env,start_new_session=True,cwd=cwd or ROOT)
   try:proc.wait(timeout=seconds)
   except subprocess.TimeoutExpired:
    os.killpg(proc.pid,signal.SIGTERM)
    try:proc.wait(timeout=10)
    except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
    raise
   need(proc.returncode==0,"native command "+label+" failed")
 except BaseException as e:error=e
 finally:
  if proc is not None:
   def live_members():
    found=[]
    for path in Path("/proc").glob("[0-9]*/stat"):
     try:
      raw=path.read_text();fields=raw[raw.rfind(")")+2:].split()
      if int(fields[2])==proc.pid and fields[0]not in("Z","X"):found.append(int(path.parent.name))
     except FileNotFoundError:pass
    return found
   live=live_members()
   if live:
    error=error or RuntimeError("owned command group left live children")
    try:os.killpg(proc.pid,signal.SIGTERM)
    except ProcessLookupError:pass
    try:proc.wait(timeout=10)
    except subprocess.TimeoutExpired:pass
    if live_members():
     try:os.killpg(proc.pid,signal.SIGKILL)
     except ProcessLookupError:pass
    proc.wait(timeout=10)
    deadline=time.monotonic()+5
    while live_members()and time.monotonic()<deadline:time.sleep(.1)
    need(not live_members(),"owned native group did not stop")
  for p in(so,se):
   if p.exists():(DERIVED/p.name).write_bytes(p.read_bytes())
  save(label+"-command.json",dict(argv=list(map(str,argv)),returncode=None if proc is None else proc.returncode,elapsed_seconds=time.monotonic()-begin,
   error=None if error is None else repr(error),stdout=pin(so)if so.exists()else None,stderr=pin(se)if se.exists()else None,**FLAGS))
 if error is not None:raise error

def current_cases(identity,access):
 def box(polygons):
  need(len(polygons)==1,"single actual rectangular gate/contact")
  pairs=[tuple(map(int,p))for p in re.findall(r"(-?\d+),(-?\d+)",polygons[0])]
  need(len(pairs)==4 and len(set(pairs))==4,"four actual rectangle corners")
  xs=[p[0]for p in pairs];ys=[p[1]for p in pairs]
  b=[min(xs),min(ys),max(xs),max(ys)]
  need(set(pairs)=={(x,y)for x in(b[0],b[2])for y in(b[1],b[3])},"axis-aligned actual rectangle")
  return b
 mos={p["layout"]["id"]:p["layout"]for p in identity["pairs"]if p["layout"]["model"]=="sg13_lv_nmos"}
 need(len(mos)==200 and len(access["gates"])==200,"current physical MOS count")
 rows=[]
 for g in access["gates"]:
  m=mos[g["device"]];p=m["parameters"];b=box(g["terminal_polygons"])
  need(m["terminals"]["G"]["cluster"]==g["native_cluster"],"same native gate owner")
  need(abs((b[2]-b[0])*.001-p["L"])<1e-9 and abs((b[3]-b[1])*.001-p["W"])<1e-9,"actual gate dimensions")
  contacts=[box([poly])for poly in g["contact_polygons"]]
  need(all(c[0]>=b[0]and c[2]<=b[2]for c in contacts),"all contacts on same narrow gate axis")
  below=[c[3]for c in contacts if c[3]<=b[1]]
  above=[c[1]for c in contacts if c[1]>=b[3]]
  need(len(below)+len(above)==len(contacts),"no contact inside intrinsic channel")
  rows.append(dict(native_id=g["device"],parameters=p,contacted_ends=int(bool(below))+int(bool(above)),
   gate_group=g["gate_group"],native_cluster=g["native_cluster"],terminal_bbox_dbu=b,
   nearest_below_edge_dbu=max(below)if below else None,nearest_above_edge_dbu=min(above)if above else None))
 need(len({r["native_id"]for r in rows})==200 and sum(r["contacted_ends"]==1 for r in rows)==50 and sum(r["contacted_ends"]==2 for r in rows)==150,"complete current physical contacted ends")
 return sorted(rows,key=lambda r:r["native_id"])

def intrinsic_variant(models):
 import shutil
 fixture=read(ROOT/"docs/evidence/mos650-current-gate-model-cases.json");geometries={}
 for unit in fixture["devices"]:
  p=unit["parameters"];key=tuple(p[k]for k in("W","L","AS","AD","PS","PD"))
  geometries.setdefault(key,[]).append(unit["native_id"])
 need(len(fixture["devices"])==200 and len(geometries)==4,"complete current physical dimensions")
 original={str(p):pin(p)for p in models.rglob("*")if p.is_file()}
 variant=NATIVE/"intrinsic-models";shutil.copytree(models/"models",variant/"models")
 model=variant/"models/models/sg13g2_moslv_parm.lib";raw=model.read_bytes();source=raw.decode("latin-1")
 matches=[row for row in logical_lines(source)if re.match(r"(?i)^\.model\s+sg13g2_lv_nmos_psp_rf\s+pspnqs103va\b",row["text"])]
 need(len(matches)==1,"exact single frozen RF NMOS model")
 row=matches[0];lines=source.splitlines(keepends=True);start=sum(len(t)for t in lines[:row["line"]-1]);end=sum(len(t)for t in lines[:row["end_line"]])
 block=source[start:end];changed=block
 for key,value in (("rgo","40.0"),("rshg","3.0")):
  pattern=r"(?i)\b"+key+r"\s*=\s*'rfmode\s*\*\s*"+re.escape(value)+r"'"
  changed,count=re.subn(pattern,key+"=0.0",changed);need(count==1,"exact original RF "+key+" assignment")
 modified=source[:start]+changed+source[end:];model.write_bytes(modified.encode("latin-1"))
 need(modified[:start]==source[:start]and modified.endswith(source[end:]),"no outside RF model changes")
 save("intrinsic-model-derivation.json",dict(source_file="models/models/sg13g2_moslv_parm.lib",original=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()),variant=pin(model),
  original_RF_RGO_ohm=40,original_RF_RSHG_ohm=3,variant_RF_RGO_ohm=0,variant_RF_RSHG_ohm=0,
  retained_RINT_RVPOLY_and_all_other_model_parameters=True,original_files_unchanged=True,physical_poly_network_present=False,**FLAGS))
 variant_pins={str(p):pin(p)for p in variant.rglob("*")if p.is_file()}
 engine=NATIVE/"models/source/runtime/patched-ngspice";engine.chmod(0o755)

 need(pin(model)["sha256"]=="dc3d592a1b2ee61074e4d3c473021b788e0d88a4a229c3ee2264e752fd61be9a","exact independently qualified intrinsic variant")
 need(all(pin(Path(p))==v for p,v in original.items()),"unchanged original models")
 return variant


def characterize(models):
 import cdr_mos650_full650 as full
 import cdr_mos650_full650_loaded as loaded
 cfg=read(ROOT/CFG)
 mim=NATIVE/"mim-current";mim.mkdir();acquire(cfg["mim"],mim,lambda n:n in cfg["mim"]["selected"])
 reduction=NATIVE/"gate-reduction";reduction.mkdir();acquire(cfg["reduction"],reduction,lambda n:n in cfg["reduction"]["selected"])
 identity=read(NATIVE/"current-wire/derived/lvs_flat-identity.json")
 anchors=read(mim/"native/mim-precise/wire/anchors08.json")
 legacy=read(NATIVE/"magic/binding/binding.json")
 metal=(mim/"native/mim-precise/wire/rc03/wires.spice").read_text()
 mimproof=read(mim/"derived/precise-mim-result.json")
 capture=mimproof["result"]["capture"]
 fixture=read(ROOT/"docs/evidence/mos650-current-gate-model-cases.json")
 results={}
 for n in(1,2,4,8,16):
  parts=[]
  for gi in range(50):
   folder=reduction/f"native/reduction-g{gi}-n{n}"
   parts.append((read(folder/"ports-and-matrices.json"),(folder/"reduced-positive-resistors.cir").read_text()))
  text,contract=full.assemble(identity,anchors,legacy,metal,capture,parts,fixture,n)
  bound=full.probes(contract)
  target=NATIVE/f"composition-n{n}";target.mkdir()
  (target/"model.cir").write_text(text)
  (target/"contract.json").write_bytes(enc(contract))
  (target/"probes.json").write_bytes(enc(bound))
  results[n]=(target,contract,bound)
  save(f"composition-n{n}.json",dict(partition=n,model=pin(target/"model.cir"),contract=pin(target/"contract.json"),
    probes=pin(target/"probes.json"),physical_devices=650,actual_intrinsic_MOS_instances=200*n,
    metal_R=28634,metal_C=18476,native_MIM=7,physical_tail_units=bound["physical_mos_tail_count"],
    original_tail_families=bound["original_mos_tail_families"],stage_groups=len(bound["mos_tail_groups"]),
    all_actual_terminal_bindings_checked=True,**FLAGS))
  print("ASSEMBLED_ACTUAL650_PARTITION",n,flush=True)
 variant=intrinsic_variant(models)
 engine=NATIVE/"models/source/runtime/patched-ngspice";engine.chmod(0o755)
 n=int(os.environ["GATE_PARTITION"]);case=os.environ["LOADED_CASE"]
 need(n in results and case in loaded.CASES,"explicit selected full circuit case")
 target,contract,bound=results[n]
 result=loaded.run_loaded(sys.modules[__name__],models,variant,engine,target/"model.cir",contract,bound,case)
 save("selected-whole-loaded-summary.json",dict(case=case,partition=n,status=result["status"],
    all256bits_executed=True,unchanged_original_electrical_gates=True,**FLAGS))
 return n


def main():
 ctx=gate()
 if sys.argv[1:]==["--publish"]:publish();return
 OUT.mkdir();NATIVE.mkdir();DERIVED.mkdir()
 try:
  cfg=read(ROOT/CFG)
  if sys.argv[1:]==["--controls"]:
   need(cfg["runtime"]["producer"]["run_id"]==39029337682,"exact frozen model runtime")
   from cdr_mos650_archive_transport import controls
   save("archive-transport-controls.json",controls())
   data=read(ROOT/"docs/evidence/mos650-current-gate-model-cases.json")
   need(len(data["devices"])==200 and len({r["native_id"]for r in data["devices"]})==200,"all current native gates")
   need(cfg["current_wire"]["run"]==41712243960 and data["source_members"]==cfg["current_wire"]["selected"],"actual current source binding")
   need(os.environ["GATE_PARTITION"]=="2"and os.environ["LOADED_CASE"]=="nominal_late","explicit N2 full loaded comparison case")
   save("source-controls.json",dict(context=ctx,selected_partition=2,selected_case="nominal_late",source_files_verified=True,**FLAGS));return
  need(sys.argv[1:]==["--extract"],"explicit cloud characterization")
  current=NATIVE/"current-wire";current.mkdir()
  acquire(cfg["current_wire"],current,lambda n:n in cfg["current_wire"]["selected"])
  observed=current_cases(read(current/"derived/lvs_flat-identity.json"),read(current/"derived/gate-poly-access.json"))
  need(observed==read(ROOT/"docs/evidence/mos650-current-gate-model-cases.json")["devices"],"complete native current fixture readback")
  save("current-physical-cases.json",dict(devices=observed,source=cfg["current_wire"],**FLAGS))
  models=acquire_models(cfg["runtime"]);model_report(models)
  magic=NATIVE/"magic";magic.mkdir()
  acquire(cfg["magic"],magic,lambda n:n in cfg["magic"]["selected"])
  count=characterize(models)
  gate();save("result.json",dict(status="PASS_SELECTED_WHOLE650_LOADED_CASE_REQUIRES_REFINEMENT_PVT_CLOSED_LOOP_AND_PHY",context=ctx,
   selected_partition=count,actual_mos_units=200,gate_resistance_qualified=False,**FLAGS))
 except BaseException as e:
  save("failure.json",dict(error_type=type(e).__name__,error=str(e),traceback=traceback.format_exc(),**FLAGS));raise
if __name__=="__main__":main()
