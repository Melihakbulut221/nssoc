# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Literal second-stage native-load change and unchanged fail-closed method."""

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import characterize_pcie_div4_v3 as m  # noqa: E402


def test_exact_native_geometry_and_four_changed_instance_paths():
    m.verify_sources()
    case = m.cases("pilot")[0]
    text = m.CIRCUIT.read_text()
    # Two actual latch instances each contain both changed collector loads.
    ports, rows = m.OLD.statements(text, m.CORE)
    assert ports == "clkp clkn qp qn avdd avss sub".split()
    latches = [r for r in rows if r[-1] == m.LATCH]
    assert [r[0] for r in latches] == ["xm", "xs"]
    _, loads = m.OLD.statements(text, m.LATCH)
    changed = [r for r in loads if "l=2.4u" in r]
    assert [r[0] for r in changed] == ["xrp", "xrn"]
    assert all(r[4:] == ["rppd", "w=8u", "l=2.4u", "b=0", "sw_et=1"] for r in changed)
    actual = {
        "xdiv.xsecond." + latch[0] + "." + load[0]
        for latch in latches
        for load in changed
    }
    hbts, resistors = m.device_contract(case)
    assert len(hbts) == 60 and len(resistors) == 35 and actual <= set(resistors)
    assert (hbts, resistors) == m.prior.device_contract(case)
    assert m.vectors(case) == m.prior.vectors(case)


@pytest.mark.parametrize(
    "before,after",
    [
        ("w=8u l=2.4u", "w=8u l=2.41u"),
        ("w=1u l=12.7u", "w=1u l=12.6u"),
        ("XDP qn dp se", "XDP qp dp se"),
        ("XFIRST clkp clkn", "XFIRST clkn clkp"),
        ("w=20u l=20u", "w=21u l=20u"),
    ],
)
def test_other_physical_changes_fail_source_guard(tmp_path, monkeypatch, before, after):
    p = tmp_path / "mutated.spice"
    source = m.CIRCUIT.read_text()
    assert before in source
    p.write_text(source.replace(before, after, 1))
    monkeypatch.setattr(m, "CIRCUIT", p)
    with pytest.raises(ValueError, match="Exact four native load"):
        m.verify_sources()


@pytest.mark.parametrize("case", m.cases("negative"))
def test_real_fault_changes_only_second_core(case):
    source = m.source_texts(case)
    assert source[m.OLD.CIRCUIT.name] == m.OLD.CIRCUIT.read_text()
    assert source[m.OLD.LATCH.name] == m.OLD.LATCH.read_text()
    assert source[m.BASE.CONDITIONER.name] == m.BASE.CONDITIONER.read_text()
    top = source[m.CIRCUIT.name]
    assert (
        "XFIRST clkp clkn s1p s1n avdd avss sub nssoc_clock_div2_conditioned_hbt" in top
    )
    hbts, resistors = m.device_contract(case)
    assert len(hbts) == 60 and len(resistors) == 35
    assert top.count("w=8u l=2.4u") == 2
    if case["fault"] == "second_same_clock":
        assert "XSECOND ckp ckp" in top
    else:
        assert "XSECOND ckp ckn qp qn avdd avss sub " + m.CORE + "_fault" in top


def test_unknown_fault_is_not_silently_baseline():
    with pytest.raises(ValueError, match="physical fault"):
        m.source_texts(dict(m.OLD.BASE, fault="invented"))


def test_private_reuse_leaves_limits_native_execution_and_prior_globals_unchanged():
    assert m._scope is not m.prior._scope
    assert m.prior._scope["TOP"] == "nssoc_clock_div4_hbt_v2"
    assert m.prior._scope["CIRCUIT"] == m.prior.CIRCUIT
    for name in ("run", "read_flags", "initial_op", "measure", "accepted", "deck"):
        assert m._scope[name].__code__ is m.prior._scope[name].__code__
        assert m._scope[name].__globals__ is m._scope
    assert m._scope["old"].LIMITS == m.prior._scope["old"].LIMITS


def test_two_case_pilot_targets_actual_failure_and_nominal_then_full_plan_is_unchanged():
    assert [c["name"] for c in m.cases("pilot")] == ["hot_slow", "nominal"]
    assert m.cases("finite") == m.prior.cases("finite")
    assert m.cases("negative") == m.prior.cases("negative")
    with pytest.raises(ValueError):
        m.cases("invented")


def test_native_deck_real_top_and_timezero_startup_are_unchanged():
    for case in m.cases("pilot"):
        text = m.deck(case, Path("/models"), [Path("/model.osdi")])
        assert "XDIV clkp clkn qp qn dvdd 0 0 " + m.TOP in text
        assert '.include "clock_div4_hbt_v3.spice"' in text
        assert text.count("NSSOC_DIV4_FLAG_BEGIN") == 60
        assert "\nop\nwrdata initial-op.dat " in text
        assert "tran 1e-12 2e-08 0 1e-12" in text
        assert not any(token in text.lower() for token in (" uic", ".ic ", "nodeset"))
