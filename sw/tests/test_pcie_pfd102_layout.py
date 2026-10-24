# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Preserve the simulated PFD topology while constructing its physical component."""

from collections import Counter
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "hw/soc/flow"))
import make_pcie_pfd102_v1 as maker  # noqa: E402


def sources():
    return {
        name: (ROOT / "hw/soc/analog/pcie" / name).read_text() for name in maker.SOURCES
    }


def test_pfd_preserves_clocks_reset_and_body_connections():
    rows = maker.devices(sources())
    assert Counter(r["model"] for r in rows) == {"sg13_hv_nmos": 51, "sg13_hv_pmos": 51}
    assert maker.PORTS == ["ref", "fb", "reset", "up", "down", "vdd", "vss", "sub"]
    for row in rows:
        assert row["nets"][3] == ("sub" if row["model"].endswith("nmos") else "vdd")
        assert row["params"]["l"] == "0.45u"
    by_path = {r["path"]: r for r in rows}
    assert by_path["xloop.xup.xcc.xp"]["nets"][1] == "ref"
    assert by_path["xloop.xdn.xcc.xp"]["nets"][1] == "fb"
    assert any("reset" in r["nets"] for r in rows if ".xclr." in r["path"])
    assert maker.use_direction("up") == ("SIGNAL", "OUTPUT")
    assert maker.use_direction("down") == ("SIGNAL", "OUTPUT")
    assert maker.use_direction("sub") == ("GROUND", "INOUT")


@pytest.mark.parametrize(
    "old,new",
    [
        ("XUP vdd ref clearb up", "XUP vdd fb clearb up"),
        ("XDN vdd fb clearb down", "XDN vdd ref clearb down"),
        ("XCLR both reset clearb", "XCLR both vss clearb"),
        ("w=4u l=0.45u", "w=4.5u l=0.45u"),
        ("a vdd vdd sg13_hv_pmos", "a vdd sub sg13_hv_pmos"),
    ],
)
def test_changed_phase_detector_source_is_rejected(old, new):
    texts = sources()
    name = "pll_pfd_charge_pump_hv_v1.spice"
    assert old in texts[name]
    texts[name] = texts[name].replace(old, new, 1)
    with pytest.raises(ValueError, match="Frozen PFD source changed"):
        maker.devices(texts)


def test_missing_phase_detector_source_is_rejected():
    with pytest.raises(ValueError, match="Frozen PFD source changed"):
        maker.devices({})
