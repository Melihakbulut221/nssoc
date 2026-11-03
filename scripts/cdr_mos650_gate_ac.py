#!/usr/bin/env python3
"""Inspect exact compact-model gate controls and actual gate access geometry in cloud."""
import hashlib,json,os,re,subprocess,sys,tarfile,traceback,time,signal,math
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"mos650-gate-ac";NATIVE=OUT/"native";DERIVED=OUT/"derived"
CFG="scripts/cdr-mos650-gate-ac-inputs.json";PINS="scripts/cdr-mos650-gate-ac-pins.json"
REPO="Melihakbulut221/nssoc";BRANCH="codex/cdr-mos650-gate-contact-ac"
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

def execute(argv,label,seconds=1200):
 so=NATIVE/(label+".stdout");se=NATIVE/(label+".stderr");begin=time.monotonic();proc=None;error=None
 env={k:v for k,v in os.environ.items()if k not in("GH_TOKEN","GITHUB_TOKEN","PYTHONOPTIMIZE","LD_PRELOAD","PYTHONPATH","PYTHONHOME")}
 try:
  with so.open("xb")as stdout,se.open("xb")as stderr:
   proc=subprocess.Popen(list(map(str,argv)),stdout=stdout,stderr=stderr,env=env,start_new_session=True,cwd=ROOT)
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

