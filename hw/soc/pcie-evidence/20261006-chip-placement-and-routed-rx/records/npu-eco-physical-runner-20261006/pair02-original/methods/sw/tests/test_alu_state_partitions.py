# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Complete independent output obligations, with no assumed internal cutpoints."""
import copy
import json
from pathlib import Path
import shutil
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts'))
import prove_alu_state_partitions as part  # noqa: E402


def fixture():
    module, _ = part.state.lift(part.state.fixture(), ['ff0', 'ff1'])
    return module, part.make_plan(module, module, 2)


def records(plan):
    return [dict(shard=i, groups=[dict(id=g['id'], shard=i, bits=len(g['obligations']),
                 verdict='PROVED_ALL_BINARY_BOUNDARY_EQUATIONS', native_returncode=0)
                 for g in plan['groups'] if g['shard'] == i]) for i in range(part.SHARDS)]


def test_complete_unique_obligations_and_aliases_preserve_original_graph():
    module, plan = fixture(); source = copy.deepcopy(module)
    wrapped = part.alias_outputs(module, plan)
    assert module == source and wrapped['cells'] == source['cells'] and wrapped['netnames'] == source['netnames']
    assert plan['total_output_bits'] == 9 and plan['symbolic_input_bits'] == 6
    assert sum(len(g['obligations']) for g in plan['groups']) == 9
    for name, port in module['ports'].items(): assert wrapped['ports'][name] == port
    for g in plan['groups']:
        assert wrapped['ports'][g['id']]['bits'] == [module['ports'][name]['bits'][bit] for name, bit in g['obligations']]


@pytest.mark.parametrize('fault', ['omit_bit', 'duplicate_bit', 'extra_bit', 'omit_group', 'duplicate_group',
    'wrong_shard', 'wrong_input_count', 'wrong_total_count', 'empty_group'])
def test_plan_cannot_hide_duplicate_or_add_obligations(fault):
    _, plan = fixture()
    if fault == 'omit_bit': plan['groups'][0]['obligations'].pop()
    if fault == 'duplicate_bit': plan['groups'][0]['obligations'][1] = plan['groups'][0]['obligations'][0]
    if fault == 'extra_bit': plan['groups'][-1]['obligations'].append(['unknown', 0])
    if fault == 'omit_group': plan['groups'].pop()
    if fault == 'duplicate_group': plan['groups'].append(plan['groups'][0])
    if fault == 'wrong_shard': plan['groups'][0]['shard'] = 1
    if fault == 'wrong_input_count': plan['symbolic_input_bits'] -= 1
    if fault == 'wrong_total_count': plan['total_output_bits'] -= 1
    if fault == 'empty_group': plan['groups'][0]['obligations'] = []
    with pytest.raises(ValueError): part.validate_plan(plan)


def test_source_port_width_direction_and_reserved_namespace_guard():
    module, _ = fixture(); other = copy.deepcopy(module)
    other['ports']['data']['bits'].pop()
    with pytest.raises(ValueError): part.make_plan(module, other)
    other = copy.deepcopy(module); other['ports'][part.PREFIX+'bad'] = dict(direction='output', bits=[1])
    with pytest.raises(ValueError): part.make_plan(other, other)


def test_every_group_must_pass_in_addition_to_complete_coverage():
    _, plan = fixture(); good = records(plan)
    assert part.aggregate(plan, good)['state_bijection_proved'] is True
    for verdict in ['TIMEOUT_UNPROVED', 'COUNTEREXAMPLE_PRESERVED', 'UNKNOWN']:
        bad = copy.deepcopy(good); bad[0]['groups'][0]['verdict'] = verdict
        assert part.aggregate(plan, bad)['state_bijection_proved'] is False


@pytest.mark.parametrize('fault', ['omit_shard', 'duplicate_shard', 'omit_group', 'duplicate_group', 'wrong_bits', 'wrong_owner'])
def test_aggregate_rejects_incomplete_or_duplicate_native_receipts(fault):
    _, plan = fixture(); rows = records(plan)
    if fault == 'omit_shard': rows.pop()
    if fault == 'duplicate_shard': rows[1] = rows[0]
    if fault == 'omit_group': rows[0]['groups'].pop()
    if fault == 'duplicate_group': rows[0]['groups'].append(rows[0]['groups'][0])
    if fault == 'wrong_bits': rows[0]['groups'][0]['bits'] += 1
    if fault == 'wrong_owner': rows[0]['groups'][0]['shard'] = 1
    with pytest.raises(ValueError): part.aggregate(plan, rows)


