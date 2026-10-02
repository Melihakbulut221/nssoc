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
import run_cloud_electrical_repair as repair


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
def test_three_reference_guards_cannot_be_waived(fault):
    before = baseline(); after = copy.deepcopy(before)
    after.update(slew_violations=0, capacitance_violations=1)
    if fault == 'c10-setup': after['setup_wns_seconds'] = -5e-9
    if fault == 'c10-hold': after['hold_wns_seconds'] = -2e-9
    if fault == 'matched-cap': after['capacitance_violations'] = 2
    if fault == 'candidate-setup': after['setup_wns_seconds'] -= 0.01e-9
    if fault == 'candidate-hold': after['hold_wns_seconds'] -= 0.01e-9
    if fault == 'candidate-count': after['hold_violating_endpoints'] += 1
    if fault == 'candidate-tns': after['setup_tns_seconds'] -= 0.01e-9
    if fault == 'no-electrical-gain': after = copy.deepcopy(before)
    metrics = {repair.STAGES[0]: before, repair.STAGES[-1]: after}
    result = repair.guard(metrics, locked(), fault != 'reload', fault != 'protected')
    assert result['aggregate_estimate_guard_passed'] is (fault is None)
    assert result['candidate_adopted'] is result['timing_accepted'] is result['manufacturing_approval'] is False
    assert result['zero_violations'] is False


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
        p = candidate/name; p.write_text('unadopted '+name); pins[name] = repair.eco.file_pin(p)
    l['candidate_files'] = pins
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
    for name in (repair.HELPER, repair.FIXTURE, repair.STEP):
        result = subprocess.run(['tclsh'], input=f'set f [open {{{ROOT/name}}}]; set s [read $f]; close $f; puts [info complete $s]\n',
            capture_output=True, text=True, check=True)
        assert result.stdout.strip() == '1' and not result.stderr
    source = (ROOT/repair.STEP).read_text()
    assert source.index('NSSOC_ELECTRICAL_BASELINE_EXACT_BEFORE_REPAIR') < source.index('nssoc_electrical_repair $driver $netname')
    assert 'nssoc_timing_experiment' not in source and 'repair_timing' not in source


def test_workflow_is_opt_in_cloud_and_preserves_exact_git_producer():
    text = (ROOT/'.github/workflows/timing-electrical-repair.yml').read_text()
    assert 'fetch-depth: 0' in text and 'cancel-in-progress: false' in text
    assert text.count('      - .github/workflows/timing-electrical-repair.yml') == 1
    assert 'timeout-minutes: 360' in text and '--seconds 900' in text
    assert 'run_cloud_electrical_repair.py validate' in text


def test_native_api_is_bound_to_executed_runtime_revision():
    data = locked()['native_api_source']
    assert data['commit'] == 'dcf36133a369abc8f3c5e5738cd4d82e4903c0e0'
    assert set(data['files']) == {'src/rsz/src/Resizer.i', 'src/rsz/src/RepairDesign.cc', 'src/rsz/test/repair_wire9.tcl'}
    for pin in data['files'].values():
        assert '/'+data['commit']+'/' in pin['url']; repair.common.pin(pin)


def test_tiny_fixture_preconditions_do_not_change_reference_sdc():
    text = (ROOT/repair.FIXTURE).read_text()
    assert 'set_max_capacitance' not in text and 'set_max_transition' not in text
    assert 'real_capacitance_before $before real_capacitance_after $after' in text
    assert all(name in text for name in ('missing_api_rejected', 'wrong_net_rejected', 'missing_driver_rejected', 'dont_touch_rejected'))


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
    assert step.index('source $::env(NSSOC_ELECTRICAL_BASELINE_TCL)') < step.index('nssoc_electrical_repair $driver $netname')
    assert 'NSSOC_ELECTRICAL_CANDIDATE_ODB' not in (ROOT/'scripts/run_cloud_hold_diagnostic.py').read_text()
