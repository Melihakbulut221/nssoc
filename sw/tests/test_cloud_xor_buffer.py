# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent graph mutations and capture/control gates; no history or network."""
import csv
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
import run_cloud_xor_buffer as trial  # noqa: E402


def dump(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w') as stream:
        writer = csv.writer(stream, delimiter='\t', lineterminator='\n')
        writer.writerow(['kind', 'name', 'master', 'pin', 'net'])
        writer.writerows(rows)


def graphs(tmp_path):
    before = [
        ('instance', '_071517_', 'sg13g2_xor2_1', '', ''),
        ('pin', '_071517_', 'INPUT:SIGNAL', 'A', 'input_a'),
        ('pin', '_071517_', 'INPUT:SIGNAL', 'B', 'input_b'),
        ('pin', '_071517_', 'OUTPUT:SIGNAL', 'X', '_017423_'),
        ('pin', '_071517_', 'INOUT:POWER', 'VDD', 'VDD'),
        ('pin', '_071517_', 'INOUT:GROUND', 'VSS', 'VSS'),
        ('instance', '_071519_', 'sg13g2_xnor2_1', '', ''),
        ('pin', '_071519_', 'INPUT:SIGNAL', 'A', '_017423_'),
        ('pin', '_071519_', 'INPUT:SIGNAL', 'B', 'input_c'),
        ('pin', '_071519_', 'OUTPUT:SIGNAL', 'Y', 'output'),
        ('net', '_017423_', 'SIGNAL', '', ''),
        ('net', 'VDD', 'POWER', '', ''), ('net', 'VSS', 'GROUND', '', ''),
        ('port', 'a', 'INPUT:SIGNAL', '', 'input_a'),
    ]
    buffer, new = 'nssoc_xor_buf21', 'nssoc_xor_bufnet1'
    after = [r[:-1]+(new,) if r[:2] == ('pin', '_071517_') and r[3] == 'X' else r for r in before]
    after += [
        ('instance', buffer, 'sg13g2_buf_2', '', ''),
        ('pin', buffer, 'INPUT:SIGNAL', 'A', new),
        ('pin', buffer, 'OUTPUT:SIGNAL', 'X', '_017423_'),
        ('pin', buffer, 'INOUT:POWER', 'VDD', 'VDD'),
        ('pin', buffer, 'INOUT:GROUND', 'VSS', 'VSS'),
        ('net', new, 'SIGNAL', '', ''),
    ]
    insertion = dict(buffer=buffer, new_net=new, original_net='_017423_',
        driver='_071517_/X', sink='_071519_/A', master='sg13g2_buf_2',
        initial_instances=2, location_um=[10, 20])
    dump(tmp_path/'before.tsv', before)
    dump(tmp_path/'after.tsv', after)
    return before, after, insertion


def test_contract_one_real_noninverting_topology(tmp_path):
    _, _, insertion = graphs(tmp_path)
    assert trial.verify_contraction(tmp_path/'before.tsv', tmp_path/'after.tsv', insertion) == dict(
        original_instance_count=2, inserted_instances=1, inserted_signal_nets=1,
        full_original_graph_preserved=True, noninverting_cell='sg13g2_buf_2')


@pytest.mark.parametrize('mutation', ['wrong_master', 'reversed', 'extra_load', 'extra_cell',
    'original_fanin_changed', 'original_master_changed', 'original_port_changed', 'floating_power',
    'wrong_power', 'extra_signal_pin', 'missing_pin', 'duplicate_row', 'extra_net'])
def test_contraction_rejects_unrelated_or_unsafe_changes(tmp_path, mutation):
    _, after, insertion = graphs(tmp_path)
    def replace(match, change):
        for i, row in enumerate(after):
            if match(row):
                after[i] = change(row)
                return
        raise AssertionError('test mutation did not apply')
    if mutation == 'wrong_master':
        replace(lambda r: r[:2] == ('instance', insertion['buffer']), lambda r: (r[0], r[1], 'sg13g2_inv_1', '', ''))
    elif mutation == 'reversed':
        for i, r in enumerate(after):
            if r[0] == 'pin' and r[1] == insertion['buffer'] and r[3] in {'A', 'X'}:
                after[i] = r[:-1]+('_017423_' if r[3] == 'A' else insertion['new_net'],)
    elif mutation == 'extra_load':
        after.append(('port', 'hidden_load', 'OUTPUT:SIGNAL', '', '_017423_'))
    elif mutation == 'extra_cell':
        after.append(('instance', 'unrelated', 'sg13g2_buf_2', '', ''))
    elif mutation == 'original_fanin_changed':
        replace(lambda r: r[:2] == ('pin', '_071517_') and r[3] == 'B', lambda r: r[:-1]+('input_c',))
    elif mutation == 'original_master_changed':
        replace(lambda r: r[:2] == ('instance', '_071519_'), lambda r: (r[0], r[1], 'sg13g2_xor2_1', '', ''))
    elif mutation == 'original_port_changed':
        replace(lambda r: r[0] == 'port', lambda r: r[:-1]+('input_b',))
    elif mutation in {'floating_power', 'wrong_power'}:
        replace(lambda r: r[1] == insertion['buffer'] and r[3] == 'VDD',
                lambda r: r[:-1]+('' if mutation == 'floating_power' else 'VSS',))
    elif mutation == 'extra_signal_pin':
        after.append(('pin', insertion['buffer'], 'INPUT:SIGNAL', 'B', 'input_a'))
    elif mutation == 'missing_pin':
        after = [r for r in after if not (r[1] == '_071517_' and r[3] == 'B')]
    elif mutation == 'duplicate_row':
        after.append(after[0])
    else:
        after.append(('net', 'unrelated_net', 'SIGNAL', '', ''))
    dump(tmp_path/'after.tsv', after)
    with pytest.raises(ValueError):
        trial.verify_contraction(tmp_path/'before.tsv', tmp_path/'after.tsv', insertion)


@pytest.mark.parametrize('field,value', [('driver', '_071522_/Y'), ('sink', '_071519_/B'),
    ('master', 'sg13g2_buf_4'), ('initial_instances', 3), ('initial_instances', True)])
def test_exact_target_receipt_cannot_change(tmp_path, field, value):
    _, _, insertion = graphs(tmp_path)
    insertion[field] = value
    with pytest.raises(ValueError):
        trial.verify_contraction(tmp_path/'before.tsv', tmp_path/'after.tsv', insertion)


def test_guard_still_rejects_source_c10_regression_despite_local_gain():
    before = dict(setup_wns_seconds=-4.909516349e-9, hold_wns_seconds=-1.840965380e-9,
        setup_tns_seconds=-4e-6, hold_tns_seconds=-2e-8, setup_violating_endpoints=1384,
        hold_violating_endpoints=113, slew_violations=0, capacitance_violations=1)
    after = {**before, 'setup_wns_seconds': -4.8e-9}
    result = trial.aggregate_policy(dict(matched_before=before, after_buffer=after, after_full_update=after),
                                    dict(setup_wns_ns=-4.710829, hold_wns_ns=-1.840329))
    assert result['no_regression_from_matched_before'] and result['setup_improved']
    assert not result['no_regression_from_selected_c10'] and not result['aggregate_estimate_guard_passed']
    assert not result['candidate_adopted'] and not result['timing_accepted']


def test_separate_aggregate_count_must_match_complete_endpoint_census():
    data = dict(setup_wns_seconds=-4e-9, hold_wns_seconds=-1e-9,
        setup_tns_seconds=-4e-6, hold_tns_seconds=-2e-8, setup_violating_endpoints=1384,
        hold_violating_endpoints=113, slew_violations=0, capacitance_violations=1, instance_count=80000)
    trial.validate_metrics(data, dict(negative_vertex_endpoints=113))
    with pytest.raises(ValueError, match='complete native endpoint'):
        trial.validate_metrics({**data, 'hold_violating_endpoints': 0}, dict(negative_vertex_endpoints=113))


def test_own_capture_retains_only_rejected_views_without_changing_shared_policy(tmp_path, monkeypatch):
    output, destination = tmp_path/'output', tmp_path/'capture'
    candidate = output/'run/01-openroad-resizertimingpostgrt/rejected-candidate'
    candidate.mkdir(parents=True)
    for name in ('soc_top.odb', 'soc_top.def', 'wrong.gds'):
        (candidate/name).write_bytes(name.encode())
    def base_capture(source, target):
        target.mkdir()
        return dict(files={}, timing_accepted=False, candidate_adopted=False, restart_checkpoint_accepted=False)
    monkeypatch.setattr(trial.shared, 'capture', base_capture)
    row = trial.capture(output, destination)
    assert len(row['files']) == 2 and all(n.endswith(('.odb', '.def')) for n in row['files'])
    assert row['rejected_candidate_only'] and not row['restart_checkpoint_accepted']
    for name, pin in row['files'].items():
        assert (destination/name).read_bytes() == (output/name).read_bytes()
        assert pin['source_truncated_during_copy'] is False


def gate_fixture(root):
    step, methods = root/'step', root/'methods'
    control = step/'xor-control'
    before, _, insertion = graphs(control)
    dump(control/'contracted.tsv', before)
    for p in [control/'before.sdc', control/'after.sdc']:
        p.write_text('create_clock -period 20 clk\n')
    for c in ('fast', 'slow', 'typical'):
        (control/(c+'.rpt')).write_text('Corner: '+c+'\n')
    for name in (trial.HELPER, trial.FIXTURE):
        (methods/name).parent.mkdir(parents=True, exist_ok=True)
        (methods/name).write_text(name)
    row = dict(status='PASS_NATIVE_XOR_BUFFER_CONTROL', missing_api_rejected=True,
        extra_fanout_rejected=True, duplicate_rejected=True, original_graph_preserved=True,
        constraints_preserved=True, supply_connections_preserved=True, corners=['fast', 'slow', 'typical'],
        insertion=insertion, timing_accepted=False, candidate_adopted=False, manufacturing_approval=False)
    gate = dict(status='PASS_NATIVE_XOR_GATE', returncode=0, native_identity=trial.targeted.NATIVE_IDENTITY,
        fixture_sha256=trial.shared.common.sha(methods/trial.FIXTURE),
        helper_sha256=trial.shared.common.sha(methods/trial.HELPER))
    (step/'xor-gate.json').write_text(json.dumps(gate))
    (control/'result.json').write_text(json.dumps(row))
    (step/'xor-control.log').write_text('PASS_NATIVE_XOR_BUFFER_CONTROL_NO_CHIP_ACCEPTANCE\n')
    return step, methods, row


def test_gate_independently_checks_full_native_fixture_graph(tmp_path):
    step, methods, _ = gate_fixture(tmp_path)
    assert trial.validate_gate(step, methods)['contraction']['full_original_graph_preserved']


@pytest.mark.parametrize('field', ['extra_fanout_rejected', 'supply_connections_preserved', 'duplicate_rejected'])
def test_gate_rejects_missing_native_control(tmp_path, field):
    step, methods, row = gate_fixture(tmp_path)
    row[field] = False
    (step/'xor-control/result.json').write_text(json.dumps(row))
    with pytest.raises(ValueError):
        trial.validate_gate(step, methods)


def test_gate_rejects_changed_native_source(tmp_path):
    step, methods, _ = gate_fixture(tmp_path)
    (methods/trial.HELPER).write_text('changed')
    with pytest.raises(ValueError, match='sources'):
        trial.validate_gate(step, methods)


def test_spec_preserves_shared_frozen_methods():
    spec = trial.specification()
    assert set(trial.shared.SOURCES) <= set(spec.sources)
    assert spec.entrypoint == 'scripts/run_cloud_xor_buffer.py'
    assert spec.step == 'hw/soc/pnr/timing_xor_buffer_step.tcl'
    assert trial.shared.diagnostic_spec().sources == trial.shared.SOURCES
