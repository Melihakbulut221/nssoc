# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual gearbox port counterexamples to bit loss, overflow, lane mixing and stale flush."""

from pathlib import Path
import json
import os
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from cocotb_results import count_results  # noqa: E402


MUTANTS = [
    ("tx_bits[lane]>>32", "tx_bits[lane]>>31"),
    ("rx_bits[lane]>>130", "rx_bits[lane]>>128"),
    ("tx_left<=8'd30", "tx_left<=8'd62"),
    ("rx_left<=8'd128", "rx_left<=8'd160"),
    ("tx_payload_i[lane*128+:128]", "tx_payload_i[0+:128]"),
    ("tx_header_i}<<tx_left", "{tx_header_i[0],tx_header_i[1]}}<<tx_left"),
    ("end else if(flush_i) begin", "end else if(1'b0) begin"),
]


@pytest.mark.parametrize("before,after", MUTANTS)
def test_real_port_counterexample_rejects_gearbox_fault(tmp_path, before, after):
    if (
        not shutil.which("iverilog")
        or not (Path(sys.executable).parent / "cocotb-config").is_file()
    ):
        pytest.skip("Real Icarus/cocotb required")
    rtl = tmp_path / "rtl"
    rtl.mkdir()
    source = ROOT / "hw/soc/rtl/pcie/soc_pcie_gen3_gearbox.v"
    original = source.read_text()
    assert original.count(before) == 1
    (rtl / source.name).write_text(original.replace(before, after))
    out = tmp_path / "run"
    run = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/check_pcie_gen3_gearbox.py"),
            "--out",
            str(out),
            "--rtl-dir",
            str(rtl),
        ],
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    (tmp_path / "mutation.log").write_text(run.stdout + run.stderr)
    assert run.returncode == 1
    record = json.loads((out / "result.json").read_text())
    assert record["status"] == "FAIL"
    passed, failed, skipped = count_results([out / "results.xml"])
    assert passed + failed == 3 and failed > 0 and skipped == 0
    assert "AssertionError" in (out / "simulation.log").read_text()
