# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual SAT equivalence and rejection controls for the CRC verdict shortcut."""
from pathlib import Path
import shutil
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from check_pcie_crc_residue import REFERENCE, predicate, run

SOURCE = ROOT / "hw/soc/rtl/pcie/soc_pcie_lcrc_rx.v"


def test_all_crc_state_byte_and_sop_inputs(tmp_path):
    yosys = Path(shutil.which("yosys") or ROOT / "hw/soc/tools/oss-cad-suite/bin/yosys")
    result = run(SOURCE, tmp_path / "proof", yosys)
    assert result["status"] == "PASS" and result["inputs_unchanged"]


@pytest.mark.parametrize("old,new", [
    ("32'h00be26ed", "32'h00be26ec"),
    ("{24'b0,rx_data_i}", "{rx_data_i,24'b0}"),
    ("((rx_sop_i ? 32'hffffffff : crc) ^", "(crc ^"),
])
def test_actual_wrong_predicate_is_rejected(tmp_path, old, new):
    text = SOURCE.read_text()
    assert text.count(old) == 1
    source = tmp_path / "wrong.v"
    source.write_text(text.replace(old, new))
    yosys = Path(shutil.which("yosys") or ROOT / "hw/soc/tools/oss-cad-suite/bin/yosys")
    assert run(source, tmp_path / "proof", yosys)["status"] == "FAIL"
    # Older Yosys aborts at -verify before printing the counterexample table.
    assert "ERROR: Called with -verify and proof did fail!" in (tmp_path / "proof/proof.log").read_text()


@pytest.mark.parametrize("old,new", [
    ("length<=received-5", "length<=received-4"),
    ("state!=EMIT", "state==EMIT"),
    ("crc<=crc_next", "crc<=32'b0"),
])
def test_unrelated_behavior_change_is_rejected(old, new):
    with pytest.raises(ValueError, match="Packet state"):
        predicate(SOURCE.read_text().replace(old, new), REFERENCE.read_text())
