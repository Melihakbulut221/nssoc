#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Map the frozen SDS cohort deskew and each fault, then replay all 30 port cases with a proven fixed-parameter bench adapter."""

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
TOP = "soc_pcie_gen3_sds_deskew_v1"
RTL = ROOT / "hw/soc/rtl/pcie" / (TOP + ".v")
TEST = ROOT / "sw/tests/test_pcie_gen3_sds_deskew_v1.py"
RTL_SHA = "0690fd9c8a594fb413e61ec9f24b2ba0da4fb35c421e8f53c506c290e2fc3e89"
TEST_SHA = "563283239973bc146567d4b209b817c969836a1f4a3c3fe56e4cbf79214ae025"
FLOOR = 528 * 1024**2
OWNED_LIMIT = 320 * 1024**2


MUTANT_DIAGNOSTICS = {
    "lane_order": "DATA_ORDINAL_OR_LANE_MISMATCH",
    "partial_data_group": "DATA_ORDINAL_OR_LANE_MISMATCH",
    "lost_data_stall": "STALLED_DATA_CONSUMED",
    "lost_skp_stall": "SKP_BACKPRESSURE_LOST",
    "truncated_skp": "SKP_RECORD_CORRUPTION",
    "no_sds_timeout": "BOUNDED_COHORT_DID_NOT_COMPLETE",
    "first_skp_permitted": "FAULT_DETECTED_TOO_LATE",
    "missing_upstream_abort": "FAULT_WAS_NOT_DETECTED",
    "rearm_ignored": "FAULT_WAS_NOT_DETECTED",
    "sds_without_alignment": "FAULT_WAS_NOT_DETECTED",
}


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


FAILED_RESULT_SHA = "d94ed1c37a8c394f63ebe02d7da040aa7af3cedc3b391f2a304d385a70c095e9"


def adapt_fixed_parameter_bench(text, module):
    override = "#(.MAX_SKEW_CYCLES(64))"
    value = module.get("parameter_default_values", {}).get("MAX_SKEW_CYCLES")
    if value != "00000000000000000000000001000000":
        raise ValueError("Native map must prove exact parameter64")
    if text.count(override) != 1 or not text.lstrip().startswith("module tb;"):
        raise ValueError("Exact frozen parameter64 bench required")
    return "`timescale 1ns/1ps\n" + text.replace(override, "")


def verify_reused_map(result_path, liberty, models):
    if pin(result_path)["sha256"] != FAILED_RESULT_SHA:
        raise ValueError("Exact preserved first failure required")
    prior = json.loads(result_path.read_text())
    if prior["status"] != "FAIL_RETAINED" or prior["cases"] or len(prior["maps"]) != 1:
        raise ValueError("Expected compile-only prior failure")
    for name, expected in prior["source_pins"].items():
        if pin(Path(name)) != expected:
            raise ValueError("Prior source changed: " + name)
    for path in (liberty, models):
        if pin(path) != prior["source_pins"][str(path)]:
            raise ValueError("Prior PDK changed")
    for name, expected in prior["runtime"].items():
        if pin(Path(name)) != expected:
            raise ValueError("Prior runtime changed: " + name)
    inputs = [result_path]
    for name, expected in prior["outputs"].items():
        path = result_path.parent / name
        if pin(path) != expected:
            raise ValueError("Prior output changed: " + name)
        inputs.append(path)
    original = prior["maps"][RTL_SHA]
    if original["source_pin"] != pin(RTL):
        raise ValueError("Prior map does not use exact RTL")
    map_root = result_path.parent / "maps" / RTL_SHA[:16]
    module = json.loads((map_root / "mapped.json").read_text())["modules"][TOP]
    if module["parameter_default_values"].get("MAX_SKEW_CYCLES") != "00000000000000000000000001000000":
        raise ValueError("Prior map parameter is not64")
    if not module["cells"] or any(not c["type"].startswith("sg13g2_") for c in module["cells"].values()):
        raise ValueError("Prior map is not exclusively SG13 cells")
    inputs.extend(Path(name) for name in prior["source_pins"])
    return prior, map_root, inputs


def main():
    signal.signal(signal.SIGTERM, interrupted)
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("out", "tools", "liberty", "models"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--reuse-map-result", type=Path)
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
        ROOT / "scripts/check_pcie_gen3_sds_deskew_native_v1.py",
        ROOT / "sw/tests/test_pcie_gen3_sds_deskew_native_v2.py",
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
        planned_retained_storage_bytes=160 * 1024**2,
        maximum_owned_bytes=0,
        cases=[],
        maps={},
        entry_free_bytes=shutil.disk_usage("/dev/shm").free,
        minimum_free_bytes=shutil.disk_usage("/dev/shm").free,
        entry_floor_bytes=1024**3,
        continuous_storage_floor_bytes=FLOOR,
        address_space_limit_bytes=2 * 1024**3,
        elapsed_watchdog_seconds=None,
        scope="Default64-cycle common-clock SDS cohort/DATA ordinal transport only: 20 public-port scenarios (3 positive and17 expected-fault) and10 independently mapped actual HDL mutants. Native SG13 functional replay at explicit4ns testbench clock and1ns observation; noSDF/physical timing/CDC/metastability/LTSSM/OS-aware descrambler/parity/ratecompensation/fullPCS claim.",
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

    if args.reuse_map_result is not None:
        prior_path = args.reuse_map_result.resolve()
        prior, prior_map, source_paths = verify_reused_map(prior_path, args.liberty, args.models)
        key = RTL_SHA
        target = args.out / "maps" / key[:16]
        target.mkdir(parents=True)
        for name in ("map.ys", "map.log", "mapped.json", "mapped.v"):
            source = prior_map / name
            shutil.copyfile(source, target / name)
            assert pin(source) == pin(target / name)
        record["source_pins"].update({str(p): pin(p) for p in source_paths})
        record["reused_original_map"] = dict(
            prior_result=str(prior_path), prior_pin=pin(prior_path),
            prior_status=prior["status"], map_files_identical=True, synthesis_repeated=False,
        )
        record["maps"][key] = dict(
            source=str(RTL), source_pin=pin(RTL),
            mapped_cells=prior["maps"][key]["mapped_cells"],
            reused_from=str(prior_map),
            outputs={str(p.relative_to(args.out)): pin(p) for p in target.iterdir()},
        )
        maps[key] = target / "mapped.v"
        save()

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
            oracle.test_actual_sds_cohort_and_faults(root, name)
            expected_fault = oracle.fixture(name)[2]
            record["cases"].append(dict(
                name=name, role="expected_fault_scenario" if expected_fault else "positive",
                status="PASS", native_exit=0,
            ))
            save()
        for name in oracle.MUTANTS:
            active_fault = name
            root = args.out / "fault" / name
            root.mkdir(parents=True)
            oracle.test_actual_hardware_fault_is_observable(root, name)
            record["cases"].append(dict(
                name=name, role="actual_hdl_fault",
                status="REJECTED_BY_SPECIFIC_NATIVE_FATAL", native_exit=1,
                reason=MUTANT_DIAGNOSTICS[name],
            ))
            save()
        active_fault = None
        assert len(record["cases"]) == 30 and len(record["maps"]) == 11
        assert len(record["closed_vvp_preservation"]) == 30
        assert all(pin(Path(p)) == v for p, v in record["source_pins"].items())
        assert all(pin(Path(p)) == v for p, v in record["runtime"].items())
        record["status"] = "PASS_NATIVE_GEN3_SDS_COHORT_DESKEW"
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