def characterize(models):
 import shutil
 fixture=read(ROOT/"docs/evidence/mos650-current-gate-model-cases.json")
 units=fixture["devices"]
 need(len(units)==200 and len({u["native_id"]for u in units})==200,"complete actual current intrinsic gates")
 need({str(n):sum(u["contacted_ends"]==n for u in units)for n in(1,2)}=={"1":50,"2":150},"actual one/two-ended geometry")
 geometries={}
 for u in units:
  p=u["parameters"];key=tuple(p[k]for k in("W","L","AS","AD","PS","PD"))
  geometries.setdefault(key,{}).setdefault(u["contacted_ends"],[]).append(u["native_id"])
 need(len(geometries)==4,"all four current physical dimensions")
 original_files={str(p):pin(p)for p in models.rglob("*")if p.is_file()}
 variant=NATIVE/"ngcon-models";shutil.copytree(models/"models",variant/"models")
 mod=variant/"models/models/sg13g2_moslv_mod.lib";raw=mod.read_bytes();text=raw.decode("latin-1")
 match=re.search(r"(?ims)^\.subckt[ \t]+sg13_lv_nmos[ \t].*?^\.ends[^\r\n]*",text)
 need(match is not None,"exact original lv NMOS wrapper")
 block=match.group();need(block.count("ngcon=2")==6 and "gate_ngcon"not in block,"six original hardcoded contact counts")
 lines=block.splitlines(keepends=True);head=lines[0];ending="\r\n"if head.endswith("\r\n")else"\n"
 need(head.endswith(ending),"original header newline")
 lines[0]=head[:-len(ending)]+" gate_ngcon=2"+ending
 updated="".join(lines).replace("ngcon=2","ngcon='gate_ngcon'")
 # The inserted gate_ngcon=2 must retain its default; replace only instance tokens.
 updated=updated.replace("gate_ngcon='gate_ngcon'","gate_ngcon=2")
 need(updated.count("ngcon='gate_ngcon'")==6 and updated.count("gate_ngcon=2")==1,"only six instance arguments and one default")
 new=text[:match.start()]+updated+text[match.end():];mod.write_bytes(new.encode("latin-1"))
 need(text[:match.start()]==new[:match.start()]and new.endswith(text[match.end():]),"all outside-wrapper text unchanged")
 derivation=dict(source_file="models/models/sg13g2_moslv_mod.lib",original=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()),
  variant=pin(mod),original_block_sha256=hashlib.sha256(block.encode("latin-1")).hexdigest(),variant_block_sha256=hashlib.sha256(updated.encode("latin-1")).hexdigest(),
  original_instance_ngcon=2,variant_default=2,instance_replacements=6,all_resistance_model_parameters_unchanged=True,full_model_qualification=False)
 save("ngcon-wrapper-derivation.json",dict(derivation,**FLAGS))
 engine=NATIVE/"models/source/runtime/patched-ngspice";engine.chmod(0o755)
 basecases=[];cases=[]
 for i,(dimensions,ends)in enumerate(sorted(geometries.items())):
  W,L,AS,AD,PS,PD=dimensions
  for rf in(0,1):
   common=dict(rfmode=rf,W_um=W,L_um=L,AS_um2=AS,AD_um2=AD,PS_um=PS,PD_um=PD,drain_bias_V=.6,gate_bias_V=.8)
   basecases.append(dict(common,label=f"g{i}n2r{rf}",ngcon=2,physical_native_ids=sorted(d for ids in ends.values()for d in ids),canonical_default_reference=True))
   for ngcon,ids in sorted(ends.items()):
    cases.append(dict(common,label=f"g{i}n{ngcon}r{rf}",ngcon=ngcon,physical_native_ids=sorted(ids),canonical_default_reference=False))
 need(len(basecases)==8 and len(cases)==14,"complete dimension/contact/QS-RF cases")
 def sweep(label,lib,cases,override):
  ac=NATIVE/label;ac.mkdir()
  deck=["* Current explicit physical MOS dimensions and contact-count diagnostic",f'.lib "{lib}/models/models/cornerMOSlv.lib" mos_tt',"Vd d 0 0.6"]
  for case in cases:
   n=case["label"];W,L,AS,AD,PS,PD=[case[k]for k in("W_um","L_um","AS_um2","AD_um2","PS_um","PD_um")]
   extra=f' gate_ngcon={case["ngcon"]}'if override else""
   deck += [f"V{n} {n} 0 DC 0.8 AC 1",
    f'X{n} d {n} 0 0 sg13_lv_nmos w={W:.12g}u l={L:.12g}u as={AS*1e-12:.12g} ad={AD*1e-12:.12g} ps={PS:.12g}u pd={PD:.12g}u ng=1 m=1 rfmode={case["rfmode"]} pre_layout=0'+extra]
  deck += [".control",f"pre_osdi {models}/frontend/psp103.osdi",f"pre_osdi {models}/frontend/psp103_nqs.osdi",
   "set num_threads=1","set numdgt=16","set wr_singlescale","set wr_vecnames","op","show all",
   "echo NSSOC_GATE_INSTANCE_READBACK_BEGIN"]
  for case in cases:deck.append(f'print @n.x{case["label"]}.nsg13_lv_nmos[ngcon]')
  deck+=["echo NSSOC_GATE_INSTANCE_READBACK_END","echo NSSOC_GATE_MODEL_READBACK_BEGIN","showmod","echo NSSOC_GATE_MODEL_READBACK_END","ac dec 4 1meg 10g"]
  columns=[]
  for case in cases:
   n=case["label"];deck += [f"let z{n} = -1 / v{n}#branch",f"let r{n} = real(z{n})",f"let x{n} = imag(z{n})"];columns += [f"r{n}",f"x{n}"]
  deck += [f"wrdata {ac}/impedance.txt "+" ".join(columns),"quit",".endc",".end"]
  (ac/"bench.cir").write_text("\n".join(deck)+"\n");(ac/"spinit").write_text("set num_threads=1\n")
  os.environ["SPICE_SCRIPTS"]=str(ac);os.environ["OMP_NUM_THREADS"]="1"
  execute([engine,"-n","-b",ac/"bench.cir"],label,180)
  log=(NATIVE/(label+".stdout")).read_text()+(NATIVE/(label+".stderr")).read_text()
  bad=[line for line in log.splitlines()if re.search(r"error|warning|no such vector|not found|unknown parameter|singular matrix|timestep too small",line,re.I)]
  save(label+"-diagnostics.json",dict(lines=bad,**FLAGS));need(not bad,"all native diagnostics require investigation")
  need(log.count("NSSOC_GATE_INSTANCE_READBACK_BEGIN")==1 and log.count("NSSOC_GATE_INSTANCE_READBACK_END")==1,"actual instance readback markers")
  actual=[]
  for case in cases:
   key=f'@n.x{case["label"]}.nsg13_lv_nmos[ngcon]'
   values=re.findall(re.escape(key)+r"\s*=\s*([0-9.eE+-]+)",log,re.I)
   need(len(values)==1 and float(values[0])==case["ngcon"],"actual native instance NGCON "+key)
   actual.append(dict(instance=key,ngcon=float(values[0]),expected=case["ngcon"]))
  readback=[dict(line=i,text=line)for i,line in enumerate(log.splitlines(),1)if re.search(r"^\s*(model|swgeo|rgo|rshg|rint|rvpoly|dlsil|xgw|swnqs)\s",line,re.I)]
  need(all(any(re.match(r"\s*"+key+r"\s",row["text"],re.I)for row in readback)for key in("swgeo","rgo","rshg","rint","rvpoly","dlsil","swnqs")),"all compact-model resistance/mode readbacks present")
  rows=(ac/"impedance.txt").read_text().splitlines();header=rows[0].split()
  need(header==["frequency"]+columns,"complete physical case columns")
  data=[[float(v)for v in row.split()]for row in rows[1:]]
  need(len(data)==17 and all(len(row)==len(header)and all(math.isfinite(v)for v in row)for row in data),"complete finite actual frequency sweep")
  need(abs(data[0][0]-1e6)<1 and abs(data[-1][0]-1e10)<1,"full frequency endpoints")
  observations=[dict(case,points=[dict(frequency_Hz=row[0],real_impedance_ohm=row[1+2*i],imag_impedance_ohm=row[2+2*i])for row in data])for i,case in enumerate(cases)]
  save(label+"-readbacks.json",dict(instances=actual,models=readback,**FLAGS))
  save(label+"-measurements.json",dict(cases=observations,deck=pin(ac/"bench.cir"),native_measurements=pin(ac/"impedance.txt"),physical_gate_network_present=False,compact_model_overlap_resolved=False,**FLAGS))
  return observations
 canonical=[]
 for case in basecases:canonical.extend(sweep("canonical-"+case["label"],models,[case],False))
 save("canonical-ngcon2-measurements.json",dict(cases=canonical,one_instance_per_native_deck=True,**FLAGS))
 before_variant={str(p):pin(p)for p in variant.rglob("*")if p.is_file()}
 measured=[]
 for case in cases:measured.extend(sweep("explicit-"+case["label"],variant,[case],True))
 save("explicit-ngcon12-measurements.json",dict(cases=measured,one_instance_per_native_deck=True,**FLAGS))
 matches=[]
 for baseline in canonical:
  actual=next(row for row in measured if row["label"]==baseline["label"])
  for a,b in zip(actual["points"],baseline["points"]):
   need(a["frequency_Hz"]==b["frequency_Hz"],"canonical frequency identity")
   for key in("real_impedance_ohm","imag_impedance_ohm"):
    need(math.isclose(a[key],b[key],rel_tol=1e-9,abs_tol=1e-7),"explicit NGCON2 reproduces unchanged original model "+key)
  matches.append(baseline["label"])
 need(original_files=={str(p):pin(p)for p in models.rglob("*")if p.is_file()},"all original model files unchanged")
 need(before_variant=={str(p):pin(p)for p in variant.rglob("*")if p.is_file()},"explicit model variant unchanged during native runs")
 save("gate-contact-ac-comparison.json",dict(current_physical_run=41710162510,current_wire_run=41712243960,
  current_candidate=fixture["candidate"],actual_intrinsic_gates=200,one_ended=50,two_ended=150,
  original_ngcon2_reproduced_cases=matches,canonical_cases=canonical,contact_cases=measured,
  native_ngcon_readback_verified=True,one_instance_per_native_deck=True,complete_original_model_files_unchanged=True,
  equivalent_physical_gate_resistance_extracted=False,physical_gate_network_present=False,compact_model_overlap_resolved=False,**FLAGS))
 return len(geometries)


