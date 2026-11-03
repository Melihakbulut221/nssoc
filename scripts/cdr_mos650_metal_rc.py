#!/usr/bin/env python3
"""Fresh distributed metal/via RC on the complete physically bound650-device view."""
import ast,hashlib,io,json,os,shutil,signal,subprocess,sys,tarfile,time,tokenize,traceback
from collections import Counter
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"mos650-metal-rc";NATIVE=OUT/"native";DERIVED=OUT/"derived"
CFG="scripts/cdr-mos650-metal-rc-inputs.json";PINS="scripts/cdr-mos650-metal-rc-pins.json"
METHODS="docs/evidence/mos650-metal-rc-original-methods.json"
REPO="Melihakbulut221/nssoc";BRANCH="codex/cdr-mos650-mim-rc"
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
 acquire(cfg["runtime"],runtime,lambda n:n in cfg["runtime"]["selected"])
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

def mim_extract(cfg,physical):
 import cdr_mos650_mim_support as support
 import tx_native_cap_order as cap_order
 precise="1a44bd5c70af3800213419c2e3b2213285523a74fcc4b92bc9cf7314d93a592c"
 runtime=NATIVE/"runtime-parent";source=physical/"native/view"
 flat=read(physical/"derived/lvs_flat-identity.json")
 need(len(flat["pairs"])==650 and flat["terminal_count"]==2046,"all current native650 identities")
 binding=dict(devices=[dict(native_id=p["layout"]["id"],model=p["layout"]["model"],native_parameters={k:str(v)for k,v in p["layout"]["parameters"].items()})for p in flat["pairs"]])
 need(sum(d["model"]=="cap_cmim"for d in binding["devices"])==7,"seven actual native MIMs")
 methods0,derivation=methods();results={}
 execute([sys.executable,"-B",ROOT/"scripts/tx_reverse_native_cap_order.py","--controls"],"reverse-order-controls")
 save("native-order-controls.json",dict(controls=cap_order.controls(),**FLAGS))
 for variant in("precise","precise_reversed"):
  stage=NATIVE/("mim-"+variant);stage.mkdir()
  os.environ["NSSOC_MIM_STAGE"]=str(stage);support.OUT=stage
  (stage/"binding.json").write_bytes(enc(binding))
  execute([sys.executable,"-B",ROOT/"scripts/cdr_mos650_mim_support.py","--geometry"],variant+"-actual-mim-geometry")
  generated=read(stage/"native-binding.json")
  need(generated["actual_mim_devices"]==7 and generated["actual_mim_masks_exact"]and generated["original_metal_and_vias_unchanged"],"exact current MIM geometry")
  magic=stage/"magic-cloud";shutil.copytree(NATIVE/"wire-stage/magic-cloud",magic)
  shutil.copyfile(runtime/"mim/precise/precision-runtime/lib/magic/tcl/tclmagic.so",magic/"runtime/lib/magic/tcl/tclmagic.so")
  need(pin(magic/"runtime/lib/magic/tcl/tclmagic.so")["sha256"]==precise,"qualified double-total native Magic")
  shutil.rmtree(magic/"tech")
  shutil.copytree(runtime/"mim/precise/ngspice-mim-tech",magic/"tech")
  need(pin(magic/"tech/ihp-sg13g2-extract.tech")["sha256"]=="1439949ae12e2e4da21b0fcb2833b78cf10ac8ad52fa5c68889057aabb69b96c","explicit MIM model semantics, no duplicate device estimate")
  wire=stage/"wire";method=methods0["run-rc01.py"]
  old="e8f2d96121e704acee41e7a58c23feead887527e3bfc4f51da4d97aa8183970e"
  need(method.count(old)==1,"single original native engine pin");method=method.replace(old,precise)
  if variant=="precise_reversed":
   marker="'extract all',";need(method.count(marker)==1,"exact native cap-order insertion")
   command="exec /usr/bin/python3 {"+str(ROOT/"scripts/tx_reverse_native_cap_order.py")+"} {"+str(wire/"rc03/pump_wires.ext")+"}"
   method=method.replace(marker,marker+repr(command)+",")
  (wire/"run-rc01.py").write_text(method)
  audit=methods0["audit-rc48.py"]
  edits=[
   ("import networkx as nx",'import networkx as nx\nsys.path.insert(0,str(Path.cwd()/"scripts"))\nfrom cdr_mos650_mim_support import validate_mim'),
   ("require(not after['devices'] and not before['devices'] and not before['resistors'],'Device insertion into wire-only graph')","require(not before['resistors'],'Unexpected baseline resistor insertion')"),
   ("require(native_r==export_r,'Native/export resistor topology/value differs')","require(native_r==export_r,'Native/export resistor topology/value differs')\n mim_proof=validate_mim(rows,rep,before,after,original,owners,anchors)"),
   ("original_devices=650,","native_mim_intrinsic=mim_proof,original_devices=650,")]
  for a,b in edits:
   need(audit.count(a)==1,"unique MIM audit adaptation "+a);audit=audit.replace(a,b)
  (wire/"audit-rc48.py").write_text(audit);(wire/"mutations48.py").write_text(methods0["mutations48.py"])
  for path in(wire/"run-rc01.py",wire/"audit-rc48.py",wire/"mutations48.py"):ast.parse(path.read_text())
  execute([sys.executable,"-B",wire/"run-rc01.py"],variant+"-native-mim-rc")
  capture=read(wire/"rc03/result.json")
  need(capture["status"]=="NATIVE_COMPLETE_AWAITING_RC_AUDIT"and capture["returncode"]==0,"actual complete MIM-aware RC")
  anchors=read(wire/"anchors08.json")
  captured=support.check_capture((wire/"rc03/wires.spice").read_text(),anchors,binding)
  execute([sys.executable,"-B",wire/"audit-rc48.py",wire/"rc03",wire/"anchors08.json",wire/"mim-audit.json"],variant+"-raw-audit")
  audited=read(wire/"mim-audit.json")
  need(audited["status"]=="PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY"and audited["native_mim_intrinsic"]["devices"]==7,"complete raw RC and actual MIM identity")
  need(audited["actual_exported_resistors"]==captured["R"]and audited["actual_exported_capacitors"]==captured["C"],"same actual full native counts")
  execute([sys.executable,"-B",wire/"mutations48.py"],variant+"-wire-faults")
  faults=read(wire/"native-mutations01.json");need(faults["status"]=="PASS_REAL_NATIVE_BASELINE_AND13_RAW_CORRUPTION_CONTROLS"and len(faults["cases"])==13,"all original13 native wire faults")
  execute([sys.executable,"-B",ROOT/"scripts/cdr_mos650_mim_support.py","--faults"],variant+"-mim-faults")
  intrinsic=read(stage/"intrinsic-controls.json");need(len(intrinsic)==9 and all(x["rejected"]for x in intrinsic),"all9 actual MIM identity corruptions")
  results[variant]=dict(capture=captured,geometry=generated,audit=audited,wire_fault_controls=faults,intrinsic_fault_controls=intrinsic,
   method=pin(wire/"run-rc01.py"),audit_method=pin(wire/"audit-rc48.py"),native_spice=pin(wire/"rc03/wires.spice"))
  save(variant+"-mim-result.json",dict(result=results[variant],**FLAGS))
 first=NATIVE/"mim-precise/wire/rc03";second=NATIVE/"mim-precise_reversed/wire/rc03"
 need(support.records(first/"wires.spice")==support.records(second/"wires.spice"),"both native orders preserve complete R/C/device records")
 _,equivalence=cap_order.reorder((second/"pump_wires.ext").read_text(),(first/"pump_wires.ext").read_text())
 for token in("device","parameters","node","port","equiv","substrate"):
  need([r for r in cap_order.rows((first/"pump_wires.ext").read_text())if r[0]==token]==[r for r in cap_order.rows((second/"pump_wires.ext").read_text())if r[0]==token],"actual noncoupling records unchanged "+token)
 reversal=read(second/"pump_wires.order-proof.json")
 need(reversal["reversed_enumeration"]and reversal["symmetric_endpoint_value_multiset_exact"]and reversal["non_coupling_records_unchanged"],"actual native input order was reversed")
 for n,p in cfg["view"]["selected"].items():need(pin(physical/n)==p,"current physical source unchanged")
 gate()
 save("result.json",dict(status="PASS_CURRENT650_MIM_AWARE_TWO_ORDER_RC_AND22_FAULTS_EACH_REQUIRES_FULL_COMPOSITION",
  context=gate(),physical_source_run=41712243960,current_native_devices=650,current_native_terminals=2046,physical_anchors=1428,physical_gate_contacts=200,
  native_mim_devices=7,actual_resistors=results["precise"]["capture"]["R"],actual_capacitors=results["precise"]["capture"]["C"],
  native_orders=["precise","precise_reversed"],both_native_orders_verified=True,native_rc_and_device_records_equal_in_both_orders=True,
  wire_fault_controls_per_order=13,mim_fault_controls_per_order=9,order_equivalence=equivalence,reversal=reversal,
  intrinsic_mim_cards_separated_from_wire_C_matrix=True,full_loaded_composition_executed=False,**FLAGS))

def main():
 ctx=gate()
 if sys.argv[1:]==["--publish"]:publish();return
 OUT.mkdir();NATIVE.mkdir();DERIVED.mkdir()
 try:
  _,changes=methods();save("source-controls.json",dict(context=ctx,numerical_methods=changes,**FLAGS))
  if sys.argv[1:]==["--controls"]:return
  need(sys.argv[1:]==["--extract"],"explicit native mode")
  cfg=read(ROOT/CFG);wire,physical,selected=inputs(cfg)
  mim_extract(cfg,physical)
 except BaseException as e:
  save("failure.json",dict(error=repr(e),traceback=traceback.format_exc(),**FLAGS));raise
 finally:
  rc=NATIVE/"wire-stage/wire/rc03"
  if(rc/"native.log").exists():(DERIVED/"native.log").write_bytes((rc/"native.log").read_bytes())
  for n in("result.json",):
   if(rc/n).exists()and not(DERIVED/("raw-"+n)).exists():save("raw-"+n,read(rc/n))
if __name__=="__main__":main()
