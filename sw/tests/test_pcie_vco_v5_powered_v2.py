# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exact-source bias-only extension of the frozen, native-proven controller."""

import hashlib
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import diagnose_pcie_vco_v5_powered_v1 as prior
import diagnose_pcie_vco_v5_powered_v2 as method


def test_only_two_predeclared_bias_accept_lists_change():
    source = Path(prior.__file__).read_bytes()
    assert hashlib.sha256(source).hexdigest() == (
        "feba40e94fa011d20d930d68be8a71b96d0b002df7d9556622aed9a53b3a2185"
    )
    expected = source.replace(
        b"vctrl in (0.4, 0.6, 0.85)", b"vctrl in (0.4, 0.55, 0.6, 0.85)"
    ).replace(b"choices=(0.4, 0.6, 0.85)", b"choices=(0.4, 0.55, 0.6, 0.85)")
    assert Path(method.__file__).read_bytes() == expected


def small_contract():
    return dict(
        ports=[
            "AVDD",
            "VCTRL",
            "AVSS",
            "SUB",
            "BODY_SUBSTRATE",
            "WIRE_CREF",
            "CLKP",
            "CLKN",
        ]
    ), dict(hbts=[dict(id=i) for i in range(30)], vectors=["v(CLKP)", "v(CLKN)"])


def test_native_deck_changes_only_actual_external_tuning_voltage():
    comp, contract = small_contract()
    args = comp, contract, Path("/frozen/models"), [Path("/frozen/r3.osdi")]
    old = prior.deck(*args, 0.6)
    new = method.deck(*args, 0.55)
    assert old.count("Vs_vctrl VCTRL 0 PWL(0 0 500p 0.6)") == 1
    assert new == old.replace(
        "Vs_vctrl VCTRL 0 PWL(0 0 500p 0.6)",
        "Vs_vctrl VCTRL 0 PWL(0 0 500p 0.55)",
    )


@pytest.mark.parametrize("bias", [0.4, 0.6, 0.85])
def test_prior_native_recipe_unchanged(bias):
    comp, contract = small_contract()
    args = comp, contract, Path("/frozen/models"), []
    assert method.deck(*args, bias) == prior.deck(*args, bias)


@pytest.mark.parametrize("bias", [0.54, 0.550001, float("nan"), -0.55])
def test_unregistered_bias_rejects(bias):
    comp, contract = small_contract()
    with pytest.raises((ValueError, RuntimeError), match="Predeclared VCTRL"):
        method.deck(comp, contract, Path("/frozen/models"), [], bias)
