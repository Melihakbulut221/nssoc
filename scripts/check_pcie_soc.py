#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual CPU + PCIe packet completer sharing soc_top GPIO; no PHY claim."""

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
from check_pcie_rx_flow import COMMON
from cocotb_results import count_results

ROOT = Path(__file__).resolve().parents[1]
SOC = ROOT / "hw/soc"
sys.path.insert(0, str(SOC / "flow"))
from interface_profile import resolve


def pin(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def firmware():
    # RV32I, reset vector C0000080, no RAM/stack or interrupt manipulation.
    # lui x1,0xff902; addi x2,x0,-1; sw x2,8(x1); addi x2,x0,1;
    # loop: sw x2,0x74(x1); lw x3,0x1c(x1); jal x0,loop.
    def store(rs2, rs1, imm):
        return (
            ((imm >> 5) << 25)
            | (rs2 << 20)
            | (rs1 << 15)
            | (2 << 12)
            | ((imm & 31) << 7)
            | 0x23
        )

    offset = (-8) & ((1 << 21) - 1)
    jump = (
        ((offset >> 20) << 31)
        | (((offset >> 1) & 1023) << 21)
        | (((offset >> 11) & 1) << 20)
        | (((offset >> 12) & 255) << 12)
        | 0x6F
    )
    words = [0x13] * 2016
    words[:7] = [
        0xFF9020B7,
        0xFFF00113,
        store(2, 1, 8),
        0x00100113,
        store(2, 1, 0x74),
        (0x1C << 20) | (1 << 15) | (2 << 12) | (3 << 7) | 3,
        jump,
    ]
    return "".join(f"{w:08x}\n" for w in words)


def sources():
    bundle, _ = resolve("base")
    # Reuse the qualified core selector, which verifies its patched top.
    core = subprocess.check_output(
        [
            "bash",
            "-c",
            'source "$1"; IBEX_FAULT_PORT=1 ibex_sources "$2"',
            "source-list",
            str(SOC / "flow/ibex_sources.sh"),
            str(SOC),
        ],
        text=True,
    ).splitlines()
    names = "soc_top soc_bus soc_req_pipe soc_apb_bridge soc_mem soc_mem_ecc soc_scrub soc_boot soc_pnp soc_apb_pnp soc_uart soc_gpio soc_spw soc_i2c soc_spi soc_can soc_eth soc_apb_wb soc_qspi soc_clint soc_gptimer soc_wdog soc_busstat soc_tmr_bank soc_npu soc_npu_ser prim_clock_gating".split()
    pilot = "pilot_top lif_core aer_fifo scrub tmr_voter".split()
    return [
        *[SOC / "rtl" / (n + ".v") for n in names],
        bundle,
        *[ROOT / "hw/rtl" / (n + ".v") for n in pilot],
        *[Path(p) for p in core],
        *[SOC / "rtl/pcie" / (n + ".v") for n in (*COMMON, "soc_pcie_apb_arbiter")],
        SOC / "tb/tb_soc_pcie_packet.v",
    ]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--iverilog-dir", type=Path, required=True)
    p.add_argument(
        "--top-override", type=Path, help="Counterexample copy, never edit shipping RTL"
    )
    a = p.parse_args()
    out = a.out.resolve()
    if out.exists():
        p.error("Use a fresh output directory")
    files = sources()
    if a.top_override:
        files = [
            a.top_override.resolve() if f == SOC / "rtl/soc_top.v" else f for f in files
        ]
    bench = SOC / "tb/cocotb/test_soc_pcie_soc.py"
    method = SOC / "tb/cocotb/Makefile.soc_pcie_soc"
    dependencies = [
        bench,
        method,
        Path(__file__),
        ROOT / "scripts/check_pcie_rx_flow.py",
        ROOT / "scripts/cocotb_results.py",
        SOC / "flow/ibex_sources.sh",
        SOC / "flow/ibex_fault_port.py",
        SOC / "flow/interface_profile.py",
        SOC / "flow/prepare_interfaces.py",
        *sorted((SOC / "rtl").glob("*.vh")),
        *sorted((ROOT / "hw/rtl").glob("*.vh")),
    ]
    dependencies += [
        bench.with_name(n)
        for n in (
            "pcie_rx_flow_common.py",
            "test_soc_pcie_tlp_integrity.py",
            "test_soc_pcie_tlp_stream.py",
            "test_soc_pcie_packet_tx.py",
        )
    ]
    out.mkdir(parents=True)
    rom = out / "rom.hex"
    rom.write_text(firmware())
    before = {str(f): pin(f) for f in [*files, *dependencies, rom]}
    candidates = [
        Path(sys.executable).parent,
        ROOT / "hw/.venv/bin",
        SOC / "tools/cocotb-venv/bin",
    ]
    python_dir = next((p for p in candidates if (p / "cocotb-config").is_file()), None)
    if python_dir is None:
        config = shutil.which("cocotb-config")
        if not config:
            p.error("A Python 3.9-3.13 cocotb installation is required")
        python_dir = Path(config).parent
    python = python_dir / "python"
    env = os.environ.copy()
    env.update(
        PYTHONDONTWRITEBYTECODE="1",
        PCIE_ROOT=str(ROOT),
        PCIE_ROM=str(rom),
        PATH=str(python_dir)
        + os.pathsep
        + str(a.iverilog_dir.resolve())
        + os.pathsep
        + env["PATH"],
    )
    paths = subprocess.check_output(
        [str(python), "-c", "import sys,os; print(os.pathsep.join(sys.path))"],
        text=True,
    ).strip()
    env["PYTHONPATH"] = str(bench.parent) + os.pathsep + paths
    command = [
        "make",
        "--no-print-directory",
        "-f",
        str(method),
        "VERILOG_SOURCES=" + " ".join(map(str, files)),
        f"SIM_BUILD={out}/sim",
        f"COCOTB_RESULTS_FILE={out}/results.xml",
    ]
    runtime = {
        str(x): pin(x)
        for x in [
            a.iverilog_dir.resolve() / "iverilog",
            a.iverilog_dir.resolve() / "vvp",
            python.resolve(),
        ]
    }
    record = dict(
        status="RUNNING",
        inputs=before,
        runtime=runtime,
        argv=command,
        scope="Actual Ibex CPU ROM + same-clock packet endpoint + GPIO/APB. Base interface profile, hardened default core/memory and clock gates. No PHY/PCS/LTSSM, external PCIe peer, SRAM macro, full boot software or physical timing qualification.",
    )
    result = out / "result.json"

    def save():
        result.write_text(json.dumps(record, indent=2) + "\n")

    save()
    try:
        with (out / "run.log").open("w") as log:
            completed = subprocess.run(
                command,
                cwd=out,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=600,
            )
        record["returncode"] = completed.returncode
        record["unchanged"] = before == {
            str(f): pin(f) for f in [*files, *dependencies, rom]
        }
        record["runtime_unchanged"] = runtime == {p: pin(Path(p)) for p in runtime}
        counts = count_results([out / "results.xml"])
        record["tests"] = dict(zip(("passed", "failed", "skipped"), counts))
        if (
            completed.returncode
            or not record["unchanged"]
            or not record["runtime_unchanged"]
            or counts != (2, 0, 0)
        ):
            raise ValueError(
                "Incomplete, failed, skipped or source-drifting integration test"
            )
        if any(
            t in (out / "run.log").read_text() for t in ("WARNING:", "ERROR:", "FATAL:")
        ):
            raise ValueError("Native elaboration/runtime diagnostic")
        record["status"] = "PASS"
    except BaseException as error:
        record.update(status="FAIL", error=repr(error))
    finally:
        record["outputs"] = {
            str(f.relative_to(out)): pin(f)
            for f in [out / "run.log", out / "results.xml"]
            if f.exists()
        }
        save()
    print(
        json.dumps(
            {k: v for k, v in record.items() if k not in ("inputs", "argv")}, indent=2
        )
    )
    return record["status"] != "PASS"


if __name__ == "__main__":
    raise SystemExit(main())
