# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bounded observations are measurements, not a complete mapped-state proof."""
import copy
from pathlib import Path
import shutil
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts'))
import benchmark_alu_state_bits as bit  # noqa: E402
import test_alu_state_refinement as fixtures  # noqa: E402


def fixture():
    original, timeouts, refined = fixtures.fixture()
    remaining = [dict(id=f'{bit.part.PREFIX}{i:04d}', parent=g['id'], bit=0, original=g['obligations'][0])
                 for i, g in enumerate(refined['groups'])]
    plan = bit.observation_plan(refined, remaining)
    return original, timeouts, refined, remaining, plan


def test_only_observations_are_changed_and_all_symbolic_inputs_remain():
    _, _, refined, selected, plan = fixture()
    assert plan['symbolic_inputs'] == refined['symbolic_inputs']
    text = bit.wrapper(refined, selected)
    assert text.count('nssoc_preserved_miter preserved(') == 1
    assert text.count('input wire') == len(refined['symbolic_inputs'])
    for name in refined['symbolic_inputs']:
        assert f'.in_{name}(in_{name})' in text
    for row in selected:
        for prefix in ('gold', 'gate'):
            assert f'assign {prefix}_{row["id"]} = observed_{prefix}_{row["parent"]}[0];' in text
    assert not any(x in text for x in ('assume', 'force', 'cutpoint', 'setundef'))


@pytest.mark.parametrize('fault', ['too_few', 'too_many', 'duplicate', 'parent', 'bit', 'negative', 'bool', 'name'])
def test_invalid_observation_cannot_enter_miter(fault):
    _, _, refined, selected, _ = fixture()
    if fault == 'too_few': selected = selected[:3]
    if fault == 'too_many': selected *= 3
    if fault == 'duplicate': selected[1].update(parent=selected[0]['parent'], bit=selected[0]['bit'])
    if fault == 'parent': selected[0]['parent'] = 'unknown'
    if fault == 'bit': selected[0]['bit'] = 1
    if fault == 'negative': selected[0]['bit'] = -1
    if fault == 'bool': selected[0]['bit'] = False
    if fault == 'name': selected[0]['id'] = 'unknown'
    with pytest.raises(ValueError): bit.observation_plan(refined, selected)


def test_prior_coverage_counts_only_real_passes_and_keeps_every_bit():
    original, timeouts, refined, _, _ = fixture()
    old = fixtures.records(original, timeouts)
    new = fixtures.records(refined, [refined['groups'][0]['id']])
    coverage = bit.coverage(original, old, refined, new, timeouts)
    assert len(coverage['proved']) == 8 and len(coverage['remaining']) == 1
    assert coverage['original_bits'] == 9 and not coverage['aggregate']['state_bijection_proved']


@pytest.mark.parametrize('fault', ['cex', 'unknown', 'error', 'missing', 'duplicate'])
def test_prior_failure_and_coverage_cannot_be_discarded(fault):
    original, timeouts, refined, _, _ = fixture()
    rows = fixtures.records(refined, [refined['groups'][0]['id']])
    if fault == 'cex': rows[0]['groups'][0]['verdict'] = 'COUNTEREXAMPLE_PRESERVED'
    if fault == 'unknown': rows[0]['groups'][0]['verdict'] = 'UNKNOWN'
    if fault == 'error': rows[0]['groups'][0]['native_returncode'] = 1
    if fault == 'missing': rows[0]['groups'].pop()
    if fault == 'duplicate': rows[0]['groups'].append(copy.deepcopy(rows[0]['groups'][0]))
    with pytest.raises(ValueError): bit.coverage(original, fixtures.records(original, timeouts), refined, rows, timeouts)


def test_selection_exactly_covers_seven_categories_with_two_extra_data_samples():
    remaining = []
    for name in ['ff_clk', 'ff_d', 'ff_reset_b', 'gate_clk', 'gate_enable', 'gate_next', 'memory_inputs']:
        for i in range(12 if name == 'ff_d' else 3):
            remaining.append(dict(parent=bit.part.PREFIX+'0000', bit=len(remaining), original=[bit.state.PREFIX+name, i]))
    selected = bit.choose_representatives(remaining)
    assert len(selected) == 16
    for name in {r['original'][0] for r in remaining}:
        numbers = [r['original'][1] for r in selected if r['original'][0] == name]
        assert numbers == ([0, 4, 8, 11] if name.endswith('ff_d') else [0, 2])


def test_timing_instrumentation_does_not_change_frozen_native_traversal(tmp_path):
    _, _, _, _, plan = fixture()
    generated = bit.timed_script(tmp_path/'miter.il', plan, 0, tmp_path, 120)
    stripped = '\n'.join(line for line in generated.splitlines()
        if not line.startswith(('set benchmark_started', 'yosys log NSSOC_BIT_MILLISECONDS')))+'\n'
    assert stripped == bit.part.shard_script(tmp_path/'miter.il', plan, 0, tmp_path, 120)
    assert '-set ' not in generated and '-assumes' not in generated
    for timeout in [0, 121, True]:
        with pytest.raises(ValueError): bit.timed_script(tmp_path/'miter.il', plan, 0, tmp_path, timeout)


