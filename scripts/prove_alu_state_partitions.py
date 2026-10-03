#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exhaustive independent binary output equations from one immutable miter.

Partitioning changes which outputs are observed, never the symbolic inputs or
internal equations. No assumed cutpoints, reachable-state restrictions, RTL
resynthesis, or physical/adoption claims are introduced.
"""
import argparse
import copy
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import time
import zipfile

import prove_alu_state_repair as correction

state = correction.state
replay = correction.replay
ROOT = Path(__file__).resolve().parents[1]
PREFIX = '__nssoc_obligation_'
WIDTH = 128
SHARDS = 4
TIMEOUT = 120
OWN = ('scripts/prove_alu_state_partitions.py', 'sw/tests/test_alu_state_partitions.py',
       '.github/workflows/timing-alu-state-partitions.yml')
PINS = {**state.METHOD_PINS,
    'scripts/prove_alu_mapped_state.py': replay.STATE_METHOD,
    'scripts/replay_alu_state_counterexample.py': correction.REPLAY_SHA,
    'scripts/prove_alu_state_repair.py': 'd44cb8d809c1d9649b0c33435e41a044d3610044316f16701027d612abfaeea5'}
TIMEOUT_RUN = 37009833162
TIMEOUT_COMMIT = 'ad5f555cbffe33666d1b7356c74323e16251d79f'
TIMEOUT_ARTIFACT = 11227859633
TIMEOUT_ZIP = dict(bytes=3899723, sha256='790a403c5707227bb4442b097894667b2908d9102e80cacd7c30bb3e94460c59')
TIMEOUT_URL = 'https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20260927-chip-io/closure-alu-state-timeout-37009833162-20261002.zip'
TIMEOUT_MEMBERS = {
    'result.json': dict(bytes=13334, sha256='b8e639f574b89abf45d17098a0d75e0ffdfbb2938a2a4d82e0c58f9f3e8970f0'),
    'corrected-candidate-lifted.json': dict(bytes=62840132, sha256='59ac19437b4f0e1fd8a8c2a54d20c16377d8efe9bb7aacdf8fd44a404db156c8'),
    'corrected-candidate-obligations.json': dict(bytes=1089942, sha256='5aa0a5cb8bb1259e2d3aa86dd280696d7888e42d4f311198f89a32bf59eb4247'),
    'corrected-state-proposal.json': dict(bytes=481475, sha256='70ef71091387a6c358c0c73302288ab2c05d2a37b1a631e489d90400044c179f'),
    'corrected-miter.log': dict(bytes=57074, sha256='9dd7ebecf5d0cb1546143f04d6a0dbb1d056388aaf306fc185e4220ea37e97e6'),
}


def make_plan(left, right, width=WIDTH):
    state.require(type(width) is int and width > 0, 'Invalid partition width')
    inputs = {n: len(p['bits']) for n, p in left['ports'].items() if p['direction'] == 'input'}
    outputs = {n: len(p['bits']) for n, p in left['ports'].items() if p['direction'] == 'output'}
    state.require(inputs == {n: len(p['bits']) for n, p in right['ports'].items() if p['direction'] == 'input'}
                  and outputs == {n: len(p['bits']) for n, p in right['ports'].items() if p['direction'] == 'output'},
                  'Original lifted interfaces differ')
    state.require(not any(n.startswith(PREFIX) for n in left['ports'] | right['ports']), 'Partition namespace collision')
    obligations = [[name, bit] for name in sorted(outputs) for bit in range(outputs[name])]
    groups = [dict(id=f'{PREFIX}{i//width:04d}', obligations=obligations[i:i+width], shard=(i//width) % SHARDS)
              for i in range(0, len(obligations), width)]
    plan = dict(schema=1, symbolic_inputs=inputs, output_widths=outputs, symbolic_input_bits=sum(inputs.values()),
                total_output_bits=len(obligations), chunk_width=width, shards=SHARDS, groups=groups)
    validate_plan(plan)
    return plan


def validate_plan(plan):
    expected = [(n, i) for n in sorted(plan['output_widths']) for i in range(plan['output_widths'][n])]
    seen = []; ids = set()
    state.require(plan['schema'] == 1 and plan['shards'] == SHARDS and plan['groups'], 'Unsupported/empty partition plan')
    state.require(plan['symbolic_input_bits'] == sum(plan['symbolic_inputs'].values()), 'Input census differs')
    for index, group in enumerate(plan['groups']):
        state.require(group['id'] == f'{PREFIX}{index:04d}' and group['id'] not in ids
                      and group['shard'] == index % SHARDS, 'Invalid/duplicate partition identity')
        ids.add(group['id'])
        state.require(0 < len(group['obligations']) <= plan['chunk_width'], 'Empty or oversized partition')
        seen.extend(tuple(x) for x in group['obligations'])
    state.require(seen == expected and len(set(seen)) == len(expected) == plan['total_output_bits'],
                  'Partition obligations missing, duplicated, reordered or extra')
    return plan


def alias_outputs(module, plan):
    validate_plan(plan)
    result = copy.deepcopy(module)
    for group in plan['groups']:
        state.require(group['id'] not in module['ports'], 'Existing group output')
        result['ports'][group['id']] = dict(direction='output', bits=[module['ports'][n]['bits'][i]
                                                                   for n, i in group['obligations']])
    stripped = copy.deepcopy(result)
    for group in plan['groups']: del stripped['ports'][group['id']]
    state.require(stripped == module, 'Alias wrappers changed source graph or original boundary')
    return result


def build_script(left, right, library, output_il, interface):
    script = state.miter_script(left, right, library, output_il.with_suffix('.unused'))
    script = script[:script.index('sat -verify ')]
    script = script.replace('miter -equiv -flatten gold gate miter',
                            'miter -equiv -make_outputs -make_outcmp -flatten gold gate miter')
    return script + f'write_rtlil {state.quoted(output_il)}\nwrite_json {state.quoted(interface)}\n'


def validate_interface(module, plan):
    actual = {n: len(p['bits']) for n, p in module['ports'].items() if p['direction'] == 'input'}
    expected = {'in_'+n: w for n, w in plan['symbolic_inputs'].items()}
    state.require(actual == expected, 'Compiled common miter changed symbolic inputs')
    for group in plan['groups']:
        for prefix, width in [('cmp_', 1), ('gold_', len(group['obligations'])), ('gate_', len(group['obligations']))]:
            p = module['ports'][prefix+group['id']]
            state.require(p['direction'] == 'output' and len(p['bits']) == width, 'Compiled group comparator boundary differs')
    return dict(symbolic_inputs=actual, symbolic_input_bits=sum(actual.values()),
                module_cells=len(module['cells']), native_groups=len(plan['groups']))


def tcl_command(command):
    state.require(not any(x in command for x in '{}\r\n'), 'Unsafe generated Tcl command')
    return 'yosys {'+command+'}'


def shard_script(common_il, plan, shard, directory, timeout=TIMEOUT):
    validate_plan(plan)
    state.require(type(shard) is int and 0 <= shard < SHARDS, 'Invalid shard')
    groups = [g for g in plan['groups'] if g['shard'] == shard]
    state.require(groups, 'Empty shard')
    lines = [tcl_command('read_rtlil '+state.quoted(common_il)), tcl_command('design -save full_miter')]
    for group in groups:
        name = group['id']; selected = [prefix+name for prefix in ('cmp_', 'gold_', 'gate_')]
        lines += [tcl_command(f'log NSSOC_GROUP_BEGIN {name}'), tcl_command('design -load full_miter'),
                  tcl_command('select -module miter'),
                  tcl_command('delete -output o:* '+ ' '.join('w:'+n+' %d' for n in selected)),
                  tcl_command('opt_clean -purge'), tcl_command('select -assert-count 3 o:*'),
                  tcl_command('select -assert-count '+str(len(plan['symbolic_inputs']))+' i:*')]
        for selected_name in selected:
            lines.append(tcl_command('select -assert-count 1 o:'+selected_name))
        for input_name in plan['symbolic_inputs']:
            state.require(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', input_name), 'Unsafe input name')
            lines.append(tcl_command('select -assert-count 1 i:in_'+input_name))
        lines += [tcl_command('select -module miter'), tcl_command('check -assert'), tcl_command('stat')]
        # Without -verify, a negative/timeout result does not abort the process
        # before later independent groups run. Raw native verdicts are mandatory
        # below; traversal success alone can never establish equivalence.
        cmd = (f'sat -prove cmp_{name} 1 -show-inputs -show-outputs -timeout {timeout} '
               f'-dump_json {state.quoted(directory/(name+".json"))} -dump_vcd {state.quoted(directory/(name+".vcd"))}')
        state.require(' -set ' not in cmd and '-assumes' not in cmd, 'Partition introduced assumptions')
        lines += ['set code [catch {'+tcl_command(cmd)+'} message]',
                  f'yosys log NSSOC_GROUP_END {name} $code']
    lines += [tcl_command('log NSSOC_ALL_ASSIGNED_GROUPS_VISITED'), '']
    return '\n'.join(lines)


def parse_shard(text, plan, shard, output, *, write_logs=True):
    expected = [g for g in validate_plan(plan)['groups'] if g['shard'] == shard]
    matches = list(re.finditer(r'^NSSOC_GROUP_BEGIN (\S+)\n(.*?)^NSSOC_GROUP_END (\S+) ([01])$', text, re.M | re.S))
    state.require([m[1] for m in matches] == [g['id'] for g in expected]
                  and all(m[1] == m[3] for m in matches)
                  and text.count('NSSOC_ALL_ASSIGNED_GROUPS_VISITED') == 1, 'Incomplete/duplicated native group execution')
    results = []
    for match, group in zip(matches, expected):
        block, code = match[2], int(match[4])
        state.require(re.findall(r'^Final constraint equation:.*$', block, re.M) == ['Final constraint equation: { } = { }'],
                      'Native group has missing/extra constraints')
        state.require(code == 0, 'Native group command failed')
        passed = block.count('SAT proof finished - no model found: SUCCESS!')
        failed = block.count('SAT proof finished - model found: FAIL!')
        if 'Interrupted SAT solver: TIMEOUT!' in block:
            state.require(passed == failed == 0, 'Conflicting timeout verdict')
            verdict = 'TIMEOUT_UNPROVED'
        elif passed == 1 and failed == 0:
            verdict = 'PROVED_ALL_BINARY_BOUNDARY_EQUATIONS'
        elif failed == 1 and passed == 0:
            verdict = 'COUNTEREXAMPLE_PRESERVED'
        else:
            raise ValueError('Native group proof incomplete or conflicting')
        if verdict == 'COUNTEREXAMPLE_PRESERVED':
            state.require((output/(group['id']+'.json')).is_file() and (output/(group['id']+'.vcd')).is_file(),
                          'Missing group counterexample')
        group_log = output/(group['id']+'.log')
        if write_logs:
            group_log.write_text(block)
        else:
            state.require(group_log.read_text() == block, 'Captured group log differs from full native log')
        results.append(dict(id=group['id'], shard=shard, bits=len(group['obligations']), verdict=verdict,
                            native_returncode=code, log=state.archived.pin(output/(group['id']+'.log'))))
    return results


def aggregate(plan, records):
    validate_plan(plan)
    state.require(len(records) == SHARDS and {r['shard'] for r in records} == set(range(SHARDS)), 'Missing/duplicate shard')
    results = [g for row in records for g in row['groups']]
    by_id = {g['id']: g for g in results}
    state.require(len(by_id) == len(results) == len(plan['groups'])
                  and set(by_id) == {g['id'] for g in plan['groups']}, 'Missing/duplicate group result')
    for group in plan['groups']:
        row = by_id[group['id']]
        state.require(row['bits'] == len(group['obligations']) and row['shard'] == group['shard'], 'Wrong group ownership/coverage')
    proven = all(g['verdict'] == 'PROVED_ALL_BINARY_BOUNDARY_EQUATIONS' and g['native_returncode'] == 0 for g in results)
    return dict(status='PROVED_ALL_PARTITIONED_BINARY_BOUNDARY_EQUATIONS' if proven else 'INCOMPLETE_OR_COUNTEREXAMPLE_PRESERVED',
        state_bijection_proved=proven, complete_groups=len(results), proved_groups=sum(g['verdict']=='PROVED_ALL_BINARY_BOUNDARY_EQUATIONS' for g in results),
        complete_output_obligation_bits=sum(g['bits'] for g in results), symbolic_input_bits=plan['symbolic_input_bits'],
        no_internal_assumptions=True, original_failed_proof_preserved=True, monolithic_timeout_preserved=True,
        candidate_adopted=False, full_soc_functional_accepted=False, timing_accepted=False, manufacturing_approval=False)


def execute_tcl(runtime, script, output, name):
    command = [str(runtime), 'yosys', '-Q', '-T', '-c', str(script)]
    started = time.monotonic()
    def limit():
        resource.setrlimit(resource.RLIMIT_AS, (6*1024**3,)*2)
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    with (output/(name+'.log')).open('x') as log:
        child = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=False,
                               preexec_fn=limit)
    row = dict(command=command, returncode=child.returncode, seconds=time.monotonic()-started,
               script=state.archived.pin(script), log=state.archived.pin(output/(name+'.log')))
    state.common.save(output/(name+'-execution.json'), row)
    return row


def controls(runtime, library, output):
    left, _ = state.lift(state.fixture(), ['ff0', 'ff1'])
    wrong = copy.deepcopy(left); wrong['ports']['output_q']['bits'][0] = '0'
    wrong_clock = copy.deepcopy(left); wrong_clock['ports'][state.PREFIX+'ff_clk']['bits'][0] = '0'
    results = {}
    for case, right in [('equal', left), ('wrong_output', wrong), ('wrong_clock_then_continue', wrong_clock)]:
        out = output/case; out.mkdir()
        plan = make_plan(left, right, 2)
        # At least one chunk per shard in this tiny complete boundary fixture.
        for tag, module in [('left', left), ('right', right)]:
            state.common.save(out/(tag+'.json'), {'modules': {'soc_top': alias_outputs(module, plan)}})
        common_il = out/'common.il'; interface = out/'common.json'; script = out/'build.ys'
        script.write_text(build_script(out/'left.json', out/'right.json', library, common_il, interface))
        execution = state.execute(runtime, script, out, 'build', 60)
        state.require(execution['returncode'] == 0, 'Tiny common miter failed')
        validate_interface(json.loads(interface.read_text())['modules']['miter'], plan)
        records = []
        for shard in range(SHARDS):
            script = out/(str(shard)+'.tcl'); script.write_text(shard_script(common_il, plan, shard, out, 10))
            execution = execute_tcl(runtime, script, out, 'shard'+str(shard))
            state.require(execution['returncode'] == 0, 'Native tiny partition traversal failed')
            groups = parse_shard((out/('shard'+str(shard)+'.log')).read_text(), plan, shard, out)
            records.append(dict(shard=shard, groups=groups))
        verdict = aggregate(plan, records)
        state.require(verdict['state_bijection_proved'] == (case == 'equal'), 'Wrong tiny partition proof verdict')
        if case == 'equal':
            for fault in ('omitted', 'duplicate'):
                bad = copy.deepcopy(records)
                if fault == 'omitted': bad[0]['groups'].pop()
                else: bad[0]['groups'].append(copy.deepcopy(bad[0]['groups'][0]))
                try:
                    aggregate(plan, bad)
                except ValueError:
                    verdict[fault+'_native_group_receipt_rejected'] = True
                else:
                    raise ValueError('Incomplete native receipt control was accepted')
        state.common.save(out/'plan.json', plan); state.common.save(out/'groups.json', records)
        results[case] = verdict
    return results


def snapshot_methods(output):
    methods = {}
    for name in (*PINS, *OWN):
        if name in PINS: state.require(state.common.sha(ROOT/name) == PINS[name], 'Pinned producer changed')
        dest = output/'methods'/name; dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((ROOT/name).read_bytes()); methods[name] = state.archived.pin(dest)
    return methods


def timeout_archive(path):
    state.common.download(dict(TIMEOUT_ZIP, url=TIMEOUT_URL), path)


def verify_proposal_serialization(proposal, output, expected):
    # The frozen producer uses integer mapping keys in Python. JSON writes
    # those keys as strings; reproduce its exact serializer and byte pin rather
    # than treating that required JSON conversion as a changed proposal.
    state.common.save(output, proposal)
    state.common.verify_file(output, expected)
    return state.archived.pin(output)


def prepare(output, work):
    state.require(os.environ.get('GITHUB_ACTIONS') == 'true', 'Full miter construction is cloud-only')
    output, work = state.common.fresh_directory(output), state.common.fresh_directory(work)
    row = dict(status='PREPARING', github_source_commit=os.environ.get('GITHUB_SHA'),
               original_failed_proof_preserved=True, monolithic_timeout_preserved=True, state_bijection_proved=False)
    try:
        row['methods'] = snapshot_methods(output); state.common.save(output/'result.json', row)
        failed = work/'failed.zip'; replay.fetch_artifact(failed); source = work/'failed'; replay.restore(failed, source)
        timed = work/'timeout.zip'; timeout_archive(timed); second = work/'timeout'; second.mkdir()
        with zipfile.ZipFile(timed) as z:
            state.require(len(z.namelist()) == len(set(z.namelist())), 'Duplicate timeout member')
            for name, expected in TIMEOUT_MEMBERS.items():
                state.require(z.getinfo(name).file_size == expected['bytes'], 'Timeout member size differs')
                with z.open(name) as src, (second/name).open('xb') as dest:
                    while block := src.read(1024**2): dest.write(block)
                state.common.verify_file(second/name, expected)
        previous = json.loads((second/'result.json').read_text())
        state.require(previous['github_source_commit'] == TIMEOUT_COMMIT and previous['status'] == 'FAILED_OR_INCOMPLETE'
                      and previous['state_bijection_proved'] is False
                      and 'Interrupted SAT solver: TIMEOUT!' in (second/'corrected-miter.log').read_text(),
                      'Original timeout status changed')
        docs = {tag: json.loads((source/(tag+'-lifted.json')).read_text()) for tag in ('original', 'candidate')}
        labels = {tag: json.loads((source/(tag+'-obligations.json')).read_text()) for tag in docs}
        proposed = json.loads((source/'state-bijection-proposal.json').read_text())
        fixed, fixed_labels, fixed_proposal = correction.corrected_proposal(docs['original']['modules']['soc_top'],
            docs['candidate']['modules']['soc_top'], proposed, labels)
        expected = json.loads((second/'corrected-candidate-lifted.json').read_text())
        row['reconstruction_checks'] = dict(graph_object_equal=expected['modules']['soc_top'] == fixed,
            labels_object_equal=json.loads((second/'corrected-candidate-obligations.json').read_text()) == fixed_labels)
        common_record = work/'rebuilt-state-proposal.json'
        row['reconstruction_checks']['proposal_exact_serialized_pin'] = verify_proposal_serialization(
            fixed_proposal, common_record, TIMEOUT_MEMBERS['corrected-state-proposal.json'])
        state.common.save(output/'result.json', row)
        state.require(row['reconstruction_checks']['graph_object_equal']
                      and row['reconstruction_checks']['labels_object_equal'],
                      'Rebuilt exact corrected relation differs from preserved timeout')
        left = docs['original']['modules']['soc_top']; plan = make_plan(left, fixed)
        state.require((plan['symbolic_input_bits'], plan['total_output_bits'], len(plan['groups'])) == (10828, 34321, 269),
                      'Complete source partition census changed')
        state.common.save(output/'plan.json', plan)
        for tag, module in [('original', left), ('candidate', fixed)]:
            state.common.save(work/(tag+'-wrapped.json'), {'modules': {'soc_top': alias_outputs(module, plan)}})
        wrapped_pins = {tag: state.archived.pin(work/(tag+'-wrapped.json')) for tag in ('original', 'candidate')}
        del docs, labels, fixed, fixed_labels, fixed_proposal, expected, left, module
        lock = state.archived.validate_lock(json.loads((ROOT/state.archived.LOCK).read_text()))
        bundle = work/'library'; state.archived.restore(ROOT/lock['archive']['path'], bundle, lock)
        library = bundle/'pdk/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib'
        row['clock_gate_semantics'] = state.validate_gate_liberty(library)
        manifest = state.common.validate_manifest(json.loads((ROOT/state.archived.MANIFEST).read_text()))
        runtime = work/'runtime.AppImage'; state.common.download(manifest['runtime'], runtime); runtime.chmod(0o755)
        tiny = output/'controls'; tiny.mkdir(); row['controls'] = controls(runtime, library, tiny)
        script = output/'build.ys'; common_il = output/'common-miter.il'; interface = work/'common-interface.json'
        script.write_text(build_script(work/'original-wrapped.json', work/'candidate-wrapped.json', library, common_il, interface))
        execution = state.execute(runtime, script, output, 'build', 900)
        state.require(execution['returncode'] == 0, 'Common native miter construction failed')
        row['native_interface'] = validate_interface(json.loads(interface.read_text())['modules']['miter'], plan)
        for name, expected_pin in replay.MEMBERS.items(): state.common.verify_file(source/name, expected_pin)
        for name, expected_pin in TIMEOUT_MEMBERS.items(): state.common.verify_file(second/name, expected_pin)
        for tag, expected_pin in wrapped_pins.items(): state.common.verify_file(work/(tag+'-wrapped.json'), expected_pin)
        for name, expected_pin in row['methods'].items(): state.common.verify_file(output/'methods'/name, expected_pin)
        for name, expected_pin in lock['files'].items(): state.common.verify_file(bundle/name, expected_pin)
        state.common.verify_file(runtime, manifest['runtime']); state.common.verify_file(timed, TIMEOUT_ZIP)
        row.update(status='COMMON_MITER_PREPARED_NOT_PROVED', common_miter=state.archived.pin(common_il),
            plan=state.archived.pin(output/'plan.json'), native_build=execution,
            source_archives=dict(failed=replay.ARTIFACT, timeout=TIMEOUT_ZIP), runtime=manifest['runtime'],
            original_graph=replay.MEMBERS['original-lifted.json'], corrected_graph=TIMEOUT_MEMBERS['corrected-candidate-lifted.json'],
            wrapped_graphs=wrapped_pins, complete_inputs_rechecked=True)
    except BaseException as exc:
        row.update(status='PREPARATION_FAILED', error=repr(exc)); raise
    finally:
        row['outputs'] = {str(p.relative_to(output)): state.archived.pin(p) for p in sorted(output.rglob('*'))
                          if p.is_file() and p != output/'result.json'}
        state.common.save(output/'result.json', row)
    return row


def verify_common(bundle):
    row = json.loads((bundle/'result.json').read_text())
    state.require(row['status'] == 'COMMON_MITER_PREPARED_NOT_PROVED' and row['complete_inputs_rechecked'] is True,
                  'Common miter incomplete')
    state.require(row['github_source_commit'] == os.environ.get('GITHUB_SHA'), 'Different preparation/current source')
    state.require(set(row['methods']) == set(PINS) | set(OWN), 'Incomplete/extra common method inventory')
    verify_inventory(bundle, row['outputs'])
    for name, expected in row['methods'].items():
        state.common.verify_file(ROOT/name, expected)
        state.common.verify_file(bundle/'methods'/name, expected)
        if name in PINS:
            state.require(expected['sha256'] == PINS[name], 'Common frozen producer changed')
    manifest = state.common.validate_manifest(json.loads((ROOT/state.archived.MANIFEST).read_text()))
    state.require(row['runtime'] == manifest['runtime'], 'Prepared runtime differs from pinned manifest')
    state.common.verify_file(bundle/'common-miter.il', row['common_miter'])
    state.common.verify_file(bundle/'plan.json', row['plan'])
    plan = validate_plan(json.loads((bundle/'plan.json').read_text()))
    state.require((plan['symbolic_input_bits'], plan['total_output_bits'], len(plan['groups'])) == (10828, 34321, 269),
                  'Full common boundary census differs')
    return row, plan


def verify_inventory(directory, inventory):
    actual = set()
    for path in directory.rglob('*'):
        state.require(not path.is_symlink(), 'Linked proof artifact member')
        if path.is_file() and path != directory/'result.json':
            actual.add(str(path.relative_to(directory)))
    state.require(set(inventory) == actual, 'Incomplete/extra proof artifact inventory')
    for name, expected in inventory.items():
        state.common.verify_file(directory/state.common.safe_relative(name), expected)


def run_shard(bundle, shard, output, work):
    state.require(os.environ.get('GITHUB_ACTIONS') == 'true', 'Full partition proof is cloud-only')
    output, work = state.common.fresh_directory(output), state.common.fresh_directory(work)
    row = dict(status='PREPARING_SHARD', shard=shard, github_source_commit=os.environ.get('GITHUB_SHA'))
    try:
        prepared, plan = verify_common(bundle)
        row.update(common_miter=prepared['common_miter'], plan=prepared['plan'], methods=prepared['methods'])
        state.require(prepared['github_source_commit'] == row['github_source_commit'], 'Different build/proof source')
        runtime = work/'runtime.AppImage'; state.common.download(prepared['runtime'], runtime); runtime.chmod(0o755)
        script = output/'partitions.tcl'; script.write_text(shard_script(bundle/'common-miter.il', plan, shard, output))
        execution = execute_tcl(runtime, script, output, 'partitions')
        state.require(execution['returncode'] == 0, 'Native partition traversal incomplete')
        results = parse_shard((output/'partitions.log').read_text(), plan, shard, output)
        state.common.verify_file(bundle/'common-miter.il', prepared['common_miter'])
        state.common.verify_file(runtime, prepared['runtime'])
        row.update(status='ALL_ASSIGNED_GROUPS_VISITED', groups=results, execution=execution,
                   complete_inputs_rechecked=True, all_assigned_groups_proved=all(
                       g['verdict'] == 'PROVED_ALL_BINARY_BOUNDARY_EQUATIONS' for g in results))
    except BaseException as exc:
        row.update(status='SHARD_FAILED_OR_INCOMPLETE', error=repr(exc)); raise
    finally:
        row['outputs'] = {str(p.relative_to(output)): state.archived.pin(p) for p in sorted(output.rglob('*'))
                          if p.is_file() and p != output/'result.json'}
        state.common.save(output/'result.json', row)
    return row


def aggregate_directories(bundle, directories, output):
    prepared, plan = verify_common(bundle)
    rows = []
    for directory in directories:
        row = json.loads((directory/'result.json').read_text())
        state.require(row['status'] == 'ALL_ASSIGNED_GROUPS_VISITED' and row['complete_inputs_rechecked'] is True
                      and row['github_source_commit'] == prepared['github_source_commit']
                      and row['common_miter'] == prepared['common_miter'] and row['plan'] == prepared['plan']
                      and row['methods'] == prepared['methods'], 'Unmatched/incomplete proof shard')
        verify_inventory(directory, row['outputs'])
        parsed = parse_shard((directory/'partitions.log').read_text(), plan, row['shard'], directory, write_logs=False)
        state.require(parsed == row['groups'], 'Captured group verdict differs from raw native log')
        rows.append(row)
    result = aggregate(plan, rows)
    result.update(github_source_commit=prepared['github_source_commit'], common_miter=prepared['common_miter'],
                  plan=prepared['plan'], shard_results={str(row['shard']): state.archived.pin(directory/'result.json')
                  for row, directory in zip(rows, directories)}, scope='All original binary storage-boundary equations; equal initial corresponding state and identical opaque SRAM behavior remain preconditions. No reset reachability, 4-state, CDC, memory-internal or physical acceptance.')
    state.common.save(output, result)
    state.require(result['state_bijection_proved'], 'Some complete output groups remain unproved or have counterexamples')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['prepare', 'shard', 'aggregate'])
    parser.add_argument('--output', type=Path, required=True); parser.add_argument('--work', type=Path)
    parser.add_argument('--bundle', type=Path); parser.add_argument('--shard', type=int)
    parser.add_argument('--shard-dir', type=Path, action='append'); args = parser.parse_args()
    if args.phase == 'prepare': result = prepare(args.output.resolve(), args.work.resolve())
    elif args.phase == 'shard': result = run_shard(args.bundle.resolve(), args.shard, args.output.resolve(), args.work.resolve())
    else: result = aggregate_directories(args.bundle.resolve(), args.shard_dir, args.output.resolve())
    print(result['status'])


if __name__ == '__main__': main()
