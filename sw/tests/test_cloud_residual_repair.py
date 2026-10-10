# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Pure non-native gates for immutable candidate continuation and rejection."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
import run_cloud_residual_repair as repair


def locked(): return repair.lock(ROOT)


def baseline(): return dict(recorded_ms=1, **locked()['baseline_metrics'])


@pytest.mark.parametrize('field', ['setup_wns_seconds', 'hold_wns_seconds', 'setup_tns_seconds',
    'hold_tns_seconds', 'setup_violating_endpoints', 'hold_violating_endpoints',
    'slew_violations', 'capacitance_violations', 'instance_count'])
def test_exact_candidate_baseline_rejects_any_measured_change(field):
    current = baseline(); repair.equal_metrics(current, locked()['baseline_metrics'])
    current[field] += 1e-15 if field.endswith('_seconds') else 1
    with pytest.raises(ValueError, match='fresh baseline'): repair.equal_metrics(current, locked()['baseline_metrics'])


def test_observation_timestamp_is_not_a_physical_identity():
    current = baseline(); current['recorded_ms'] += 100
    repair.equal_metrics(current, locked()['baseline_metrics'])


@pytest.mark.parametrize('fault', [None, 'c10-setup', 'c10-hold', 'matched-cap', 'candidate-setup',
    'candidate-hold', 'candidate-count', 'candidate-tns', 'no-electrical-gain', 'reload', 'protected'])
def test_five_reference_guards_cannot_be_waived(fault):
    before = baseline(); after = copy.deepcopy(before)
    for key,value in locked()['combined_parent_metrics'].items():
        if key.endswith('_ns'): after[key.removesuffix('_ns')+'_seconds'] = value*1e-9
        else: after[key] = min(after.get(key, value), value)
    after.update(slew_violations=0, capacitance_violations=0, hold_violating_endpoints=64, hold_wns_seconds=-0.15e-9, hold_tns_seconds=-2e-9)
    after.update(setup_wns_seconds=-4e-9, setup_tns_seconds=-3.5e-6, setup_violating_endpoints=1300)
    if fault == 'c10-setup': after['setup_wns_seconds'] = -5e-9
    if fault == 'c10-hold': after['hold_wns_seconds'] = -2e-9
    if fault == 'matched-cap': after['capacitance_violations'] = 2
    if fault == 'candidate-setup': after['setup_wns_seconds'] = before['setup_wns_seconds']-0.01e-9
    if fault == 'candidate-hold': after['hold_wns_seconds'] = before['hold_wns_seconds']-0.01e-9
    if fault == 'candidate-count': after['hold_violating_endpoints'] = 68
    if fault == 'candidate-tns': after['setup_tns_seconds'] = before['setup_tns_seconds']-0.01e-9
    if fault == 'no-electrical-gain': after = copy.deepcopy(before)
    metrics = {repair.STAGES[0]: before, repair.STAGES[-1]: after}
    result = repair.guard(metrics, locked(), fault != 'reload', fault != 'protected')
    assert result['aggregate_estimate_guard_passed'] is (fault is None)
    assert result['candidate_adopted'] is result['timing_accepted'] is result['manufacturing_approval'] is False
    assert result['zero_violations'] is False
    assert set(result['no_regression']) == {'selected_c10','matched_c10','combined_parent','electrical_first','candidate_before'}


@pytest.mark.parametrize('fault', ['protected-flag', 'clock-type', 'clock-connection', 'missing-original'])
def test_clock_and_dont_touch_objects_preserved(fault):
    before = {('instance', 'keep'): dict(dont_touch='1', signal_type='', connections=''),
        ('net', 'clk'): dict(dont_touch='0', signal_type='CLOCK', connections='d/X|q/CLK')}
    after = copy.deepcopy(before)
    after[('instance', 'newbuf')] = dict(dont_touch='0', signal_type='', connections='')
    assert repair.verify_protected(before, after)['added_objects'] == 1
    if fault == 'protected-flag': after[('instance', 'keep')]['dont_touch'] = '0'
    if fault == 'clock-type': after[('net', 'clk')]['signal_type'] = 'SIGNAL'
    if fault == 'clock-connection': after[('net', 'clk')]['connections'] = 'd/X|other/CLK'
    if fault == 'missing-original': del after[('instance', 'keep')]
    with pytest.raises(ValueError, match='Original dont-touch'): repair.verify_protected(before, after)


