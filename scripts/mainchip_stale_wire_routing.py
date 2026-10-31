"""Source-bound stale-wire removal and exact current-census clock adapter."""
import ast,copy,hashlib,inspect,json,types
from pathlib import Path
import mainchip_bulk_postdrt_antenna as p

ROOT=Path(__file__).resolve().parent.parent
MANIFEST="scripts/mainchip-stale-wire-routing-pins.json"
INNER="scripts/mainchip_stale_wire_routing_inner.py"
OLD_INNER="scripts/mainchip_saved_diode_routing_inner.py"
NATIVE="scripts/mainchip_stale_wire_routing_native.py"
HOST="scripts/cloud_mainchip_stale_wire_routing.py"
GATE_SHA="ed5669d48a87ce30d00fc3213792f7f57001651d4907d9367ca2b705f945c74b"
HOST_SHA="c817c771ac2d400789cc9718699357ee6d791d23e1c8c9afb7919673600a058e"
NEW=("scripts/mainchip_stale_wire_routing.py",INNER,NATIVE,HOST,
     "scripts/check_mainchip_stale_wire_routing.py")

def clone(fn,**updates):
    return types.FunctionType(fn.__code__,dict(fn.__globals__,**updates),
                              fn.__name__,fn.__defaults__,fn.__closure__)

def source_gate():
    import cloud_mainchip_saved_diode_routing as original
    inherited=original.source_gate()
    manifest=json.loads((ROOT/MANIFEST).read_bytes())
    p.require(manifest["schema"]=="mainchip-stale-wire-routing-v1","stale-wire manifest schema")
    p.require(manifest["scoped_routing_authorized"]is True and manifest["native_repair_authorized"]is False
      and manifest["diode_reconstruction_authorized"]is False,"only stale-wire routing")
    p.require(all(manifest[k]is False for k in p.FLAGS),"no final acceptance")
    p.require(set(inherited["files"])|{original.MANIFEST}|set(NEW)<=set(manifest["files"]),"complete source projection")
    for name,digest in inherited["files"].items():p.exact(manifest["files"][name],digest,"inherited source pin")
    for name,digest in manifest["files"].items():
        p.require(not Path(name).is_absolute() and ".."not in Path(name).parts,"source namespace")
        path=ROOT/name
        p.require(path.is_file() and not path.is_symlink(),"regular source")
        p.require(hashlib.sha256(path.read_bytes()).hexdigest()==digest,"source hash: "+name)
    return manifest

def clear_delta(before,after,admission):
    """Compare complete native snapshots; only owned encoded wires may disappear."""
    mutable=set(admission["mutable_nets"]);protected=set(admission["protected_nets"])
    p.require(mutable and len(mutable)==len(admission["mutable_nets"]),"unique mutable census")
    p.require(mutable==set(admission["attachments"].values()),"derived signal ownership")
    p.require(not mutable&protected,"no protected owner")
    p.exact(sorted(before),sorted(after),"complete snapshot keys")
    for key in before:
        if key not in ("nets","def_pin"):p.exact(after[key],before[key],"unchanged snapshot "+key)
    p.exact(sorted(after["nets"]),sorted(before["nets"]),"complete net names")
    p.require(mutable|protected<=set(before["nets"]),"known owned/protected nets")
    for name,old in before["nets"].items():
        new=after["nets"][name]
        if name not in mutable:p.exact(new,old,"unowned wire or net changed: "+name);continue
        p.require(old["identity"]["sigtype"]=="SIGNAL","only ordinary signals")
        p.require(old["encoded"]["wire_present"]is True and old["wire"]["opcode_count"]>0
          and old["encoded"]["metadata"]=="ROUTED" and set(old["encoded"]["paths"])=={"ROUTED"},"owned initial ROUTED wire")
        expected=copy.deepcopy(old)
        expected["encoded"].update(wire_present=False,paths=[])
        expected["wire"]=dict(pin=p.pin(p.encode(None)),opcode_count=0)
        p.exact(new,expected,"only complete stale-wire removal: "+name)
    return dict(complete=True,cleared_nets=sorted(mutable),all_nonmutable_exact=True,
                all_instances_and_guides_checked_separately=True,**p.FLAGS)

def route_text(raw,work):
    """Change exactly one input DB, retaining all router arguments and failure saving."""
    old="read_db "+str(work/"fixed.odb")
    # Native Tcl rendering quotes paths with braces.
    old="read_db {"+str(work/"fixed.odb")+"}"
    new="read_db {"+str(work/"stale-wire-cleared.odb")+"}"
    p.require(raw.count(old)==1 and raw.count("detailed_route ")==1,"single exact route input and invocation")
    p.require("stale-wire-cleared"not in raw,"fresh route input")
    result=raw.replace(old,new)
    p.require(result.replace(new,old)==raw,"only route input changed")
    return result

def gate_tree(raw):
    p.require(hashlib.sha256(raw).hexdigest()==GATE_SHA,"original clock gate source")
    tree=ast.parse(raw);expected=ast.parse("assert len(list(b.getInsts()))==153130").body[0]
    matches=[n for n in ast.walk(tree)if isinstance(n,ast.Assert)and ast.dump(n)==ast.dump(expected)]
    p.require(len(matches)==1,"one original instance census")
    matches[0].test.comparators[0]=ast.parse('{"before":153130,"after":154480}[label]',mode="eval").body
    return ast.fix_missing_locations(tree)

def gate_run_path(path,run_name):
    import mainchip_original_clock_restoration as clock
    p.require(path==str(clock.ROOT/clock.GATE)and run_name=="__main__","only exact original gate")
    raw=Path(path).read_bytes();tree=gate_tree(raw)
    namespace={"__name__":"__main__","__file__":path}
    exec(compile(tree,path,"exec"),namespace)
    return namespace

def gate_adapter(original):
    proxy=types.SimpleNamespace(**vars(original.__globals__["runpy"]))
    proxy.run_path=gate_run_path
    return clone(original,runpy=proxy)

def host_perform(original,**globals_updates):
    raw=Path(inspect.getsourcefile(original)).read_bytes()
    p.require(hashlib.sha256(raw).hexdigest()==HOST_SHA,"unchanged original host")
    tree=ast.parse(inspect.getsource(original));count=0
    for node in ast.walk(tree):
        if isinstance(node,ast.Constant)and node.value==OLD_INNER:node.value=INNER;count+=1
    p.require(count==3,"exact three inner-copy/identity path substitutions")
    scope=dict(original.__globals__,**globals_updates)
    exec(compile(ast.fix_missing_locations(tree),inspect.getsourcefile(original),"exec"),scope)
    return scope[original.__name__]

def hosted_argv(original,ctx,work,uid,gid):
    import os
    p.require(os.environ.get("GITHUB_ACTIONS")=="true","actual hosted context")
    argv=original(ctx,work,uid,gid)
    p.require(argv[:2]==["docker","create"]and not any("GITHUB_ACTIONS"in x for x in argv),"unmodified original container command")
    # Env is inherited from actual hosted context, never inferred inside native execution.
    return argv[:2]+["--env","GITHUB_ACTIONS="+os.environ["GITHUB_ACTIONS"]]+argv[2:]
