#!/usr/bin/env python3
"""Inspect exact compact-model gate controls and actual gate access geometry in cloud."""
import hashlib,json,os,re,subprocess,sys,tarfile,traceback,time,signal,math
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"paired650-gate-mesh";NATIVE=OUT/"native";DERIVED=OUT/"derived"
CFG="scripts/cdr-mos650-gate-ac-inputs.json";PINS="scripts/cdr-mos650-gate-ac-pins.json"
REPO="Melihakbulut221/nssoc";BRANCH="codex/cdr650-paired-gate-mesh"
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
 import klayout.db as db
 import importlib.metadata
 from collections import defaultdict,deque
 from fractions import Fraction
 current=NATIVE/"current-wire"
 access=read(current/"derived/gate-poly-access.json");anchors=read(current/"derived/terminal-anchors.json")
 gds=current/"native/selected/layout/nssoc_cdr_pd500_resistor_v59.gds"
 need(pin(gds)==dict(bytes=1627742,sha256="285760f3930a1cc142b45a3c43866202f1ea4694f468fb1603f286cb546cd514"),"exact current DRC/LVS-passing geometry")
 layout=db.Layout();layout.read(str(gds));top=layout.top_cell();need(top.name=="nssoc_cdr_pd500_resistor_v59"and layout.dbu==.001,"actual GDS coordinates")
 def layer(n):return db.Region(top.begin_shapes_rec(layout.layer(n,0))).merged()
 allpoly=layer(5);allcuts=layer(6);salblock=layer(28);psd=layer(14);metal=layer(8)
 def region(strings):
  out=db.Region()
  for text in strings:out.insert(db.Polygon.from_s(text.split(" props=")[0]))
  return out.merged()
 def exact_area(shape):
  value=shape.area()
  need(math.isfinite(value)and value==int(value)and abs(value)<2**53,"exact representable integer DBU squared area")
  return int(value)
 def same(a,b):return (a^b).is_empty()
 gates={g["device"]:g for g in access["gates"]}
 gate_anchors={a["label"]:a for a in anchors["anchors"]if "gate_contact"in a["detail"]}
 groups=access["groups"];need(len(gates)==200 and len(groups)==50 and len(gate_anchors)==200,"actual full gate/contact scope")
 physical=[]
 for i,group in enumerate(sorted(groups,key=lambda g:g["group"])):
  devices=sorted(group["devices"]);poly=region(group["access_poly_polygons"])
  need(poly.count()==1 and not list(poly.each())[0].holes(),"single simply connected actual gate poly")
  need((poly&salblock).is_empty()and(poly&psd).is_empty(),"nominal n-salicided gate material: no SalBlock/pSD intersection")
  terms={d:region(gates[d]["terminal_polygons"])for d in devices};contact={}
  for d,terminal in terms.items():
   need(gates[d]["gate_group"]==group["group"]and same(allpoly.interacting(terminal),poly),"current native intrinsic gate/poly material")
   need((terminal-poly).is_empty(),"full intrinsic electrode inside actual poly")
  for label in group["contact_anchors"]:
   a=gate_anchors[label];cut=region([a["detail"]["contact_polygon"]])
   need(a["detail"]["gate_group"]==group["group"]and a["native_cluster"]==group["native_cluster"],"same real contact ownership")
   need(cut.count()==1 and exact_area(cut)==160*160 and (cut-poly).is_empty()and(cut-metal).is_empty(),"real contact cut and M1 enclosure")
   center=cut.bbox().center();need(a["point_dbu"]==[center.x,center.y],"same actual metal anchor point")
   contact[label]=cut
  union=db.Region()
  for cut in contact.values():union+=cut
  need(same(allcuts.inside(poly),union),"all actual contacts included exactly")
  physical.append(dict(index=i,id=group["group"],poly=poly,terms=terms,contacts=contact))
 parameters=dict(sheet_ohm_per_square=7.0,contact_ohm_per_160nm_cut=15.0,sheet_range=[6.2,7.8],contact_range=[8,20],
  source="https://ihp-open-pdk-docs.readthedocs.io/en/latest/process_specs/02_process_control_params.html",
  scope="Nominal published salicided n-poly and M1/n-poly contact values; no narrow-gate calibration, temperature/corner qualification or full PEX claim.")
 save("physical-material-readback.json",dict(gds=pin(gds),klayout=importlib.metadata.version("klayout"),groups=50,intrinsic_gates=200,contacts=200,
  all_gate_poly_excludes_SalBlock_and_pSD=True,all_contacts_in_poly_and_M1=True,parameters=parameters,**FLAGS))
 engine=NATIVE/"models/source/runtime/patched-ngspice";engine.chmod(0o755)
 def refine(values,pitch):
  values=sorted(set(values));out=set(values)
  for a,b in zip(values,values[1:]):
   n=math.ceil((b-a)/pitch)
   for j in range(1,n):out.add(a+((b-a)*j)//n)
  return sorted(out)
 def grid(poly,regions,pitch,prefix):
  xs=[];ys=[]
  for r in [poly]+list(regions):
   for polygon in r.each():
    pts=list(polygon.each_point_hull())
    need(all(a.x==b.x or a.y==b.y for a,b in zip(pts,pts[1:]+pts[:1])),"orthogonal actual polygons")
    xs += [p.x for p in pts];ys += [p.y for p in pts]
  xs=refine(xs,pitch);ys=refine(ys,pitch);cells={};union=db.Region()
  for ix,(x0,x1)in enumerate(zip(xs,xs[1:])):
   for iy,(y0,y1)in enumerate(zip(ys,ys[1:])):
    box=db.Box(x0,y0,x1,y1);r=db.Region(box);overlap=r&poly
    if overlap.is_empty():continue
    need(same(overlap,r),"no partial finite-volume cell")
    name=f"{prefix}_{ix}_{iy}";cells[(ix,iy)]=dict(node=name,box=box,area=exact_area(box));union.insert(box)
  need(same(union,poly)and sum(c["area"]for c in cells.values())==exact_area(poly),"exact native poly material coverage without gaps or double counting")
  edges=[]
  for (ix,iy),c in cells.items():
   for dx,dy in ((1,0),(0,1)):
    other=cells.get((ix+dx,iy+dy))
    if other is None:continue
    a=c["box"];b=other["box"]
    if dx:distance=(a.width()+b.width())/2;face=a.height();need(a.right==b.left and a.bottom==b.bottom and a.top==b.top,"shared vertical face")
    else:distance=(a.height()+b.height())/2;face=a.width();need(a.top==b.bottom and a.left==b.left and a.right==b.right,"shared horizontal face")
    edges.append(dict(a=c["node"],b=other["node"],ohm=7.0*distance/face,kind="poly",squares=distance/face))
  return cells,edges
 def run_deck(label,deck,voltages,currents):
  folder=NATIVE/label;folder.mkdir();deck+=[".control","set num_threads=1","set numdgt=16","op"]
  for node in voltages:deck.append("print v("+node+")")
  for source in currents:deck.append("print i("+source+")")
  deck+=["quit",".endc",".end"];(folder/"bench.cir").write_text("\n".join(deck)+"\n");(folder/"spinit").write_text("set num_threads=1\n")
  os.environ["SPICE_SCRIPTS"]=str(folder);os.environ["OMP_NUM_THREADS"]="1"
  execute([engine,"-n","-b",folder/"bench.cir"],label,180)
  log=(NATIVE/(label+".stdout")).read_text()+(NATIVE/(label+".stderr")).read_text()
  bad=[s for s in log.splitlines()if re.search(r"error|warning|no such vector|not found|unknown parameter|singular matrix|timestep too small",s,re.I)]
  save(label+"-diagnostics.json",dict(lines=bad,**FLAGS));need(not bad,"native mesh diagnostics")
  def number(expr):
   found=re.findall(re.escape(expr)+r"\s*=\s*([0-9.eE+-]+)",log,re.I)
   need(len(found)==1 and math.isfinite(float(found[0])),"actual native mesh observation "+expr);return float(found[0])
  return dict(voltages={n:number("v("+n+")")for n in voltages},currents={n:number("i("+n+")")for n in currents},deck=pin(folder/"bench.cir"))
 summaries=[];pitches=(600,300,150,75)
 for pitch in pitches:
  # Independent native rectangular-sheet reference: exact analytic R=Rs*L/W.
  rectangle=db.Region(db.Box(0,0,10000,1000));cells,edges=grid(rectangle,[],pitch,"cal")
  deck=["* Analytic rectangular sheet check","VL left 0 DC 1","VR right 0 DC 0"]
  for i,e in enumerate(edges):deck.append(f"R{i} {e['a']} {e['b']} {e['ohm']:.17g}")
  ri=len(edges)
  for c in cells.values():
   box=c["box"]
   for side,coordinate in(("left",box.left),("right",box.right)):
    if coordinate!=(0 if side=="left"else 10000):continue
    deck.append(f"R{ri} {side} {c['node']} {7*box.width()/2/box.height():.17g}");ri+=1
  check=run_deck(f"analytic-{pitch}",deck,[],["vl","vr"])
  need(math.isclose(-check["currents"]["vl"],1/70,rel_tol=1e-9,abs_tol=1e-13)and math.isclose(check["currents"]["vr"],1/70,rel_tol=1e-9,abs_tol=1e-13),"native finite-volume rectangle matches exact70ohm")
  save(f"analytic-{pitch}.json",dict(pitch_nm=pitch,expected_ohm=70,actual=check,**FLAGS))
  all_edges=[];all_cells=[];coupling=[];contacts=[];group_rows=[]
  for p in physical:
   cells,edges=grid(p["poly"],list(p["terms"].values())+list(p["contacts"].values()),pitch,"pg"+str(p["index"]))
   bynode={c["node"]:c for c in cells.values()};adj=defaultdict(list)
   for e in edges:adj[e["a"]].append(e["b"]);adj[e["b"]].append(e["a"])
   seen=set();queue=deque([next(iter(bynode))])
   while queue:
    node=queue.popleft()
    if node in seen:continue
    seen.add(node);queue.extend(adj[node])
   need(seen==set(bynode),"every actual poly mesh cell is connected")
   for label,cut in p["contacts"].items():
    pieces=[];area=0
    for c in cells.values():
     overlap=db.Region(c["box"])&cut
     if overlap.is_empty():continue
     need(exact_area(overlap)==c["area"],"contact cut on exact mesh boundaries")
     area+=c["area"];ohm=15.0*exact_area(cut)/c["area"]
     edges.append(dict(a="gm_"+label.lower(),b=c["node"],ohm=ohm,kind="contact",contact=label,area_dbu2=c["area"]))
     pieces.append(dict(node=c["node"],area_dbu2=c["area"],ohm=ohm))
    need(area==exact_area(cut)and math.isclose(sum(1/x["ohm"]for x in pieces),1/15,rel_tol=1e-12),"whole real contact area and total conductance conserved")
    contacts.append(dict(label=label,node="gm_"+label.lower(),physical_anchor=gate_anchors[label],patches=pieces))
   for device,terminal in p["terms"].items():
    patches=[];total=exact_area(terminal)
    for c in cells.values():
     overlap=db.Region(c["box"])&terminal
     if overlap.is_empty():continue
     need(exact_area(overlap)==c["area"],"intrinsic electrode on exact mesh boundaries")
     patches.append(dict(node=c["node"],area_dbu2=c["area"],weight_numerator=c["area"],weight_denominator=total))
    need(sum(x["area_dbu2"]for x in patches)==total and sum(Fraction(x["weight_numerator"],x["weight_denominator"])for x in patches)==1,"full intrinsic gate area and exact total weight")
    coupling.append(dict(device=device,gate_group=p["id"],area_dbu2=total,patches=patches,nonuniform_intrinsic_composition_qualified=False))
   all_edges+=edges;all_cells += [dict(node=c["node"],bbox_dbu=[c["box"].left,c["box"].bottom,c["box"].right,c["box"].top],area_dbu2=c["area"])for c in cells.values()]
   group_rows.append(dict(group=p["id"],cells=len(cells),edges=len(edges),poly_area_dbu2=exact_area(p["poly"]),contacts=len(p["contacts"]),gates=len(p["terms"])))
  need(len(contacts)==200 and len({c["label"]for c in contacts})==200 and len(coupling)==200 and len({c["device"]for c in coupling})==200,"all current contacts and intrinsic gates")
  need(all(math.isfinite(e["ohm"])and e["ohm"]>0 and e["a"]!=e["b"]for e in all_edges),"positive finite physical mesh resistors")
  native=NATIVE/f"mesh-{pitch}";native.mkdir()
  fragment=["* Actual current650 gate poly/contact resistor mesh; nominal material values only"]
  for i,e in enumerate(all_edges):fragment.append(f"Rgp{i} {e['a']} {e['b']} {e['ohm']:.17g}")
  (native/"gate-poly-resistors.cir").write_text("\n".join(fragment)+"\n")
  (native/"mesh.json").write_bytes(enc(dict(cells=all_cells,edges=all_edges,groups=group_rows,contacts=contacts,coupling=coupling,parameters=parameters,**FLAGS)))
  deck=["* Actual physical gate mesh: uniform1nA per intrinsic gate, all M1 contact ports held at0V",f'.include "{native}/gate-poly-resistors.cir"']
  sources=[]
  for c in contacts:
   src="vp_"+c["label"].lower();sources.append(src);deck.append(src+" "+c["node"]+" 0 DC 0")
  # Actual SPICE voltage source identifiers must begin with V.
  voltages=[];weights=[]
  for c in coupling:
   avg="avg_"+str(c["device"]);voltages.append(avg);terms=[]
   for j,p in enumerate(c["patches"]):
    weight=p["weight_numerator"]/p["weight_denominator"]
    deck.append(f"Iinj{c['device']}_{j} 0 {p['node']} {1e-9*weight:.17g}")
    terms.append(f"{weight:.17g}*v({p['node']})")
   deck.append("Bavg"+str(c["device"])+" "+avg+" 0 v={")
   for offset in range(0,len(terms),8):deck.append("+ "+("+"if offset else"")+"+".join(terms[offset:offset+8]))
   deck.append("+ }")
   weights.append(dict(device=c["device"],patch_count=len(c["patches"]),area_dbu2=c["area_dbu2"]))
  observed=run_deck(f"native-mesh-{pitch}",deck,voltages,sources)
  need(all(v>0 for v in observed["voltages"].values()),"every actual intrinsic gate receives a finite positive resistive potential")
  need(all(v>=-1e-16 for v in observed["currents"].values())and math.isclose(sum(observed["currents"].values()),200e-9,rel_tol=1e-8,abs_tol=1e-15),"all injected gate current returns through actual metal contacts")
  record=dict(pitch_nm=pitch,cells=len(all_cells),poly_resistors=sum(e["kind"]=="poly"for e in all_edges),
   contact_resistors=sum(e["kind"]=="contact"for e in all_edges),groups=group_rows,gate_quadrature=weights,
   physical_contacts=200,intrinsic_gates=200,actual_uniform_injection_observation=observed,
   native_resistor_fragment=pin(native/"gate-poly-resistors.cir"),native_complete_mesh=pin(native/"mesh.json"),
   metal_contact_ports_held_zero_only_in_diagnostic=True,uniform_gate_injection_A=1e-9,actual_intrinsic_devices_present=False,
   physical_gate_resistance_network_generated=True,material_values_qualified_for_signoff=False,**FLAGS)
  save(f"gate-poly-mesh-{pitch}.json",record);summaries.append(record)
 changes=[]
 for coarse,fine in zip(summaries,summaries[1:]):
  a=coarse["actual_uniform_injection_observation"]["voltages"];b=fine["actual_uniform_injection_observation"]["voltages"];need(set(a)==set(b),"same actual200 intrinsic gate averages")
  changes.append(dict(coarse_pitch_nm=coarse["pitch_nm"],fine_pitch_nm=fine["pitch_nm"],max_relative_gate_average_change=max(abs(a[k]-b[k])/abs(b[k])for k in a)))
 need(pin(gds)==dict(bytes=1627742,sha256="285760f3930a1cc142b45a3c43866202f1ea4694f468fb1603f286cb546cd514"),"actual geometry unchanged")
 save("physical-gate-resistance-network.json",dict(pitches_nm=list(pitches),gate_groups=50,intrinsic_gates=200,physical_contacts=200,
  native_rectangle_references_passed=len(pitches),native_actual_mesh_DC_runs_passed=len(pitches),refinement_observations=changes,
  material_parameters=parameters,physical_gate_resistance_network_generated=True,full_metal_network_integrated=False,
  actual_intrinsic_devices_present=False,nonuniform_gate_convergence_qualified=False,material_values_qualified_for_signoff=False,**FLAGS))
 return 4


def paired_current(dest):
 import zipfile
 def artifact(aid,digest,run,head,name):
  r=api('actions/runs/'+str(run));need(r['status']=='completed' and r['conclusion']=='success' and r['head_sha']==head,'qualified paired producer')
  meta=api('actions/artifacts/'+str(aid));need(meta['workflow_run']['id']==run and meta['workflow_run']['head_sha']==head and meta['digest']=='sha256:'+digest and not meta['expired'],'paired artifact identity')
  path=NATIVE/name
  with path.open('xb')as out:subprocess.run(['gh','api','repos/'+REPO+'/actions/artifacts/'+str(aid)+'/zip'],stdout=out,check=True)
  need(pin(path)['sha256']==digest,'paired archive content')
  return zipfile.ZipFile(path)
 geometry=artifact(14124521775,'84bbb918af34605e7c6f14598fc68e7d5bb811a3d32d6c22bb294c0a51623ac6',43621748603,'0d90e18e09678eb1733123d97f41942dace720b3','paired-geometry.zip')
 anchors=artifact(14124672969,'a3e3b980b8d03f8ef38d854b414649a40496711d532f4824957184fc9082c199',43623472892,'54a4766e9256d2cd0a3f93f5441ca5d1c238c7ce','paired-anchors.zip')
 identity=artifact(14125295448,'d8376d4009da54acbe52569fd119add9f07f4f13d8120ebc65bd5fa193c899ac',43622884786,'e0a87989915cb7d65a20176de33649859f013393','paired-identity.zip')
 rows={'native/selected/layout/nssoc_cdr_pd500_resistor_v59.gds':geometry.read('candidate.gds'),
       'derived/gate-poly-access.json':anchors.read('gate-poly-access.json'),
       'derived/terminal-anchors.json':anchors.read('terminal-anchors.json'),
       'derived/lvs_flat-identity.json':identity.read('lvs_flat-identity.json')}
 for name,raw in rows.items():
  path=dest/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
 save('paired-current-acquisition.json',dict(files={n:pin(dest/n)for n in rows},geometry_run=43621748603,anchors_run=43623472892,identity_run=43622884786,**FLAGS))
 return {n:pin(dest/n)for n in rows}

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
  paired_source=paired_current(current)
  observed=current_cases(read(current/"derived/lvs_flat-identity.json"),read(current/"derived/gate-poly-access.json"))
  need(len(observed)==200,"complete new native current fixture readback")
  save("current-physical-cases.json",dict(devices=observed,source=paired_source,**FLAGS))
  models=acquire_models(cfg["runtime"]);model_report(models)
  magic=NATIVE/"magic";magic.mkdir()
  acquire(cfg["magic"],magic,lambda n:n.startswith("wire-stage/magic-cloud/"))
  tech_report(magic/"wire-stage/magic-cloud/tech")
  count=characterize(models)
  gate();save("result.json",dict(status="BUILT_ACTUAL_GATE_POLY_R_NETWORK_REQUIRES_INTRINSIC_AND_FULL_METAL_COMPOSITION",context=ctx,
   unique_physical_dimensions=count,actual_mos_units=200,gate_resistance_qualified=False,**FLAGS))
 except BaseException as e:
  save("failure.json",dict(error_type=type(e).__name__,error=str(e),traceback=traceback.format_exc(),**FLAGS));raise
if __name__=="__main__":main()
