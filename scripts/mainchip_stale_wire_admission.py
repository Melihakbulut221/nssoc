"""Source-bound read-only admission of the one additional stale-wire clear phase.

This module runs no native tool. A cloud caller must authenticate the complete
producer capsule and source before audit(); the source-only workflow tests only
synthetic records and does not authorize native acquisition or acceptance.
"""
import ast,copy,gc,hashlib,inspect,json
from pathlib import Path
import mainchip_saved_diode_routing as original
import mainchip_stale_wire_routing as stale
import mainchip_exit_checked_command_evidence as command
import cloud_mainchip_original_clock_restoration as streams
from mainchip_stale_wire_routing import p

ROOT=stale.ROOT
MANIFEST="scripts/mainchip-stale-wire-admission-pins.json"
PLAN="scripts/mainchip_saved_diode_routing.py"
PLAN_SHA="262f9078a57500e1e9431ed096358f3bd634ef244b4900b414887a55309780c0"
CLEAR="bulk-postdrt-stale-wire-clear"
ROUTE="bulk-postdrt-route"
ARGV=["/work/engine/openroad","-no_init","-exit","-python",
      "/work/tail-source/scripts/mainchip_stale_wire_routing_native.py"]
WORK=Path("/work/out/work/bulk-postdrt-antenna")
NEW=("scripts/mainchip_stale_wire_admission.py",
     "scripts/check_mainchip_stale_wire_admission.py",
     "scripts/check_mainchip_stale_wire_admission_inherited.py")

def source_gate():
    inherited=stale.source_gate()
    m=json.loads((ROOT/MANIFEST).read_bytes())
    p.require(m["schema"]=="mainchip-stale-wire-admission-source-v1"
      and m["source_controls_authorized"]is True,"source-only admission manifest")
    for flag in ("native_acquisition_authorized","native_execution_authorized","scoped_routing_authorized",
                 "current_native_result_accepted",*p.FLAGS):
        p.require(m[flag]is False,"source controls are not native acceptance")
    p.require(set(inherited["files"])|{stale.MANIFEST}|set(NEW)<=set(m["files"]),"complete protected source projection")
    for name,digest in inherited["files"].items():p.exact(m["files"][name],digest,"inherited source pin")
    for name,digest in m["files"].items():
        path=regular(ROOT,name)
        p.require(pin(path)["sha256"]==digest,"protected source: "+name)
    return m

def regular(root,name):
    name=Path(name);root=Path(root)
    p.require(not name.is_absolute()and ".."not in name.parts and name.parts,"owned relative member")
    p.require(root.is_dir()and not root.is_symlink(),"regular archive root")
    current=root
    for part in name.parts:
        current=current/part;p.require(not current.is_symlink(),"no member symlink")
    p.require(current.is_file(),"required regular member: "+str(name))
    return current

def pin(path):
    h=hashlib.sha256();size=0
    with Path(path).open("rb")as stream:
        for data in iter(lambda:stream.read(1024*1024),b""):h.update(data);size+=len(data)
    return dict(bytes=size,sha256=h.hexdigest())

def exact_bytes(first,second,reason):
    p.require(type(first)is bytes and type(second)is bytes and first==second,reason)

def decode(root,name):
    return json.loads(regular(root,name).read_bytes())

def validator_tree(raw):
    p.require(hashlib.sha256(raw).hexdigest()==PLAN_SHA,"exact original plan module")
    module=ast.parse(raw);functions=[n for n in module.body if isinstance(n,ast.FunctionDef)and n.name=="accept_native_result"]
    p.require(len(functions)==1,"unique original validator")
    before=functions[0];after=copy.deepcopy(before)
    expected=ast.parse('expected=["bulk-postdrt-version","bulk-postdrt-ldd"]+["bulk-postdrt-route-continuation-"+x if x in PREPARATION else "bulk-postdrt-"+x for x in PHASES]').body[0]
    matches=[i for i,n in enumerate(after.body)if ast.dump(n)==ast.dump(expected)]
    p.require(len(matches)==1,"unique exact expected command assignment")
    insert=ast.parse('expected.insert(expected.index("bulk-postdrt-route"),"bulk-postdrt-stale-wire-clear")').body[0]
    after.body.insert(matches[0]+1,insert)
    reverse=copy.deepcopy(after);removed=reverse.body.pop(matches[0]+1)
    p.exact(ast.dump(removed),ast.dump(insert),"only added statement")
    p.exact(ast.dump(reverse),ast.dump(before),"all original validator AST unchanged")
    return ast.fix_missing_locations(ast.Module(body=[after],type_ignores=[]))

def derived_validator():
    raw=regular(ROOT,PLAN).read_bytes();tree=validator_tree(raw)
    scope=dict(vars(original));exec(compile(tree,str(ROOT/PLAN)+"::one-extra-clear","exec"),scope)
    return scope["accept_native_result"]

