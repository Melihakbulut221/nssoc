# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Freeze actual device dimensions and polarity in the CML interface source."""

import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "follower_layout", ROOT / "hw/soc/flow/make_pcie_cml_input_follower_v1.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_native_interface_source_has_expected_circuit():
    rows = MODULE.devices((ROOT / MODULE.CIRCUIT).read_text())
    assert [r["nets"] for r in rows] == [
        ["avdd", "cp", "bp", "sub"],
        ["avdd", "cn", "bn", "sub"],
        ["bp", "avss", "sub"],
        ["bn", "avss", "sub"],
    ]
    assert all(
        r["model"] == "npn13g2" and r["params"] == dict(nx="2", we="0.07u", le="0.9u")
        for r in rows[:2]
    )
    assert all(
        r["model"] == "rppd"
        and r["params"] == dict(w="2.0u", l="8.0u", ps="0.0u", b="0", m="1", sw_et="1")
        for r in rows[2:]
    )


@pytest.mark.parametrize(
    "old,new",
    [
        ("avdd cp bp sub", "avdd cn bp sub"),
        ("nx=2", "nx=1"),
        ("l=8.0u", "l=4.0u"),
        ("bp avss sub", "bp avdd sub"),
        ("XFN avdd cn bn sub npn13g2 nx=2 we=0.07u le=0.9u", ""),
    ],
)
def test_changed_native_source_requires_explicit_requalification(old, new):
    source = (ROOT / MODULE.CIRCUIT).read_text()
    assert old in source
    with pytest.raises(ValueError, match="frozen circuit"):
        MODULE.devices(source.replace(old, new))
