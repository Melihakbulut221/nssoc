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
MODULE = "soc_pcie_gen3_ingress"
FAULTS = (
    ("lane_swap", "word_i[lane*32+:32]", "word_i[((lane+1)%4)*32+:32]"),
    ("lost_bit", "residual_count+8'd32", "residual_count+8'd31"),
    ("early_block", "residual_count>=8'd98", "residual_count>=8'd96"),
    ("header_shift", "assembled[lane][1:0]", "assembled[lane][2:1]"),
    ("residue_shift", "assembled[k]>>130", "assembled[k]>>129"),
    ("miss_full_pop", "queued<FIFO_DEPTH || pop", "queued<FIFO_DEPTH"),
    ("silent_overwrite", "queued<FIFO_DEPTH || pop", "1'b1"),
    ("bad_wrap", "wr_ptr==FIFO_DEPTH-1", "wr_ptr==FIFO_DEPTH-2"),
    ("no_epoch_clear", "end else if(flush_i || start_i)", "end else if(flush_i)"),
    ("no_halt", "running<=0;overflow_o<=1", "running<=1;overflow_o<=1"),
)


def run(tmp_path, rtl=None, depth=4):
    installed = shutil.which("iverilog")
    tools = Path(installed).parent if installed else ROOT / "hw/soc/tools/oss-cad-suite/bin"
    assert all(os.access(tools / n, os.X_OK) for n in ("iverilog", "vvp"))
    out = tmp_path / "capture"
    argv = [sys.executable, str(ROOT / "scripts/check_pcie_gen3_ingress.py"),
            "--out", str(out), "--iverilog-dir", str(tools), "--fifo-depth", str(depth)]
    if rtl is not None:
        argv += ["--rtl-dir", str(rtl)]
    with (tmp_path / "launch.log").open("w") as log:
        result = subprocess.run(argv, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    record = json.loads((out / "result.json").read_text())
    cases = list(ET.parse(out / "results.xml").getroot().iter("testcase"))
    assert len(cases) == 4
    assert all(case.find("skipped") is None for case in cases)
    return result, record, cases, out


@pytest.mark.parametrize("name,before,after", FAULTS, ids=[r[0] for r in FAULTS])
def test_actual_ingress_fault_rejected(tmp_path, name, before, after):
    directory = tmp_path / "rtl"
    directory.mkdir()
    text = (ROOT / "hw/soc/rtl/pcie" / (MODULE + ".v")).read_text()
    assert text.count(before) == 1
    (directory / (MODULE + ".v")).write_text(text.replace(before, after))
    result, record, cases, out = run(tmp_path, directory)
    assert result.returncode != 0 and record["status"] == "FAIL"
    assert any(case.find("failure") is not None for case in cases)
    assert "AssertionError" in (out / "simulation.log").read_text()


@pytest.mark.parametrize("depth", [1, 3, 4, 7, 32])
def test_real_fifo_capacities_and_wrap(tmp_path, depth):
    result, record, cases, _ = run(tmp_path, depth=depth)
    assert result.returncode == 0, record
    assert record["tests"] == {"passed": 4, "failed": 0, "skipped": 0}
    assert all(case.find("failure") is None for case in cases)
