#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Map exact lane aligner and replay its frozen port oracle and real RTL faults."""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import time
from types import SimpleNamespace

from check_pcie_integrity_native import LIB_SHA, MODEL_SHA, quote

ROOT = Path(__file__).resolve().parents[1]
TOP = "soc_pcie_gen3_lane_align_v1"
RTL = ROOT / "hw/soc/rtl/pcie" / (TOP + ".v")
TEST = ROOT / "sw/tests/test_pcie_gen3_lane_align_v1.py"
RTL_SHA = "e59b8b6a42c900eca49020ea3b5008d55a993650cc44fc673a6e28fc6068fadd"
TEST_SHA = "185078582ce8d56a31552302c4b336b302cc934e5526c6d4acc352a7570f5de6"
FLOOR = 528 * 1024**2


def pin(path):
    with Path(path).open("rb") as stream:
        return dict(
            bytes=Path(path).stat().st_size,
            sha256=hashlib.file_digest(stream, "sha256").hexdigest(),
        )


def atomic(path, value):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, indent=2) + "\n")
    temp.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("out", "tools", "liberty", "models"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    args.out, args.tools, args.liberty, args.models = [
        p.resolve() for p in (args.out, args.tools, args.liberty, args.models)
    ]
    if args.out.exists():
        parser.error("Fresh output required")
    if shutil.disk_usage("/dev/shm").free < 1024**3:
        parser.error("1GiB entry floor required")
    assert pin(RTL)["sha256"] == RTL_SHA and pin(TEST)["sha256"] == TEST_SHA
    assert (
        pin(args.liberty)["sha256"] == LIB_SHA
        and pin(args.models)["sha256"] == MODEL_SHA
    )
    args.out.mkdir(parents=True)
    inputs = [
        RTL,
        TEST,
        Path(__file__).resolve(),
        ROOT / "scripts/check_pcie_integrity_native.py",
        args.liberty,
        args.models,
    ]
    record = dict(
        status="RUNNING",
        source_pins={str(p): pin(p) for p in inputs},
        runtime={
            str(args.tools / n): pin(args.tools / n)
            for n in ("yosys", "iverilog", "vvp")
        },
        commands=[],
        cases=[],
        maps={},
        entry_free_bytes=shutil.disk_usage("/dev/shm").free,
        minimum_free_bytes=shutil.disk_usage("/dev/shm").free,
        entry_floor_bytes=1024**3,
        continuous_storage_floor_bytes=FLOOR,
        address_space_limit_bytes=2 * 1024**3,
        elapsed_watchdog_seconds=None,
        scope="Frozen single-lane fixed130 interface; same seven public-port cases and twelve actual HDL faults. Native SG13 functional replay at explicit4ns testbench clock with1ns observation offset; noSDF/physicalSTA/variableSKP/deskew/LTSSM/fullPCS claim.",
    )
    result = args.out / "result.json"

    def save():
        atomic(result, record)

    def limit():
        resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})

    env = {
        **os.environ,
        "TMPDIR": "/dev/shm",
        "YOSYS_MAX_THREADS": "1",
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }

    def execute(command, log, requested=None):
        row = dict(
            argv=list(map(str, command)),
            oracle_requested_argv=requested,
            log=str(log),
            status="LAUNCHING",
        )
        record["commands"].append(row)
        save()
        p = None
        try:
            with log.open("w") as stream:
                p = subprocess.Popen(
                    row["argv"],
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                    env=env,
                    start_new_session=True,
                    preexec_fn=limit,
                )
                row.update(pid=p.pid, process_group=p.pid, status="RUNNING")
                save()
                while p.poll() is None:
                    free = shutil.disk_usage("/dev/shm").free
                    record["minimum_free_bytes"] = min(
                        record["minimum_free_bytes"], free
                    )
                    if free < FLOOR:
                        raise RuntimeError("Shared storage floor breached")
                    time.sleep(0.2)
                p.wait()
                row.update(status="EXITED", returncode=p.returncode)
        except BaseException:
            if p is not None:
                # Failure/interruption only; diagnostic persistence must never
                # precede this unconditional whole-group kill/reap guarantee.
                try:
                    try:
                        os.killpg(p.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    time.sleep(5)
                finally:
                    try:
                        os.killpg(p.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    p.wait()
            raise
        finally:
            if log.exists():
                row["log_pin"] = pin(log)
            save()
        if p.returncode:
            raise RuntimeError("Native command failed: " + str(log))
        return subprocess.CompletedProcess(
            row["argv"], p.returncode, log.read_text(), ""
        )

    maps = {}

    def mapped(source):
        key = pin(source)["sha256"]
        if key in maps:
            return maps[key]
        out = args.out / "maps" / key[:16]
        out.mkdir(parents=True)
        recipe = (
            "read_liberty -lib "
            + quote(args.liberty)
            + "; read_verilog -sv "
            + quote(source)
            + "; hierarchy -check -top "
            + TOP
            + "; synth -top "
            + TOP
            + " -nofsm -noabc; dfflibmap -liberty "
            + quote(args.liberty)
            + "; abc -liberty "
            + quote(args.liberty)
            + "; clean; check -assert; stat -liberty "
            + quote(args.liberty)
            + "; write_json "
            + quote(out / "mapped.json")
            + "; write_verilog -noattr -noexpr "
            + quote(out / "mapped.v")
            + "\n"
        )
        (out / "map.ys").write_text(recipe)
        execute(
            [args.tools / "yosys", "-Q", "-T", "-s", out / "map.ys"], out / "map.log"
        )
        cells = json.loads((out / "mapped.json").read_text())["modules"][TOP]["cells"]
        if not cells or any(
            not c["type"].startswith("sg13g2_") for c in cells.values()
        ):
            raise RuntimeError("Incomplete actual SG13 cell mapping")
        record["maps"][key] = dict(
            source=str(source),
            source_pin=pin(source),
            mapped_cells=len(cells),
            outputs={
                str(p.relative_to(args.out)): pin(p)
                for p in out.iterdir()
                if p.is_file()
            },
        )
        maps[key] = out / "mapped.v"
        save()
        return maps[key]

    spec = importlib.util.spec_from_file_location("frozen_lane_oracle", TEST)
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)

    def native_run(command, **kwargs):
        requested = list(map(str, command))
        command = list(command)
        if Path(command[0]).name == "iverilog":
            source = Path(command[-2])
            bench = Path(command[-1])
            netlist = mapped(source)
            # Same stimulus/scoreboard, explicitly declared physical time unit.
            text = bench.read_text()
            assert text.startswith("module tb;")
            bench.write_text("`timescale 1ns/1ps\n" + text)
            command[-2] = str(netlist)
            command += [str(args.models), "-gspecify"]
            return execute(command, bench.parent / "native-compile.log", requested)
        if Path(command[0]).name != "vvp":
            raise RuntimeError("Unexpected oracle subprocess")
        return execute(
            command, Path(command[1]).parent / "native-simulation.log", requested
        )

    oracle.subprocess = SimpleNamespace(run=native_run)
    oracle.shutil = SimpleNamespace(
        which=lambda n: str(args.tools / n) if n in ("iverilog", "vvp") else None
    )
    try:
        save()
        for name, fn in oracle.CASES.items():
            root = args.out / "positive" / name
            fn(root)
            record["cases"].append(dict(name=name, role="positive", status="PASS"))
            save()
        for name, before, after, case in oracle.FAULTS:
            root = args.out / "fault" / name
            root.mkdir(parents=True)
            original = RTL.read_text()
            assert original.count(before) == 1
            source = root / "mutant.v"
            source.write_text(original.replace(before, after))
            try:
                oracle.CASES[case](root, source)
            except AssertionError as error:
                record["cases"].append(
                    dict(
                        name=name,
                        role="actual_hdl_fault",
                        status="REJECTED_BY_PUBLIC_PORT_ASSERTION",
                        reason=str(error),
                    )
                )
            else:
                raise RuntimeError("Fault falsely accepted: " + name)
            save()
        assert len(record["cases"]) == 19 and len(record["maps"]) == 13
        assert all(pin(Path(p)) == v for p, v in record["source_pins"].items())
        assert all(pin(Path(p)) == v for p, v in record["runtime"].items())
        record["status"] = "PASS_NATIVE_GEN3_FIXED130_LANE_ALIGNMENT"
    except BaseException as error:
        record.update(status="FAIL_RETAINED", error=repr(error))
        raise
    finally:
        record["outputs"] = {
            str(p.relative_to(args.out)): pin(p)
            for p in args.out.rglob("*")
            if p.is_file() and p != result and p.suffix != ".tmp"
        }
        save()


if __name__ == "__main__":
    main()
