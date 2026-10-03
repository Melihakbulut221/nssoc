#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exact800-identity OR batches; native ABC with original-equation CEX attribution."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import subprocess

import prove_alu_hard_bits as hard

ROOT = Path(__file__).resolve().parents[1]
LOCK = 'hw/soc/pnr/alu-remaining-abc-input.lock.json'
OWN = ('scripts/prove_alu_remaining_abc.py', 'sw/tests/test_alu_remaining_abc.py', LOCK,
       '.github/workflows/timing-alu-remaining-abc.yml')
SOURCE = '41b45215a7cf4da06296e694fe3ba84d63eeba88'
LOCK_SHA256 = '815b5800909c0aa6ceca05adb97c01f8148b0e347ef01ed7f3671363e6e35e54'
remaining, state, part, ref = hard.remaining, hard.state, hard.part, hard.ref
require, pin, save = hard.require, hard.pin, hard.save


def load_lock():
    require(pin(ROOT/LOCK)['sha256'] == LOCK_SHA256, 'Changed grouped input lock')
    locked = json.loads((ROOT/LOCK).read_text()); old = hard.load_lock()
    require(locked['schema'] == 1 and locked['source_commit'] == SOURCE
        and locked['runtime'] == old['runtime'] and locked['refined_miter'] == old['refined_miter']
        and locked['source_run'] == 37105127162 and locked['shards'] == 16
        and locked['max_parallel'] == 4 and locked['batch_sizes'] == [16, 16, 14, 4]
        and locked['batch_seconds'] == 120 and locked['symbolic_inputs'] == 10828
        and locked['original_bits'] == 34321 and locked['remaining_bits'] == 800,
        'Changed grouped proof scope or original source')
    require(set(locked['dependencies']) == set(old['dependencies'])|set(hard.OWN), 'Frozen dependency closure changed')
    for name, value in locked['dependencies'].items():
        state.common.verify_file(ROOT/name, value)
        raw = subprocess.check_output(['git', 'show', SOURCE+':'+name], cwd=ROOT)
        require(dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()) == value, 'Original Git method mismatch')
    require(set(locked['archives']) == {'common', 'bit0', 'bit1', 'bit2', 'bit3', 'verdict'}, 'Incomplete original hard artifacts')
    require(locked['archives']['common']['sha256'] == '069068d45ab3b2e1f31e165706b65d415300850370efc26577f56c0033bbbde3'
        and locked['archives']['verdict']['sha256'] == 'db08464db3d157ba1cec1dbca96dcf91261ee97220ba69a444a14b44fe957b5d',
        'Changed successful hard capture')
    for value in locked['archives'].values():
        require(value['url'].startswith('https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20260927-chip-io/'),
                'Foreign hard archive URL')
    return locked


@contextmanager
def historical_capture_context():
    """Only replays already captured historical evidence; no native process is launched here."""
    current = os.environ.get('GITHUB_SHA'); os.environ['GITHUB_SHA'] = SOURCE
    try: yield
    finally:
        if current is None: os.environ.pop('GITHUB_SHA', None)
        else: os.environ['GITHUB_SHA'] = current


def verify_prior(directory, locked):
    common = directory/'common'; prepared = json.loads((common/'result.json').read_text())
    require(prepared['github_source_commit'] == SOURCE, 'Foreign historical source')
    for name, value in prepared['methods'].items():
        require(locked['dependencies'][name] == value, 'Historical method not in frozen closure')
    with historical_capture_context():
        actual, _ = hard.verify_prepared(common)
    require(actual == prepared, 'Historical preparation replay changed')
    rows = [hard.replay_result(directory/f'bit{i}', prepared, pin(common/'result.json'), common) for i in range(4)]
    combined = hard.merge(rows); captured = json.loads((directory/'verdict/alu-hard-verdict.json').read_text())
    require(all(captured[k] == v for k, v in combined.items()) and captured['prepared_result'] == pin(common/'result.json')
        and captured['github_source_commit'] == SOURCE and combined['new_proved'] == 4
        and combined['counterexamples'] == combined['timeouts'] == combined['undecided'] == 0,
        'Original four hard proofs cannot be reproduced')
    catalog = remaining.validate_catalog(json.loads((common/'prerequisites/catalog.json').read_text()), remaining.load_lock())
    plan = json.loads((common/'prerequisites/refined-plan.json').read_text())
    require(hard.hard_selection(catalog, plan) == prepared['hard_bits'], 'Hard original identity mismatch')
    return catalog, plan, dict(source_commit=SOURCE, common_result=pin(common/'result.json'),
        bit_results={str(i): pin(directory/f'bit{i}/result.json') for i in range(4)},
        verdict=pin(directory/'verdict/alu-hard-verdict.json'), proved_original_bits=[list(x) for x in hard.HARD],
        historical_source_context_only=True)


