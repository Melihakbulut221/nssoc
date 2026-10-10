# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual scrambler port counterexamples to feedback, seed, control masks, stalls and flush."""

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
    ("23'h210125", "23'h210121"),
    ("^next_state[lane][22]", "^next_state[lane][21]"),
    ("1:seed=23'h0607bb;", "1:seed=23'h1dbfbc;"),
    ("else if(ready_o) begin", "else if(ready_o || valid_i) begin"),
    ("if(reseed_after_i[lane])", "if(1'b0)"),
    ("end else if(flush_i) begin", "end else if(1'b0) begin"),
    ("if(scramble_i[lane*4+bit_index/8])", "if(1'b1)"),
]


@pytest.mark.parametrize("before,after", MUTANTS)
def test_real_port_counterexample_rejects_scrambler_fault(tmp_path, before, after):
    if (
        not shutil.which("iverilog")
        or not (Path(sys.executable).parent / "cocotb-config").is_file()
    ):
        pytest.skip("Real Icarus/cocotb required")
    rtl = tmp_path / "rtl"
    rtl.mkdir()
    source = ROOT / "hw/soc/rtl/pcie/soc_pcie_gen3_scrambler.v"
    original = source.read_text()
    assert original.count(before) == 1
    (rtl / source.name).write_text(original.replace(before, after))
    out = tmp_path / "run"
    run = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/check_pcie_gen3_scrambler.py"),
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
