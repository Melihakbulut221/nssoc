#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Four unchanged binary boundary equations through pinned ABC, with full CEX replay."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import time

import prove_alu_remaining_bits as remaining

ROOT = Path(__file__).resolve().parents[1]
LOCK = 'hw/soc/pnr/alu-hard-bits-input.lock.json'
OWN = ('scripts/prove_alu_hard_bits.py', 'sw/tests/test_alu_hard_bits.py', LOCK,
       '.github/workflows/timing-alu-hard-bits.yml')
FROZEN_COMMIT = '14f5b2f38ce6040433b888b3522800b1b264a04d'
HARD = [('__mapped_state_equiv_ff_d', 738), ('__mapped_state_equiv_ff_d', 5732),
        ('__mapped_state_equiv_gate_enable', 0), ('__mapped_state_equiv_gate_next', 0)]
PASS, CEX, OPEN = 'PROVED_ALL_BINARY_BOUNDARY_EQUATIONS', 'COUNTEREXAMPLE_REPLAYED_ON_ORIGINAL', 'UNDECIDED_UNPROVED'
state, part, ref = remaining.state, remaining.part, remaining.ref
require, pin, save = state.require, remaining.pin, remaining.save


def load_lock():
    row = json.loads((ROOT/LOCK).read_text()); prior = remaining.load_lock()
    require(row['schema'] == 1 and row['frozen_commit'] == FROZEN_COMMIT
        and row['runtime'] == prior['runtime'] and row['refined_miter'] == prior['refined_miter']
        and row['symbolic_input_bits'] == 10828 and row['original_bits'] == 34321
        and row['solver_seconds'] == 120 and row['memory_bytes'] == 6*1024**3,
        'Changed frozen graph/runtime/budget')
    require(row['hard_original_bits'] == [list(x) for x in HARD]
        and row['hard_original_bits'] == prior['hard_original_bits'], 'Changed four hard identities')
    require(set(row['dependencies']) == set(prior['source_method_pins'])|set(remaining.OWN), 'Dependency closure differs')
    for name, expected in row['dependencies'].items():
        state.common.verify_file(ROOT/name, expected)
        raw = subprocess.check_output(['git', 'show', FROZEN_COMMIT+':'+name], cwd=ROOT)
        require(dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()) == expected, 'Frozen Git dependency differs')
    require(row['native_abc']['sha256'] == 'c4ff60740cc2d6f0afe72f0dda58f65342cce10d64eddb6bf169577c7fa69f71'
        and row['native_yosys']['sha256'] == '3a9560d83e60d9e98f34a03cdbedbb49adefc8a63096bd77c7c4108bc9ccdef2',
        'Changed native binary contract')
    return row


def snapshot(output, locked):
    result = {}
    for name in (*locked['dependencies'], *OWN):
        target = output/'methods'/name; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT/name).read_bytes()); result[name] = pin(target)
    return result


def verify_methods(output, methods, locked):
    require(set(methods) == set(locked['dependencies'])|set(OWN), 'Method closure changed')
    for name, value in methods.items():
        state.common.verify_file(ROOT/name, value); state.common.verify_file(output/'methods'/name, value)
        if name in locked['dependencies']: require(value == locked['dependencies'][name], 'Dependency replaced')


def execute(command, output, label, memory):
    def limit():
        resource.setrlimit(resource.RLIMIT_AS, (memory, memory)); resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    env = {k: v for k, v in os.environ.items() if k not in ('GH_TOKEN', 'GITHUB_TOKEN', 'PYTHONPATH', 'PYTHONHOME')}
    start = time.monotonic()
    with (output/(label+'.log')).open('x') as stream:
        p = subprocess.run(list(map(str, command)), stdout=stream, stderr=subprocess.STDOUT,
                           stdin=subprocess.DEVNULL, env=env, preexec_fn=limit, check=False)
    row = dict(command=list(map(str, command)), returncode=p.returncode, seconds=time.monotonic()-start,
               memory_limit_bytes=memory, log=pin(output/(label+'.log')))
    save(output/(label+'-execution.json'), row)
    return row


