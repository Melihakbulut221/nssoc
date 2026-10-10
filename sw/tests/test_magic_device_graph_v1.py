# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from decimal import Decimal
from pathlib import Path
import sys

import pytest

nx = pytest.importorskip('networkx', reason='Native graph audit requires NetworkX with VF2++')
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from compare_magic_device_graph_v1 import exact_bijection


def circuit():
    graph = nx.Graph()
    graph.add_nodes_from([('supply', {'color': 'port:SUPPLY'}),
                         ('body', {'color': 'port:BODY'}),
                         ('signal', {'color': 'port:SIGNAL'})])
    for index in range(108):
        graph.add_node(('tap', index), color=('tap', Decimal('81.6667')))
        graph.add_edges_from([(('tap', index), 'body'), (('tap', index), 'supply')])
    graph.add_node('device', color=('device', Decimal('7e-8')))
    for role, net in (('C', 'supply'), ('B', 'signal'), ('E', 'body')):
        graph.add_node(role, color=('terminal', role))
        graph.add_edges_from([('device', role), (role, net)])
    return graph


def test_complete_numeric_and_parallel_bijection():
    a = circuit()
    b = nx.relabel_nodes(a, {n: i for i, n in enumerate(reversed(list(a)))})
    node = next(n for n in b if b.nodes[n]['color'] == ('device', Decimal('7e-8')))
    b.nodes[node]['color'] = ('device', Decimal('7.0e-8'))
    assert len(exact_bijection(a, b)) == len(a)
    assert all('refined' not in row for _, row in a.nodes(data=True))


@pytest.mark.parametrize('fault', ['missing_tap', 'terminal_swap', 'dimension', 'port', 'open', 'extra_edge'])
def test_real_topology_and_device_differences_reject(fault):
    a = circuit()
    b = a.copy()
    if fault == 'missing_tap':
        b.remove_node(('tap', 0))
    elif fault == 'terminal_swap':
        b.remove_edges_from([('B', 'signal'), ('E', 'body')])
        b.add_edges_from([('B', 'body'), ('E', 'signal')])
    elif fault == 'dimension':
        b.nodes['device']['color'] = ('device', Decimal('7.1e-8'))
    elif fault == 'port':
        b.nodes['signal']['color'] = 'port:OTHER'
    elif fault == 'open':
        b.remove_edge('C', 'supply')
    else:
        b.add_edge('signal', 'supply')
    assert exact_bijection(a, b) is None


def test_final_verification_rejects_wrong_solver_mapping(monkeypatch):
    a = circuit()
    wrong = dict(zip(a, a))
    wrong['C'], wrong['B'] = wrong['B'], wrong['C']
    monkeypatch.setattr(nx, 'vf2pp_isomorphism', lambda *args, **kwargs: wrong)
    with pytest.raises(ValueError, match='invalid complete bijection'):
        exact_bijection(a, a)


def test_unsupported_graph_type_rejected():
    with pytest.raises(ValueError, match='incidence graphs'):
        exact_bijection(nx.MultiGraph(), nx.Graph())
