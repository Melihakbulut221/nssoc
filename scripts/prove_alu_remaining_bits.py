#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Visit every previously untested ALU boundary bit; never promote sampling to proof."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import time

import benchmark_alu_state_bits as bench

ref, part, state = bench.ref, bench.part, bench.state
ROOT = Path(__file__).resolve().parents[1]
LOCK = 'hw/soc/pnr/alu-state-bits-complete-input.lock.json'
OWN = ('scripts/prove_alu_remaining_bits.py', 'sw/tests/test_alu_remaining_bits.py', LOCK,
       '.github/workflows/timing-alu-state-bits-complete.yml')
PASS, TIMEOUT, CEX = bench.PASS, bench.TIMEOUT, 'COUNTEREXAMPLE_PRESERVED'
BATCHES = (16, 16, 14, 4)
require = state.require
pin = state.archived.pin
save = state.common.save


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def load_lock():
    row = json.loads((ROOT/LOCK).read_text())
    old = bench.load_lock()
    require(row['schema'] == 1 and row['refinement']['run_id'] == old['source_run']
        and row['refinement']['source_commit'] == old['source_commit']
        and row['refinement']['source_conclusion'] == 'failure', 'Changed original refinement')
    require(set(row['refinement']['archives']) == set(old['artifacts']), 'Missing original archive')
    for name, source in old['artifacts'].items():
        actual = row['refinement']['archives'][name]
        require(all(actual[k] == v for k, v in source.items()) and actual['url'].startswith(
            'https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20260927-chip-io/'),
            'Changed archived refinement identity')
    expected = (33505, 12, 33517, 800, 4, 34321, 10828, 16, 4, 120)
    require(tuple(row[k] for k in ('prior_proved', 'benchmark_proved', 'preserved_proved', 'untested',
        'hard', 'original_bits', 'symbolic_input_bits', 'shards', 'max_parallel', 'per_bit_sat_seconds'))
        == expected and row['batch_sizes'] == list(BATCHES), 'Changed exhaustive boundary/budget contract')
    b = row['benchmark']
    require(b['run_id'] == 37071773706 and b['source_commit'] == 'c7ffba6373529530bf208e58dc9d1bf66eb1182b'
        and b['source_conclusion'] == 'success' and b['artifact'] == dict(id=11255066521,
            name='alu-state-bit-benchmark-1', bytes=616389,
            sha256='3037a0629d15d9b5c8ffc20bb5a1e43b0b6421ecd666a24df164e9ba6e28576e',
            url='https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20260927-chip-io/closure-alu-state-bit-benchmark-37071773706-20261003.zip'),
        'Changed bounded benchmark source')
    require(row['runtime'] == ref.manifest()['runtime'] and row['refined_miter'] == old['common_miter'],
            'Changed runtime or refined graph')
    require(set(row['source_method_pins']) == set(bench.PINS)|set(bench.OWN), 'Frozen method closure differs')
    for name, expected_pin in row['source_method_pins'].items():
        state.common.verify_file(ROOT/name, expected_pin)
        if name in bench.PINS:
            require(expected_pin['sha256'] == bench.PINS[name], 'Changed frozen method')
    return row


def source_snapshot(output, locked):
    result = {}
    for name in (*locked['source_method_pins'], *OWN):
        path = output/'methods'/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT/name).read_bytes())
        result[name] = pin(path)
    return result


def verify_methods(bundle, row, locked):
    require(set(row['methods']) == set(locked['source_method_pins'])|set(OWN), 'New method closure differs')
    for name, value in row['methods'].items():
        state.common.verify_file(ROOT/name, value)
        state.common.verify_file(bundle/'methods'/name, value)
        if name in locked['source_method_pins']:
            require(value == locked['source_method_pins'][name], 'Frozen source replaced')


def run_identity(source):
    run = ref.api('actions/runs/'+str(source['run_id']))
    require(run['id'] == source['run_id'] and run['head_sha'] == source['source_commit']
        and run['status'] == 'completed' and run['conclusion'] == source['source_conclusion']
        and run['run_attempt'] == 1 and run['repository']['full_name'] == 'Melihakbulut221/nssoc',
        'Original workflow identity differs')
    return {k: run[k] for k in ('id', 'head_sha', 'status', 'conclusion', 'run_attempt', 'html_url')}


