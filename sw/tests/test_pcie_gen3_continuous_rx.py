# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Execute the port oracle against actual HDL faults and non-power-of-two FIFOs."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULES = ("soc_pcie_gen3_ingress", "soc_pcie_gen3_data_descrambler", "soc_pcie_gen3_framer_rx_v3", "soc_pcie_gen3_continuous_rx")
FAULTS = (
    ("zero_payload_lost", "soc_pcie_gen3_framer_rx_v3", "(state==TOKEN || state==LOOK || state==EMIT)", "1'b1"),
    ("successor_payload_lost", "soc_pcie_gen3_framer_rx_v3", "(!block_pending || block_data==512'b0)", "1'b1"),
    ("missing_look_release", "soc_pcie_gen3_framer_rx_v3", "if(state==LOOK && !block_pending)", "if(1'b0)"),
    ("no_idle_bypass", "soc_pcie_gen3_framer_rx_v3", "|| idle_fast);", "|| 1'b0);"),
    ("scrambler_epoch", "soc_pcie_gen3_data_descrambler", "mask(128,bit_number)", "mask(127,bit_number)"),
    ("wrong_lane_seed", "soc_pcie_gen3_data_descrambler", "2:seed=23'h1ec760", "2:seed=23'h1dbfbc"),
    ("lost_reseed", "soc_pcie_gen3_continuous_rx", "transport_flush || stream_start_i", "flush_i"),
    ("late_overflow_flag", "soc_pcie_gen3_continuous_rx", "(overflow_sticky || raw_overflow)", "overflow_sticky"),
    ("restart_blocked", "soc_pcie_gen3_continuous_rx", "(stream_abort_i || overflow_o || raw_overflow) && !stream_start_i", "stream_abort_i || overflow_sticky || raw_overflow"),
    ("wrong_lane_word", "soc_pcie_gen3_ingress", "word_i[lane*32+:32]", "word_i[((lane+1)%4)*32+:32]"),
)


def run(tmp_path, rtl=None):
    installed = shutil.which("iverilog")
    tools = Path(installed).parent if installed else ROOT / "hw/soc/tools/oss-cad-suite/bin"
    assert all(os.access(tools / n, os.X_OK) for n in ("iverilog", "vvp"))
    out = tmp_path / "capture"
    argv = [sys.executable, str(ROOT / "scripts/check_pcie_gen3_continuous_rx.py"),
            "--out", str(out), "--iverilog-dir", str(tools)]
    if rtl is not None:
        argv += ["--rtl-dir", str(rtl)]
    with (tmp_path / "launch.log").open("w") as log:
        result = subprocess.run(argv, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    record = json.loads((out / "result.json").read_text())
    cases = list(ET.parse(out / "results.xml").getroot().iter("testcase"))
    assert len(cases) == 6
    assert all(case.find("skipped") is None for case in cases)
    return result, record, cases, out


@pytest.mark.parametrize("name,module,before,after", FAULTS, ids=[r[0] for r in FAULTS])
def test_actual_continuous_rx_fault_rejected(tmp_path, name, module, before, after):
    directory = tmp_path / "rtl"
    directory.mkdir()
    for item in MODULES:
        shutil.copyfile(ROOT / "hw/soc/rtl/pcie" / (item + ".v"), directory / (item + ".v"))
    source = directory / (module + ".v")
    text = source.read_text()
    assert text.count(before) == 1
    source.write_text(text.replace(before, after))
    result, record, cases, out = run(tmp_path, directory)
    assert result.returncode != 0 and record["status"] == "FAIL"
    assert any(case.find("failure") is not None for case in cases)
    assert "AssertionError" in (out / "simulation.log").read_text()


def test_actual_continuous_rx_positive(tmp_path):
    result, record, cases, _ = run(tmp_path)
    assert result.returncode == 0, record
    assert record["tests"] == {"passed": 6, "failed": 0, "skipped": 0}
    assert all(case.find("failure") is None for case in cases)
