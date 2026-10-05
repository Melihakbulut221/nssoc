# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Physical composition and real fault sensitivity; no ideal-clock acceptance."""

import copy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import characterize_pcie_vco_v6_feedback_v1 as m


@pytest.fixture(autouse=True)
def exact_public_physical_inputs(monkeypatch):
    # Exact published native composition/wire bytes: fresh CI needs no private
    # RAM restoration, simulator, PDK installation or network access.
    monkeypatch.setattr(
        m, "HYBRID", Path(__file__).parent / "fixtures/pcie_vco_v6_feedback_v1"
    )


def test_all_native_feedback_devices_and_wire_bytes_preserved():
    c, rows, texts = m.config()
    old = m.old.chain_config()
    gold = m.n.graph(
        {Path(p).name: Path(p).read_text() for p in old["sources"]}, old["roots"]
    )
    assert [r for r in rows if not r["path"].startswith("xchain.xosc.")] == [
        r for r in gold if not r["path"].startswith("xchain.xosc.")
    ]
    assert texts["hybrid-open.spice"] == (m.HYBRID / "hybrid-open.spice").read_text()
    assert len(rows) == 437
    assert sum(r["model"] == "npn13g2" for r in rows) == 64
    assert sum(r["model"] in ("ptap1", "ntap1") for r in rows) == 13
    assert c["wire_resistors"] == 889 and c["wire_capacitors"] == 765
    assert {f"CLOAD_{x} {x.lower()} 0 50f" for x in ("CLKP", "CLKN")} <= set(
        c["fixture"]
    )


@pytest.mark.parametrize(
    "bad",
    [
        ("XDIV clkp clkn", "XDIV qp qn"),
        (
            "core_vdd avss sub nssoc_pll_feedback",
            "core_vdd avss avss nssoc_pll_feedback",
        ),
        ("wire_cref nssoc_vco_local", "avss nssoc_vco_local"),
        ("XFB qp qn", "BCLK qp avss V=sin(time)\nXFB qp qn"),
    ],
)
def test_missing_or_behavioral_connections_rejected(bad):
    text = m.SOURCE.read_text()
    assert text.count(bad[0]) == 1
    with pytest.raises(ValueError, match="topology"):
        m.topology(text.replace(*bad))


@pytest.mark.parametrize("name", m.PINS)
def test_physical_source_drift_rejected(monkeypatch, name):
    original = m.n.common.sha
    monkeypatch.setattr(
        m.n.common,
        "sha",
        lambda p: "0" * 64 if Path(p) == m.HYBRID / name else original(p),
    )
    with pytest.raises(ValueError, match="physical VCO"):
        m.config()


@pytest.mark.parametrize("fault", m.FAULTS)
def test_fault_is_real_device_connection_with_full_census(fault):
    c, rows, texts = m.config(fault=fault)
    _, gold, good = m.config()
    assert len(rows) == len(gold) == 437 and rows != gold
    changed = [name for name in texts if texts[name] != good[name]]
    assert len(changed) == 1
    old, new = m.FAULTS[fault]
    assert texts[changed[0]] == good[changed[0]].replace(old, new)
    assert c["step_s"] == 5e-12 and c["stop_s"] == 34e-9


def test_vector_contract_all_devices_and_strict_native_startup():
    c, rows, texts = m.config()
    expected = m.n.vectors(rows, c["extra_vectors"])
    assert len(expected) == len(set(expected)) == 785
    deck = m.deck(c, rows, texts)
    assert deck.count("echo NSSOC_NATIVE_FLAG_BEGIN ") == 64
    assert "op\nwrite op.raw all\nrun stream.fifo\n" in deck
    assert ".tran 5e-12 3.4e-08 0 5e-12" in deck
    assert "uic" not in deck.lower() and "gmin" not in deck.lower()


def test_tuning_only_changes_external_control():
    lo, rows, texts = m.config(0.6)
    hi, rows_hi, texts_hi = m.config(0.85)
    assert rows == rows_hi and texts == texts_hi
    delta = [k for k in lo if lo[k] != hi[k]]
    assert set(delta) == {"vctrl", "fixture"}
    assert [x for x in lo["fixture"] if not x.startswith("VCTRL")] == [
        x for x in hi["fixture"] if not x.startswith("VCTRL")
    ]


def test_contact_screen_does_not_drop_any_noncontact_device():
    c, rows, _ = m.config()
    meter = m.Meter(["time", *m.n.vectors(rows, c["extra_vectors"])], rows, c)
    assert len(meter.contacts) == 13 and len(meter.rows) == 424
    assert set(x["path"] for x in meter.contacts + meter.rows) == set(
        x["path"] for x in rows
    )
    changed = copy.deepcopy(c)
    changed["extra_vectors"].append("v(clkp)")
    with pytest.raises(AssertionError):
        m.n.vectors(rows, changed["extra_vectors"])