def acquire(source, entry, archive, *, permanent):
    try:
        metadata = ref.api('actions/artifacts/'+str(entry['id']))
    except subprocess.CalledProcessError:
        require(permanent, 'Benchmark artifact metadata unavailable; no unverified fallback')
        metadata = None
    if metadata is not None:
        require(metadata['id'] == entry['id'] and metadata['name'] == entry['name']
            and metadata['size_in_bytes'] == entry['bytes'] and metadata['digest'] == 'sha256:'+entry['sha256']
            and metadata['workflow_run']['id'] == source['run_id']
            and metadata['workflow_run']['head_sha'] == source['source_commit'], 'Available artifact identity differs')
    if permanent:
        state.common.download(entry, archive)
    else:
        require(metadata is not None and not metadata['expired'], 'Original benchmark unavailable')
        with archive.open('xb') as stream:
            subprocess.run(['gh', 'api', 'repos/Melihakbulut221/nssoc/actions/artifacts/'+str(entry['id'])+'/zip'],
                           stdout=stream, check=True)
    state.common.verify_file(archive, entry)
    return dict(verified_zip=pin(archive), metadata_available=metadata is not None,
                source='exact_permanent_asset' if permanent else 'exact_original_artifact')


def parsed_costs(directory, plan, shard, *, create_logs=False):
    text = (directory/f'shard{shard}.log').read_text()
    rows = part.parse_shard(text, plan, shard, directory, write_logs=create_logs)
    costs = re.findall(r'^NSSOC_BIT_MILLISECONDS (\S+) ([0-9]+)$', text, re.M)
    require([n for n, _ in costs] == [x['id'] for x in rows], 'Missing/duplicated per-bit costs')
    for row, (_, ms) in zip(rows, costs, strict=True):
        block = (directory/(row['id']+'.log')).read_text()
        sizes = re.findall(r'Solving problem with ([0-9]+) variables and ([0-9]+) clauses', block)
        require(len(sizes) == 1, 'Missing/ambiguous native CNF census')
        row.update(elapsed_milliseconds=int(ms), sat_variables=int(sizes[0][0]), sat_clauses=int(sizes[0][1]))
    return rows


def replay_controls(directory, controls):
    for name in ('equal', 'wrong_clock', 'wrong_output'):
        root = directory/name
        plan = json.loads((root/'plan.json').read_text())
        captured = json.loads((root/'groups.json').read_text())
        actual = []
        for shard in range(4):
            groups = parsed_costs(root, plan, shard)
            require(groups == captured[shard]['groups'] and captured[shard]['shard'] == shard,
                    'Tiny raw control verdict differs')
            actual.append(dict(shard=shard, groups=groups))
        verdict = part.aggregate(plan, actual)
        require(verdict == controls[name] and verdict['state_bijection_proved'] == (name == 'equal')
            and all(g['verdict'] != TIMEOUT for r in actual for g in r['groups']), 'Tiny control failed or timed out')
        if name != 'equal':
            require(any(g['verdict'] == CEX for r in actual for g in r['groups']), 'Negative control has no counterexample')
    return controls


