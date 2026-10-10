# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Sequential reference proof and real arithmetic counterexamples."""

from pathlib import Path
import shutil
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from check_pcie_credit_equivalence import run


@pytest.mark.parametrize("fault", [None, "double_header", "ignore_debit", "wrong_class"])
def test_credit_accounting_equivalence(tmp_path, fault):
    binary = shutil.which("yosys") or str(ROOT / "hw/soc/tools/oss-cad-suite/bin/yosys")
    assert Path(binary).is_file(), "Real Yosys is required; do not skip the proof"
    source = ROOT / "hw/soc/rtl/pcie/soc_pcie_credit_tx.v"
    candidate = tmp_path / "candidate.v"
    text = source.read_text()
    if fault:
        before, after = {
            "double_header": ("h_idle_remaining-8'd1", "h_idle_remaining-8'd2"),
            "ignore_debit": ("credit_debit ? d_debit_remaining[11] : d_idle_remaining[11]", "d_idle_remaining[11]"),
            "wrong_class": ("consume && reserve_class_i==fc_class_i", "consume"),
        }[fault]
        assert text.count(before) == 1
        text = text.replace(before, after)
    candidate.write_text(text)
    result = run(candidate, tmp_path / "proof", Path(binary))
    if fault:
        assert result["status"] == "FAIL"
        assert "unproven $equiv" in (tmp_path / "proof/proof.log").read_text()
    else:
        assert result["status"] == "PASS_SEQUENTIAL_EQUIVALENCE"
        assert result["inputs_unchanged"]
