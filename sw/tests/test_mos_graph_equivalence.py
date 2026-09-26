# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Electrical identity, named terminals, multiplicity and inconclusive symmetry."""
import copy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'hw/soc/flow'))
from mos_graph_equivalence import prove_mos_graph


def circuit(prefix=''):
    nodes = {key: prefix + key for key in ['out', 'gate', 'ground']}
    return dict(nets={n: n for n in nodes.values()},
                pins={nodes['out']: 'OUT', nodes['gate']: 'GATE', nodes['ground']: 'VSS'},
                devices=[dict(name='M0', model='NMOS', w=.5, l=.13,
                              D=nodes['out'], G=nodes['gate'], S=nodes['ground'], B=nodes['ground'])],
                maximum_float_normalization_um=0)


def test_renaming_and_drain_source_symmetry_preserve_identity():
    a, b = circuit(), circuit('different_')
    b['devices'][0]['D'], b['devices'][0]['S'] = b['devices'][0]['S'], b['devices'][0]['D']
    proof = prove_mos_graph(a, b)
    assert proof['mapping'] == {name: 'different_' + name for name in a['nets']}


@pytest.mark.parametrize('fault', ['gate_short', 'body_short', 'width', 'pin_swap', 'extra_device'])
def test_real_electrical_changes_rejected(fault):
    a, b = circuit(), circuit()
    if fault == 'gate_short':
        b['devices'][0]['G'] = 'ground'
    elif fault == 'body_short':
        b['devices'][0]['B'] = 'out'
    elif fault == 'width':
        b['devices'][0]['w'] += .005
    elif fault == 'pin_swap':
        b['pins']['out'], b['pins']['gate'] = b['pins']['gate'], b['pins']['out']
    else:
        b['devices'].append(copy.deepcopy(b['devices'][0]))
    with pytest.raises(ValueError):
        prove_mos_graph(a, b)


def test_ambiguous_mapping_is_not_reported_as_proof():
    a = circuit()
    del a['pins']['out']
    a['nets']['second_out'] = 'second_out'
    second = copy.deepcopy(a['devices'][0])
    second.update(name='M1', D='second_out')
    a['devices'].append(second)
    with pytest.raises(ValueError, match='unique net bijection'):
        prove_mos_graph(a, copy.deepcopy(a))


def test_empty_graph_cannot_pass():
    a = circuit()
    a['devices'].clear()
    with pytest.raises(ValueError, match='No MOS devices'):
        prove_mos_graph(a, a)