def snapshot(directory, locked):
    methods = {}
    for name in (*locked['dependencies'], *OWN):
        target = directory/'methods'/name; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT/name).read_bytes()); methods[name] = pin(target)
    return methods


def verify_methods(directory, methods, locked):
    require(set(methods) == set(locked['dependencies'])|set(OWN), 'Current method closure changed')
    for name, value in methods.items():
        state.common.verify_file(ROOT/name, value); state.common.verify_file(directory/'methods'/name, value)
        if name in locked['dependencies']: require(value == locked['dependencies'][name], 'Frozen dependency changed')


def grouped_wrapper(plan, selected):
    require(1 <= len(selected) <= 16 and len({tuple(x['original']) for x in selected}) == len(selected),
            'Duplicate/oversized OR batch')
    parents = {g['id']: g for g in plan['groups']}; names = list(plan['symbolic_inputs'])
    observed = sorted({x['parent'] for x in selected})
    # Reuse the frozen single-observation name/parent/offset guards.
    for row in selected: hard.wrapper(plan, row)
    declarations = [f'input wire [{w-1}:0] in_{n}' for n, w in plan['symbolic_inputs'].items()]
    lines = ['module observation('+',\n'.join(declarations+['output wire bad'])+');',
             f'(* keep = 1 *) wire [{len(selected)-1}:0] selected_diff;']
    for parent in observed:
        for prefix in ('gold', 'gate'): lines.append(f'wire [{len(parents[parent]["obligations"])-1}:0] {prefix}_{parent};')
    connections = [f'.in_{n}(in_{n})' for n in names]
    connections += [f'.{prefix}_{n}({prefix}_{n})' for n in observed for prefix in ('gold', 'gate')]
    lines.append('nssoc_preserved_miter p('+',\n'.join(connections)+');')
    for i, row in enumerate(selected):
        parent, bit = row['parent'], row['bit']
        lines.append(f'assign selected_diff[{i}]=gold_{parent}[{bit}]^gate_{parent}[{bit}];')
    return '\n'.join(lines+['assign bad=|selected_diff;', 'endmodule', ''])


def differing_originals(witness, selected):
    rows = [x for x in witness['signal'] if x['name'] == 'selected_diff']
    require(len(rows) == 1, 'Missing original mismatch vector')
    row = rows[0]
    if len(selected) == 1 and row.get('wave', '').startswith(('0', '1')): bits = row['wave'][0]
    else:
        require(isinstance(row.get('data'), list) and len(row['data']) >= 1, 'Missing original mismatch data')
        bits = row['data'][0]
    require(isinstance(bits, str) and len(bits) == len(selected) and set(bits) <= {'0', '1'},
            'Undefined or truncated original mismatch vector')
    actual = [selected[i]['original'] for i, b in enumerate(reversed(bits)) if b == '1']
    require(actual and len(actual) == len({tuple(x) for x in actual}), 'No actual differing original identities')
    return actual


def vector_script(source, observation, assignments, expected, output):
    original = hard.replay_script(source, observation, assignments, expected, output)
    require(original.count('-show-inputs -show-outputs') == 1, 'Original replay template changed')
    return original.replace('-show-inputs -show-outputs', '-show selected_diff -show-inputs -show-outputs')


