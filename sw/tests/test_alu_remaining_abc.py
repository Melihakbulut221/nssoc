# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exhaustive original identities, OR semantics and fail-closed native CEX attribution."""
import copy
import json
import os
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
import prove_alu_remaining_abc as proof  # noqa: E402


def catalog():
    return dict(preserved_proved=[['prior', i] for i in range(33517)],
        hard=[dict(original=list(x)) for x in proof.hard.HARD],
        untested=[dict(id=f'bit{i}', parent=f'p{i//16}', bit=i%16, original=['new', i]) for i in range(800)])


def rows(value):
    return [dict(shard=s, batch=b, selected=proof.remaining.batch_selection(value, s, b),
                 proof=dict(verdict=proof.hard.PASS)) for s in range(16) for b in range(4)]


def tiny_plan():
    return dict(symbolic_inputs=dict(clock=1, state=2, unused=1), groups=[
        dict(id='p0', obligations=[['ff_d', 0], ['ff_d', 1]]),
        dict(id='p1', obligations=[['gate_next', 0]])])


def selected():
    return [dict(parent='p0', bit=1, original=['ff_d', 1]), dict(parent='p1', bit=0, original=['gate_next', 0])]


def test_exact_archives_and_published_dependency_closure():
    lock = proof.load_lock()
    assert len(lock['dependencies']) == 28 and len(lock['archives']) == 6
    assert lock['source_run'] == 37105127162 and lock['refined_miter']['bytes'] == 143063944
    assert lock['symbolic_inputs'] == 10828 and lock['batch_sizes'] == [16,16,14,4]


@pytest.mark.parametrize('field', ['runtime','refined_miter','source_commit','source_run','shards','max_parallel',
    'batch_sizes','batch_seconds','symbolic_inputs','original_bits','remaining_bits','dependencies','archives'])
def test_any_changed_source_or_scope_lock_fails_before_native(tmp_path, monkeypatch, field):
    lock = json.loads((ROOT/proof.LOCK).read_text()); lock[field] = None
    path = tmp_path/proof.LOCK; path.parent.mkdir(parents=True); path.write_text(json.dumps(lock))
    monkeypatch.setattr(proof, 'ROOT', tmp_path)
    with pytest.raises(ValueError, match='input lock'): proof.load_lock()


@pytest.mark.parametrize('original', [None, 'a'*40])
@pytest.mark.parametrize('raises', [True, False])
def test_historical_evidence_context_always_restores_current_source(monkeypatch, original, raises):
    if original is None: monkeypatch.delenv('GITHUB_SHA', raising=False)
    else: monkeypatch.setenv('GITHUB_SHA', original)
    try:
        with proof.historical_capture_context():
            assert os.environ['GITHUB_SHA'] == proof.SOURCE
            if raises: raise ValueError('old evidence failure')
    except ValueError: pass
    assert os.environ.get('GITHUB_SHA') == original


def test_group_query_keeps_all_inputs_and_each_exact_equation_once():
    text = proof.grouped_wrapper(tiny_plan(), selected())
    assert 'input wire [0:0] in_unused' in text and 'input wire [0:0] in_clock' in text
    assert '(* keep = 1 *) wire [1:0] selected_diff;' in text
    assert text.count('assign selected_diff[') == 2 and 'assign bad=|selected_diff;' in text
    assert 'gold_p0[1]^gate_p0[1]' in text and 'gold_p1[0]^gate_p1[0]' in text
    assert text.count('output wire') == 1 and 'assume' not in text and 'cutpoint' not in text


@pytest.mark.parametrize('fault', ['empty','duplicate','oversized','parent','offset','name'])
def test_bad_group_observations_rejected(fault):
    plan = tiny_plan(); chosen = selected()
    if fault == 'empty': chosen = []
    if fault == 'duplicate': chosen.append(copy.deepcopy(chosen[0]))
    if fault == 'oversized': chosen = [dict(parent='p0', bit=0, original=['x', i]) for i in range(17)]
    if fault == 'parent': chosen[0]['parent'] = 'missing'
    if fault == 'offset': chosen[0]['bit'] = 2
    if fault == 'name': plan['symbolic_inputs']['bad; quit'] = 1
    with pytest.raises((ValueError, KeyError)): proof.grouped_wrapper(plan, chosen)


