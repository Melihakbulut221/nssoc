# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual conditioner topology, nested pin binding and measurement faults."""

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import characterize_pcie_div2_conditioned as c  # noqa: E402
import test_pcie_div2 as base_tests  # noqa: E402


def case():
    return c.old.cases()[0]


def wave():
    # Reuse the separately labelled analytical predicate oracle, never as
    # transistor evidence. Native campaigns are recorded independently.
    prior = base_tests.waveform.__wrapped__(case())
    data = {k.replace("xdiv.", "xdiv.xcore."): list(v) for k, v in prior.items()}
    data["v(xdiv.ckp)"] = [x + 0.2 for x in data["v(clkp)"]]
    data["v(xdiv.ckn)"] = [x + 0.2 for x in data["v(clkn)"]]
    for name in c.CONDITIONERS:
        data[f"v({name}.dt)"] = [0.1] * len(data["time"])
        for field, value in (("r_dc", 250.0), ("ibody", 0.0005), ("power", 0.0001)):
            data[f"@n.{name}.nr1[{field}]"] = [value] * len(data["time"])
    assert set(data) == {"time", *c.vectors(case())}
    return data


def test_exact_frozen_native_network_and_complete_nested_inventory():
    c.verify_vco()
    h, r = c.device_contract(case())
    assert len(h) == 33 and len(r) == len(set(r)) == 22
    assert set(c.CONDITIONERS) <= set(r)
    assert h["xdiv.xcore.xm.xcs"] == (
        ("xdiv.xcore.xm.se", "xdiv.ckn", "xdiv.xcore.xm.te"),
        4,
    )
    assert h["xdiv.xcore.xs.xcs"][0][1] == "xdiv.ckp"
    assert h["xosc.xftp"][0][0] == "clkp"
    assert h["xdiv.xcore.xm.xdp"][0][1] == "qn"
    assert c.old.LIMITS["min_vce_v"] == 0.4


def test_frozen_measurement_bytecode_rebound_without_module_mutation():
    assert c._native_measure.__code__ is c.old.measure.__code__
    assert c._native_measure.__globals__ is not c.old.measure.__globals__
    assert c._native_measure.__globals__["device_contract"] is c.device_contract
    assert c.old.measure.__globals__["device_contract"] is c.old.device_contract
    assert c.old.read_wave.__globals__["vectors"] is c.old.vectors
    assert "xdiv.xm.xcs" in c.old.device_contract(case())[0]
    assert "xdiv.xcore.xm.xcs" not in c.old.device_contract(case())[0]


def test_generated_deck_all_actual_native_flags_and_separate_zero_op():
    text = c.deck(case(), Path("/models"), [Path("/native.osdi")])
    assert text.count("alter @q.") == 33
    assert "show q.xdiv.xcore.xm.xt.qnpn13g2 : off" in text
    assert "XDIV clkp clkn qp qn dvdd 0 0 nssoc_clock_div2_conditioned_hbt" in text
    assert '.include "clock_div2_hbt.spice"' in text
    assert '.include "clock_div2_conditioned_hbt.spice"' in text
    assert "\nsave " + " ".join(c.vectors(case())) + "\n" in text
    assert (
        "wrdata initial-op.dat " + " ".join(c.electrical_vectors(case())) + "\n" in text
    )
    assert text.count("@n.xdiv.xsp.nr1[r_dc]") == 2
    assert " uic" not in text.lower() and ".nodeset" not in text.lower()


@pytest.mark.parametrize(
    "change",
    [
        ("l=3.6u", "l=3.5u"),
        ("XUP avdd", "XUP avss"),
        ("XSN clkn", "XSN clkp"),
        ("XSP clkp ckp", "XSP clkp clkn"),
    ],
)
def test_unapproved_resistance_or_clock_supply_connectivity_rejected(
    tmp_path, monkeypatch, change
):
    p = tmp_path / "conditioner.spice"
    p.write_text(c.CIRCUIT.read_text().replace(*change))
    monkeypatch.setattr(c, "CIRCUIT", p)
    with pytest.raises(ValueError, match="physical series/pullup"):
        c.verify_vco()


def test_measurement_observes_exact_new_devices_and_both_clock_rails():
    result = c.measure(wave(), case())
    assert result["screen_pass"] and result["functional_divide_pass"]
    assert len(result["devices"]) == 33
    assert len(result["resistor_max_selfheat_k"]) == 22
    assert set(result["conditioner_models"]) == set(c.CONDITIONERS)
    assert result["conditioner_models"]["xdiv.xsp"]["r_dc"]["mean"] == 250
    assert (
        result["conditioner_models"]["xdiv.xup"]["ibody"]["max_abs_capture"] == 0.0005
    )


@pytest.mark.parametrize(
    "vector,value,check",
    [
        ("v(xdiv.xcore.xm.te)", 0.1, "operating_headroom"),
        ("v(xdiv.xcore.ref)", 1.8, "full_capture_maximum_vce"),
        ("@q.xdiv.xcore.xref.qnpn13g2[ic]", 0.01, "current_density"),
        ("@n.xdiv.xsp.nr1[r_dc]", -1, "conditioner_resistance_positive"),
    ],
)
def test_nested_electrical_failures_are_not_hidden(vector, value, check):
    data = wave()
    data[vector][5000] = value
    result = c.measure(data, case())
    assert not result["screen_pass"] and not result["checks"][check]
    assert result["functional_divide_pass"]


def test_failed_conditioner_swing_does_not_become_logical_negative_pass():
    data = wave()
    data["v(xdiv.ckp)"] = [1.5] * len(data["time"])
    data["v(xdiv.ckn)"] = [1.5] * len(data["time"])
    result = c.measure(data, case())
    assert not result["screen_pass"]
    assert result["functional_divide_pass"]
    assert not c.old.expected_result(
        dict(
            case=dict(case(), fault="same_clock"),
            returncode=0,
            numerical={"clean": True},
            measurement=result,
        )
    )


def test_actual_native_faults_resolve_nested_frozen_pins():
    cs = {x["fault"]: x for x in c.old.cases() if x["fault"]}
    for row in cs.values():
        assert len(c.device_contract(row)[0]) == 33
    h, _ = c.device_contract(cs["no_toggle"])
    assert h["xdiv.xcore.xm.xdp"][0][1] == "qp"
    h, _ = c.device_contract(cs["same_phase"])
    assert h["xdiv.xcore.xm.xcs"][0][1] == "xdiv.ckp"
    text = c.deck(cs["same_clock"], Path("/models"), [])
    assert "XDIV clkp clkp qp qn dvdd 0 0 nssoc_clock_div2_conditioned_hbt" in text