def verify_benchmark(directory, locked, refined, previous):
    state.common.verify_file(directory/'result.json', locked['benchmark']['result'])
    row = json.loads((directory/'result.json').read_text())
    require(row['status'] == 'BOUNDED_BIT_BENCHMARK_COMPLETE'
        and row['github_source_commit'] == locked['benchmark']['source_commit']
        and row['methods'] == locked['source_method_pins'] and row['complete_inputs_rechecked'] is True
        and row['runtime'] == locked['runtime'] and row['prior_common_miter'] == locked['refined_miter'],
        'Original benchmark is incomplete or changed')
    part.verify_inventory(directory, row['outputs'])
    for name, value in row['methods'].items():
        state.common.verify_file(directory/'methods'/name, value)
        state.common.verify_file(ROOT/name, value)
        raw = subprocess.check_output(['git', 'show', row['github_source_commit']+':'+name], cwd=ROOT)
        require(hashlib.sha256(raw).hexdigest() == value['sha256'], 'Original Git method differs')
    require(json.loads((directory/'preserved-proof-coverage.json').read_text()) == json.loads(json.dumps(previous)),
            'Original preserved proof coverage differs')
    selection = json.loads((directory/'selection.json').read_text())
    require(selection == bench.load_lock()['selected'] == bench.choose_representatives(previous['remaining']),
            'Benchmark observation selection differs')
    plan = bench.observation_plan(refined, selection)
    require(json.loads((directory/'plan.json').read_text()) == plan
        and (directory/'observations.v').read_text() == bench.wrapper(refined, selection),
        'Benchmark wrapper or symbolic interface changed')
    records = []
    for shard in range(4):
        execution = json.loads((directory/f'shard{shard}-execution.json').read_text())
        script = (directory/f'shard{shard}.tcl').read_text()
        match = re.search(r'^yosys \{read_rtlil "([^"]+)"\}', script)
        require(match is not None and execution['returncode'] == 0, 'Incomplete benchmark native traversal')
        require(script == bench.timed_script(Path(match[1]), plan, shard, Path(execution['command'][-1]).parent, 120),
                'Benchmark native script changed')
        require(pin(directory/f'shard{shard}.tcl') == execution['script']
            and pin(directory/f'shard{shard}.log') == execution['log'], 'Benchmark execution pin differs')
        records.append(dict(shard=shard, groups=parsed_costs(directory, plan, shard), execution=execution))
    require(records == json.loads((directory/'groups.json').read_text()), 'Benchmark raw results differ')
    verdict = bench.benchmark_verdict(plan, selection, records, len(previous['proved']), previous['original_bits'])
    require(all(row[k] == value for k, value in verdict.items()), 'Benchmark verdict differs')
    replay_controls(directory/'controls', row['controls'])
    require(row['selected_proved_bits'] == 12 and row['selected_timeouts'] == 4
        and row['selected_counterexamples'] == 0, 'Unexpected original benchmark outcome')
    return verdict


def catalog(previous, benchmark):
    """Set partition by ORIGINAL port/bit, never by recycled batch-local names."""
    proved = [tuple(x) for x in previous['proved']]
    remaining = previous['remaining']
    by_original = {tuple(x['original']): x for x in remaining}
    require(len(proved) == len(set(proved)) and len(by_original) == len(remaining)
        and not set(proved)&set(by_original) and len(proved)+len(remaining) == previous['original_bits'],
        'Previous proof partition overlaps, duplicates or omits bits')
    selected = benchmark['per_bit']
    require(len(selected) == len({tuple(x['original']) for x in selected})
        and len(selected) == benchmark['selected_bits'], 'Duplicated selected identity')
    passed, hard = [], []
    for row in selected:
        key = tuple(row['original'])
        require(key in by_original and all(row[k] == by_original[key][k] for k in ('parent', 'bit', 'original')),
                'Selected bit is not the corresponding original unproved bit')
        require(row['native_returncode'] == 0 and row['verdict'] in {PASS, TIMEOUT},
                'Prior counterexample or native failure cannot be hidden')
        (passed if row['verdict'] == PASS else hard).append(by_original[key])
    chosen = {tuple(x['original']) for x in selected}
    untested = sorted((x for k, x in by_original.items() if k not in chosen), key=lambda x: tuple(x['original']))
    require(len(passed) == benchmark['selected_proved_bits'] and len(hard) == benchmark['selected_timeouts'],
            'Benchmark count differs from exact identities')
    preserved = sorted(proved+[tuple(x['original']) for x in passed])
    universe = set(proved)|set(by_original)
    parts = [set(preserved), {tuple(x['original']) for x in untested}, {tuple(x['original']) for x in hard}]
    require(sum(map(len, parts)) == len(universe) and set().union(*parts) == universe,
            'New proof partition is not disjoint and exhaustive')
    return dict(original_bits=previous['original_bits'], preserved_proved=[list(x) for x in preserved],
                benchmark_proved=passed, untested=untested, hard=hard)


