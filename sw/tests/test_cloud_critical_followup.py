# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Pure source, target-neighborhood and nonacceptance gates; no native chip work."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
import run_cloud_critical_followup as repair  # noqa: E402


def locked():
    return json.loads((ROOT/repair.LOCK).read_text())


def baseline():
    return dict(recorded_ms=1, **locked()['baseline_metrics'])


def test_current_lock_retains_complete_prior_method_and_parent_chain():
    row = repair.lock(ROOT)
    assert set(row['frozen_method_pins']) == set(repair.prior.SOURCES)
    assert set(row['historical_reference_metrics']) == {
        'selected_c10', 'matched_c10', 'combined_parent', 'electrical_first',
        'electrical_margin_parent', 'residual_parent'}


@pytest.mark.parametrize('fault', ['runtime', 'manifest', 'producer', 'hold_endpoint',
    'setup_permission', 'hold_passes', 'sizing_master', 'missing_view', 'missing_method',
    'changed_method', 'missing_historical_reference'])
def test_lock_rejects_changed_native_or_historical_contract(tmp_path, fault):
    row = locked()
    for name in row['frozen_method_pins']:
        path = tmp_path/name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, path)
    if fault == 'runtime': row['runtime_sha256'] = '0'*64
    if fault == 'manifest': row['manifest_sha256'] = '0'*64
    if fault == 'producer': row['producer']['source_commit'] = '0'*40
    if fault == 'hold_endpoint': row['hold_endpoint'] = '_135214_/D'
    if fault == 'setup_permission': row['hold_policy']['allow_setup_violations'] = True
    if fault == 'hold_passes': row['hold_policy']['max_passes'] = 2
    if fault == 'sizing_master': row['sizing_target']['after_master'] = 'sg13g2_buf_16'
    if fault == 'missing_view': del row['candidate_files']['soc_top.sdc']
    if fault == 'missing_method': row['frozen_method_pins'].pop(next(iter(row['frozen_method_pins'])))
    if fault == 'changed_method': (tmp_path/next(iter(row['frozen_method_pins']))).write_text('changed')
    if fault == 'missing_historical_reference': del row['historical_reference_metrics']['combined_parent']
    (tmp_path/repair.LOCK).write_text(json.dumps(row))
    with pytest.raises(ValueError): repair.lock(tmp_path)


def target_fixture(tmp_path, fault=None):
    row = locked()
    driver = ' sg13g2_buf_4 fanout639 (.A(net_upstream),\n    .X(net639));'
    loads = [f' sg13g2_inv_1 load{i} (.A(net639),\n    .Y(out{i}));' for i in range(8)]
    hold = ' '+row['hold_target']['body']
    placement = ['instance\tmaster\tx_dbu\ty_dbu\torientation\tstatus',
        'fanout639\tsg13g2_buf_4\t123000\t456000\tR0\tPLACED']
    placement += [f'load{i}\tsg13g2_inv_1\t{124000+i*100}\t456000\tMX\tPLACED' for i in range(8)]
    if fault == 'missing_driver': driver = ''
    if fault == 'wrong_master': driver = driver.replace('buf_4', 'buf_2')
    if fault == 'wrong_output_net': driver = driver.replace('.X(net639)', '.X(other)')
    if fault == 'extra_driver_port': driver = driver.replace('.X(net639)', '.X(net639), .VDD(VDD)')
    if fault == 'duplicate_port': driver = driver.replace('.X(net639)', '.X(net639), .X(net639)')
    if fault == 'unmapped_input': driver = driver.replace('net_upstream', '\\escaped.input ')
    if fault == 'missing_load': loads.pop()
    if fault == 'extra_load': loads.append(' sg13g2_inv_1 load8 (.A(net639), .Y(out8));')
    if fault == 'duplicate_instance': loads.append(loads[0])
    if fault == 'hold_body': hold = hold.replace('.RESET_B(net6187)', '.RESET_B(other_reset)')
    if fault == 'missing_place': placement.pop()
    if fault == 'wrong_place_master': placement[1] = placement[1].replace('buf_4', 'buf_8')
    if fault == 'wrong_place_header': placement[0] = placement[0].replace('x_dbu', 'x_um')
    netlist = tmp_path/'soc_top.v'
    netlist.write_text('module soc_top;\n'+driver+'\n'+'\n'.join(loads)+'\n'+hold+'\nendmodule\n')
    path = tmp_path/'placement.tsv'; path.write_text('\n'.join(placement)+'\n')
    row['candidate_files']['soc_top.v'] = repair.eco.file_pin(netlist)
    row['source_placement_pin'] = repair.eco.file_pin(path)
    if fault == 'netlist_pin': netlist.write_text(netlist.read_text()+'// altered after pin\n')
    if fault == 'placement_pin': path.write_text(path.read_text()+'other\tcell\t0\t0\tR0\tPLACED\n')
    return row, netlist, path


