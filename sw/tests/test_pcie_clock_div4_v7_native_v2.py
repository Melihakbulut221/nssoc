# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Saved real KLayout passive syntax plus geometry/body/multiplicity controls."""

from pathlib import Path
import hashlib
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "hw/soc/flow"))
import check_pcie_clock_div4_v7 as prior
import check_pcie_clock_div4_v7_v2 as m

FIXTURE_SHA = "8a6af77904a94ec75c2b220a7017f5c179e1e8818cda437bf4af1d80c30fe4a6"
FIXTURE = (
    Path(__file__).parent / "fixtures/pcie_clock_div4_v7/native-deep-extracted.cir"
)


def original():
    text = FIXTURE.read_text()
    assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == FIXTURE_SHA
    return text


def test_saved_native_74device_result_passes_exact_fields_old_failure_retained():
    text = original()
    with pytest.raises(ValueError, match="unmultiplied straight native passive"):
        prior.validate_expanded_devices(text)
    m.validate_expanded_devices(text)
    assert text.count("ps=0u") == 33 and text.count(" cap_cmim ") == 6


@pytest.mark.parametrize(
    "before,after",
    [
        ("ps=0u", "ps=1u"),
        ("ps=0u ", " "),
        ("m=1", "m=4"),
        ("b=0", "b=1"),
        ("w=1u l=4u", "w=2u l=4u"),
        ("w=1u l=4u", "w=1u l=6.4u"),
        ("A=400p", "A=399p"),
        ("P=80u", "P=79u"),
        ("A=400p", "A=0p"),
        ("P=80u", "P=80n"),
        ("w=20u l=20u A=400p P=80u", "w=10u l=20u A=200p P=60u"),
        ("A=400p", "A=400p A=400p"),
        ("A=400p", "A=NaNp"),
        ("ptap1 A=72p", "ptap1 A=68p"),
        ("P=144u", "P=136u"),
        ("Nx=2", "Nx=1"),
        ("we=70n", "we=71n"),
    ],
)
def test_real_saved_netlist_tampering_rejected(before, after):
    text = original()
    assert before in text
    with pytest.raises(ValueError):
        m.validate_expanded_devices(text.replace(before, after, 1))