@pytest.mark.parametrize('fault', ['duplicate', 'invalid-flag', 'invalid-kind', 'wrong-columns'])
def test_status_parser_rejects_incomplete_or_ambiguous_contract(tmp_path, fault):
    content = 'kind\tname\tdont_touch\tsignal_type\tconnections\nnet\tn\t0\tSIGNAL\t\n'
    if fault == 'duplicate': content += 'net\tn\t0\tSIGNAL\t\n'
    if fault == 'invalid-flag': content = content.replace('\t0\t', '\tmaybe\t')
    if fault == 'invalid-kind': content = content.replace('net\tn', 'unknown\tn')
    if fault == 'wrong-columns': content = content.replace('signal_type', 'scope')
    path = tmp_path/'status.tsv'; path.write_text(content)
    with pytest.raises(ValueError): repair.protected_status(path)


def test_overlay_verifies_all_four_actual_source_views_and_baseline_tcl(tmp_path):
    methods = tmp_path/'methods'/Path(repair.LOCK).parent; methods.mkdir(parents=True)
    candidate = tmp_path/'candidate'; candidate.mkdir()
    l = locked(); pins = {}
    for name in repair.parent.VIEW_NAMES:
        p = candidate/name; p.write_text('\n'.join(t['cell']['body'] for t in l['hold_targets']) if name == 'soc_top.v' else 'unadopted '+name); pins[name] = repair.eco.file_pin(p)
    l['candidate_files'] = pins
    l['graph_evidence']['netlist_sha256'] = pins['soc_top.v']['sha256']
    (tmp_path/'methods'/repair.LOCK).write_text(json.dumps(l))
    baseline_tcl = tmp_path/'candidate-baseline.tcl'; baseline_tcl.write_text('immutable baseline')
    row = dict(original_capture_validation='PASS', producer=l['producer'],
        candidate_overlay=dict(directory=str(candidate), files=pins, baseline_tcl=repair.eco.file_pin(baseline_tcl)))
    assert repair.verify_overlay(tmp_path, row) == candidate
    (candidate/'soc_top.odb').write_text('mutated')
    with pytest.raises(ValueError, match='pinned input'): repair.verify_overlay(tmp_path, row)


def test_full_native_input_is_never_loaded_locally(tmp_path, monkeypatch):
    monkeypatch.delenv('GITHUB_ACTIONS', raising=False)
    with pytest.raises(ValueError, match='cloud-only'): repair.prepare_overlay(tmp_path, {})


def test_sources_are_complete_tcl_is_balanced_and_no_setup_repair():
    assert repair.specification().sources == repair.SOURCES
    for name in repair.SOURCES: assert (ROOT/name).is_file(), name
    for name in (repair.HELPER, repair.FIXTURE, repair.STEP, repair.BASELINE):
        result = subprocess.run(['tclsh'], input=f'set f [open {{{ROOT/name}}}]; set s [read $f]; close $f; puts [info complete $s]\n',
            capture_output=True, text=True, check=True)
        assert result.stdout.strip() == '1' and not result.stderr
    source = (ROOT/repair.STEP).read_text()
    assert source.index('NSSOC_ELECTRICAL_BASELINE_EXACT_BEFORE_REPAIR') < source.index('nssoc_electrical_margin_repair $driver $netname')
    assert 'nssoc_timing_experiment' not in source and 'repair_timing' not in source


def test_workflow_is_opt_in_cloud_and_preserves_exact_git_producer():
    text = (ROOT/'.github/workflows/timing-residual-repair.yml').read_text()
    assert 'fetch-depth: 0' in text and 'cancel-in-progress: false' in text
    assert text.count('      - .github/workflows/timing-residual-repair.yml') == 1
    assert 'timeout-minutes: 360' in text and '--seconds 900' in text
    assert 'run_cloud_residual_repair.py validate' in text


def test_native_api_is_bound_to_executed_runtime_revision():
    data = locked()['native_api_source']
    assert data['commit'] == 'dcf36133a369abc8f3c5e5738cd4d82e4903c0e0'
    assert {'RepairHold.cc','Resizer.i','src/rsz/src/RepairDesign.cc'} <= set(data['files'])
    for pin in data['files'].values():
        assert '/'+data['commit']+'/' in pin['url']; repair.common.pin(pin)