def test_openroad_one_space_export_derives_exact_eight_load_contract(tmp_path):
    row, netlist, place = target_fixture(tmp_path)
    result = repair.target_binding(netlist, place, row)
    assert result['input_net'] == 'net_upstream'
    assert result['terminals'] == sorted([['fanout639', 'sg13g2_buf_4', 'X']]
        + [[f'load{i}', 'sg13g2_inv_1', 'A'] for i in range(8)])
    assert result['native_placement']['x_dbu'] == '123000'
    assert result['native_placement']['orientation'] == 'R0'


@pytest.mark.parametrize('fault', ['missing_driver', 'wrong_master', 'wrong_output_net',
    'extra_driver_port', 'duplicate_port', 'unmapped_input', 'missing_load', 'extra_load',
    'duplicate_instance', 'hold_body', 'missing_place', 'wrong_place_master',
    'wrong_place_header', 'netlist_pin', 'placement_pin'])
def test_target_neighborhood_and_native_census_fail_closed(tmp_path, fault):
    row, netlist, place = target_fixture(tmp_path, fault)
    with pytest.raises(ValueError): repair.target_binding(netlist, place, row)


def test_generated_tcl_is_literal_and_contains_measured_neighborhood(tmp_path):
    row, netlist, place = target_fixture(tmp_path)
    binding = repair.target_binding(netlist, place, row)
    script = repair.baseline_script(row, binding)
    assert '[list {fanout639} {sg13g2_buf_4} {X}]' in script
    assert '[list {123000} {456000} {R0} {PLACED}]' in script
    assert 'set nssoc_critical_input {net_upstream}' in script
    assert row['baseline_fingerprints']['constraints'] in script


@pytest.mark.parametrize('fault', ['input', 'terminal', 'placement'])
def test_generated_tcl_rejects_command_or_variable_substitution(tmp_path, fault):
    row, netlist, place = target_fixture(tmp_path)
    binding = repair.target_binding(netlist, place, row)
    if fault == 'input': binding['input_net'] = 'net; error unsafe'
    if fault == 'terminal': binding['terminals'][0][0] = 'x}\nerror unsafe\n{'
    if fault == 'placement': binding['native_placement']['x_dbu'] = '$other'
    with pytest.raises(ValueError): repair.baseline_script(row, binding)


def parent_fixture(row):
    refs = copy.deepcopy(row['historical_reference_metrics'])
    canonical = refs.pop('residual_parent')
    refs['candidate_before'] = refs.pop('electrical_margin_parent')
    return dict(status='COMPLETE_DIAGNOSTIC_ONLY', github_source_commit=row['producer']['source_commit'],
        method_files=copy.deepcopy(row['frozen_method_pins']), diagnostic=dict(
            native=dict(candidate_files=copy.deepcopy(row['candidate_files']),
                timing_metrics=dict(reload_repeat=dict(recorded_ms=123, **row['baseline_metrics']))),
            independently_checked_stages=dict(reload_repeat=dict(fingerprints=copy.deepcopy(row['baseline_fingerprints']))),
            aggregate_guard_assessment=dict(reference_metrics=refs, canonical_reloaded=canonical)))


def test_parent_reference_renaming_preserves_all_metrics():
    row = locked(); producer = parent_fixture(row)
    repair.validate_parent_contract(producer, row)


@pytest.mark.parametrize('fault', ['status', 'commit', 'method', 'view', 'metric', 'fingerprint',
                                  'historical', 'canonical'])