def main():
 ctx=gate()
 if sys.argv[1:]==["--publish"]:publish();return
 OUT.mkdir();NATIVE.mkdir();DERIVED.mkdir()
 try:
  cfg=read(ROOT/CFG)
  if sys.argv[1:]==["--controls"]:
   need(cfg["runtime"]["producer"]["run_id"]==39029337682,"exact frozen model runtime")
   data=read(ROOT/"docs/evidence/mos650-current-gate-model-cases.json")
   need(len(data["devices"])==200 and len({r["native_id"]for r in data["devices"]})==200,"all current native gates")
   need(cfg["current_wire"]["run"]==41712243960 and data["source_members"]==cfg["current_wire"]["selected"],"actual current source binding")
   save("source-controls.json",dict(context=ctx,source_files_verified=True,**FLAGS));return
  need(sys.argv[1:]==["--extract"],"explicit cloud characterization")
  current=NATIVE/"current-wire";current.mkdir()
  acquire(cfg["current_wire"],current,lambda n:n in cfg["current_wire"]["selected"])
  observed=current_cases(read(current/"derived/lvs_flat-identity.json"),read(current/"derived/gate-poly-access.json"))
  need(observed==read(ROOT/"docs/evidence/mos650-current-gate-model-cases.json")["devices"],"complete native current fixture readback")
  save("current-physical-cases.json",dict(devices=observed,source=cfg["current_wire"],**FLAGS))
  models=acquire_models(cfg["runtime"]);model_report(models)
  magic=NATIVE/"magic";magic.mkdir()
  acquire(cfg["magic"],magic,lambda n:n.startswith("wire-stage/magic-cloud/"))
  tech_report(magic/"wire-stage/magic-cloud/tech")
  count=characterize(models)
  gate();save("result.json",dict(status="MEASURED_CURRENT_GATE_CONTACT_COUNT_EFFECT_REQUIRES_PHYSICAL_NETWORK_COMPOSITION",context=ctx,
   unique_physical_dimensions=count,actual_mos_units=200,gate_resistance_qualified=False,**FLAGS))
 except BaseException as e:
  save("failure.json",dict(error_type=type(e).__name__,error=str(e),traceback=traceback.format_exc(),**FLAGS));raise
if __name__=="__main__":main()
