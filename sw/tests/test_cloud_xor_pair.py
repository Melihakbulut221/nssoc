# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Pure fixed-two-target graph and gate regression; no history/network/native."""
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts'))
import run_cloud_xor_pair as trial  # noqa: E402
import test_cloud_xor_buffer as first_test  # noqa: E402


def graphs(root):
    before, first, insertion = first_test.graphs(root)
    addition = [
        ('instance', '_070589_', 'sg13g2_xnor2_1', '', ''),
        ('pin', '_070589_', 'OUTPUT:SIGNAL', 'Y', '_016495_'),
        ('pin', '_070589_', 'INOUT:POWER', 'VDD', 'VDD'),
        ('pin', '_070589_', 'INOUT:GROUND', 'VSS', 'VSS'),
        ('instance', '_070602_', 'sg13g2_a22oi_1', '', ''),
        ('pin', '_070602_', 'INPUT:SIGNAL', 'A2', '_016495_'),
        ('instance', '_072894_', 'sg13g2_a221oi_1', '', ''),
        ('pin', '_072894_', 'INPUT:SIGNAL', 'A1', '_016495_'),
        ('net', '_016495_', 'SIGNAL', '', ''),
    ]
    before += addition
    first += addition
    insertion['initial_instances'] = 5
    buffer, new = 'nssoc_xnor_buf21', 'nssoc_xnor_bufnet1'
    after = [r[:-1]+(new,) if r[:4] == ('pin', '_070589_', 'OUTPUT:SIGNAL', 'Y') else r for r in first]
    after += [('instance', buffer, 'sg13g2_buf_2', '', ''),
              ('pin', buffer, 'INPUT:SIGNAL', 'A', new),
              ('pin', buffer, 'OUTPUT:SIGNAL', 'X', '_016495_'),
              ('pin', buffer, 'INOUT:POWER', 'VDD', 'VDD'),
              ('pin', buffer, 'INOUT:GROUND', 'VSS', 'VSS'),
              ('net', new, 'SIGNAL', '', '')]
    second = dict(buffer=buffer, new_net=new, original_net='_016495_', driver='_070589_/Y',
                  sinks=['_070602_/A2', '_072894_/A1'], master='sg13g2_buf_2', initial_instances=6)
    for name, rows in [('before', before), ('first', first), ('after', after), ('contracted', before)]:
        first_test.dump(root/(name+'.tsv'), rows)
    return before, first, after, [insertion, second]


def verify(root, rows):
    return trial.verify_pair(root/'before.tsv', root/'first.tsv', root/'after.tsv', rows)


def test_two_fixed_buffers_contract_to_entire_original_graph(tmp_path):
    *_, rows = graphs(tmp_path)
    assert verify(tmp_path, rows) == dict(original_instance_count=5, inserted_instances=2,
        inserted_signal_nets=2, full_original_graph_preserved=True, noninverting_cell='sg13g2_buf_2')


@pytest.mark.parametrize('mutation', ['missing_sink', 'extra_sink', 'wrong_sink', 'direction', 'power',
    'floating_power', 'extra_cell', 'changed_first_buffer', 'original_master', 'extra_signal', 'duplicate'])
def test_second_eco_cannot_change_unrelated_logic_or_topology(tmp_path, mutation):
    _, _, after, rows = graphs(tmp_path)
    def change(name, pin, value):
        for i, row in enumerate(after):
            if row[0] == 'pin' and row[1] == name and row[3] == pin:
                after[i] = row[:-1]+(value,)
                return
        raise AssertionError('mutation not applied')
    if mutation == 'missing_sink':
        change('_072894_', 'A1', '')
    elif mutation == 'wrong_sink':
        change('_072894_', 'A1', 'input_a')
    elif mutation == 'extra_sink':
        after.append(('port', 'unexpected', 'OUTPUT:SIGNAL', '', '_016495_'))
    elif mutation == 'direction':
        change(rows[1]['buffer'], 'A', '_016495_')
    elif mutation in {'power', 'floating_power'}:
        change(rows[1]['buffer'], 'VDD', 'VSS' if mutation == 'power' else '')
    elif mutation == 'extra_cell':
        after.append(('instance', 'unrelated', 'sg13g2_buf_2', '', ''))
    elif mutation == 'changed_first_buffer':
        change(rows[0]['buffer'], 'VDD', 'VSS')
    elif mutation == 'original_master':
        after = [(r[0], r[1], 'sg13g2_inv_1', '', '') if r[:2] == ('instance', '_070602_') else r for r in after]
    elif mutation == 'extra_signal':
        after.append(('pin', rows[1]['buffer'], 'INPUT:SIGNAL', 'B', 'input_a'))
    else:
        after.append(after[0])
    first_test.dump(tmp_path/'after.tsv', after)
    with pytest.raises(ValueError):
        verify(tmp_path, rows)