def solve(runtime, export, source, output, expected, selected, *, seconds=120, memory=6*1024**3):
    proof = hard.solve(runtime, export, source, output, expected, seconds=seconds, memory=memory)
    if proof['verdict'] == hard.CEX:
        d = output/'attribution'; d.mkdir(); script = d/'replay.ys'
        script.write_text(vector_script(source, export/'observe.v', proof['assignments'], expected, d))
        execution = hard.execute([runtime, 'yosys', '-Q', '-T', '-s', script], d, 'replay', memory)
        require(execution['returncode'] == 0 and 'SAT proof finished - model found: FAIL!' in (d/'replay.log').read_text(),
                'Original grouped counterexample attribution failed')
        witness = json.loads((d/'original-cex.json').read_text())
        bad = [x for x in witness['signal'] if x['name'] == 'bad']
        require(len(bad) == 1 and bad[0]['wave'].startswith('1'), 'Attribution did not reproduce original bad=1')
        proof['attribution'] = dict(execution=execution, script=pin(script), witness=pin(d/'original-cex.json'),
            differing_original_bits=differing_originals(witness, selected))
    return proof


def verify_solve(directory, export, native_export, native_output, runtime, proof, expected, source, selected,
                 *, seconds=120, memory=6*1024**3):
    hard.verify_solve(directory, export, native_export, native_output, runtime, proof, expected, source,
                      seconds=seconds, memory=memory)
    if proof['verdict'] == hard.CEX:
        row = proof['attribution']; d = directory/'attribution'; n = native_output/'attribution'
        require((d/'replay.ys').read_text() == vector_script(source, native_export/'observe.v', proof['assignments'], expected, n)
            and pin(d/'replay.ys') == row['script'] and pin(d/'original-cex.json') == row['witness'], 'Changed attribution source')
        ex = json.loads((d/'replay-execution.json').read_text())
        require(ex == row['execution'] and ex['returncode'] == 0 and ex['memory_limit_bytes'] == memory
            and ex['command'] == list(map(str, [runtime, 'yosys', '-Q', '-T', '-s', n/'replay.ys']))
            and pin(d/'replay.log') == ex['log'] and 'SAT proof finished - model found: FAIL!' in (d/'replay.log').read_text(),
            'Changed original attribution execution')
        witness = json.loads((d/'original-cex.json').read_text())
        require(differing_originals(witness, selected) == row['differing_original_bits'], 'Changed differing original IDs')
        bad = [x for x in witness['signal'] if x['name'] == 'bad']
        require(len(bad) == 1 and bad[0]['wave'].startswith('1'), 'Original attribution lost bad=1')
    else: require('attribution' not in proof, 'Attribution without actual counterexample')


def control_source(mode):
    require(mode in ('equal', 'wrong_output', 'wrong_clock'), 'Unknown control')
    declarations = ['input [7:0] in_lhs,in_rhs', 'input [0:0] in_carry,in_spare']
    declarations += ['output [0:0] '+p+f'_g{i}' for i in range(3) for p in ('gold', 'gate')]
    text = 'module miter('+','.join(declarations)+');\nwire equal_bad,wrong_bad;\n'
    text += 'equal_arithmetic e(in_lhs,in_rhs,in_carry,in_spare,equal_bad);\nwrong_arithmetic w(in_lhs,in_rhs,in_carry,in_spare,wrong_bad);\n'
    text += 'assign gold_g0=0;assign gate_g0=equal_bad;assign gold_g1=0;assign gate_g1='+('wrong_bad' if mode == 'wrong_output' else 'equal_bad')+';\n'
    text += 'assign gold_g2=in_carry;assign gate_g2='+('~in_carry' if mode == 'wrong_clock' else 'in_carry')+';endmodule\n'
    return text+hard.arithmetic_control().replace('module observation', 'module equal_arithmetic')+hard.arithmetic_control(True).replace('module observation', 'module wrong_arithmetic')