def test_binary_witness_attribution_preserves_verilog_bit_order():
    witness = dict(signal=[dict(name='selected_diff', wave='=4', data=['10',''])])
    assert proof.differing_originals(witness, selected()) == [['gate_next',0]]
    witness['signal'][0]['data'][0] = '11'
    assert proof.differing_originals(witness, selected()) == [['ff_d',1],['gate_next',0]]
    assert proof.differing_originals(dict(signal=[dict(name='selected_diff',wave='14')]), selected()[:1]) == [['ff_d',1]]


@pytest.mark.parametrize('fault', ['missing','duplicate','undefined','short','long','zero','missing_data'])
def test_bad_or_empty_counterexample_attribution_is_never_accepted(fault):
    witness = dict(signal=[dict(name='selected_diff', wave='=4', data=['10',''])])
    if fault == 'missing': witness['signal'] = []
    if fault == 'duplicate': witness['signal'] *= 2
    if fault == 'undefined': witness['signal'][0]['data'][0] = '1x'
    if fault == 'short': witness['signal'][0]['data'][0] = '1'
    if fault == 'long': witness['signal'][0]['data'][0] = '101'
    if fault == 'zero': witness['signal'][0]['data'][0] = '00'
    if fault == 'missing_data': witness['signal'][0].pop('data')
    with pytest.raises(ValueError): proof.differing_originals(witness, selected())


def test_cex_vector_replay_reads_unlowered_source_and_all_assignments():
    text = proof.vector_script(Path('/original143.il'), Path('/observe.v'), dict(in_clock=1,in_state=2,in_unused=0),
        dict(in_clock=1,in_state=2,in_unused=1), Path('/out'))
    assert 'read_rtlil "/original143.il"' in text and '-show selected_diff' in text
    assert "-set in_clock 1'h1 -set in_state 2'h2 -set in_unused 1'h0" in text
    assert 'aigmap' not in text and 'assume' not in text


def test_exact800_or_successes_complete_only_binary_boundary_not_product():
    value = catalog(); result = proof.merge(value, rows(value))
    assert result['new_800_proved'] == 800 and result['total_unique_proved'] == 34321
    assert result['state_bijection_proved'] is True and result['candidate_adopted'] is False
    assert result['full_soc_functional_accepted'] is result['timing_accepted'] is result['manufacturing_approval'] is False
    assert result['unresolved_four_state_boot_failure'] is True
    assert result['sat_partial_evidence_unchanged_and_not_added_again'] is True
    assert result['grouped_query_differs_from_individual_query'] is True


@pytest.mark.parametrize('fault', ['missing','duplicate_batch','wrong_shard','wrong_selection','duplicate_selection','unknown',
    'prior_overlap','prior_missing','wrong_hard','untested_overlap','untested_missing'])
def test_merge_rejects_any_coverage_gap_duplicate_or_foreign_identity(fault):
    value = catalog(); actual = rows(value)
    if fault == 'missing': actual.pop()
    if fault == 'duplicate_batch': actual[-1] = copy.deepcopy(actual[0])
    if fault == 'wrong_shard': actual[0]['shard'] = 16
    if fault == 'wrong_selection': actual[0]['selected'] = actual[1]['selected']
    if fault == 'duplicate_selection': actual[0]['selected'].append(copy.deepcopy(actual[0]['selected'][0]))
    if fault == 'unknown': actual[0]['proof']['verdict'] = 'CI_SUCCESS'
    if fault == 'prior_overlap': value['preserved_proved'][0] = value['untested'][0]['original']
    if fault == 'prior_missing': value['preserved_proved'].pop()
    if fault == 'wrong_hard': value['hard'][0]['original'] = ['foreign',0]
    if fault == 'untested_overlap': value['untested'][0]['original'] = value['untested'][1]['original']
    if fault == 'untested_missing': value['untested'].pop()
    with pytest.raises(ValueError): proof.merge(value, actual)


@pytest.mark.parametrize('outcome', [proof.hard.CEX,proof.hard.OPEN,'TIMEOUT_UNPROVED'])
def test_any_nonproof_keeps_entire_group_open(outcome):
    value = catalog(); actual = rows(value); actual[0]['proof']['verdict'] = outcome
    if outcome == proof.hard.CEX:
        actual[0]['proof']['attribution'] = dict(differing_original_bits=[actual[0]['selected'][3]['original']])
    result = proof.merge(value, actual)
    assert result['new_800_proved'] == 784 and result['state_bijection_proved'] is False
    assert len(result['unproved_original_bits']) == 16 and result['total_unique_proved'] == 34305
    if outcome == proof.hard.CEX: assert result['actual_counterexample_original_bits'] == [actual[0]['selected'][3]['original']]


