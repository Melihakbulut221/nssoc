#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Wait for an identified physical producer, then check retained ECO equations.

Neither waiting nor the proof has an elapsed-time cutoff. A disappeared/reused
producer, changed input or failed flow is an error, never an accepted proof.
SRAM interiors, physical connectivity and timing are outside the proof scope.
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
READY = "ROUTED_DIAGNOSTIC_REQUIRES_NEW_EQUIVALENCE_DRC_LVS"
WAITING = {"WAITING_FOR_LOCAL_RESOURCES", "RUNNING_POSTROUTE_TIMING_REPAIR_CANDIDATE"}


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_pins(pins):
    if not pins:
        raise ValueError("Missing input hashes")
    for path, expected in pins.items():
        if digest(path) != expected:
            raise ValueError("Changed proof input: " + path)


def process_alive(pid, birth, proc=Path("/proc")):
    try:
        # comm may contain spaces or parentheses; stat fields start after it.
        fields = (proc / str(pid) / "stat").read_text().rsplit(")", 1)[1].split()
    except FileNotFoundError:
        return False
    return fields[19] == str(birth) and fields[0] not in {"Z", "X"}


def producer_state(producer, expected):
    # The existing producer writes this small JSON in place. Allow its write to
    # finish, but reject persistently malformed evidence instead of hiding it.
    for attempt in range(3):
        try:
            row = json.loads((producer / "result.json").read_text())
            break
        except json.JSONDecodeError:
            if attempt == 2:
                raise
            time.sleep(0.1)
    if row.get("input_sha256") != expected:
        raise ValueError("Producer input inventory changed")
    status = row.get("status")
    if status == READY:
        if row.get("returncode") != 0:
            raise ValueError("Completed producer has no successful exit")
        return row
    if status not in WAITING:
        raise ValueError("Physical producer failed or has unknown status: " + str(status))
    return None


def wait_for_producer(producer, expected, pid, birth, *, alive=process_alive, sleep=time.sleep):
    while True:
        row = producer_state(producer, expected)
        if row is not None:
            return row
        if not alive(pid, birth):
            # Cover the normal final-write/process-exit race before rejecting.
            row = producer_state(producer, expected)
            if row is not None:
                return row
            raise RuntimeError("Physical producer exited or PID was reused before completion")
        sleep(20)


def completed_inputs(producer):
    final = producer / "run/final/state.json"
    state = json.loads(final.read_text())
    after = Path(state["nl"]).resolve()
    if not after.is_relative_to((producer / "run").resolve()) or not after.is_file():
        raise ValueError("Final netlist is missing or outside this producer")
    resolved = producer / "run/resolved.json"
    cfg = json.loads(resolved.read_text())
    macros = cfg["MACROS"]
    if len(macros) != 2 or sum(len(v["instances"]) for v in macros.values()) != 32:
        raise ValueError("Expected two SRAM masters and 32 instances")
    libs = [Path(p) for p in cfg["LIB"]["nom_slow_1p08V_125C"] if "stdcell" in p]
    if len(libs) != 1 or not libs[0].is_file():
        raise ValueError("Expected one actual slow standard-cell Liberty")
    return after, libs[0], [producer / "result.json", final, after, libs[0], resolved]


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3,) * 2)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--producer", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--producer-pid", type=int, required=True)
    parser.add_argument("--producer-birth", required=True)
    args = parser.parse_args()
    producer, out = args.producer.resolve(), args.output.resolve()
    if not all(p.is_relative_to(ROOT / "hw/soc/out") for p in (producer, out)):
        parser.error("Producer and output must be inside this project's hw/soc/out")
    out.mkdir(parents=True, exist_ok=False)
    rec = dict(status="PREPARING", timing_accepted=False, manufacturing_approval=False,
               producer_pid=args.producer_pid, producer_birth=args.producer_birth,
               elapsed_timeout_seconds=None,
               scope="Retained digital equations and exact supported loads only; excludes SRAM interiors, timing, CDC, GDS connectivity, DRC/LVS and manufacturing acceptance.")

    def save():
        rec["recorded"] = datetime.now().astimezone().isoformat()
        temporary = out / "result.json.tmp"
        temporary.write_text(json.dumps(rec, indent=2) + "\n")
        temporary.replace(out / "result.json")

    try:
        save()
        app = ROOT / "hw/soc/tools/physical/librelane-3.0.5-x86_64.AppImage"
        original = ROOT / "hw/soc/out/timing-repair2-20260927/replacement-map-pipeline/soc_top.netlist.v"
        macro = ROOT / "hw/soc/out/external-review-20260919/route-closure-20260923/sram-chip-integration/independent_bb.v"
        checker = ROOT / "hw/soc/flow/check_eco_load_logic.py"
        expected = json.loads((producer / "result.json").read_text())["input_sha256"]
        verify_pins(expected)
        pins = dict(expected)
        for p in (Path(__file__), app, original, macro, checker,
                  checker.with_name("eco_logic.py"), checker.with_name("eco_logic_loads.py")):
            key, value = str(p.resolve()), digest(p)
            if key in pins and pins[key] != value:
                raise ValueError("Conflicting input hash: " + key)
            pins[key] = value
        rec.update(status="WAITING_FOR_COMPLETE_PIPELINE_PHYSICAL", input_sha256=pins)
        save()
        wait_for_producer(producer, expected, args.producer_pid, args.producer_birth)
        verify_pins(pins)
        after, lib, completed = completed_inputs(producer)
        pins.update({str(p): digest(p) for p in completed})
        cmd = [str(app), "python", str(checker), str(original), str(after),
               "--liberty", str(lib), "--macro-verilog", str(macro), "--output", str(out / "proof")]
        rec.update(status="RUNNING_COMPLETED_LAYOUT_EQUATION_CHECK", command=cmd)
        save()
        with (out / "run.log").open("x") as stream:
            child = subprocess.Popen(cmd, stdout=stream, stderr=subprocess.STDOUT, preexec_fn=limits)
            rec["child_pid"] = child.pid
            save()
            code = child.wait()
        rec["returncode"] = code
        if code:
            raise RuntimeError("Equation check failed; retained diagnostics are not waived")
        proof_path = out / "proof/result.json"
        proof = json.loads(proof_path.read_text())
        if proof.get("status") != "PASS within scope":
            raise ValueError("Equation proof did not pass")
        verify_pins(pins)
        rec.update(status="PASS_COMPLETED_PIPELINE_EQUATIONS_WITHIN_SCOPE",
                   proof_sha256=digest(proof_path), proof=proof)
        save()
        return 0
    except Exception as exc:
        rec.update(status="ERROR", error=repr(exc))
        save()
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