def validate_catalog(value, locked):
    require(value['original_bits'] == locked['original_bits'] and len(value['preserved_proved']) == locked['preserved_proved']
        and len(value['benchmark_proved']) == locked['benchmark_proved'] and len(value['untested']) == locked['untested']
        and len(value['hard']) == locked['hard'] and canonical(value['untested']) == locked['untested_canonical_sha256']
        and [x['original'] for x in value['hard']] == locked['hard_original_bits'], 'Source-bound complete catalog differs')
    all_bits = [tuple(x) for x in value['preserved_proved']]+[tuple(x['original']) for x in value['untested']+value['hard']]
    require(len(all_bits) == len(set(all_bits)) == locked['original_bits'], 'Complete catalog duplicates original bits')
    return value


def batch_selection(value, shard, batch):
    require(type(shard) is int and 0 <= shard < 16 and type(batch) is int and 0 <= batch < 4,
            'Invalid shard/batch')
    assigned = value['untested'][shard::16]
    require(len(value['untested']) == 800 and len(assigned) == 50, 'Shard does not contain exactly50 obligations')
    start = sum(BATCHES[:batch])
    return [dict(x, id=f'{part.PREFIX}{i:04d}') for i, x in enumerate(assigned[start:start+BATCHES[batch]])]


def native_execute(runtime, script, directory, name, *, tcl=False, memory_bytes=6*1024**3):
    """No elapsed process timeout; per-bit SAT timeout is inside the reviewed Tcl."""
    def limit():
        resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    env = os.environ.copy()
    for key in ('GH_TOKEN', 'GITHUB_TOKEN', 'PYTHONPATH', 'PYTHONHOME'):
        env.pop(key, None)
    command = [str(runtime), 'yosys', '-Q', '-T', '-c' if tcl else '-s', str(script)]
    start = time.monotonic()
    with (directory/(name+'.log')).open('x') as stream:
        process = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT,
                                 stdin=subprocess.DEVNULL, env=env, preexec_fn=limit, check=False)
    row = dict(command=command, returncode=process.returncode, seconds=time.monotonic()-start,
               script=pin(script), log=pin(directory/(name+'.log')), memory_limit_bytes=memory_bytes)
    save(directory/(name+'-execution.json'), row)
    return row


def run_observations(runtime, source, refined, selected, directory, work, *, timeout=120, memory_bytes=6*1024**3):
    require(1 <= timeout <= 120, 'Unbounded SAT time budget')
    plan = bench.observation_plan(refined, selected)
    save(directory/'selection.json', selected); save(directory/'plan.json', plan)
    observed = directory/'observations.v'; observed.write_text(bench.wrapper(refined, selected))
    script = directory/'build.ys'; graph = work/'common-miter.il'; interface = work/'interface.json'
    script.write_text(ref.build_script(source, observed, graph, interface))
    execution = native_execute(runtime, script, directory, 'build', memory_bytes=memory_bytes)
    require(execution['returncode'] == 0, 'Native observation build failed')
    actual = part.validate_interface(json.loads(interface.read_text())['modules']['miter'], plan)
    require(actual['symbolic_input_bits'] == refined['symbolic_input_bits'], 'Native symbolic boundary changed')
    build = dict(source_graph=pin(source), graph=pin(graph), native_interface=actual, execution=execution)
    save(directory/'build.json', build)
    rows = []
    for shard in range(4):
        script = directory/f'shard{shard}.tcl'
        script.write_text(bench.timed_script(graph, plan, shard, directory, timeout))
        execution = native_execute(runtime, script, directory, f'shard{shard}', tcl=True, memory_bytes=memory_bytes)
        require(execution['returncode'] == 0, 'Native per-bit traversal failed')
        groups = parsed_costs(directory, plan, shard, create_logs=True)
        rows.append(dict(shard=shard, groups=groups, execution=execution))
        save(directory/'groups.json', rows)
        print(f'NSSOC_REMAINING_SUBSHARD_DONE {shard} '+str(len(groups)), flush=True)
    require(pin(source) == build['source_graph'] and pin(graph) == build['graph'], 'Native input/output graph changed')
    return build, rows


