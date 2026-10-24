# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Regress the actual pin-order change that miswired two loop experiments."""

import importlib.util
from pathlib import Path

import pytest


SOURCE = Path(__file__).resolve().parents[2] / "scripts/check_pcie_pfd_instance.py"
SPEC = importlib.util.spec_from_file_location("pfd_instance", SOURCE)
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)
MODEL = ".subckt nssoc_pfd255_wire_v1 sub vdd ref vss up fb down reset wire_cref\n"
GOOD = "XDET sub div_avdd fb avss up ref down reset pfd_wire_cref nssoc_pfd255_wire_v1\n"
OLD_CALL = "XDET sub div_avdd fb ref reset avss up down pfd_wire_cref nssoc_pfd255_wire_v1\n"


def test_actual_new_order_and_old_miswired_call():
    assert checker.check(GOOD, MODEL)["binding"]["vss"] == "avss"
    with pytest.raises(ValueError, match="named boundary mismatch"):
        checker.check(OLD_CALL, MODEL)


def test_matching_permutation_is_legal():
    words, nodes = MODEL.split(), GOOD.split()
    model = " ".join(words[:2] + list(reversed(words[2:])))
    call = " ".join(nodes[:1] + list(reversed(nodes[1:-1])) + nodes[-1:])
    assert checker.check(call, model)["binding"] == checker.check(GOOD, MODEL)["binding"]


@pytest.mark.parametrize("left,right", [(1, 2), (3, 6), (4, 8), (5, 7)])
def test_supply_polarity_reset_and_output_swaps_are_rejected(left, right):
    words = GOOD.split()
    words[left], words[right] = words[right], words[left]
    with pytest.raises(ValueError, match="named boundary mismatch"):
        checker.check(" ".join(words), MODEL)


@pytest.mark.parametrize("model,call", [
    (MODEL.replace("vss", "vdd"), GOOD),
    (MODEL, GOOD.replace("pfd_wire_cref ", "")),
    (MODEL + MODEL, GOOD),
    (MODEL, GOOD + GOOD),
])
def test_duplicate_missing_and_ambiguous_interfaces_rejected(model, call):
    with pytest.raises(ValueError):
        checker.check(call, model)