def test_parent_cannot_substitute_an_easier_reference(fault):
    row = locked(); producer = parent_fixture(row); d = producer['diagnostic']
    if fault == 'status': producer['status'] = 'FAILED'
    if fault == 'commit': producer['github_source_commit'] = '0'*40
    if fault == 'method': producer['method_files'].pop(next(iter(producer['method_files'])))
    if fault == 'view': d['native']['candidate_files']['soc_top.odb']['sha256'] = '0'*64
    if fault == 'metric': d['native']['timing_metrics']['reload_repeat']['hold_violating_endpoints'] += 1
    if fault == 'fingerprint': d['independently_checked_stages']['reload_repeat']['fingerprints']['constraints'] = '0'*64
    if fault == 'historical': del d['aggregate_guard_assessment']['reference_metrics']['combined_parent']
    if fault == 'canonical': d['aggregate_guard_assessment']['canonical_reloaded']['setup_wns_ns'] -= 1
    with pytest.raises(ValueError): repair.validate_parent_contract(producer, row)


def producer_network_fixture(monkeypatch, fault=None):
    trial = locked()['producer']; raw = b'exact fixture release zip'
    trial.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    run = dict(id=trial['run_id'], head_sha=trial['source_commit'], status='completed', conclusion='success', run_attempt=1,
               repository=dict(full_name=repair.eco.REPOSITORY))
    meta = dict(id=trial['artifact_id'], name=trial['artifact_name'], size_in_bytes=trial['bytes'],
        digest='sha256:'+trial['sha256'], expired=fault == 'expired',
        workflow_run=dict(id=trial['run_id'], head_sha=trial['source_commit']))
    if fault == 'run_id': run['id'] += 1
    if fault == 'run_source': run['head_sha'] = '0'*40
    if fault == 'run_failure': run['conclusion'] = 'failure'
    if fault == 'run_attempt': run['run_attempt'] = 2
    if fault == 'run_repository': run['repository']['full_name'] = 'other/repo'
    if fault == 'artifact_id': meta['id'] += 1
    if fault == 'artifact_source': meta['workflow_run']['head_sha'] = '0'*40
    if fault == 'artifact_run': meta['workflow_run']['id'] += 1
    if fault == 'artifact_name': meta['name'] = 'other'
    if fault == 'artifact_size': meta['size_in_bytes'] += 1
    if fault == 'artifact_digest': meta['digest'] = 'sha256:'+'0'*64
    calls = []
    def api(path):
        if path.startswith('actions/runs/'):
            if fault == 'unavailable_run': raise subprocess.CalledProcessError(1, ['gh'])
            return run
        if fault == 'unavailable_metadata': raise subprocess.CalledProcessError(1, ['gh'])
        if fault == 'malformed_metadata': raise ValueError('invalid response')
        return meta
    def download(source, destination):
        calls.append(source.copy()); destination.write_bytes(raw)
        repair.common.verify_file(destination, source)
    monkeypatch.setattr(repair.eco, 'github_json', api)
    monkeypatch.setattr(repair.common, 'download', download)
    return trial, calls


@pytest.mark.parametrize('case', [None, 'expired', 'unavailable_metadata'])
def test_permanent_exact_release_survives_artifact_expiry(tmp_path, monkeypatch, case):
    trial, calls = producer_network_fixture(monkeypatch, case)
    result = repair.download_producer(trial, tmp_path/'source.zip')
    assert len(calls) == 1 and '/releases/download/' in calls[0]['url']
    assert result['artifact_metadata_available'] is (case != 'unavailable_metadata')
    assert result['verified_zip'] == dict(bytes=trial['bytes'], sha256=trial['sha256'])


@pytest.mark.parametrize('fault', ['run_id', 'run_source', 'run_failure', 'run_attempt', 'run_repository',
    'artifact_id', 'artifact_source', 'artifact_run', 'artifact_name', 'artifact_size',
    'artifact_digest', 'unavailable_run', 'malformed_metadata'])
def test_available_provenance_mismatch_never_falls_back(tmp_path, monkeypatch, fault):
    trial, calls = producer_network_fixture(monkeypatch, fault)
    with pytest.raises((ValueError, subprocess.CalledProcessError)):
        repair.download_producer(trial, tmp_path/'source.zip')
    assert calls == []


def improved_metrics():
    row = baseline()
    row.update(setup_wns_seconds=-4e-9, setup_tns_seconds=-3.4e-6,
        hold_wns_seconds=-.14e-9, hold_tns_seconds=-2e-9,
        setup_violating_endpoints=1300, hold_violating_endpoints=50,
        slew_violations=0, capacitance_violations=0)
    return row


@pytest.mark.parametrize('fault', [None, 'setup', 'hold', 'setup_tns', 'hold_tns',
    'setup_count', 'hold_count', 'slew', 'capacitance', 'repeatability', 'protected', 'no_gain'])
