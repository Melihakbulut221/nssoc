# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual HDL faults must fail the independent public-port oracle."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT / "hw/soc/rtl/pcie"
def iverilog_directory():
    """Prefer the installed CI toolchain; retain the optional local checkout."""
    installed = shutil.which("iverilog")
    directory = (
        Path(installed).parent
        if installed
        else ROOT / "hw/soc/tools/oss-cad-suite/bin"
    )
    assert all(os.access(directory / name, os.X_OK) for name in ("iverilog", "vvp")), (
        f"Actual Icarus and vvp executables required in {directory}"
    )
    return directory


SOURCES = (
    "soc_pcie_gen3_stp",
    "soc_pcie_gen3_framer_tx",
    "soc_pcie_gen3_packet_tx_path",
    "soc_pcie_gen3_tx_path_v3",
    "soc_pcie_gen3_gearbox",
)
FAULTS = [
    (
        "crc_polynomial",
        "soc_pcie_gen3_stp",
        "l[10]^l[7]^l[6]^l[4]^l[2]^l[1]^l[0]",
        "l[7]^l[6]^l[4]^l[2]^l[1]^l[0]",
        "soc_pcie_gen3_stp",
    ),
    (
        "frame_parity",
        "soc_pcie_gen3_stp",
        "wire parity = ^{l,c};",
        "wire parity = 1'b0;",
        "soc_pcie_gen3_stp",
    ),
    (
        "reserved_prefix",
        "soc_pcie_gen3_framer_tx",
        "(!dllp_i && data_i[7:4]!=0)",
        "1'b0",
        "soc_pcie_gen3_framer_tx",
    ),
    (
        "header_length",
        "soc_pcie_gen3_framer_tx",
        "final_bytes!=expected_bytes",
        "1'b0",
        "soc_pcie_gen3_framer_tx",
    ),
    (
        "format_prefix",
        "soc_pcie_gen3_framer_tx",
        "fmt[2] || final_bytes",
        "1'b0 || final_bytes",
        "soc_pcie_gen3_framer_tx",
    ),
    (
        "stall_loss",
        "soc_pcie_gen3_framer_tx",
        "if (block_ready_i) begin",
        "if (1'b1) begin",
        "soc_pcie_gen3_framer_tx",
    ),
    (
        "striping",
        "soc_pcie_gen3_framer_tx",
        "(index % 4)*128 + ((index % 64)/4)*8",
        "(index % 64)*8",
        "soc_pcie_gen3_framer_tx",
    ),
    (
        "omit_edb",
        "soc_pcie_gen3_framer_tx",
        "if (nullify) begin",
        "if (1'b0) begin",
        "soc_pcie_gen3_framer_tx",
    ),
    (
        "edb_length",
        "soc_pcie_gen3_framer_tx",
        "framed_dw = framed_bytes[12:2];",
        "framed_dw = framed_bytes[12:2] + nullify;",
        "soc_pcie_gen3_framer_tx",
    ),
    (
        "ignore_input_error",
        "soc_pcie_gen3_framer_tx",
        "if (error_i || dllp_i!=is_dllp",
        "if (1'b0 || dllp_i!=is_dllp",
        "soc_pcie_gen3_framer_tx",
    ),
    (
        "wrong_header",
        "soc_pcie_gen3_packet_tx_path",
        ".header_i(header)",
        ".header_i(2'b01)",
        "soc_pcie_gen3_packet_tx_path",
    ),
    (
        "no_scrambling",
        "soc_pcie_gen3_packet_tx_path",
        ".scramble_i(64'hffffffffffffffff)",
        ".scramble_i(64'h0000000000000000)",
        "soc_pcie_gen3_packet_tx_path",
    ),
    (
        "reseed_each_block",
        "soc_pcie_gen3_packet_tx_path",
        ".reseed_after_i(4'b0)",
        ".reseed_after_i(4'b1111)",
        "soc_pcie_gen3_packet_tx_path",
    ),
]


@pytest.mark.parametrize("name,module,old,new,top", FAULTS, ids=[x[0] for x in FAULTS])
def test_real_source_fault_rejected(tmp_path, name, module, old, new, top):
    directory = tmp_path / "rtl"
    directory.mkdir()
    for source in SOURCES:
        shutil.copyfile(RTL / (source + ".v"), directory / (source + ".v"))
    path = directory / (module + ".v")
    text = path.read_text()
    assert text.count(old) == 1
    path.write_text(text.replace(old, new))
    result = tmp_path / "capture"
    command = [
        sys.executable,
        str(ROOT / "scripts/check_pcie_gen3_framer.py"),
        "--top",
        top,
        "--out",
        str(result),
        "--rtl-dir",
        str(directory),
        "--iverilog-dir",
        str(iverilog_directory()),
        "--command-timeout-seconds",
        "60",
    ]
    with (tmp_path / "launch.log").open("w") as log:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            stdout=log,
            stderr=subprocess.STDOUT,
            timeout=90,
        )
    assert completed.returncode != 0
    record = json.loads((result / "result.json").read_text())
    assert record["status"] == "FAIL"
    # Require an executed HDL assertion failure, not compilation/tool absence.
    log = (result / "simulation.log").read_text()
    assert "AssertionError" in log and "failed" in log
    assert (result / "results.xml").exists()


@pytest.mark.parametrize("capacity", [17, 4119])
def test_capacity_cli_rejects_unsupported_elaboration(tmp_path, capacity):
    p = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/check_pcie_gen3_framer.py"),
            "--out",
            str(tmp_path / "unused"),
            "--max-encoded-bytes",
            str(capacity),
        ],
        capture_output=True,
        text=True,
    )
    assert p.returncode == 2 and "Capacity18..4118" in p.stderr
    assert not (tmp_path / "unused").exists()