def native_controls(runtime, library, directory, work, memory_bytes=2*1024**3):
    left, _ = state.lift(state.fixture(), ['ff0', 'ff1'])
    wrong_clock = copy.deepcopy(left); wrong_clock['ports'][state.PREFIX+'ff_clk']['bits'][0] = '0'
    wrong_output = copy.deepcopy(left); wrong_output['ports']['output_q']['bits'][0] = '0'
    controls = {}
    for name, right in [('equal', left), ('wrong_clock', wrong_clock), ('wrong_output', wrong_output)]:
        output = directory/name; output.mkdir(); scratch = work/name; scratch.mkdir()
        plan = part.make_plan(left, right, 2)
        selected = [dict(parent=g['id'], bit=i, original=pair, id=f'{part.PREFIX}{j:04d}')
            for j, (g, i, pair) in enumerate((g, i, pair) for g in plan['groups'] for i, pair in enumerate(g['obligations']))]
        for tag, module in [('left', left), ('right', right)]:
            save(output/(tag+'.json'), dict(modules=dict(soc_top=part.alias_outputs(module, plan))))
        script = output/'original.ys'; source = output/'original.il'
        script.write_text(part.build_script(output/'left.json', output/'right.json', library, source, output/'original-interface.json'))
        require(native_execute(runtime, script, output, 'original', memory_bytes=memory_bytes)['returncode'] == 0,
                'Tiny original native build failed')
        _, rows = run_observations(runtime, source, plan, selected, output, scratch, timeout=10, memory_bytes=memory_bytes)
        controls[name] = part.aggregate(bench.observation_plan(plan, selected), rows)
    replay_controls(directory, controls)
    save(directory/'result.json', controls)
    return controls


def verify_old(bundle, locked):
    prepared, refined, previous = bench.verify_refinement(bundle/'prior', bench.load_lock())
    verdict = verify_benchmark(bundle/'benchmark', locked, refined, previous)
    value = validate_catalog(catalog(previous, verdict), locked)
    return prepared, refined, value


def prepare(output, work):
    require(os.environ.get('GITHUB_ACTIONS') == 'true', 'Full graph preparation is cloud-only')
    output, work = state.common.fresh_directory(output), state.common.fresh_directory(work)
    row = dict(status='PREPARING_EXHAUSTIVE_REMAINING_BITS', github_source_commit=os.environ.get('GITHUB_SHA'),
               state_bijection_proved=False, candidate_adopted=False, unresolved_four_state_boot_failure=True)
    try:
        locked = load_lock(); row['methods'] = source_snapshot(output, locked)
        row['original_runs'] = {k: run_identity(locked[k]) for k in ('refinement', 'benchmark')}
        prior = output/'prior'; prior.mkdir(); row['archive_acquisition'] = {}
        for name, entry in locked['refinement']['archives'].items():
            archive = work/(name+'.zip')
            row['archive_acquisition'][name] = acquire(locked['refinement'], entry, archive, permanent=True)
            ref.restore(archive, prior/name)
        archive = work/'benchmark.zip'
        row['archive_acquisition']['benchmark'] = acquire(locked['benchmark'], locked['benchmark']['artifact'], archive, permanent=True)
        ref.restore(archive, output/'benchmark')
        prepared, refined, value = verify_old(output, locked)
        save(output/'catalog.json', value); save(output/'refined-plan.json', refined)
        runtime = work/'runtime.AppImage'; state.common.download(locked['runtime'], runtime); runtime.chmod(0o755)
        library_lock = state.archived.validate_lock(json.loads((ROOT/state.archived.LOCK).read_text()))
        library_bundle = work/'library'; state.archived.restore(ROOT/library_lock['archive']['path'], library_bundle, library_lock)
        library = library_bundle/'pdk/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib'
        controls = output/'controls'; controls.mkdir(); scratch = work/'controls'; scratch.mkdir()
        row['controls'] = native_controls(runtime, library, controls, scratch)
        require(verify_old(output, locked) == (prepared, refined, value), 'Original inputs changed during preparation')
        verify_methods(output, row, locked); state.common.verify_file(runtime, locked['runtime'])
        for name, entry in library_lock['files'].items(): state.common.verify_file(library_bundle/name, entry)
        row.update(status='EXHAUSTIVE_REMAINING_INPUT_PREPARED', runtime=locked['runtime'], refined_miter=locked['refined_miter'],
            refined_plan=pin(output/'refined-plan.json'), catalog=pin(output/'catalog.json'), complete_inputs_rechecked=True)
    except BaseException as error:
        row.update(status='PREPARATION_FAILED_PRESERVED', error=repr(error)); raise
    finally:
        row['outputs'] = ref.inventory(output); save(output/'result.json', row)
    return row


