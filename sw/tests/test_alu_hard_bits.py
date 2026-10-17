# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Source identity, original input bijection, native verdict and complete coverage guards."""
import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
import prove_alu_hard_bits as proof  # noqa: E402


def test_exact_frozen_method_dependency_closure():
    locked = proof.load_lock()
    assert len(locked['dependencies']) == 24 and locked['symbolic_input_bits'] == 10828
    assert locked['refined_miter']['bytes'] == 143063944


@pytest.mark.parametrize('fault', ['commit', 'runtime', 'graph', 'inputs', 'bits', 'seconds', 'memory', 'hard', 'dependency', 'abc'])
def test_changed_original_contract_rejected(tmp_path, monkeypatch, fault):
    locked = proof.load_lock()
    if fault == 'commit': locked['frozen_commit'] = '0'*40
    if fault == 'runtime': locked['runtime']['sha256'] = '0'*64
    if fault == 'graph': locked['refined_miter']['sha256'] = '0'*64
    if fault == 'inputs': locked['symbolic_input_bits'] -= 1
    if fault == 'bits': locked['original_bits'] -= 1
    if fault == 'seconds': locked['solver_seconds'] = 1800
    if fault == 'memory': locked['memory_bytes'] += 1
    if fault == 'hard': locked['hard_original_bits'][0] = locked['hard_original_bits'][1]
    if fault == 'dependency': locked['dependencies'].pop(next(iter(locked['dependencies'])))
    if fault == 'abc': locked['native_abc']['sha256'] = '0'*64
    p = tmp_path/proof.LOCK; p.parent.mkdir(parents=True); p.write_text(json.dumps(locked))
    original_verify = proof.state.common.verify_file
    original_git = proof.subprocess.check_output
    def verify(path, expected):
        return original_verify(ROOT/path.relative_to(tmp_path) if path.is_relative_to(tmp_path) else path, expected)
    def git(command, **kwargs):
        if kwargs.get('cwd') == tmp_path: kwargs['cwd'] = ROOT
        return original_git(command, **kwargs)
    monkeypatch.setattr(proof.state.common, 'verify_file', verify)
    monkeypatch.setattr(proof.subprocess, 'check_output', git)
    monkeypatch.setattr(proof, 'ROOT', tmp_path)
    with pytest.raises(ValueError): proof.load_lock()


def expected_map():
    return dict(lhs=2, clock=1), 'input 0 0 lhs\ninput 1 1 lhs\ninput 2 0 clock\noutput 0 0 bad\n'


def test_complete_map_includes_unused_and_clock_inputs():
    expected, text = expected_map(); rows = proof.parse_map(text, expected)
    assert rows == [(0, 'lhs', 0), (1, 'lhs', 1), (2, 'clock', 0)]
    assert proof.counterexample_values('101# DONE\n', rows, expected) == {'lhs': 1, 'clock': 1}


@pytest.mark.parametrize('fault', ['missing', 'duplicate', 'foreign', 'offset', 'order', 'latch', 'output', 'duplicate_output'])
def test_nonbijective_map_rejected(fault):
    expected, text = expected_map()
    if fault == 'missing': text = text.replace('input 2 0 clock\n', '')
    if fault == 'duplicate': text = text.replace('input 1 1 lhs', 'input 1 0 lhs')
    if fault == 'foreign': text = text.replace('clock', 'cutpoint')
    if fault == 'offset': text = text.replace('input 2 0 clock', 'input 2 1 clock')
    if fault == 'order': text = text.replace('input 1 1 lhs', 'input 3 1 lhs')
    if fault == 'latch': text += 'latch 0 0 state\n'
    if fault == 'output': text = text.replace('output 0 0 bad', 'output 1 0 bad')
    if fault == 'duplicate_output': text += 'output 0 0 bad\n'
    with pytest.raises(ValueError): proof.parse_map(text, expected)


@pytest.mark.parametrize('raw', ['10# DONE', '1010# DONE', '1x1# DONE', '101', '101# DONE\nextra', '1 0 1# DONE'])
def test_partial_or_minimized_counterexample_rejected(raw):
    expected, text = expected_map()
    with pytest.raises(ValueError): proof.counterexample_values(raw, proof.parse_map(text, expected), expected)


def aig():
    # AND3=(input0 & input1), preserved unused input2; no sequential/property extension.
    return b'aig 4 3 0 1 1\n8\n'+bytes([4, 2])+b'i0 lhs[0]\ni1 lhs[1]\ni2 clock\no0 bad\nc\nfixture\n'


def test_native_binary_aig_census():
    expected, text = expected_map()
    assert proof.validate_aiger(aig(), proof.parse_map(text, expected), expected)['and_nodes'] == 1


