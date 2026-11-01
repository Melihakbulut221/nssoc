"""Exact inherited hosted lifecycle with explicit 828-net source/result bindings."""
import ast
import copy
import hashlib
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import cloud_mainchip_saved_diode_routing as original
import mainchip_stale_wire_routing as inherited
import mainchip_targeted_counterpart_routing as core
import mainchip_exit_checked_command_evidence as command_evidence
import cloud_mainchip_original_clock_restoration as stream_contract

ROOT = original.ROOT
MANIFEST = "scripts/mainchip-targeted-counterpart-host-pins.json"
CONFIG = "scripts/mainchip-targeted-counterpart-routing-inputs.json"
INNER = "scripts/mainchip_targeted_counterpart_routing_inner.py"
CONTROL = "targeted-routing-controls/result.json"
REPORT = "bulk-postdrt-antenna/stale-wire-mutation.json"

def source_gate():
    prior = inherited.source_gate()
    manifest = json.loads((ROOT / MANIFEST).read_bytes())
    config = json.loads((ROOT / CONFIG).read_bytes())
    core.exact(manifest["schema"], "mainchip-targeted-counterpart-host-v1", "target host schema")
    core.require(type(manifest["native_execution_authorized"]) is bool, "typed native authority")
    core.require(manifest["native_execution_authorized"] is config["native_execution_authorized"],
                 "single explicit native authority")
    core.require(manifest["scoped_routing_authorized"] is True
                 and manifest["native_repair_authorized"] is False
                 and manifest["diode_reconstruction_authorized"] is False, "only scoped routing")
    for key in core.FLAGS:
        core.require(manifest[key] is False, "no physical/timing/PHY acceptance")
    required = set(prior["files"]) | {inherited.MANIFEST, CONFIG, __file_relative__()}
    required |= set(config["source_files"])
    required |= {config["materialized_directory"] + "/" + name for name in config["inputs"]}
    core.require(set(manifest["files"]) == required, "complete exact supplemental projection")
    for name, digest in prior["files"].items():
        core.exact(manifest["files"][name], digest, "original source pin unchanged")
    for name, digest in manifest["files"].items():
        core.require(not Path(name).is_absolute() and ".." not in Path(name).parts, "source namespace")
        path = ROOT / name
        core.require(path.is_file() and not path.is_symlink(), "regular projected source")
        core.exact(hashlib.sha256(path.read_bytes()).hexdigest(), digest, "source pin: " + name)
    return manifest

def __file_relative__():
    return "scripts/cloud_mainchip_targeted_counterpart_routing.py"

def authorize(manifest):
    core.require(manifest["native_execution_authorized"] is True, "targeted routing disabled")
    return original.authorize_native(manifest)

def inputs_scope():
    config = json.loads((ROOT / CONFIG).read_bytes())
    values = {}
    for name, pin in config["inputs"].items():
        raw = (ROOT / config["materialized_directory"] / name).read_bytes()
        core.require(len(raw) == pin["bytes"]
                     and hashlib.sha256(raw).hexdigest() == pin["sha256"], "actual scope input")
        values[name] = json.loads(raw)
    plan = values["insertion_plan.json"]
    scope = core.build_scope(plan, values["counterparts.json"], values["summary.json"])
    return config, plan, scope

def control_evidence(ctx):
    raw = (ROOT / CONTROL).read_bytes()
    value = json.loads(raw)
    core.exact(value, dict(tests=15, errors=0, failures=0, skips=0, source=ctx["source"],
                         run=ctx["run_id"], native_executed=False, **core.FLAGS),
               "all current target scope controls")
    host = json.loads((ROOT / "targeted-host-controls/result.json").read_bytes())
    core.require(host["source"] == ctx["source"] and host["run"] == ctx["run_id"]
                 and host["tests"] == 10 and host["failures"] == host["errors"] == host["skips"] == 0
                 and host["native_executed"] is False, "all current host adapter controls")
    # Original complete integration and 165 saved-diode predicates are retained
    # separately by the inherited perform() and original workflow admission.
    return dict(scope=value, host=host)