def verify_prepared(bundle):
    locked = load_lock(); row = json.loads((bundle/'result.json').read_text())
    require(row['status'] == 'EXHAUSTIVE_REMAINING_INPUT_PREPARED' and row['complete_inputs_rechecked'] is True
        and row['github_source_commit'] == os.environ.get('GITHUB_SHA') and row['runtime'] == locked['runtime']
        and row['refined_miter'] == locked['refined_miter'] and row['state_bijection_proved'] is False
        and row['candidate_adopted'] is False and row['unresolved_four_state_boot_failure'] is True,
        'Incomplete/changed source preparation')
    part.verify_inventory(bundle, row['outputs']); verify_methods(bundle, row, locked)
    _, refined, value = verify_old(bundle, locked)
    require(json.loads((bundle/'catalog.json').read_text()) == value
        and json.loads((bundle/'refined-plan.json').read_text()) == refined
        and pin(bundle/'catalog.json') == row['catalog'] and pin(bundle/'refined-plan.json') == row['refined_plan'],
        'Prepared selection or refined plan differs')
    replay_controls(bundle/'controls', row['controls'])
    return row, refined, value, locked


def run_batch(bundle, shard, batch, output, work):
    require(os.environ.get('GITHUB_ACTIONS') == 'true', 'Actual full graph proof is cloud-only')
    output = state.common.fresh_directory(output); work.mkdir(parents=True, exist_ok=True)
    row = dict(status='PREPARING_REMAINING_BATCH', shard=shard, batch=batch,
               github_source_commit=os.environ.get('GITHUB_SHA'), candidate_adopted=False, state_bijection_proved=False,
               unresolved_four_state_boot_failure=True,
               native_paths=dict(bundle=str(bundle), output=str(output), work=str(work)))
    try:
        prepared, refined, value, locked = verify_prepared(bundle)
        selected = batch_selection(value, shard, batch)
        row.update(prepared_result=pin(bundle/'result.json'), methods=prepared['methods'], source_graph=locked['refined_miter'],
                   catalog=prepared['catalog'], selected=selected)
        save(output/'result.json', row)  # Attempted IDs survive a later native failure.
        runtime = work/'runtime.AppImage'
        if not runtime.exists(): state.common.download(locked['runtime'], runtime); runtime.chmod(0o755)
        state.common.verify_file(runtime, locked['runtime'])
        scratch = work/f'batch{batch}'; scratch.mkdir()
        build, groups = run_observations(runtime, bundle/'prior/common/common-miter.il', refined, selected, output, scratch)
        require(verify_prepared(bundle)[0] == prepared, 'Prepared source changed during batch')
        state.common.verify_file(runtime, locked['runtime'])
        row.update(status='ALL_ASSIGNED_BATCH_BITS_VISITED', build=build, groups=groups,
                   verdict=part.aggregate(bench.observation_plan(refined, selected), groups), complete_inputs_rechecked=True)
    except BaseException as error:
        row.update(status='BATCH_FAILED_OR_INCOMPLETE', error=repr(error)); raise
    finally:
        row['outputs'] = ref.inventory(output); save(output/'result.json', row)
    return row