def controls(runtime, output):
    output.mkdir(); plan = dict(symbolic_inputs=dict(lhs=8, rhs=8, carry=1, spare=1),
        groups=[dict(id=f'g{i}', obligations=[[f'fixture{i}', 0]]) for i in range(3)])
    selected = [dict(parent=f'g{i}', bit=0, original=[f'fixture{i}', 0]) for i in range(3)]
    expected = {'in_'+n: w for n, w in plan['symbolic_inputs'].items()}; result = {}
    for mode in ('equal', 'wrong_output', 'wrong_clock'):
        d = output/mode; d.mkdir(); source = d/'source.v'; source.write_text(control_source(mode)); script = d/'source.ys'
        original = d/'original.il'; script.write_text(f'read_verilog {state.quoted(source)}\nprep -top miter -flatten\nwrite_rtlil {state.quoted(original)}\n')
        start = hard.execute([runtime, 'yosys', '-Q', '-T', '-s', script], d, 'source', 2*1024**3)
        require(start['returncode'] == 0, 'Tiny original graph build failed')
        (d/'observe.v').write_text(grouped_wrapper(plan, selected)); script = d/'export.ys'; script.write_text(hard.export_script(original, [d]))
        export = hard.execute([runtime, 'yosys', '-Q', '-T', '-s', script], d, 'export', 2*1024**3)
        require(export['returncode'] == 0, 'Tiny grouped export failed')
        proof = solve(runtime, d, original, d, expected, selected, seconds=10, memory=2*1024**3)
        require(proof['verdict'] == (hard.PASS if mode == 'equal' else hard.CEX), 'Grouped native control failed')
        if mode != 'equal': require(proof['attribution']['differing_original_bits'] == [[f'fixture{1 if mode == "wrong_output" else 2}', 0]], 'Wrong original fault attribution')
        result[mode] = dict(proof=proof, source_execution=start, export_execution=export,
                            source=pin(source), original=pin(original))
    save(output/'result.json', result)
    return result


def verify_controls(output, recorded, runtime):
    require(recorded == json.loads((output/'result.json').read_text()) and set(recorded) == {'equal', 'wrong_output', 'wrong_clock'},
            'Changed grouped native controls')
    plan = dict(symbolic_inputs=dict(lhs=8, rhs=8, carry=1, spare=1),
        groups=[dict(id=f'g{i}', obligations=[[f'fixture{i}', 0]]) for i in range(3)])
    selected = [dict(parent=f'g{i}', bit=0, original=[f'fixture{i}', 0]) for i in range(3)]
    expected = {'in_'+n: w for n, w in plan['symbolic_inputs'].items()}
    for mode, row in recorded.items():
        d = output/mode; native = Path(row['source_execution']['command'][-1]).parent
        require(native.is_absolute() and (d/'source.v').read_text() == control_source(mode)
            and pin(d/'source.v') == row['source'] and pin(d/'original.il') == row['original']
            and (d/'observe.v').read_text() == grouped_wrapper(plan, selected)
            and (d/'source.ys').read_text() == f'read_verilog {state.quoted(native/"source.v")}\nprep -top miter -flatten\nwrite_rtlil {state.quoted(native/"original.il")}\n'
            and (d/'export.ys').read_text() == hard.export_script(native/'original.il', [native]), 'Grouped control source changed')
        for label in ('source', 'export'):
            ex = json.loads((d/(label+'-execution.json')).read_text())
            require(ex == row[label+'_execution'] and ex['returncode'] == 0 and ex['memory_limit_bytes'] == 2*1024**3
                and ex['command'] == list(map(str, [runtime, 'yosys', '-Q', '-T', '-s', native/(label+'.ys')]))
                and ex['log'] == pin(d/(label+'.log')), 'Tiny native execution changed')
        proof = row['proof']; verify_solve(d, d, native, native, runtime, proof, expected, native/'original.il', selected,
                                          seconds=10, memory=2*1024**3)
        require(proof['verdict'] == (hard.PASS if mode == 'equal' else hard.CEX), 'Unexpected control verdict')
        if mode != 'equal': require(proof['attribution']['differing_original_bits'] == [[f'fixture{1 if mode == "wrong_output" else 2}', 0]], 'Control fault identity changed')


