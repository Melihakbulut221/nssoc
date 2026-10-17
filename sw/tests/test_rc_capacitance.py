# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from audit_rc_capacitance import compare, numeric, project


def matrix(text, mapping=None):
    return project(text.splitlines(), mapping or {"a": "A", "b": "B", "0": "GND"})[0]


def test_segmented_rc_preserves_pair_values():
    ref = matrix("C1 a b 1p\nC2 a 0 2f")
    rc = matrix("R1 a ax 1k\nC1 ax b 0.25p\nC2 a b 750f\nC3 ax 0 2e-15",
                {"a": "A", "ax": "A", "b": "B", "0": "GND"})
    result = compare(ref, rc)
    assert result["status"] == "PASS_CAPACITANCE_MATRIX_ONLY"
    assert result["qualified_pex"] is False


def test_grounding_coupling_fails_even_with_same_capacitor_sum():
    ref = matrix("C1 a b 1p")
    grounded = matrix("C1 a 0 .5p\nC2 b 0 .5p")
    assert sum(ref.values()) == sum(grounded.values())
    result = compare(ref, grounded)
    assert (result["missing_pairs"], result["extra_pairs"]) == (1, 2)
    assert result["status"] == "FAIL_RC_CAPACITANCE_CONSERVATION"


def test_resistor_cannot_hide_wrong_net_identity():
    with pytest.raises(ValueError, match="crosses"):
        matrix("R1 a b 1\nC1 a 0 1p")


@pytest.mark.parametrize("text,reason", [
    ("C1 a missing 1p", "Unmapped"),
    ("C1 a a 1p", "self-pair"),
    ("C1 a b 1p\nc1 a 0 2p", "duplicate"),
    ("C1 a b {value}", "Unsupported"),
    ("C1 a b 0", "Nonpositive"),
    ("C1 a b -1p", "negative"),
    ("C1 a b 1e999", "nonfinite"),
    ("R1 a a 1", "No capacitors"),
    (".include extra.sp\nC1 a b 1p", "External"),
    (".subckt x a b\nC1 a b 1p\n.ends\n.subckt y a b", "single-subcircuit"),
])
def test_malformed_or_incomplete_exports_fail(text, reason):
    with pytest.raises(ValueError, match=reason):
        matrix(text)


def test_case_collision_is_rejected():
    with pytest.raises(ValueError, match="Conflicting"):
        matrix("C1 a b 1p", {"a": "A", "A": "WRONG", "b": "B"})


def test_valid_suffixes_whitespace_and_comments():
    values = matrix("  c1 A b .001n ; comment\n* comment\nC2 a B 2F $ comment")
    assert values[("A", "B")] == pytest.approx(1.002e-12)
    assert numeric("1M") == .001
    assert numeric("1MEG") == 1e6


def test_same_pair_changed_value_is_rejected():
    result = compare(matrix("C1 a b 1p"), matrix("C1 a b 1.1p"))
    assert result["mismatched_pairs"] == 1
    assert result["status"] == "FAIL_RC_CAPACITANCE_CONSERVATION"


def test_dollar_in_node_identity_is_not_a_comment():
    values = matrix("C1 a$1 b 1p", {"a$1": "A", "b": "B"})
    assert values[("A", "B")] == 1e-12