def test_guard_requires_gain_without_any_historical_regression(fault):
    before = baseline(); after = improved_metrics()
    if fault == 'setup': after['setup_wns_seconds'] = -5e-9
    if fault == 'hold': after['hold_wns_seconds'] = -2e-9
    if fault == 'setup_tns': after['setup_tns_seconds'] = -5e-6
    if fault == 'hold_tns': after['hold_tns_seconds'] = -30e-9
    if fault == 'setup_count': after['setup_violating_endpoints'] = 1500
    if fault == 'hold_count': after['hold_violating_endpoints'] = 114
    if fault == 'slew': after['slew_violations'] = 1
    if fault == 'capacitance': after['capacitance_violations'] = 1
    if fault == 'no_gain': after = before.copy()
    result = repair.guard({repair.STAGES[0]:before, repair.STAGES[-1]:after}, locked(),
                          fault != 'repeatability', fault != 'protected')
    assert result['aggregate_estimate_guard_passed'] is (fault is None)
    assert set(result['no_regression']) == set(locked()['historical_reference_metrics']) | {'candidate_before'}
    assert result['candidate_adopted'] is result['timing_accepted'] is result['manufacturing_approval'] is False
    assert result['zero_violations'] is False


@pytest.mark.parametrize('reference', ['selected_c10', 'matched_c10', 'combined_parent',
    'electrical_first', 'electrical_margin_parent', 'residual_parent'])
def test_each_ancestor_can_independently_block_acceptance(reference):
    row = locked(); row['historical_reference_metrics'][reference]['setup_wns_ns'] = -3.9
    result = repair.guard({repair.STAGES[0]:baseline(), repair.STAGES[-1]:improved_metrics()}, row, True, True)
    assert result['no_regression'][reference] is False
    assert result['aggregate_estimate_guard_passed'] is False


def test_no_setup_gain_is_not_accepted_even_when_all_references_pass():
    row = locked(); after = improved_metrics()
    result = repair.guard({repair.STAGES[0]:after, repair.STAGES[-1]:after}, row, True, True)
    assert all(result['no_regression'].values())
    assert result['setup_improved'] is False
    assert result['aggregate_estimate_guard_passed'] is False


def test_fresh_before_is_an_additional_guard_not_a_parent_substitution():
    before = improved_metrics(); before['setup_wns_seconds'] = -3.95e-9
    result = repair.guard({repair.STAGES[0]:before, repair.STAGES[-1]:improved_metrics()}, locked(), True, True)
    assert all(result['no_regression'][name] for name in locked()['historical_reference_metrics'])
    assert result['no_regression']['candidate_before'] is False
    assert result['aggregate_estimate_guard_passed'] is False


def test_actual_chip_preparation_remains_cloud_only(tmp_path, monkeypatch):
    monkeypatch.delenv('GITHUB_ACTIONS', raising=False)
    with pytest.raises(ValueError, match='cloud-only'): repair.prepare_overlay(tmp_path, {})


def test_sizing_preserves_every_other_cell_and_terminal(tmp_path):
    _, source, _ = target_fixture(tmp_path)
    before = source.read_text()
    after = before.replace('sg13g2_buf_4 fanout639', 'sg13g2_buf_8 fanout639')
    result = repair.validate_only_size(before, after)
    assert result['retained_logical_instances'] == 10
    assert result['all_terminal_expressions_preserved'] is True


@pytest.mark.parametrize('fault', ['unchanged', 'target_master', 'other_master', 'input',
    'output', 'load', 'hold_reset', 'added', 'removed', 'duplicate', 'duplicate_port'])
def test_sizing_rejects_any_additional_logical_mutation(tmp_path, fault):
    _, source, _ = target_fixture(tmp_path)
    before = source.read_text()
    after = before.replace('sg13g2_buf_4 fanout639', 'sg13g2_buf_8 fanout639')
    if fault == 'unchanged': after = before
    if fault == 'target_master': after = after.replace('buf_8 fanout639', 'buf_16 fanout639')
    if fault == 'other_master': after = after.replace('inv_1 load0', 'inv_2 load0')
    if fault == 'input': after = after.replace('.A(net_upstream)', '.A(other)')
    if fault == 'output': after = after.replace('.X(net639)', '.X(other)')
    if fault == 'load': after = after.replace('load0 (.A(net639)', 'load0 (.A(other)')
    if fault == 'hold_reset': after = after.replace('.RESET_B(net6187)', '.RESET_B(other)')
    if fault == 'added': after += '\n sg13g2_inv_1 added (.A(net639), .Y(other));\n'
    if fault == 'removed': after = after.replace('sg13g2_inv_1 load0', 'unsupported load0')
    if fault == 'duplicate': after += '\n sg13g2_inv_1 load0 (.A(net639), .Y(out0));\n'
    if fault == 'duplicate_port': after = after.replace('.X(net639)', '.X(net639), .X(net639)')
    with pytest.raises(ValueError): repair.validate_only_size(before, after)


