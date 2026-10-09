# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual SAT proofs reject corrupt reads even with initially undefined RAM."""
from pathlib import Path
import shutil
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from check_pcie_rx_read_cut import run, read_expression

SOURCE = ROOT / "hw/soc/rtl/pcie/soc_pcie_rx_credit.v"


@pytest.mark.parametrize("parameters", [{}, {"MAX_TLP_DWORDS": 3, "SLOTS_PER_CLASS": 1}])
def test_actual_read_cut(tmp_path, parameters):
    yosys = Path(shutil.which("yosys") or ROOT / "hw/soc/tools/oss-cad-suite/bin/yosys")
    assert run(SOURCE, tmp_path / "proof", yosys, parameters)["status"] == "PASS"


@pytest.mark.parametrize("old,new", [
    ("packets[bank*CAP+output_index]", "packets[bank*CAP+(output_index^1)]"),
    ("dllp[output_index]", "dllp[output_index^1]"),
])
def test_actual_wrong_byte_is_rejected(tmp_path, old, new):
    text = SOURCE.read_text()
    assert text.count(old) == 1
    candidate = tmp_path / "wrong.v"
    candidate.write_text(text.replace(old, new))
    yosys = Path(shutil.which("yosys") or ROOT / "hw/soc/tools/oss-cad-suite/bin/yosys")
    result = run(candidate, tmp_path / "proof", yosys, {"MAX_TLP_DWORDS": 3, "SLOTS_PER_CLASS": 1})
    assert result["status"] == "FAIL"
    assert "SAT proof finished - model found: FAIL!" in (tmp_path / "proof/proof.log").read_text()


def test_changed_state_shape_is_rejected():
    with pytest.raises(ValueError, match="state shape"):
        read_expression(SOURCE.read_text().replace("CAP=MAX_TLP_DWORDS*4+6", "CAP=MAX_TLP_DWORDS*4+7"))
