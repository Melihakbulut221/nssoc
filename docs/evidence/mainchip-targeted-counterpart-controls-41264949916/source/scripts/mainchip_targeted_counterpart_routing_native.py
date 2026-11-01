"""Cloud-only native adapter for a separately authenticated 828-net route scope.

The shipped manifest disables native execution. Activation and hosted lifecycle
qualification are separate prerequisites; this file is not a standalone runner.
"""
import gc
import hashlib
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, "/work/tail-source/scripts")
import odb
import mainchip_stale_wire_routing as inherited
import mainchip_saved_diode_routing_native as saved
import mainchip_bulk_postdrt_antenna_native as native
import mainchip_targeted_counterpart_routing as scope_core

p, n = native.p, native.n
WORK, DATA = saved.WORK, saved.DATA
MANIFEST = "scripts/mainchip-targeted-counterpart-routing-inputs.json"

def load_scope():
    inherited.source_gate()
    config = json.loads((p.ROOT / MANIFEST).read_bytes())
    p.require(config["native_execution_authorized"] is True, "target routing not activated")
    for name, pin in config["source_files"].items():
        path = p.ROOT / name
        p.require(path.is_file() and not path.is_symlink(), "regular target source")
        raw = path.read_bytes()
        p.require(len(raw) == pin["bytes"] and hashlib.sha256(raw).hexdigest() == pin["sha256"],
                  "target source pin: " + name)
    values = {}
    for name, pin in config["inputs"].items():
        path = p.ROOT / config["materialized_directory"] / name
        p.require(path.is_file() and not path.is_symlink(), "regular authenticated scope input")
        raw = path.read_bytes()
        p.require(len(raw) == pin["bytes"] and hashlib.sha256(raw).hexdigest() == pin["sha256"],
                  "scope input pin: " + name)
        values[name] = json.loads(raw)
    original_plan = json.loads((DATA / "insertion-plan.json").read_bytes())
    p.exact(original_plan, values["insertion_plan.json"], "complete original antenna plan")
    result = scope_core.build_scope(original_plan, values["counterparts.json"], values["summary.json"])
    return original_plan, result

def clear():
    plan, scope = load_scope()
    original, target = WORK / "fixed.odb", WORK / "stale-wire-cleared.odb"
    p.require(original.is_file() and not target.exists(), "fresh owned clear output")
    input_pin = native.fp(original)
    before = json.loads((DATA / "fixed-snapshot.json").read_bytes())
    p.require(len(before["instances"]) == 154480 and len(before["nets"]) == 143820,
              "complete current candidate census")
    guides = saved.read_guides(original)
    saved.save("targeted-routing-scope.json", scope)
    saved.save("stale-wire-original-guides.json", guides)
    db, block = n.load(original)
    report = dict(complete=False, removed=[], input=input_pin, scope=scope, **p.FLAGS)
    try:
        # Refuse an unsupported special/port signal before the first wire mutation.
        for name in scope["routing_nets"]:
            net = block.findNet(name)
            expected = "ROUTED" if name in scope["antenna_nets"] else "FIXED"
            p.require(net is not None and str(net.getSigType()) == "SIGNAL"
                      and not net.isSpecial() and not list(net.getSWires())
                      and not list(net.getBTerms()), "qualified ordinary ITerm-only signal")
            p.require(net.getWire() is not None and str(net.getWireType()) == expected,
                      "exact original live wire class")
        for name in scope["routing_nets"]:
            net = block.findNet(name)
            odb.dbWire.destroy(net.getWire())
            net.setWireType("ROUTED")
            p.require(net.getWire() is None and str(net.getWireType()) == "ROUTED",
                      "scoped live removal/class readback")
            report["removed"].append(name)
        p.exact(saved.guides(block), guides, "all guides unchanged in memory")
        odb.write_db(db, str(target))
        report["candidate"] = native.fp(target)
    except BaseException as exc:
        report["error"] = repr(exc)
        try:
            partial = WORK / "stale-wire-unadmitted-partial.odb"
            odb.write_db(db, str(partial))
            report["partial"] = native.fp(partial)
        except BaseException as secondary:
            report["partial_error"] = repr(secondary)
        raise
    finally:
        odb.dbDatabase.destroy(db)
        saved.save("stale-wire-mutation.json", report)
    p.exact(saved.read_guides(target), guides, "all guides unchanged after reload")
    del guides
    gc.collect()
    after = native.snapshot(target, WORK / "stale-wire-cleared.def", plan["protected_nets"])
    saved.save("stale-wire-cleared-snapshot.json", after)
    report["delta"] = scope_core.clear_delta(before, after, plan, scope, p.pin(p.encode(None)))
    p.exact(native.fp(original), input_pin, "unchanged fixed input")
    p.exact(report["removed"], scope["routing_nets"], "all 828 removals")
    original_plan, original_scope = load_scope()
    p.exact((plan, scope), (original_plan, original_scope), "scope and antenna plan unchanged")
    route = WORK / "route.tcl"
    raw = route.read_text()
    render = native.route_tcl(WORK, Path(os.environ["NSSOC_BULK_ENVIRONMENT"]),
                              Path(os.environ["NSSOC_BULK_ORIGINAL_TCL"]))
    p.exact(raw, render, "unchanged original router program")
    changed = inherited.route_text(raw, WORK)
    (DATA / "route-before-stale-wire-clear.tcl").write_text(raw)
    (DATA / "route-after-stale-wire-clear.tcl").write_text(changed)
    route.write_text(changed)
    report.update(complete=True, all_guides_unchanged=True,
                  route_before=p.pin(raw.encode()), route_after=p.pin(changed.encode()))
    saved.save("stale-wire-mutation.json", report)

def bind_phase(plan, scope):
    """Change routing ownership consumers, retaining physical algorithms exactly."""
    def checked(plan_argument):
        p.exact(plan_argument, plan, "original physical caller plan")
        return scope_core.observation_scope(plan, scope)
    proxy_p = SimpleNamespace(**vars(p))
    proxy_p.route_delta = lambda before, after, argument: (
        checked(argument) and scope_core.route_delta(before, after, plan, scope, p.same_base))
    proxy_router = SimpleNamespace(**vars(native.router))
    proxy_router.routing_delta = lambda before, after, owners: scope_core.scoped_def_delta(
        before, after, owners, plan, scope, native.router.routing_delta)
    proxy_n = SimpleNamespace(**vars(n))
    proxy_n.original_gate = inherited.gate_adapter(n.original_gate)
    # Both physical connectivity modes and every diode pin remain checked.
    def connectivity(path, argument, out):
        return native.connectivity(path, checked(argument), out)
    def routes(path, argument, out, label):
        return native.preserve_owned_routes(path, checked(argument), out, label)
    return inherited.clone(native.phase, p=proxy_p, router=proxy_router, n=proxy_n,
                           connectivity=connectivity, preserve_owned_routes=routes)

def main():
    plan, scope = load_scope()
    mode = os.environ.get("NSSOC_TARGETED_ROUTE_PHASE")
    if mode == "clear":
        p.source_guard()
        saved.verify_inputs()
        p.run_phase("stale-wire-clear", clear, saved.verify_inputs, saved.save)
        return
    p.require(mode == "audit" and os.environ.get("NSSOC_BULK_PHASE") in
              ("restored-audit", "failure-restored-audit"), "only exact restored audit callers")
    inherited.clone(native.main, phase=bind_phase(plan, scope))()

if __name__ == "__main__":
    main()
