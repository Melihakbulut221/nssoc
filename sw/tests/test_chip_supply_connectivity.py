# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from check_chip_supply_connectivity import supply_errors


def rails():
    return {
        name: {("nssoc_chip", index)}
        for index, name in enumerate(["iovss", "iovdd", "vss", "vdd"], 1)
    }


def test_four_distinct_root_supplies():
    assert not supply_errors(rails())


def test_child_local_cluster_collision_is_never_accepted():
    value = rails()
    value["iovss"] = {("IOPad", 1)}
    assert any("child-circuit" in e for e in supply_errors(value))


def test_cross_supply_short_rejected():
    value = rails()
    value["vdd"] = value["vss"]
    assert any("share" in e for e in supply_errors(value))


def test_split_rail_rejected():
    value = rails()
    value["vdd"].add(("nssoc_chip", 99))
    assert any("distinct" in e for e in supply_errors(value))


def test_missing_or_empty_rail_rejected():
    value = rails()
    del value["vdd"]
    assert supply_errors(value)
    value["vdd"] = set()
    assert supply_errors(value)
    assert supply_errors({})
