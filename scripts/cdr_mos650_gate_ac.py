#!/usr/bin/env python3
"""Inspect exact compact-model gate controls and actual gate access geometry in cloud."""
import hashlib,json,os,re,subprocess,sys,tarfile,traceback,time,signal,math
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"mos650-gate-ac";NATIVE=OUT/"native";DERIVED=OUT/"derived"
CFG="scripts/cdr-mos650-gate-ac-inputs.json";PINS="scripts/cdr-mos650-gate-ac-pins.json"
REPO="Melihakbulut221/nssoc";BRANCH="codex/cdr-mos650-gate-port-reduction"
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
 os.environ["OPENBLAS_NUM_THREADS"]="1";os.environ["OMP_NUM_THREADS"]="1"
 import numpy as np
 import scipy
 from scipy.sparse import coo_matrix
 from scipy.sparse.linalg import splu
 from fractions import Fraction
 from collections import defaultdict
 cfg=read(ROOT/CFG);meshdir=NATIVE/"mesh-producer";meshdir.mkdir()
 acquire(cfg["mesh"],meshdir,lambda n:n in cfg["mesh"]["selected"])
 mesh=read(meshdir/"native/mesh-75/mesh.json")
 fixture=read(ROOT/"docs/evidence/mos650-current-gate-model-cases.json")
 units={u["native_id"]:u for u in fixture["devices"]}
 need(len(units)==200 and len(mesh["groups"])==50 and len(mesh["contacts"])==200 and len(mesh["coupling"])==200,"complete current physical field scope")
 source_mesh=pin(meshdir/"native/mesh-75/mesh.json")
 physical_fragment=meshdir/"native/mesh-75/gate-poly-resistors.cir"
 raw_branches=[line.split()for line in physical_fragment.read_text().splitlines()if line.strip()and not line.lstrip().startswith("*")]
 need(len(raw_branches)==len(mesh["edges"]),"complete native resistor fragment census")
 for i,(row,edge)in enumerate(zip(raw_branches,mesh["edges"])):
  need(len(row)==4 and row[0]=="Rgp"+str(i)and row[1:3]==[edge["a"],edge["b"]]and float(row[3])==edge["ohm"],"every original native resistor endpoint and value matches")
 save("native-field-fragment-binding.json",dict(source_mesh=source_mesh,source_fragment=pin(physical_fragment),branches=len(raw_branches),exact_order_endpoints_and_values=True,**FLAGS))
 dep=Path("/tmp/nssoc-gate-reduce-packages.json")
 need(dep.is_file()and np.__version__=="2.3.3"and scipy.__version__=="1.16.2","exact numerical dependency versions")
 save("numeric-dependencies.json",dict(numpy=np.__version__,scipy=scipy.__version__,installation=read(dep),**FLAGS))
 engine=NATIVE/"models/source/runtime/patched-ngspice";engine.chmod(0o755)
 tolerances=dict(dc_relative=1e-7,dc_absolute_V=1e-12,ac_relative=1e-7,ac_absolute_ohm=1e-8,noise_relative=2e-6,noise_absolute_V2_Hz=1e-28,
  solve_residual=1e-9,reciprocity_relative=1e-10,factor_relative=1e-10,positive_eigen_relative=1e-12,power_relative=1e-7,power_absolute_W=1e-18)
 save("predeclared-port-tolerances.json",dict(tolerances=tolerances,scope="Numerical equivalence of nominal linear R-network ports; not physical material or full PHY qualification.",**FLAGS))
 def expr(lines,head,terms):
  need(bool(terms),"nonempty weighted voltage")
  lines.append(head+"{")
  for k in range(0,len(terms),8):lines.append("+ "+("+"if k else"")+"+".join(terms[k:k+8]))
  lines.append("+ }")
 def table(path,columns,rows):
  lines=path.read_text().splitlines();header=lines[0].split()
  need(header[1:]==columns,"exact native response columns "+str(path))
  result=[[float(v)for v in line.split()]for line in lines[1:]]
  need(len(result)==rows and all(len(r)==len(columns)+1 and all(math.isfinite(v)for v in r)for r in result),"complete finite native response "+str(path))
  return result
 def run(label,lines):
  folder=NATIVE/label;folder.mkdir();(folder/"bench.cir").write_text("\n".join(lines)+"\n");(folder/"spinit").write_text("set num_threads=1\n")
  os.environ["SPICE_SCRIPTS"]=str(folder);execute([engine,"-n","-b",folder/"bench.cir"],label,180)
  log=(NATIVE/(label+".stdout")).read_text()+(NATIVE/(label+".stderr")).read_text()
  bad=[line for line in log.splitlines()if re.search(r"error|warning|no such vector|not found|unknown parameter|singular matrix|timestep too small",line,re.I)]
  save(label+"-diagnostics.json",dict(lines=bad,**FLAGS));need(not bad,"native port diagnostics "+label)
  return folder
 # Preserve the frozen engine's measured Johnson-noise prefactor, including any legacy Boltzmann constant.
 calpath=NATIVE/"noise-calibration";cal_lines=["* Native thermal-noise unit reference",".temp 27","Rcal p 0 70","Ical 0 p DC 0 AC 1",".control",
  "set num_threads=1","set numdgt=16","set wr_singlescale","set wr_vecnames","set sqrnoise","noise v(p) Ical lin 2 1meg 2meg","setplot noise1",
  f"wrdata {calpath}/noise.txt onoise_spectrum","quit",".endc",".end"]
 cal=run("noise-calibration",cal_lines);noise=table(cal/"noise.txt",["onoise_spectrum"],2)
 need([r[0]for r in noise]==[1e6,2e6]and noise[0][1]>0 and math.isclose(noise[0][1],noise[1][1],rel_tol=1e-12),"native white resistor-noise spectrum")
 thermal=noise[0][1]/70;boltzmann=thermal/(4*300.15)
 need(math.isclose(boltzmann,1.380649e-23,rel_tol=5e-5),"native thermal prefactor near SI; no arbitrary calibration")
 save("native-thermal-reference.json",dict(temperature_C=27,temperature_K=300.15,resistor_ohm=70,output_PSD_V2_Hz=noise,thermal_factor=thermal,effective_Boltzmann_J_K=boltzmann,
  legacy_constant_relative_budget=5e-5,**FLAGS))
 group_index={g["group"]:i for i,g in enumerate(mesh["groups"])}
 cells={c["node"]:c for c in mesh["cells"]};owners={node:int(node.split("_")[0][2:])for node in cells}
 contacts_by_group=defaultdict(list);coupling_by_group=defaultdict(list);edges_by_group=defaultdict(list)
 for c in mesh["contacts"]:
  gi=group_index[c["physical_anchor"]["detail"]["gate_group"]];owners[c["node"]]=gi;contacts_by_group[gi].append(c)
 for c in mesh["coupling"]:
  gi=group_index[c["gate_group"]];need(units[c["device"]]["gate_group"]==c["gate_group"],"same actual native gate owner")
  need(sum(p["area_dbu2"]for p in c["patches"])==c["area_dbu2"],"complete actual electrode area")
  coupling_by_group[gi].append(c)
 for e in mesh["edges"]:
  need(e["a"]in owners and e["b"]in owners and owners[e["a"]]==owners[e["b"]]and e["ohm"]>0,"actual same-group positive branch")
  edges_by_group[owners[e["a"]]].append(e)
 need(len(cells)==131310 and len(mesh["edges"])==238068,"exact75nm field census")
 def project(c,n):
  bbox=units[c["device"]]["terminal_bbox_dbu"];x0,y0,x1,y1=bbox
  need((x1-x0)*(y1-y0)==c["area_dbu2"],"exact current rectangular intrinsic electrode")
  ports=[]
  for stripe in range(n):
   lo=Fraction(y0)+Fraction((y1-y0)*stripe,n);hi=Fraction(y0)+Fraction((y1-y0)*(stripe+1),n)
   area=(x1-x0)*(hi-lo);weights=[]
   for p in c["patches"]:
    box=cells[p["node"]]["bbox_dbu"]
    need(x0<=box[0]<box[2]<=x1 and y0<=box[1]<box[3]<=y1,"actual electrode field cell bounds")
    height=max(Fraction(0),min(hi,box[3])-max(lo,box[1]))
    if not height:continue
    weight=Fraction(box[2]-box[0])*height/area
    weights.append(dict(node=p["node"],numerator=weight.numerator,denominator=weight.denominator))
   need(sum(Fraction(w["numerator"],w["denominator"])for w in weights)==1,"exact nonnegative complete stripe weights")
   ports.append(dict(kind="projected_gate",device=c["device"],stripe=stripe,copies=n,intrinsic_multiplicity=dict(numerator=1,denominator=n),
    y_bounds_dbu=[[lo.numerator,lo.denominator],[hi.numerator,hi.denominator]],weights=weights))
  return ports
 def positive_fragment(gi,n,ports,A,quiet=False,wrong_resistance=False):
  count=len(ports);lines=[f".subckt gp_g{gi}_n{n} ref "+" ".join("p"+str(i)for i in range(count))]
  r0=2 if wrong_resistance else 1
  for k,row in enumerate(A):
   terms=[f"({value:.17g})*v(p{i},ref)"for i,value in enumerate(row)if value!=0]
   expr(lines,f"Bt{k} b{k} ref v=",terms);lines.append(f"Vs{k} b{k} r{k} 0")
   lines.append(f"Gquiet{k} r{k} ref r{k} ref 1"if quiet else f"Rthermal{k} r{k} ref {r0}")
   for i,value in enumerate(row):
    if value!=0:lines.append(f"Fr{k}_{i} p{i} ref Vs{k} {value:.17g}")
  lines.append(".ends");return lines,r0
 def original_fragment(gi,n,ports,reference,edges):
  count=len(ports);mapping={reference:"ref"}
  for i,p in enumerate(ports):
   if p["kind"]=="metal_contact":mapping[p["node"]]="p"+str(i)
  lines=[f".subckt gp_g{gi}_n{n} ref "+" ".join("p"+str(i)for i in range(count))]
  for i,e in enumerate(edges):lines.append(f"Rsheet{i} {mapping.get(e['a'],e['a'])} {mapping.get(e['b'],e['b'])} {e['ohm']:.17g}")
  for i,p in enumerate(ports):
   if p["kind"]!="projected_gate":continue
   lines.append(f"Vproj{i} p{i} bproj{i} 0")
   terms=[]
   for j,w in enumerate(p["weights"]):
    alpha=w["numerator"]/w["denominator"];node=mapping.get(w["node"],w["node"])
    terms.append(f"({alpha:.17g})*v({node},ref)")
    lines.append(f"Fproj{i}_{j} ref {node} Vproj{i} {alpha:.17g}")
   expr(lines,f"Bproj{i} bproj{i} ref v=",terms)
  lines.append(".ends");return lines
 def probes_for(ports):
  count=len(ports);first_gate=next(i for i,p in enumerate(ports)if p["kind"]=="projected_gate")
  result=[]
  for i in sorted({0,first_gate,count-1}):result.append((i,None))
  for pair in((0,first_gate),(first_gate,count-1)):
   if pair[0]!=pair[1]and pair not in result:result.append(pair)
  return result
 def native_response(label,fragment,gi,n,ports,noise_probes,Z,r0=None):
  count=len(ports);folder=NATIVE/label
  path=NATIVE/(label+"-network.cir");path.write_text("\n".join(fragment)+"\n")
  currents=[((-1)**i)*1e-6/(i+1)for i in range(count)]
  lines=["* Actual poly/contact field port equivalence, no nonlinear intrinsic devices",".temp 27",f'.include "{path}"',"Vref ref 0 DC 0",
   "Xnet ref "+" ".join("p"+str(i)for i in range(count))+f" gp_g{gi}_n{n}"]
  for i,current in enumerate(currents):lines.append(f"Ip{i} ref p{i} DC {current:.17g} AC {int(i==0)}")
  lines += [".control","set num_threads=1","set numdgt=16","set wr_singlescale","set wr_vecnames","set sqrnoise","op"]
  dc_columns=[]
  for i in range(count):lines.append(f"let d{i}=v(p{i})");dc_columns.append("d"+str(i))
  # The reduced positive resistors are internal to Xnet; native voltages prove branch power.
  if r0 is not None:
   for k in range(count):lines.append(f"let t{k}=v(xnet.r{k})-v(ref)");dc_columns.append("t"+str(k))
  lines.append(f"wrdata {folder}/dc.txt "+" ".join(dc_columns));lines.append("ac dec 1 1meg 10g")
  ac_columns=[]
  for i in range(count):
   lines += [f"let a{i}=real(v(p{i}))",f"let b{i}=imag(v(p{i}))"];ac_columns += ["a"+str(i),"b"+str(i)]
  lines.append(f"wrdata {folder}/ac.txt "+" ".join(ac_columns))
  previous_noise_drive=0
  for j,(a,b)in enumerate(noise_probes):
   output=f"v(p{a})"if b is None else f"v(p{a},p{b})"
   drive=a if b is None or abs(Z[a,a]-Z[b,a])>=abs(Z[a,b]-Z[b,b]) else b
   gain=float(Z[a,drive]if b is None else Z[a,drive]-Z[b,drive]);need(abs(gain)>1e-12,"nonzero physical noise input reference gain")
   lines += [f"alter Ip{previous_noise_drive} acmag = 0",f"alter Ip{drive} acmag = 1",
    f"noise {output} Ip{drive} lin 2 1meg 2meg",f"setplot noise{2*j+1}",f"wrdata {folder}/noise-{j}.txt onoise_spectrum"]
   previous_noise_drive=drive
  lines += ["quit",".endc",".end"];run(label,lines)
  dc=table(folder/"dc.txt",dc_columns,1)[0][1:];ac=table(folder/"ac.txt",ac_columns,5)
  need([r[0]for r in ac]==[1e6,1e7,1e8,1e9,1e10]or all(math.isclose(r[0],10**(6+i),rel_tol=1e-12)for i,r in enumerate(ac)),"all native AC endpoints")
  spectra=[]
  for j,(a,b)in enumerate(noise_probes):
   values=table(folder/f"noise-{j}.txt",["onoise_spectrum"],2);need([r[0]for r in values]==[1e6,2e6]and all(r[1]>=0 for r in values),"native nonnegative power spectra")
   factor=float(Z[a,a]if b is None else Z[a,a]+Z[b,b]-2*Z[a,b]);need(factor>0,"positive physical noise quadratic form")
   spectra.append(dict(ports=[a,b],measured=values,expected_PSD_V2_Hz=thermal*factor))
  predicted=Z@np.array(currents);failures=[];maxima=dict(dc=0.0,ac=0.0,noise=0.0,power=0.0)
  def compare(kind,observed,expected,relative,absolute,where):
   error=abs(observed-expected);budget=absolute+relative*abs(expected);ratio=float(error/budget);maxima[kind]=max(maxima[kind],ratio)
   if error>budget:failures.append(dict(kind=kind,where=where,error=float(error),budget=float(budget),ratio=ratio))
  for i,(a,b)in enumerate(zip(dc[:count],predicted)):compare("dc",a,b,tolerances["dc_relative"],tolerances["dc_absolute_V"],i)
  for row in ac:
   for i in range(count):compare("ac",complex(row[1+2*i],row[2+2*i]),Z[i,0],tolerances["ac_relative"],tolerances["ac_absolute_ohm"],[row[0],i])
  for item in spectra:
   for freq,value in item["measured"]:compare("noise",value,item["expected_PSD_V2_Hz"],tolerances["noise_relative"],tolerances["noise_absolute_V2_Hz"],[item["ports"],freq])
  power=None
  if r0 is not None:
   input_power=sum(i*v for i,v in zip(currents,dc[:count]));branch_power=sum(v*v/r0 for v in dc[count:])
   compare("power",branch_power,input_power,tolerances["power_relative"],tolerances["power_absolute_W"],"source vs positive resistor branches")
   power=dict(input_W=input_power,branch_W=branch_power)
  result=dict(group=gi,copies=n,ports=count,dc_currents_A=currents,dc_voltages_V=dc[:count],AC=ac,noise=spectra,power=power,
   budget_fractions=maxima,failures=failures,fragment=pin(path),deck=pin(folder/"bench.cir"),full_nonlinear_circuit_integrated=False,**FLAGS)
  save(label+"-measurements.json",result);return result
 summaries=[];fault_results=[];native_runs=1
 for gi,group in enumerate(mesh["groups"]):
  contacts=sorted(contacts_by_group[gi],key=lambda c:c["label"]);reference=contacts[0]["node"];edges=edges_by_group[gi]
  nodes=sorted({e[k]for e in edges for k in("a","b")}-{reference});node_index={n:i for i,n in enumerate(nodes)}
  rr=[];cc=[];vv=[]
  for e in edges:
   g=1/e["ohm"];a=node_index.get(e["a"]);b=node_index.get(e["b"])
   for i in(a,b):
    if i is not None:rr.append(i);cc.append(i);vv.append(g)
   if a is not None and b is not None:rr += [a,b];cc += [b,a];vv += [-g,-g]
  L=coo_matrix((vv,(rr,cc)),shape=(len(nodes),len(nodes))).tocsc();L.sum_duplicates()
  need((L-L.T).nnz==0 and np.all(L.diagonal()>0),"exact symmetric physical conductance stamp")
  lu=splu(L);group_records=[]
  for n in(1,2,4,8,16):
   ports=[dict(kind="metal_contact",label=c["label"],node=c["node"],physical_anchor=c["physical_anchor"])for c in contacts[1:]]
   for c in sorted(coupling_by_group[gi],key=lambda c:c["device"]):ports+=project(c,n)
   count=len(ports);T=np.zeros((len(nodes),count))
   for j,p in enumerate(ports):
    if p["kind"]=="metal_contact":T[node_index[p["node"]],j]=1
    else:
     for w in p["weights"]:T[node_index[w["node"]],j]+=w["numerator"]/w["denominator"]
   need(np.all(T>=0)and np.allclose(T.sum(axis=0),1,rtol=0,atol=1e-13),"complete positive power-dual injection and observation columns")
   U=lu.solve(T);residual=float(np.max(np.abs(L@U-T)));need(residual<tolerances["solve_residual"],"actual field linear solve residual")
   Z=T.T@U;scale=float(np.max(np.abs(Z)));symmetry=float(np.max(np.abs(Z-Z.T))/scale)
   need(symmetry<tolerances["reciprocity_relative"],"actual field reciprocal port impedance")
   # Averaging only roundoff after the measured reciprocity check, never eigenvalue clipping.
   Z=(Z+Z.T)/2;eigen=np.linalg.eigvalsh(Z)
   need(eigen[0]>eigen[-1]*tolerances["positive_eigen_relative"],"strict positive physical port resistance")
   Y=np.linalg.solve(Z,np.eye(count));y_symmetry=float(np.max(np.abs(Y-Y.T))/np.max(np.abs(Y)))
   need(y_symmetry<tolerances["reciprocity_relative"],"reciprocal port admittance");Y=(Y+Y.T)/2
   A=np.linalg.cholesky(Y).T;factor_error=float(np.max(np.abs(A.T@A-Y))/np.max(np.abs(Y)))
   need(factor_error<tolerances["factor_relative"],"positive resistor transformer factorization")
   directory=NATIVE/f"reduction-g{gi}-n{n}";directory.mkdir()
   data=dict(group=group["group"],group_index=gi,copies=n,actual_reference_contact=contacts[0],ports=ports,
    source_mesh=source_mesh,source_cells=len(nodes)+1,source_resistors=len(edges),solve_residual=residual,
    reciprocity_relative=symmetry,admittance_reciprocity_relative=y_symmetry,
    eigenvalue_min_ohm=float(eigen[0]),eigenvalue_max_ohm=float(eigen[-1]),factor_relative=factor_error,
    resistance_matrix_ohm=Z.tolist(),admittance_matrix_S=Y.tolist(),transformer_A=A.tolist(),reference_resistor_ohm=1,
    reference_contact_is_not_global_ground=True,thermal_noise_preserving_realization_required=True,**FLAGS)
   (directory/"ports-and-matrices.json").write_bytes(enc(data))
   full=original_fragment(gi,n,ports,reference,edges);reduced,r0=positive_fragment(gi,n,ports,A)
   (directory/"full-field-projected.cir").write_text("\n".join(full)+"\n")
   (directory/"reduced-positive-resistors.cir").write_text("\n".join(reduced)+"\n")
   probes=probes_for(ports)
   original=native_response(f"full-g{gi}-n{n}",full,gi,n,ports,probes,Z)
   compact=native_response(f"reduced-g{gi}-n{n}",reduced,gi,n,ports,probes,Z,r0);native_runs+=2
   need(not original["failures"]and not compact["failures"],"native original/projected reduction DC AC power or noise mismatch")
   record=dict(group=gi,copies=n,port_count=count,source_cells=len(nodes)+1,source_resistors=len(edges),
    solve_residual=residual,reciprocity_relative=symmetry,factor_relative=factor_error,
    native_original=original["budget_fractions"],native_reduced=compact["budget_fractions"],
    matrices=pin(directory/"ports-and-matrices.json"),full_field=pin(directory/"full-field-projected.cir"),reduced=pin(directory/"reduced-positive-resistors.cir"))
   group_records.append(record);summaries.append(record)
   if not fault_results and n==4 and count>=3:
    quiet,_=positive_fragment(gi,n,ports,A,quiet=True)
    quiet_result=native_response(f"fault-noiseless-g{gi}-n{n}",quiet,gi,n,ports,probes,Z,1)
    need(quiet_result["failures"]and {x["kind"]for x in quiet_result["failures"]}=={"noise"},"native noiseless substitution must pass deterministic checks and fail noise")
    wrong,wrong_r0=positive_fragment(gi,n,ports,A,wrong_resistance=True)
    wrong_result=native_response(f"fault-resistance-g{gi}-n{n}",wrong,gi,n,ports,probes,Z,wrong_r0)
    need({"dc","ac","noise"}<={x["kind"]for x in wrong_result["failures"]},"native wrong physical resistor must be rejected")
    fault_results=[dict(name="noiseless conductance substitution",rejected=True,failures=quiet_result["failures"]),dict(name="doubled reference resistance",rejected=True,failures=wrong_result["failures"])]
    native_runs+=2
    save("native-reduction-fault-controls.json",dict(cases=fault_results,**FLAGS))
  save(f"completed-group-{gi:02}.json",dict(group=group["group"],records=group_records,**FLAGS))
  print("COMPLETED_ACTUAL_GATE_GROUP",gi,len(group_records),flush=True)
 need(len(summaries)==250 and len(fault_results)==2 and native_runs==503,"all actual groups and partition bases, no reduced scope")
 save("physical-gate-port-reduction.json",dict(actual_groups=50,actual_intrinsic_gates=200,actual_contacts=200,
  partition_counts=[1,2,4,8,16],port_networks=250,native_simulator_executions=native_runs,native_fault_controls=2,
  source_mesh=source_mesh,thermal_reference_factor=thermal,tolerances=tolerances,groups=summaries,
  exact_current_physical_contact_bindings=True,reference_contact_is_not_global_ground=True,
  nominal_R_network_port_reduction_qualified=True,full_nonlinear_circuit_integrated=False,full_metal_network_integrated=False,
  extrinsic_poly_C_included=False,material_corner_temperature_qualified=False,**FLAGS))
 return 4


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
  gate();save("result.json",dict(status="PASS_NOMINAL_PHYSICAL_GATE_PORT_REDUCTION_REQUIRES_FULL_NONLINEAR_AND_METAL_INTEGRATION",context=ctx,
   unique_physical_dimensions=count,actual_mos_units=200,gate_resistance_qualified=False,**FLAGS))
 except BaseException as e:
  save("failure.json",dict(error_type=type(e).__name__,error=str(e),traceback=traceback.format_exc(),**FLAGS));raise
if __name__=="__main__":main()
