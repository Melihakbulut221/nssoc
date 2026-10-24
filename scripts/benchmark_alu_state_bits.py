#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Measure selected unproved output bits; never substitute sampling for equivalence."""
import argparse
import copy
import json
import os
from pathlib import Path
import re

import prove_alu_state_refinement as ref

part, state = ref.part, ref.state
ROOT = Path(__file__).resolve().parents[1]
LOCK = 'hw/soc/pnr/alu-state-bit-benchmark-input.lock.json'
OWN = ('scripts/benchmark_alu_state_bits.py', 'sw/tests/test_alu_state_bit_benchmark.py',
       '.github/workflows/timing-alu-state-bit-benchmark.yml', LOCK)
PINS = {**ref.PINS,
    'scripts/prove_alu_state_refinement.py': '0f37ca66568a3a6f8d5e4d318fa2c525215e0b666fd618cf7aaa98f2b18a192f',
    'sw/tests/test_alu_state_refinement.py': '7b1e1514a352e40c2de644c56b56644052ae693616c6bac9a0594693169e5ad9',
    '.github/workflows/timing-alu-state-refinement.yml': '4418f24ddfa360bddbc77e45a87437ef90d7a794ae9b884834be7b0125225a70',
    ref.LOCK: '1f883357ff93e0ed1a379d711cc132f105fcdbd57ac03771e289f0d70033a6b5'}
PASS = 'PROVED_ALL_BINARY_BOUNDARY_EQUATIONS'
TIMEOUT = 'TIMEOUT_UNPROVED'


def load_lock():
    row = json.loads((ROOT/LOCK).read_text())
    state.require(row['schema'] == 1 and row['source_run'] == 37030551226
        and row['source_commit'] == 'c73ad3eaff3f7a2574f8293525b4436283678f7a'
        and row['source_conclusion'] == 'failure'
        and set(row['artifacts']) == {'common', 'verdict', 'shard0', 'shard1', 'shard2', 'shard3'}
        and (row['prior_proved_bits'], row['remaining_bits'], row['symbolic_input_bits'],
             row['original_output_bits'], row['refined_proved_groups'], row['refined_timeout_groups'])
        == (33505, 816, 10828, 34321, 101, 51)
        and row['per_bit_timeout_seconds'] == 120 and len(row['selected']) == 16,
        'Unreviewed per-bit benchmark input')
    return row


def coverage(original, old_rows, refined, rows, timeouts):
    """Reproduce the old decision and partition its original bits, without dropping any."""
    verdict = ref.combined_verdict(original, old_rows, refined, rows, timeouts)
    parents = {g['id']: g for g in original['groups']}
    groups = {g['id']: g for g in refined['groups']}
    proved = [tuple(x) for r in old_rows for g in r['groups'] if g['verdict'] == PASS
              for x in parents[g['id']]['obligations']]
    remaining = []
    for row in rows:
        for group in row['groups']:
            state.require(group['verdict'] in {PASS, TIMEOUT} and group['native_returncode'] == 0,
                          'Prior counterexample or tool failure cannot be relabeled')
            for offset, (parent, bit) in enumerate(groups[group['id']]['obligations']):
                original_bit = parents[parent]['obligations'][bit]
                if group['verdict'] == PASS:
                    proved.append(tuple(original_bit))
                else:
                    remaining.append(dict(parent=group['id'], bit=offset, original=original_bit))
    all_bits = {tuple(x) for g in original['groups'] for x in g['obligations']}
    unproved = {tuple(x['original']) for x in remaining}
    state.require(len(proved) == len(set(proved)) and len(remaining) == len(unproved)
        and not set(proved) & unproved and set(proved) | unproved == all_bits,
        'Prior proofs and remaining observations do not partition the full relation')
    return dict(aggregate=verdict, proved=sorted(proved), remaining=sorted(remaining,
        key=lambda x: (x['original'][0], x['original'][1])), original_bits=len(all_bits))


