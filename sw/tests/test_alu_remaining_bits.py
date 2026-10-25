# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Identity/coverage/provenance mutations; native tiny controls run separately."""
import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
import prove_alu_remaining_bits as proof  # noqa: E402


def input_cases():
    previous = dict(proved=[['old', i] for i in range(33505)], original_bits=34321,
        remaining=[dict(parent=f'parent{i//16}', bit=i%16, original=['new', i]) for i in range(816)])
    selected = [dict(x, id=f'bit{i}', native_returncode=0, verdict=proof.PASS if i < 12 else proof.TIMEOUT)
                for i, x in enumerate(previous['remaining'][:16])]
    benchmark = dict(per_bit=selected, selected_bits=16, selected_proved_bits=12, selected_timeouts=4)
    return previous, benchmark


def value():
    return proof.catalog(*input_cases())


def batch_rows(catalog):
    result = []
    for shard in range(16):
        for batch in range(4):
            selected = proof.batch_selection(catalog, shard, batch)
            groups = [dict(shard=i, groups=[]) for i in range(4)]
            for i, bit in enumerate(selected):
                groups[i%4]['groups'].append(dict(id=bit['id'], verdict=proof.PASS, native_returncode=0,
                    log=dict(bytes=1, sha256='f'*64)))
            result.append(dict(shard=shard, batch=batch, groups=groups))
    return result


def test_actual_lock_keeps_original_graph_methods_and_fixed_limits():
    lock = proof.load_lock()
    assert lock['preserved_proved']+lock['untested']+lock['hard'] == 34321
    assert lock['refined_miter']['bytes'] == 143063944
    assert lock['refined_miter']['sha256'] == '30a72098dbe310b987cd868b590e548428a3f1fc03b3e232e06886c33c0c6151'


@pytest.mark.parametrize('fault', ['count','prior_run','prior_source','prior_verdict','archive_hash','archive_url',
    'benchmark_run','benchmark_source','benchmark_hash','runtime','graph','batch_sizes','limit','missing_method'])
def test_changed_lock_contract_rejected(tmp_path, monkeypatch, fault):
    row = proof.load_lock()
    if fault == 'count': row['preserved_proved'] += 1
    if fault == 'prior_run': row['refinement']['run_id'] += 1
    if fault == 'prior_source': row['refinement']['source_commit'] = '0'*40
    if fault == 'prior_verdict': row['refinement']['source_conclusion'] = 'success'
    if fault == 'archive_hash': row['refinement']['archives']['common']['sha256'] = '0'*64
    if fault == 'archive_url': row['refinement']['archives']['common']['url'] = 'https://example.org/x.zip'
    if fault == 'benchmark_run': row['benchmark']['run_id'] += 1
    if fault == 'benchmark_source': row['benchmark']['source_commit'] = '0'*40
    if fault == 'benchmark_hash': row['benchmark']['artifact']['sha256'] = '0'*64
    if fault == 'runtime': row['runtime']['sha256'] = '0'*64
    if fault == 'graph': row['refined_miter']['sha256'] = '0'*64
    if fault == 'batch_sizes': row['batch_sizes'] = [16,16,16,2]
    if fault == 'limit': row['per_bit_sat_seconds'] = 999
    if fault == 'missing_method': row['source_method_pins'].pop(next(iter(row['source_method_pins'])))
    path = tmp_path/proof.LOCK; path.parent.mkdir(parents=True); path.write_text(json.dumps(row))
    monkeypatch.setattr(proof, 'ROOT', tmp_path)
    with pytest.raises(ValueError): proof.load_lock()


def test_all_800_identities_are_unique_and_disjoint_from33517_and_hard4():
    catalog = value()
    assert len(catalog['preserved_proved']) == 33517
    assert len(catalog['untested']) == 800 and len(catalog['hard']) == 4
    observed = [tuple(x['original']) for s in range(16) for b in range(4) for x in proof.batch_selection(catalog,s,b)]
    assert len(set(observed)) == len(observed) == 800
    assert set(observed).isdisjoint(map(tuple,catalog['preserved_proved']))
    assert set(observed).isdisjoint(tuple(x['original']) for x in catalog['hard'])
    for s in range(16):
        assert [len(proof.batch_selection(catalog,s,b)) for b in range(4)] == [16,16,14,4]