def native_identity_script():
    return """import hashlib,json,pathlib,shutil
base=pathlib.Path('/nix/store/4bmfi4470w0i3ixcaidfki18d3fyqvva-yosys-with-plugins-0.62/bin')
leaf=pathlib.Path('/nix/store/f1q0w7rd0a4ny4hqvfxlhs4cmariidcy-yosys-0.62/bin')
def pin(p):
    return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(p.open('rb'),'sha256').hexdigest())
result=dict(binaries={},bindings={})
for name in ('yosys','yosys-abc'):
    entry=pathlib.Path(shutil.which(name)).resolve(); intermediate=base/name
    assert str(intermediate).encode() in entry.read_bytes()
    if name=='yosys':
        wrapped=base/'.yosys-wrapped'
        assert str(wrapped) in intermediate.read_text()
        target=wrapped.resolve()
    else: target=intermediate.resolve()
    assert target==leaf/name
    result['binaries'][name]=pin(target)
    result['bindings'][name]=dict(entry=dict(path=str(entry),**pin(entry)),
        intermediate=dict(path=str(intermediate),**pin(intermediate)),
        target=dict(path=str(target),**pin(target)),launcher_reference_verified=True)
print(json.dumps(result))
"""


def native_identity(runtime, output, locked):
    script = output/'native-identity.py'; script.write_text(native_identity_script())
    ex = execute([runtime, 'python', script], output, 'native-identity', 2*1024**3)
    require(ex['returncode'] == 0, 'Native identity query failed')
    actual = json.loads((output/'native-identity.log').read_text())
    require(actual['binaries'] == {'yosys': locked['native_yosys'], 'yosys-abc': locked['native_abc']},
            'Native executable mismatch')
    return actual


def hard_selection(value, refined):
    selected = value['hard']; parents = {g['id']: g for g in refined['groups']}
    require([tuple(x['original']) for x in selected] == HARD and len(selected) == 4,
            'Hard set is not the exact four original equations')
    for x in selected:
        require(x['parent'] in parents and type(x['bit']) is int
            and 0 <= x['bit'] < len(parents[x['parent']]['obligations']), 'Invalid native parent/offset')
    require(refined['symbolic_input_bits'] == sum(refined['symbolic_inputs'].values()) == 10828,
            'Original symbolic boundary changed')
    return selected


def wrapper(plan, selected):
    names = list(plan['symbolic_inputs']); parent = selected['parent']
    require(all(re.fullmatch('[A-Za-z_][A-Za-z0-9_]*', n) for n in [*names, parent]), 'Unsafe port name')
    parents = {g['id']: g for g in plan['groups']}; width = len(parents[parent]['obligations'])
    require(type(selected['bit']) is int and 0 <= selected['bit'] < width, 'Invalid observed offset')
    declarations = [f'input wire [{w-1}:0] in_{n}' for n, w in plan['symbolic_inputs'].items()]
    lines = ['module observation('+',\n'.join(declarations+['output wire bad'])+');',
             f'wire [{width-1}:0] gold_bits,gate_bits;']
    connections = [f'.in_{n}(in_{n})' for n in names]
    connections += [f'.gold_{parent}(gold_bits)', f'.gate_{parent}(gate_bits)']
    lines += ['nssoc_preserved_miter p('+',\n'.join(connections)+');',
              f'assign bad=gold_bits[{selected["bit"]}]^gate_bits[{selected["bit"]}];', 'endmodule', '']
    return '\n'.join(lines)


def export_commands(directory):
    require(re.fullmatch(r'[A-Za-z0-9_./-]+', str(directory)), 'Unsafe AIG backend path')
    return ['techmap', 'opt -full', 'aigmap', 'opt_clean -purge', 'delete t:$scopeinfo', 'check -assert',
            'stat', f'write_json {state.quoted(directory/"interface.json")}',
            f'write_aiger -symbols -map {directory/"ports.map"} {directory/"miter.aig"}']


def export_script(source, exports):
    lines = [f'read_rtlil {state.quoted(source)}', 'design -save source_original']
    for directory in exports:
        lines += ['design -load source_original', 'rename miter nssoc_preserved_miter',
                  f'read_verilog {state.quoted(directory/"observe.v")}', 'prep -top observation -flatten']
        lines += export_commands(directory)
    return '\n'.join(lines)+'\n'


def parse_map(text, expected, *, constant_output=False):
    rows = []
    for line in text.splitlines():
        fields = line.split()
        require(len(fields) == 4 and fields[0] in {'input', 'output'}, 'Unknown AIG map record')
        kind, index, offset, name = fields
        require(index.isdigit() and offset.isdigit(), 'Noninteger AIG map coordinate')
        if kind == 'output': require(fields == ['output', '0', '0', 'bad'], 'Foreign AIG output')
        else: rows.append((int(index), name, int(offset)))
    count = text.splitlines().count('output 0 0 bad')
    require(count == 1 or (constant_output and count == 0), 'Missing/duplicate bad output')
    require([x[0] for x in rows] == list(range(sum(expected.values())))
        and {(n, b) for _, n, b in rows} == {(n, b) for n, w in expected.items() for b in range(w)}
        and len({(n, b) for _, n, b in rows}) == len(rows), 'AIG map is not exact original input bijection')
    return rows