def prepare(output, work):
    require(os.environ.get('GITHUB_ACTIONS') == 'true', 'Full original graph preparation is cloud-only')
    output = state.common.fresh_directory(output); work = state.common.fresh_directory(work)
    row = dict(status='PREPARING_GROUPED_800', github_source_commit=os.environ.get('GITHUB_SHA'), candidate_adopted=False)
    try:
        locked = load_lock(); row['methods'] = snapshot(output, locked)
        original = dict(run_id=locked['source_run'], source_commit=SOURCE, source_conclusion='success')
        row['original_run'] = remaining.run_identity(original); row['acquisition'] = {}
        (output/'prior').mkdir()
        for name, entry in locked['archives'].items():
            archive = work/(name+'.zip'); row['acquisition'][name] = remaining.acquire(original, entry, archive, permanent=True)
            ref.restore(archive, output/'prior'/name)
        catalog, plan, verification = verify_prior(output/'prior', locked)
        save(output/'catalog.json', catalog); save(output/'plan.json', plan); row['prior_verification'] = verification
        runtime = work/'runtime.AppImage'; state.common.download(locked['runtime'], runtime); runtime.chmod(0o755)
        row['native_identity'] = hard.native_identity(runtime, output, hard.load_lock())
        row['controls'] = controls(runtime, output/'controls')
        require(verify_prior(output/'prior', locked) == (catalog, plan, verification), 'Original source changed during grouped controls')
        verify_methods(output, row['methods'], locked); state.common.verify_file(runtime, locked['runtime'])
        row.update(status='EXACT800_GROUPED_SOURCE_PREPARED', complete_inputs_rechecked=True, runtime=locked['runtime'],
                   source_graph=locked['refined_miter'], native_paths=dict(output=str(output), work=str(work)),
                   catalog=pin(output/'catalog.json'), plan=pin(output/'plan.json'))
    except BaseException as error:
        row.update(status='PREPARATION_FAILED_PRESERVED', error=repr(error)); raise
    finally: row['outputs'] = ref.inventory(output); save(output/'result.json', row)
    return row


def verify_prepared(bundle):
    locked = load_lock(); row = json.loads((bundle/'result.json').read_text())
    require(row['status'] == 'EXACT800_GROUPED_SOURCE_PREPARED' and row['complete_inputs_rechecked'] is True
        and row['github_source_commit'] == os.environ.get('GITHUB_SHA') and row['runtime'] == locked['runtime']
        and row['source_graph'] == locked['refined_miter'] and row['candidate_adopted'] is False, 'Incomplete/foreign grouped source')
    part.verify_inventory(bundle, row['outputs']); verify_methods(bundle, row['methods'], locked)
    catalog, plan, prior = verify_prior(bundle/'prior', locked)
    require(prior == row['prior_verification'] and pin(bundle/'catalog.json') == row['catalog'] and pin(bundle/'plan.json') == row['plan']
        and json.loads((bundle/'catalog.json').read_text()) == catalog and json.loads((bundle/'plan.json').read_text()) == plan,
        'Changed original identity partition')
    paths = {k: Path(v) for k, v in row['native_paths'].items()}
    require(set(paths) == {'output', 'work'} and all(p.is_absolute() for p in paths.values()), 'Unbound native preparation paths')
    runtime = paths['work']/'runtime.AppImage'
    verify_controls(bundle/'controls', row['controls'], runtime)
    identity = json.loads((bundle/'native-identity.log').read_text())
    require(identity == row['native_identity'] and (bundle/'native-identity.py').read_text() == hard.native_identity_script()
        and identity['binaries'] == {n: hard.load_lock()[k] for n, k in [('yosys', 'native_yosys'), ('yosys-abc', 'native_abc')]},
        'Changed native runtime identity')
    execution = json.loads((bundle/'native-identity-execution.json').read_text())
    require(execution['returncode'] == 0 and execution['memory_limit_bytes'] == 2*1024**3
        and execution['command'] == list(map(str, [runtime, 'python', paths['output']/'native-identity.py']))
        and execution['log'] == pin(bundle/'native-identity.log'), 'Changed native launcher binding query')
    return row, catalog, plan, locked