def native_binding_fixture(tmp_path):
    row, netlist, place = target_fixture(tmp_path)
    binding = repair.target_binding(netlist, place, row)
    call = dict(observed_input_net='net_upstream', observed_output_net='net639',
        observed_output_terminals=copy.deepcopy(binding['terminals']),
        observed_placement=['123000', '456000', 'R0', 'PLACED'],
        observed_all_pin_nets=dict(A='net_upstream', X='net639', VDD='VDD', VSS='VSS'))
    return call, binding


def test_native_witness_matches_exact_derived_graph_place_and_supply(tmp_path):
    call, binding = native_binding_fixture(tmp_path)
    repair.validate_native_binding(call, binding)


@pytest.mark.parametrize('fault', ['input', 'output', 'missing_load', 'extra_load',
    'load_master', 'placement', 'orientation', 'status', 'missing_supply', 'null_supply',
    'empty_supply', 'extra_pin', 'wrong_input_pin', 'wrong_output_pin'])
def test_native_binding_rejects_changed_load_place_or_open_supply(tmp_path, fault):
    call, binding = native_binding_fixture(tmp_path)
    if fault == 'input': call['observed_input_net'] = 'other'
    if fault == 'output': call['observed_output_net'] = 'other'
    if fault == 'missing_load': call['observed_output_terminals'].pop()
    if fault == 'extra_load': call['observed_output_terminals'].append(['extra', 'sg13g2_inv_1', 'A'])
    if fault == 'load_master': call['observed_output_terminals'][1][1] = 'sg13g2_inv_2'
    if fault == 'placement': call['observed_placement'][0] = '123001'
    if fault == 'orientation': call['observed_placement'][2] = 'MX'
    if fault == 'status': call['observed_placement'][3] = 'UNPLACED'
    if fault == 'missing_supply': del call['observed_all_pin_nets']['VDD']
    if fault == 'null_supply': call['observed_all_pin_nets']['VSS'] = 'NULL'
    if fault == 'empty_supply': call['observed_all_pin_nets']['VDD'] = ''
    if fault == 'extra_pin': call['observed_all_pin_nets']['Z'] = 'net639'
    if fault == 'wrong_input_pin': call['observed_all_pin_nets']['A'] = 'other'
    if fault == 'wrong_output_pin': call['observed_all_pin_nets']['X'] = 'other'
    with pytest.raises(ValueError): repair.validate_native_binding(call, binding)



def sizing_geometry_fixture(orientation):
    # Exact observed coordinates from the four real OpenROAD controls. Keep
    # the MY/R180 transform origin distinct from the lower-left anchor.
    y,oy,ox,sx,ax,dx={
        'R0':(15120,15120,20160,20160,20160,0),
        'MY':(15120,15120,24000,17760,26400,-2400),
        'MX':(18900,22680,20160,20160,20160,0),
        'R180':(18900,22680,24000,17760,26400,-2400),
    }[orientation]
    before=dict(x=20160,y=y,origin_x=ox,origin_y=oy,width=3840,height=3780,site_width=480,
        bbox_x_min=20160,bbox_y_min=y,bbox_x_max=24000,bbox_y_max=y+3780,
        orientation=orientation,status='PLACED')
    swapped=dict(before,x=sx,width=6240,bbox_x_min=sx,bbox_x_max=sx+6240)
    anchored=dict(before,width=6240,origin_x=ax,bbox_x_max=26400)
    return dict(geometry_before=before,geometry_after_native_swap=swapped,geometry_after_anchor_restore=anchored,
        native_swap_delta_x_dbu=dx,anchor_restore_calls=1,source_lower_left_restored=True,
        observed_placement=['20160',str(y),orientation,'PLACED'],original_width=3840,replacement_width=6240,site_width=480)


