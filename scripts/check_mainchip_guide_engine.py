"""Cloud controls for hostile capsules and explicit full-chip new-engine binding."""
import ast,hashlib,io,json,tarfile,tempfile
from pathlib import Path
from mainchip_guide_engine_acquisition import restore,need,fp
ROOT=Path(__file__).resolve().parents[1]
def source(name):return(ROOT/"scripts"/name).read_text()
def node(text,name):return next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)and n.name==name)
def body(text,name):return ast.dump(node(text,name),include_attributes=False)
def pin(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
payload=b"actual transport fixture\n";expected={"dir/selected":pin(payload),"other":pin(b"unselected")}
def capsule(rows):
 stream=io.BytesIO()
 with tarfile.open(fileobj=stream,mode="w:gz")as tar:
  for name,data,kind in rows:
   t=tarfile.TarInfo(name);t.type=kind;t.size=len(data)if kind==tarfile.REGTYPE else 0
   if kind in(tarfile.LNKTYPE,tarfile.SYMTYPE):t.linkname="dir/selected"
   tar.addfile(t,io.BytesIO(data)if t.isreg()else None)
 return stream.getvalue()
valid=[("dir",b"",tarfile.DIRTYPE),("dir/selected",payload,tarfile.REGTYPE),("other",b"unselected",tarfile.REGTYPE)]
def attempt(rows,files=expected,selected=("dir/selected",),directories=True):
 with tempfile.TemporaryDirectory()as temp:
  root=Path(temp);archive=root/"a.tar.gz";archive.write_bytes(capsule(rows));dest=root/"selected";dest.mkdir()
  result=restore(archive,files,selected,dest,directories)
  need(result==files,"entire fixture census");need(fp(dest/"dir/selected")==expected["dir/selected"],"selected fixture bytes")
  need(not(dest/"other").exists(),"unselected fixture not extracted")
attempt(valid)
attempt(valid[1:],directories=False)
bad=[
 ("traversal",valid+[("../escape",b"x",tarfile.REGTYPE)]),
 ("absolute",valid+[("/escape",b"x",tarfile.REGTYPE)]),
 ("noncanonical",valid+[("dir/../escape",b"x",tarfile.REGTYPE)]),
 ("duplicate",valid+[valid[1]]),
 ("symlink",[valid[0],("dir/selected",b"",tarfile.SYMTYPE),valid[2]]),
 ("hardlink",[valid[0],("dir/selected",b"",tarfile.LNKTYPE),valid[2]]),
 ("fifo",valid+[("pipe",b"",tarfile.FIFOTYPE)]),
 ("unknown",valid+[("unknown",b"x",tarfile.REGTYPE)]),
 ("unknown_directory",valid+[("unexpected",b"",tarfile.DIRTYPE)]),
 ("missing_file",valid[:-1]),
 ("missing_directory",valid[1:]),
 ("size",[valid[0],("dir/selected",payload+b"x",tarfile.REGTYPE),valid[2]]),
 ("selected_hash",[valid[0],("dir/selected",b"X"+payload[1:],tarfile.REGTYPE),valid[2]]),
 ("unselected_hash",[valid[0],valid[1],("other",b"Unselected",tarfile.REGTYPE)]),
 ("duplicate_directory",[valid[0],*valid]),
]
refused=[]
for label,rows in bad:
 try:attempt(rows)
 except ValueError:refused.append(label)
 else:raise AssertionError("accepted hostile capsule: "+label)
need(len(refused)==15,"all transport refusals")
try:attempt(valid,selected=("not-in-index",))
except ValueError:refused.append("unknown_selection")
else:raise AssertionError("unknown selected file accepted")
old=source("cloud_mainchip_route47_recovery.py");new=source("cloud_mainchip_guide_engine_roundtrip.py")
for name in("sha","fp","api","write","own_sources"):need(body(old,name)==body(new,name),"original host primitive "+name)
oldi=source("mainchip_route47_recovery_inner.py");inner=source("mainchip_guide_engine_inner.py")
for name in("usage","resources","runtime","terminal"):
 def nested(text):
  return next(n for n in ast.walk(node(text,"main"))if isinstance(n,ast.FunctionDef)and n.name==name)
 need(ast.dump(nested(oldi),include_attributes=False)==ast.dump(nested(inner),include_attributes=False),"original native runtime/resource guard "+name)
for fragment in("base.stop_supervision(report,sup,beat)","memory_policy.configure(sup,int(report['cgroup_initial']['memory.max']))",
 "memory_policy.checker(Path(base.command_evidence.__file__).read_bytes())","base.supervised_run(rep,label,argv,seconds,sup)",
 "p.source_guard();assert fingerprint(Path(ORIGINAL_ENGINE))==c.ENGINE"):
 need(fragment in inner,"retained native lifecycle "+fragment)
for fragment in('fingerprint(Path(ENGINE))==CONFIG["binary"]','CONFIG["runtime_dependencies"]',
 'CONFIG["image"]==c.IMAGE','ENGINE="/work/guide-engine/openroad"'):
 need(fragment in inner,"explicit engine/runtime binding")
need("c.ENGINE="not in inner and "base.ENGINE="not in inner,"no replacement of original engine contract")
phases=next(n for n in ast.parse(inner).body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=="PHASES"for t in n.targets))
need(ast.literal_eval(phases.value)==("roundtrip","final-check","measure"),"all native phases")
native=source("mainchip_guide_engine_native.py")
for call in("native.snapshot(","odb.write_db(","native.check_tcl(","native.collect_checks("):
 need(call in native,"actual native full-chip operation "+call)
need("detailed_route"not in native and "repair_antennas"not in native,"no hidden routing")
engine=json.loads((ROOT/"scripts/mainchip-guide-engine-built-inputs.json").read_bytes())
reference=json.loads((ROOT/"scripts/mainchip-guide-engine-reference.json").read_bytes())
need(engine["producer"]["run"]==41493369685 and engine["binary"]==engine["output_index"]["files"]["openroad"],"exact successful engine")
need(reference["producer"]["run"]==41440285882 and len(reference["index"]["files"])==72,"actual entire recovered reference")
need(len(reference["selected"])==8 and set(reference["selected"])<=set(reference["index"]["files"]),"entire declared selected reference")
need(engine["native_chip_roundtrip_qualified"]is False and engine["native_routing_qualified"]is False,"build is not chip qualification")
out=ROOT/"guide-engine-controls";out.mkdir()
(out/"result.json").write_text(json.dumps(dict(status="PASS_GUIDE_ENGINE_TRANSPORT_AND_BINDING_CONTROLS",
 positive_capsule_controls=2,hostile_capsule_refusals=refused,original_resource_guards_unchanged=True,
 native_executed=False,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False),sort_keys=True,indent=2)+"\n")
print("PASS guide engine: 2 complete transports, 16 hostile capsule refusals, explicit engine binding and original resource guards")