def prepare_shard(bundle, shard, output, work):
    require(os.environ.get('GITHUB_ACTIONS') == 'true' and type(shard) is int and 0 <= shard < 16, 'Invalid cloud shard')
    output = state.common.fresh_directory(output); work = state.common.fresh_directory(work)
    row = dict(status='PREPARING_GROUPED_SHARD', shard=shard, github_source_commit=os.environ.get('GITHUB_SHA'), candidate_adopted=False)
    try:
        prepared, catalog, plan, locked = verify_prepared(bundle)
        runtime = work/'runtime.AppImage'; state.common.download(locked['runtime'], runtime); runtime.chmod(0o755)
        source = bundle/'prior/common/prerequisites/prior/common/common-miter.il'; state.common.verify_file(source, locked['refined_miter'])
        selections = {str(i): remaining.batch_selection(catalog, shard, i) for i in range(4)}; exports = []
        for i in range(4):
            d = output/'exports'/str(i); d.mkdir(parents=True); (d/'observe.v').write_text(grouped_wrapper(plan, selections[str(i)])); exports.append(d)
        script = output/'export.ys'; script.write_text(hard.export_script(source, exports))
        execution = hard.execute([runtime, 'yosys', '-Q', '-T', '-s', script], output, 'export', 6*1024**3)
        require(execution['returncode'] == 0, 'Native grouped export failed')
        expected = {'in_'+n: w for n, w in plan['symbolic_inputs'].items()}
        row.update(exports={str(i): hard.validate_export(d, expected) for i, d in enumerate(exports)}, selections=selections,
            prepared_result=pin(bundle/'result.json'), source_graph=locked['refined_miter'], methods=prepared['methods'],
            native_paths=dict(bundle=str(bundle), output=str(output), work=str(work)), export_execution=execution, symbolic_inputs=expected)
        require(verify_prepared(bundle)[0] == prepared, 'Original grouped source changed during export')
        state.common.verify_file(runtime, locked['runtime']); state.common.verify_file(source, locked['refined_miter'])
        row.update(status='FOUR_GROUPED_EXPORTS_PREPARED', complete_inputs_rechecked=True)
    except BaseException as error: row.update(status='SHARD_PREPARATION_FAILED', error=repr(error)); raise
    finally: row['outputs'] = ref.inventory(output); save(output/'result.json', row)
    return row


def verify_shard(bundle, directory, prepared, catalog, plan):
    row = json.loads((directory/'result.json').read_text()); shard = row['shard']
    require(type(shard) is int and 0 <= shard < 16 and row['status'] == 'FOUR_GROUPED_EXPORTS_PREPARED'
        and row['complete_inputs_rechecked'] is True and row['github_source_commit'] == prepared['github_source_commit']
        and row['prepared_result'] == pin(bundle/'result.json') and row['methods'] == prepared['methods']
        and row['source_graph'] == prepared['source_graph'] and row['candidate_adopted'] is False, 'Foreign/incomplete grouped shard')
    part.verify_inventory(directory, row['outputs']); paths = {k: Path(v) for k, v in row['native_paths'].items()}
    require(set(paths) == {'bundle', 'output', 'work'} and all(p.is_absolute() for p in paths.values()), 'Unbound native shard paths')
    selected = {str(i): remaining.batch_selection(catalog, shard, i) for i in range(4)}
    expected = {'in_'+n: w for n, w in plan['symbolic_inputs'].items()}
    require(row['selections'] == selected and row['symbolic_inputs'] == expected and sum(expected.values()) == 10828,
            'Changed original batch coverage or symbolic boundary')
    for i in range(4):
        d = directory/'exports'/str(i)
        require((d/'observe.v').read_text() == grouped_wrapper(plan, selected[str(i)])
            and hard.validate_export(d, expected) == row['exports'][str(i)], 'Changed grouped AIG observation')
    source = paths['bundle']/'prior/common/prerequisites/prior/common/common-miter.il'
    require((directory/'export.ys').read_text() == hard.export_script(source, [paths['output']/'exports'/str(i) for i in range(4)]),
            'Changed original graph read/export command')
    execution = json.loads((directory/'export-execution.json').read_text())
    require(execution == row['export_execution'] and execution['returncode'] == 0 and execution['memory_limit_bytes'] == 6*1024**3
        and execution['command'] == list(map(str, [paths['work']/'runtime.AppImage', 'yosys', '-Q', '-T', '-s', paths['output']/'export.ys']))
        and execution['log'] == pin(directory/'export.log'), 'Changed native export execution')
    return row