def replay_batch(directory, prepared, refined, value):
    row = json.loads((directory/'result.json').read_text())
    require(row['status'] == 'ALL_ASSIGNED_BATCH_BITS_VISITED' and row['complete_inputs_rechecked'] is True
        and row['github_source_commit'] == prepared['github_source_commit'] and row['methods'] == prepared['methods']
        and row['source_graph'] == prepared['refined_miter'] and row['catalog'] == prepared['catalog']
        and row['candidate_adopted'] is False and row['state_bijection_proved'] is False
        and row['unresolved_four_state_boot_failure'] is True,
        'Incomplete/foreign batch cannot be merged')
    part.verify_inventory(directory, row['outputs'])
    selected = batch_selection(value, row['shard'], row['batch']); plan = bench.observation_plan(refined, selected)
    require(row['selected'] == selected and json.loads((directory/'selection.json').read_text()) == selected
        and json.loads((directory/'plan.json').read_text()) == plan
        and (directory/'observations.v').read_text() == bench.wrapper(refined, selected), 'Batch observation correspondence differs')
    require(row['build'] == json.loads((directory/'build.json').read_text())
        and row['build']['source_graph'] == prepared['refined_miter']
        and row['build']['native_interface']['symbolic_input_bits'] == refined['symbolic_input_bits'], 'Native build graph/interface differs')
    paths = {k: Path(v) for k, v in row['native_paths'].items()}
    require(set(paths) == {'bundle', 'output', 'work'} and all(p.is_absolute() for p in paths.values()),
            'Native path binding missing')
    script_expected = ref.build_script(paths['bundle']/'prior/common/common-miter.il',
        paths['output']/'observations.v', paths['work']/f'batch{row["batch"]}'/'common-miter.il',
        paths['work']/f'batch{row["batch"]}'/'interface.json')
    require((directory/'build.ys').read_text() == script_expected, 'Original refined build script changed')
    build = row['build']['execution']
    require(build['returncode'] == 0 and build['memory_limit_bytes'] == 6*1024**3
        and build['command'] == [str(paths['work']/'runtime.AppImage'), 'yosys', '-Q', '-T', '-s',
                                 str(paths['output']/'build.ys')], 'Observation native build identity failed')
    require(pin(directory/'build.ys') == build['script'] and pin(directory/'build.log') == build['log'], 'Build execution pin differs')
    groups = []
    for shard in range(4):
        execution = json.loads((directory/f'shard{shard}-execution.json').read_text())
        script = (directory/f'shard{shard}.tcl').read_text()
        require(execution['returncode'] == 0 and execution['memory_limit_bytes'] == 6*1024**3
            and pin(directory/f'shard{shard}.tcl') == execution['script']
            and pin(directory/f'shard{shard}.log') == execution['log'], 'Native execution incomplete or changed')
        match = re.search(r'^yosys \{read_rtlil "([^"]+)"\}', script)
        require(match is not None and Path(match[1]) == paths['work']/f'batch{row["batch"]}'/'common-miter.il'
            and execution['command'] == [str(paths['work']/'runtime.AppImage'), 'yosys', '-Q', '-T', '-c',
                                         str(paths['output']/f'shard{shard}.tcl')]
            and script == bench.timed_script(Path(match[1]), plan, shard, paths['output'], 120),
            'Native per-bit script differs')
        groups.append(dict(shard=shard, groups=parsed_costs(directory, plan, shard), execution=execution))
    require(groups == row['groups'] == json.loads((directory/'groups.json').read_text())
        and part.aggregate(plan, groups) == row['verdict'], 'Raw batch verdict differs')
    return row