def validate_aiger(raw, mapping, expected):
    header, rest = raw.split(b'\n', 1); tokens = header.decode().split()
    require(len(tokens) == 6 and tokens[0] == 'aig' and all(s.isdigit() for s in tokens[1:]),
            'Require binary combinational AIG with no property/constraint extensions')
    maximum, inputs, latches, outputs, ands = map(int, tokens[1:])
    require(inputs == sum(expected.values()) and latches == 0 and outputs == 1 and maximum == inputs+ands,
            'AIG input/latch/output/variable census differs')
    output, rest = rest.split(b'\n', 1)
    require(output.isdigit() and int(output) <= 2*maximum+1, 'Invalid AIG output literal')
    offset = 0
    for index in range(ands):
        deltas = []
        for _ in range(2):
            value = shift = 0
            while True:
                require(offset < len(rest) and shift <= 63, 'Truncated/overflow AIG delta')
                byte = rest[offset]; offset += 1; value |= (byte & 127) << shift
                if byte < 128: break
                shift += 7
            deltas.append(value)
        lhs = 2*(inputs+index+1); first = lhs-deltas[0]; second = first-deltas[1]
        require(0 <= second <= first < lhs, 'Non-topological AIG edge')
    symbols = rest[offset:].decode('ascii').split('\nc\n', 1)
    require(len(symbols) == 2, 'Missing AIG symbol/comment boundary')
    found = {}
    for line in symbols[0].splitlines():
        key, name = line.split(' ', 1); require(key not in found, 'Duplicate AIG symbol'); found[key] = name
    wanted = {f'i{i}': n if expected[n] == 1 else f'{n}[{b}]' for i, n, b in mapping}; wanted['o0'] = 'bad'
    require(found == wanted, 'AIG symbols differ from exact original port map')
    return dict(header=header.decode(), original_inputs=inputs, and_nodes=ands, output_literal=int(output),
                no_latches_or_constraints=True)


def validate_export(directory, expected):
    module = json.loads((directory/'interface.json').read_text())['modules']
    require(set(module) == {'observation'}, 'Residual hierarchy in native interface'); module = module['observation']
    ports = module['ports']; require(set(ports) == set(expected)|{'bad'}, 'Native interface ports changed')
    require(ports['bad']['direction'] == 'output' and len(ports['bad']['bits']) == 1, 'Native bad output changed')
    ids = []
    for name, width in expected.items():
        port = ports[name]
        require(port['direction'] == 'input' and len(port['bits']) == width and port.get('offset', 0) == 0
            and port.get('upto', 0) == 0 and all(type(b) is int for b in port['bits']), 'Changed native input bits')
        ids += port['bits']
    require(len(set(ids)) == len(ids), 'Aliased independent original inputs')
    for cell in module.get('cells', {}).values():
        require(cell['type'] in {'$_AND_', '$_NOT_'}, 'State, assumption, assertion or unsupported cell in AIG')
        for bits in cell['connections'].values():
            require(all(type(b) is int or b in ('0', '1') for b in bits), 'Undefined native logic value')
    # OPT may retain x on unused debug netname slices; only ports/cell connections are functional.
    require(all(type(b) is int or b in ('0', '1') for b in ports['bad']['bits']), 'Undefined functional output')
    constant = ports['bad']['bits'][0] if ports['bad']['bits'][0] in ('0', '1') else None
    mapping = parse_map((directory/'ports.map').read_text(), expected, constant_output=constant is not None)
    result = validate_aiger((directory/'miter.aig').read_bytes(), mapping, expected)
    require(constant is None or result['output_literal'] == int(constant), 'Native constant output differs from AIG literal')
    result['constant_output'] = constant
    aliases = [v['bits'] for v in module.get('netnames', {}).values() if any(b in ('x', 'z') for b in v['bits'])]
    result.update(files={n: pin(directory/n) for n in ('observe.v', 'interface.json', 'ports.map', 'miter.aig')},
                  symbolic_inputs=expected, native_cells=len(module.get('cells', {})),
                  metadata_only_undefined_aliases=len(aliases),
                  metadata_only_undefined_alias_bits=sum(b in ('x', 'z') for bits in aliases for b in bits))
    return result