def choose_representatives(remaining):
    by_category = {}
    for row in remaining:
        by_category.setdefault(row['original'][0], []).append(row)
    selected = []
    for name in sorted(by_category):
        group = sorted(by_category[name], key=lambda x: x['original'][1])
        state.require(len(group) >= 2, 'Expected two remaining bits per category')
        selected.extend([group[0], group[-1]])
    data = sorted(by_category[state.PREFIX+'ff_d'], key=lambda x: x['original'][1])
    selected.extend([data[len(data)//3], data[2*len(data)//3]])
    selected = sorted(selected, key=lambda x: (x['original'][0], x['original'][1]))
    state.require(len(selected) <= 16 and len({tuple(x['original']) for x in selected}) == len(selected),
                  'Representative selection exceeds budget or duplicates bits')
    return [dict(row, id=f'{part.PREFIX}{i:04d}') for i, row in enumerate(selected)]


def observation_plan(refined, selected):
    part.validate_plan(refined)
    state.require(4 <= len(selected) <= 16, 'Bounded benchmark requires 4 to 16 bits')
    parents = {g['id']: g for g in refined['groups']}
    seen = set()
    for index, row in enumerate(selected):
        key = (row['parent'], row['bit'])
        state.require(row['id'] == f'{part.PREFIX}{index:04d}' and key not in seen
            and row['parent'] in parents and type(row['bit']) is int
            and 0 <= row['bit'] < len(parents[row['parent']]['obligations']), 'Invalid or duplicate selected bit')
        seen.add(key)
    plan = dict(schema=1, symbolic_inputs=dict(refined['symbolic_inputs']),
        symbolic_input_bits=refined['symbolic_input_bits'], output_widths={r['id']: 1 for r in selected},
        total_output_bits=len(selected), chunk_width=1, shards=4,
        groups=[dict(id=r['id'], obligations=[[r['id'], 0]], shard=i % 4) for i, r in enumerate(selected)])
    return part.validate_plan(plan)


def wrapper(refined, selected):
    plan = observation_plan(refined, selected)
    names = list(plan['symbolic_inputs']) + [r['parent'] for r in selected]
    state.require(all(re.fullmatch('[A-Za-z_][A-Za-z0-9_]*', n) for n in names), 'Unsafe observation name')
    declarations = [f'input wire [{w-1}:0] in_{n}' for n, w in plan['symbolic_inputs'].items()]
    for row in selected:
        declarations.extend(f'output wire {prefix}_{row["id"]}' for prefix in ('cmp', 'gold', 'gate'))
    lines = ['module miter('+',\n'.join(declarations)+');']
    parents = {g['id']: g for g in refined['groups']}
    observed = sorted({r['parent'] for r in selected})
    for name in observed:
        for prefix in ('gold', 'gate'):
            lines.append(f'wire [{len(parents[name]["obligations"])-1}:0] observed_{prefix}_{name};')
    connections = [f'.in_{n}(in_{n})' for n in plan['symbolic_inputs']]
    connections += [f'.{p}_{n}(observed_{p}_{n})' for n in observed for p in ('gold', 'gate')]
    lines.append('nssoc_preserved_miter preserved('+',\n'.join(connections)+');')
    for row in selected:
        for prefix in ('gold', 'gate'):
            lines.append(f'assign {prefix}_{row["id"]} = observed_{prefix}_{row["parent"]}[{row["bit"]}];')
        lines.append(f'assign cmp_{row["id"]} = gold_{row["id"]} == gate_{row["id"]};')
    return '\n'.join(lines+['endmodule', ''])


def verify_refinement(bundle, lock):
    common = bundle/'common'
    state.common.verify_file(common/'result.json', lock['common_result'])
    prepared = json.loads((common/'result.json').read_text())
    state.require(prepared['status'] == 'REFINED_MITER_PREPARED_NOT_PROVED'
        and prepared['complete_inputs_rechecked'] is True
        and prepared['github_source_commit'] == lock['source_commit']
        and prepared['runtime'] == ref.manifest()['runtime'] and set(prepared['methods']) == set(PINS),
        'Unbound refined common preparation')
    part.verify_inventory(common, prepared['outputs'])
    for name, pin in prepared['methods'].items():
        state.require(pin['sha256'] == PINS[name], 'Prior method changed')
        state.common.verify_file(ROOT/name, pin)
        state.common.verify_file(common/'methods'/name, pin)
    previous_lock = ref.load_lock()
    _, original, old_rows = ref.verify_prior(common/'prior', previous_lock)
    state.common.verify_file(ROOT/ref.LOCK, prepared['original_lock'])
    state.require(prepared['original_common_miter'] == previous_lock['common_miter'], 'Original graph changed')
    for name, field in [('common-miter.il', 'common_miter'), ('plan.json', 'plan')]:
        state.require(prepared[field] == lock[field], 'Refined graph or plan record changed')
        state.common.verify_file(common/name, lock[field])
    refined = part.validate_plan(json.loads((common/'plan.json').read_text()))
    state.require(refined == ref.refinement_plan(original, previous_lock['timed_out_groups'],
        previous_lock['refinement_width']), 'Refined observation plan changed')
    state.require((common/'observations.v').read_text() == ref.wrapper(original, refined,
        previous_lock['timed_out_groups']), 'Preserved refinement wrapper changed')
    rows = []
    for shard in range(4):
        directory = bundle/('shard'+str(shard))
        state.common.verify_file(directory/'result.json', lock['shard_results'][str(shard)])
        row = json.loads((directory/'result.json').read_text())
        state.require(row['shard'] == shard and row['status'] == 'ALL_REFINED_GROUPS_VISITED'
            and row['execution']['returncode'] == 0 and row['complete_inputs_rechecked'] is True
            and all(row[k] == prepared[k] for k in ('github_source_commit', 'common_miter', 'plan',
                                                  'methods', 'original_common_miter', 'original_lock')),
            'Refined shard has changed or incomplete provenance')
        part.verify_inventory(directory, row['outputs'])
        parsed = part.parse_shard((directory/'partitions.log').read_text(), refined, shard, directory, write_logs=False)
        state.require(parsed == row['groups'], 'Refined raw native verdict changed')
        rows.append(row)
    result = coverage(original, old_rows, refined, rows, previous_lock['timed_out_groups'])
    path = bundle/'verdict'/'alu-refinement-verdict.json'
    state.common.verify_file(path, lock['aggregate_result'])
    captured = json.loads(path.read_text())
    state.require(all(captured[k] == v for k, v in result['aggregate'].items())
        and all(captured[k] == prepared[k] for k in ('github_source_commit', 'common_miter', 'plan',
                                                   'original_common_miter', 'original_lock'))
        and captured['shard_results'] == lock['shard_results'], 'Prior aggregate cannot be reproduced')
    state.require((len(result['proved']), len(result['remaining']), result['original_bits'],
                   refined['symbolic_input_bits'], result['aggregate']['refined_proved_groups'])
        == (lock['prior_proved_bits'], lock['remaining_bits'], lock['original_output_bits'],
            lock['symbolic_input_bits'], lock['refined_proved_groups'])
        and sum(g['verdict'] == TIMEOUT for r in rows for g in r['groups']) == lock['refined_timeout_groups'],
        'Previous proof coverage changed')
    state.require(choose_representatives(result['remaining']) == lock['selected'], 'Selected bit correspondence changed')
    return prepared, refined, result


def timed_script(miter, plan, shard, directory, timeout):
    state.require(type(timeout) is int and 1 <= timeout <= 120, 'Unbounded per-bit SAT timeout')
    script = part.shard_script(miter, plan, shard, directory, timeout)
    for group in plan['groups']:
        if group['shard'] != shard:
            continue
        name = group['id']
        begin = part.tcl_command(f'log NSSOC_GROUP_BEGIN {name}')
        end = f'yosys log NSSOC_GROUP_END {name} $code'
        state.require(script.count(begin) == script.count(end) == 1, 'Frozen traversal markers changed')
        script = script.replace(begin, 'set benchmark_started [clock milliseconds]\n'+begin, 1)
        script = script.replace(end, end+f'\nyosys log NSSOC_BIT_MILLISECONDS {name} [expr {{[clock milliseconds] - $benchmark_started}}]', 1)
    return script


def costs(text, plan, shard, directory):
    groups = part.parse_shard(text, plan, shard, directory)
    measured = re.findall(r'^NSSOC_BIT_MILLISECONDS (\S+) ([0-9]+)$', text, re.M)
    state.require([n for n, _ in measured] == [g['id'] for g in groups], 'Missing or duplicate native per-bit cost')
    for group, (_, ms) in zip(groups, measured):
        block = (directory/(group['id']+'.log')).read_text()
        cnf = re.findall(r'Solving problem with ([0-9]+) variables and ([0-9]+) clauses', block)
        state.require(len(cnf) == 1, 'Missing or ambiguous native SAT size')
        group.update(elapsed_milliseconds=int(ms), sat_variables=int(cnf[0][0]), sat_clauses=int(cnf[0][1]))
    return groups


def benchmark_verdict(plan, selected, records, prior_proved, original_bits):
    result = part.aggregate(plan, records)
    state.require(len(selected) == len(plan['groups']) and [r['id'] for r in selected]
        == [r['id'] for r in plan['groups']] and prior_proved+len(selected) < original_bits,
        'Benchmark cannot be relabeled as full proof')
    by_id = {g['id']: g for r in records for g in r['groups']}
    state.require(all(g['verdict'] in {PASS, TIMEOUT, 'COUNTEREXAMPLE_PRESERVED'}
        and g['native_returncode'] == 0 for g in by_id.values()), 'Unknown or failed native benchmark verdict')
    return dict(status='BOUNDED_BIT_BENCHMARK_COMPLETE', selected_bits=len(selected),
        selected_proved_bits=result['proved_groups'], selected_timeouts=sum(g['verdict'] == TIMEOUT for g in by_id.values()),
        selected_counterexamples=sum(g['verdict'] == 'COUNTEREXAMPLE_PRESERVED' for g in by_id.values()),
        per_bit=[dict(s, **{k: v for k, v in by_id[s['id']].items() if k != 'id'}) for s in selected],
        cost_scope='Per-bit elapsed time includes restoring the common design, pruning unobserved output cones and SAT.',
        prior_proved_bits_preserved=prior_proved, original_output_bits=original_bits,
        remaining_unproved_bits=original_bits-prior_proved-result['proved_groups'],
        symbolic_input_bits=plan['symbolic_input_bits'], no_internal_assumptions=True,
        state_bijection_proved=False, full_soc_functional_accepted=False, candidate_adopted=False,
        timing_accepted=False, manufacturing_approval=False, unresolved_four_state_boot_failure=True)


def native_controls(runtime, library, directory):
    left, _ = state.lift(state.fixture(), ['ff0', 'ff1'])
    wrong_clock = copy.deepcopy(left); wrong_clock['ports'][state.PREFIX+'ff_clk']['bits'][0] = '0'
    wrong_output = copy.deepcopy(left); wrong_output['ports']['output_q']['bits'][0] = '0'
    controls = {}
    for name, right in [('equal', left), ('wrong_clock', wrong_clock), ('wrong_output', wrong_output)]:
        out = directory/name; out.mkdir()
        source_plan = part.make_plan(left, right, 2)
        selected = [dict(id=f'{part.PREFIX}{i:04d}', parent=g['id'], bit=offset, original=pair)
                    for i, (g, offset, pair) in enumerate((g, o, p) for g in source_plan['groups']
                                                         for o, p in enumerate(g['obligations']))]
        plan = observation_plan(source_plan, selected)
        for tag, module in [('left', left), ('right', right)]:
            state.common.save(out/(tag+'.json'), dict(modules=dict(soc_top=part.alias_outputs(module, source_plan))))
        script = out/'original.ys'; script.write_text(part.build_script(out/'left.json', out/'right.json', library,
                                                                       out/'original.il', out/'original-interface.json'))
        state.require(state.execute(runtime, script, out, 'original', 60)['returncode'] == 0, 'Tiny original build failed')
        observations = out/'observations.v'; observations.write_text(wrapper(source_plan, selected))
        script = out/'build.ys'; script.write_text(ref.build_script(out/'original.il', observations,
                                                                  out/'common.il', out/'interface.json'))
        state.require(state.execute(runtime, script, out, 'build', 60)['returncode'] == 0, 'Tiny bit wrapper failed')
        part.validate_interface(json.loads((out/'interface.json').read_text())['modules']['miter'], plan)
        records = []
        for shard in range(4):
            script = out/(str(shard)+'.tcl'); script.write_text(timed_script(out/'common.il', plan, shard, out, 10))
            state.require(part.execute_tcl(runtime, script, out, 'shard'+str(shard))['returncode'] == 0, 'Tiny traversal failed')
            records.append(dict(shard=shard, groups=costs((out/('shard'+str(shard)+'.log')).read_text(), plan, shard, out)))
        result = part.aggregate(plan, records)
        state.require(result['state_bijection_proved'] == (name == 'equal'), 'Wrong native bit control verdict')
        state.require(all(g['verdict'] != TIMEOUT for r in records for g in r['groups']), 'Tiny control timed out')
        state.common.save(out/'plan.json', plan); state.common.save(out/'selection.json', selected)
        state.common.save(out/'groups.json', records); controls[name] = result
    return controls


def snapshot_methods(output):
    methods = {}
    for name in (*PINS, *OWN):
        if name in PINS:
            state.require(state.common.sha(ROOT/name) == PINS[name], 'Frozen source changed')
        dest = output/'methods'/name; dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((ROOT/name).read_bytes()); methods[name] = state.archived.pin(dest)
    return methods


def run(output, work):
    state.require(os.environ.get('GITHUB_ACTIONS') == 'true', 'Full per-bit benchmark is cloud-only')
    output, work = state.common.fresh_directory(output), state.common.fresh_directory(work)
    row = dict(status='PREPARING_BIT_BENCHMARK', github_source_commit=os.environ.get('GITHUB_SHA'),
               state_bijection_proved=False, candidate_adopted=False, unresolved_four_state_boot_failure=True)
    try:
        row['methods'] = snapshot_methods(output); state.common.save(output/'result.json', row)
        lock = load_lock(); prior = work/'prior'; prior.mkdir()
        row['original_archives'] = ref.fetch_originals(lock, prior, work)
        prepared, refined, previous = verify_refinement(prior, lock)
        state.common.save(output/'preserved-proof-coverage.json', previous)
        runtime = work/'runtime.AppImage'; state.common.download(prepared['runtime'], runtime); runtime.chmod(0o755)
        library_lock = state.archived.validate_lock(json.loads((ROOT/state.archived.LOCK).read_text()))
        library_bundle = work/'library'; state.archived.restore(ROOT/library_lock['archive']['path'], library_bundle, library_lock)
        library = library_bundle/'pdk/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib'
        tiny = output/'controls'; tiny.mkdir(); row['controls'] = native_controls(runtime, library, tiny)
        plan = observation_plan(refined, lock['selected']); state.common.save(output/'plan.json', plan)
        state.common.save(output/'selection.json', lock['selected'])
        observations = output/'observations.v'; observations.write_text(wrapper(refined, lock['selected']))
        script = output/'build.ys'; common = work/'common-miter.il'; interface = work/'interface.json'
        script.write_text(ref.build_script(prior/'common/common-miter.il', observations, common, interface))
        row['native_build'] = state.execute(runtime, script, output, 'build', 900)
        state.require(row['native_build']['returncode'] == 0, 'Native bit observation wrapper failed')
        row['native_interface'] = part.validate_interface(json.loads(interface.read_text())['modules']['miter'], plan)
        row.update(common_miter=state.archived.pin(common), runtime=prepared['runtime'],
                   prior_common_miter=prepared['common_miter'], original_common_miter=prepared['original_common_miter'])
        records = []
        for shard in range(4):
            script = output/('shard'+str(shard)+'.tcl')
            script.write_text(timed_script(common, plan, shard, output, lock['per_bit_timeout_seconds']))
            execution = part.execute_tcl(runtime, script, output, 'shard'+str(shard))
            state.require(execution['returncode'] == 0, 'Native bit traversal incomplete')
            records.append(dict(shard=shard, groups=costs((output/('shard'+str(shard)+'.log')).read_text(),
                                                        plan, shard, output), execution=execution))
            state.common.save(output/'groups.json', records)
        after, after_plan, after_coverage = verify_refinement(prior, lock)
        state.require((after, after_plan, after_coverage) == (prepared, refined, previous), 'Original evidence changed during benchmark')
        state.common.verify_file(runtime, prepared['runtime']); state.common.verify_file(common, row['common_miter'])
        for name, pin in row['methods'].items():
            state.common.verify_file(ROOT/name, pin); state.common.verify_file(output/'methods'/name, pin)
        for name, pin in library_lock['files'].items():
            state.common.verify_file(library_bundle/name, pin)
        row.update(benchmark_verdict(plan, lock['selected'], records, len(previous['proved']), previous['original_bits']))
        row['complete_inputs_rechecked'] = True
    except BaseException as exc:
        row.update(status='BIT_BENCHMARK_FAILED_OR_INCOMPLETE', error=repr(exc)); raise
    finally:
        row['outputs'] = ref.inventory(output); state.common.save(output/'result.json', row)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--work', required=True, type=Path)
    args = parser.parse_args()
    print(run(args.output.resolve(), args.work.resolve())['status'])


if __name__ == '__main__':
    main()
