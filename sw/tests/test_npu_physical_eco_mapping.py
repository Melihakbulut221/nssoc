# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Reject changes outside the exact binary-preserving mapped NPU gate repair."""
import copy
import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('eco_bridge', ROOT / 'scripts/check_npu_physical_eco_mapping.py')
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


def fixtures():
    nets = {'_026035_': 10, '_043474_': 11, '_032758_': 12, '_043517_': 13,
            '_043518_': 14, '_043519_': 15, 'state': 16}
    old = {'netnames': {n: {'bits': [v]} for n, v in nets.items()},
           'ports': {'out': {'direction': 'output', 'bits': [15]}}, 'cells': {}}

    def add(module, name, kind, connections):
        module['cells'][name] = {'type': kind, 'parameters': {}, 'port_directions': {},
                                'connections': {p: module['netnames'][n]['bits'][:] for p, n in connections.items()}}
    add(old, '_103491_', 'sg13g2_nand3_1', dict(A='_026035_', B='_032758_', C='_043517_', Y='_043518_'))
    add(old, '_103492_', 'sg13g2_o21ai_1', dict(A1='_026035_', A2='_043474_', B1='_043518_', Y='_043519_'))
    add(old, 'state_flop', 'sg13g2_dfrbp_1', dict(D='_043519_', Q='state'))
    for i in range(32):
        add(old, 'mem' + str(i), 'SP6TSRAM512x64' if i < 16 else 'DP8TSRAMDP256x16', dict(A='state'))
    new = copy.deepcopy(old)
    # Deliberately renumber every signal to exercise actual graph correspondence.
    for n in new['netnames'].values():
        n['bits'] = [x + 100 for x in n['bits']]
    for p in new['ports'].values():
        p['bits'] = [x + 100 for x in p['bits']]
    for c in new['cells'].values():
        c['connections'] = {p: [x + 100 for x in bits] for p, bits in c['connections'].items()}
    new['netnames'].update(nssoc_npu_init_b_n={'bits': [200]}, nssoc_npu_init_cd={'bits': [201]})
    add(new, 'nssoc_npu_init_invert', 'sg13g2_inv_1', dict(A='_043474_', Y='nssoc_npu_init_b_n'))
    add(new, 'nssoc_npu_init_product', 'sg13g2_and2_1', dict(A='_032758_', B='_043517_', X='nssoc_npu_init_cd'))
    add(new, '_103492_', 'sg13g2_mux2_1', dict(A0='nssoc_npu_init_b_n', A1='nssoc_npu_init_cd', S='_026035_', X='_043519_'))
    return old, new


def test_exact_renumbered_graph():
    a, b = fixtures()
    r = bridge.check(a, b)
    assert r['unchanged_cells'] == 34 and len(r['macros']) == 32
    assert not r['full_soc_functional_accepted'] and not r['timing_accepted']


@pytest.mark.parametrize('fault', ['mux_select', 'mux_data', 'mux_master', 'product', 'invert',
                                 'predecessor', 'flop', 'memory', 'missing_memory', 'port',
                                 'alias', 'new_alias', 'extra_load', 'extra_cell', 'extra_net', 'width'])
def test_actual_graph_faults(fault):
    a, b = fixtures()
    if fault == 'mux_select':
        b['cells']['_103492_']['connections']['S'] = [111]
    elif fault == 'mux_data':
        c = b['cells']['_103492_']['connections']; c['A0'], c['A1'] = c['A1'], c['A0']
    elif fault == 'mux_master':
        b['cells']['_103492_']['type'] = 'sg13g2_xor2_1'
    elif fault == 'product':
        b['cells']['nssoc_npu_init_product']['connections']['B'] = [111]
    elif fault == 'invert':
        b['cells']['nssoc_npu_init_invert']['connections']['A'] = [110]
    elif fault == 'predecessor':
        b['cells']['_103491_']['connections']['A'] = [111]
    elif fault == 'flop':
        b['cells']['state_flop']['connections']['D'] = [110]
    elif fault == 'memory':
        b['cells']['mem0']['connections']['A'] = [110]
    elif fault == 'missing_memory':
        del b['cells']['mem0']
    elif fault == 'port':
        b['ports']['out']['bits'] = [110]
    elif fault == 'alias':
        b['netnames']['_043474_']['bits'] = [110]
    elif fault == 'new_alias':
        b['netnames']['nssoc_npu_init_b_n']['bits'] = [110]
    elif fault == 'extra_load':
        b['cells']['state_flop']['connections']['D'] = [200]
    elif fault == 'extra_cell':
        b['cells']['another'] = copy.deepcopy(b['cells']['state_flop'])
    elif fault == 'extra_net':
        b['netnames']['another'] = {'bits': [202]}
    elif fault == 'width':
        b['netnames']['state']['bits'].append(117)
    with pytest.raises(ValueError):
        bridge.check(a, b)
