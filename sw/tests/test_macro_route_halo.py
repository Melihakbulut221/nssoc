# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Keep-out geometry must not close pin access or reserve macro interiors."""
import importlib.util
from itertools import combinations
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("macro_route_halo", Path(__file__).resolve().parents[2] / "hw/soc/flow/macro_route_halo.py")
halo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(halo)


def pixels(rect):
    return {(x, y) for x in range(rect[0], rect[2]) for y in range(rect[1], rect[3])}


@pytest.mark.parametrize("cut", [(2, 2, 8, 8), (-2, 2, 5, 8), (-2, -2, 12, 12), (10, 0, 12, 10), (3, -2, 7, 12)])
def test_subtraction_exact_pixel_set_and_no_overlap(cut):
    original = (0, 0, 10, 10)
    pieces = halo.subtract(original, cut)
    assert set().union(*(pixels(p) for p in pieces)) == pixels(original) - pixels(cut)
    assert sum(map(halo.area, pieces)) == len(pixels(original) - pixels(cut))
    assert all(halo.intersection(a, b) is None for a, b in combinations(pieces, 2))


@pytest.mark.parametrize("pins", [[], [(0, 4, 2, 6)], [(8, 4, 10, 6)], [(4, 0, 6, 2)], [(4, 8, 6, 10)], [(0, 4, 2, 6), (0, 5, 2, 7)], [(4, 4, 6, 6)]])
def test_ring_is_exact_minus_edge_corridors(pins):
    bounds = (0, 0, 10, 10)
    pieces, corridors = halo.halo_rectangles(bounds, 2, pins, 1)
    expected = pixels((-2, -2, 12, 12)) - pixels(bounds)
    for corridor in corridors:
        expected -= pixels(corridor)
    assert set().union(*(pixels(p) for p in pieces)) == expected
    assert sum(map(halo.area, pieces)) == len(expected)
    assert all(halo.intersection(a, b) is None for a, b in combinations(pieces, 2))
    if pins == [(4, 4, 6, 6)]:
        assert not corridors


@pytest.mark.parametrize("width,clearance", [(0, 1), (-1, 1), (1, -1)])
def test_bad_dimensions_rejected(width, clearance):
    with pytest.raises(ValueError):
        halo.halo_rectangles((0, 0, 10, 10), width, [], clearance)


@pytest.mark.parametrize("bounds", [(10, 10, 0, 0), (0, 0, 0, 10)])
def test_invalid_rectangle_rejected_even_if_signed_area_is_positive(bounds):
    with pytest.raises(ValueError):
        halo.halo_rectangles(bounds, 2, [], 1)
