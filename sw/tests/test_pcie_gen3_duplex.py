# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Real HDL glue faults must fail independent serialized-word or packet tests."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULES = (
    "soc_pcie_gen3_stp",
    "soc_pcie_gen3_framer_tx",
    "soc_pcie_gen3_packet_tx_path",
    "soc_pcie_gen3_tx_path_v3",
    "soc_pcie_gen3_gearbox",
    "soc_pcie_gen3_scrambler",
    "soc_pcie_gen3_framer_rx",
    "soc_pcie_gen3_packet_rx_path",
    "soc_pcie_gen3_packet_duplex",
)
FAULTS = (
    ("lane_mapping", "lane*128+feed_index*32", "((lane+1)%4)*128+feed_index*32"),
    ("beat_mapping", "k*128+collect_index*32", "k*128+(3-collect_index)*32"),
    ("concealed_header", "decoded_headers<=raw_headers", "decoded_headers<=8'haa"),
    ("no_descrambling", ".scramble_i(16'hffff)", ".scramble_i(16'h0000)"),
    ("stalled_lfsr", ".advance_i(16'hffff)", ".advance_i(16'h0000)"),
    ("reseed_each_beat", ".reseed_after_i(4'b0)", ".reseed_after_i(4'b1111)"),
    ("partial_block", "if(collect_index==3)", "if(collect_index==2)"),
    ("lost_held_block", "if(decoded_valid && decoded_ready)", "if(decoded_valid)"),
    (
        "epoch_not_flushed",
        "flush_i || stream_start_i || stream_abort_i || !active_o",
        "flush_i || stream_abort_i || !active_o",
    ),
    (
        "old_decoded_state",
        "end else if(transport_flush) begin",
        "end else if(flush_i) begin",
    ),
)


@pytest.mark.parametrize("name,before,after", FAULTS, ids=[r[0] for r in FAULTS])
def test_actual_glue_fault_rejected(tmp_path, name, before, after):
    directory = tmp_path / "rtl"
    directory.mkdir()
    for module in MODULES:
        shutil.copyfile(
            ROOT / "hw/soc/rtl/pcie" / (module + ".v"), directory / (module + ".v")
        )
    source = directory / "soc_pcie_gen3_packet_rx_path.v"
    text = source.read_text()
    assert text.count(before) == 1
    source.write_text(text.replace(before, after))
    installed = shutil.which("iverilog")
    tools = (
        Path(installed).parent if installed else ROOT / "hw/soc/tools/oss-cad-suite/bin"
    )
    assert all(os.access(tools / n, os.X_OK) for n in ("iverilog", "vvp"))
    out = tmp_path / "capture"
    with (tmp_path / "launch.log").open("w") as log:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/check_pcie_gen3_duplex.py"),
                "--out",
                str(out),
                "--rtl-dir",
                str(directory),
                "--iverilog-dir",
                str(tools),
                "--command-timeout-seconds",
                "60",
            ],
            cwd=ROOT,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            stdout=log,
            stderr=subprocess.STDOUT,
            timeout=90,
        )
    assert result.returncode != 0
    record = json.loads((out / "result.json").read_text())
    assert record["status"] == "FAIL"
    assert record["error"] == "RuntimeError('Actual duplex port simulation failed')"
    assert "AssertionError" in (out / "simulation.log").read_text()
    cases = list(ET.parse(out / "results.xml").getroot().iter("testcase"))
    assert len(cases) == 5
    assert all(case.find("skipped") is None for case in cases)
    assert any(case.find("failure") is not None for case in cases)
