# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""A solver's fatal message or unfinished refinement overrides a zero exit."""
import importlib.util
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[2] / "hw/soc/flow/check_fastercap_completion.py"
SPEC = importlib.util.spec_from_file_location("fastercap_completion", PATH)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)
LOG = """Running FasterCap version 6.0.7
Auto calculation with max error: 0.003
Iteration number #1
Capacitance matrix is:
Dimension 2 x 2
g1_A 2e-9 -1e-9
g2_B -1e-9 2e-9
Weighted Frobenius norm of the difference between capacitance (auto option): 0.002
Total allocated memory: 1000 kilobytes
Total time: 1.5s (0 days, 0 hours, 0 mins, 1 s)
"""


def test_completed_matrix_units_and_numerical_scope():
    result = MOD.check(LOG, 0, .003)
    assert result["conductors"] == ["g1_A", "g2_B"]
    assert result["matrix_F"][0] == pytest.approx([2e-15, -1e-15], abs=1e-25)
    assert result["last_relative_norm"] == .002
    assert not result["qualified_pex"] and not result["manufacturing_approval"]


@pytest.mark.parametrize("text,code,tolerance", [
    (LOG + "Error: Out of memory, program execution stopped!\n", 0, .003),
    (LOG, 1, .003),
    (LOG, -9, .003),
    (LOG, 0, .001),
    (LOG, 0, float("nan")),
    (LOG.replace("option): 0.002", "option): 0.004"), 0, .003),
    (LOG.replace("option): 0.002", "option): nan"), 0, .003),
    (LOG[:LOG.index("Total time:")], 0, .003),
    (LOG.replace("Total allocated", "Iteration number #2\nTotal allocated"), 0, .003),
    (LOG.replace("g2_B", "g1_A"), 0, .003),
    (LOG.replace("2e-9 -1e-9", "nan -1e-9"), 0, .003),
    (LOG.replace("g2_B -1e-9 2e-9\n", ""), 0, .003),
    (LOG.replace("Iteration number #1", "Warning: unconverged solve"), 0, .003),
])
def test_failed_or_incomplete_output_cannot_pass(text, code, tolerance):
    with pytest.raises(ValueError):
        MOD.check(text, code, tolerance)


def test_earlier_iteration_warning_is_recorded_but_final_warning_fails():
    marker = "Iteration number #1\n"
    previous = """Iteration number #0
Capacitance matrix is:
Dimension 2 x 2
g1_A 2e-9 1e-9
g2_B 1e-9 2e-9
Warning: capacitance matrix has a non-negative off-diagonal element at row 1 col 2
"""
    result = MOD.check(LOG.replace(marker, previous + marker), 0, .003)
    assert len(result["earlier_iteration_warnings"]) == 1
    final_warning = previous.splitlines()[-1] + "\n"
    with pytest.raises(ValueError, match="Final matrix"):
        MOD.check(LOG.replace("Total allocated", final_warning + "Total allocated"), 0, .003)
