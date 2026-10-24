# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Physical continuity must reject open wires and unconnected route fragments."""
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / 'hw/soc/flow/check_routed_net_paths.py'
spec = importlib.util.spec_from_file_location('routed_paths', SCRIPT)
paths = importlib.util.module_from_spec(spec)
spec.loader.exec_module(paths)


def test_bridge_and_removed_bridge():
    nodes = [('M2', (0, 0, 2, 2)), ('M2', (8, 0, 10, 2)),
             ('M2', (1, 0, 9, 2))]
    assert paths.connectivity(nodes, [], {'A': 0, 'B': 1})['all_pins_connected']
    assert not paths.connectivity(nodes[:2], [], {'A': 0, 'B': 1})['all_pins_connected']


def test_crossing_layers_need_via():
    nodes = [('M2', (0, 0, 10, 2)), ('M3', (4, -4, 6, 6))]
    assert not paths.connectivity(nodes, [], {'A': 0, 'B': 1})['all_pins_connected']
    assert paths.connectivity(nodes, [(0, 1)], {'A': 0, 'B': 1})['all_pins_connected']


def test_orphan_shape_is_failure_even_when_pins_connected():
    nodes = [('M2', (0, 0, 4, 2)), ('M2', (3, 0, 6, 2)),
             ('M2', (20, 20, 22, 22))]
    result = paths.connectivity(nodes, [], {'A': 0, 'B': 1})
    assert result['all_pins_connected']
    assert not result['all_route_shapes_connected']


@pytest.mark.parametrize('second', [(2, 0, 4, 2), (2, 2, 4, 4), (3, 0, 5, 2)])
def test_edge_contact_corner_contact_and_gap_are_not_area_connections(second):
    assert not paths.connectivity([('M2', (0, 0, 2, 2)), ('M2', second)],
                                  [], {'A': 0, 'B': 1})['all_pins_connected']


def test_declared_cell_port_connects_multiple_internal_shapes():
    nodes = [('M2', (0, 0, 2, 2)), ('M2', (8, 0, 10, 2)),
             ('M2', (9, 0, 12, 2))]
    assert paths.connectivity(nodes, [(0, 1)], {'CELL/A': 0, 'CELL2/B': 2})['all_pins_connected']


@pytest.mark.parametrize('nodes,links,pins', [
    ([], [], {}),
    ([('M2', (0, 0, 0, 2))], [], {'A': 0}),
    ([('', (0, 0, 2, 2))], [], {'A': 0}),
    ([('M2', (0, 0, 2, 2))], [(0, -1)], {'A': 0}),
    ([('M2', (0, 0, 2, 2))], [(0, 1)], {'A': 0}),
    ([('M2', (0, 0, 2, 2))], [], {'A': 1}),
    ([('M2', (0, 0, 2, 2))], [], {}),
])
def test_malformed_geometry_rejected(nodes, links, pins):
    with pytest.raises(ValueError):
        paths.connectivity(nodes, links, pins)
