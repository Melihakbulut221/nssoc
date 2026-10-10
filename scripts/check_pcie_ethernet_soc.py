#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual CPU, PCIe packet traffic and asynchronous Ethernet loopback together."""

import argparse
import hashlib
import json
import os
import shutil
import re
import tarfile
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


from pcie_ethernet_firmware import firmware


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
        SOC / "tb/tb_soc_pcie_ethernet.v",
    ]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--iverilog-dir", type=Path, required=True)
    p.add_argument(
        "--top-override", type=Path, help="Counterexample copy, never edit shipping RTL"
    )
    p.add_argument(
        "--eth-mbist-pdk",
        type=Path,
        help="Use 16 actual vendor FIFO SRAM models and POR MBIST",
    )
    p.add_argument(
        "--async-pcie",
        action="store_true",
        help="Separate 250 MHz packet/controller and 50 MHz CPU clocks",
    )
    a = p.parse_args()
    out = a.out.resolve()
    if out.exists():
        p.error("Use a fresh output directory")
    files = sources()
    if a.async_pcie:
        files.append(SOC / "rtl/pcie/soc_pcie_apb_cdc.v")
    if a.top_override:
        files = [
            a.top_override.resolve() if f == SOC / "rtl/soc_top.v" else f for f in files
        ]
    if a.eth_mbist_pdk:
        version = subprocess.check_output(
            [str(a.iverilog_dir.resolve() / "iverilog"), "-V"],
            stderr=subprocess.STDOUT,
            text=True,
        )
        match = re.search(r"Icarus Verilog version (\d+)", version)
        if not match or int(match[1]) < 13:
            p.error("Vendor SRAM models require Icarus >=13")
        files += [
            SOC / "rtl/dft" / name
            for name in (
                "soc_eth_fifo_sram.v",
                "soc_sram_mbist.v",
                "soc_sram_zero_check.v",
            )
        ]
        models = a.eth_mbist_pdk.resolve() / "libs.ref/sg13g2_sram/verilog"
        files += [
            models / name
            for name in (
                "RM_IHPSG13_2P_256x16_c2_bm_bist.v",
                "RM_IHPSG13_2P_core_behavioral_bm_bist_ideal.v",
                "RM_IHPSG13_2P_core_behavioral_ideal.v",
            )
        ]
    bench = SOC / "tb/cocotb/test_soc_pcie_ethernet.py"
    method = SOC / "tb/cocotb/Makefile.soc_pcie_ethernet"
    dependencies = [
        bench,
        method,
        Path(__file__),
        ROOT / "scripts/pcie_ethernet_firmware.py",
        bench.with_name("test_soc_pcie_soc.py"),
        ROOT / "scripts/check_pcie_rx_flow.py",
        ROOT / "scripts/cocotb_results.py",
        SOC / "flow/ibex_sources.sh",
        SOC / "flow/ibex_fault_port.py",
        SOC / "flow/interface_profile.py",
        SOC / "flow/prepare_interfaces.py",
        SOC / "flow/adapt_eth_mbist.py",
        SOC / "gen/interfaces.bundle.json",
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
    # Preserve the actual generated bundles, ROM, models and experiment
    # sources before starting; a later source edit cannot erase this run.
    with tarfile.open(out / "inputs.tar.gz", "w:gz") as archive:
        for i, name in enumerate(before):
            source = Path(name).resolve()
            arcname = (
                str(source.relative_to(ROOT))
                if source.is_relative_to(ROOT)
                else f"external/{i}/{source.name}"
            )
            archive.add(source, arcname=arcname, recursive=False)
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
        JOINT_PCIE_ASYNC="1" if a.async_pcie else "0",
        JOINT_ETH_MBIST="1" if a.eth_mbist_pdk else "0",
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
        "TOPLEVEL=tb_soc_pcie_ethernet",
        "COCOTB_TEST_MODULES=test_soc_pcie_ethernet",
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
        scope="Actual Ibex CPU, PCIe packet/GPIO and GMII Ethernet concurrent traffic. Base interface bundle; external loopback over independent 125 MHz clocks and 50 MHz APB. Optional 16 vendor functional FIFO SRAM instances with POR MBIST. No PCIe serial PHY, LTSSM, Ethernet PHY, full system SRAM mapping, layout, RC or timing qualification.",
        ethernet_vendor_sram=bool(a.eth_mbist_pdk),
        asynchronous_pcie=bool(a.async_pcie),
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
            )
        record["returncode"] = completed.returncode
        record["unchanged"] = before == {
            str(f): pin(f) for f in [*files, *dependencies, rom]
        }
        record["runtime_unchanged"] = runtime == {p: pin(Path(p)) for p in runtime}
        counts = count_results([out / "results.xml"])
        record["tests"] = dict(zip(("passed", "failed", "skipped"), counts))
        compiled = (out / "sim/sim.vvp").read_text()
        record["ethernet_sram_instances"] = len(
            re.findall(
                r'\.scope module, "u_mem" "RM_IHPSG13_2P_256x16_c2_bm_bist"', compiled
            )
        )
        if record["ethernet_sram_instances"] != (16 if a.eth_mbist_pdk else 0):
            raise ValueError("Unexpected or missing actual Ethernet SRAM instances")
        record["elaboration_warnings"] = [
            line
            for line in (out / "run.log").read_text().splitlines()
            if "warning:" in line.lower()
        ]
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
            for f in [
                out / "run.log",
                out / "results.xml",
                out / "inputs.tar.gz",
                out / "rom.hex",
                out / "sim/sim.vvp",
            ]
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
