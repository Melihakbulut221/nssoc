# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from plan_chip_supply_probes import (
    parse_lef,
    rectangle,
    transform_box,
    rotation_degrees,
)


def lef(geometry="LAYER Metal3 ;\n      RECT 1 2 3 4 ;"):
    return (
        "MACRO Pad\n  PIN vdd\n    USE POWER ;\n    PORT\n      "
        + geometry
        + "\n    END\n  END vdd\nEND Pad\n"
    )


def test_all_ports_and_layers_are_kept():
    data = lef(
        "LAYER Metal3 ;\n      RECT 1 2 3 4 ;\n    END\n"
        "    PORT\n      LAYER TopMetal2 ;\n      RECT 2 3 4 5 ;"
    )
    pins = parse_lef(data)["Pad"]
    assert pins["vdd"] == [
        {"layer": "Metal3", "box_nm": [1000, 2000, 3000, 4000]},
        {"layer": "TopMetal2", "box_nm": [2000, 3000, 4000, 5000]},
    ]


@pytest.mark.parametrize(
    "geometry",
    [
        "LAYER Unknown ;\n RECT 1 2 3 4 ;",
        "LAYER Metal3 ;\n POLYGON 1 2 3 4 5 6 ;",
        "LAYER Metal3 ;\n VIA 1 2 v1 ;",
        "RECT 1 2 3 4 ;",
    ],
)
def test_unsupported_geometry_is_not_silently_dropped(geometry):
    with pytest.raises(ValueError):
        parse_lef(lef(geometry))


@pytest.mark.parametrize(
    "data",
    [
        lef() + lef(),
        lef().replace("USE POWER", "USE GROUND"),
        lef().replace("END vdd", "END other"),
    ],
)
def test_duplicate_or_incomplete_identity_rejected(data):
    with pytest.raises(ValueError):
        parse_lef(data)


@pytest.mark.parametrize(
    "box", ["0 0 0 2", "1 2 0 3", "0 0 1 2 3", "0 0 .0005 1", "0 0 NaN 1"]
)
def test_invalid_or_subnanometre_coordinates_rejected(box):
    with pytest.raises(ValueError):
        rectangle(box)


@pytest.mark.parametrize(
    "angle,expected",
    [
        (0, [11, 22, 13, 24]),
        (90, [6, 21, 8, 23]),
        (180, [7, 16, 9, 18]),
        (270, [12, 17, 14, 19]),
        (-90, [12, 17, 14, 19]),
        (360, [11, 22, 13, 24]),
    ],
)
def test_rotated_placement_bounds(angle, expected):
    assert transform_box([1, 2, 3, 4], angle, 10, 20) == expected


def test_nonorthogonal_transform_rejected():
    with pytest.raises(ValueError):
        transform_box([1, 2, 3, 4], 45, 0, 0)


def test_placement_quarter_turns_are_not_degrees():
    assert [rotation_degrees(i) for i in range(4)] == [0, 90, 180, 270]
    for wrong in [90, -1, True, 1.0]:
        with pytest.raises(ValueError):
            rotation_degrees(wrong)
