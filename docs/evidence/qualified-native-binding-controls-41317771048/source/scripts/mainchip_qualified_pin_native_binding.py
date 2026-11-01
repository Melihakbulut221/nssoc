"""Bind independently qualified physical conductors to the original native reader.
The original reader still persists every wire-only graph before this adapter runs.
This changes the explicitly named material model, not the original predicate.
"""
import copy,hashlib,json
from types import SimpleNamespace
import mainchip_qualified_pin_connectivity as core

QUALIFICATION={"docs/evidence/restored-pin-gds-terminal-41314829887/derived/placed-pin-correspondence.json":{"bytes":1521534,"sha256":"427fc458b36a60c040858df4a7b1af6661485186533487625451a7cf5d99bf3f"},"docs/evidence/restored-pin-gds-terminal-41314829887/derived/result.json":{"bytes":721,"sha256":"446a740f3372f39ab71da57070a85d68b36e64033709f42f084a2234c938aa13"}}
PREFIX="docs/evidence/restored-pin-gds-terminal-41314829887/derived/"
def records(root):
 values={}
 for name,expected in QUALIFICATION.items():
  path=root/name
  assert path.is_file()and not path.is_symlink(),("regular qualification",name)
  raw=path.read_bytes()
  assert dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())==expected,("qualification pin",name)
  values[name]=json.loads(raw)
 rows=values[PREFIX+"placed-pin-correspondence.json"];result=values[PREFIX+"result.json"]
 assert result["context"]==dict(run=41314829887,source="b0cc820906e9cc75c3a7d55fce11297a8e4f1da1")
 core.qualification(rows,result)
 return rows,result

def bind(native,scope_core,clone,plan,scope,source_root):
 scope_core.validate_scope(scope,plan)
 original=copy.deepcopy([plan,scope])
 original_predicate=native.p.validate_connectivity
 def connectivity(path,argument,out):
  native.p.exact([plan,scope],original,"unchanged binding plan and scope")
  native.p.exact(argument,plan,"original physical caller plan")
  projected=scope_core.observation_scope(plan,scope)
  assert len(projected["mutable_nets"])==828 and len(projected["attachments"])==1351
  before=native.fp(path)
  assert before==core.CANDIDATE,"exact GDS-qualified candidate ODB"
  rows,result=records(source_root)
  calls=[];proof={}
  proxy=SimpleNamespace(**vars(native.p))
  def physical(observations,actual_plan):
   native.p.exact(actual_plan,projected,"exact projected native caller")
   assert not calls,"exactly one native connectivity predicate call"
   calls.append(True)
   outcome,reports=core.audit(observations,actual_plan,rows,result,native.graph.observe,original_predicate)
   native.save(out/"qualified-pin-conductor-per-net.json",reports)
   proof.update(connectivity=outcome)
   return outcome
  proxy.validate_connectivity=physical
  native.save(out/"qualified-pin-conductor-binding.json",dict(status="STARTED",
   candidate=before,qualification=QUALIFICATION,model=core.MODEL,
   original_wire_only_reports_preserved=True,native_adapter_executed=True,**core.FLAGS))
  try:
   outcome=clone(native.connectivity,p=proxy)(path,projected,out)
   assert len(calls)==1 and outcome==proof["connectivity"]
   assert native.fp(path)==before,"candidate changed during qualified connectivity"
   assert records(source_root)==(rows,result),"qualification changed during native readout"
   native.p.exact([plan,scope],original,"unchanged binding plan and scope after readout")
   native.save(out/"qualified-pin-conductor-binding.json",dict(status="COMPLETE",
    candidate=before,qualification=QUALIFICATION,connectivity=outcome,
    original_wire_only_reports_preserved=True,native_adapter_executed=True,**core.FLAGS))
   return outcome
  except BaseException as exc:
   native.save(out/"qualified-pin-conductor-failure.json",dict(error=repr(exc),
    candidate_before=before,qualification=QUALIFICATION,native_adapter_executed=True,**core.FLAGS))
   raise
 return connectivity