@pytest.mark.parametrize('bad', [[],[['foreign',0]],[['new',0],['new',0]]])
def test_cex_must_identify_nonempty_subset_of_the_actual_batch(bad):
    value = catalog(); actual = rows(value); actual[0]['proof'] = dict(verdict=proof.hard.CEX,
        attribution=dict(differing_original_bits=bad))
    with pytest.raises(ValueError): proof.merge(value, actual)


def test_preparation_failure_is_preserved_before_any_native_execution(tmp_path, monkeypatch):
    monkeypatch.setenv('GITHUB_ACTIONS','true')
    def fail(): raise ValueError('original source mismatch')
    monkeypatch.setattr(proof,'load_lock',fail)
    with pytest.raises(ValueError): proof.prepare(tmp_path/'output',tmp_path/'work')
    row = json.loads((tmp_path/'output/result.json').read_text())
    assert row['status'] == 'PREPARATION_FAILED_PRESERVED' and 'source mismatch' in row['error']


def test_incomplete_final_artifacts_are_preserved_without_success(tmp_path, monkeypatch):
    value = catalog(); monkeypatch.setattr(proof,'verify_prepared',lambda _: ({},value,{},{}))
    with pytest.raises(ValueError): proof.aggregate(tmp_path, [], [], tmp_path/'final.json')
    row = json.loads((tmp_path/'final.json').read_text())
    assert row['state_bijection_proved'] is False and row['candidate_adopted'] is False
    assert row['status'] == 'INCOMPLETE_GROUPED_CAPTURE_OR_FAILED_REPLAY'


def test_native_full_graph_entrypoints_reject_local_execution(tmp_path, monkeypatch):
    monkeypatch.delenv('GITHUB_ACTIONS',raising=False)
    with pytest.raises(ValueError): proof.prepare(tmp_path/'out',tmp_path/'work')
    with pytest.raises(ValueError): proof.prepare_shard(tmp_path,0,tmp_path/'out',tmp_path/'work')
    with pytest.raises(ValueError): proof.run_batch(tmp_path,tmp_path,0,tmp_path/'out')


def test_workflow_has_exact64_batch_captures_and_bounded_concurrency():
    text = (ROOT/'.github/workflows/timing-alu-remaining-abc.yml').read_text()
    assert 'max-parallel: 4' in text and 'shard: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]' in text
    assert text.count("if: always() && steps.prepare_shard.outcome == 'success'") == 4
    assert text.count('include-hidden-files: true') == 7 and 'fetch-depth: 0' in text
    assert 'scripts/prove_alu_remaining_abc.py aggregate' in text


@pytest.mark.parametrize('mutation', [False, True])
def test_batch_rechecks_all_prepared_inputs_after_native_solve(tmp_path, monkeypatch, mutation):
    monkeypatch.setenv('GITHUB_ACTIONS','true')
    prepared=dict(methods={}, original='stable'); locked=dict(runtime={},refined_miter={})
    shard=dict(shard=0,native_paths=dict(work=str(tmp_path/'work')),selections={'0':selected()},symbolic_inputs={})
    events=[]
    def verify(_):
        events.append('complete-inputs')
        value=copy.deepcopy(prepared)
        if mutation and 'native-solve' in events: value['original']='changed old proof or current method'
        return value,{}, {},locked
    def solve(*args, **kwargs): events.append('native-solve'); return dict(verdict=proof.hard.PASS)
    monkeypatch.setattr(proof,'verify_prepared',verify)
    monkeypatch.setattr(proof,'verify_shard',lambda *args:shard)
    monkeypatch.setattr(proof,'solve',solve)
    monkeypatch.setattr(proof.state.common,'verify_file',lambda *args:None)
    monkeypatch.setattr(proof,'pin',lambda *args:dict(bytes=0,sha256='a'*64))
    output=tmp_path/'result'
    if mutation:
        with pytest.raises(ValueError,match='Complete prepared inputs changed'):
            proof.run_batch(tmp_path,tmp_path,0,output)
    else: proof.run_batch(tmp_path,tmp_path,0,output)
    row=json.loads((output/'result.json').read_text())
    assert events==['complete-inputs','native-solve','complete-inputs']
    assert row['status']==('GROUPED_BATCH_FAILED_OR_INCOMPLETE' if mutation else 'GROUPED_BATCH_NATIVE_RESULT_CAPTURED')
    assert row.get('complete_inputs_rechecked',False) is not mutation
