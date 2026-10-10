#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Map the frozen SDS cohort deskew and each fault, then replay all 29 strict-policy port cases with a proven fixed-parameter bench adapter."""

import argparse
import hashlib
import gzip
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
TOP = "soc_pcie_gen3_sds_deskew_v2"
RTL = ROOT / "hw/soc/rtl/pcie" / (TOP + ".v")
TEST = ROOT / "sw/tests/test_pcie_gen3_sds_deskew_v2.py"
RTL_SHA = "bc3120f3f03af9e267449a72ebb77241a90b5fb008e74edfd14e154451a25ac7"
TEST_SHA = "bfccea93f5fa488fb4979cbd8ffaa3e6d1d393e855c444b0dd270866f3a5f222"
FLOOR = 528 * 1024**2
OWNED_LIMIT = 320 * 1024**2


MUTANT_DIAGNOSTICS = {'pending_bypassed': 'UNEXPECTED_STRICT_COHORT_FAULT', 'eds_ignored': 'UNEXPECTED_STRICT_COHORT_FAULT', 'lengths_unchecked': 'FAULT_NOT_DETECTED', 'decision_ownership_unchecked': 'FAULT_NOT_DETECTED', 'data_lane_reverse': 'DATA_ORDINAL_MISMATCH', 'data_backpressure_ignored': 'LOST_DATA_BACKPRESSURE', 'skp_backpressure_ignored': 'NONATOMIC_SKP', 'skp_truncated': 'CORRUPT_SKP_COHORT', 'eieos_kind_lost': 'WRONG_END_KIND', 'cohort_timeout_removed': 'BOUNDED_STRICT_COHORT_TIMEOUT'}


def validate_mutant_exit(completed, expected):
    """A specific testbench assertion is required, never an unrelated tool error."""
    fatals = [line for line in completed.stdout.splitlines() if line.startswith("FATAL:")]
    if (completed.returncode != 1 or len(fatals) != 1
            or not fatals[0].endswith(": " + expected)):
        raise RuntimeError("Wrong native mutant termination: " + repr(
            (completed.returncode, expected, fatals)
        ))


def pin(path):
    with Path(path).open("rb") as stream:
        return dict(
            bytes=Path(path).stat().st_size,
            sha256=hashlib.file_digest(stream, "sha256").hexdigest(),
        )


def directory_bytes(directory):
    return sum(p.stat().st_size for p in directory.rglob("*") if p.is_file())


def identity(path):
    s = path.stat()
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)


def compress_closed_vvp(path, resource_check=lambda: None):
    """Called only after this owned simulator exited and its stdout was closed."""
    if path.is_symlink() or not path.is_file() or path.suffix != ".vvp":
        raise ValueError("Only an owned regular completed VVP may be preserved")
    compressed = path.with_suffix(path.suffix + ".gz")
    temporary = path.with_suffix(path.suffix + ".gz.partial")
    if compressed.exists() or temporary.exists():
        raise ValueError("Fresh immutable compression paths required")
    before = identity(path)
    raw = pin(path)
    resource_check()
    with path.open("rb") as source, temporary.open("xb") as target:
        with gzip.GzipFile(
            fileobj=target, mode="wb", compresslevel=6, mtime=0
        ) as stream:
            while chunk := source.read(1024 * 1024):
                stream.write(chunk)
                resource_check()
    with gzip.open(temporary, "rb") as stream:
        digest = hashlib.sha256()
        size = 0
        while chunk := stream.read(1024 * 1024):
            size += len(chunk)
            digest.update(chunk)
            resource_check()
    recovered = dict(bytes=size, sha256=digest.hexdigest())
    if recovered != raw or identity(path) != before or pin(path) != raw:
        raise ValueError(
            "Closed VVP changed or compressed readback differs; raw retained"
        )
    temporary.rename(compressed)
    compressed_pin = pin(compressed)
    # Do not remove any changed path, even after successful gzip verification.
    if identity(path) != before or pin(path) != raw:
        raise ValueError("VVP changed before unlink; both copies retained")
    path.unlink()
    return dict(
        raw_path=str(path),
        raw=raw,
        compressed_path=str(compressed),
        compressed=compressed_pin,
        full_decompressed_readback=recovered,
        observed_closed_after_native_exit=True,
        raw_unlinked=True,
    )