def test_tiny_fixture_preconditions_do_not_change_reference_sdc():
    text = (ROOT/repair.FIXTURE).read_text()
    assert 'set_max_capacitance' not in text and 'set_max_transition' not in text
    assert 'before_hold_seconds $before after_hold_seconds $after' in text
    assert all(name in text for name in ('missing_api_rejected', 'wrong_endpoint_rejected', 'native_setup_guard_preserved', 'protected_rejected'))


def proof_chain():
    def pin(value): return dict(bytes=1, sha256=value*64)
    original, parent, repaired, liberty, macro = map(pin, 'abcde')
    manifest = dict(files={repair.eco.BEFORE: original, repair.eco.STANDARD: liberty, repair.eco.MACRO: macro})
    lock = dict(candidate_files={'soc_top.v': parent})
    def proof(before, after):
        return dict(before=before, after=after, result=dict(status='PASS within scope',
            sources={name: p['sha256'] for name, p in zip(('before','after','lib','macro'), (before,after,liberty,macro), strict=True)}))
    row = dict(logic_proofs={'parent-logic': proof(original, parent), 'electrical-logic': proof(parent, repaired)},
        diagnostic=dict(native=dict(candidate_files={'soc_top.v': repaired})))
    return row, lock, manifest


@pytest.mark.parametrize('fault', [None, 'wrong-original', 'wrong-parent', 'wrong-export',
    'producer-status', 'repair-status', 'missing-liberty', 'missing-macro', 'missing-netlist'])
def test_actual_limited_proofs_bind_the_complete_original_parent_export_chain(fault):
    row, lock, manifest = proof_chain()
    proofs = row['logic_proofs']
    if fault == 'wrong-original': proofs['parent-logic']['before'] = dict(bytes=1, sha256='f'*64)
    if fault == 'wrong-parent': proofs['electrical-logic']['before'] = dict(bytes=1, sha256='f'*64)
    if fault == 'wrong-export': proofs['electrical-logic']['after'] = dict(bytes=1, sha256='f'*64)
    if fault == 'producer-status': proofs['parent-logic']['result']['status'] = 'INCOMPLETE'
    if fault == 'repair-status': proofs['electrical-logic']['result']['status'] = 'INCOMPLETE'
    if fault == 'missing-liberty': del proofs['electrical-logic']['result']['sources']['lib']
    if fault == 'missing-macro': del proofs['parent-logic']['result']['sources']['macro']
    if fault == 'missing-netlist': del proofs['electrical-logic']['result']['sources']['after']
    if fault is None: assert repair.validate_proof_inputs(row, lock, manifest)
    else:
        with pytest.raises(ValueError): repair.validate_proof_inputs(row, lock, manifest)


def test_candidate_overlay_begins_after_native_env_restore_and_baseline_gate(tmp_path):
    step = (ROOT/repair.STEP).read_text()
    assert step.index('source $::env(SCRIPTS_DIR)/openroad/common/io.tcl') < step.index('set ::env(CURRENT_ODB) $::env(NSSOC_ELECTRICAL_CANDIDATE_ODB)')
    assert step.index('NSSOC_ELECTRICAL_NATIVE_GATE_PASS_BEFORE_CANDIDATE_LOAD') < step.index('read_current_odb')
    assert step.index('source $::env(NSSOC_ELECTRICAL_BASELINE_TCL)') < step.index('nssoc_electrical_margin_repair $driver $netname')
    assert 'NSSOC_ELECTRICAL_CANDIDATE_ODB' not in (ROOT/'scripts/run_cloud_hold_diagnostic.py').read_text()


def test_generated_baseline_tcl_preserves_actual_graph_brackets_and_margins(tmp_path):
    l = locked(); path = tmp_path/'baseline.tcl'; path.write_text(repair.baseline_script(l))
    result = subprocess.run(['tclsh'], input=f'source {{{path}}}\nputs [llength [dict get $nssoc_electrical_expected_targets fanout3120]]\nputs [dict get $nssoc_electrical_expected_metrics instance_count]\n',
        capture_output=True, text=True, check=True)
    assert result.stdout.splitlines() == ['6', '103895'] and not result.stderr
    l['graph_evidence']['targets']['fanout3120']['terminals'][0]['odb_instance'] = 'unsafe;exec'
    with pytest.raises(ValueError, match='Unsafe target graph'): repair.baseline_script(l)


