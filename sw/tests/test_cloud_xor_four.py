# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Four exact target graph mutations and native gate contracts, entirely pure."""
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts'))
import run_cloud_xor_four as trial  # noqa: E402
import test_cloud_xor_pair as pair_test  # noqa: E402


def graphs(root):
    before, first, second, rows = pair_test.graphs(root)
    extra = []
    for target in trial.TARGETS.values():
        driver, dp = target['driver'].split('/'); sink, sp = target['sink'].split('/')
        extra += [('instance', driver, target['driver_master'], '', ''),
                  ('pin', driver, 'OUTPUT:SIGNAL', dp, target['original_net']),
                  ('pin', driver, 'INOUT:POWER', 'VDD', 'VDD'),
                  ('pin', driver, 'INOUT:GROUND', 'VSS', 'VSS'),
                  ('instance', sink, target['sink_master'], '', ''),
                  ('pin', sink, 'INPUT:SIGNAL', sp, target['original_net']),
                  ('net', target['original_net'], 'SIGNAL', '', '')]
    stages = [before+extra, first+extra, second+extra]
    for row in rows:
        row['initial_instances'] += 4
    for index in (3, 4):
        target = trial.TARGETS[index]; driver, dp = target['driver'].split('/')
        buffer, new = target['prefix']+str(index), target['prefix']+'net'+str(index)
        after = [r[:-1]+(new,) if r[:4] == ('pin', driver, 'OUTPUT:SIGNAL', dp) else r for r in stages[-1]]
        after += [('instance', buffer, 'sg13g2_buf_2', '', ''),
                  ('pin', buffer, 'INPUT:SIGNAL', 'A', new),
                  ('pin', buffer, 'OUTPUT:SIGNAL', 'X', target['original_net']),
                  ('pin', buffer, 'INOUT:POWER', 'VDD', 'VDD'),
                  ('pin', buffer, 'INOUT:GROUND', 'VSS', 'VSS'),
                  ('net', new, 'SIGNAL', '', '')]
        rows.append(dict(index=index, buffer=buffer, new_net=new,
            **{k: target[k] for k in ('driver', 'sink', 'original_net')}, master='sg13g2_buf_2', initial_instances=9+index-1))
        stages.append(after)
    paths = [root/(n+'.tsv') for n in ('before', 'first', 'second', 'third', 'after')]
    for path, stage in zip(paths, stages, strict=True):
        pair_test.first_test.dump(path, stage)
    pair_test.first_test.dump(root/'contracted.tsv', stages[0])
    return paths, stages, rows


def test_four_prescribed_buffers_contract_without_other_changes(tmp_path):
    paths, _, rows = graphs(tmp_path)
    assert trial.verify_four(paths, rows) == dict(original_instance_count=9, inserted_instances=4,
        inserted_signal_nets=4, full_original_graph_preserved=True, noninverting_cell='sg13g2_buf_2')


@pytest.mark.parametrize('index', [3, 4])
@pytest.mark.parametrize('mutation', ['extra_sink', 'missing_sink', 'wrong_sink', 'reverse', 'power',
    'floating_power', 'wrong_master', 'previous_buffer_modified', 'unrelated_cell', 'extra_signal', 'duplicate'])
def test_each_added_target_fails_closed_for_mutated_topology(tmp_path, index, mutation):
    paths, stages, rows = graphs(tmp_path)
    after = list(stages[index]); row = rows[index-1]; target = trial.TARGETS[index]
    def replace(name, pin, value):
        for i, r in enumerate(after):
            if r[0] == 'pin' and r[1] == name and r[3] == pin:
                after[i] = r[:-1]+(value,); return
        raise AssertionError('mutation not applied')
    sink, sp = target['sink'].split('/')
    if mutation == 'extra_sink':
        after.append(('port', 'unexpected', 'INPUT:SIGNAL', '', target['original_net']))
    elif mutation in {'missing_sink', 'wrong_sink'}:
        replace(sink, sp, '' if mutation == 'missing_sink' else 'input_a')
    elif mutation == 'reverse':
        replace(row['buffer'], 'A', target['original_net'])
    elif mutation in {'power', 'floating_power'}:
        replace(row['buffer'], 'VDD', 'VSS' if mutation == 'power' else '')
    elif mutation == 'wrong_master':
        after = [(r[0], r[1], 'sg13g2_inv_1', '', '') if r[:2] == ('instance', row['buffer']) else r for r in after]
    elif mutation == 'previous_buffer_modified':
        replace(rows[0]['buffer'], 'VDD', 'VSS')
    elif mutation == 'unrelated_cell':
        after.append(('instance', 'other', 'sg13g2_buf_2', '', ''))
    elif mutation == 'extra_signal':
        after.append(('pin', row['buffer'], 'INPUT:SIGNAL', 'B', 'input_a'))
    else:
        after.append(after[0])
    pair_test.first_test.dump(paths[index], after)
    with pytest.raises(ValueError):
        trial.verify_four(paths, rows)


