# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual APB port counterexamples to ownership, phase and late-completion faults."""

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
    ("wire request_zero=m0_psel_i && !served_zero;", "wire request_zero=m0_psel_i;"),
    ("wire request_one=m1_psel_i && !served_one;", "wire request_one=m1_psel_i;"),
    ("assign m0_pready_o=done && !owner;", "assign m0_pready_o=done;"),
    ("state<=SETUP;", "state<=ACCESS;"),
    (
        "assign psel_o=rst_ni && state!=IDLE && present;",
        "assign psel_o=rst_ni && state!=IDLE;",
    ),
    ("state<=IDLE;prefer_one<=!owner;", "state<=IDLE;prefer_one<=1'b0;"),
    ("assign m1_pslverr_o=m1_pready_o && pslverr_i;", "assign m1_pslverr_o=1'b1;"),
]


@pytest.mark.parametrize("before,after", MUTANTS)
def test_real_port_counterexample_rejects_arbiter_fault(tmp_path, before, after):
    if (
        not shutil.which("iverilog")
        or not (Path(sys.executable).parent / "cocotb-config").is_file()
    ):
        pytest.skip("Real Icarus/cocotb required")
    rtl = tmp_path / "rtl"
    rtl.mkdir()
    source = ROOT / "hw/soc/rtl/pcie/soc_pcie_apb_arbiter.v"
    original = source.read_text()
    assert original.count(before) == 1
    (rtl / source.name).write_text(original.replace(before, after))
    out = tmp_path / "run"
    run = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/check_pcie_apb_arbiter.py"),
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
    assert passed + failed == 6 and failed > 0 and skipped == 0
    assert "AssertionError" in (out / "simulation.log").read_text()
