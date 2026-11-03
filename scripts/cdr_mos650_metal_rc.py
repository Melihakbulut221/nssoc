#!/usr/bin/env python3
"""Fresh distributed metal/via RC on the complete physically bound650-device view."""
import ast,hashlib,io,json,os,shutil,signal,subprocess,sys,tarfile,time,tokenize,traceback
from collections import Counter
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"mos650-metal-rc";NATIVE=OUT/"native";DERIVED=OUT/"derived"
CFG="scripts/cdr-mos650-metal-rc-inputs.json";PINS="scripts/cdr-mos650-metal-rc-pins.json"
METHODS="docs/evidence/mos650-metal-rc-original-methods.json"
REPO="Melihakbulut221/nssoc";BRANCH="codex/cdr-mos650-gate-metal-rc"
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
def methods():
 source=read(ROOT/METHODS);outputs={};changes={}
 for name,meta in source["methods"].items():
  text=meta["text"];need(hashlib.sha256(text.encode()).hexdigest()==meta["sha256"],"frozen complete numerical method")
  original=text;edits=[]
  def replace(before,after):
   nonlocal text
   need(text.count(before)==1,"unique numerical method adaptation "+name+" "+before)
   text=text.replace(before,after);edits.append(dict(before=before,after=after))
  if name=="run-rc01.py":
   replace("Path('/dev/shm/nssoc-magic-area-product-v4-build/runtime/lib')","B.parent/'magic-cloud/runtime/lib'")
   replace("Path('/dev/shm/nssoc-magic-pad-stack-tech-v1')","B.parent/'magic-cloud/tech'")
   replace("(2*1024**3,)*2","(4*1024**3,)*2")
   replace("size>80*1024**2","size>1024*1024**2");replace("OWNED_SCRATCH_80MIB_LIMIT","OWNED_SCRATCH_1024MIB_LIMIT")
   # Keep numerical Tcl unchanged, but place the direct Magic child in the
   # outer owned session so timeout/exception cleanup also reaches native work.
   replace("start_new_session=True","start_new_session=False")
   replace("os.killpg(p.pid,signal.SIGTERM)","os.kill(p.pid,signal.SIGTERM)")
   replace("os.killpg(p.pid,signal.SIGKILL)","os.kill(p.pid,signal.SIGKILL)")
  elif name=="audit-rc48.py":
   replace("original_devices=54","original_devices=650")
   mapping={"12":"25","17":"113","18":"114","112":"1428","154":"2046","54":"643","100":"1403"}
   changed=Counter();tokens=[]
   for t in tokenize.generate_tokens(io.StringIO(text).readline):
    if t.type==tokenize.NUMBER and t.string in mapping:
     changed[t.string]+=1;t=t._replace(string=mapping[t.string])
    tokens.append(t)
   need(set(changed)==set(mapping),"all explicit native650 census adaptations")
   text=tokenize.untokenize(tokens);edits.append(dict(numeric_census_tokens=dict(changed),mapping=mapping))
   replace("==['18']","==['114']");replace("==['17']","==['113']")
   replace("dict(ACTUAL_TERMINAL_METAL_POINT_REFERENCE=1403,RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE=643)",
    "dict(ACTUAL_TERMINAL_METAL_POINT_REFERENCE=1203,RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE=643,RETAINED_INTRINSIC_GATE_REQUIRES_POLY_RC=200)")
   replace("metal_device_terminals=1403,", "metal_device_terminals=1203,physical_gate_contact_probes=200,unmodeled_intrinsic_gate_terminals=200,")
   replace(" for r in native_rows:", " require(anchors['gate_groups']==frozen['gate_groups'] and anchors['intrinsic_gate_metal_shortcuts']is False,'Actual distributed gate groups changed')\n require(anchors['physical_gate_contact_count']==200,'Physical gate contact census changed')\n gate_probes=[v for v in anchors['anchors']if 'gate_contact'in v['detail']]\n require(len(gate_probes)==200 and all(v==next(q for q in frozen['anchors']if q['label']==v['label'])for v in gate_probes),'Actual gate contact geometry or owner changed')\n for r in native_rows:")

  else:
   need(name=="mutations48.py","only original numerical methods")
   replace("cases=[\n",source["nonbridge_selector"]+"cases=[\n")
   replace(r"re.sub(r'^R\d+ .*\n','',text,count=1,flags=re.M)","dropped_text")
  ast.parse(text)
  outputs[name]=text
  changes[name]=dict(original_sha256=meta["sha256"],derived_sha256=hashlib.sha256(text.encode()).hexdigest(),changes=edits)
 need(set(outputs)=={"run-rc01.py","audit-rc48.py","mutations48.py"},"complete native extraction/audit/control methods")
 return outputs,changes