def native_log(plan, shard, timeout=False):
    lines = []
    for group in plan['groups']:
        if group['shard'] != shard: continue
        lines += [f'NSSOC_GROUP_BEGIN {group["id"]}', 'Final constraint equation: { } = { }',
                  'Solving problem with 345 variables and 678 clauses',
                  'Interrupted SAT solver: TIMEOUT!' if timeout else 'SAT proof finished - no model found: SUCCESS!',
                  f'NSSOC_GROUP_END {group["id"]} 0', f'NSSOC_BIT_MILLISECONDS {group["id"]} 123']
    return '\n'.join(lines+['NSSOC_ALL_ASSIGNED_GROUPS_VISITED', ''])


@pytest.mark.parametrize('timeout', [False, True])
def test_native_cost_and_timeout_are_parsed_without_acceptance(tmp_path, timeout):
    _, _, _, selected, plan = fixture()
    rows = [dict(shard=s, groups=bit.costs(native_log(plan, s, timeout), plan, s, tmp_path)) for s in range(4)]
    result = bit.benchmark_verdict(plan, selected, rows, 10, 30)
    assert result['selected_proved_bits'] == (0 if timeout else 8)
    assert result['selected_timeouts'] == (8 if timeout else 0)
    assert result['remaining_unproved_bits'] == (20 if timeout else 12)
    assert result['per_bit'][0]['elapsed_milliseconds'] == 123
    assert result['per_bit'][0]['sat_variables'] == 345
    assert not result['state_bijection_proved'] and not result['candidate_adopted']
    assert result['unresolved_four_state_boot_failure']


@pytest.mark.parametrize('fault', ['cost_missing', 'cost_duplicate', 'cnf_missing', 'cnf_duplicate', 'constraint'])
def test_native_metrics_and_verdict_cannot_be_fabricated_or_ambiguous(tmp_path, fault):
    _, _, _, _, plan = fixture(); text = native_log(plan, 0)
    if fault == 'cost_missing': text = '\n'.join(x for x in text.splitlines() if not x.startswith('NSSOC_BIT_MILLISECONDS'))
    if fault == 'cost_duplicate': text += f'NSSOC_BIT_MILLISECONDS {plan["groups"][0]["id"]} 123\n'
    if fault == 'cnf_missing': text = text.replace('Solving problem with', 'Not solving')
    if fault == 'cnf_duplicate': text = text.replace('Solving problem with 345 variables and 678 clauses',
        'Solving problem with 345 variables and 678 clauses\nSolving problem with 345 variables and 678 clauses')
    if fault == 'constraint': text = text.replace('Final constraint equation: { } = { }', 'Final constraint equation: x = 0')
    with pytest.raises(ValueError): bit.costs(text, plan, 0, tmp_path)


def test_sampling_cannot_become_full_proof():
    _, _, _, selected, plan = fixture()
    with pytest.raises(ValueError): bit.benchmark_verdict(plan, selected, fixtures.records(plan), 10, 18)


@pytest.mark.parametrize('fault', ['unknown', 'error', 'missing', 'duplicate'])
def test_sample_aggregation_fails_closed_on_incomplete_or_failed_native_records(fault):
    _, _, _, selected, plan = fixture(); rows = fixtures.records(plan)
    if fault == 'unknown': rows[0]['groups'][0]['verdict'] = 'UNKNOWN'
    if fault == 'error': rows[0]['groups'][0]['native_returncode'] = 1
    if fault == 'missing': rows[0]['groups'].pop()
    if fault == 'duplicate': rows[0]['groups'].append(copy.deepcopy(rows[0]['groups'][0]))
    with pytest.raises(ValueError): bit.benchmark_verdict(plan, selected, rows, 10, 30)


