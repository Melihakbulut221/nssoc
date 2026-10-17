# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exact isolated reuse, real geometry delta and unchanged /4 predicates."""

from pathlib import Path
import sys
import types

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import characterize_pcie_div4_v2 as d  # noqa: E402


def test_only_actual_interstage_geometry_changes():
    d.verify_sources()
    assert d.CIRCUIT.read_text() == d.expected_circuit()
    text = d.CIRCUIT.read_text()
    assert text.count("w=2u l=8u") == 2
    assert text.count("w=1u l=6u") == 2
    assert text.count("w=20u l=20u") == 2
    assert "XSECOND ckp ckn qp qn avdd avss sub nssoc_clock_div2_hbt" in text
    assert (
        "XFIRST clkp clkn s1p s1n avdd avss sub nssoc_clock_div2_conditioned_hbt"
        in text
    )


def test_no_imported_namespace_or_native_predicate_is_changed():
    before = dict(vars(d.prior))
    for name in (
        "deck",
        "measure",
        "read_wave",
        "read_flags",
        "initial_op",
        "accepted",
        "device_contract",
        "source_texts",
        "cases",
    ):
        assert getattr(d, name).__code__ is getattr(d.prior, name).__code__
    assert d.run.__code__.co_code == d.prior.run.__code__.co_code
    assert [
        i
        for i, (a, b) in enumerate(
            zip(d.run.__code__.co_consts, d.prior.run.__code__.co_consts)
        )
        if a != b
    ] == [d.prior.run.__code__.co_consts.index(d._old_tuple)]
    assert "20x20um" in d._new_tuple[-1] and "10x10um" in d._old_tuple[-1]
    for case in d.cases("finite"):
        d.device_contract(case)
        d.deck(case, Path("/native-models"), [Path("/model.osdi")])
    assert dict(vars(d.prior)) == before
    assert d.prior.CIRCUIT.name == "clock_div4_hbt.spice"
    assert d.prior.TOP == "nssoc_clock_div4_hbt"


@pytest.mark.parametrize("case", d.cases("finite"), ids=lambda x: x["name"])
def test_all_actual_pins_and_devices_remain_explicit(case):
    hbts, resistors = d.device_contract(case)
    assert len(hbts) == 60 and len(resistors) == 35
    assert d.device_contract(case) == d.prior.device_contract(case)
    assert d.vectors(case) == d.prior.vectors(case)
    text = d.deck(case, Path("/native-models"), [Path("/model.osdi")])
    assert 'include "clock_div4_hbt_v2.spice"' in text
    assert "XDIV clkp clkn qp qn dvdd 0 0 nssoc_clock_div4_hbt_v2" in text
    assert text.count("alter @q.") == 60


@pytest.mark.parametrize(
    "before,after",
    [
        ("w=2u l=8u", "w=2u l=4u"),
        ("w=1u l=6u", "w=1u l=3u"),
        ("w=20u l=20u", "w=10u l=10u"),
        ("XDP ckp avss", "XDP ckp avdd"),
    ],
)
def test_unapproved_geometry_or_bias_cannot_silently_run(
    tmp_path, monkeypatch, before, after
):
    p = tmp_path / "wrong.spice"
    p.write_text(d.CIRCUIT.read_text().replace(before, after, 1))
    monkeypatch.setattr(d, "CIRCUIT", p)
    with pytest.raises(ValueError, match="Exact v2 physical geometry"):
        d.verify_sources()


def test_private_native_reader_uses_new_source_inventory():
    assert isinstance(d._scope["_read"], types.FunctionType)
    assert d._scope["_read"].__globals__["vectors"] is d.vectors
    assert d._scope["CIRCUIT"] == d.CIRCUIT
    assert d._scope["__file__"] == d.__file__
    assert (
        d._scope["FROZEN"][Path(d.prior.__file__)]
        == "d4aa14a731dd5219be816d654583a264becb30df78340c8df93e264f97f2db16"
    )