def abc_command(runtime, graph, cex, seconds):
    require(type(seconds) is int and 1 <= seconds <= 120, 'Unbounded native CEC budget')
    # No named CEX export: the exact runtime aborts after nontrivial CEC decomposition.
    require(all(re.fullmatch(r'[A-Za-z0-9_./-]+', str(p)) for p in (graph, cex)), 'Unsafe ABC path')
    return [str(runtime), 'yosys-abc', '-c',
            f'read_aiger {graph}; &get -n; &cec -m -T {seconds} -v; write_cex {cex}']


def abc_verdict(text, returncode):
    require(returncode == 0 and not re.search(r'(?im)^.*(?:assertion .*failed|error:|cannot open|read error)', text),
            'Native ABC failed; no verdict accepted')
    events = re.findall(r'^Networks are (equivalent\.|NOT EQUIVALENT\.|UNDECIDED[^\n]*|undecided[^\n]*)', text, re.M)
    require(events, 'Missing native terminal verdict')
    positive = [x for x in events if x == 'equivalent.']; negative = [x for x in events if x == 'NOT EQUIVALENT.']
    require(len(positive) <= 1 and len(negative) <= 1 and not (positive and negative), 'Conflicting native verdicts')
    if positive: require(events[-1] == 'equivalent.', 'No final resolved equivalent verdict'); return PASS
    if negative: require(events[-1] == 'NOT EQUIVALENT.', 'No final resolved negative verdict'); return CEX
    return 'TIMEOUT_UNPROVED' if re.search(r'(?i)time.?out|time limit', text) else OPEN


def counterexample_values(text, mapping, expected):
    match = re.fullmatch(r'\s*([01]+)\s*# DONE\s*', text)
    require(match is not None and len(match[1]) == sum(expected.values()), 'Incomplete/nonbinary native CEX')
    require([i for i, _, _ in mapping] == list(range(len(match[1]))), 'CEX map changed')
    require({(n, b) for _, n, b in mapping} == {(n, b) for n, w in expected.items() for b in range(w)},
            'CEX map omits or substitutes an original input')
    values = {n: 0 for n in expected}
    for (_, name, bit), digit in zip(mapping, match[1], strict=True): values[name] |= int(digit) << bit
    return values


def replay_script(source, observation, values, expected, output, *, tiny=False):
    require(set(values) == set(expected) and all(type(v) is int and 0 <= v < 2**expected[n]
        for n, v in values.items()), 'Incomplete original-input replay assignment')
    lines = ([f'read_verilog {state.quoted(observation)}'] if tiny else
        [f'read_rtlil {state.quoted(source)}', 'rename miter nssoc_preserved_miter',
         f'read_verilog {state.quoted(observation)}'])
    lines += ['prep -top observation -flatten', 'check -assert']
    assignments = ' '.join(f'-set {n} {expected[n]}\'h{values[n]:x}' for n in expected)
    lines.append(f'sat -prove bad 0 {assignments} -show-inputs -show-outputs -dump_json {state.quoted(output/"original-cex.json")}')
    return '\n'.join(lines)+'\n'


def solve(runtime, export, source, output, expected, *, seconds=120, memory=6*1024**3, tiny=False):
    census = validate_export(export, expected)
    ex = execute(abc_command(runtime, export/'miter.aig', output/'counterexample.txt', seconds), output, 'abc', memory)
    verdict = abc_verdict((output/'abc.log').read_text(), ex['returncode'])
    result = dict(verdict=verdict, execution=ex, export=census)
    if verdict == CEX:
        mapping = parse_map((export/'ports.map').read_text(), expected, constant_output=census['constant_output'] is not None)
        values = counterexample_values((output/'counterexample.txt').read_text(), mapping, expected)
        script = output/'replay.ys'; script.write_text(replay_script(source, export/'observe.v', values, expected, output, tiny=tiny))
        replay = execute([runtime, 'yosys', '-Q', '-T', '-s', script], output, 'replay', memory)
        require(replay['returncode'] == 0 and 'SAT proof finished - model found: FAIL!' in (output/'replay.log').read_text(),
                'Native ABC counterexample did not reproduce on original equation')
        witness = json.loads((output/'original-cex.json').read_text())
        bad = [x for x in witness['signal'] if x['name'] == 'bad']
        require(len(bad) == 1 and bad[0]['wave'].startswith('1'), 'Original witness does not show bad=1')
        result.update(counterexample=pin(output/'counterexample.txt'), assignments=values, replay=replay,
                      original_witness=pin(output/'original-cex.json'), replay_script=pin(script))
    else:
        require(not (output/'counterexample.txt').exists() or not (output/'counterexample.txt').read_text().strip(),
                'Unexpected native counterexample with nonnegative verdict')
    require(validate_export(export, expected) == census, 'Export changed during native solve')
    return result