@pytest.mark.parametrize('fault', ['ascii', 'latch', 'constraint', 'inputs', 'output', 'forward', 'truncated', 'symbols', 'duplicate'])
def test_state_constraint_or_wrong_symbolic_boundary_rejected(fault):
    raw = aig(); expected, text = expected_map()
    if fault == 'ascii': raw = raw.replace(b'aig ', b'aag ', 1)
    if fault == 'latch': raw = raw.replace(b'4 3 0 1 1', b'4 2 1 1 1')
    if fault == 'constraint': raw = raw.replace(b'4 3 0 1 1', b'4 3 0 1 1 0 1')
    if fault == 'inputs': raw = raw.replace(b'4 3 0 1 1', b'4 2 0 1 2')
    if fault == 'output': raw = raw.replace(b'\n8\n', b'\n99\n')
    if fault == 'forward': raw = raw.replace(bytes([4, 2]), bytes([0, 0]))
    if fault == 'truncated': raw = raw[:16]
    if fault == 'symbols': raw = raw.replace(b'i2 clock', b'i2 cutpoint')
    if fault == 'duplicate': raw = raw.replace(b'\no0', b'\ni2 clock\no0')
    with pytest.raises((ValueError, UnicodeDecodeError)): proof.validate_aiger(raw, proof.parse_map(text, expected), expected)


def test_final_abc_verdict_allows_actual_resolved_internal_fallback():
    text = 'Networks are UNDECIDED after the new CEC engine. Time=0\nCalling the old CEC engine.\nNetworks are equivalent. Time=0\n'
    assert proof.abc_verdict(text, 0) == proof.PASS
    assert proof.abc_verdict('Networks are NOT EQUIVALENT. Time=0\n', 0) == proof.CEX
    assert proof.abc_verdict('Networks are UNDECIDED.\n', 0) == proof.OPEN
    assert proof.abc_verdict('Time limit reached\nNetworks are UNDECIDED.\n', 0) == 'TIMEOUT_UNPROVED'


@pytest.mark.parametrize('text,code', [('ABC read failed', 0), ('Networks are equivalent.\n', 1),
    ('Networks are equivalent.\nNetworks are NOT EQUIVALENT.\n', 0),
    ('Networks are equivalent.\nNetworks are equivalent.\n', 0),
    ('Networks are equivalent.\nNetworks are UNDECIDED.\n', 0),
    ('Networks are equivalent.\nError: read failed', 0),
    ('Assertion i<size failed\nNetworks are equivalent.\n', -6)])
def test_exit_zero_or_partial_native_output_never_implies_proof(text, code):
    with pytest.raises(ValueError): proof.abc_verdict(text, code)


def test_solver_uses_plain_complete_cex_and_only_native_budget():
    command = proof.abc_command(Path('/runtime'), Path('/a/miter.aig'), Path('/a/cex'), 120)
    assert command[-1] == 'read_aiger /a/miter.aig; &get -n; &cec -m -T 120 -v; write_cex /a/cex'
    with pytest.raises(ValueError): proof.abc_command(Path('/r'), Path('/a; quit'), Path('/c'), 120)
    with pytest.raises(ValueError): proof.abc_command(Path('/r'), Path('/a'), Path('/c'), 121)


def test_replay_uses_original_graph_all_assignments_and_no_lowering():
    expected = dict(in_clock=1, in_state=3)
    script = proof.replay_script(Path('/original143.il'), Path('/observe.v'), dict(in_clock=1, in_state=5), expected, Path('/out'))
    assert 'read_rtlil "/original143.il"' in script
    assert '-set in_clock 1\'h1 -set in_state 3\'h5' in script
    assert 'aigmap' not in script and 'assume' not in script and 'sat -prove bad 0' in script
    with pytest.raises(ValueError): proof.replay_script(None, Path('/x'), dict(in_clock=1), expected, Path('/out'), tiny=True)


def rows():
    return [dict(index=i, original=dict(original=list(x)), proof=dict(verdict=proof.PASS)) for i, x in enumerate(proof.HARD)]


def test_four_proofs_alone_never_adopt_or_hide800_pending():
    result = proof.merge(rows())
    assert result['new_proved'] == 4 and result['known_proved_without_pending800'] == 33521
    assert result['remaining_without_pending800'] == 800 and result['state_bijection_proved'] is False
    assert result['pending800_results_not_merged'] is True and result['unresolved_four_state_boot_failure'] is True


@pytest.mark.parametrize('fault', ['missing', 'duplicate', 'foreign', 'unknown'])
def test_complete_merge_guards(fault):
    actual = rows()
    if fault == 'missing': actual.pop()
    if fault == 'duplicate': actual[-1] = copy.deepcopy(actual[0])
    if fault == 'foreign': actual[-1]['original']['original'][1] = 1
    if fault == 'unknown': actual[-1]['proof']['verdict'] = 'SUCCESS'
    with pytest.raises(ValueError): proof.merge(actual)


def test_counterexample_and_unknown_stay_distinct():
    actual = rows(); actual[0]['proof']['verdict'] = proof.CEX; actual[1]['proof']['verdict'] = proof.OPEN
    actual[2]['proof']['verdict'] = 'TIMEOUT_UNPROVED'; result = proof.merge(actual)
    assert (result['new_proved'], result['counterexamples'], result['undecided'], result['timeouts']) == (1, 1, 1, 1)


