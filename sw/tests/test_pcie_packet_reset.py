# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Real reset-cone induction and asynchronous/latency fault counterexamples."""

from pathlib import Path
import shutil
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from check_pcie_packet_reset import run


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "synchronous_assertion",
        "early_release",
        "wrong_reset_state",
        "clock_gated_output",
    ],
)
def test_packet_reset_after_por(tmp_path, fault):
    yosys = Path(shutil.which("yosys") or ROOT / "hw/soc/tools/oss-cad-suite/bin/yosys")
    assert yosys.is_file(), "Actual Yosys required; no skipped proof"
    out = tmp_path / "proof"
    result = run(ROOT / "hw/soc/rtl/soc_top.v", out, yosys, fault)
    assert result["inputs_unchanged"]
    assert result["status"] == ("FAIL" if fault else "PASS_AFTER_POR")
    if fault:
        assert (out / "trace.vcd").is_file()