def validate_native_result(inner):
    """Exact original final predicates plus the actual extra phase identity."""
    original_bytes=p.encode(inner)
    rows=inner["commands"];labels=[x["label"]for x in rows]
    p.require(labels.count(CLEAR)==1 and labels.count(ROUTE)==1
      and labels.index(CLEAR)+1==labels.index(ROUTE),"single clear immediately before single route")
    clear=rows[labels.index(CLEAR)];route=rows[labels.index(ROUTE)]
    p.exact(clear["argv"],ARGV,"exact clear invocation")
    p.require(type(clear["requested_timeout_seconds"])is int and clear["requested_timeout_seconds"]==1200,
      "original clear phase budget")
    p.require(type(route["requested_timeout_seconds"])is int and route["requested_timeout_seconds"]==14400,
      "unchanged original route budget")
    terminal=inner["stale_wire_clear"]
    p.require(terminal["phase"]=="stale-wire-clear"and terminal["complete"]is True
      and terminal["error"]is None and terminal["terminal_errors"]==[],"actual complete clear terminal")
    p.require(all(terminal[k]is False for k in p.FLAGS),"no premature clear acceptance")
    result=derived_validator()(inner)
    exact_bytes(p.encode(inner),original_bytes,"preserve full historical record")
    return result

def audit(root):
    """Replay source-bound derived evidence, never generate geometry or reroute."""
    source_gate()
    root=Path(root);inner=decode(root,"bulk-postdrt-inner-result.json")
    result=validate_native_result(inner)
    trace=root/"bulk-postdrt-supervision"
    for row in inner["commands"][2:]:
        label=row["label"];seconds=14400 if label==ROUTE else 1200
        p.require(type(row["requested_timeout_seconds"])is int and row["requested_timeout_seconds"]==seconds,
          "unchanged original command deadline")
        member="bulk-postdrt-supervision/"+label+".command.json"
        record=decode(root,member)
        p.exact(row["command_record_pin"],pin(regular(root,member)),"actual command record pin")
        p.exact(record,row["supervision_record"],"embedded and archived command equality")
        p.exact(record["label"],label,"command label")
        p.exact(record["argv"],row["argv"],"command argv")
        p.exact(row["command_evidence"],command.validate(record,seconds),"full original supervisor proof")
        for stream in ("stdout","stderr"):regular(root,"bulk-postdrt-supervision/"+label+"."+stream)
        streams.terminal_stream(record,trace,label)
    data="bulk-postdrt-antenna/"
    p.exact(decode(root,data+"stale-wire-clear-terminal.json"),inner["stale_wire_clear"],"actual terminal bytes")
    mutation=decode(root,data+"stale-wire-mutation.json")
    admission=decode(root,data+"insertion-plan.json")
    p.require(len(admission["mutable_nets"])==608 and len(admission["attachments"])==1351
      and len(admission["protected_nets"])==1691,"actual current scoped census")
    p.require(mutation["complete"]is True and mutation["all_guides_unchanged"]is True,
      "complete native mutation and serialization guide checks")
    p.require(all(mutation[k]is False for k in p.FLAGS),"no premature mutation acceptance")
    p.exact(mutation["removed"],sorted(admission["mutable_nets"]),"exact ordered608wire removal")
    before=decode(root,data+"fixed-snapshot.json")
    after=decode(root,data+"stale-wire-cleared-snapshot.json")
    p.require(len(before["instances"])==154480 and len(before["nets"])==143820,"complete candidate census")
    p.exact(mutation["delta"],stale.clear_delta(before,after,admission),"complete native snapshot replay")
    del before,after;gc.collect()
    p.exact(mutation["input"],pin(regular(root,"work/bulk-postdrt-antenna/fixed.odb")),"unchanged fixed input")
    p.exact(mutation["candidate"],pin(regular(root,"work/bulk-postdrt-antenna/stale-wire-cleared.odb")),"cleared ODB")
    # Native producer source verifies every guide before and after ODB serialization.
    # This read-only gate preserves its complete guide record; it does not rerun ODB extraction.
    guide=regular(root,data+"stale-wire-original-guides.json")
    before=regular(root,data+"route-before-stale-wire-clear.tcl").read_bytes()
    after=regular(root,data+"route-after-stale-wire-clear.tcl").read_bytes()
    p.exact(mutation["route_before"],p.pin(before),"original route text pin")
    p.exact(mutation["route_after"],p.pin(after),"changed route text pin")
    exact_bytes(stale.route_text(before.decode(),WORK).encode(),after,"only approved route input substitution")
    p.exact(decode(root,data+"saved-diode-routing-result.json"),inner["saved_diode_routing_result"],"actual native physical verdict")
    p.exact(pin(regular(root,"work/bulk-postdrt-antenna/final-measured.odb")),
      inner["saved_diode_routing_result"]["candidate"],"actual final candidate")
    return dict(status="PASS_SOURCE_BOUND_STALE_WIRE_ROUTING_READBACK",
      original_failed_workflow_unchanged=True,native_rerun=False,
      current_scope_only=True,command_count=len(inner["commands"]),clear_nets=608,
      complete_guide_record=pin(guide),original_validator_sha256=PLAN_SHA,
      native_result=result,**p.FLAGS)