@pytest.mark.parametrize('fault', ['duplicate_proved','duplicate_remaining','overlap','omit_remaining','duplicate_selected',
    'wrong_original','wrong_parent','wrong_bit','wrong_native_code','counterexample','unknown_status','wrong_pass_count'])
def test_original_correspondence_and_preserved_outcome_fail_closed(fault):
    previous, benchmark = input_cases()
    if fault == 'duplicate_proved': previous['proved'][1] = previous['proved'][0]
    if fault == 'duplicate_remaining': previous['remaining'][1] = previous['remaining'][0]
    if fault == 'overlap': previous['proved'][0] = previous['remaining'][0]['original']
    if fault == 'omit_remaining': previous['remaining'].pop()
    if fault == 'duplicate_selected': benchmark['per_bit'][1] = benchmark['per_bit'][0]
    if fault == 'wrong_original': benchmark['per_bit'][0]['original'] = ['old',0]
    if fault == 'wrong_parent': benchmark['per_bit'][0]['parent'] = 'another'
    if fault == 'wrong_bit': benchmark['per_bit'][0]['bit'] += 1
    if fault == 'wrong_native_code': benchmark['per_bit'][0]['native_returncode'] = 1
    if fault == 'counterexample': benchmark['per_bit'][0]['verdict'] = proof.CEX
    if fault == 'unknown_status': benchmark['per_bit'][0]['verdict'] = 'success'
    if fault == 'wrong_pass_count': benchmark['selected_proved_bits'] = 16
    with pytest.raises(ValueError): proof.catalog(previous, benchmark)


@pytest.mark.parametrize('shard,batch', [(-1,0),(16,0),(True,0),(0,-1),(0,4),(0,False)])
def test_bad_batch_coordinates_are_rejected(shard,batch):
    with pytest.raises(ValueError): proof.batch_selection(value(),shard,batch)


def test_even800_successes_leave_four_unproved_and_boot_blocked():
    catalog = value(); result = proof.merged_verdict(catalog, batch_rows(catalog))
    assert result['new_proved_bits'] == 800 and result['total_proved_bits'] == 34317
    assert result['remaining_unproved_bits'] == 4
    assert result['state_bijection_proved'] is False and result['candidate_adopted'] is False
    assert result['unresolved_four_state_boot_failure'] is True


@pytest.mark.parametrize('fault', ['omit_batch','duplicate_batch','wrong_shard','omit_bit','duplicate_bit','unknown_id',
                                  'unknown_verdict','native_failure'])
def test_no_incomplete_or_duplicated_new_proof_merge(fault):
    catalog = value(); rows = batch_rows(catalog)
    if fault == 'omit_batch': rows.pop()
    if fault == 'duplicate_batch': rows[-1] = copy.deepcopy(rows[0])
    if fault == 'wrong_shard': rows[-1]['shard'] = 0
    if fault == 'omit_bit': rows[0]['groups'][0]['groups'].pop()
    if fault == 'duplicate_bit': rows[0]['groups'][0]['groups'].append(copy.deepcopy(rows[0]['groups'][0]['groups'][0]))
    if fault == 'unknown_id': rows[0]['groups'][0]['groups'][0]['id'] = 'foreign'
    if fault == 'unknown_verdict': rows[0]['groups'][0]['groups'][0]['verdict'] = 'OK'
    if fault == 'native_failure': rows[0]['groups'][0]['groups'][0]['native_returncode'] = 1
    with pytest.raises(ValueError): proof.merged_verdict(catalog, rows)


def test_real_timeout_and_counterexample_are_distinct_unproved_outcomes():
    catalog = value(); rows = batch_rows(catalog)
    rows[0]['groups'][0]['groups'][0]['verdict'] = proof.TIMEOUT
    rows[1]['groups'][0]['groups'][0]['verdict'] = proof.CEX
    result = proof.merged_verdict(catalog,rows)
    assert (result['new_proved_bits'], result['new_timeouts'], result['new_counterexamples']) == (798,1,1)
    assert result['remaining_unproved_bits'] == 6


