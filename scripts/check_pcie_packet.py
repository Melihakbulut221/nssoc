#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Port-only RTL or unchanged-model mapped replay of the PCIe integrity wrapper."""

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from cocotb_results import count_results

ROOT = Path(__file__).resolve().parents[1]
TOP = "soc_pcie_packet_endpoint"
SOURCES = tuple(
    "hw/soc/rtl/pcie/" + n + ".v"
    for n in (
        "soc_pcie_crc32_byte",
        "soc_pcie_lcrc_rx",
        "soc_pcie_sequence_rx",
        "soc_pcie_lcrc_tx",
        TOP,
        "soc_pcie_tlp_stream",
        "soc_pcie_tlp_regs",
    )
)
BENCH = "hw/soc/tb/cocotb/test_soc_pcie_packet_endpoint.py"
MAKEFILE = "hw/soc/tb/cocotb/Makefile.soc_pcie_packet_endpoint"


def pin(path):
    data = Path(path).read_bytes()
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def tool_environment(iverilog_dir=None):
    """Use this Python/cocotb, then the requested native Icarus wrappers."""
    env = dict(os.environ)
    env["PATH"] = os.pathsep.join(
        [str(Path(sys.executable).parent)]
        + ([str(iverilog_dir.resolve())] if iverilog_dir else [])
        + [env.get("PATH", "")]
    )
    env["PYTHONPATH"] = os.pathsep.join(
        [str(ROOT / "hw/soc/tb/cocotb"), *map(str, sys.path)]
    )
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PCIE_CFG_ID"] = "65535"
    return env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--netlist", type=Path)
    parser.add_argument("--models", type=Path)
    parser.add_argument("--iverilog-dir", type=Path)
    parser.add_argument("--rtl-dir", type=Path)
    parser.add_argument("--unit-tx", action="store_true")
    args = parser.parse_args()
    top = "soc_pcie_lcrc_tx" if args.unit_tx else TOP
    bench = "hw/soc/tb/cocotb/test_soc_pcie_lcrc_tx.py" if args.unit_tx else BENCH
    if bool(args.netlist) != bool(args.models):
        parser.error("--netlist and --models must be supplied together")
    if args.netlist and args.rtl_dir:
        parser.error("mapped replay never mixes RTL and mapped sources")
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    sources = (
        [args.netlist.resolve(), args.models.resolve()]
        if args.netlist
        else [
            ((args.rtl_dir / n.split("/")[-1]) if args.rtl_dir else ROOT / n).resolve()
            for n in SOURCES
        ]
    )
    files = sources + [
        ROOT / bench,
        ROOT / MAKEFILE,
        ROOT / "hw/soc/tb/cocotb/test_soc_pcie_tlp_stream.py",
        ROOT / "hw/soc/tb/cocotb/test_soc_pcie_tlp_integrity.py",
        Path(__file__).resolve(),
        ROOT / "scripts/cocotb_results.py",
    ]
    original = {str(p): pin(p) for p in files}
    tree = ast.parse((ROOT / bench).read_text())
    expected = sum(
        isinstance(n, ast.AsyncFunctionDef) and bool(n.decorator_list)
        for n in tree.body
    )
    assert expected > 0
    env = tool_environment(args.iverilog_dir)
    record = dict(
        status="FAIL",
        top=top,
        mode="mapped" if args.netlist else "rtl",
        inputs=original,
        expected_tests=expected,
        scope="Classic sequence RX and prefix/LCRC TX around standalone transaction/APB boundary. No full DLL, PHY, link-up, SoC integration or timing/signoff claim.",
    )
    command = [
        "make",
        "-f",
        str(ROOT / MAKEFILE),
        "--no-print-directory",
        "TOPLEVEL=" + top,
        "COCOTB_TEST_MODULES=" + Path(bench).stem,
        "VERILOG_SOURCES=" + " ".join(map(str, sources)),
        "SIM_BUILD=" + str(out / "sim"),
        "COCOTB_RESULTS_FILE=" + str(out / "results.xml"),
        "PCIE_NATIVE=" + ("1" if args.netlist else "0"),
    ]
    record["command"] = command
    try:
        with (out / "driver.log").open("w") as log:
            r = subprocess.run(
                command,
                cwd=out,
                stdout=log,
                stderr=subprocess.STDOUT,
                env=env,
                timeout=900,
            )
        record["returncode"] = r.returncode
        passed, failed, skipped = count_results([out / "results.xml"])
        record["tests"] = dict(passed=passed, failed=failed, skipped=skipped)
        record["xml"] = pin(out / "results.xml")
        record["log"] = pin(out / "driver.log")
        assert r.returncode == 0 and (passed, failed, skipped) == (expected, 0, 0), (
            "Port-level integrity replay failed"
        )
        assert original == {str(p): pin(p) for p in files}, (
            "Inputs changed during replay"
        )
        record["status"] = "PASS_PORT_ONLY_PCIE_PACKET_CONTROLS"
        record["inputs_rechecked"] = True
    finally:
        (out / "result.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record["tests"]))


if __name__ == "__main__":
    main()
