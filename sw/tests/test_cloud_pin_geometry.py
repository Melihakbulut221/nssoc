# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Off-origin asymmetric rectangles expose rotation/reflection mistakes."""
import importlib.util
from pathlib import Path
import pytest

path = Path(__file__).resolve().parents[2] / 'scripts/probe_cloud_newer_congestion.py'
spec = importlib.util.spec_from_file_location('pin_geometry', path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


@pytest.mark.parametrize('orientation,expected', [
    ('R0', (13, 16, 16, 20)), ('R90', (4, 15, 8, 18)),
    ('R180', (6, 6, 9, 10)), ('R270', (14, 8, 18, 11)),
    ('MY', (6, 16, 9, 20)), ('MYR90', (4, 8, 8, 11)),
    ('MX', (13, 6, 16, 10)), ('MXR90', (14, 15, 18, 18)),
])
def test_rotation_and_origin(orientation, expected):
    assert m.transformed_rectangle((2, 3, 5, 7), orientation, (11, 13)) == expected


def test_invalid_geometry_not_silently_repaired():
    with pytest.raises(AssertionError):
        m.transformed_rectangle((5, 3, 2, 7), 'R0', (0, 0))
    with pytest.raises(AssertionError):
        m.transformed_rectangle((2, 3, 5, 7), 'UNKNOWN', (0, 0))