def accept_result(inner, mutation, config, plan, scope, original_accept):
    core.exact(mutation["scope"], scope, "actual authenticated native scope")
    core.exact(mutation["input"], config["seed_pins"]["fixed_odb"], "actual exact fixed ODB")
    core.exact(mutation["fixed_snapshot"], config["seed_pins"]["fixed_snapshot"], "actual exact fixed snapshot")
    core.require(mutation["complete"] is True and mutation["all_guides_unchanged"] is True,
                 "complete native clear and guide readback")
    core.exact(mutation["removed"], scope["routing_nets"], "actual all828 clear census")
    delta = mutation["delta"]
    core.require(delta["complete"] is True and delta["original_antenna_plan_preserved"] is True
                 and delta["all_nonmutable_exact"] is True, "complete native clear delta")
    core.exact(delta["cleared_nets"], scope["routing_nets"], "actual delta all828 census")
    core.require(delta["original_antenna_nets"] == 608 and delta["additional_counterpart_nets"] == 220,
                 "actual distinct antenna and counterpart counts")
    for result in (mutation, delta, scope):
        for key in core.FLAGS:
            core.require(result[key] is False, "no final acceptance")
    terminal = inner["stale_wire_clear"]
    core.require(terminal["phase"] == "stale-wire-clear" and terminal["complete"] is True
                 and terminal["error"] is None and terminal["terminal_errors"] == [],
                 "actual clear terminal")
    for key in core.FLAGS:
        core.require(terminal[key] is False, "no early terminal acceptance")
    commands = inner["commands"]
    indices = [i for i, row in enumerate(commands) if row["label"] == "bulk-postdrt-stale-wire-clear"]
    core.require(len(indices) == 1, "exactly one native clear command")
    i = indices[0]
    core.require(i + 1 < len(commands) and commands[i + 1]["label"] == "bulk-postdrt-route",
                 "clear immediately precedes original route")
    expected_argv = ["/work/engine/openroad", "-no_init", "-exit", "-python",
                     "/work/tail-source/scripts/mainchip_targeted_counterpart_routing_native.py"]
    row = commands[i]
    core.require(row["returncode"] == 0 and row["requested_timeout_seconds"] == 1200,
                 "clear command status and unchanged budget")
    core.exact(row["argv"], expected_argv, "exact clear command")
    core.exact(row["supervision_record"]["argv"], expected_argv, "actual supervised command")
    proof = command_evidence.validate(row["supervision_record"], 1200)
    core.exact(row["command_evidence"], proof, "actual original supervision evidence")
    # This projection removes exactly the separately validated added command.
    # Original phase, command-order, every command RC, physical and result gates
    # still see their complete unmodified original inputs.
    projected = copy.deepcopy(inner)
    projected["commands"] = commands[:i] + commands[i + 1:]
    result = original_accept(projected)
    return dict(result, targeted_routing_scope=scope, complete_targeted_clear=mutation,
                actual_complete_command_count=len(commands), actual_clear_calls=1)

def authenticate_clear_streams(inner, out):
    rows = [row for row in inner["commands"] if row["label"] == "bulk-postdrt-stale-wire-clear"]
    core.require(len(rows) == 1, "one clear stream owner")
    row = rows[0]
    trace = out / "bulk-postdrt-supervision"
    raw = (trace / "bulk-postdrt-stale-wire-clear.command.json").read_bytes()
    core.exact(original.p.pin(raw), row["command_record_pin"], "actual complete command bytes")
    core.exact(json.loads(raw), row["supervision_record"], "actual complete command object")
    stream_contract.terminal_stream(row["supervision_record"], trace, row["label"])
    return row["command_record_pin"]

def perform(ctx, proof, evidence):
    manifest = source_gate()
    authorize(manifest)  # before inherited acquisition/container/native work
    current_controls = control_evidence(ctx)
    original.f.write_new(evidence / "targeted-source-controls.json", original.f.encode(current_controls))
    config, plan, scope = inputs_scope()
    def accept(inner):
        # Inherited host owns exactly this run-scoped output directory.
        out = Path(os.environ["RUNNER_TEMP"]) / (original.GROUP + "-" + ctx["token"]) / "out"
        mutation = json.loads((out / REPORT).read_bytes())
        authenticate_clear_streams(inner, out)
        return accept_result(inner, mutation, config, plan, scope, original.plan.accept_native_result)
    proxy_plan = SimpleNamespace(**vars(original.plan))
    proxy_plan.accept_native_result = accept
    proxy_container = SimpleNamespace(**vars(original.c))
    proxy_container.create_argv = lambda *args: inherited.hosted_argv(original.c.create_argv, *args)
    # Reuse the exact original host AST adapter; only its three inner path
    # constants and explicit private globals change.
    adapter = inherited.clone(inherited.host_perform, INNER=INNER)
    bound = adapter(original.perform, source_gate=source_gate, MANIFEST=MANIFEST,
                    plan=proxy_plan, c=proxy_container, authorize_native=authorize)
    return bound(ctx, proof, evidence)

def main():
    return inherited.clone(original.main, perform=perform)()

if __name__ == "__main__":
    main()
