# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Strict new native limiter census, literal topology and unchanged old guards."""

import ast
import copy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import characterize_pcie_div4_v4 as m  # noqa: E402


def test_exact_real_limiter_and_all_old_hbt_terminals_preserved():
    m.verify_sources()
    c = m.cases("pilot")[0]
    hbts, resistors = m.device_contract(c)
    old_hbts, old_resistors = m.prior.device_contract(c)
    assert len(hbts) == 64 and len(resistors) == 42
    assert {n: hbts[n] for n in old_hbts} == old_hbts
    assert set(old_resistors) <= set(resistors)
    added = set(hbts) - set(old_hbts)
    assert added == {"xdiv.xlp", "xdiv.xln", "xdiv.xlt", "xdiv.xlref"}
    assert hbts["xdiv.xlp"] == (("xdiv.ln", "xdiv.bip", "xdiv.lt"), 2)
    assert hbts["xdiv.xln"] == (("xdiv.lp", "xdiv.bin", "xdiv.lt"), 2)
    assert hbts["xdiv.xlt"] == (("xdiv.lt", "xdiv.lref", "0"), 4)
    assert len(m.CONDITIONERS) == 11 and set(m.CONDITIONERS) <= set(resistors)
    for path in added:
        assert "@q." + path + ".qnpn13g2[ic]" in m.vectors(c)
        assert "v(" + path + ".t)" in m.vectors(c)
    assert len(m.vectors(c)) == 257


@pytest.mark.parametrize(
    "before,after",
    [
        ("XLP ln bip lt", "XLP lp bip lt"),
        ("XLT lt lref avss", "XLT lt avss avss"),
        ("w=1u l=9u", "w=1u l=8u"),
        ("w=8u l=4u", "w=8u l=5u"),
        ("XCP lp ckp", "XCP s1p ckp"),
        ("XFIRST clkp clkn", "XFIRST clkn clkp"),
    ],
)
def test_unapproved_physical_change_rejected(tmp_path, monkeypatch, before, after):
    p = tmp_path / "bad.spice"
    text = m.CIRCUIT.read_text()
    assert before in text
    p.write_text(text.replace(before, after, 1))
    monkeypatch.setattr(m, "CIRCUIT", p)
    with pytest.raises(ValueError, match="Exact native limiter"):
        m.verify_sources()


def test_metadata_and_strict_resource_floor_match_new_actual_census():
    tree = ast.parse(m.TRANSFORMED_SOURCE["run"])
    values = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.keyword) and n.arg in (
            "hbt_count",
            "resistor_count",
            "capacitor_count",
            "mos_count",
        ):
            values[n.arg] = ast.literal_eval(n.value)
    assert values == dict(
        hbt_count=64, resistor_count=42, capacitor_count=12, mos_count=1
    )
    assert "600 * 1024 ** 2" in m.TRANSFORMED_SOURCE["run"]
    assert "all64" in m.TRANSFORMED_SOURCE["run"]
    assert "all60" not in m.TRANSFORMED_SOURCE["run"]
    assert m.prior._scope["TOP"] == "nssoc_clock_div4_hbt_v2"
    assert m._scope["old"].LIMITS == m.prior._scope["old"].LIMITS
    for n in ("accepted", "initial_op", "deck"):
        assert m._scope[n].__code__ is m.prior._scope[n].__code__
        assert m._scope[n].__globals__ is m._scope


@pytest.mark.parametrize("case", m.cases("negative"))
def test_faults_still_target_second_latch_and_keep_limiter(case):
    texts = m.source_texts(case)
    assert len(m.device_contract(case)[0]) == 64
    assert "XLP ln bip lt sub npn13G2 Nx=2" in texts[m.CIRCUIT.name]
    assert "XLREF lref lref avss sub npn13G2 Nx=1" in texts[m.CIRCUIT.name]
    assert texts[m.OLD.LATCH.name] == m.OLD.LATCH.read_text()
    assert texts[m.BASE.CONDITIONER.name] == m.BASE.CONDITIONER.read_text()


@pytest.mark.parametrize(
    "peak,old_safe,want",
    [(0.31, True, True), (0.299, True, False), (0.31, False, False)],
)
def test_added_clock_target_cannot_hide_old_safety_failure(
    monkeypatch, peak, old_safe, want
):
    original = dict(
        interfaces={"second_input": dict(diff_range_v=[-peak, peak])},
        checks={"all_old_checks": old_safe},
        screen_pass=old_safe,
    )
    monkeypatch.setattr(m, "_base_measure", lambda *args: copy.deepcopy(original))
    data = {"time": [4e-9, 20e-9]}
    for n in ("bip", "bin", "lp", "ln"):
        data[f"v(xdiv.{n})"] = [2.0, 2.2]
    result = m.measure(data, m.cases("pilot")[0])
    assert result["screen_pass"] is want
    assert result["checks"]["all_old_checks"] is old_safe


def test_native_flags_and_deck_follow_all64_actual_devices():
    c = m.cases("pilot")[0]
    text = m.deck(c, Path("/models"), [Path("/model.osdi")])
    assert text.count("NSSOC_DIV4_FLAG_BEGIN") == 64
    assert "XDIV clkp clkn qp qn dvdd 0 0 " + m.TOP in text
    assert "\nop\nwrdata initial-op.dat " in text
    assert not any(s in text.lower() for s in (" uic", ".ic ", "nodeset"))
    assert [c["name"] for c in m.cases("pilot")] == ["hot_slow", "nominal"]