def atomic(path, value):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, indent=2) + "\n")
    temp.replace(path)


def interrupted(signum, frame):
    """Turn external TERM into the existing unconditional group-cleanup path."""
    raise KeyboardInterrupt("External process signal " + str(signum))


def adapt_fixed_parameter_bench(text, module):
    override = "#(.MAX_SKEW_CYCLES(64))"
    value = module.get("parameter_default_values", {}).get("MAX_SKEW_CYCLES")
    if value != "00000000000000000000000001000000":
        raise ValueError("Native map must prove exact parameter64")
    if text.count(override) != 1 or not text.lstrip().startswith("module tb;"):
        raise ValueError("Exact frozen parameter64 bench required")
    return "`timescale 1ns/1ps\n" + text.replace(override, "")


def main():
    signal.signal(signal.SIGTERM, interrupted)
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
    assert pin(ROOT / "scripts/check_pcie_gen3_lane_align_native_v4.py")["sha256"] == (
        "8852893c22343d1a70cf9b842d53323e08c843f0c6754bc3d5da38ea1ac5e448"
    )
    assert pin(RTL)["sha256"] == RTL_SHA and pin(TEST)["sha256"] == TEST_SHA
    assert (
        pin(args.liberty)["sha256"] == LIB_SHA
        and pin(args.models)["sha256"] == MODEL_SHA
    )
    args.out.mkdir(parents=True)
    inputs = [
        RTL,
        TEST,
        ROOT / "scripts/check_pcie_gen3_sds_deskew_native_v2.py",
        ROOT / "sw/tests/test_pcie_gen3_sds_deskew_native_v3.py",
        Path(__file__).resolve(),
        ROOT / "scripts/check_pcie_gen3_lane_align_native_v4.py",
        ROOT / "scripts/check_pcie_integrity_native.py",
        args.liberty,
        args.models,
    ]
    record = dict(
        status="RUNNING",
        source_pins={str(p): pin(p) for p in inputs},
        runtime={
            str(args.tools / n): pin(args.tools / n)
            for n in (
                "yosys",
                "iverilog",
                "vvp",
                "../libexec/yosys",
                "../libexec/iverilog",
                "../libexec/vvp",
                "../lib/ivl/ivl",
                "../lib/ivl/ivlpp",
                "../lib/ivl/vvp.tgt",
            )
            if (args.tools / n).is_file()
        },
        commands=[],
        closed_vvp_preservation=[],
        bench_adaptations=[],
        owned_storage_limit_bytes=OWNED_LIMIT,
        planned_retained_storage_bytes=96 * 1024**2,
        maximum_owned_bytes=0,
        cases=[],
        maps={},
        entry_free_bytes=shutil.disk_usage("/dev/shm").free,
        minimum_free_bytes=shutil.disk_usage("/dev/shm").free,
        entry_floor_bytes=1024**3,
        continuous_storage_floor_bytes=FLOOR,
        address_space_limit_bytes=2 * 1024**3,
        elapsed_watchdog_seconds=None,
        scope="Default64-cycle strict SDS cohort with externally supplied four-cycle parser decisions: 19 public-port scenarios (4 positive and15 expected-fault) and10 independently mapped actual HDL mutants. Exact equal-length SKP, EDS decision ownership and EIOS/EIEOS ending behavior. Native SG13 functional replay at explicit4ns testbench clock and1ns observation; noSDF/physical timing/CDC/metastability/LTSSM/integrated parser/descrambler/parity/ratecompensation/fullPCS claim.",
    )
    result = args.out / "result.json"

    def save():
        atomic(result, record)

    def check_storage():
        owned = directory_bytes(args.out)
        record["maximum_owned_bytes"] = max(record["maximum_owned_bytes"], owned)
        if owned > OWNED_LIMIT:
            raise RuntimeError("Owned storage budget breached")
        free = shutil.disk_usage("/dev/shm").free
        record["minimum_free_bytes"] = min(record["minimum_free_bytes"], free)
        if free < FLOOR:
            raise RuntimeError("Shared storage floor breached")

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

    def execute(command, log, requested=None, allowed_exit_codes=(0,)):
        row = dict(
            argv=list(map(str, command)),
            oracle_requested_argv=requested,
            log=str(log),
            status="LAUNCHING",
            allowed_exit_codes=list(allowed_exit_codes),
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
                    check_storage()
                    time.sleep(0.2)
                p.wait()
                check_storage()
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
        if p.returncode not in allowed_exit_codes:
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

    spec = importlib.util.spec_from_file_location("frozen_deskew_oracle", TEST)
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)

    active_fault = None

    def native_run(command, **kwargs):
        requested = list(map(str, command))
        command = list(command)
        command[0] = str(args.tools / Path(command[0]).name)
        if Path(command[0]).name == "iverilog":
            source = Path(command[-2])
            bench = Path(command[-1])
            netlist = mapped(source)
            # The exact RTL oracle specializes64; native JSON proves that same
            # elaborated value, so remove only its absent Verilog parameter.
            text = bench.read_text()
            module = json.loads(netlist.with_suffix(".json").read_text())["modules"][TOP]
            adapted = adapt_fixed_parameter_bench(text, module)
            original_bench = bench.with_name("rtl-oracle-tb.v")
            original_bench.write_text(text)
            bench.write_text(adapted)
            record["bench_adaptations"].append(dict(
                path=str(bench), original=pin(original_bench), adapted=pin(bench),
                parameter="MAX_SKEW_CYCLES", elaborated_value=64,
                transformation="Prefix timescale1ns/1ps; remove exactly one literal parameter64 override",
            ))
            save()
            command[-2] = str(netlist)
            command += [str(args.models), "-gspecify"]
            return execute(command, bench.parent / "native-compile.log", requested)
        if Path(command[0]).name != "vvp":
            raise RuntimeError("Unexpected oracle subprocess")
        completed = execute(
            command, Path(command[1]).parent / "native-simulation.log", requested,
            allowed_exit_codes=(0, 1) if active_fault is not None else (0,),
        )
        if active_fault is not None:
            validate_mutant_exit(completed, MUTANT_DIAGNOSTICS[active_fault])
        # execute returned only after permitted native exit/reap and log close.
        # The oracle subsequently parses stdout; it never reuses this executable.
        preserved = compress_closed_vvp(Path(command[1]), check_storage)
        record["closed_vvp_preservation"].append(preserved)
        save()
        return completed

    oracle.subprocess = SimpleNamespace(run=native_run)
    oracle.shutil = SimpleNamespace(
        which=lambda n: str(args.tools / n) if n in ("iverilog", "vvp") else None
    )
    try:
        save()
        for name in oracle.CASES:
            root = args.out / "scenario" / name
            oracle.test_real_record_ports_and_parser_decisions(root, name)
            expected_fault = oracle.fixture(name)[3]
            record["cases"].append(dict(
                name=name, role="expected_fault_scenario" if expected_fault else "positive",
                status="PASS", native_exit=0,
            ))
            save()
        for name in oracle.MUTANTS:
            active_fault = name
            root = args.out / "fault" / name
            root.mkdir(parents=True)
            oracle.test_actual_policy_faults_are_observed(root, name)
            record["cases"].append(dict(
                name=name, role="actual_hdl_fault",
                status="REJECTED_BY_SPECIFIC_NATIVE_FATAL", native_exit=1,
                reason=MUTANT_DIAGNOSTICS[name],
            ))
            save()
        active_fault = None
        assert len(record["cases"]) == 29 and len(record["maps"]) == 11
        assert len(record["closed_vvp_preservation"]) == 29
        assert all(pin(Path(p)) == v for p, v in record["source_pins"].items())
        assert all(pin(Path(p)) == v for p, v in record["runtime"].items())
        record["status"] = "PASS_NATIVE_GEN3_STRICT_SDS_COHORT_DESKEW"
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