def write_graph(path, l):
    text = 'driver\tnet\tinstance\tmaster\tport\n'
    for driver, graph in l['graph_evidence']['targets'].items():
        for term in graph['terminals']:
            text += '\t'.join([driver, graph['net'], *(term[k] for k in ('odb_instance','master','port'))])+'\n'
    path.write_text(text)


@pytest.mark.parametrize('fault', [None, 'antenna-removed', 'wrong-sram-bit', 'wrong-net', 'duplicate', 'unescaped-native-name'])
def test_actual_new_driver_graph_includes_antenna_and_exact_sram_bits(tmp_path, fault):
    l = locked(); path = tmp_path/'graph.tsv'; write_graph(path, l); text = path.read_text()
    if fault == 'antenna-removed': text = '\n'.join(x for x in text.splitlines() if 'wire21194' not in x)+'\n'
    if fault == 'wrong-sram-bit': text = text.replace('d[37]', 'd[38]')
    if fault == 'wrong-net': text = text.replace('net3120', 'net3121')
    if fault == 'duplicate': text += text.splitlines()[1]+'\n'
    if fault == 'unescaped-native-name': text = text.replace('bank\\[0\\]', 'bank[0]')
    path.write_text(text)
    if fault is None:
        result = repair.verify_graph(path, l)
        assert result['exact'] and result['terminal_count'] == 6
    else:
        with pytest.raises(ValueError, match='terminal graph'): repair.verify_graph(path, l)


@pytest.mark.parametrize('fault', [None, 'placement-hash', 'unwitnessed-rename', 'native-name', 'macro-master', 'logical-name', 'omitted-witness'])
def test_native_instance_spelling_is_bound_to_exact_captured_placement(tmp_path, fault):
    l = locked(); graph = l['graph_evidence']; witness = graph['native_instance_witness']
    term = next(t for t in graph['targets']['fanout3120']['terminals'] if 'bank[0]' in t['instance'])
    if fault == 'placement-hash': witness['member_pin']['sha256'] = '0'*64
    if fault == 'unwitnessed-rename': graph['targets']['fanout3120']['terminals'][0]['odb_instance'] += '_different'
    if fault == 'native-name': term['odb_instance'] = term['instance']
    if fault == 'macro-master': term['master'] = 'different'
    if fault == 'logical-name': term['instance'] = term['odb_instance']
    if fault == 'omitted-witness': witness['instances'].pop()
    path = tmp_path/repair.LOCK; path.parent.mkdir(parents=True); path.write_text(json.dumps(l))
    if fault is None: assert repair.lock(tmp_path) == l
    else:
        with pytest.raises(ValueError): repair.lock(tmp_path)


def test_generated_tcl_retains_literal_native_backslashes_and_does_not_unescape_ports(tmp_path):
    l = locked(); path = tmp_path/'baseline.tcl'; path.write_text(repair.baseline_script(l))
    result = subprocess.run(['tclsh'], input=f'source {{{path}}}\nforeach term [dict get $nssoc_electrical_expected_targets fanout3120] {{puts [join $term |]}}\n',
        capture_output=True, text=True, check=True)
    expected = ['|'.join(t[k] for k in ('odb_instance','master','port'))
                for t in l['graph_evidence']['targets']['fanout3120']['terminals']]
    assert result.stdout.splitlines() == expected and not result.stderr
    assert any('bank\\[0\\].mem|SP6TSRAM512x64|d[37]' in line for line in expected)


@pytest.mark.parametrize('atom', ['bad\\nname', 'bad\\;name', 'bad\\[0\\];exec', 'bad\\\nname', '{bad}', 'bad name'])
def test_native_name_support_does_not_accept_arbitrary_tcl_escapes(atom):
    l = locked(); l['graph_evidence']['targets']['fanout3120']['terminals'][0]['odb_instance'] = atom
    with pytest.raises(ValueError, match='Unsafe target graph'): repair.baseline_script(l)