@pytest.mark.parametrize('field,value', [('driver', '_071522_/Y'), ('sinks', ['_072894_/A1']),
    ('sinks', ['_070602_/A2', '_072894_/B1']), ('master', 'sg13g2_buf_4'), ('initial_instances', True), ('initial_instances', 5)])
def test_prescribed_second_target_cannot_be_weakened(tmp_path, field, value):
    *_, rows = graphs(tmp_path)
    rows[1][field] = value
    with pytest.raises(ValueError):
        verify(tmp_path, rows)


def gate_fixture(root):
    step, methods = root/'step', root/'methods'
    control = step/'xor-pair-control'
    *_, insertions = graphs(control)
    for name in ['before.sdc', 'after.sdc']:
        (control/name).write_text('create_clock -period 20 clk\n')
    for corner in ['fast', 'slow', 'typical']:
        (control/(corner+'.rpt')).write_text('Corner: '+corner+'\n')
    for name in (trial.HELPER, trial.FIXTURE):
        (methods/name).parent.mkdir(parents=True, exist_ok=True)
        (methods/name).write_text(name)
    flags = ['missing_api_rejected', 'extra_fanout_rejected', 'duplicate_rejected',
        'missing_sink_rejected', 'wrong_sink_rejected', 'extra_second_sink_rejected',
        'floating_power_rejected', 'wrong_power_rejected', 'second_duplicate_rejected',
        'original_graph_preserved', 'constraints_preserved', 'supply_connections_preserved']
    row = dict(status='PASS_NATIVE_XOR_PAIR_CONTROL', **{k: True for k in flags},
        corners=['fast', 'slow', 'typical'], insertions=insertions,
        timing_accepted=False, candidate_adopted=False, manufacturing_approval=False)
    gate = dict(status='PASS_NATIVE_XOR_PAIR_GATE', returncode=0, native_identity=trial.targeted.NATIVE_IDENTITY,
        fixture_sha256=trial.shared.common.sha(methods/trial.FIXTURE), helper_sha256=trial.shared.common.sha(methods/trial.HELPER))
    (control/'result.json').write_text(json.dumps(row))
    (step/'xor-pair-gate.json').write_text(json.dumps(gate))
    (step/'xor-pair-control.log').write_text('PASS_NATIVE_XOR_PAIR_CONTROL_NO_CHIP_ACCEPTANCE\n')
    return step, methods, row


def test_gate_checks_native_two_buffer_graph(tmp_path):
    step, methods, _ = gate_fixture(tmp_path)
    assert trial.validate_gate(step, methods)['contraction']['inserted_instances'] == 2


@pytest.mark.parametrize('field', ['missing_sink_rejected', 'wrong_sink_rejected', 'extra_second_sink_rejected',
    'floating_power_rejected', 'wrong_power_rejected', 'second_duplicate_rejected'])
def test_missing_native_negative_control_rejected(tmp_path, field):
    step, methods, row = gate_fixture(tmp_path)
    row[field] = False
    (step/'xor-pair-control/result.json').write_text(json.dumps(row))
    with pytest.raises(ValueError):
        trial.validate_gate(step, methods)


def test_original_source_guard_and_false_adoption_unchanged():
    before = dict(setup_wns_seconds=-4.91e-9, hold_wns_seconds=-1.840965e-9,
        setup_tns_seconds=-4e-6, hold_tns_seconds=-2e-8, setup_violating_endpoints=1384,
        hold_violating_endpoints=113, slew_violations=0, capacitance_violations=1)
    after = {**before, 'setup_wns_seconds': -4.717e-9}
    out = trial.aggregate_policy(dict(matched_before=before, after_full_update=after),
        dict(setup_wns_ns=-4.710829, hold_wns_ns=-1.840329))
    assert out['setup_improved'] and not out['aggregate_estimate_guard_passed']
    assert not out['candidate_adopted'] and not out['timing_accepted']


def test_owned_spec_preserves_original_producer_and_all_frozen_methods():
    spec = trial.specification()
    assert set(trial.single.SOURCES) < set(spec.sources)
    assert len(spec.sources) == len(set(spec.sources))
    assert spec.entrypoint == 'scripts/run_cloud_xor_pair.py'
    assert spec.step == 'hw/soc/pnr/timing_xor_pair_step.tcl'
    assert trial.single.specification().entrypoint == 'scripts/run_cloud_xor_buffer.py'
    assert trial.STAGES == ('matched_before', 'after_first', 'after_second', 'after_full_update')
