# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""No circuit/model/control weakening in the separate bias-settling revision."""

from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import characterize_pcie_clock_trim_bias_v2 as new  # noqa: E402


def test_exact14_widths_are_the_only_native_change():
    c = dict(new.old.BASE, code=2)
    old = new.prior.circuit(c, 64, 4)
    revised = new.circuit(c)
    a = [x for x in old.splitlines() if not x.startswith((".subckt", ".ends"))]
    b = [x for x in revised.splitlines() if not x.startswith((".subckt", ".ends"))]
    pairs = [(x, y) for x, y in zip(a, b) if x != y]
    assert len(a) == len(b) and len(pairs) == 14
    assert sum("w=8u" in x and "w=16u" in y for x, y in pairs) == 2
    assert sum("w=4u" in x and "w=8u" in y for x, y in pairs) == 12
    for x, y in pairs:
        assert x.split()[:5] == y.split()[:5]
        assert x.split()[6:] == y.split()[6:]
    assert new.prior.driver.contract(old, 4) == new.prior.driver.contract(revised, 4)


def test_same_native_initialization_tolerances_loads_observers_and_time_grid():
    c = dict(new.old.BASE, code=2, step_s=0.5e-12)
    hbts = new.prior.driver.contract(new.circuit(c), 4)
    args = (c, Path("/models"), [Path("/runtime.osdi")], 0.9e-12, 0.92e-12, hbts)
    old = new.prior.deck(*args)
    actual = new.deck(*args)
    assert actual == old.replace(new.prior.TOP, new.TOP).replace(
        new.prior.FILE, new.FILE
    )
    assert actual.count("alter @q.xosc.") == 30
    assert "tran 5e-13 12n 0 5e-13" in actual


def test_exact_seven_corner_and_pilot_identity():
    rows = new.cases("seven")
    assert len(rows) == len({c["name"] for c in rows}) == 14
    assert new.cases("fast_pilot") == rows[-2:]
    for label, mods in new.prior.driver.parent.TUNING:
        pair = [r for r in rows if r["name"].startswith(label + "_")]
        assert len(pair) == 2 and pair[0]["code"] == pair[1]["code"]
        assert all(all(r[k] == v for k, v in mods.items()) for r in pair)
        assert all(r["step_s"] == 0.5e-12 for r in pair)


def test_frozen_prior_mutation_rejected(monkeypatch):
    monkeypatch.setattr(new, "PRIOR_SHA", "0" * 64)
    with pytest.raises(ValueError, match="Frozen"):
        new.circuit(dict(new.old.BASE, code=0))