def parent_record(l):
    return dict(status='COMPLETE_DIAGNOSTIC_ONLY',diagnostic=dict(
        native=dict(candidate_files=l['candidate_files'],timing_metrics=dict(reload_repeat=dict(recorded_ms=0,**l['baseline_metrics']))),
        independently_checked_stages=dict(reload_repeat=dict(fingerprints=l['baseline_fingerprints']),candidate_before=dict(fingerprints=dict(placement=l['graph_evidence']['native_instance_witness']['member_pin']['sha256']))),
        aggregate_guard_assessment=dict(reference_metrics=dict(selected_c10=l['original_selected_metrics'],
            matched_c10=l['original_matched_metrics'],combined_parent=l['combined_parent_metrics'],candidate_before=l['electrical_first_metrics']))))


@pytest.mark.parametrize('fault', [None, 'candidate', 'baseline', 'fingerprint', 'combined-parent', 'original'])
def test_original_c10_and_combined_parent_guards_survive_chaining(fault):
    l = locked(); row = copy.deepcopy(parent_record(l))
    if fault == 'candidate': row['diagnostic']['native']['candidate_files']['soc_top.odb']['sha256'] = '0'*64
    if fault == 'baseline': row['diagnostic']['native']['timing_metrics']['reload_repeat']['capacitance_violations'] = 0
    if fault == 'fingerprint': row['diagnostic']['independently_checked_stages']['reload_repeat']['fingerprints']['routing'] = '0'*64
    if fault == 'combined-parent': row['diagnostic']['aggregate_guard_assessment']['reference_metrics']['candidate_before']['setup_wns_ns'] -= 1
    if fault == 'original': row['diagnostic']['aggregate_guard_assessment']['reference_metrics']['matched_c10']['capacitance_violations'] = 3
    if fault is None: repair.validate_parent_contract(row,l)
    else:
        with pytest.raises(ValueError): repair.validate_parent_contract(row,l)


def test_just_removing_caps_cannot_mask_existing_setup_and_hold_regression():
    l = locked(); before = baseline(); after = dict(before,capacitance_violations=0)
    result = repair.guard({repair.STAGES[0]:before,repair.STAGES[-1]:after},l,True,True)
    assert result['no_regression']['candidate_before'] is True
    assert result['no_regression']['combined_parent'] is False
    assert result['aggregate_estimate_guard_passed'] is False


def test_second_actual_native_baseline_precedes_all_mutations():
    text=(ROOT/repair.STEP).read_text()
    assert text.index('timing_electrical_margin_baseline.tcl') < text.index('NSSOC_ELECTRICAL_TWO_BASELINES_EXACT_BEFORE_REPAIR') < text.index('nssoc_electrical_margin_repair $driver $netname')
    baseline_source=(ROOT/repair.BASELINE).read_text()
    assert 'timing_combined_reload.tcl' in baseline_source
    assert 'nssoc_electrical_expected_metrics' in baseline_source and 'nssoc_electrical_expected_files' in baseline_source
    helper=(ROOT/repair.HELPER).read_text()
    assert 'rsz::repair_hold_pin $pin 1e-10 2e-11 0 [expr {32.0/$before}] 1' in helper
    assert 'set_max_capacitance' not in helper and 'set_max_transition' not in helper


def hold_calls():
    row=locked();initial=103895;calls=[]
    for target in row['hold_targets']:
        calls.append(dict(endpoint=target['endpoint'],master=target['cell']['master'],
            status='ONE_NATIVE_PASS_COMPLETE',native_calls=1,initial_slack_seconds=target['after_seconds'],
            initial_instance_count=initial,actual_instance_count=initial+1,**row['hold_policy']))
        initial+=1
    return calls


@pytest.mark.parametrize('fault',[None,'setup-permission','setup-margin','hold-margin','passes','budget',
    'endpoint','master','missing','reordered','positive-called','growth','chain','skip-mutated','skip-negative'])
