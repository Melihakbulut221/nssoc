# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""The corrected storage proposal must not constrain or discard any equation."""
import copy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts'))
import prove_alu_state_repair as repair  # noqa: E402


def fixture():
    pairs = [[f'original_{i}', f'candidate_{i}'] for i in range(10009)]
    for index, original, old, _ in repair.CORRECTION:
        pairs[index] = [original, old]
    modules, labels = {}, {}
    for tag, side in [('original', 0), ('candidate', 1)]:
        ports = {}
        for offset, suffix in enumerate(repair.BOUNDARIES):
            ports[repair.state.PREFIX+suffix] = dict(direction='input' if suffix == 'ff_state' else 'output',
                                                    bits=list(range(2+offset*20000, 10011+offset*20000)))
        ports['external'] = dict(direction='output', bits=[90000])
        modules[tag] = dict(attributes={'preserve': 'whole'}, ports=ports, cells={}, netnames={})
        labels[tag] = {repair.state.PREFIX+suffix: [p[side] for p in pairs] for suffix in repair.BOUNDARIES}
        labels[tag]['untouched'] = ['external']
    for tag, index in [('original', 9982), ('candidate', 9983)]:
        m = modules[tag]; q = m['ports'][repair.state.PREFIX+'ff_state']['bits'][index]
        m['netnames']['u_qspi.phase'] = dict(bits=[91000, 91001, 91002, 91003])
        name = '_063550_' if tag == 'original' else '_063685_'
        m['cells'][name] = dict(type='sg13g2_nand2b_1', parameters={}, connections={'A_N': [91002], 'B': [q], 'Y': [92000]})
    for tag, index in [('original', 9988), ('candidate', 9982)]:
        m = modules[tag]; q = m['ports'][repair.state.PREFIX+'ff_state']['bits'][index]
        m['netnames']['u_uart0.rx_state'] = dict(bits=[91010, 91011])
        name = '_116680_' if tag == 'original' else '_084219_'
        m['cells'][name] = dict(type='sg13g2_nor2b_1', parameters={}, connections={'A': [91011], 'B_N': [q], 'Y': [92001]})
    for tag, index in [('original', 9983), ('candidate', 9988)]:
        m = modules[tag]; q = m['ports'][repair.state.PREFIX+'ff_state']['bits'][index]
        m['netnames']['u_can.ready'] = dict(bits=[91020])
        inv, gate = ('_064333_', '_064334_') if tag == 'original' else ('_064014_', '_064015_')
        m['cells'][inv] = dict(type='sg13g2_inv_1', parameters={}, connections={'A': [q], 'Y': [92002]})
        m['cells'][gate] = dict(type='sg13g2_a21oi_1', parameters={}, connections={
            'A1': [92002], 'A2': [92003], 'B1': [91020], 'Y': [m['ports'][repair.state.PREFIX+'ff_d']['bits'][index]]})
    return modules, dict(pairs=pairs, anchored=9892, proposed_anonymous=117), labels


def test_exact_three_cycle_preserves_every_cell_port_and_identity():
    modules, proposal, labels = fixture(); original = copy.deepcopy((modules, proposal, labels))
    fixed, meanings, receipt = repair.corrected_proposal(modules['original'], modules['candidate'], proposal, labels)
    assert (modules, proposal, labels) == original
    assert receipt['candidate_old_position_for_new'] == {9982: 9983, 9983: 9988, 9988: 9982}
    assert receipt['mapped_cells_unchanged'] and receipt['all_original_state_ids_preserved']
    assert receipt['all_candidate_state_ids_preserved'] and receipt['equivalence_proved'] is False
    assert fixed['cells'] == modules['candidate']['cells'] and fixed['netnames'] == modules['candidate']['netnames']
    assert fixed['attributes'] == modules['candidate']['attributes']
    assert fixed['ports']['external'] == modules['candidate']['ports']['external']
    for suffix in repair.BOUNDARIES:
        name = repair.state.PREFIX+suffix
        assert sorted(fixed['ports'][name]['bits']) == sorted(modules['candidate']['ports'][name]['bits'])
        assert meanings[name] == [p[1] for p in receipt['pairs']]
        assert fixed['ports'][name]['bits'][9987] == modules['candidate']['ports'][name]['bits'][9987]


@pytest.mark.parametrize('fault', ['old_index_typo', 'wrong_original', 'wrong_candidate', 'duplicate_state',
    'missing_state', 'wrong_count', 'missing_label', 'wrong_label', 'qspi_pin', 'uart_pin', 'can_pin', 'can_d', 'cell_type'])
def test_changed_old_identity_or_witness_is_rejected(fault):
    m, p, labels = fixture()
    if fault == 'old_index_typo': p['pairs'][9987], p['pairs'][9988] = p['pairs'][9988], p['pairs'][9987]
    if fault == 'wrong_original': p['pairs'][9982][0] = 'different_original'
    if fault == 'wrong_candidate': p['pairs'][9982][1] = 'different_candidate'
    if fault == 'duplicate_state': p['pairs'][3] = p['pairs'][4]
    if fault == 'missing_state': p['pairs'].pop()
    if fault == 'wrong_count': p['anchored'] -= 1
    if fault == 'missing_label': labels['original'][repair.state.PREFIX+'ff_d'].pop()
    if fault == 'wrong_label': labels['candidate'][repair.state.PREFIX+'ff_clk'][0] = 'wrong'
    if fault == 'qspi_pin': m['candidate']['cells']['_063685_']['connections']['B'] = [123]
    if fault == 'uart_pin': m['candidate']['cells']['_084219_']['connections']['B_N'] = [123]
    if fault == 'can_pin': m['candidate']['cells']['_064015_']['connections']['A1'] = [123]
    if fault == 'can_d': m['candidate']['cells']['_064015_']['connections']['Y'] = [123]
    if fault == 'cell_type': m['candidate']['cells']['_064014_']['type'] = 'sg13g2_buf_1'
    with pytest.raises((ValueError, KeyError)):
        repair.corrected_proposal(m['original'], m['candidate'], p, labels)


@pytest.mark.parametrize('mapping', [{0: 1}, {0: 1, 1: 1}, {-1: -1}, {10009: 10009}, {True: True}])
def test_boundary_permutation_cannot_remove_duplicate_or_use_invalid_state(mapping):
    m, _, labels = fixture()
    with pytest.raises(ValueError): repair.permute(m['candidate'], labels['candidate'], mapping)


def test_every_original_symbolic_input_is_unconstrained(tmp_path):
    script = repair.unconstrained_script(tmp_path/'original', tmp_path/'candidate', tmp_path/'lib', tmp_path/'model')
    assert ' -set ' not in script and '-set-assumes' not in script
    assert 'sat -verify -prove trigger 0 -show-inputs -show-outputs' in script
    assert script.count('read_json') == 2 and 'synth' not in script and 'abc' not in script
    assert 'select -assert-none t:sg13g2_* t:RM_*' in script


def test_guard_rejects_future_constraint_regression(tmp_path, monkeypatch):
    monkeypatch.setattr(repair.state, 'miter_script', lambda *a: 'sat -verify -prove trigger 0 -set in_x 0\n')
    with pytest.raises(ValueError, match='unconstrained'):
        repair.unconstrained_script(tmp_path/'a', tmp_path/'b', tmp_path/'c', tmp_path/'d')


def test_full_proof_never_runs_locally(tmp_path, monkeypatch):
    monkeypatch.delenv('GITHUB_ACTIONS', raising=False)
    with pytest.raises(ValueError, match='cloud-only'): repair.run(tmp_path/'out', tmp_path/'work')
    assert not (tmp_path/'out').exists()
