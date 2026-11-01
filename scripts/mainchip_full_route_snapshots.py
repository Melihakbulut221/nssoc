"""Retain native iteration ODBs while preserving original full64 routing settings."""
import re
import mainchip_full_route_stage as original
import hashlib
import json
from pathlib import Path

ITERATIONS = 64
BASELINE_ITERATIONS = 64
BASELINE_TCL_SHA256 = "4769e146e1bf59e08fb4c08c436d1f0f285de4086f8c72974825305db6fa9a7b"
REPORT = "full-route-stage.json"
FILES = ("route-partial.def", "route-partial.odb", "routed-fixed.def", "routed-fixed.odb")
FLAGS = dict(physical_acceptance=False, timing_accepted=False, full_phy_accepted=False)
OLD = b"lappend drt_args -droute_end_iter $::env(DRT_OPT_ITERS)\n"
NEW = OLD

def require(ok, message):
    if not ok: raise AssertionError(message)

def pin(raw):
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())

def file_pin(path):
    require(path.is_file() and not path.is_symlink(), "regular native checkpoint")
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    require(path.stat().st_size > 0, "nonempty native checkpoint")
    return dict(bytes=path.stat().st_size, sha256=digest)

SNAPSHOT_MARKER = b'set drc_report_iter_step_arg ""\n'
SNAPSHOT_ENABLE = b'set ::env(DRT_SAVE_SNAPSHOTS) 1\n'
def render(raw):
    original.render(raw)
    require(raw.count(SNAPSHOT_MARKER)==1, "single original snapshot branch")
    changed=raw.replace(SNAPSHOT_MARKER,SNAPSHOT_ENABLE+SNAPSHOT_MARKER,1)
    require(changed.replace(SNAPSHOT_ENABLE,b"",1)==raw, "only snapshot enable changes")
    return changed

def snapshot_inventory(work):
    found={}
    for path in sorted(work.iterdir()):
        if not path.name.startswith("drt_iter"):continue
        match=re.fullmatch(r"drt_iter([0-9]+)\.odb",path.name)
        require(match is not None and 0<=int(match[1])<=64,"exact bounded native snapshot name")
        found[path.name]=dict(iteration=int(match[1]),**file_pin(path),reload_verified=False)
    return found

def execute_stage(report, runner, argv, seconds, work, data):
    require(seconds == 14400, "unchanged native supervision budget")
    require(argv == ["/work/engine/openroad", "-no_init", "-exit", str(work / "route.tcl")],
            "unchanged native command")
    require("full_route_stage" not in report, "exactly one bounded stage")
    require(not snapshot_inventory(work), "no stale iteration snapshots")
    for name in FILES:
        require(not (work / name).exists() and not (work / name).is_symlink(), "no stale checkpoint")
    raw = (work / "route.tcl").read_bytes()
    changed = render(raw)
    stage = dict(schema="mainchip-full-route-snapshots-v1", stage=1, iterations=ITERATIONS,
                 baseline_iterations=BASELINE_ITERATIONS, original_program=pin(raw),
                 actual_program=pin(changed), route_returned=False, checkpoints={},
                 complete=False, error=None, snapshots_enabled=True, snapshot_inventory={}, snapshot_reload_qualified=False, **FLAGS)
    report["full_route_stage"] = stage
    for name, content in (("full-route-before.tcl", raw), ("full-route-after.tcl", changed)):
        path = data / name
        with path.open("xb") as stream: stream.write(content)
    (work / "route.tcl").write_bytes(changed)
    try:
        value = runner(report, "bulk-postdrt-route", argv, seconds)
        stage["route_returned"] = True
        for name in FILES: stage["checkpoints"][name] = file_pin(work / name)
        require((work / "route.tcl").read_bytes() == changed, "actual stage Tcl unchanged")
        stage["complete"] = True
        return value
    except BaseException as error:
        stage["error"] = repr(error)
        raise
    finally:
        try: stage["snapshot_inventory"] = snapshot_inventory(work)
        except BaseException as error: stage["snapshot_inventory_error"] = repr(error)
        # Always retain available partial output. A failed route is never promoted.
        for name in FILES:
            path = work / name
            if name not in stage["checkpoints"] and path.is_file() and not path.is_symlink():
                try: stage["checkpoints"][name] = file_pin(path)
                except BaseException as error: stage.setdefault("checkpoint_errors", {})[name] = repr(error)
        with (data / REPORT).open("x") as stream:
            json.dump(stage, stream, sort_keys=True, indent=2)
            stream.write("\n")

def validate(stage):
    require(stage["schema"] == "mainchip-full-route-snapshots-v1" and stage["stage"] == 1,
            "explicit full64 invocation")
    require(stage["iterations"] == ITERATIONS and stage["baseline_iterations"] == BASELINE_ITERATIONS,
            "explicit stage and original bounds")
    require(stage["original_program"]["sha256"] == BASELINE_TCL_SHA256, "original actual Tcl")
    require(stage["route_returned"] is True and stage["complete"] is True and stage["error"] is None,
            "completed native route and checkpoint")
    require(set(stage["checkpoints"]) == set(FILES), "all four returned route outputs")
    for value in [stage["actual_program"], stage["original_program"], *stage["checkpoints"].values()]:
        require(type(value["bytes"]) is int and value["bytes"] > 0
                and len(value["sha256"]) == 64 and all(c in "0123456789abcdef" for c in value["sha256"]),
                "complete native output pins")
    require(stage["snapshots_enabled"] is True and stage["snapshot_reload_qualified"] is False, "snapshots are not qualified resume states")
    baseline = (Path(__file__).resolve().parent / "mainchip-bounded-route-baseline.tcl").read_bytes()
    require(stage["actual_program"] == pin(render(baseline)), "exact snapshot-only Tcl delta")
    require(not stage.get("snapshot_inventory_error"), "snapshot inventory errors")
    require(not stage.get("checkpoint_errors"), "no checkpoint errors")
    for key in FLAGS: require(stage[key] is False, "stage does not establish signoff")
    return stage
