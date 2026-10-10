#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent serialized-word and packet tests of the elastic x4 duplex seam."""

import argparse
import ast
import json
from pathlib import Path
import shutil

from check_pcie_gen3_framer import execute_command
from check_pcie_integrity import pin, tool_environment
from check_pcie_integrity_native import MODEL_SHA
from cocotb_results import count_results

ROOT = Path(__file__).resolve().parents[1]
TOP = "soc_pcie_gen3_packet_duplex"
MODULES = (
    "soc_pcie_gen3_stp",
    "soc_pcie_gen3_framer_tx",
    "soc_pcie_gen3_packet_tx_path",
    "soc_pcie_gen3_tx_path_v3",
    "soc_pcie_gen3_gearbox",
    "soc_pcie_gen3_scrambler",
    "soc_pcie_gen3_framer_rx",
    "soc_pcie_gen3_packet_rx_path",
    TOP,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--iverilog-dir", type=Path)
    parser.add_argument("--rtl-dir", type=Path)
    parser.add_argument("--netlist", type=Path)
    parser.add_argument("--models", type=Path)
    parser.add_argument("--command-timeout-seconds", type=float)
    args = parser.parse_args()
    if (args.netlist is None) != (args.models is None) or (
        args.netlist and args.rtl_dir
    ):
        parser.error("External native netlist+models required together; no mixed RTL")
    if args.command_timeout_seconds is not None and args.command_timeout_seconds <= 0:
        parser.error("Explicit watchdog must be positive")
    out = args.out.resolve()
    if out.exists():
        parser.error("Fresh output required")
    tools = args.iverilog_dir or Path(shutil.which("iverilog") or "iverilog").parent
    tools = tools.resolve()
    rtl_dir = args.rtl_dir or ROOT / "hw/soc/rtl/pcie"
    rtl = [(rtl_dir / (name + ".v")).resolve() for name in MODULES]
    bench = ROOT / "hw/soc/tb/cocotb" / ("test_" + TOP + ".py")
    makefile = bench.with_name("Makefile." + TOP)
    files = rtl + [
        bench,
        makefile,
        Path(__file__).resolve(),
        ROOT / "scripts/check_pcie_gen3_framer.py",
        ROOT / "scripts/check_pcie_integrity.py",
        ROOT / "scripts/check_pcie_integrity_native.py",
        ROOT / "scripts/cocotb_results.py",
    ]
    simulation_sources = rtl
    if args.netlist:
        if pin(args.models)["sha256"] != MODEL_SHA:
            parser.error("Exact unmodified SG13G2 cell model required")
        simulation_sources = [args.netlist.resolve(), args.models.resolve()]
        files += simulation_sources
    before = {str(p): pin(p) for p in files}
    runtime = {str(tools / name): pin(tools / name) for name in ("iverilog", "vvp")}
    expected = sum(
        isinstance(n, ast.AsyncFunctionDef) and bool(n.decorator_list)
        for n in ast.parse(bench.read_text()).body
    )
    if not expected:
        parser.error("No actual port tests")
    out.mkdir(parents=True)
    record = dict(
        status="RUNNING",
        top=TOP,
        mode="external_native" if args.netlist else "rtl",
        inputs=before,
        runtime=runtime,
        expected_tests=expected,
        max_encoded_bytes=150,
        scope="Elastic already-aligned x4 Data Stream packet TX/RX. Independent serialized-word oracle plus independently encoded RX controls. No nonbackpressurable PMA, OS/LTSSM, line-rate, SDF, main-chip or PHY acceptance.",
    )

    def save():
        temporary = out / "result.tmp"
        temporary.write_text(json.dumps(record, indent=2) + "\n")
        temporary.replace(out / "result.json")

    try:
        save()
        command = [
            "make",
            "-f",
            str(makefile),
            "--no-print-directory",
            "VERILOG_SOURCES=" + " ".join(map(str, simulation_sources)),
            "SIM_BUILD=" + str(out / "sim"),
            "COCOTB_RESULTS_FILE=" + str(out / "results.xml"),
            "PCIE_NATIVE=" + str(int(args.netlist is not None)),
        ]
        record["command"] = command
        record["returncode"] = execute_command(
            command,
            out / "simulation.log",
            tool_environment(tools),
            args.command_timeout_seconds,
        )
        if record["returncode"]:
            raise RuntimeError("Actual duplex port simulation failed")
        counts = count_results([out / "results.xml"])
        record["tests"] = dict(zip(("passed", "failed", "skipped"), counts))
        if counts != (expected, 0, 0):
            raise ValueError("Missing, failed or skipped duplex port tests")
        if before != {p: pin(p) for p in before} or runtime != {
            p: pin(p) for p in runtime
        }:
            raise ValueError("Source/runtime drift")
        record["status"] = "PASS_ELASTIC_GEN3_DUPLEX_PORTS"
    except BaseException as error:
        record.update(status="FAIL", error=repr(error))
        raise
    finally:
        record["outputs"] = {
            name: pin(out / name)
            for name in ("results.xml", "simulation.log")
            if (out / name).is_file()
        }
        save()
    print(record["status"], record["tests"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