def verify_solve(directory, export, native_export, native_output, runtime, proof, expected, source,
                 *, seconds=120, memory=6*1024**3, tiny=False):
    ex = json.loads((directory/'abc-execution.json').read_text())
    require(ex == proof['execution'] and ex['memory_limit_bytes'] == memory
        and ex['command'] == abc_command(runtime, native_export/'miter.aig', native_output/'counterexample.txt', seconds)
        and pin(directory/'abc.log') == ex['log'] and proof['export'] == validate_export(export, expected)
        and abc_verdict((directory/'abc.log').read_text(), ex['returncode']) == proof['verdict'], 'Native ABC record changed')
    if proof['verdict'] == CEX:
        values = counterexample_values((directory/'counterexample.txt').read_text(),
            parse_map((export/'ports.map').read_text(), expected,
                      constant_output=proof['export']['constant_output'] is not None), expected)
        script = replay_script(source, native_export/'observe.v', values, expected, native_output, tiny=tiny)
        replay = json.loads((directory/'replay-execution.json').read_text())
        require(values == proof['assignments'] and (directory/'replay.ys').read_text() == script
            and pin(directory/'replay.ys') == proof['replay_script'] and pin(directory/'counterexample.txt') == proof['counterexample']
            and replay == proof['replay'] and replay['returncode'] == 0 and replay['memory_limit_bytes'] == memory
            and replay['command'] == list(map(str, [runtime, 'yosys', '-Q', '-T', '-s', native_output/'replay.ys']))
            and pin(directory/'replay.log') == replay['log']
            and 'SAT proof finished - model found: FAIL!' in (directory/'replay.log').read_text()
            and pin(directory/'original-cex.json') == proof['original_witness'], 'Original CEX replay changed')
        bad = [x for x in json.loads((directory/'original-cex.json').read_text())['signal'] if x['name'] == 'bad']
        require(len(bad) == 1 and bad[0]['wave'].startswith('1'), 'Missing original bad=1 witness')
    else:
        require(not (directory/'counterexample.txt').exists() or not (directory/'counterexample.txt').read_text().strip(),
                'Unexpected captured CEX with nonnegative verdict')


def verify_controls(directory, captured, runtime):
    require(captured == json.loads((directory/'result.json').read_text()) and set(captured) == {'equal', 'wrong_output'},
            'Changed native controls')
    expected = dict(lhs=8, rhs=8, carry=1, spare=1)
    for name, wrong in [('equal', False), ('wrong_output', True)]:
        d = directory/name; proof = captured[name]; execution = proof['export_execution']
        native = Path(execution['command'][-1]).parent
        require(native.is_absolute() and execution == json.loads((d/'export-execution.json').read_text())
            and execution['returncode'] == 0 and execution['memory_limit_bytes'] == 2*1024**3
            and execution['command'] == list(map(str, [runtime, 'yosys', '-Q', '-T', '-s', native/'export.ys']))
            and pin(d/'export.log') == execution['log'] and (d/'observe.v').read_text() == arithmetic_control(wrong),
            'Tiny control source or native export changed')
        script = '\n'.join([f'read_verilog {state.quoted(native/"observe.v")}',
            'prep -top observation -flatten', *export_commands(native)])+'\n'
        require((d/'export.ys').read_text() == script and proof['verdict'] == (CEX if wrong else PASS)
            and proof['export']['and_nodes'] > 10, 'Tiny export or expected result changed')
        verify_solve(d, d, native, native, runtime, proof, expected, None, seconds=10, memory=2*1024**3, tiny=True)
    return captured


def arithmetic_control(wrong=False):
    lines = ['module observation(input [7:0] lhs,rhs,input carry,spare,output bad);',
             'wire [8:0] rcarry,pcarry,ripple,prefix; wire [7:0] p,g;',
             'assign p=lhs^rhs; assign g=lhs&rhs; assign rcarry[0]=carry; assign pcarry[0]=carry;']
    for i in range(8):
        lines += [f'assign rcarry[{i+1}]=g[{i}]|(p[{i}]&rcarry[{i}]);', f'assign ripple[{i}]=p[{i}]^rcarry[{i}];']
        terms = [' & '.join([f'p[{j}]' for j in range(i, k, -1)]+[f'g[{k}]']) for k in range(i, -1, -1)]
        terms.append(' & '.join([f'p[{j}]' for j in range(i, -1, -1)]+['carry']))
        lines.append(f'assign pcarry[{i+1}]='+' | '.join('('+t+')' for t in terms)+';')
        lines.append(f'assign prefix[{i}]=p[{i}]^pcarry[{i}]'+(' ^ (lhs[6]&rhs[2])' if wrong and i == 3 else '')+';')
    return '\n'.join(lines+['assign ripple[8]=rcarry[8]; assign prefix[8]=pcarry[8]; assign bad=|(ripple^prefix); endmodule', ''])


