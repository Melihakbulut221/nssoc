# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exact physical source deltas and unchanged observed fault/measurement contract."""

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import characterize_pcie_vco_v6_feedback_bias_v2 as m


@pytest.fixture(autouse=True)
def exact_public_inputs(monkeypatch):
    monkeypatch.setattr(
        m.core, "HYBRID", Path(__file__).parent / "fixtures/pcie_vco_v6_feedback_v1"
    )


def test_every_new_source_has_exact_inverse_to_frozen_predecessor():
    expected = m.sources()
    for old, (new, edits) in m.BRIDGES.items():
        text = expected[new.name]
        for before, after, count in reversed(edits):
            assert text.count(after) == count
            text = text.replace(after, before)
        assert text == (m.ANALOG / old).read_text()


@pytest.mark.parametrize(
    "vctrl,fault",
    [
        (0.6, ""),
        (0.85, ""),
        (0.6, "disconnect_divider_clock"),
        (0.6, "wrong_feedback_modulus"),
    ],
)
def test_only_two_real_resistor_lengths_change_in_all437_devices(vctrl, fault):
    old_c, old_rows, old_texts = m.previous.config(vctrl, fault)
    c, rows, texts = m.config(vctrl, fault)
    assert len(rows) == len(old_rows) == 437
    assert sum(r["model"] == "npn13g2" for r in rows) == 64
    changes = []
    for old, new in zip(old_rows, rows):
        assert old["path"] == new["path"]
        if old != new:
            changes.append(old["path"])
            assert old["model"] == "rppd"
            assert old["params"]["w"] == new["params"]["w"] == "1u"
            assert new == dict(old, params=dict(old["params"], l="4u"))
            assert old["params"]["l"] == "6.4u"
    assert changes == ["xchain.xdiv.xfirst.xup", "xchain.xdiv.xfirst.xun"]
    assert texts["hybrid-open.spice"] == old_texts["hybrid-open.spice"]
    for key in (
        "fixture",
        "window_s",
        "step_s",
        "stop_s",
        "extra_vectors",
        "minimum_states",
        "vctrl",
        "fault",
    ):
        assert c[key] == old_c[key]
    assert m.core.n.vectors(rows, c["extra_vectors"]) == m.core.n.vectors(
        old_rows, old_c["extra_vectors"]
    )
    assert len(m.core.n.vectors(rows, c["extra_vectors"])) == 785


@pytest.mark.parametrize(
    "before,after",
    [
        ("XUP avdd ckp", "XUP avss ckp"),
        ("w=1u l=4u", "w=2u l=4u"),
        ("l=4u", "l=6.4u"),
        (
            ".ends nssoc_clock_div2_conditioned_hbt_v3",
            "BFAKE ckp avss V=1.3\n.ends nssoc_clock_div2_conditioned_hbt_v3",
        ),
    ],
)
def test_wrong_terminal_geometry_or_ideal_bias_cannot_enter_candidate(
    monkeypatch, before, after
):
    read = Path.read_text

    def modified(path, *args, **kwargs):
        text = read(path, *args, **kwargs)
        return text.replace(before, after) if path == m.CONDITIONER else text

    monkeypatch.setattr(Path, "read_text", modified)
    with pytest.raises(ValueError, match="declared two-rppd"):
        m.config()


def test_original_functional_fault_connections_remain_real():
    c, rows, texts = m.config(fault="disconnect_divider_clock")
    assert "XDIV clkp clkp qp qn" in texts[m.CHAIN.name]
    assert "v(clkn)" in c["extra_vectors"]
    assert "clkn" not in [
        n for r in rows if r["path"].startswith("xchain.xdiv.") for n in r["nets"]
    ]
    _, _, texts = m.config(fault="wrong_feedback_modulus")
    assert "XD2N q2b q1 q1 d2b" in texts[m.core.old.counter.CIRCUIT.name]


def test_all_measurement_lifecycle_and_resource_code_stays_identical():
    for name in (
        "measurement",
        "run",
        "run_native",
        "capture",
        "deck",
        "guard",
        "native_limit",
    ):
        assert m._scope[name].__code__ is m.previous._scope[name].__code__
    assert m._scope["Meter"] is m.previous._scope["Meter"]
    assert m._scope["OWN_LIMIT"] == 80 * 1024**2
    assert m._scope["FLOOR"] == 512 * 1024**2
    assert m.previous._scope["SOURCE"] is not m.CHAIN
    assert m.previous.run.__globals__["config"] is m.previous.config