def inputs(cfg):
 physical=ROOT/"mos650-wires";need(not physical.exists(),"exclusive authenticated source-view restoration")
 selected=acquire(cfg["view"],physical,lambda n:n.startswith(("native/view/","native/selected/","derived/")))
 view=physical/"native/view";record=read(physical/"derived/result.json")
 need(record["status"]=="PASS_CURRENT650_WIRES_200_GATE_CONTACTS_AND_SEPARATE_INTRINSIC_ELECTRODES_REQUIRES_RC","actual complete650 topology producer")
 need((record["devices"],record["terminals"],record["components"],record["electrical_nets"])==(650,2046,113,114),"all actual native topology counts")
 anchors=read(view/"wire/anchors08.json")
 need((anchors["logical_anchor_count"],anchors["physical_anchor_count"])==(1428,1428),"actual geometric alias counts")
 need(len(anchors["anchors"])==1428 and anchors["dispositions"]==dict(ACTUAL_TERMINAL_METAL_POINT_REFERENCE=1203,RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE=643,RETAINED_INTRINSIC_GATE_REQUIRES_POLY_RC=200),"all geometric anchors and explicit body scope")
 need(record["physical_run"]==41710162510 and record["physical_gate_contacts"]==200 and record["intrinsic_gate_metal_shortcuts"]is False,"current physically accepted source and separate gate electrodes")
 need(anchors["physical_gate_contact_count"]==200 and anchors["intrinsic_gate_metal_shortcuts"]is False and len(anchors["gate_groups"])==50,"all current native gate contacts and groups")
 for n,h in anchors["inputs"].items():
  p=Path(n);need(p.is_relative_to(physical)and p.is_file()and pin(p)["sha256"]==h,"unchanged absolute complete source input binding")
 runtime=NATIVE/"runtime-parent";runtime.mkdir()
 acquire(cfg["runtime"],runtime,lambda n:n.startswith("wire-stage/magic-cloud/"))
 stage=NATIVE/"wire-stage";stage.mkdir();shutil.copytree(runtime/"wire-stage/magic-cloud",stage/"magic-cloud")
 need(pin(stage/"magic-cloud/runtime/lib/magic/tcl/tclmagic.so")["sha256"]=="e8f2d96121e704acee41e7a58c23feead887527e3bfc4f51da4d97aa8183970e","original qualified native Magic")
 wire=stage/"wire";wire.mkdir()
 for n in ("anchors08.json","native05/wires.gds","native05/wires.l2n","native05/result.json"):
  p=wire/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(view/"wire"/n,p)
  need(pin(p)==pin(view/"wire"/n),"exact current input copy")
 texts,derivation=methods()
 for n,t in texts.items():(wire/n).write_text(t)
 parser=ROOT/"hw/soc/out/pcie-magic-resis-terminals-v1-20261004/audit_pilot.py";parser.parent.mkdir(parents=True,exist_ok=True)
 parser.write_bytes((ROOT/"scripts/frozen_cdr_rc/audit_pilot.py").read_bytes())
 save("input-binding.json",dict(view_source=cfg["view"]["source"],geometry_counts=record,
  logical_anchors=1428,physical_anchors=1428,wire_inputs={n:pin(wire/n)for n in ("anchors08.json","native05/wires.gds","native05/wires.l2n","native05/result.json")},
  numerical_methods=derivation,old500_RC_reused=False,**FLAGS))
 return wire,physical,selected