def run_batch(bundle, shard_directory, batch, output):
    require(os.environ.get('GITHUB_ACTIONS') == 'true' and type(batch) is int and 0 <= batch < 4, 'Invalid native grouped batch')
    output = state.common.fresh_directory(output)
    row = dict(status='PREPARING_GROUPED_BATCH', batch=batch, github_source_commit=os.environ.get('GITHUB_SHA'), candidate_adopted=False)
    try:
        prepared, catalog, plan, locked = verify_prepared(bundle); shard = verify_shard(bundle, shard_directory, prepared, catalog, plan)
        runtime = Path(shard['native_paths']['work'])/'runtime.AppImage'; state.common.verify_file(runtime, locked['runtime'])
        selected = shard['selections'][str(batch)]; source = bundle/'prior/common/prerequisites/prior/common/common-miter.il'
        row.update(shard=shard['shard'], selected=selected, shard_result=pin(shard_directory/'result.json'),
            prepared_result=pin(bundle/'result.json'), methods=prepared['methods'], source_graph=locked['refined_miter'],
            native_paths=dict(bundle=str(bundle), shard=str(shard_directory), output=str(output)))
        save(output/'result.json', row)
        row['proof'] = solve(runtime, shard_directory/'exports'/str(batch), source, output, shard['symbolic_inputs'], selected)
        require(verify_shard(bundle, shard_directory, prepared, catalog, plan) == shard, 'Grouped shard changed during proof')
        require(verify_prepared(bundle)[0] == prepared, 'Complete prepared inputs changed during grouped proof')
        state.common.verify_file(runtime, locked['runtime']); state.common.verify_file(source, locked['refined_miter'])
        row.update(status='GROUPED_BATCH_NATIVE_RESULT_CAPTURED', complete_inputs_rechecked=True)
    except BaseException as error: row.update(status='GROUPED_BATCH_FAILED_OR_INCOMPLETE', error=repr(error)); raise
    finally: row['outputs'] = ref.inventory(output); save(output/'result.json', row)
    return row


def replay_batch(directory, bundle, shard_directory, prepared, shard):
    row = json.loads((directory/'result.json').read_text()); batch = row['batch']
    require(type(batch) is int and 0 <= batch < 4 and row['status'] == 'GROUPED_BATCH_NATIVE_RESULT_CAPTURED'
        and row['complete_inputs_rechecked'] is True and row['github_source_commit'] == prepared['github_source_commit']
        and row['shard'] == shard['shard'] and row['selected'] == shard['selections'][str(batch)]
        and row['shard_result'] == pin(shard_directory/'result.json') and row['prepared_result'] == pin(bundle/'result.json')
        and row['methods'] == prepared['methods'] and row['source_graph'] == prepared['source_graph']
        and row['candidate_adopted'] is False, 'Foreign/incomplete OR batch')
    part.verify_inventory(directory, row['outputs']); paths = {k: Path(v) for k, v in row['native_paths'].items()}
    require(set(paths) == {'bundle', 'shard', 'output'} and all(x.is_absolute() for x in paths.values())
        and paths['bundle'] == Path(shard['native_paths']['bundle']) and paths['shard'] == Path(shard['native_paths']['output']),
        'Changed native batch paths')
    require(row['proof']['export'] == shard['exports'][str(batch)], 'Wrong grouped AIG')
    verify_solve(directory, shard_directory/'exports'/str(batch), paths['shard']/'exports'/str(batch), paths['output'],
        Path(shard['native_paths']['work'])/'runtime.AppImage', row['proof'], shard['symbolic_inputs'],
        paths['bundle']/'prior/common/prerequisites/prior/common/common-miter.il', row['selected'])
    return row


