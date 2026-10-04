#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Port-only active x4 receive framing; optional external mapped-netlist replay."""

import argparse
import ast
import json
from pathlib import Path

from check_pcie_gen3_framer import execute_command
from check_pcie_integrity import pin, tool_environment
from check_pcie_integrity_native import MODEL_SHA
from cocotb_results import count_results

ROOT = Path(__file__).resolve().parents[1]
TOP = "soc_pcie_gen3_framer_rx"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--iverilog-dir", type=Path, required=True)
    p.add_argument("--rtl", type=Path)
    p.add_argument("--netlist", type=Path)
    p.add_argument("--models", type=Path)
    p.add_argument("--max-encoded-bytes", type=int, default=150)
    p.add_argument("--command-timeout-seconds", type=float)
    a = p.parse_args()
    if not 18 <= a.max_encoded_bytes <= 4118:
        p.error("Capacity18..4118")
    if a.command_timeout_seconds is not None and a.command_timeout_seconds <= 0:
        p.error("Explicit watchdog must be positive")
    if (a.netlist is None) != (a.models is None) or (a.netlist and a.rtl):
        p.error(
            "External native replay requires netlist+models and forbids RTL override"
        )
    out = a.out.resolve()
    if out.exists():
        p.error("Fresh output required")
    rtl = (a.rtl or ROOT / "hw/soc/rtl/pcie" / f"{TOP}.v").resolve()
    bench = ROOT / "hw/soc/tb/cocotb" / f"test_{TOP}.py"
    makefile = bench.with_name("Makefile." + TOP)
    files = [
        rtl,
        bench,
        makefile,
        Path(__file__).resolve(),
        ROOT / "scripts/check_pcie_gen3_framer.py",
        ROOT / "scripts/check_pcie_integrity.py",
        ROOT / "scripts/check_pcie_integrity_native.py",
        ROOT / "scripts/cocotb_results.py",
    ]
    sources = [rtl]
    if a.netlist:
        if pin(a.models)["sha256"] != MODEL_SHA:
            p.error("Exact unmodified IHP model required")
        sources = [a.netlist.resolve(), a.models.resolve()]
        files += sources
    expected = sum(
        isinstance(n, ast.AsyncFunctionDef) and bool(n.decorator_list)
        for n in ast.parse(bench.read_text()).body
    )
    assert expected > 0
    before = {str(f): pin(f) for f in files}
    runtime = {
        str((a.iverilog_dir / t).resolve()): pin((a.iverilog_dir / t).resolve())
        for t in ("iverilog", "vvp")
    }
    out.mkdir(parents=True)
    record = dict(
        status="RUNNING",
        top=TOP,
        mode="external_native" if a.netlist else "rtl",
        max_encoded_bytes=a.max_encoded_bytes,
        inputs=before,
        runtime=runtime,
        expected_tests=expected,
        address_space_limit_bytes=2 * 1024**3,
        command_timeout_seconds=a.command_timeout_seconds,
        scope="Already aligned/deskewed/descrambled active x4 Data Stream; full packet quarantine, STP/SDP/EDB/IDL/EDS. External stream start/abort. No LCRC/CRC16 checks, OS processing, training, LTSSM, PMA or line-rate ingress claim.",
    )

    def save():
        (out / "result.json").write_text(json.dumps(record, indent=2) + "\n")

    try:
        save()
        command = [
            "make",
            "-f",
            str(makefile),
            "--no-print-directory",
            "VERILOG_SOURCES=" + " ".join(map(str, sources)),
            "SIM_BUILD=" + str(out / "sim"),
            "COCOTB_RESULTS_FILE=" + str(out / "results.xml"),
            "PCIE_NATIVE=" + str(int(a.netlist is not None)),
            "PCIE_FRAMER_CAPACITY=" + str(a.max_encoded_bytes),
        ]
        record["command"] = command
        record["returncode"] = execute_command(
            command,
            out / "simulation.log",
            tool_environment(a.iverilog_dir),
            a.command_timeout_seconds,
        )
        if record["returncode"]:
            raise RuntimeError("Actual port simulation failed")
        counts = count_results([out / "results.xml"])
        record["tests"] = dict(zip(("passed", "failed", "skipped"), counts))
        if counts != (expected, 0, 0):
            raise ValueError("Missing/failed/skipped port cases")
        if before != {str(f): pin(f) for f in files}:
            raise ValueError("Inputs changed during capture")
        if runtime != {f: pin(f) for f in runtime}:
            raise ValueError("Runtime changed during capture")
        record["status"] = "PASS_PORT_ONLY_GEN3_RECEIVE_FRAMING"
    except BaseException as error:
        record.update(status="FAIL", error=repr(error))
        raise
    finally:
        record["outputs"] = {
            f: pin(out / f)
            for f in ("simulation.log", "results.xml")
            if (out / f).is_file()
        }
        save()
    print(record["status"], record["tests"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
