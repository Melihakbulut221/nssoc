#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Separate 4 GiB compile/replay profile for the exact failed 2 GiB V5 map.

No synthesis, HDL, bench, model, timing-argument or acceptance-gate change.
Healthy compilation/simulation has no elapsed watchdog. Explicit cancellation
or either continuous resource floor terminates the owned process group.
"""

import argparse
import ast
import hashlib
import json
import lzma
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

from cocotb_results import count_results

ROOT = Path(__file__).resolve().parents[1]
BASE = Path("/dev/shm/nssoc-dllp-consumer-v5-native01")
BASE_RESULT_SHA = "16882e7a6859a2d6147704b79d0b25901283f1ea6dc6d06680ad13d98594a724"
GIB = 1024**3
ENTRY_MEMORY = 8 * GIB
ENTRY_SCRATCH = (13 * GIB + 9) // 10
RUN_MEMORY = 2 * GIB
RUN_SCRATCH = 528 * 1024**2
AS_LIMIT = 4 * GIB
PROFILE = "Separate4GiBAS/core0/oneCPU; entry8GiBMemAvailable+1.3GiBshm; continuous2GiBMemAvailable+528MiBshm; noelapsedwatchdog"
TEST_FILE = ROOT / "sw/tests/test_pcie_gen3_dllp_consumer_v5_4g_v1.py"


def pin(path):
    digest = hashlib.sha256()
    length = 0
    with Path(path).open("rb") as stream:
        while block := stream.read(1024**2):
            digest.update(block)
            length += len(block)
    return {"bytes": length, "sha256": digest.hexdigest()}


def memory_available():
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            key, number, unit = line.split()
            if unit != "kB":
                raise RuntimeError("Unexpected MemAvailable units")
            return int(number) * 1024
    raise RuntimeError("Missing MemAvailable")


def resource_snapshot():
    return dict(
        memory_available_bytes=memory_available(),
        scratch_free_bytes=shutil.disk_usage("/dev/shm").free,
    )


def check_resources(snapshot, entry=False):
    mem, scratch = (ENTRY_MEMORY, ENTRY_SCRATCH) if entry else (RUN_MEMORY, RUN_SCRATCH)
    if snapshot["memory_available_bytes"] < mem:
        raise RuntimeError("MemAvailable floor: " + str(mem))
    if snapshot["scratch_free_bytes"] < scratch:
        raise RuntimeError("Shared scratch floor: " + str(scratch))


def verify_pins(inventory):
    for name, expected in inventory.items():
        if pin(name) != expected:
            raise RuntimeError("Pinned input changed: " + name)


def baseline():
    if pin(BASE / "result.json")["sha256"] != BASE_RESULT_SHA:
        raise RuntimeError("Original 2 GiB failure record changed")
    old = json.loads((BASE / "result.json").read_text())
    if (
        old["status"] != "FAIL"
        or old["mapped_cells"] != 128490
        or old["expected_tests"] != 6
        or old["commands"][0]["returncode"] != 0
        or old["commands"][1]["returncode"] != 2
    ):
        raise RuntimeError("Wrong original failure/map contract")
    verify_pins(old["inputs"] | old["runtime"])
    verify_pins(
        {n: p for n, p in old["mapped_inputs"].items() if not n.endswith("mapped.json")}
    )
    # The inactive JSON was losslessly compressed only after full public
    # capsule/member readback. Verify its original bytes without restoring it.
    digest = hashlib.sha256()
    length = 0
    with lzma.open(BASE / "mapped.json.xz", "rb") as stream:
        while block := stream.read(1024**2):
            digest.update(block)
            length += len(block)
    expected = old["mapped_inputs"][str(BASE / "mapped.json")]
    if dict(bytes=length, sha256=digest.hexdigest()) != expected:
        raise RuntimeError("Compressed original mapping identity changed")
    bench = ROOT / "hw/soc/tb/cocotb/test_soc_pcie_gen3_dllp_consumer_v5.py"
    cases = [
        n.name
        for n in ast.parse(bench.read_text()).body
        if isinstance(n, ast.AsyncFunctionDef) and n.decorator_list
    ]
    if len(cases) != 6 or len(set(cases)) != 6:
        raise RuntimeError("Require all six frozen actual public-port cases")
    inventory = (
        old["inputs"]
        | old["runtime"]
        | {
            str(BASE / n): pin(BASE / n)
            for n in (
                "result.json",
                "mapped.v",
                "mapped.json.xz",
                "map.ys",
                "abc.script",
                "simulation.log",
                "map.log",
            )
        }
    )
    if "std::bad_alloc" not in (BASE / "simulation.log").read_text():
        raise RuntimeError("Missing preserved original compiler failure")
    return old, inventory, cases


def interrupted(signum, frame):
    raise KeyboardInterrupt("External process signal " + str(signum))


def validate_results(path, cases):
    actual = [
        case.attrib.get("name") for case in ET.parse(path).getroot().iter("testcase")
    ]
    if sorted(actual) != sorted(cases):
        raise RuntimeError("Actual frozen case identity mismatch")
    counts = dict(zip(("passed", "failed", "skipped"), count_results([path])))
    if counts != dict(passed=6, failed=0, skipped=0):
        raise RuntimeError("Wrong exact six-case disposition/count")
    return counts


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (AS_LIMIT, AS_LIMIT))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})


def execute(command, out, env, record, save):
    start = time.monotonic()
    minimum = resource_snapshot()
    check_resources(minimum, entry=True)
    with (out / "simulation.log").open("x") as log:
        child = subprocess.Popen(
            command,
            cwd=out,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            preexec_fn=limits,
        )
        try:
            record["active_group"] = child.pid
            save()
            while child.poll() is None:
                current = resource_snapshot()
                minimum = {k: min(v, current[k]) for k, v in minimum.items()}
                check_resources(current)
                time.sleep(0.2)
        except BaseException:
            # Evidence writes cannot interrupt the unconditional KILL/reap.
            # Kill the group even if its leader already exited after TERM.
            try:
                try:
                    os.killpg(child.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                time.sleep(5)
            finally:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                child.wait()
            raise
    code = child.wait()
    record.update(
        active_group=None,
        native_returncode=code,
        elapsed_s=time.monotonic() - start,
        minimum_resources=minimum,
    )
    save()
    if code:
        raise RuntimeError("Exact frozen native replay failed: " + str(code))


def main():
    signal.signal(signal.SIGTERM, interrupted)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 12):
        parser.error("Use the actual pinned cocotb Python3.12 runtime")
    old, before, cases = baseline()
    out = args.out.resolve()
    if out.exists():
        parser.error("Fresh output directory required")
    before |= {
        str(p.resolve()): pin(p)
        for p in (
            Path(__file__),
            TEST_FILE,
            ROOT / "scripts/cocotb_results.py",
            Path(sys.executable).resolve(),
        )
    }
    # Pin actual compiler binaries in addition to the original shell wrappers.
    oss = ROOT / "hw/soc/tools/oss-cad-suite"
    for name in ("libexec/iverilog", "lib/ivl/ivl", "lib/ivl/ivlpp", "lib/ivl/vvp.tgt"):
        file = oss / name
        if not file.is_file():
            raise RuntimeError("Required compiler runtime missing: " + str(file))
        before[str(file)] = pin(file)
    admission = resource_snapshot()
    check_resources(admission, entry=True)
    out.mkdir(parents=True)
    command = [
        arg.replace(str(BASE / "sim"), str(out / "sim")).replace(
            str(BASE / "results.xml"), str(out / "results.xml")
        )
        for arg in old["commands"][1]["argv"]
    ]
    # Exact original compile/model/bench command, only fresh output paths.
    if [
        arg.replace(str(out / "sim"), str(BASE / "sim")).replace(
            str(out / "results.xml"), str(BASE / "results.xml")
        )
        for arg in command
    ] != old["commands"][1]["argv"]:
        raise RuntimeError("Replay command bridge changed")
    env = dict(os.environ)
    for key in (
        "PYTHONPATH",
        "PYTHONHOME",
        "PYTHONEXECUTABLE",
        "COCOTB_TEST_FILTER",
        "COCOTB_TESTCASE",
    ):
        env.pop(key, None)
    env.update(YOSYS_MAX_THREADS="1", OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
    env["PATH"] = os.pathsep.join(
        [
            str(ROOT / "hw/soc/tools/cocotb-venv/bin"),
            str(BASE / "runtime"),
            env.get("PATH", ""),
        ]
    )
    record = dict(
        status="RUNNING",
        inputs=before,
        argv=command,
        baseline_result_sha256=BASE_RESULT_SHA,
        original_status=old["status"],
        original_error=old["error"],
        original_resource_contract=old["resource_contract"],
        resource_contract=PROFILE,
        admission=admission,
        mapped_cells=old["mapped_cells"],
        synthesis_performed=False,
        expected_cases=cases,
        expected_tests=6,
        scope="Different compiler resource profile only; no logic/protocol/physical-timing gate changed or physical acceptance implied.",
    )

    def save():
        temp = out / "result.tmp"
        temp.write_text(json.dumps(record, indent=2) + "\n")
        temp.replace(out / "result.json")

    save()
    try:
        verify_pins(before)
        execute(command, out, env, record, save)
        verify_pins(before)
        counts = validate_results(out / "results.xml", cases)
        record["tests"] = counts
        if "Unexpected sys.executable" in (out / "simulation.log").read_text():
            raise RuntimeError("Embedded Python identity mismatch")
        record["status"] = "PASS_NATIVE_IHP_V5_SEPARATE_4G_PROFILE"
    except BaseException as error:
        record.update(status="FAIL", error=repr(error))
        raise
    finally:
        record["outputs"] = {
            str(p.relative_to(out)): pin(p)
            for p in out.rglob("*")
            if p.is_file() and p.name not in ("result.json", "result.tmp")
        }
        save()


if __name__ == "__main__":
    main()
