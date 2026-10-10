# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Pin the independently simulated differential gain/follower circuit."""

import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "gain_follower_layout", ROOT / "hw/soc/flow/make_pcie_cml_gain_follower_v1.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_gain_polarity_tail_and_followers():
    rows = MODULE.devices((ROOT / MODULE.CIRCUIT).read_text())
    assert [r["nets"] for r in rows] == [
        ["an", "cp", "atail", "sub"],
        ["ap", "cn", "atail", "sub"],
        ["avdd", "ap", "sub"],
        ["avdd", "an", "sub"],
        ["atail", "avss", "sub"],
        ["avdd", "ap", "bp", "sub"],
        ["avdd", "an", "bn", "sub"],
        ["bp", "avss", "sub"],
        ["bn", "avss", "sub"],
    ]
    assert all(
        rows[i]["model"] == "npn13g2"
        and rows[i]["params"] == dict(nx="2", we="0.07u", le="0.9u")
        for i in [0, 1, 5, 6]
    )
    assert all(
        rows[i]["model"] == "rppd"
        and rows[i]["params"]
        == dict(w="2.0u", l=length, ps="0.0u", b="0", m="1", sw_et="1")
        for i, length in [
            (2, "2.0u"),
            (3, "2.0u"),
            (4, "8.0u"),
            (7, "8.0u"),
            (8, "8.0u"),
        ]
    )


@pytest.mark.parametrize(
    "old,new",
    [
        ("XAP an cp atail", "XAP an cn atail"),
        ("nx=2", "nx=1"),
        ("l=2.0u", "l=4.0u"),
        ("atail avss sub", "atail avdd sub"),
        ("XFP avdd ap bp sub", "XFP avdd cp bp sub"),
        ("XRN bn avss sub rppd w=2.0u l=8.0u ps=0.0u b=0 m=1 sw_et=1", ""),
    ],
)
def test_source_change_requires_requalification(old, new):
    source = (ROOT / MODULE.CIRCUIT).read_text()
    assert old in source
    with pytest.raises(ValueError, match="frozen circuit"):
        MODULE.devices(source.replace(old, new))
