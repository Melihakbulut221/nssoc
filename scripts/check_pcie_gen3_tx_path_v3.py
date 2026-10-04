#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Port-only RTL/native four-lane block scrambling connected to fixed130/32 transport."""

import argparse
import ast
import json
import os
import signal
import resource
import shutil
from pathlib import Path
import subprocess
import sys

from check_pcie_integrity import pin, tool_environment
from check_pcie_integrity_native import LIB_SHA, MODEL_SHA, quote
from cocotb_results import count_results

ROOT = Path(__file__).resolve().parents[1]
COMMON = ("soc_pcie_gen3_tx_path_v3", "soc_pcie_gen3_gearbox")


def execute_command(command, log_path, environment, timeout):
    """Wait for completion by default; explicit watchdogs own the whole child group."""

    def child_limits():
        resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))

    with log_path.open("x") as log:
        process = subprocess.Popen(
            command,
            cwd=log_path.parent,
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
            preexec_fn=child_limits,
            start_new_session=True,
        )
        try:
            return process.wait(timeout=timeout)
        except BaseException:
            # Killing make alone leaves vvp writing late results to failed captures.
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
            finally:
                # The leader may exit on TERM while a descendant ignores it.
                # Reap/kill the group even when the leader already returned.
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--top",
        choices=("soc_pcie_gen3_tx_path_v3",),
        default="soc_pcie_gen3_tx_path_v3",
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--iverilog-dir", type=Path)
    parser.add_argument("--rtl-dir", type=Path)
    parser.add_argument("--native", action="store_true")
    for name in ("yosys", "liberty", "models"):
        parser.add_argument("--" + name, type=Path)
    parser.add_argument(
        "--command-timeout-seconds",
        type=float,
        help="Optional watchdog; local runs wait for completion by default",
    )
    args = parser.parse_args()
    if args.command_timeout_seconds is not None and args.command_timeout_seconds <= 0:
        parser.error("Explicit watchdog must be positive")
    if args.native and (
        args.rtl_dir
        or any(
            getattr(args, n) is None
            for n in ("yosys", "liberty", "models", "iverilog_dir")
        )
    ):
        parser.error(
            "Native run requires explicit tools/libraries and forbids mutated RTL"
        )
    out = args.out.resolve()
    if out.exists():
        parser.error("Use a fresh output directory")
    rtl_dir = args.rtl_dir or ROOT / "hw/soc/rtl/pcie"
    rtl = [(rtl_dir / (name + ".v")).resolve() for name in COMMON]
    bench = ROOT / "hw/soc/tb/cocotb" / ("test_" + args.top + ".py")
    makefile = bench.with_name("Makefile." + args.top)
    files = [
        *rtl,
        bench,
        makefile,
        Path(__file__).resolve(),
        ROOT / "scripts/check_pcie_integrity.py",
        ROOT / "scripts/check_pcie_integrity_native.py",
        ROOT / "scripts/cocotb_results.py",
    ]
    expected = sum(
        isinstance(n, ast.AsyncFunctionDef) and bool(n.decorator_list)
        for n in ast.parse(bench.read_text()).body
    )
    if expected == 0:
        parser.error("No actual port cases")
    if args.native:
        args.liberty, args.models = args.liberty.resolve(), args.models.resolve()
        if (
            pin(args.liberty)["sha256"] != LIB_SHA
            or pin(args.models)["sha256"] != MODEL_SHA
        ):
            parser.error("Require the exact unmodified c4 SG13G2 library/model bytes")
        version = subprocess.check_output(
            [str(args.iverilog_dir.resolve() / "iverilog"), "-V"],
            stderr=subprocess.STDOUT,
            text=True,
        )
        import re

        match = re.search(r"Icarus Verilog version (\d+)", version)
        if not match or int(match[1]) < 13:
            parser.error("Native cell delayed ports require Icarus >=13")
        files += [args.liberty, args.models]
    runtime = {}
    for tool in ("iverilog", "vvp", "yosys"):
        candidate = (
            args.yosys
            if tool == "yosys" and args.native
            else args.iverilog_dir / tool
            if args.iverilog_dir and tool != "yosys"
            else None
        )
        if candidate is None and tool != "yosys":
            candidate = Path(shutil.which(tool) or tool)
        if candidate is not None:
            candidate = candidate.resolve()
            runtime[str(candidate)] = pin(candidate)
    before = {str(p): pin(p) for p in files}
    out.mkdir(parents=True)
    record = dict(
        status="RUNNING",
        top=args.top,
        inputs=before,
        expected_tests=expected,
        mode="native" if args.native else "rtl",
        commands=[],
        runtime=runtime,
        address_space_limit_bytes=2 * 1024**3,
        command_timeout_seconds=args.command_timeout_seconds,
        scope="Four logical lanes0..3,128bit payload blocks and unchanged headers through an actual fixed130/32 gearbox. Explicit per-byte advance/XOR and after-block reseed. Independent serial oracle, stalls and reset/flush. No ordered-set/DC-balance policy, variableSKP, lane assignment, LTSSM, PMA, CDC, SDF or physical timing qualification.",
    )

    def save():
        (out / "result.json").write_text(json.dumps(record, indent=2) + "\n")

    def execute(command, log_name, environment=None):
        returncode = execute_command(
            command, out / log_name, environment, args.command_timeout_seconds
        )
        record["commands"].append(
            dict(
                argv=command,
                returncode=returncode,
                log=log_name,
                log_pin=pin(out / log_name),
            )
        )
        save()
        if returncode:
            raise RuntimeError("Control failed: " + str(out / log_name))

    try:
        save()
        simulation_sources = rtl
        if args.native:
            script = (
                "read_liberty -lib "
                + quote(args.liberty)
                + "; read_verilog -sv "
                + " ".join(map(quote, rtl))
                + "; hierarchy -check -top "
                + args.top
                + "; flatten -noscopeinfo; synth -top "
                + args.top
                + " -noabc; "
                + "dfflibmap -liberty "
                + quote(args.liberty)
                + "; abc -liberty "
                + quote(args.liberty)
                + "; clean; check -assert; stat -liberty "
                + quote(args.liberty)
                + "; write_json "
                + quote(out / "mapped.json")
                + "; write_verilog -noattr -noexpr "
                + quote(out / "mapped.v")
            )
            (out / "map.ys").write_text(script + "\n")
            execute(
                [str(args.yosys.resolve()), "-Q", "-T", "-s", str(out / "map.ys")],
                "map.log",
            )
            cells = json.loads((out / "mapped.json").read_text())["modules"][args.top][
                "cells"
            ]
            if not cells or any(
                not c["type"].startswith("sg13g2_") for c in cells.values()
            ):
                raise ValueError("Unimplemented or non-IHP mapped cells")
            record["mapped_cells"] = len(cells)
            simulation_sources = [out / "mapped.v", args.models]
        execute(
            [
                "make",
                "-f",
                str(makefile),
                "--no-print-directory",
                "VERILOG_SOURCES=" + " ".join(map(str, simulation_sources)),
                "SIM_BUILD=" + str(out / "sim"),
                "COCOTB_RESULTS_FILE=" + str(out / "results.xml"),
                "PCIE_NATIVE=" + str(int(args.native)),
            ],
            "simulation.log",
            tool_environment(args.iverilog_dir),
        )
        counts = count_results([out / "results.xml"])
        record["tests"] = dict(zip(("passed", "failed", "skipped"), counts))
        if counts != (expected, 0, 0):
            raise ValueError("Missing, failed or skipped port cases")
        if before != {str(p): pin(p) for p in files}:
            raise ValueError("Sources changed during verification")
        if runtime != {p: pin(Path(p)) for p in runtime}:
            raise ValueError("Runtime changed during verification")
        record["status"] = "PASS_PORT_ONLY_PCIE_GEN3_TX_PATH_V3"
    except BaseException as error:
        record.update(status="FAIL", error=repr(error))
    finally:
        record["outputs"] = {
            str(p.relative_to(out)): pin(p)
            for p in out.rglob("*")
            if p.is_file()
            and p.name != "result.json"
            and "sim" not in p.relative_to(out).parts
        }
        save()
    print(record["status"], record.get("tests", record.get("error")))
    return int(record["status"] != "PASS_PORT_ONLY_PCIE_GEN3_TX_PATH_V3")


if __name__ == "__main__":
    raise SystemExit(main())
