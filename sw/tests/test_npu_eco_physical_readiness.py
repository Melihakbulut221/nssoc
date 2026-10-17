# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Readiness rejection controls; synthetic boot fixtures are not a boot result."""
import copy
import importlib.util
import json
from pathlib import Path
import stat
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('npu_readiness', ROOT / 'scripts/check_npu_eco_physical_readiness.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def binary_fixture():
    prior = [['prior', i] for i in range(33517)]
    hard = [list(x) for x in sorted(gate.HARD)]
    new = [['new', i] for i in range(800)]
    catalog = {'preserved_proved': prior, 'hard': [{'original': x} for x in hard],
               'untested': [{'original': x} for x in new], 'original_bits': 34321}
    final = {'status': 'COMPLETE_BINARY_BOUNDARY_RELATION_PROVED', 'state_bijection_proved': True,
             'original_bits': 34321, 'preserved_prior': 33517, 'independently_proved_hard': 4,
             'new_800_proved': 800, 'total_unique_proved': 34321, 'unproved_original_bits': [],
             'actual_counterexample_original_bits': [], 'proved_800_original_bits': new}
    batches = [{'key': (i // 4, i % 4), 'original_ids': new[i::64], 'verdict': 'PROVED_ALL_BINARY_BOUNDARY_EQUATIONS',
                'inputs': 10828, 'latches': 0, 'assumptions': 0, 'native_abc_exitcode': 0} for i in range(64)]
    return catalog, final, batches


def test_complete_three_disjoint_sets():
    result = gate.validate_union(*binary_fixture())
    assert result == {'prior': 33517, 'separate_hard': 4, 'grouped_new': 800,
                      'total': 34321, 'symbolic_inputs': 10828, 'batches': 64}


@pytest.mark.parametrize('fault', ['missing_hard', 'wrong_hard', 'prior_duplicate', 'overlap',
                                  'missing_batch', 'duplicate_batch', 'narrow_inputs', 'assumption',
                                  'latch', 'solver_failure', 'unproved', 'cex', 'false_final',
                                  'count_only_forgery', 'duplicate_new', 'negative_identity'])
def test_incomplete_binary_relation_rejected(fault):
    c, f, b = binary_fixture()
    if fault == 'missing_hard':
        c['hard'].pop()
    elif fault == 'wrong_hard':
        c['hard'][0]['original'] = ['different', 0]
    elif fault == 'prior_duplicate':
        c['preserved_proved'][1] = c['preserved_proved'][0]
    elif fault == 'overlap':
        c['untested'][0]['original'] = c['preserved_proved'][0]
    elif fault == 'missing_batch':
        b.pop()
    elif fault == 'duplicate_batch':
        b[1]['key'] = b[0]['key']
    elif fault == 'narrow_inputs':
        b[0]['inputs'] = 10827
    elif fault == 'assumption':
        b[0]['assumptions'] = 1
    elif fault == 'latch':
        b[0]['latches'] = 1
    elif fault == 'solver_failure':
        b[0]['native_abc_exitcode'] = 9
    elif fault == 'unproved':
        f['unproved_original_bits'] = [['new', 0]]
    elif fault == 'cex':
        f['actual_counterexample_original_bits'] = [['new', 0]]
    elif fault == 'false_final':
        f['state_bijection_proved'] = False
    elif fault == 'count_only_forgery':
        b[0]['original_ids'][0] = ['foreign', 0]
    elif fault == 'duplicate_new':
        b[0]['original_ids'][0] = b[1]['original_ids'][0]
    else:
        c['preserved_proved'][0] = ['prior', -1]
    with pytest.raises(ValueError):
        gate.validate_union(c, f, b)


def boot_fixture():
    startup = {'status': 'COMPILED_READY_FOR_FOUR_STATE_BOOT', 'github_source_commit': gate.BOOT_COMMIT,
               'variant': 'candidate', 'memory': 'vendor', 'cycle_bound': 3000000,
               'eco': {'original': gate.PAIR['candidate'], 'candidate': gate.FACTORED},
               'sources': {'model.v': {'sha256': 'a' * 64, 'bytes': 17}},
               'methods': {'strict.py': {'sha256': 'b' * 64, 'bytes': 10}},
               'compile': {'command': ['iverilog', '-DTIMEOUT_CYCLES=3000000'], 'returncode': 0},
               'boot_command': ['vvp', '-i', '/native/factored.vvp', '+flash0=/native/flash.hex'],
               'outputs': {}, 'scope': 'Synthetic acceptance boundary fixture only'}
    row = copy.deepcopy(startup)
    row.update(status='PASS_FOUR_STATE_MAPPED_BOOT_AND_POWER_ON_MBIST_ONLY',
               boot_execution={'returncode': 0, 'command': startup['boot_command'][:]})
    run = {'id': gate.BOOT_RUN, 'head_sha': gate.BOOT_COMMIT, 'run_attempt': 1,
           'status': 'completed', 'conclusion': 'success'}
    artifact = {'id': 1, 'name': 'npu-init-eco-final-1', 'digest': 'sha256:' + 'c' * 64,
                'workflow_run': {'id': gate.BOOT_RUN, 'head_sha': gate.BOOT_COMMIT}}
    log = 'QUALIFICATION_MBIST PASS cycles=983048\nLOGICROM_GL PASS checks=28\n'
    return row, startup, run, artifact, log


def test_synthetic_complete_boot_boundary_only():
    result = gate.validate_boot(*boot_fixture())
    assert result['firmware_checks'] == 28 and result['vendor_eco_netlist'] == gate.FACTORED


@pytest.mark.parametrize('fault', ['running', 'failed', 'missing_status', 'cancelled_run', 'running_run',
                                  'different_run', 'different_commit', 'retry', 'startup_artifact',
                                  'foreign_artifact', '26_checks', 'mbist_missing', 'duplicate_pass',
                                  'fatal', 'exit_nonzero', 'wrong_command', 'changed_model',
                                  'changed_method', 'changed_compile', 'changed_netlist',
                                  'short_workload', 'independent_memory'])
def test_boot_cannot_be_waived_by_binary_proof(fault):
    row, startup, run, artifact, log = boot_fixture()
    if fault == 'running':
        row['status'] = 'RUNNING_FOUR_STATE_BOOT_AND_POWER_ON_MBIST'
    elif fault == 'failed':
        row['status'] = 'FAILED_PRESERVED'
    elif fault == 'missing_status':
        row.pop('status')
    elif fault == 'cancelled_run':
        run['conclusion'] = 'cancelled'
    elif fault == 'running_run':
        run['status'] = 'in_progress'
    elif fault == 'different_run':
        run['id'] += 1
    elif fault == 'different_commit':
        run['head_sha'] = '0' * 40
    elif fault == 'retry':
        run['run_attempt'] = 2
    elif fault == 'startup_artifact':
        artifact['name'] = 'npu-init-eco-startup-1'
    elif fault == 'foreign_artifact':
        artifact['workflow_run']['id'] += 1
    elif fault == '26_checks':
        log = log.replace('checks=28', 'checks=26')
    elif fault == 'mbist_missing':
        log = 'LOGICROM_GL PASS checks=28\n'
    elif fault == 'duplicate_pass':
        log += 'LOGICROM_GL PASS checks=28\n'
    elif fault == 'fatal':
        log += 'FATAL: rejected\n'
    elif fault == 'exit_nonzero':
        row['boot_execution']['returncode'] = 1
    elif fault == 'wrong_command':
        row['boot_execution']['command'].append('+relax')
    elif fault == 'changed_model':
        row['sources']['model.v']['sha256'] = 'd' * 64
    elif fault == 'changed_method':
        row['methods']['strict.py']['sha256'] = 'd' * 64
    elif fault == 'changed_compile':
        row['compile']['command'].append('-DTWO_STATE')
    elif fault == 'changed_netlist':
        row['eco']['candidate'] = gate.PAIR['candidate']
    elif fault == 'short_workload':
        row['cycle_bound'] = 1000000
    else:
        row['memory'] = 'independent'
    with pytest.raises(ValueError):
        gate.validate_boot(row, startup, run, artifact, log)


@pytest.mark.parametrize('member', ['../result.json', '/absolute', 'a\\b', 'symlink', 'duplicate'])
def test_actual_unsafe_zip_rejected_before_boot_read(tmp_path, monkeypatch, member):
    startup = tmp_path / gate.STARTUP / 'result.json'
    startup.parent.mkdir(parents=True)
    startup.write_text('{}')
    monkeypatch.setattr(gate, 'STARTUP_SHA', gate.pin(startup)['sha256'])
    archive = tmp_path / 'capture.zip'
    with zipfile.ZipFile(archive, 'w') as z:
        info = zipfile.ZipInfo(member)
        if member == 'symlink':
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
        z.writestr(info, '{}')
        if member == 'duplicate':
            with pytest.warns(UserWarning):
                z.writestr(info, '{}')
    ap = gate.pin(archive)
    run = tmp_path / 'run.json'; run.write_text('{}')
    meta = tmp_path / 'artifact.json'
    meta.write_text(json.dumps({'size_in_bytes': ap['bytes'], 'digest': 'sha256:' + ap['sha256']}))
    with pytest.raises(ValueError, match='Unsafe|Duplicate'):
        gate.verify_boot(tmp_path, archive, run, meta)


def test_missing_boot_blocks_whole_gate_after_valid_prior_components(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, 'verify_binary', lambda root: {'count': 34321})
    monkeypatch.setattr(gate, 'verify_mapping', lambda root: {'physical_input': gate.PHYSICAL_INPUT})
    result = gate.check(tmp_path)
    assert result['status'] == 'BLOCKED'
    assert 'Completed strict boot' in result['blocker']
    assert not result['physical_flow_executed'] and not result['physical_signoff']


def test_pin_mismatch_rejected_even_if_document_claims_pass(tmp_path):
    path = tmp_path / 'result.json'
    path.write_text('{"status":"PASS"}')
    with pytest.raises(ValueError, match='Pinned evidence differs'):
        gate.document(path, '0' * 64)
