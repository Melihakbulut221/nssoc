#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud source controls for exact diode reconstruction; no native acquisition."""
import ast,copy,hashlib,json,os,subprocess,sys
from pathlib import Path
import mainchip_saved_diode_reconstruction as plan
def main():
    root=Path(__file__).resolve().parents[1];target=Path(sys.argv[1])
    inherited=target.with_name("reconstruction-inherited-observer-controls.json")
    subprocess.run([sys.executable,"-B",str(root/"scripts/check_mainchip_saved_repair_audit.py"),str(inherited)],check=True)
    previous=json.loads(inherited.read_bytes())
    assert previous["status"]=="PASS_SAVED_REPAIR_AUDIT_SOURCE_CONTROLS"and previous["count"]==30
    rows=["inherited/"+x for x in previous["passed_cases"]]
    nets={k:dict(identity=dict(sigtype=t))for k,t in(("signal","SIGNAL"),("clock","SIGNAL"),("vdd","POWER"),("vss","GROUND"),("other","POWER"))}
    template=dict(master=["lib",plan.p.DIODE],master_type="CORE_ANTENNACELL",origin=[10,20],location=[10,20],
      orientation="R0",status="PLACED",pins={"A":dict(net="signal",sigtype="SIGNAL",io="INPUT"),
      "VDD":dict(net="vdd",sigtype="POWER",io="INOUT"),"VSS":dict(net="vss",sigtype="GROUND",io="INOUT")})
    raw=copy.deepcopy(template);raw["pins"]["VDD"]["net"]=None;raw["pins"]["VSS"]["net"]=None
    def check(name,ok):assert ok,name;rows.append(name)
    def normalize(row,t=None,n=None):
        return plan.normalized_diode(row,template if t is None else t,nets if n is None else n,["clock"])
    check("unconnected PG is bound only to existing template",normalize(raw)==template and raw["pins"]["VDD"]["net"]is None)
    check("existing correct PG retained",normalize(template)==template)
    edits=[
      ("different master refused",lambda x:x.update(master=["lib","other"])),
      ("different master type refused",lambda x:x.update(master_type="CORE")),
      ("unplaced refused",lambda x:x.update(status="UNPLACED")),
      ("unknown orientation refused",lambda x:x.update(orientation="guess")),
      ("boolean origin refused",lambda x:x["origin"].__setitem__(0,True)),
      ("noninteger location refused",lambda x:x["location"].__setitem__(0,1.5)),
      ("missing A refused",lambda x:x["pins"].pop("A")),
      ("extra terminal refused",lambda x:x["pins"].update(extra=copy.deepcopy(x["pins"]["A"]))),
      ("protected A refused",lambda x:x["pins"]["A"].update(net="clock")),
      ("missing signal refused",lambda x:x["pins"]["A"].update(net="missing")),
      ("power A refused",lambda x:x["pins"]["A"].update(net="vdd")),
      ("wrong A direction refused",lambda x:x["pins"]["A"].update(io="OUTPUT")),
      ("wrong existing PG refused",lambda x:x["pins"]["VDD"].update(net="other")),
      ("wrong PG type refused",lambda x:x["pins"]["VSS"].update(sigtype="SIGNAL"))]
    for name,edit in edits:
        changed=copy.deepcopy(raw);edit(changed)
        try:normalize(changed)
        except(ValueError,AssertionError):rows.append(name)
        else:raise AssertionError(name)
    bad=copy.deepcopy(template);bad["pins"]["VDD"]["net"]="missing"
    try:normalize(raw,t=bad)
    except(ValueError,AssertionError):rows.append("missing template PG refused")
    else:raise AssertionError("missing template PG")
    bad_nets=copy.deepcopy(nets);bad_nets["vdd"]["identity"]["sigtype"]="SIGNAL"
    try:normalize(raw,n=bad_nets)
    except(ValueError,AssertionError):rows.append("wrong template PG net type refused")
    else:raise AssertionError("wrong template PG type")
    path=root/"scripts/mainchip_saved_diode_reconstruction_native.py"
    tree=ast.parse(path.read_bytes());nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in("native_pointer","same_native")]
    assert len(nodes)==2
    scope={};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),"exec"),scope)
    class Proxy:
        def __init__(self,address):self.this=address
    check("same live native object across distinct wrappers",scope["same_native"](Proxy(4096),Proxy(4096)))
    check("different live native objects stay distinct",not scope["same_native"](Proxy(4096),Proxy(8192)))
    for name,value in(("zero native pointer refused",Proxy(0)),("missing native pointer refused",None)):
        try:scope["same_native"](value,Proxy(4096))
        except(ValueError,AttributeError):rows.append(name)
        else:raise AssertionError(name)
    # Reproduce the actual hosted failure and exercise the actual fixed host
    # transfer statement using the authentic complete native engine report.
    evidence=root/"docs/evidence/mainchip-diode-reconstruction-terminal-41190910993"
    raw_inner=(evidence/"readable-records/native/bulk-postdrt-inner-result.json").read_bytes()
    assert len(raw_inner)==33323 and hashlib.sha256(raw_inner).hexdigest()=="7fdfb7680e2dd98c53a6d501b65d79f7aaafa9d217663210ccfb924586798f4c"
    actual=json.loads(raw_inner)
    failed=json.loads((evidence/"readable-records/failure.json").read_bytes())
    assert failed["error"]["error"]=="KeyError('saved_audit_result')"
    old=ast.parse((evidence/"tested-source/scripts/cloud_mainchip_saved_diode_reconstruction.py").read_bytes())
    transfers=[n for n in ast.walk(old)if isinstance(n,ast.Assign)and any(
      isinstance(t,ast.Subscript)and isinstance(t.value,ast.Name)and t.value.id=="report"
      and isinstance(t.slice,ast.Constant)and t.slice.value=="saved_diode_reconstruction_result"for t in n.targets)]
    assert len(transfers)==1
    try:exec(compile(ast.Module(body=transfers,type_ignores=[]),"actual prior host transfer","exec"),dict(report={},result=actual))
    except KeyError as exc:check("authentic prior host transfer reproduces failure",str(exc)=="'saved_audit_result'")
    else:raise AssertionError("previous genuine failure did not reproduce")
    current=ast.parse((root/"scripts/cloud_mainchip_saved_diode_reconstruction.py").read_bytes())
    calls=[n for n in ast.walk(current)if isinstance(n,ast.Expr)and isinstance(n.value,ast.Call)
      and isinstance(n.value.func,ast.Attribute)and n.value.func.attr=="update"
      and isinstance(n.value.func.value,ast.Name)and n.value.func.value.id=="report"
      and len(n.value.args)==1 and isinstance(n.value.args[0],ast.Call)
      and isinstance(n.value.args[0].func,ast.Attribute)and n.value.args[0].func.attr=="accept_native_result"]
    assert len(calls)==1
    scope=dict(report={},result=actual,plan=plan)
    exec(compile(ast.Module(body=calls,type_ignores=[]),"actual fixed host transfer","exec"),scope)
    expected=plan.accept_native_result(actual)
    check("actual fixed host transfer accepts authentic completed native report",
      scope["report"]==expected and expected["saved_diode_reconstruction_result"]["candidate"]==dict(
        bytes=213798975,sha256="2675b9465e7e220931b608ecc0aeec4f171355f3b19259024e04c4e0fb079c34"))
    refusals=[
      ("incomplete native phase refused",lambda x:x["reconstruction_phase_states"].update(admit="failed")),
      ("nonzero actual child refused",lambda x:x["commands"][-1].update(returncode=7)),
      ("changed original wire refused",lambda x:x["saved_diode_reconstruction_result"].update(all_original_wire_bytes_and_metadata_preserved=False)),
      ("wrong actual diode count refused",lambda x:x["saved_diode_reconstruction_result"].update(added_diodes=1350)),
      ("malformed candidate identity refused",lambda x:x["saved_diode_reconstruction_result"]["candidate"].update(sha256="bad")),
      ("false physical acceptance refused",lambda x:x["saved_diode_reconstruction_result"].update(physical_acceptance=True)),
      ("unexpected routing scope refused",lambda x:x.update(actual_route_calls=1)),
      ("missing actual native result refused",lambda x:x.pop("saved_diode_reconstruction_result"))]
    for name,edit in refusals:
        bad=copy.deepcopy(actual);edit(bad)
        try:plan.accept_native_result(bad)
        except(ValueError,AssertionError,KeyError):rows.append(name)
        else:raise AssertionError(name)
    assert len(rows)==62 and len(set(rows))==62
    result=dict(status="PASS_SAVED_DIODE_RECONSTRUCTION_SOURCE_CONTROLS",count=62,passed_cases=rows,
      inherited_observer_controls=30,reconstruction_controls=22,handoff_controls=10,
      source=os.environ["GITHUB_SHA"],run_id=int(os.environ["GITHUB_RUN_ID"]),attempt=int(os.environ["GITHUB_RUN_ATTEMPT"]),
      source_pin=hashlib.sha256(path.read_bytes()).hexdigest(),native_executed=False,**plan.p.FLAGS)
    target.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n");print(json.dumps(result,sort_keys=True))
if __name__=="__main__":main()
