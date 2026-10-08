# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Real sequential proofs at the integration and boundary configurations."""

from pathlib import Path
import shutil
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from check_pcie_chip_timing_equivalence import run


@pytest.mark.parametrize("kind,parameters", [
    ("cdc", {}),
    ("rx", {"COMPLETER_ONLY": 1}),
    ("rx", {"MAX_TLP_DWORDS": 3, "SLOTS_PER_CLASS": 1}),
    ("mbist", {"WIDTH": 16, "DEPTH": 2048}),
    ("mbist", {"WIDTH": 64, "DEPTH": 8192}),
    ("mbist", {"WIDTH": 1, "DEPTH": 1}),
    ("mbist", {"WIDTH": 5, "DEPTH": 7, "READ_LATENCY": 3}),
])
def test_actual_sequential_equivalence(tmp_path, kind, parameters):
    yosys = Path(shutil.which("yosys") or ROOT / "hw/soc/tools/oss-cad-suite/bin/yosys")
    assert yosys.is_file(), "Actual Yosys required; no skipped proof"
    result = run(kind, None, tmp_path / "proof", yosys, parameters)
    assert result["status"] == "PASS"
    assert result["inputs_unchanged"]