@pytest.mark.parametrize('orientation', repair.ROW_ORIENTATIONS)
def test_native_master_swap_preserves_origin_then_explicitly_restores_lower_left(orientation):
    call=sizing_geometry_fixture(orientation)
    result=repair.validate_sizing_geometry(call,orientation)
    assert result['native_origin_preserved'] and result['explicit_source_lower_left_restored']
    assert result['raw_native_lower_left_delta_x_dbu']==(-2400 if orientation in ('MY','R180') else 0)
    assert result['no_geometry_tolerance_applied']


@pytest.mark.parametrize('orientation', repair.ROW_ORIENTATIONS)
@pytest.mark.parametrize('fault', ['moved_origin','extra_delta','vertical_shift','not_anchored','wrong_anchor_origin',
    'orientation','status','width','height','bbox','coordinate_type','wrong_expected_orientation',
    'restore_omitted','restore_count','restore_boolean','delta_boolean','source_witness','omitted_coordinate'])
def test_native_swap_never_accepts_an_unexplained_move_or_missing_restore(orientation,fault):
    call=sizing_geometry_fixture(orientation);expected=orientation
    raw=call['geometry_after_native_swap'];after=call['geometry_after_anchor_restore']
    if fault=='moved_origin':raw['origin_x']+=1
    if fault=='extra_delta':raw['x']-=1
    if fault=='vertical_shift':raw['y']+=1
    if fault=='not_anchored':after['x']-=1
    if fault=='wrong_anchor_origin':after['origin_x']+=1
    if fault=='orientation':raw['orientation']='R90'
    if fault=='status':after['status']='UNPLACED'
    if fault=='width':raw['width']+=480
    if fault=='height':raw['height']+=3780
    if fault=='bbox':raw['bbox_x_max']+=1
    if fault=='coordinate_type':raw['x']=str(raw['x'])
    if fault=='wrong_expected_orientation':expected='R90'
    if fault=='restore_omitted':call['source_lower_left_restored']=False
    if fault=='restore_count':call['anchor_restore_calls']=0
    if fault=='restore_boolean':call['anchor_restore_calls']=True
    if fault=='delta_boolean':call['native_swap_delta_x_dbu']=False
    if fault=='source_witness':call['observed_placement'][0]='20161'
    if fault=='omitted_coordinate':del raw['bbox_x_max']
    with pytest.raises(ValueError):repair.validate_sizing_geometry(call,expected)


def sizing_control_fixture(tmp_path):
    root = tmp_path/'control'; root.mkdir()
    for name in ('before.sdc', 'after.sdc'):
        (root/name).write_text('create_clock -period 10 [get_ports clk]\n')
    for corner in ('fast', 'slow', 'typical'):
        (root/f'after-{corner}.rpt').write_text(f'Corner: {corner}\n driver/X (sg13g2_buf_8)\n')
    gate = dict(status='PASS_NATIVE_CRITICAL_SIZE_CONTROL', fixture_orientation='R0', native_overlap_error='DPL-0033',
        negative_control_messages={k: 'observed rejection '+k for k in repair.SIZE_NEGATIVES},
        pre_sdc_sha256=repair.common.sha(root/'before.sdc'),
        post_sdc_sha256=repair.common.sha(root/'after.sdc'),
        candidate_adopted=False, timing_accepted=False, manufacturing_approval=False,
        call=dict(instance='driver', original_master='sg13g2_buf_4', replacement_master='sg13g2_buf_8',
            native_calls=1, instance_count=4, original_width=3840, replacement_width=6240,
            site_width=480, connectivity_preserved=True, immediate_placement_preserved=True))
    gate['call'].update(sizing_geometry_fixture('R0'))
    gate.update({k+'_rejected': True for k in repair.SIZE_NEGATIVES})
    gate.update({k: True for k in ('native_overlap_detected', 'native_overlap_repaired',
        'all_three_corners_loaded_and_timed', 'constraints_preserved', 'pg_bindings_preserved',
        'all_instance_connections_preserved', 'debug_hold_resizer_journal_api_called',
        'native_report_buffers_called', 'native_report_buffers_cmd_zero_called')})
    log = tmp_path/'native.log'
    log.write_text('DPL-0033\nHold Buffer Report:\nHold Buffer Report:\n'
                   'PASS_NATIVE_CRITICAL_SIZE_CONTROL_NO_CHIP_ACCEPTANCE\n')
    return root, gate, log