def execute(argv,label,seconds=1200):
 so=NATIVE/(label+".stdout");se=NATIVE/(label+".stderr");begin=time.monotonic();proc=None;error=None
 env={k:v for k,v in os.environ.items()if k not in("GH_TOKEN","GITHUB_TOKEN","PYTHONOPTIMIZE")}
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
def publish():
 ctx=gate();tag="cloud-results-"+str(ctx["run"])+"-1-cdr-mos650-metal-rc";rel=api("releases/tags/"+tag)
 need(rel["target_commitish"]==ctx["source"]and not rel["assets"]and api("git/ref/tags/"+tag)["object"]["sha"]==ctx["source"],"independent empty release")
 dest=OUT/"publication";dest.mkdir()
 paths=[p for p in OUT.rglob("*")if p.is_file()and dest not in p.parents]
 # The authenticated current view is preserved in its immutable producer release.
 rows={str(p.relative_to(OUT)):pin(p)for p in sorted(paths)}
 index=dest/"complete-output-index.json";index.write_bytes(enc(dict(context=ctx,files=rows,**FLAGS)))
 archive=dest/"native-metal-rc.tar.gz"
 with tarfile.open(archive,"w:gz",compresslevel=1)as tar:
  for n in rows:tar.add(OUT/n,arcname="mos650-metal-rc/"+n,recursive=False)
 for p in(index,archive):subprocess.run(["gh","release","upload",tag,str(p),"--repo",REPO],check=True,timeout=1200)
 assets=api("releases/"+str(rel["id"]))["assets"]
 for p in(index,archive):
  a=next(a for a in assets if a["name"]==p.name);need(a["size"]==p.stat().st_size and a["digest"]=="sha256:"+pin(p)["sha256"],"exact published output")
 save("publication.json",dict(release=rel["id"],assets=assets,**FLAGS))
def main():
 ctx=gate()
 if sys.argv[1:]==["--publish"]:publish();return
 OUT.mkdir();NATIVE.mkdir();DERIVED.mkdir()
 try:
  _,changes=methods();save("source-controls.json",dict(context=ctx,numerical_methods=changes,**FLAGS))
  if sys.argv[1:]==["--controls"]:return
  need(sys.argv[1:]==["--extract"],"explicit native mode")
  cfg=read(ROOT/CFG);wire,physical,selected=inputs(cfg)
  binary=wire.parent/"magic-cloud/runtime/lib/magic/tcl/tclmagic.so"
  execute(["ldd",binary],"runtime-linkage",60)
  need(b"not found"not in(NATIVE/"runtime-linkage.stdout").read_bytes(),"complete native linkage")
  execute([sys.executable,"-B",wire/"run-rc01.py"],"native-extraction")
  capture=read(wire/"rc03/result.json");need(capture["returncode"]==0 and capture["status"]=="NATIVE_COMPLETE_AWAITING_RC_AUDIT","actual extraction success")
  execute([sys.executable,"-B",wire/"audit-rc48.py",wire/"rc03",wire/"anchors08.json",wire/"audit.json"],"native-audit")
  audit=read(wire/"audit.json");need(audit["status"]=="PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY","full raw R/C topology/point/value/alias audit")
  execute([sys.executable,"-B",wire/"mutations48.py"],"native-fault-controls")
  controls=read(wire/"native-mutations01.json");need(controls["status"]=="PASS_REAL_NATIVE_BASELINE_AND13_RAW_CORRUPTION_CONTROLS"and len(controls["cases"])==13,"all original meaningful native corruptions")
  for n,p in selected.items():need(pin(physical/n)==p,"current full source view unchanged")
  gate()
  for name,value in [("capture.json",capture),("audit.json",audit),("native-controls.json",controls)]:save(name,value)
  save("result.json",dict(status="PASS_ACTUAL650_FRESH_METAL_VIA_RC_REQUIRES_GATE_POLY_MIM_AND_ELECTRICAL_COMPOSITION",
   context=ctx,physical_source_run=cfg["view"]["run"],actual_resistors=audit["actual_exported_resistors"],actual_capacitors=audit["actual_exported_capacitors"],
   physical_anchors=1428,logical_anchors=1428,native_fault_controls=13,metal_via_RC_extracted=True,physical_gate_contacts=200,intrinsic_gate_metal_shortcuts=False,**FLAGS))
 except BaseException as e:
  save("failure.json",dict(error=repr(e),traceback=traceback.format_exc(),**FLAGS));raise
 finally:
  rc=NATIVE/"wire-stage/wire/rc03"
  if(rc/"native.log").exists():(DERIVED/"native.log").write_bytes((rc/"native.log").read_bytes())
  for n in("result.json",):
   if(rc/n).exists()and not(DERIVED/("raw-"+n)).exists():save("raw-"+n,read(rc/n))
if __name__=="__main__":main()