def merge(catalog, rows):
    require(len(rows) == 64 and {(r['shard'], r['batch']) for r in rows} == {(s, b) for s in range(16) for b in range(4)},
            'Missing or duplicate original OR batch')
    passed, open_bits, counterexamples = [], [], []
    for row in rows:
        selected = remaining.batch_selection(catalog, row['shard'], row['batch'])
        require(row['selected'] == selected, 'Grouped proof original IDs differ')
        verdict = row['proof']['verdict']; require(verdict in {hard.PASS, hard.CEX, hard.OPEN, 'TIMEOUT_UNPROVED'}, 'Unknown native grouped verdict')
        (passed if verdict == hard.PASS else open_bits).extend(x['original'] for x in selected)
        if verdict == hard.CEX:
            actual = row['proof']['attribution']['differing_original_bits']
            require(actual and len(actual) == len({tuple(x) for x in actual}) and set(map(tuple, actual)) <= {tuple(x['original']) for x in selected}, 'CEX refers to wrong original identities')
            counterexamples.extend(actual)
    all_new = passed+open_bits; expected = {tuple(x['original']) for x in catalog['untested']}
    require(len(all_new) == len(set(map(tuple, all_new))) == 800 and set(map(tuple, all_new)) == expected,
            'OR-batch universe is not exactly800 disjoint original equations')
    preserved = {tuple(x) for x in catalog['preserved_proved']}; hard_ids = {tuple(x['original']) for x in catalog['hard']}
    require(len(preserved) == 33517 and hard_ids == set(hard.HARD) and len(preserved|hard_ids|expected) == 34321
        and len(preserved)+len(hard_ids)+len(expected) == 34321, 'Global identities overlap or omit equations')
    complete = len(passed) == 800
    return dict(status='COMPLETE_BINARY_BOUNDARY_RELATION_PROVED' if complete else 'GROUPED_800_REMAINS_INCOMPLETE_OR_COUNTEREXAMPLE',
        original_bits=34321, preserved_prior=33517, independently_proved_hard=4, new_800_proved=len(passed),
        total_unique_proved=33521+len(passed), unproved_original_bits=open_bits, proved_800_original_bits=passed,
        actual_counterexample_original_bits=counterexamples, grouped_pass_implies_each_listed_bit=True,
        grouped_query_differs_from_individual_query=True, sat_partial_evidence_unchanged_and_not_added_again=True,
        state_bijection_proved=complete, candidate_adopted=False, full_soc_functional_accepted=False,
        unresolved_four_state_boot_failure=True, timing_accepted=False, manufacturing_approval=False)


def aggregate(bundle, shards, batches, output):
    row = dict(status='INCOMPLETE_GROUPED_CAPTURE_OR_FAILED_REPLAY', state_bijection_proved=False, candidate_adopted=False)
    try:
        prepared, catalog, plan, _ = verify_prepared(bundle)
        require(len(shards) == 16 and len(batches) == 64, 'Incomplete native source/batch artifacts')
        mapped = {}
        for d in shards:
            s = verify_shard(bundle, d, prepared, catalog, plan); require(s['shard'] not in mapped, 'Duplicate captured shard'); mapped[s['shard']] = (d, s)
        require(set(mapped) == set(range(16)), 'Missing original cloud shard')
        rows = []
        for d in batches:
            index = json.loads((d/'result.json').read_text())['shard']; require(index in mapped, 'Unknown batch shard')
            sd, sr = mapped[index]; rows.append(replay_batch(d, bundle, sd, prepared, sr))
        row = merge(catalog, rows); row.update(github_source_commit=prepared['github_source_commit'],
            prepared_result=pin(bundle/'result.json'), hard_prior_verification=prepared['prior_verification'],
            batch_results={f'{r["shard"]}:{r["batch"]}': pin(d/'result.json') for r, d in zip(rows, batches, strict=True)})
    except BaseException as error: row['error'] = repr(error); save(output, row); raise
    save(output, row); require(not row['actual_counterexample_original_bits'], 'Actual original-equation CEX preserved')
    return row


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('phase', choices=['prepare', 'shard', 'batch', 'aggregate', 'controls'])
    p.add_argument('--output', type=Path, required=True); p.add_argument('--work', type=Path); p.add_argument('--bundle', type=Path)
    p.add_argument('--shard', type=int); p.add_argument('--batch', type=int); p.add_argument('--shard-directory', type=Path)
    p.add_argument('--artifact-root', type=Path); p.add_argument('--runtime', type=Path); a = p.parse_args()
    if a.phase == 'prepare': row = prepare(a.output.resolve(), a.work.resolve())
    elif a.phase == 'shard': row = prepare_shard(a.bundle.resolve(), a.shard, a.output.resolve(), a.work.resolve())
    elif a.phase == 'batch': row = run_batch(a.bundle.resolve(), a.shard_directory.resolve(), a.batch, a.output.resolve())
    elif a.phase == 'aggregate':
        paths = list(a.artifact_root.rglob('result.json'))
        shards = sorted(x.parent for x in paths if x.parent.name.startswith('alu-abc-shard-'))
        batches = sorted(x.parent for x in paths if x.parent.name.startswith('alu-abc-batch-'))
        row = aggregate(a.bundle.resolve(), shards, batches, a.output.resolve())
    else: row = controls(a.runtime.resolve(), a.output.resolve())
    print(row.get('status', 'PASS_GROUPED_NATIVE_CONTROLS'), flush=True)


if __name__ == '__main__': main()