def controls(runtime, output):
    output.mkdir(); expected = dict(lhs=8, rhs=8, carry=1, spare=1); result = {}
    for name, wrong in [('equal', False), ('wrong_output', True)]:
        directory = output/name; directory.mkdir(); (directory/'observe.v').write_text(arithmetic_control(wrong))
        script = directory/'export.ys'; script.write_text('\n'.join([
            f'read_verilog {state.quoted(directory/"observe.v")}', 'prep -top observation -flatten',
            *export_commands(directory)])+'\n')
        ex = execute([runtime, 'yosys', '-Q', '-T', '-s', script], directory, 'export', 2*1024**3)
        require(ex['returncode'] == 0, 'Tiny native export failed')
        result[name] = solve(runtime, directory, None, directory, expected, seconds=10, memory=2*1024**3, tiny=True)
        require(result[name]['verdict'] == (CEX if wrong else PASS) and result[name]['export']['and_nodes'] > 10,
                'Nontrivial native control failed')
        result[name]['export_execution'] = ex
    save(output/'result.json', result)
    return result


def prepare(output, work):
    require(os.environ.get('GITHUB_ACTIONS') == 'true', 'Full graph preparation is cloud-only')
    output = state.common.fresh_directory(output); work = state.common.fresh_directory(work)
    row = dict(status='PREPARING_HARD_BITS', github_source_commit=os.environ.get('GITHUB_SHA'),
               candidate_adopted=False, state_bijection_proved=False, unresolved_four_state_boot_failure=True)
    try:
        locked = load_lock(); row['methods'] = snapshot(output, locked)
        remaining.prepare(output/'prerequisites', work/'prerequisites')
        prior, refined, value, _ = remaining.verify_prepared(output/'prerequisites')
        row['prior_result'] = pin(output/'prerequisites/result.json'); selected = hard_selection(value, refined)
        runtime = work/'prerequisites/runtime.AppImage'; row['runtime'] = locked['runtime']
        row['native_identity'] = native_identity(runtime, output, locked)
        row['controls'] = controls(runtime, output/'controls')
        source = output/'prerequisites/prior/common/common-miter.il'; state.common.verify_file(source, locked['refined_miter'])
        exports = []
        for index, item in enumerate(selected):
            directory = output/'exports'/str(index); directory.mkdir(parents=True)
            (directory/'observe.v').write_text(wrapper(refined, item)); exports.append(directory)
        script = output/'export.ys'; script.write_text(export_script(source, exports))
        ex = execute([runtime, 'yosys', '-Q', '-T', '-s', script], output, 'export', locked['memory_bytes'])
        require(ex['returncode'] == 0, 'Full native four-bit export failed')
        expected = {'in_'+n: w for n, w in refined['symbolic_inputs'].items()}
        row.update(exports={str(i): validate_export(d, expected) for i, d in enumerate(exports)}, export_execution=ex,
                   hard_bits=selected, symbolic_inputs=expected, native_paths=dict(output=str(output), work=str(work)),
                   source_graph=locked['refined_miter'])
        require(remaining.verify_prepared(output/'prerequisites')[0] == prior, 'Prerequisite source changed during export')
        state.common.verify_file(source, locked['refined_miter']); state.common.verify_file(runtime, locked['runtime'])
        verify_methods(output, row['methods'], locked)
        row.update(status='FOUR_HARD_BIT_EXPORTS_PREPARED', complete_inputs_rechecked=True)
    except BaseException as error:
        row.update(status='PREPARATION_FAILED_PRESERVED', error=repr(error)); raise
    finally:
        row['outputs'] = ref.inventory(output); save(output/'result.json', row)
    return row