def merged_verdict(value, batches):
    require(len(batches) == 64 and {(r['shard'], r['batch']) for r in batches}
        == {(s, b) for s in range(16) for b in range(4)}, 'Missing/duplicate cloud batch')
    observed = []
    for row in batches:
        selected = batch_selection(value, row['shard'], row['batch'])
        by_id = {x['id']: x for group in row['groups'] for x in group['groups']}
        require(len(by_id) == sum(len(g['groups']) for g in row['groups']) == len(selected)
            and set(by_id) == {x['id'] for x in selected}, 'Incomplete/duplicated batch bit verdict')
        for bit in selected:
            result = by_id[bit['id']]
            require(result['native_returncode'] == 0 and result['verdict'] in {PASS, TIMEOUT, CEX}, 'Invalid native bit result')
            observed.append(dict(original=bit['original'], parent=bit['parent'], bit=bit['bit'],
                cloud_shard=row['shard'], batch=row['batch'], verdict=result['verdict'], native_log=result['log']))
    expected = {tuple(x['original']) for x in value['untested']}
    require(len(observed) == len({tuple(x['original']) for x in observed}) == 800
        and {tuple(x['original']) for x in observed} == expected, 'Merged new proof is not exhaustive')
    counts = {v: sum(x['verdict'] == v for x in observed) for v in (PASS, TIMEOUT, CEX)}
    return dict(status='COUNTEREXAMPLE_PRESERVED_IN_NEW_BITS' if counts[CEX] else 'ALL_800_UNTESTED_BITS_VISITED_HARD_BITS_STILL_OPEN',
        original_bits=value['original_bits'],
        previous_proved_bits=len(value['preserved_proved']), new_proved_bits=counts[PASS],
        new_timeouts=counts[TIMEOUT], new_counterexamples=counts[CEX], untouched_hard_bits=value['hard'],
        total_proved_bits=len(value['preserved_proved'])+counts[PASS], remaining_unproved_bits=len(value['hard'])+800-counts[PASS],
        exact_new_bit_results=sorted(observed, key=lambda x: tuple(x['original'])), symbolic_input_bits=10828,
        no_internal_assumptions=True, state_bijection_proved=False, candidate_adopted=False,
        full_soc_functional_accepted=False, timing_accepted=False, manufacturing_approval=False,
        unresolved_four_state_boot_failure=True)


def aggregate(bundle, directories, output):
    result = dict(status='INCOMPLETE_BATCH_SET_OR_FAILED_REPLAY', state_bijection_proved=False,
                  candidate_adopted=False, unresolved_four_state_boot_failure=True)
    try:
        prepared, refined, value, _ = verify_prepared(bundle)
        require(len(directories) == 64, 'Missing/extra captured batch directory')
        rows = [replay_batch(d, prepared, refined, value) for d in directories]
        expected_preparation = pin(bundle/'result.json')
        require(all(r['prepared_result'] == expected_preparation for r in rows), 'Foreign prepared input result')
        result = merged_verdict(value, rows)
        result.update(github_source_commit=prepared['github_source_commit'], prepared_result=expected_preparation,
            methods=prepared['methods'], source_graph=prepared['refined_miter'], catalog=prepared['catalog'],
            batch_results={f'{r["shard"]}:{r["batch"]}': pin(d/'result.json') for r, d in zip(rows, directories, strict=True)})
    except BaseException as error:
        result['error'] = repr(error); save(output, result); raise
    save(output, result)
    require(result['new_counterexamples'] == 0, 'Counterexample preserved in new actual bit proof')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['prepare', 'batch', 'aggregate', 'controls'])
    parser.add_argument('--output', type=Path, required=True); parser.add_argument('--work', type=Path)
    parser.add_argument('--bundle', type=Path); parser.add_argument('--shard', type=int); parser.add_argument('--batch', type=int)
    parser.add_argument('--batch-root', type=Path); parser.add_argument('--runtime', type=Path); parser.add_argument('--liberty', type=Path)
    args = parser.parse_args()
    if args.phase == 'prepare': result = prepare(args.output.resolve(), args.work.resolve())
    elif args.phase == 'batch': result = run_batch(args.bundle.resolve(), args.shard, args.batch, args.output.resolve(), args.work.resolve())
    elif args.phase == 'aggregate':
        directories = sorted(p.parent for p in args.batch_root.rglob('result.json') if p.parent.name.startswith('alu-bits-shard-'))
        result = aggregate(args.bundle.resolve(), directories, args.output.resolve())
    else:
        args.output.mkdir(parents=True); args.work.mkdir(parents=True)
        result = native_controls(args.runtime.resolve(), args.liberty.resolve(), args.output.resolve(), args.work.resolve())
    print(result.get('status', 'PASS_TINY_NATIVE_REMAINING_CONTROLS'), flush=True)


if __name__ == '__main__':
    main()
