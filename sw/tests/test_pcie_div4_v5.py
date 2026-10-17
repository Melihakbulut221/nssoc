# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Literal native collector revision and private unchanged measurement guards."""

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import characterize_pcie_div4_v5 as m  # noqa: E402


def test_only_two_collector_lengths_change():
    m.verify_sources()
    old = m.prior.CIRCUIT.read_text().splitlines()
    new = m.CIRCUIT.read_text().splitlines()
    assert len(old) == len(new)
    diffs = [(a, b) for a, b in zip(old, new) if a != b]
    physical = [(a, b) for a, b in diffs if a.startswith("X")]
    assert len(diffs) == 5 and len(physical) == 2
    assert all(a.replace("l=4u", "l=4.4u") == b for a, b in physical)
    for case in m.cases("finite"):
        assert m.device_contract(case) == m.prior.device_contract(case)
        assert m.vectors(case) == m.prior.vectors(case)
        assert len(m.device_contract(case)[0]) == 64
        assert len(m.device_contract(case)[1]) == 42


@pytest.mark.parametrize(
    "before,after",
    [
        ("w=8u l=4.4u", "w=8u l=4.5u"),
        ("XLP ln bip lt", "XLP lp bip lt"),
        ("XLT lt lref avss", "XLT lt avss avss"),
        ("w=1u l=7u", "w=1u l=8u"),
        ("XCP lp ckp", "XCP s1p ckp"),
    ],
)
def test_unapproved_geometry_or_topology_rejected(tmp_path, monkeypatch, before, after):
    text = m.CIRCUIT.read_text()
    assert before in text
    path = tmp_path / "bad.spice"
    path.write_text(text.replace(before, after, 1))
    monkeypatch.setattr(m, "CIRCUIT", path)
    with pytest.raises(ValueError, match="Exact two-load"):
        m.verify_sources()


def test_measurement_thresholds_native_run_and_old_globals_unchanged():
    for name in ("run", "accepted", "deck", "read_flags", "initial_op"):
        assert m._scope[name].__code__ is m.prior._scope[name].__code__
        assert m._scope[name].__globals__ is m._scope
    assert m.measure.__code__ is m.prior.measure.__code__
    assert m.measure.__globals__["SECOND_CLOCK_MIN_PEAK_V"] == 0.30
    assert m._base_measure.__globals__ is m._scope
    assert m._base_measure.__code__ is m.prior._base_measure.__code__
    assert m.prior._scope["TOP"] == "nssoc_clock_div4_hbt_v4"
    assert m.prior._scope["CIRCUIT"] == m.prior.CIRCUIT
    assert m._scope["old"].LIMITS == m.prior._scope["old"].LIMITS


@pytest.mark.parametrize("case", m.cases("negative"))
def test_actual_second_stage_fault_decks_keep_new_limiter(case):
    text = m.source_texts(case)[m.CIRCUIT.name]
    assert text.count("w=8u l=4.4u") == 2
    assert len(m.device_contract(case)[0]) == 64
    deck = m.deck(case, Path("/models"), [Path("/model.osdi")])
    assert m.TOP in deck and m.prior.TOP not in deck
    assert deck.count("NSSOC_DIV4_FLAG_BEGIN") == 64
    assert "\nop\nwrdata initial-op.dat " in deck
    assert not any(x in deck.lower() for x in (" uic", ".ic ", "nodeset"))