def verify_prepared(bundle):
    locked = load_lock(); row = json.loads((bundle/'result.json').read_text())
    require(row['status'] == 'FOUR_HARD_BIT_EXPORTS_PREPARED' and row['complete_inputs_rechecked'] is True
        and row['github_source_commit'] == os.environ.get('GITHUB_SHA') and row['runtime'] == locked['runtime']
        and row['source_graph'] == locked['refined_miter'] and row['candidate_adopted'] is False
        and row['state_bijection_proved'] is False and row['unresolved_four_state_boot_failure'] is True,
        'Incomplete/foreign hard-bit preparation')
    part.verify_inventory(bundle, row['outputs']); verify_methods(bundle, row['methods'], locked)
    _, refined, value, _ = remaining.verify_prepared(bundle/'prerequisites')
    require(pin(bundle/'prerequisites/result.json') == row['prior_result']
        and row['hard_bits'] == hard_selection(value, refined), 'Original hard-bit provenance changed')
    paths = {k: Path(v) for k, v in row['native_paths'].items()}
    require(set(paths) == {'output', 'work'} and all(x.is_absolute() for x in paths.values()), 'Missing native prepare paths')
    runtime = paths['work']/'prerequisites/runtime.AppImage'
    execution = json.loads((bundle/'export-execution.json').read_text())
    require(execution == row['export_execution'] and execution['returncode'] == 0
        and execution['memory_limit_bytes'] == locked['memory_bytes']
        and execution['command'] == list(map(str, [runtime, 'yosys', '-Q', '-T', '-s', paths['output']/'export.ys']))
        and pin(bundle/'export.log') == execution['log']
        and (bundle/'export.ys').read_text() == export_script(paths['output']/'prerequisites/prior/common/common-miter.il',
            [paths['output']/'exports'/str(i) for i in range(4)]), 'Native original-source export changed')
    require(row['native_identity']['binaries'] == {'yosys': locked['native_yosys'], 'yosys-abc': locked['native_abc']}
        and json.loads((bundle/'native-identity.log').read_text()) == row['native_identity']
        and (bundle/'native-identity.py').read_text() == native_identity_script(), 'Changed native binaries')
    identity_execution = json.loads((bundle/'native-identity-execution.json').read_text())
    require(identity_execution['returncode'] == 0 and identity_execution['memory_limit_bytes'] == 2*1024**3
        and identity_execution['command'] == list(map(str, [runtime, 'python', paths['output']/'native-identity.py']))
        and identity_execution['log'] == pin(bundle/'native-identity.log'), 'Changed native launcher binding query')
    verify_controls(bundle/'controls', row['controls'], runtime)
    expected = {'in_'+n: w for n, w in refined['symbolic_inputs'].items()}
    require(row['symbolic_inputs'] == expected and sum(expected.values()) == 10828, 'Changed full input boundary')
    for i, item in enumerate(row['hard_bits']):
        d = bundle/'exports'/str(i)
        require((d/'observe.v').read_text() == wrapper(refined, item) and validate_export(d, expected) == row['exports'][str(i)],
                'Changed derived graph or observation')
    return row, locked


def run_bit(bundle, index, output):
    require(os.environ.get('GITHUB_ACTIONS') == 'true', 'Actual hard-bit proof is cloud-only')
    require(type(index) is int and 0 <= index < 4, 'Invalid hard-bit index')
    output = state.common.fresh_directory(output)
    row = dict(status='PREPARING_HARD_BIT', index=index, github_source_commit=os.environ.get('GITHUB_SHA'),
               candidate_adopted=False, state_bijection_proved=False, unresolved_four_state_boot_failure=True)
    try:
        prepared, locked = verify_prepared(bundle)
        runtime = Path(prepared['native_paths']['work'])/'prerequisites/runtime.AppImage'
        state.common.verify_file(runtime, locked['runtime'])
        row.update(original=prepared['hard_bits'][index], prepared_result=pin(bundle/'result.json'),
                   source_graph=prepared['source_graph'], methods=prepared['methods'], runtime=locked['runtime'],
                   native_paths=dict(bundle=str(bundle), output=str(output)))
        save(output/'result.json', row)
        source = bundle/'prerequisites/prior/common/common-miter.il'
        row['proof'] = solve(runtime, bundle/'exports'/str(index), source, output, prepared['symbolic_inputs'])
        require(verify_prepared(bundle)[0] == prepared, 'Prepared inputs changed during native proof')
        state.common.verify_file(runtime, locked['runtime'])
        row.update(status='HARD_BIT_NATIVE_RESULT_CAPTURED', complete_inputs_rechecked=True)
    except BaseException as error:
        row.update(status='HARD_BIT_FAILED_OR_INCOMPLETE', error=repr(error)); raise
    finally:
        row['outputs'] = ref.inventory(output); save(output/'result.json', row)
    return row