def native_log(plan, shard, verdict='pass'):
    body = []
    for g in plan['groups']:
        if g['shard'] != shard: continue
        result = {'pass': 'SAT proof finished - no model found: SUCCESS!',
                  'fail': 'SAT proof finished - model found: FAIL!',
                  'timeout': 'Interrupted SAT solver: TIMEOUT!'}[verdict]
        body.append(f'NSSOC_GROUP_BEGIN {g["id"]}\nFinal constraint equation: {{ }} = {{ }}\n{result}\nNSSOC_GROUP_END {g["id"]} 0')
    return '\n'.join(body)+'\nNSSOC_ALL_ASSIGNED_GROUPS_VISITED\n'


def test_native_success_parser_and_read_only_aggregate_reparse(tmp_path):
    _, plan = fixture(); text = native_log(plan, 0)
    rows = part.parse_shard(text, plan, 0, tmp_path)
    assert all(r['verdict'] == 'PROVED_ALL_BINARY_BOUNDARY_EQUATIONS' for r in rows)
    assert part.parse_shard(text, plan, 0, tmp_path, write_logs=False) == rows
    (tmp_path/(rows[0]['id']+'.log')).write_text('changed')
    with pytest.raises(ValueError): part.parse_shard(text, plan, 0, tmp_path, write_logs=False)


@pytest.mark.parametrize('fault', ['no_final', 'no_group', 'duplicate', 'constraint', 'conflicting', 'tool_error', 'no_verdict'])
def test_native_incomplete_or_constrained_proof_never_passes(tmp_path, fault):
    _, plan = fixture(); text = native_log(plan, 0)
    if fault == 'no_final': text = text.replace('NSSOC_ALL_ASSIGNED_GROUPS_VISITED', '')
    if fault == 'no_group': text = text[text.index('NSSOC_GROUP_BEGIN', 1):]
    if fault == 'duplicate': text = text.replace('NSSOC_ALL_ASSIGNED_GROUPS_VISITED', text)
    if fault == 'constraint': text = text.replace('Final constraint equation: { } = { }', 'Final constraint equation: in_state = 0')
    if fault == 'conflicting': text = text.replace('SUCCESS!', 'SUCCESS!\nSAT proof finished - model found: FAIL!')
    if fault == 'tool_error': text = text.replace(' 0\n', ' 1\n')
    if fault == 'no_verdict': text = text.replace('SAT proof finished - no model found: SUCCESS!', '')
    with pytest.raises(ValueError): part.parse_shard(text, plan, 0, tmp_path)


def test_timeout_and_real_counterexample_do_not_gain_acceptance(tmp_path):
    _, plan = fixture()
    rows = part.parse_shard(native_log(plan, 0, 'timeout'), plan, 0, tmp_path)
    assert all(r['verdict'] == 'TIMEOUT_UNPROVED' for r in rows)
    with pytest.raises(ValueError): part.parse_shard(native_log(plan, 0, 'fail'), plan, 0, tmp_path)
    for g in plan['groups']:
        if g['shard'] == 0:
            (tmp_path/(g['id']+'.json')).write_text('{}'); (tmp_path/(g['id']+'.vcd')).write_text('native fixture')
    assert all(r['verdict'] == 'COUNTEREXAMPLE_PRESERVED' for r in part.parse_shard(native_log(plan, 0, 'fail'), plan, 0, tmp_path))


def test_single_common_graph_and_native_pruning_never_cut_internal_inputs(tmp_path):
    _, plan = fixture(); text = part.shard_script(tmp_path/'common.il', plan, 0, tmp_path)
    assert text.count('read_rtlil') == 1 and text.count('design -save full_miter') == 1
    assert text.count('design -load full_miter') == 2 and 'delete -output o:*' in text
    assert 'opt_clean -purge' in text and 'select -assert-count 4 i:*' in text
    assert 'sat -prove cmp_' in text and ' -set ' not in text and '-assume' not in text
    assert 'setundef' not in text and 'cutpoint' not in text and 'blackbox' not in text and 'delete -input' not in text
    assert 'NSSOC_GROUP_BEGIN' in text and 'yosys log NSSOC_GROUP_END' in text
    assert not any(line.startswith('puts ') for line in text.splitlines())
    for group in plan['groups']:
        if group['shard'] == 0:
            for prefix in ('cmp_', 'gold_', 'gate_'):
                assert 'select -assert-count 1 o:'+prefix+group['id'] in text


def test_timeout_download_is_permanent_public_and_exactly_pinned(tmp_path, monkeypatch):
    received = []
    monkeypatch.setattr(part.state.common, 'download', lambda entry, output: received.append((entry, output)))
    part.timeout_archive(tmp_path/'timeout.zip')
    assert received == [(dict(part.TIMEOUT_ZIP, url=part.TIMEOUT_URL), tmp_path/'timeout.zip')]
    assert '/releases/download/' in part.TIMEOUT_URL and '/actions/' not in part.TIMEOUT_URL


