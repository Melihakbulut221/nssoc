#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Versioned observation control; frozen producer and original failed test stay intact."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import time

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import characterize_pcie_clock_trim_stream_v1 as method  # noqa: E402

METHOD_SHA = "9f405eaf9c68ed7237c06bfd0e81a25631a1417b74efd6395562086baf060982"
ARCHIVED_TEST = (
    ROOT
    / "hw/soc/pcie-evidence/20261004-framing-and-native-bank/prior-tests/stream-v1-original.py.txt"
)
TEST_SHA = "660131b8022474f8bc949b69fda2a67e86bad84ac75ebab4b18ba5f987a87dc9"


def pin(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def identity(pid):
    try:
        text = Path("/proc", str(pid), "stat").read_text()
    except FileNotFoundError:
        return None
    fields = text.rsplit(") ", 1)[1].split()
    return dict(
        pid=pid, state=fields[0], start_ticks=fields[19], process_group=int(fields[2])
    )


def control(root, leader_exits_first):
    root = Path(root)
    root.mkdir()
    require = method.require
    require(
        pin(method.__file__) == METHOD_SHA and pin(ARCHIVED_TEST) == TEST_SHA,
        "Frozen bytes unchanged",
    )
    script = """#!/usr/bin/python3
import json,os,pathlib,signal,time
signal.signal(signal.SIGTERM,signal.SIG_IGN)
"""
    if leader_exits_first:
        script += """pid=os.fork()
if pid:
 pathlib.Path('descendant-pid').write_text(str(pid))
 time.sleep(.08)
 raise SystemExit(0)
"""
    script += """pid=os.getpid()
fields=pathlib.Path('/proc',str(pid),'stat').read_text().rsplit(') ',1)[1].split()
deadline=time.monotonic()+DELAY
pathlib.Path('armed.json').write_text(json.dumps(dict(pid=pid,start_ticks=fields[19],process_group=os.getpgrp(),deadline_monotonic=deadline)))
with open('stream.fifo','wb',buffering=0) as stream:stream.write(b'x')
while time.monotonic()<deadline:time.sleep(.002)
pathlib.Path('late-write').write_text('UNSAFE: child ran beyond its failure cleanup')
""".replace("DELAY", "7.0")
    runtime = root / "writer"
    runtime.write_text(script)
    runtime.chmod(0o700)
    readback = {}

    def fail(stream):
        require(stream.read(1) == b"x", "Actual FIFO byte observed")
        armed = json.loads((root / "armed.json").read_text())
        actual = identity(armed["pid"])
        require(
            actual is not None and actual["start_ticks"] == armed["start_ticks"],
            "Exact original process identity",
        )
        readback.update(armed=armed, before_failure=actual)
        if leader_exits_first:
            time.sleep(0.12)
        raise ValueError("Explicit versioned failure control")

    started = time.monotonic()
    try:
        with pytest.raises(ValueError, match="Explicit versioned failure control"):
            method.native_wait(runtime, root, root / "run.log", fail)
        returned = time.monotonic()
        require(returned - started < 6.5, "Bounded native failure cleanup")
        if not leader_exits_first:
            require(
                returned - started >= 5, "Actual TERM-ignoring child reached KILL grace"
            )
        lifecycle = json.loads((root / "native-process.json").read_text())
        require(
            lifecycle["status"] == "EXITED"
            and lifecycle["capture_error"]
            and lifecycle["elapsed_watchdog_seconds"] is None,
            "Completed bounded failure cleanup",
        )
        armed = readback["armed"]
        observations = []
        end = returned + 1.0
        while True:
            observed = identity(armed["pid"])
            now = time.monotonic()
            observations.append(
                dict(after_return_seconds=now - returned, identity=observed)
            )
            gone = observed is None or observed["start_ticks"] != armed["start_ticks"]
            stopped = gone or observed["state"] == "Z"
            if stopped or now >= end:
                break
            time.sleep(0.005)
        require(
            stopped, "Exact child still executable after bounded kernel observation"
        )
        # This test waits past the real child's own monotonic latewrite deadline.
        remaining = armed["deadline_monotonic"] + 0.05 - time.monotonic()
        if remaining > 0:
            time.sleep(remaining)
        checked = time.monotonic()
        require(
            checked >= armed["deadline_monotonic"]
            and not (root / "late-write").exists(),
            "No latewrite after scheduled child action",
        )
        require(identity(lifecycle["pid"]) is None, "Direct child actually reaped")
        require(
            pin(method.__file__) == METHOD_SHA and pin(ARCHIVED_TEST) == TEST_SHA,
            "Frozen sources remained unchanged",
        )
        result = dict(
            status="PASS_VERSIONED_KERNEL_OBSERVATION",
            leader_exits_first=leader_exits_first,
            retained_identity=readback,
            bounded_observations=observations,
            observation_bound_seconds=1.0,
            cleanup_elapsed_seconds=returned - started,
            marker_deadline_monotonic=armed["deadline_monotonic"],
            marker_checked_monotonic=checked,
            marker_absent=True,
            exact_child_nonexecuting=True,
            original_test_superseded=False,
            lifecycle=lifecycle,
        )
        result["outputs"] = {p.name: pin(p) for p in root.iterdir() if p.is_file()}
        (root / "control.json").write_text(json.dumps(result, indent=2) + "\n")
        return result
    finally:
        if (root / "native-process.json").exists():
            group = json.loads((root / "native-process.json").read_text()).get(
                "process_group"
            )
            if group:
                try:
                    os.killpg(group, signal.SIGKILL)
                except ProcessLookupError:
                    pass


@pytest.mark.parametrize("leader_exits_first", [False, True])
def test_exact_child_stops_and_cannot_execute_late_marker(tmp_path, leader_exits_first):
    result = control(tmp_path / "control", leader_exits_first)
    assert result["status"] == "PASS_VERSIONED_KERNEL_OBSERVATION"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = args.out.resolve()
    method.require(
        not root.exists() and root.is_relative_to(Path("/dev/shm")),
        "Fresh bounded RAM output",
    )
    root.mkdir()
    (root / "producer.py").write_bytes(Path(__file__).read_bytes())
    cases = [
        control(root / name, flag)
        for name, flag in [("ignores-term", False), ("exited-leader", True)]
    ]
    result = dict(
        status="PASS_VERSIONED_SHUTDOWN_CONTROLS",
        source_sha256=pin(__file__),
        frozen_method_sha256=METHOD_SHA,
        frozen_original_test_sha256=TEST_SHA,
        cases=cases,
        no_spice_execution=True,
        original_aggregate_failure_preserved=True,
    )
    (root / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(result["status"], pin(root / "result.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
