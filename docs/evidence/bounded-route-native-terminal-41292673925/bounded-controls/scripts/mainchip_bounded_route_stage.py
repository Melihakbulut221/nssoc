"""An explicit intermediate routing stage; none of the signoff gates change."""
import hashlib
import json
from pathlib import Path

ITERATIONS = 8
BASELINE_ITERATIONS = 64
BASELINE_TCL_SHA256 = "4769e146e1bf59e08fb4c08c436d1f0f285de4086f8c72974825305db6fa9a7b"
REPORT = "bounded-route-stage.json"
FILES = ("route-partial.def", "route-partial.odb", "routed-fixed.def", "routed-fixed.odb")
FLAGS = dict(physical_acceptance=False, timing_accepted=False, full_phy_accepted=False)
OLD = b"lappend drt_args -droute_end_iter $::env(DRT_OPT_ITERS)\n"
NEW = b"lappend drt_args -droute_end_iter 8\n"

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

def render(raw):
    require(hashlib.sha256(raw).hexdigest() == BASELINE_TCL_SHA256, "exact qualified pre-stage Tcl")
    require(raw.count(OLD) == 1 and raw.count(b"detailed_route {*}$drt_args") == 1,
            "single exact router and bound")
    changed = raw.replace(OLD, NEW)
    require(changed.replace(NEW, OLD) == raw, "only explicit intermediate iteration bound changes")
    return changed

def execute_stage(report, runner, argv, seconds, work, data):
    require(seconds == 14400, "unchanged native supervision budget")
    require(argv == ["/work/engine/openroad", "-no_init", "-exit", str(work / "route.tcl")],
            "unchanged native command")
    require("bounded_route_stage" not in report, "exactly one bounded stage")
    for name in FILES:
        require(not (work / name).exists() and not (work / name).is_symlink(), "no stale checkpoint")
    raw = (work / "route.tcl").read_bytes()
    changed = render(raw)
    stage = dict(schema="mainchip-bounded-route-stage-v1", stage=1, iterations=ITERATIONS,
                 baseline_iterations=BASELINE_ITERATIONS, original_program=pin(raw),
                 actual_program=pin(changed), route_returned=False, checkpoints={},
                 complete=False, error=None, **FLAGS)
    report["bounded_route_stage"] = stage
    for name, content in (("bounded-route-before.tcl", raw), ("bounded-route-after.tcl", changed)):
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
    require(stage["schema"] == "mainchip-bounded-route-stage-v1" and stage["stage"] == 1,
            "explicit first stage")
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
    require(not stage.get("checkpoint_errors"), "no checkpoint errors")
    for key in FLAGS: require(stage[key] is False, "stage does not establish signoff")
    return stage
