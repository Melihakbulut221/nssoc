#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Map the bounded PCIe sequence RX and LCRC TX wrapper and replay its port tests."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

from cocotb_results import count_results

ROOT = Path(__file__).resolve().parents[1]
TOP = "soc_pcie_packet_endpoint"
RTL = tuple(
    ROOT / "hw/soc/rtl/pcie" / (name + ".v")
    for name in (
        "soc_pcie_crc32_byte",
        "soc_pcie_lcrc_rx",
        "soc_pcie_sequence_rx",
        "soc_pcie_lcrc_tx",
        TOP,
        "soc_pcie_tlp_stream",
        "soc_pcie_tlp_regs",
    )
)
LIB_SHA = "968b0cfdcefc49a88d9a5c48874769eaad9aba3509e1240b5e14a821bb07a3c4"
MODEL_SHA = "28343754a828972d614c15b7db27892e92a8c16e49fc06ed69d858a659942ed4"


def pin(path):
    data = Path(path).read_bytes()
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def quote(path):
    text = str(path)
    if "\n" in text or "\r" in text:
        raise ValueError("A tool input path must not contain a newline")
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("out", "yosys", "iverilog-dir", "liberty", "models"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists():
        parser.error("Use a fresh output directory; earlier evidence is preserved")
    lib, models = args.liberty.resolve(), args.models.resolve()
    if pin(lib)["sha256"] != LIB_SHA or pin(models)["sha256"] != MODEL_SHA:
        parser.error("The pinned unmodified SG13G2 timing and cell models are required")
    iverilog = args.iverilog_dir.resolve() / "iverilog"
    version = subprocess.check_output(
        [str(iverilog), "-V"], stderr=subprocess.STDOUT, text=True
    )
    match = re.search(r"Icarus Verilog version (\d+)", version)
    if not match or int(match[1]) < 13:
        parser.error("Native delayed cell inputs require Icarus >=13")
    driver = ROOT / "scripts/check_pcie_packet.py"
    sources = (
        *RTL,
        driver,
        Path(__file__).resolve(),
        ROOT / "scripts/cocotb_results.py",
        ROOT / "hw/soc/tb/cocotb/test_soc_pcie_packet_endpoint.py",
        ROOT / "hw/soc/tb/cocotb/test_soc_pcie_tlp_integrity.py",
        ROOT / "hw/soc/tb/cocotb/test_soc_pcie_tlp_stream.py",
        ROOT / "hw/soc/tb/cocotb/Makefile.soc_pcie_packet_endpoint",
    )
    before = {str(p.relative_to(ROOT)): pin(p) for p in sources}
    out.mkdir(parents=True)
    record = dict(
        status="RUNNING",
        top=TOP,
        source_files=before,
        models=pin(models),
        liberty=pin(lib),
        iverilog_version=version.splitlines()[0],
        commands=[],
        candidate_adopted=False,
        full_pcie_link=False,
        scope="Default-parameter, single-clock sequence RX and LCRC TX block mapped to IHP cells; no ACK/NAK DLLP encoder, replay, credits, SDF, placement, PCIe link or SoC adoption.",
    )

    def save():
        (out / "result.json").write_text(json.dumps(record, indent=2) + "\n")

    def execute(command, log_name):
        with (out / log_name).open("x") as log:
            process = subprocess.run(
                command, stdout=log, stderr=subprocess.STDOUT, check=False
            )
        record["commands"].append(
            dict(
                argv=command,
                returncode=process.returncode,
                log=log_name,
                log_pin=pin(out / log_name),
            )
        )
        save()
        if process.returncode:
            raise RuntimeError("Native control failed; inspect " + str(out / log_name))

    try:
        save()
        flow = (
            "read_liberty -lib "
            + quote(lib)
            + "; read_verilog -sv "
            + " ".join(map(quote, RTL))
            + "; hierarchy -check -top "
            + TOP
            + "; flatten -noscopeinfo; synth -top "
            + TOP
            + " -noabc; "
            + "dfflibmap -liberty "
            + quote(lib)
            + "; abc -liberty "
            + quote(lib)
            + "; clean; check -assert; stat -liberty "
            + quote(lib)
            + "; write_json "
            + quote(out / "mapped.json")
            + "; write_verilog -noattr -noexpr "
            + quote(out / "mapped.v")
        )
        (out / "map.ys").write_text(flow + "\n")
        execute(
            [str(args.yosys.resolve()), "-Q", "-T", "-s", str(out / "map.ys")],
            "map.log",
        )
        cells = json.loads((out / "mapped.json").read_text())["modules"][TOP]["cells"]
        if not cells or any(
            not c["type"].startswith("sg13g2_") for c in cells.values()
        ):
            raise RuntimeError("Mapped netlist contains unimplemented or non-IHP cells")
        record["mapped_cells"] = len(cells)
        execute(
            [
                sys.executable,
                str(driver),
                "--out",
                str(out / "simulation"),
                "--netlist",
                str(out / "mapped.v"),
                "--models",
                str(models),
                "--iverilog-dir",
                str(args.iverilog_dir.resolve()),
            ],
            "simulation.log",
        )
        # The port suite is identical for RTL and mapped cells. Its driver also
        # rejects incomplete XML; a successful shell command alone is not proof.
        result_files = sorted((out / "simulation").rglob("*.xml"))
        passed, failed, skipped = count_results(result_files)
        if not result_files or passed == 0 or failed or skipped:
            raise RuntimeError("Missing, failed or skipped native port tests")
        if before != {str(p.relative_to(ROOT)): pin(p) for p in sources}:
            raise RuntimeError("Verification sources changed during the run")
        if pin(lib) != record["liberty"] or pin(models) != record["models"]:
            raise RuntimeError("Native library changed during the run")
        record.update(
            status="PASS_MAPPED_PACKET_ENDPOINT_PORT_TESTS",
            tests=dict(passed=passed, failed=failed, skipped=skipped),
            outputs={
                str(p.relative_to(out)): pin(p)
                for p in (
                    out / "map.ys",
                    out / "mapped.v",
                    out / "mapped.json",
                    *result_files,
                )
            },
        )
    except (
        OSError,
        ValueError,
        KeyError,
        RuntimeError,
        ET.ParseError,
        subprocess.SubprocessError,
    ) as error:
        record.update(status="FAIL", error=str(error))
    finally:
        save()
    print(record["status"], record.get("error", ""))
    return int(record["status"] != "PASS_MAPPED_PACKET_ENDPOINT_PORT_TESTS")


if __name__ == "__main__":
    raise SystemExit(main())