def refined_bundle(tmp_path, monkeypatch):
    """Exact mock receipt boundary; no historical outputs or network are needed."""
    common, prepared = fixtures.prepared_bundle(tmp_path, monkeypatch)
    bundle = tmp_path/'prior-refinement'; bundle.mkdir(); shutil.move(common, bundle/'common'); common = bundle/'common'
    _, refined, original, old_rows, old_lock = bit.ref.verify_common(common)
    lock = dict(source_commit=prepared['github_source_commit'], common_result=bit.state.archived.pin(common/'result.json'),
        common_miter=prepared['common_miter'], plan=prepared['plan'], shard_results={})
    rows = []; timeouts = [g['id'] for g in refined['groups']]
    for shard in range(4):
        directory = bundle/('shard'+str(shard)); directory.mkdir()
        text = fixtures.fixture_log(refined, shard, timeouts); (directory/'partitions.log').write_text(text)
        row = {k: prepared[k] for k in ('github_source_commit', 'common_miter', 'plan', 'methods', 'original_common_miter', 'original_lock')}
        row.update(shard=shard, status='ALL_REFINED_GROUPS_VISITED', execution=dict(returncode=0), complete_inputs_rechecked=True,
                   groups=bit.part.parse_shard(text, refined, shard, directory), outputs=bit.ref.inventory(directory))
        bit.state.common.save(directory/'result.json', row); lock['shard_results'][str(shard)] = bit.state.archived.pin(directory/'result.json')
        rows.append(row)
    previous = bit.coverage(original, old_rows, refined, rows, old_lock['timed_out_groups'])
    # Selection policy has its own seven-category test; use all eight tiny bits at this mocked boundary.
    selected = [dict(r, id=f'{bit.part.PREFIX}{i:04d}') for i, r in enumerate(previous['remaining'])]
    chosen = copy.deepcopy(selected)
    monkeypatch.setattr(bit, 'choose_representatives', lambda remaining: copy.deepcopy(chosen))
    aggregate = copy.deepcopy(previous['aggregate']); aggregate.update({k: prepared[k] for k in
        ('github_source_commit', 'common_miter', 'plan', 'original_common_miter', 'original_lock')})
    aggregate['shard_results'] = lock['shard_results']
    path = bundle/'verdict/alu-refinement-verdict.json'; path.parent.mkdir(); bit.state.common.save(path, aggregate)
    lock.update(aggregate_result=bit.state.archived.pin(path), selected=selected, prior_proved_bits=1,
        remaining_bits=8, original_output_bits=9, symbolic_input_bits=6, refined_proved_groups=0, refined_timeout_groups=8)
    return bundle, lock, prepared


def test_refinement_full_provenance_and_raw_verdicts_are_replayed(tmp_path, monkeypatch):
    bundle, lock, _ = refined_bundle(tmp_path, monkeypatch)
    _, plan, previous = bit.verify_refinement(bundle, lock)
    assert plan['symbolic_input_bits'] == 6 and len(previous['remaining']) == 8


@pytest.mark.parametrize('fault', ['source', 'runtime', 'method', 'inventory', 'extra_file', 'miter', 'wrapper',
                                  'raw_log', 'group_log', 'shard', 'verdict', 'selection', 'count', 'old_source'])
def test_refinement_rejects_changed_complete_input_evidence(tmp_path, monkeypatch, fault):
    bundle, lock, prepared = refined_bundle(tmp_path, monkeypatch); common = bundle/'common'
    if fault == 'source': prepared['github_source_commit'] = 'other'
    if fault == 'runtime': prepared['runtime']['sha256'] = '0'*64
    if fault == 'method': prepared['methods'].pop(next(iter(prepared['methods'])))
    if fault == 'inventory': prepared['outputs'].pop('common-miter.il')
    if fault == 'extra_file': (common/'extra').write_text('extra')
    if fault == 'miter': (common/'common-miter.il').write_text('changed')
    if fault == 'wrapper': (common/'observations.v').write_text('changed')
    if fault == 'raw_log': (bundle/'shard0/partitions.log').write_text('changed')
    if fault == 'group_log': (bundle/f'shard0/{bit.part.PREFIX}0000.log').write_text('changed')
    if fault == 'shard': (bundle/'shard0/result.json').write_text('{}')
    if fault == 'verdict': (bundle/'verdict/alu-refinement-verdict.json').write_text('{}')
    if fault == 'selection': lock['selected'][0]['original'][1] += 1
    if fault == 'count': lock['prior_proved_bits'] += 1
    if fault == 'old_source': (common/'prior/common/methods/scripts/prove_alu_state_partitions.py').write_text('changed')
    if fault in {'source', 'runtime', 'method', 'inventory'}:
        bit.state.common.save(common/'result.json', prepared); lock['common_result'] = bit.state.archived.pin(common/'result.json')
    with pytest.raises(ValueError): bit.verify_refinement(bundle, lock)


def test_full_work_is_cloud_only_and_all_old_sources_are_frozen(tmp_path, monkeypatch):
    monkeypatch.delenv('GITHUB_ACTIONS', raising=False)
    with pytest.raises(ValueError): bit.run(tmp_path/'out', tmp_path/'work')
    assert not (tmp_path/'out').exists()
    lock = bit.load_lock()
    assert len(lock['selected']) == 16 and lock['prior_proved_bits'] == 33505
    assert len({tuple(r['original']) for r in lock['selected']}) == 16
    for name, pin in bit.PINS.items(): assert bit.state.common.sha(bit.ROOT/name) == pin


def test_workflow_is_a_bounded_measurement_not_full_retry():
    text = (bit.ROOT/bit.OWN[2]).read_text()
    assert 'timeout-minutes: 75' in text and 'cancel-in-progress: false' in text
    assert 'actions: read' in text and 'contents: write' not in text
    assert 'matrix:' not in text and 'if: always()' in text
    assert 'path: alu-bit-benchmark/' in text and 'path: ${{ runner.temp }}' not in text
