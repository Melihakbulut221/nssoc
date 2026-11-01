"""Supplemental exact source and result bindings for an intermediate route."""
import hashlib
import json
import os
from pathlib import Path
import cloud_mainchip_targeted_counterpart_routing as prior
import mainchip_stale_wire_routing as inherited
import mainchip_bounded_route_stage as stage

ROOT = prior.ROOT
MANIFEST = "scripts/mainchip-bounded-route-host-pins.json"
INNER = "scripts/mainchip_bounded_route_stage_inner.py"
WORKFLOW = ".github/workflows/cloud-evidence-summary.yml"
NEW = {"scripts/mainchip_bounded_route_stage.py", INNER,
       "scripts/cloud_mainchip_bounded_route_stage.py",
       "scripts/check_mainchip_bounded_route_stage.py", "scripts/mainchip-bounded-route-baseline.tcl", WORKFLOW}

def source_gate():
    original = prior.source_gate()
    m = json.loads((ROOT / MANIFEST).read_bytes())
    stage.require(m["schema"] == "mainchip-bounded-route-host-v1", "stage source schema")
    stage.require(m["iterations"] == 8 and m["baseline_iterations"] == 64, "explicit stage policy")
    stage.require(set(m["files"]) == set(original["files"]) | {prior.MANIFEST} | NEW,
                  "complete exact stage source projection")
    for key in ("native_execution_authorized", "scoped_routing_authorized",
                "native_repair_authorized", "diode_reconstruction_authorized", *stage.FLAGS):
        stage.require(m[key] is original[key], "original authority and no signoff claims")
    for name, digest in original["files"].items():
        stage.require(m["files"][name] == digest, "original source pins unchanged")
    for name, digest in m["files"].items():
        path = ROOT / name
        stage.require(not Path(name).is_absolute() and ".." not in Path(name).parts
                      and path.is_file() and not path.is_symlink(), "regular safe projected source")
        stage.require(hashlib.sha256(path.read_bytes()).hexdigest() == digest, "source pin " + name)
    return m

def control_evidence(ctx):
    original = prior.control_evidence(ctx)
    value = json.loads((ROOT / "bounded-route-controls/result.json").read_bytes())
    stage.require(value["source"] == ctx["source"] and value["run"] == ctx["run_id"]
                  and value["tests"] == 12 and value["failures"] == value["errors"] == value["skips"] == 0
                  and value["native_executed"] is False, "complete current stage controls")
    stage.require(value["workflow"] == stage.pin((ROOT / WORKFLOW).read_bytes()), "actual workflow source")
    return dict(original=original, stage=value)

def authenticate_stage(inner, out):
    data = out / "bulk-postdrt-antenna"
    actual = json.loads((data / stage.REPORT).read_bytes())
    stage.require(actual == inner["bounded_route_stage"], "exact native stage report")
    stage.validate(actual)
    before = (data / "bounded-route-before.tcl").read_bytes()
    after = (data / "bounded-route-after.tcl").read_bytes()
    stage.require(stage.render(before) == after, "actual exact stage Tcl change")
    stage.require(stage.pin(before) == actual["original_program"]
                  and stage.pin(after) == actual["actual_program"], "actual Tcl pins")
    work = out / "work/bulk-postdrt-antenna"
    stage.require((work / "route.tcl").read_bytes() == after, "executed Tcl preserved")
    for name, value in actual["checkpoints"].items():
        stage.require(stage.file_pin(work / name) == value, "actual retained checkpoint " + name)
    return actual

def accept_result(inner, mutation, config, plan, scope, original_accept):
    out = Path(os.environ["RUNNER_TEMP"]) / (prior.original.GROUP + "-" +
          os.environ["GITHUB_RUN_ID"] + "-" + os.environ["GITHUB_RUN_ATTEMPT"]) / "out"
    actual = authenticate_stage(inner, out)
    result = prior.accept_result(inner, mutation, config, plan, scope, original_accept)
    return dict(result, bounded_route_stage=actual)

def perform(ctx, proof, evidence):
    bound = inherited.clone(prior.perform, source_gate=source_gate, MANIFEST=MANIFEST,
                            INNER=INNER, accept_result=accept_result, control_evidence=control_evidence)
    return bound(ctx, proof, evidence)

def main():
    return inherited.clone(prior.original.main, perform=perform)()

if __name__ == "__main__":
    main()