def test_ten_actual_endpoint_attempts_preserve_native_guards(fault):
    calls=hold_calls();initial=calls[0]['initial_instance_count'];final=calls[-1]['actual_instance_count']
    if fault=='setup-permission':calls[0]['allow_setup_violations']=True
    if fault=='setup-margin':calls[0]['setup_margin_seconds']=0
    if fault=='hold-margin':calls[0]['hold_margin_seconds']=0.02
    if fault=='passes':calls[0]['max_passes']=2
    if fault=='budget':calls[0]['max_added_cells']=33
    if fault=='endpoint':calls[0]['endpoint']='_135215_/CLK'
    if fault=='master':calls[0]['master']='sg13g2_dfrbpq_2'
    if fault=='missing':calls.pop()
    if fault=='reordered':calls.reverse()
    if fault=='positive-called':calls[0]['initial_slack_seconds']=0
    if fault=='growth':calls[0]['actual_instance_count']+=32
    if fault=='chain':calls[1]['initial_instance_count']-=1
    if fault in ('skip-mutated','skip-negative'):
        calls[0].update(native_calls=0,status='NO_LONGER_NEGATIVE')
        if fault=='skip-mutated':calls[0]['initial_slack_seconds']=0
    if fault is None:
        assert repair.validate_hold_calls(calls,locked(),initial,final)['native_calls']==10
    else:
        with pytest.raises(ValueError):repair.validate_hold_calls(calls,locked(),initial,final)


def test_skipped_no_longer_negative_endpoint_is_explicit_and_cannot_hide_mutation():
    calls=hold_calls();initial=calls[0]['initial_instance_count'];final=calls[-1]['actual_instance_count']-1
    for call in calls:call['actual_instance_count']-=1
    for call in calls[1:]:call['initial_instance_count']-=1
    calls[0].update(native_calls=0,status='NO_LONGER_NEGATIVE',initial_slack_seconds=1e-12)
    assert repair.validate_hold_calls(calls,locked(),initial,final)['native_calls']==9


@pytest.mark.parametrize('fault',[None,'missing-cell','duplicate-cell','wrong-D','wrong-clock','wrong-reset'])
def test_source_bound_hold_cell_bodies_bind_every_actual_connection(tmp_path,fault):
    row=locked();text='\n'.join(t['cell']['body'] for t in row['hold_targets'])
    if fault=='missing-cell':text=text.replace(row['hold_targets'][0]['cell']['body'],'')
    if fault=='duplicate-cell':text+='\n'+row['hold_targets'][0]['cell']['body']
    if fault=='wrong-D':text=text.replace('.D(_005960_)','.D(_005961_)')
    if fault=='wrong-clock':text=text.replace('clknet_leaf_162_clk_npu','clknet_leaf_163_clk_npu')
    if fault=='wrong-reset':text=text.replace('.RESET_B(net6187)','.RESET_B(net6188)')
    path=tmp_path/'candidate.v';path.write_text(text)
    if fault is None:assert repair.verify_source_hold_cells(path,row)
    else:
        with pytest.raises(ValueError,match='body/connectivity'):repair.verify_source_hold_cells(path,row)


@pytest.mark.parametrize('fault',['order','count','master','policy','measured-positive'])
def test_source_hold_lock_mutation_fails_closed(tmp_path,fault):
    row=locked()
    if fault=='order':row['hold_targets'].reverse()
    if fault=='count':row['hold_targets'].pop()
    if fault=='master':row['hold_targets'][0]['cell']['master']='different'
    if fault=='policy':row['hold_policy']['allow_setup_violations']=True
    if fault=='measured-positive':row['hold_targets'][0]['after_seconds']=0
    path=tmp_path/repair.LOCK;path.parent.mkdir(parents=True);path.write_text(json.dumps(row))
    with pytest.raises(ValueError):repair.lock(tmp_path)


def test_data_pin_repair_uses_si_seconds_and_fresh_reload_reports_all_targets():
    helper=(ROOT/repair.HELPER).read_text();step=(ROOT/repair.STEP).read_text()
    assert 'rsz::repair_hold_pin $pin 1e-10 2e-11 0 [expr {32.0/$before}] 1' in helper
    assert '$after-$before > 32' in helper and 'NO_LONGER_NEGATIVE' in helper
    assert step.index('timing_residual_repair_native.tcl') < step.index('read_current_odb')
    assert step.index('Source-bound hold endpoint slack differs') < step.index('nssoc_electrical_margin_repair $driver $netname')
    assert step.index('nssoc_electrical_margin_repair $driver $netname') < step.index('nssoc_residual_hold_repair $endpoint $master')
    reload=(ROOT/'hw/soc/pnr/timing_residual_reload.tcl').read_text()
    assert reload.index('timing_combined_reload.tcl') < reload.index('nssoc_residual_hold_reports')
