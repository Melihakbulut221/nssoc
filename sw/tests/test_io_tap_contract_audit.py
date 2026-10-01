# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Pure arithmetic/hierarchy controls; these tests do not assert physical LVS."""

from decimal import Decimal
import importlib.util
import json
from pathlib import Path
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/io_tap_contract_audit.py"
SPEC = importlib.util.spec_from_file_location("io_tap_contract_audit", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_terminal_order_and_hierarchical_net_mapping():
    text = """.global sub!
.subckt leaf tap well
R1 tap well ptap1 A=2p P=7u
R2 well tap ptap1 A=3p P=9u
.ends
.subckt top vss iovss
X1 vss sub! leaf
X2 iovss sub! leaf
.ends
"""
    taps = MODULE.flatten_taps(text, "top")
    assert len(MODULE.combine(taps)) == 4
    joined = MODULE.combine(taps, {"iovss": "vss"})
    assert len(joined) == 2
    assert {(t["tie"], t["well"], t["area_um2"], t["perimeter_um"]) for t in joined} == {
        ("vss", "sub!", Decimal(4), Decimal(14)),
        ("sub!", "vss", Decimal(6), Decimal(18)),
    }


def test_local_wells_do_not_merge_across_instances():
    text = ".subckt leaf tie\nR0 tie local ptap1 A=2p P=6u\n.ends\n.subckt top vss\nX0 vss leaf\nX1 vss leaf\n.ends\n"
    taps = MODULE.flatten_taps(text, "top")
    assert len(MODULE.combine(taps)) == 2
    assert {t["well"] for t in taps} == {"top/x0/local", "top/x1/local"}


@pytest.mark.parametrize("value,expected", [("1.97n", "0.00000000197"), ("24.01p", "0.00000000002401"), ("19.6u", "0.0000196"), ("1e-6", "0.000001")])
def test_exact_spice_units(value, expected):
    assert MODULE.quantity(value) == Decimal(expected)


@pytest.mark.parametrize("value", ["nan", "inf", "-1p", "0", "1um", "1q"])
def test_bad_quantity_rejected(value):
    with pytest.raises(MODULE.ContractError):
        MODULE.quantity(value)


@pytest.mark.parametrize("body", ["R0 tie sub! ptap1 A=2p", "R0 tie sub! ptap1 A=2p P=6u Perim=6u", "R0 tie sub! extra ptap1 A=2p P=6u", "X0 tie sub! unknown", "R0 tie sub! ptap1 A=2p A=3p P=6u"])
def test_incomplete_or_ambiguous_contract_rejected(body):
    with pytest.raises(MODULE.ContractError):
        MODULE.flatten_taps(f".subckt top tie\n{body}\n.ends\n", "top")


def test_recursive_or_wrong_arity_rejected():
    for text in [".subckt top tie\nX0 tie top\n.ends\n", ".subckt leaf a b\n.ends\n.subckt top tie\nX0 tie leaf\n.ends\n"]:
        with pytest.raises(MODULE.ContractError):
            MODULE.flatten_taps(text, "top")


@pytest.mark.parametrize("extra", ["m=2", "mf=2", "s=2", "unknown=1", "w=2u", "r=nan", "w=2u l=-1u"])
def test_tap_multiplier_unknown_or_bad_legacy_metadata_rejected(extra):
    with pytest.raises(MODULE.ContractError):
        MODULE.flatten_taps(f".subckt top tie\nR0 tie sub! ptap1 A=2p P=6u {extra}\n.ends\n", "top")


def test_subcircuit_multiplier_cannot_silently_undercount_taps():
    text = ".subckt leaf tie\nR0 tie sub! ptap1 A=2p P=6u\n.ends\n.subckt top tie\nX0 tie leaf m=2\n.ends\n"
    with pytest.raises(MODULE.ContractError, match="multiplied subcircuit"):
        MODULE.flatten_taps(text, "top")


def test_explicit_ap_precedes_legacy_dimensions_as_pinned_reader_requires():
    # Not a rectangular W*L/2(W+L) contract: explicit A/P take precedence.
    text = ".subckt top tie\nR0 tie sub! ptap1 A=17p Perim=23u r=9.999 w=2u l=3u\n.ends\n"
    tap = MODULE.flatten_taps(text, "top")[0]
    assert tap["area_um2"] == Decimal(17)
    assert tap["perimeter_um"] == Decimal(23)


def test_join_only_does_not_hide_perimeter_error():
    ref = ".subckt sg13g2_IOPadVdd iovss vss\nR0 iovss sub! ptap1 A=3p P=7u\nR1 vss sub! ptap1 A=4p P=8u\n.ends\n"
    flat = ".subckt sg13g2_IOPadVdd iovss iovss$1 vss\nR0 iovss sub! ptap1 A=1p P=4u\nR1 iovss$1 sub! ptap1 A=2p P=6u\nR2 vss sub! ptap1 A=4p P=8u\n.ends\n"
    result = MODULE.audit(ref, flat, flat)
    assert result["parameter_comparisons"][0] == {"tie": "iovss", "area_delta_um2": Decimal(0), "perimeter_delta_um": Decimal(3), "parameters_equal": False}
    assert result["parameter_comparisons"][1]["parameters_equal"]
    assert not result["lvs_accepted"]


@pytest.mark.parametrize("output_kind", ["input", "existing"])
def test_cli_refuses_overwriting_input_or_existing_output(tmp_path, monkeypatch, output_kind):
    text = ".subckt sg13g2_IOPadVdd iovss vss\nR0 iovss sub! ptap1 A=3p P=7u\nR1 vss sub! ptap1 A=4p P=8u\n.ends\n"
    source = tmp_path / "input.cir"
    source.write_text(text)
    output = source if output_kind == "input" else tmp_path / "existing.json"
    if output != source:
        output.write_text("retain me")
    before = output.read_bytes()
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--reference", str(source), "--flat", str(source), "--deep", str(source), "--output", str(output)])
    with pytest.raises((MODULE.ContractError, FileExistsError)):
        MODULE.main()
    assert output.read_bytes() == before


def test_equal_parameters_still_never_accept_lvs(tmp_path, monkeypatch):
    source = tmp_path / "input.cir"
    source.write_text(".subckt sg13g2_IOPadVdd iovss vss\nR0 iovss sub! ptap1 A=3p P=7u\nR1 vss sub! ptap1 A=4p P=8u\n.ends\n")
    output = tmp_path / "new.json"
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--reference", str(source), "--flat", str(source), "--deep", str(source), "--output", str(output)])
    MODULE.main()
    result = json.loads(output.read_text())
    assert all(item["parameters_equal"] for item in result["parameter_comparisons"])
    assert result["status"] == "DIAGNOSTIC_ONLY_STRICT_LVS_OPEN"
    assert not result["lvs_accepted"] and not result["manufacturing_approval"]
    assert set(result["input_sha256"]) == {str(source), str(SCRIPT)}
