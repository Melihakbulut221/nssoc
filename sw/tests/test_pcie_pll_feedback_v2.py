# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exact physical change/reuse controls, alongside the frozen v1 parser tests."""

from collections import Counter
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import characterize_pcie_pll_feedback_v2 as m


def test_every_original_device_unchanged_and_exact_21_native_caps():
    before = m.native.graph(
        {"old": m.base.circuit_text()},
        m.base.config_for("nominal", m.base.CIRCUIT)["roots"],
    )
    after = m.native.graph(
        {"new": m.circuit_text()}, m.config_for("nominal", m.CIRCUIT)["roots"]
    )
    original = [x for x in after if not x["path"].endswith(".xstab")]
    added = [x for x in after if x["path"].endswith(".xstab")]
    assert original == before
    assert len(added) == 21 and len(after) == 302
    for row in added:
        assert row["model"] == "cap_cmim" and row["params"] == dict(w="2u", l="2u")
        assert row["nets"] == [row["path"].rsplit(".", 1)[0] + ".n1", "0"]
    assert Counter(x["model"] for x in after)["cap_cmim"] == 22


@pytest.mark.parametrize("case", m.CASES)
def test_same_native_case_timing_limits_and_external_stimulus(case):
    old = m.base.config_for(case, m.base.CIRCUIT)
    new = m.config_for(case, m.CIRCUIT)
    for key in old.keys() - {"sources", "roots", "method_inputs"}:
        assert old[key] == new[key]
    assert new["roots"][0][0] == m.TOP
    assert new["roots"][0][1:] == old["roots"][0][1:]
    assert m.measure is m.base.measure and m.native is m.base.native


@pytest.mark.parametrize("fault", m.FAULTS)
def test_actual_fault_connection_survives_source_revision(fault):
    old, new = m.FAULTS[fault]
    text = m.circuit_text(fault)
    assert old not in text and text.count(new) == 1
    assert text.count("XSTAB n1 vss cap_cmim w=2u l=2u") == 1


def test_changed_inherited_method_cannot_silently_change_limits(monkeypatch):
    actual = m.native.common.sha
    monkeypatch.setattr(
        m.native.common,
        "sha",
        lambda p: "0" * 64 if Path(p) == Path(m.base.__file__) else actual(p),
    )
    with pytest.raises(AssertionError):
        m.circuit_text()
    with pytest.raises(AssertionError):
        m.config_for("nominal", m.CIRCUIT)