@pytest.mark.parametrize('index', [3, 4])
@pytest.mark.parametrize('field,value', [('index', True), ('index', 5), ('initial_instances', True),
    ('initial_instances', 9), ('driver', '_071522_/Y'), ('sink', '_074831_/A'), ('master', 'sg13g2_buf_4')])
def test_exact_target_records_cannot_be_repurposed(tmp_path, index, field, value):
    paths, _, rows = graphs(tmp_path); rows[index-1][field] = value
    with pytest.raises(ValueError):
        trial.verify_four(paths, rows)


def gate_fixture(root):
    step, methods = root/'step', root/'methods'; control = step/'xor-four-control'
    _, _, rows = graphs(control)
    for name in ['before.sdc', 'after.sdc']:
        (control/name).write_text('create_clock -period 20 clk\n')
    for corner in ['fast', 'slow', 'typical']:
        (control/(corner+'.rpt')).write_text('Corner: '+corner+'\n')
    for name in (trial.HELPER, trial.FIXTURE):
        (methods/name).parent.mkdir(parents=True, exist_ok=True); (methods/name).write_text(name)
    flags = ['first_missing_sink_rejected', 'first_wrong_sink_rejected', 'missing_api_rejected', 'extra_fanout_rejected', 'duplicate_rejected', 'missing_sink_rejected',
             'wrong_sink_rejected', 'extra_second_sink_rejected', 'floating_power_rejected', 'wrong_power_rejected',
             'second_duplicate_rejected', 'original_graph_preserved', 'constraints_preserved', 'supply_connections_preserved']
    controls = [dict(index=i, **{k: True for k in ['missing_sink_rejected', 'wrong_sink_rejected',
        'extra_sink_rejected', 'floating_power_rejected', 'wrong_power_rejected', 'duplicate_rejected']}) for i in (3, 4)]
    row = dict(status='PASS_NATIVE_XOR_FOUR_CONTROL', **{k: True for k in flags}, extra_target_controls=controls,
        insertions=rows, corners=['fast', 'slow', 'typical'], timing_accepted=False, candidate_adopted=False, manufacturing_approval=False)
    gate = dict(status='PASS_NATIVE_XOR_FOUR_GATE', returncode=0, native_identity=trial.targeted.NATIVE_IDENTITY,
        fixture_sha256=trial.shared.common.sha(methods/trial.FIXTURE), helper_sha256=trial.shared.common.sha(methods/trial.HELPER))
    (control/'result.json').write_text(json.dumps(row)); (step/'xor-four-gate.json').write_text(json.dumps(gate))
    (step/'xor-four-control.log').write_text('PASS_NATIVE_XOR_FOUR_CONTROL_NO_CHIP_ACCEPTANCE\n')
    return step, methods, row


def test_native_gate_replays_all_four_graph_transitions(tmp_path):
    step, methods, _ = gate_fixture(tmp_path)
    assert trial.validate_gate(step, methods)['contraction']['inserted_instances'] == 4


@pytest.mark.parametrize('index', [0, 1])
@pytest.mark.parametrize('flag', ['missing_sink_rejected', 'wrong_sink_rejected', 'extra_sink_rejected',
    'floating_power_rejected', 'wrong_power_rejected', 'duplicate_rejected'])
def test_both_new_targets_require_actual_negative_controls(tmp_path, index, flag):
    step, methods, row = gate_fixture(tmp_path); row['extra_target_controls'][index][flag] = False
    (step/'xor-four-control/result.json').write_text(json.dumps(row))
    with pytest.raises(ValueError):
        trial.validate_gate(step, methods)


def test_original_producers_remain_owned_and_unmodified():
    spec = trial.specification()
    assert set(trial.pair.SOURCES) < set(spec.sources) and len(spec.sources) == len(set(spec.sources))
    assert spec.entrypoint == 'scripts/run_cloud_xor_four.py'
    assert trial.pair.specification().entrypoint == 'scripts/run_cloud_xor_pair.py'
    assert trial.capture is trial.pair.capture
    assert trial.STAGES == ('matched_before', 'after_first', 'after_second', 'after_third', 'after_fourth', 'after_full_update')


@pytest.mark.parametrize('flag', ['first_missing_sink_rejected', 'first_wrong_sink_rejected'])
def test_first_target_also_requires_missing_and_wrong_native_controls(tmp_path, flag):
    step, methods, row = gate_fixture(tmp_path); row[flag] = False
    (step/'xor-four-control/result.json').write_text(json.dumps(row))
    with pytest.raises(ValueError):
        trial.validate_gate(step, methods)