def test_native_sizing_gate_requires_raw_reports_and_unchanged_sdc(tmp_path):
    root, gate, log = sizing_control_fixture(tmp_path)
    (root/'result.json').write_text(json.dumps(gate))
    assert repair.validate_native_sizing_control(root, log) == gate


@pytest.mark.parametrize('negative', repair.SIZE_NEGATIVES)
def test_every_native_sizing_negative_must_have_actually_rejected(tmp_path, negative):
    root, gate, log = sizing_control_fixture(tmp_path)
    gate[negative+'_rejected'] = False
    (root/'result.json').write_text(json.dumps(gate))
    with pytest.raises(ValueError, match='negative sizing gate'):
        repair.validate_native_sizing_control(root, log)


@pytest.mark.parametrize('fault', ['missing_negative', 'extra_negative', 'empty_rejection',
    'status', 'overlap', 'pg', 'connectivity', 'clock_api', 'native_calls', 'master',
    'cell_count', 'size', 'constraints', 'raw_sdc', 'corner', 'report_master',
    'missing_marker', 'duplicate_marker', 'missing_buffer_report', 'accepted'])
def test_native_sizing_gate_fails_closed_on_receipt_or_raw_evidence_changes(tmp_path, fault):
    root, gate, log = sizing_control_fixture(tmp_path)
    if fault == 'missing_negative': gate['negative_control_messages'].pop('wrong_input')
    if fault == 'extra_negative': gate['negative_control_messages']['other'] = 'rejected'
    if fault == 'empty_rejection': gate['negative_control_messages']['wrong_input'] = ''
    if fault == 'status': gate['status'] = 'INCOMPLETE'
    if fault == 'overlap': gate['native_overlap_error'] = 'SYNTHETIC'
    if fault == 'pg': gate['pg_bindings_preserved'] = False
    if fault == 'connectivity': gate['call']['connectivity_preserved'] = False
    if fault == 'clock_api': gate['debug_hold_resizer_journal_api_called'] = False
    if fault == 'native_calls': gate['call']['native_calls'] = 2
    if fault == 'master': gate['call']['replacement_master'] = 'sg13g2_buf_16'
    if fault == 'cell_count': gate['call']['instance_count'] = 5
    if fault == 'size': gate['call']['replacement_width'] += 480
    if fault == 'constraints': gate['post_sdc_sha256'] = '0'*64
    if fault == 'raw_sdc': (root/'after.sdc').write_text('create_clock -period 20 [get_ports clk]\n')
    if fault == 'corner': (root/'after-fast.rpt').write_text('Corner: slow\n driver/X (sg13g2_buf_8)\n')
    if fault == 'report_master': (root/'after-slow.rpt').write_text('Corner: slow\n driver/X (sg13g2_buf_4)\n')
    if fault == 'missing_marker': log.write_text(log.read_text().replace('PASS_NATIVE_', 'MISSING_NATIVE_'))
    if fault == 'duplicate_marker': log.write_text(log.read_text()+'PASS_NATIVE_CRITICAL_SIZE_CONTROL_NO_CHIP_ACCEPTANCE\n')
    if fault == 'missing_buffer_report': log.write_text(log.read_text().replace('Hold Buffer Report:', '', 1))
    if fault == 'accepted': gate['candidate_adopted'] = True
    (root/'result.json').write_text(json.dumps(gate))
    with pytest.raises(ValueError): repair.validate_native_sizing_control(root, log)


def test_native_environment_drops_acquisition_credentials(monkeypatch):
    monkeypatch.setattr(repair, 'BASE_ENVIRONMENT', lambda: dict(
        PATH='/trusted/bin', GH_TOKEN='secret-a', GITHUB_TOKEN='secret-b', OTHER='preserved'))
    assert repair.clean_environment() == dict(PATH='/trusted/bin', OTHER='preserved')


