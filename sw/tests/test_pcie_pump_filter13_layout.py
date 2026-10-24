# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Source topology controls; native geometry checks run the pinned foundry decks."""
from collections import Counter
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "hw/soc/flow"))
import make_pcie_pump_filter13_v1 as maker  # noqa: E402


def sources():
    return {name: (ROOT / "hw/soc/analog/pcie" / name).read_text() for name in maker.SOURCES}


def test_core_keeps_distinct_supplies_substrate_and_ground():
    rows = maker.devices(sources())
    assert Counter(row["model"] for row in rows) == {
        "sg13_hv_nmos": 5, "sg13_hv_pmos": 4, "rppd": 3, "cap_cmim": 1,
    }
    for row in rows:
        if row["model"] == "sg13_hv_nmos":
            assert row["nets"][3] == "sub"
        if row["model"] == "sg13_hv_pmos":
            assert row["nets"][3] == "div_avdd"
        if row["model"] == "rppd":
            assert row["nets"][2] == "sub"
    high = next(row for row in rows if row["path"] == "xloop.xrhi")
    low = next(row for row in rows if row["path"] == "xloop.xrlo")
    assert high["nets"] == ["vco_avdd", "vctrl", "sub"]
    assert low["nets"] == ["vctrl", "avss", "sub"]
    assert len(maker.PORTS) == len(set(maker.PORTS)) == 7


@pytest.mark.parametrize("old,new", [
    ("w=2u l=2u", "w=2.1u l=2u"),
    ("out down sink sub", "out up sink sub"),
    ("source pb vdd vdd", "source pb vdd sub"),
])
def test_changed_pump_source_rejected(old, new):
    texts = sources()
    name = "pll_pfd_charge_pump_hv_v1.spice"
    assert old in texts[name]
    texts[name] = texts[name].replace(old, new, 1)
    with pytest.raises(ValueError, match="Frozen pump/filter source changed"):
        maker.devices(texts)


def test_changed_filter_source_rejected():
    texts = sources()
    name = "pll_pump_filter_hv_v1.spice"
    texts[name] = texts[name].replace("vctrl avss sub rppd", "vctrl sub sub rppd")
    with pytest.raises(ValueError, match="Frozen pump/filter source changed"):
        maker.devices(texts)


def test_missing_definition_rejected():
    texts = sources()
    del texts["pll_pfd_charge_pump_hv_v1.spice"]
    with pytest.raises(ValueError, match="Frozen pump/filter source changed"):
        maker.devices(texts)