def test_native_launch_strips_credentials_without_elapsed_watchdog(tmp_path, monkeypatch):
    monkeypatch.setenv('GH_TOKEN', 'secret'); calls = []
    def run(command, **kwargs):
        calls.append(kwargs); kwargs['stdout'].write('native fixture\n'); return subprocess.CompletedProcess(command, 0)
    monkeypatch.setattr(proof.subprocess, 'run', run)
    result = proof.execute(['/tool'], tmp_path, 'native', 123)
    assert result['returncode'] == 0 and 'timeout' not in calls[0] and 'GH_TOKEN' not in calls[0]['env']


def test_unfinished_aggregate_keeps_failure_receipt(tmp_path, monkeypatch):
    monkeypatch.setattr(proof, 'verify_prepared', lambda p: ({}, {}))
    (tmp_path/'result.json').write_text('{}'); output = tmp_path/'verdict.json'
    with pytest.raises(ValueError): proof.aggregate(tmp_path, [], output)
    assert json.loads(output.read_text())['status'] == 'INCOMPLETE_OR_FAILED_HARD_BIT_REPLAY'


def test_one_job_four_immutable_results_and_full_history():
    text = (ROOT/proof.OWN[-1]).read_text()
    assert text.count('runs-on:') == 1 and 'fetch-depth: 0' in text
    for i in range(4): assert f'--index {i}' in text and f'name: alu-hard-bit-{i}-' in text
    assert text.count('include-hidden-files: true') == 5


def native_export_fixture(tmp_path):
    expected, text = expected_map()
    module = dict(ports=dict(lhs=dict(direction='input', bits=[2, 3]), clock=dict(direction='input', bits=[4]),
        bad=dict(direction='output', bits=[5])),
        cells=dict(g=dict(type='$_AND_', connections=dict(A=[2], B=[3], Y=[5]))),
        netnames=dict(unused_label=dict(bits=['x', 'z'])))
    (tmp_path/'observe.v').write_text('source fixture')
    (tmp_path/'ports.map').write_text(text); (tmp_path/'miter.aig').write_bytes(aig())
    (tmp_path/'interface.json').write_text(json.dumps(dict(modules=dict(observation=module))))
    return expected, module


def test_unused_debug_alias_x_does_not_create_functional_symbolic_inputs(tmp_path):
    expected, _ = native_export_fixture(tmp_path)
    result = proof.validate_export(tmp_path, expected)
    assert result['original_inputs'] == 3 and result['metadata_only_undefined_alias_bits'] == 2


@pytest.mark.parametrize('fault', ['output_x', 'cell_x', 'cell_z', 'input_alias', 'input_x', 'assumption', 'latch'])
def test_active_unknown_or_state_or_assumption_rejected(tmp_path, fault):
    expected, module = native_export_fixture(tmp_path)
    if fault == 'output_x': module['ports']['bad']['bits'] = ['x']
    if fault == 'cell_x': module['cells']['g']['connections']['A'] = ['x']
    if fault == 'cell_z': module['cells']['g']['connections']['A'] = ['z']
    if fault == 'input_alias': module['ports']['clock']['bits'] = [2]
    if fault == 'input_x': module['ports']['clock']['bits'] = ['x']
    if fault == 'assumption': module['cells']['g']['type'] = '$assume'
    if fault == 'latch': module['cells']['g']['type'] = '$_DLATCH_P_'
    (tmp_path/'interface.json').write_text(json.dumps(dict(modules=dict(observation=module))))
    with pytest.raises(ValueError): proof.validate_export(tmp_path, expected)


def test_aiger_map_option_uses_validated_bare_path_for_exact_backend():
    command = proof.export_commands(Path('/safe/export'))[-1]
    assert '-map /safe/export/ports.map' in command and '"' not in command
    with pytest.raises(ValueError): proof.export_commands(Path('/unsafe path'))


def test_original_is_read_once_then_restored_for_each_observation():
    command = proof.export_script(Path('/original143.il'), [Path('/out')/str(i) for i in range(4)])
    assert command.count('read_rtlil') == 1 and command.count('design -load source_original') == 4
    assert command.count('write_aiger') == 4 and 'setundef' not in command and 'assume' not in command


def test_constant_bad_output_map_omission_requires_native_and_aig_agreement(tmp_path):
    expected, module = native_export_fixture(tmp_path)
    module['ports']['bad']['bits'] = ['0']; module['cells'] = {}
    (tmp_path/'interface.json').write_text(json.dumps(dict(modules=dict(observation=module))))
    (tmp_path/'ports.map').write_text(expected_map()[1].replace('output 0 0 bad\n', ''))
    (tmp_path/'miter.aig').write_bytes(b'aig 3 3 0 1 0\n0\ni0 lhs[0]\ni1 lhs[1]\ni2 clock\no0 bad\nc\nfixture\n')
    assert proof.validate_export(tmp_path, expected)['constant_output'] == '0'
    (tmp_path/'miter.aig').write_bytes((tmp_path/'miter.aig').read_bytes().replace(b'\n0\n', b'\n1\n'))
    with pytest.raises(ValueError): proof.validate_export(tmp_path, expected)