@pytest.mark.parametrize('fault', [None, 'extra_physical', 'symlink', 'extra_orientation'])
def test_capture_explicitly_retains_only_known_tiny_and_child_physical_files(tmp_path, monkeypatch, fault):
    output = tmp_path/'output'; step = output/'run/42-openroad-resizertimingpostgrt'
    expected = ['sizing-control/before.odb', 'sizing-control/after.odb',
        'sizing-control/overlapping-after-swap.def', 'hold-debug/candidate/soc_top.odb',
        'hold-debug/candidate/soc_top.def']
    for orientation in ('MY','MX','R180'):
        expected += [f'sizing-control-{orientation}/'+name for name in ('before.odb','after.odb','overlapping-after-swap.def')]
    for index, name in enumerate(expected):
        path = step/name; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(bytes([index, 0, 255, 10]))
    if fault == 'extra_physical': (step/'sizing-control/unexpected.odb').write_bytes(b'unexpected')
    if fault == 'extra_orientation':
        path=step/'sizing-control-R90/before.odb';path.parent.mkdir();path.write_bytes(b'unsupported')
    if fault == 'symlink':
        path = step/'sizing-control/before.odb'; path.unlink(); path.symlink_to(step/'sizing-control/after.odb')
    def base_capture(source, destination):
        destination.mkdir()
        return dict(files={})
    monkeypatch.setattr(repair.parent, 'capture', base_capture)
    destination = tmp_path/'capture'
    if fault:
        with pytest.raises(ValueError): repair.capture(output, destination)
        return
    row = repair.capture(output, destination)
    assert set(row['files']) == {str((step/name).relative_to(output)) for name in expected}
    for name, pin in row['files'].items():
        assert repair.eco.file_pin(destination/name) == {k: pin[k] for k in ('bytes', 'sha256')}
        assert (destination/name).read_bytes() == (output/name).read_bytes()
        assert pin['source_truncated_during_copy'] is False and pin['observed_source_bytes'] == 4


def test_cloud_workflow_keeps_acquisition_access_and_complete_source_capture():
    import yaml
    row = yaml.safe_load((ROOT/'.github/workflows/timing-critical-followup.yml').read_text())
    assert row['permissions'] == dict(contents='read', actions='read')
    steps = row['jobs']['diagnose']['steps']
    checkout = next(s for s in steps if s.get('uses', '').startswith('actions/checkout@'))
    assert checkout['with']['fetch-depth'] == 0 and checkout['with']['persist-credentials'] is False
    launch = next(s for s in steps if s.get('id') == 'launch')
    assert launch['env']['GH_TOKEN'] == '${{ github.token }}'
    uploads = [s for s in steps if s.get('uses', '').startswith('actions/upload-artifact@')]
    assert len(uploads) == 4 and all(s['with']['include-hidden-files'] is True for s in uploads)


@pytest.mark.parametrize('fault', [None, 'corner_order', 'hold_count', 'instance_count', 'macro_move', 'endpoint_set'])
def test_stage_guard_retains_sorted_native_corner_and_complete_census_contract(tmp_path, monkeypatch, fault):
    corners = ['nom_fast', 'nom_slow', 'nom_typical']
    checks = {}
    for name in ('before', 'after'):
        stage = tmp_path/name; stage.mkdir()
        (tmp_path/(name+'-stage.json')).write_text(json.dumps(dict(name=name)))
        metrics = baseline(); metrics['instance_count'] = 32
        if fault == 'hold_count' and name == 'after': metrics['hold_violating_endpoints'] += 1
        if fault == 'instance_count' and name == 'after': metrics['instance_count'] = 33
        (tmp_path/(name+'-metrics.json')).write_text(json.dumps(metrics))
        rows = ['instance\tmaster\tx_dbu\ty_dbu\torientation\tstatus']
        for index in range(32):
            x = 1 if fault == 'macro_move' and name == 'after' and index == 0 else 0
            rows.append(f'mem{index}\tSP6TSRAM512x64\t{x}\t0\tR0\tFIXED')
        (stage/'placement.tsv').write_text('\n'.join(rows)+'\n')
        checks[name] = dict(endpoint_names=['a', 'b'], corner_names=corners.copy(),
            negative_vertex_endpoints=baseline()['hold_violating_endpoints'])
    if fault == 'corner_order': checks['after']['corner_names'].reverse()
    if fault == 'endpoint_set': checks['after']['endpoint_names'][0] = 'other'
    # The underlying validator preserves receipt order; this layer must require
    # the frozen native snapshot's sorted order and independently match counts.
    monkeypatch.setattr(repair.shared, 'validate_stage', lambda path, row, sdc: checks[row['name']])
    monkeypatch.setattr(repair.parent.endpoints, 'load_stage', lambda *args: dict(loaded=True))
    if fault:
        with pytest.raises(ValueError): repair.stage_evidence(tmp_path, ('before', 'after'), '0'*64, corners)
    else:
        checked, _, metrics = repair.stage_evidence(tmp_path, ('before', 'after'), '0'*64, corners)
        assert checked == checks and set(metrics) == {'before', 'after'}