def test_native_launch_strips_credentials_and_has_no_elapsed_timeout(tmp_path,monkeypatch):
    script = tmp_path/'run.tcl'; script.write_text('test')
    monkeypatch.setenv('GH_TOKEN','private'); monkeypatch.setenv('GITHUB_TOKEN','private')
    calls = []
    def run(command, **options):
        calls.append((command,options))
        options['stdout'].write('controlled subprocess test\n')
        return subprocess.CompletedProcess(command,0)
    monkeypatch.setattr(proof.subprocess,'run',run)
    row = proof.native_execute(Path('/runtime.AppImage'),script,tmp_path,'native',tcl=True)
    assert row['returncode'] == 0
    assert calls[0][0] == ['/runtime.AppImage','yosys','-Q','-T','-c',str(script)]
    assert 'timeout' not in calls[0][1] and 'GH_TOKEN' not in calls[0][1]['env'] and 'GITHUB_TOKEN' not in calls[0][1]['env']
    assert callable(calls[0][1]['preexec_fn'])


def network_fixture(monkeypatch, fault=None):
    locked = proof.load_lock(); source = locked['benchmark']; entry = source['artifact']
    meta = dict(id=entry['id'],name=entry['name'],size_in_bytes=entry['bytes'],digest='sha256:'+entry['sha256'],
        expired=False,workflow_run=dict(id=source['run_id'],head_sha=source['source_commit']))
    if fault == 'id': meta['id'] += 1
    if fault == 'digest': meta['digest'] = 'sha256:'+'0'*64
    if fault == 'source': meta['workflow_run']['head_sha'] = '0'*40
    if fault == 'run': meta['workflow_run']['id'] += 1
    if fault == 'size': meta['size_in_bytes'] += 1
    if fault == 'name': meta['name'] = 'different'
    if fault == 'expired': meta['expired'] = True
    def api(_):
        if fault == 'unavailable': raise subprocess.CalledProcessError(1,['gh'])
        return meta
    calls=[]
    monkeypatch.setattr(proof.ref,'api',api)
    monkeypatch.setattr(proof.state.common,'download',lambda e,p:calls.append((e,p)))
    monkeypatch.setattr(proof.state.common,'verify_file',lambda p,e:None)
    monkeypatch.setattr(proof,'pin',lambda p:{k:entry[k] for k in ('bytes','sha256')})
    return source,entry,calls


@pytest.mark.parametrize('fault',['id','digest','source','run','size','name'])
def test_available_metadata_mismatch_never_uses_permanent_fallback(tmp_path,monkeypatch,fault):
    source,entry,calls=network_fixture(monkeypatch,fault)
    with pytest.raises(ValueError):proof.acquire(source,entry,tmp_path/'a.zip',permanent=True)
    assert not calls


@pytest.mark.parametrize('fault',['expired','unavailable',None])
def test_same_byte_permanent_archive_survives_expiry(tmp_path,monkeypatch,fault):
    source,entry,calls=network_fixture(monkeypatch,fault)
    result=proof.acquire(source,entry,tmp_path/'a.zip',permanent=True)
    assert len(calls)==1 and result['source']=='exact_permanent_asset'


def test_aggregate_writes_incomplete_receipt_before_failure(tmp_path,monkeypatch):
    catalog=value(); monkeypatch.setattr(proof,'verify_prepared',lambda _:({}, {}, catalog, {}))
    output=tmp_path/'verdict.json'
    with pytest.raises(ValueError):proof.aggregate(tmp_path,[],output)
    result=json.loads(output.read_text())
    assert result['status']=='INCOMPLETE_BATCH_SET_OR_FAILED_REPLAY' and result['state_bijection_proved'] is False


def test_workflow_runs16_jobs_four_at_once_and_uploads_every_attempt():
    text=(ROOT/proof.OWN[-1]).read_text()
    assert 'max-parallel: 4' in text and '15]' in text
    assert text.count('fetch-depth: 0')==3
    for batch in range(4):
        assert f'--batch {batch}' in text
        assert f'Preserve immutable batch{batch} outcome' in text
    assert text.count('include-hidden-files: true')==5
