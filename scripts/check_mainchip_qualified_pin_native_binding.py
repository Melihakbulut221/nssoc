"""Exercise the private native binding using the full authenticated 828-net readout.
ODB methods are simulated here; this is source/boundary qualification, not a native run.
The original native connectivity function and original graph/predicate bodies execute.
"""
import ast,copy,hashlib,json,sys,traceback
from pathlib import Path
from types import SimpleNamespace,FunctionType
import cloud_mainchip_qualified_pin_connectivity as qualified
import mainchip_qualified_pin_native_binding as binding
import mainchip_qualified_pin_connectivity as core
import mainchip_targeted_counterpart_routing as scope_core
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"scoped-restoration-controls"/"qualified-binding"
def save(name,value):
 path=OUT/name;path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n")
def function(path,name,globals_):
 tree=ast.parse(path.read_text())
 items=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name==name]
 assert len(items)==1
 namespace=dict(globals_)
 exec(compile(ast.Module(body=items,type_ignores=[]),str(path),"exec"),namespace)
 return namespace[name]
def main():
 OUT.mkdir(parents=True,exist_ok=False)
 qualified.OUT=OUT/"model-controls";qualified.OUT.mkdir()
 qualified.controls()
 inherited=json.loads((qualified.OUT/"qualified-controls.json").read_bytes());assert inherited["count"]==67
 for name in ["mainchip_net459_connectivity.py","mainchip_bulk_postdrt_antenna.py","mainchip_single_antenna_trial.py","mainchip_targeted_counterpart_routing.py"]:
  assert (ROOT/"scripts"/name).read_bytes()==(ROOT/"original/scripts"/name).read_bytes(),("exact original reader dependencies",name)
 clone=function(ROOT/"original/scripts/mainchip_container_floorplan_import.py","clone",dict(FunctionType=FunctionType))
 def project(plan,scope):return dict(original=plan,scope=scope,projected=scope_core.observation_scope(plan,scope))
 acquisition=clone(qualified.acquire,
  scope_core=SimpleNamespace(validate_scope=scope_core.validate_scope,observation_scope=project),
  save=lambda name,v:save("authentication/"+name,v))
 observations,bundle=acquisition()
 plan,scope=bundle["original"],bundle["scope"]
 observe,gate=qualified.original.functions()
 source=ROOT/"original/scripts/mainchip_bulk_postdrt_antenna_native.py"
 seen={};load_calls=[];destroyed=[];state=dict(changed=False)
 def require(ok,label):
  if not ok:raise AssertionError(label)
 def exact(a,b,label):require(core.enc(a)==core.enc(b),label)
 def geometry_pin(row):
  ident=row["scoped_identity"];assert ident[0]=="iterm"
  return SimpleNamespace(getInst=lambda:SimpleNamespace(getName=lambda:ident[1]),
   getMTerm=lambda:SimpleNamespace(getName=lambda:ident[2]),
   getGeometries=lambda:[(SimpleNamespace(getName=lambda layer=layer:layer),box)for layer,box in row["geometries"]])
 def net(name):
  row=observations[name]["positive_area"]
  return SimpleNamespace(isSpecial=lambda:False,getSWires=lambda:[],getBTerms=lambda:[],
   getWire=lambda:name,getITerms=lambda:[geometry_pin(p)for p in row["source_pins"]])
 db=SimpleNamespace(getTech=lambda:None);block=SimpleNamespace(findNet=net)
 def reader(path):
  load_calls.append(str(path));return db,block
 def persist(path,value):
  if path.name.startswith("connectivity-"):
   name=value["net"];assert name not in seen
   assert core.enc(value["modes"])==core.enc(observations[name]),"real original reader reconstructed exact authenticated graph"
   seen[name]=core.pin(value["modes"])
  else:save("boundary/"+path.parent.name+"/"+path.name,value)
 native_p=SimpleNamespace(require=require,exact=exact,validate_connectivity=gate)
 environment=dict(p=native_p,n=SimpleNamespace(load=reader),graph=SimpleNamespace(observe=observe),
  own=SimpleNamespace(api_evidence=lambda:{},named_layers=lambda *args:{},box=lambda box:box,
   native_wire=lambda db,block,name,layers,proof:dict(shapes=observations[name]["positive_area"]["source_shapes"])),
  odb=SimpleNamespace(dbDatabase=SimpleNamespace(destroy=lambda db:destroyed.append(True))),
  save=persist,hashlib=hashlib)
 reader_function=function(source,"connectivity",environment)
 native=SimpleNamespace(p=native_p,graph=SimpleNamespace(observe=observe),connectivity=reader_function,
  fp=lambda path:dict(core.CANDIDATE),save=persist)
 original_globals=reader_function.__globals__.copy()
 candidate=Path("/simulated-native/candidate.odb")
 call=binding.bind(native,scope_core,clone,plan,scope,ROOT)
 result=call(candidate,plan,Path("/simulated-native/output"))
 assert result["changed_nets"]==828 and result["both_modes_complete"]and result["original_graphs_replayed"]==1656
 assert result["original_wire_only_failed_nets"]==142 and result["qualified_pin_observations"]==1300
 assert len(seen)==828 and len(load_calls)==len(destroyed)==1
 assert native_p.validate_connectivity is gate and reader_function.__globals__==original_globals
 checks=["graph, predicate and scope sources identical to frozen native dependencies",
  "complete original native reader body reconstructs all 1656 authenticated graphs",
  "all 828 original wire-only graph reports retained before adapter acceptance",
  "exact full 828/142/1300/77 core with original 1351 diode predicate",
  "database destroy finally retained",
  "original predicate and native function globals unchanged"]
 def reject(label,fn):
  try:fn()
  except (AssertionError,KeyError,ValueError):checks.append("reject "+label)
  else:raise AssertionError("accepted "+label)
 changed=copy.deepcopy(plan);changed["mutable_nets"]=changed["mutable_nets"][:-1]
 reject("changed physical caller plan",lambda:call(candidate,changed,Path("/simulated-native/negative")))
 wrong=SimpleNamespace(**vars(native));wrong.fp=lambda path:dict(bytes=1,sha256="0"*64)
 reject("different candidate before any native load",lambda:binding.bind(wrong,scope_core,clone,plan,scope,ROOT)(candidate,plan,Path("/simulated-native/negative")))
 assert len(load_calls)==1
 # Test callback dispatch contracts without pretending these injected readers are native evidence.
 def no_callback(path,plan,out):return dict(both_modes_complete=True)
 missing=SimpleNamespace(**vars(native));missing.connectivity=function_from(no_callback,{"p":native_p})
 reject("reader omits predicate callback",lambda:binding.bind(missing,scope_core,clone,plan,scope,ROOT)(candidate,plan,Path("/simulated-native/negative")))
 def wrong_plan(path,plan,out):return p.validate_connectivity({},dict(mutable_nets=[]))
 wrong=SimpleNamespace(**vars(native));wrong.connectivity=function_from(wrong_plan,{"p":native_p})
 reject("changed projected plan at callback",lambda:binding.bind(wrong,scope_core,clone,plan,scope,ROOT)(candidate,plan,Path("/simulated-native/negative")))
 # Actual source qualification records are mandatory and hash-bound.
 invalid=OUT/"invalid-root";invalid.mkdir()
 for name in binding.QUALIFICATION:
  target=invalid/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/name).read_bytes())
 name=next(iter(binding.QUALIFICATION));target=invalid/name;target.write_bytes(target.read_bytes()+b" ")
 reject("modified GDS qualification bytes",lambda:binding.records(invalid))
 target.unlink();target.symlink_to(ROOT/name)
 reject("symlinked GDS qualification input",lambda:binding.records(invalid))
 assert len(checks)==12,len(checks)
 save("result.json",dict(status="PASS_ORIGINAL_NATIVE_READER_BOUNDARY_ON_AUTHENTICATED_828_GRAPHS",
  controls=len(checks),inherited_model_controls=67,checks=checks,connectivity=result,
  native_boundary_simulated=True,actual_ODB_engine_executed=False,
  original_native_reader_source="7a0776718ec37a106b7dfde0cbd477c6a2a5522f",
  **core.FLAGS))
 print(json.dumps(dict(boundary_controls=len(checks),model_controls=67,changed_nets=828,status="PASS")))
def function_from(fn,bindings):
 # Inject only into a private copy for negative fixtures.
 new=FunctionType(fn.__code__,{**fn.__globals__,**bindings},fn.__name__,fn.__defaults__,fn.__closure__)
 new.__kwdefaults__=fn.__kwdefaults__
 return new
if __name__=="__main__":
 try:main()
 except BaseException:
  OUT.mkdir(parents=True,exist_ok=True);save("failure.json",dict(traceback=traceback.format_exc(),**core.FLAGS));raise