def test_proposal_integer_keys_reproduce_exact_frozen_json_bytes(tmp_path):
    proposal = {'pairs': [['original', 'candidate']], 'candidate_old_position_for_new': {9982: 9983, 9983: 9988, 9988: 9982}}
    captured = tmp_path/'captured.json'; part.state.common.save(captured, proposal)
    assert json.loads(captured.read_text()) != proposal
    pin = part.state.archived.pin(captured)
    assert part.verify_proposal_serialization(proposal, tmp_path/'rebuilt.json', pin) == pin
    wrong = copy.deepcopy(proposal); wrong['candidate_old_position_for_new'][9982] = 9988
    with pytest.raises(ValueError): part.verify_proposal_serialization(wrong, tmp_path/'wrong.json', pin)


def test_common_interface_keeps_exact_all_symbolic_inputs():
    _, plan = fixture()
    ports = {'in_'+n: dict(direction='input', bits=list(range(w))) for n, w in plan['symbolic_inputs'].items()}
    for g in plan['groups']:
        for prefix, width in [('cmp_', 1), ('gold_', len(g['obligations'])), ('gate_', len(g['obligations']))]:
            ports[prefix+g['id']] = dict(direction='output', bits=list(range(width)))
    module = dict(ports=ports, cells={}); assert part.validate_interface(module, plan)['symbolic_input_bits'] == 6
    module['ports']['in_data']['bits'].pop()
    with pytest.raises(ValueError): part.validate_interface(module, plan)


def test_full_proofs_are_cloud_only(tmp_path, monkeypatch):
    monkeypatch.delenv('GITHUB_ACTIONS', raising=False)
    with pytest.raises(ValueError): part.prepare(tmp_path/'out', tmp_path/'work')
    with pytest.raises(ValueError): part.run_shard(tmp_path/'bundle', 0, tmp_path/'out', tmp_path/'work')
    assert not (tmp_path/'out').exists()


def prepared_bundle(tmp_path, monkeypatch):
    root = tmp_path/'checkout'; bundle = tmp_path/'common'; bundle.mkdir()
    methods = {}
    for name in (*part.PINS, *part.OWN):
        source = part.ROOT/name
        for dest in (root/name, bundle/'methods'/name):
            dest.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(source, dest)
        methods[name] = part.state.archived.pin(source)
    monkeypatch.setattr(part, 'ROOT', root); monkeypatch.setenv('GITHUB_SHA', 'fixture-source')
    module = dict(ports={'data': dict(direction='input', bits=[1]*10828),
                         'answer': dict(direction='output', bits=[1]*34321)})
    plan = part.make_plan(module, module)
    (bundle/'plan.json').write_text(json.dumps(plan)); (bundle/'common-miter.il').write_text('fixture common graph')
    row = dict(status='COMMON_MITER_PREPARED_NOT_PROVED', complete_inputs_rechecked=True,
        github_source_commit='fixture-source', methods=methods,
        runtime=json.loads((root/part.state.archived.MANIFEST).read_text())['runtime'],
        common_miter=part.state.archived.pin(bundle/'common-miter.il'), plan=part.state.archived.pin(bundle/'plan.json'),
        outputs={str(p.relative_to(bundle)): part.state.archived.pin(p) for p in bundle.rglob('*') if p.is_file()})
    (bundle/'result.json').write_text(json.dumps(row))
    return bundle, row


def test_common_receipt_has_complete_source_output_runtime_closure(tmp_path, monkeypatch):
    bundle, _ = prepared_bundle(tmp_path, monkeypatch)
    row, plan = part.verify_common(bundle)
    assert row['complete_inputs_rechecked'] and plan['total_output_bits'] == 34321


@pytest.mark.parametrize('fault', ['missing_method', 'extra_method', 'missing_output', 'extra_file',
                                  'changed_runtime', 'changed_source', 'symlink'])
def test_incomplete_common_receipt_or_changed_runtime_is_rejected(tmp_path, monkeypatch, fault):
    bundle, row = prepared_bundle(tmp_path, monkeypatch)
    if fault == 'missing_method': row['methods'].pop(next(iter(row['methods'])))
    if fault == 'extra_method': row['methods']['unreviewed.py'] = dict(bytes=1, sha256='0'*64)
    if fault == 'missing_output': row['outputs'].pop('common-miter.il')
    if fault == 'extra_file': (bundle/'unexpected.log').write_text('extra')
    if fault == 'changed_runtime': row['runtime']['sha256'] = '0'*64
    if fault == 'changed_source': row['github_source_commit'] = 'other-source'
    if fault == 'symlink': (bundle/'linked.log').symlink_to(bundle/'plan.json')
    (bundle/'result.json').write_text(json.dumps(row))
    with pytest.raises(ValueError): part.verify_common(bundle)