def replay_result(directory, prepared, expected_prepared, bundle):
    row = json.loads((directory/'result.json').read_text()); index = row['index']
    require(type(index) is int and 0 <= index < 4 and row['status'] == 'HARD_BIT_NATIVE_RESULT_CAPTURED'
        and row['complete_inputs_rechecked'] is True and row['github_source_commit'] == prepared['github_source_commit']
        and row['original'] == prepared['hard_bits'][index] and row['source_graph'] == prepared['source_graph']
        and row['methods'] == prepared['methods'] and row['prepared_result'] == expected_prepared
        and row['runtime'] == prepared['runtime'] and row['candidate_adopted'] is False
        and row['state_bijection_proved'] is False and row['unresolved_four_state_boot_failure'] is True,
        'Incomplete/foreign hard-bit result')
    part.verify_inventory(directory, row['outputs']); proof = row['proof']
    native = {k: Path(v) for k, v in row['native_paths'].items()}
    require(set(native) == {'bundle', 'output'} and all(p.is_absolute() for p in native.values())
        and native['bundle'] == Path(prepared['native_paths']['output']), 'Missing/foreign native path binding')
    runtime = Path(prepared['native_paths']['work'])/'prerequisites/runtime.AppImage'
    export = native['bundle']/'exports'/str(index)
    require(proof['export'] == prepared['exports'][str(index)], 'Foreign derived AIG')
    verify_solve(directory, bundle/'exports'/str(index), export, native['output'], runtime, proof,
        prepared['symbolic_inputs'], native['bundle']/'prerequisites/prior/common/common-miter.il')
    return row


def merge(rows):
    require(len(rows) == 4 and {r['index'] for r in rows} == set(range(4))
        and {tuple(r['original']['original']) for r in rows} == set(HARD), 'Missing/duplicate/foreign hard result')
    verdicts = [r['proof']['verdict'] for r in rows]
    require(all(v in {PASS, CEX, OPEN, 'TIMEOUT_UNPROVED'} for v in verdicts), 'Unknown hard verdict')
    count = verdicts.count(PASS)
    return dict(status='FOUR_HARD_EQUATIONS_VISITED', hard_bits=4, new_proved=count,
        counterexamples=verdicts.count(CEX), timeouts=verdicts.count('TIMEOUT_UNPROVED'), undecided=verdicts.count(OPEN),
        preserved_proved=33517, known_proved_without_pending800=33517+count,
        pending800_results_not_merged=True, original_total=34321, remaining_without_pending800=804-count,
        symbolic_input_bits=10828, state_bijection_proved=False, candidate_adopted=False,
        unresolved_four_state_boot_failure=True, full_soc_functional_accepted=False, timing_accepted=False,
        manufacturing_approval=False, bits=sorted(rows, key=lambda x: x['index']))


def aggregate(bundle, directories, output):
    row = dict(status='INCOMPLETE_OR_FAILED_HARD_BIT_REPLAY', state_bijection_proved=False, candidate_adopted=False)
    try:
        prepared, _ = verify_prepared(bundle); expected = pin(bundle/'result.json')
        require(len(directories) == 4, 'Not all four hard-bit captures exist')
        row = merge([replay_result(d, prepared, expected, bundle) for d in directories])
        row.update(prepared_result=expected, github_source_commit=prepared['github_source_commit'])
    except BaseException as error:
        row['error'] = repr(error); save(output, row); raise
    save(output, row)
    require(row['counterexamples'] == 0, 'Actual original-equation counterexample preserved')
    return row


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('phase', choices=['prepare', 'bit', 'aggregate', 'controls'])
    p.add_argument('--output', type=Path, required=True); p.add_argument('--work', type=Path)
    p.add_argument('--bundle', type=Path); p.add_argument('--index', type=int); p.add_argument('--bit-root', type=Path)
    p.add_argument('--runtime', type=Path); args = p.parse_args()
    if args.phase == 'prepare': row = prepare(args.output.resolve(), args.work.resolve())
    elif args.phase == 'bit': row = run_bit(args.bundle.resolve(), args.index, args.output.resolve())
    elif args.phase == 'aggregate':
        directories = sorted(x.parent for x in args.bit_root.rglob('result.json') if re.fullmatch(r'hard-bit-[0-3]', x.parent.name))
        row = aggregate(args.bundle.resolve(), directories, args.output.resolve())
    else: row = controls(args.runtime.resolve(), args.output.resolve())
    print(row.get('status', 'PASS_NONTRIVIAL_NATIVE_CONTROLS'), flush=True)


if __name__ == '__main__': main()
