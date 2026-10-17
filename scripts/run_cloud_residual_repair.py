#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Continue the immutable margin candidate with one cap net and ten hold pins.

The original C10 inputs remain unchanged. The explicit candidate overlay is
verified independently, never substituted into the accepted C10 checkpoint.
"""
import csv
import json
import os
from pathlib import Path
import re
import shutil
import sys

sys.dont_write_bytecode = True
import run_cloud_combined_repair as parent
import run_cloud_eco_logic_proof as eco
import run_cloud_electrical_margin as previous

shared, common, targeted = parent.shared, parent.shared.common, parent.targeted
require = parent.require
LOCK = 'hw/soc/pnr/timing-residual-repair-input.lock.json'
HELPER = 'hw/soc/pnr/timing_residual_repair_helpers.tcl'
FIXTURE = 'sw/tests/timing_residual_repair_native.tcl'
ENTRY = 'scripts/run_cloud_residual_repair.py'
STEP = 'hw/soc/pnr/timing_residual_repair_step.tcl'
STAGES = ('candidate_before', 'after_residual', 'reload_first', 'reload_repeat')
BASELINE = 'hw/soc/pnr/timing_electrical_margin_baseline.tcl'
SOURCES = tuple(dict.fromkeys(previous.SOURCES + (LOCK, HELPER, FIXTURE, ENTRY, STEP, BASELINE,
    'hw/soc/pnr/timing_residual_reload.tcl',
    '.github/workflows/timing-residual-repair.yml')))
BASE_VALIDATE = shared.validate_capture
HOLD_ENDPOINTS = ('_135215_/D', '_131421_/D', '_132896_/D', '_131422_/D',
    '_131425_/D', '_131426_/D', '_131433_/D', '_132893_/D', '_132852_/D', '_132653_/D')


def lock(root):
    row = json.loads((Path(root)/LOCK).read_text())
    require(row.get('schema') == 1 and row['runtime_sha256'] == targeted.RUNTIME_SHA
            and row['manifest_sha256'] == eco.MANIFEST_SHA, 'Electrical input/runtime lock differs')
    require(row['targets'] == [dict(driver=f'fanout{x}', pin='X', net=f'net{x}') for x in (3120,)],
            'Electrical target set changed')
    require(row['repair_margins_percent'] == dict(slew=20, cap=20), 'Experimental repair margins changed')
    require(row['producer']['source_commit'] == 'fe348fd38c73b32c76157abdef95fd283155cb9e'
            and row['producer']['run_id'] == 37018611401, 'Electrical producer identity differs')
    require(set(row['candidate_files']) == parent.VIEW_NAMES, 'Missing source candidate views')
    graph = row['graph_evidence']
    require(graph['netlist_sha256'] == row['candidate_files']['soc_top.v']['sha256']
            and set(graph['targets']) == {x['driver'] for x in row['targets']}, 'Target graph source differs')
    witness = graph['native_instance_witness']
    require(witness['member_pin']['sha256'] == '7da1f99828fa46503a95b774cff5f5f4d0b422eea86a6088e226ea65e9a848ca' and witness['source_stage'] == 'candidate_before',
            'Native instance witness is not the exact candidate placement')
    native_names = {x['verilog_instance']: (x['odb_instance'], x['master']) for x in witness['instances']}
    require(len(native_names) == len(witness['instances']) == 4, 'Native SRAM name witness is incomplete')
    reverse_names = {name: logical for logical, (name, _) in native_names.items()}
    require(len(reverse_names) == 4, 'Native SRAM name witness is not bijective')
    witnessed = set()
    for target in row['targets']:
        item = graph['targets'][target['driver']]
        require(item['net'] == target['net'] and item['master'] == 'sg13g2_buf_1'
                and any(t['instance'] == t['odb_instance'] == target['driver']
                        and t['master'] == item['master'] and t['port'] == 'X' for t in item['terminals']),
                'Target graph driver differs')
        for term in item['terminals']:
            if term['odb_instance'] in reverse_names:
                require(term['instance'] == reverse_names[term['odb_instance']], 'Logical SRAM identity differs from witness')
            if term['instance'] in native_names:
                require((term['odb_instance'], term['master']) == native_names[term['instance']],
                        'Native terminal name does not match captured placement')
                witnessed.add(term['instance'])
            else:
                require(term['odb_instance'] == term['instance'], 'Unwitnessed native name substitution')
        terms = [tuple(t[k] for k in ('odb_instance', 'master', 'port')) for t in item['terminals']]
        require(len(terms) == len(set(terms)) and len(terms) >= 2, 'Invalid target terminal census')
    require(witnessed == set(native_names), 'Unused or omitted native SRAM identity witness')
    require(tuple(t['endpoint'] for t in row['hold_targets']) == HOLD_ENDPOINTS,
            'Source-bound hold endpoint set/order changed')
    require(row['hold_policy'] == dict(setup_margin_seconds=1e-10, hold_margin_seconds=2e-11,
        allow_setup_violations=False, max_passes=1, max_added_cells=32), 'Hold repair policy changed')
    for target in row['hold_targets']:
        cell = target['cell']
        require(cell['instance']+'/D' == target['endpoint'] and cell['master'] == 'sg13g2_dfrbpq_1'
                and target['after_seconds'] < 0 and {p['port'] for p in cell['ports']} == {'D','Q','CLK','RESET_B'},
                'Source hold cell or measured violation differs')
    return row


def equal_metrics(actual, expected):
    parent.measured(actual)
    require({k: v for k, v in actual.items() if k != 'recorded_ms'} == expected,
            'Candidate fresh baseline differs from immutable parent reload')


def guard(metrics, locked, repeatable, physical_preserved):
    before, after = parent.measured(metrics[STAGES[0]]), parent.measured(metrics[STAGES[-1]])
    sources = dict(selected_c10=locked['original_selected_metrics'],
                   matched_c10=locked['original_matched_metrics'],
                   combined_parent=locked['combined_parent_metrics'], electrical_first=locked['electrical_first_metrics'], candidate_before=before)
    guards = {key: parent.policy.no_regression(value, after) for key, value in sources.items()}
    electrical_gain = (after['slew_violations'] < before['slew_violations']
                       or after['capacitance_violations'] < before['capacitance_violations'])
    passed = all(guards.values()) and electrical_gain and repeatable and physical_preserved
    return dict(reference_metrics=sources, canonical_reloaded=after, no_regression=guards,
        electrical_improved=electrical_gain, exact_reload_repeatable=repeatable,
        protected_physical_objects_preserved=physical_preserved,
        aggregate_estimate_guard_passed=passed,
        disposition='ISOLATED_IMPROVEMENT_REQUIRES_SIGNOFF' if passed else 'REJECTED_ISOLATED_CANDIDATE',
        zero_violations=all(after[k] == 0 for k in parent.policy.COUNTS),
        candidate_adopted=False, timing_accepted=False, manufacturing_approval=False)


def protected_status(path):
    with Path(path).open() as stream:
        reader = csv.DictReader(stream, delimiter='\t')
        require(reader.fieldnames == ['kind', 'name', 'dont_touch', 'signal_type', 'connections'],
                'Unexpected protected-status columns')
        rows = {}
        for row in reader:
            require(set(row) == set(reader.fieldnames) and None not in row.values()
                    and row['kind'] in {'instance', 'net'} and row['dont_touch'] in {'0', '1'},
                    'Invalid protected status')
            key = (row['kind'], row['name'])
            require(key not in rows, 'Duplicate protected object')
            rows[key] = {k: row[k] for k in ('dont_touch', 'signal_type', 'connections')}
    require(rows, 'Missing physical status')
    return rows


def verify_protected(before, after):
    for key, row in before.items():
        require(after.get(key) == row, 'Original dont-touch/clock status or protected connection changed: '+str(key))
    return dict(original_objects=len(before), added_objects=len(after)-len(before),
                original_dont_touch_and_clock_objects_preserved=True)


def baseline_script(locked):
    """Bind expected metrics, physical hashes and measured terminal graphs."""
    def atom(text):
        require(isinstance(text, str) and re.fullmatch(r'(?:[A-Za-z0-9_./\[\]]|\\[\[\]])+', text),
                'Unsafe target graph Tcl atom')
        return '{'+text+'}'
    lines = ['# Generated only from the tracked immutable candidate lock.',
             'set nssoc_electrical_expected_metrics [dict create \\']
    for name, value in locked['baseline_metrics'].items():
        require(name.replace('_', '').isalnum() and type(value) in (int, float), 'Unsafe baseline metric')
        lines.append(f'    {name} {value!r} \\')
    lines += [']', 'set nssoc_electrical_expected_files [dict create \\']
    for name, digest in locked['baseline_fingerprints'].items():
        common.pin(dict(bytes=0, sha256=digest))
        lines.append(f'    {shared.FINGERPRINT_FILES[name]} {digest} \\')
    lines += [']', 'set nssoc_electrical_expected_targets [dict create \\']
    for driver, graph in locked['graph_evidence']['targets'].items():
        terms = ' '.join('[list '+' '.join(atom(term[k]) for k in ('odb_instance', 'master', 'port'))+']'
                         for term in graph['terminals'])
        lines.append(f'    {atom(driver)} [list {terms}] \\')
    lines += [']', 'set nssoc_residual_expected_hold [dict create \\']
    for target in locked['hold_targets']:
        lines.append(f"    {atom(target['endpoint'])} {target['after_seconds']!r} \\")
    return '\n'.join(lines+[']', ''])


def verify_source_hold_cells(netlist, locked):
    text = Path(netlist).read_text()
    for target in locked['hold_targets']:
        require(text.count(target['cell']['body']) == 1, 'Pinned hold cell body/connectivity differs')
    return True


def validate_hold_calls(calls, locked, initial, final):
    require(len(calls) == len(HOLD_ENDPOINTS), 'Missing residual hold attempts')
    previous_count = initial
    for target, call in zip(locked['hold_targets'], calls, strict=True):
        require(call['endpoint'] == target['endpoint'] and call['master'] == target['cell']['master'],
                'Residual hold target changed')
        require(all(call[k] == v for k,v in locked['hold_policy'].items()), 'Native hold safety policy changed')
        require(call['initial_instance_count'] == previous_count and
                0 <= call['actual_instance_count']-previous_count <= 32, 'Residual hold growth differs')
        require(type(call['native_calls']) is int, 'Native hold invocation count must be an integer')
        if call['native_calls'] == 1:
            require(call['status'] == 'ONE_NATIVE_PASS_COMPLETE' and call['initial_slack_seconds'] < 0,
                    'Unmeasured hold repair call')
        else:
            require(call['native_calls'] == 0 and call['status'] == 'NO_LONGER_NEGATIVE'
                    and call['initial_slack_seconds'] >= 0, 'Unsupported skipped hold call')
            require(call['actual_instance_count'] == previous_count, 'Skipped call mutated cells')
        previous_count = call['actual_instance_count']
    require(previous_count == final, 'Hold call counts do not explain final design')
    return dict(attempts=len(calls), native_calls=sum(c['native_calls'] for c in calls),
                setup_violation_permission=False, max_passes_per_pin=1)


def verify_graph(path, locked):
    rows = list(shared.read_rows(path, ['driver', 'net', 'instance', 'master', 'port']))
    actual = [tuple(row[k] for k in ('driver', 'net', 'instance', 'master', 'port')) for row in rows]
    expected = [(driver, graph['net'], *(term[k] for k in ('odb_instance', 'master', 'port')))
                for driver, graph in locked['graph_evidence']['targets'].items() for term in graph['terminals']]
    require(sorted(actual) == sorted(expected), 'Observed pre-repair target terminal graph differs')
    return dict(netlist_sha256=locked['graph_evidence']['netlist_sha256'],
                target_count=len(locked['targets']), terminal_count=len(actual), exact=True)


def validate_baseline_repeat(step, locked, source_sdc_sha, expected_corners):
    repeat = step/'baseline-repeat'
    stage = json.loads((repeat/'reload_first-stage.json').read_text())
    require(stage['name'] == 'reload_first', 'Independent baseline stage name differs')
    checked = shared.validate_stage(repeat/'reload_first', stage, source_sdc_sha)
    parent.endpoints.load_stage(repeat, stage, expected_corners, source_sdc_sha)
    metrics = json.loads((repeat/'reload_first-metrics.json').read_text())
    equal_metrics(metrics, locked['baseline_metrics'])
    require(checked['fingerprints'] == locked['baseline_fingerprints'], 'Independent baseline physical fingerprints differ')
    process = json.loads((repeat/'reload_first-process.json').read_text())
    require(process['pid'] != process['parent_pid'] and process['repair_invocations'] == 0
            and process['odb_sha256'] == locked['candidate_files']['soc_top.odb']['sha256']
            and process['sdc_sha256'] == source_sdc_sha
            and process['executable_sha256'] == targeted.NATIVE_IDENTITY['actual_elf']['sha256'],
            'Independent baseline native process differs')
    headroom = json.loads((repeat/'headroom.json').read_text())
    targeted.integers(headroom, ('available_kib', 'parent_rss_kib', 'required_kib'))
    require(headroom['required_kib'] == max(2097152, (5*headroom['parent_rss_kib']+3)//4)
            and headroom['available_kib'] >= headroom['required_kib'], 'Independent baseline memory headroom missing')
    lines = (repeat/'native.log').read_text().splitlines()
    require(lines.count('NSSOC_ELECTRICAL_INDEPENDENT_BASELINE_EXACT_BEFORE_REPAIR') == 1,
            'Independent pre-repair baseline completion missing')
    del checked['endpoint_names']
    return dict(process=process, stage=checked, metrics=metrics, headroom=headroom)


def validate_diagnostic(step, source_sdc_sha, expected_corners):
    step = Path(step); output = step.parent.parent; locked = lock(output/'methods')
    targeted.validate_targeted_controls(output)
    gate = json.loads((step/'electrical-control/result.json').read_text())
    require(gate.get('status') == 'PASS_NATIVE_ELECTRICAL_CONTROL'
            and gate['call']['slew_margin_percent'] == gate['call']['cap_margin_percent'] == 20
            and gate['real_capacitance_after'] < gate['real_capacitance_before'], 'Tiny native electrical gate failed')
    for key in ('missing_api_rejected', 'wrong_net_rejected', 'missing_driver_rejected',
                'dont_touch_rejected', 'wrong_graph_rejected', 'unescaped_name_rejected',
                'omitted_terminal_rejected', 'native_escaped_name_verified',
                'constraints_preserved', 'unrelated_driver_preserved'):
        require(gate.get(key) is True, 'Missing real native control: '+key)
    require((step/'electrical-control.log').read_text().splitlines().count(
        'PASS_NATIVE_ELECTRICAL_CONTROL_NO_CHIP_ACCEPTANCE') == 1, 'Native fixture completion missing')
    require(common.sha(step/'electrical-control/before.sdc') == common.sha(step/'electrical-control/after.sdc'),
            'Tiny fixture changed constraints')
    hold_gate = json.loads((step/'residual-control/result.json').read_text())
    require(hold_gate['status'] == 'PASS_NATIVE_RESIDUAL_CONTROL'
            and hold_gate['after_hold_seconds'] > hold_gate['before_hold_seconds'], 'Native hold control failed')
    for key in ('wrong_endpoint_rejected','missing_api_rejected','wrong_master_rejected',
                'protected_rejected','protected_driver_rejected','fixed_rejected','unplaced_rejected',
                'clock_rejected','geometry_rejected','native_setup_guard_preserved','constraints_preserved'):
        require(hold_gate.get(key) is True, 'Missing actual hold control: '+key)
    require((step/'residual-control.log').read_text().splitlines().count(
        'PASS_NATIVE_RESIDUAL_CONTROL_NO_CHIP_ACCEPTANCE') == 1, 'Native hold fixture completion missing')
    require(common.sha(step/'residual-control/before.sdc') == common.sha(step/'residual-control/after.sdc'),
            'Native hold fixture changed constraints')
    for field in ('call','setup_blocked_call'):
        control = hold_gate[field]
        require(control['native_calls'] == 1 and control['status'] == 'ONE_NATIVE_PASS_COMPLETE'
                and all(control[k] == v for k,v in locked['hold_policy'].items()), 'Actual hold control policy differs')
    blocked = hold_gate['setup_blocked_call']
    require(blocked['initial_instance_count'] == blocked['actual_instance_count'], 'Unsafe setup control inserted cells')
    require(hold_gate['call']['actual_instance_count'] > hold_gate['call']['initial_instance_count'],
            'Positive hold control inserted no real delay cell')
    row = json.loads((step/'residual-repair.json').read_text())
    require(row.get('status') == 'COMPLETE_DIAGNOSTIC_ONLY'
            and all(row.get(k) is False for k in ('candidate_adopted', 'timing_accepted', 'manufacturing_approval', 'thresholds_changed')),
            'Incomplete or unsafe electrical continuation')
    require(row['setup_repair_invocations'] == 0 and row['hold_repair_invocations'] == sum(c['native_calls'] for c in row['hold_calls'])
            and row['sram_macro_count'] == 32 and row['sram_placement_preserved'] is True
            and row['source_checkpoint_preserved'] is True and row['estimated_global_route_only'] is True,
            'Continuation scope or SRAM invariant changed')
    require(tuple(s['name'] for s in row['stages']) == STAGES, 'Electrical stage sequence changed')
    checked = {s['name']: shared.validate_stage(step/s['name'], s, source_sdc_sha) for s in row['stages']}
    loaded = {s['name']: parent.endpoints.load_stage(step, s, expected_corners, source_sdc_sha) for s in row['stages']}
    metrics = row['timing_metrics']; require(set(metrics) == set(STAGES), 'Missing electrical metrics')
    equal_metrics(metrics[STAGES[0]], locked['baseline_metrics'])
    require(checked[STAGES[0]]['fingerprints'] == locked['baseline_fingerprints'], 'Fresh candidate physical fingerprints differ')
    baseline_repeat = validate_baseline_repeat(step, locked, source_sdc_sha, expected_corners)
    graph = verify_graph(step/'before-target-graph.tsv', locked)
    hold_rows = list(shared.read_rows(step/'before-hold-targets.tsv',
                    ['endpoint','master','native_data_net','global_slack_seconds']))
    require(len(hold_rows) == 10, 'Incomplete observed hold targets')
    for actual, target in zip(hold_rows, locked['hold_targets'], strict=True):
        require(actual['endpoint'] == target['endpoint'] and actual['master'] == target['cell']['master']
                and actual['native_data_net'] and float(actual['global_slack_seconds']) == target['after_seconds'],
                'Observed source-bound hold endpoint differs')
    original_macros = None
    for name in STAGES:
        parent.measured(metrics[name])
        require(json.loads((step/f'{name}-stage.json').read_text()) == next(s for s in row['stages'] if s['name'] == name),
                'Raw stage receipt differs')
        require(json.loads((step/f'{name}-metrics.json').read_text()) == metrics[name], 'Raw electrical metrics differ')
        require(checked[name]['endpoint_names'] == checked[STAGES[0]]['endpoint_names']
                and checked[name]['corner_names'] == checked[STAGES[0]]['corner_names'], 'Endpoint identities changed')
        placement = list(shared.read_rows(step/name/'placement.tsv', ['instance', 'master', 'x_dbu', 'y_dbu', 'orientation', 'status']))
        macros = {r['instance']: {k: r[k] for k in ('master', 'x_dbu', 'y_dbu', 'orientation')} for r in placement
                  if r['master'] in {'SP6TSRAM512x64', 'DP8TSRAMDP256x16'}}
        require(len(macros) == 32, '32 actual SRAM macros required')
        if original_macros is None: original_macros = macros
        require(macros == original_macros and len(placement) == metrics[name]['instance_count'], 'Macro placement or instance census changed')
        require(metrics[name]['hold_violating_endpoints'] == checked[name]['negative_vertex_endpoints'], 'Hold endpoint census differs')
    calls = row['calls']; require(len(calls) == len(locked['targets']) == 1, 'Expected exactly one residual net call')
    previous = metrics[STAGES[0]]['instance_count']
    for target, call in zip(locked['targets'], calls, strict=True):
        require(call['driver'] == target['driver']+'/X' and call['net'] == target['net']
                and call['native_calls'] == 1 and call['initial_instance_count'] == previous
                and call['max_length_m'] == 0 and call['slew_margin_percent'] == call['cap_margin_percent'] == 20,
                'Native target/margin/invocation changed')
        require(0 <= call['actual_instance_count']-previous <= 256, 'Per-net growth exceeded bound')
        previous = call['actual_instance_count']
    hold_calls = validate_hold_calls(row['hold_calls'], locked, previous, metrics[STAGES[1]]['instance_count'])
    require(0 <= metrics[STAGES[1]]['instance_count']-103697 <= 41478, 'Original cumulative growth guard changed')
    for stage in STAGES:
        for endpoint in HOLD_ENDPOINTS:
            for corner in expected_corners:
                for delay in ('min','max'):
                    path = step/f'{stage}-{endpoint.replace("/","_")}-{corner}-{delay}.rpt'
                    require(path.is_file() and path.stat().st_size > 0, 'Missing full clock-expanded hold/setup path')
    protected = verify_protected(protected_status(step/'before-status.tsv'), protected_status(step/'after-status.tsv'))
    for stage in (STAGES[0], STAGES[1]):
        for target in locked['targets']:
            for corner in expected_corners:
                require((step/f'{stage}-{target["driver"]}-{corner}.rpt').is_file(), 'Missing per-corner driver electrical report')
    require(set(row['candidate_files']) == set(shared.file_inventory(step/'candidate')) == parent.VIEW_NAMES,
            'Exported candidate views differ')
    shared.verify_evidence_files(step/'candidate', row['candidate_files'])
    require(row['candidate_files']['soc_top.sdc']['sha256'] == source_sdc_sha
            and row['candidate_files']['soc_top.v']['sha256'] == checked[STAGES[1]]['fingerprints']['netlist'],
            'Export changed constraints or netlist')
    processes = row['independent_reload_processes']
    require(len(processes) == 2 and len({p['pid'] for p in processes}) == 2
            and len({p['parent_pid'] for p in processes}) == 1, 'Independent reload processes missing')
    for name, process in zip(STAGES[-2:], processes, strict=True):
        require(process['pid'] != process['parent_pid'] and process['repair_invocations'] == 0
                and process['odb_sha256'] == row['candidate_files']['soc_top.odb']['sha256']
                and process['sdc_sha256'] == source_sdc_sha
                and process['executable_sha256'] == targeted.NATIVE_IDENTITY['actual_elf']['sha256'], 'Independent reload source differs')
        require(json.loads((step/f'{name}-process.json').read_text()) == process, 'Raw reload process receipt differs')
        require((step/f'{name}.log').read_text().splitlines().count('NSSOC_COMBINED_INDEPENDENT_RELOAD_COMPLETE '+name) == 1,
                'Independent reload completion missing')
        require((step/f'{name}.log').read_text().splitlines().count('NSSOC_RESIDUAL_RELOAD_PATHS_COMPLETE '+name) == 1,
                'Fresh per-target min/max paths missing')
        headroom = json.loads((step/f'{name}-headroom.json').read_text())
        targeted.integers(headroom, ('available_kib', 'parent_rss_kib', 'required_kib'))
        require(headroom['required_kib'] == max(2097152, (5*headroom['parent_rss_kib']+3)//4)
                and headroom['available_kib'] >= headroom['required_kib'], 'Native replay memory headroom missing')
    comparisons = {name: parent.endpoints.compare(loaded[a], loaded[b]) for name, a, b in (
        ('electrical_effect', STAGES[0], STAGES[1]), ('export_reload_effect', STAGES[1], STAGES[2]),
        ('independent_reload_repeat', STAGES[2], STAGES[3]), ('canonical_effect', STAGES[0], STAGES[3]))}
    repeatable = (checked[STAGES[2]]['fingerprints'] == checked[STAGES[3]]['fingerprints']
        and loaded[STAGES[2]]['endpoints'] == loaded[STAGES[3]]['endpoints']
        and loaded[STAGES[2]]['paths'] == loaded[STAGES[3]]['paths']
        and parent.measured(metrics[STAGES[2]]) == parent.measured(metrics[STAGES[3]])
        and all(checked[STAGES[1]]['fingerprints'][k] == checked[STAGES[2]]['fingerprints'][k]
                for k in ('constraints', 'netlist', 'placement')))
    log = (step/'openroad-resizertimingpostgrt.log').read_text().splitlines()
    markers = ['NSSOC_ELECTRICAL_NATIVE_GATE_PASS_BEFORE_CANDIDATE_LOAD',
               'NSSOC_ELECTRICAL_BASELINE_EXACT_BEFORE_REPAIR',
               'NSSOC_ELECTRICAL_TWO_BASELINES_EXACT_BEFORE_REPAIR', 'NSSOC_ELECTRICAL_COMPLETE_NO_ADOPTION']
    require(all(log.count(m) == 1 for m in markers) and [log.index(m) for m in markers] == sorted(log.index(m) for m in markers),
            'Native lifecycle markers missing/reordered')
    for value in checked.values(): del value['endpoint_names']
    return dict(native=row, native_control=gate, native_hold_control=hold_gate,
        source_bound_hold_targets=hold_rows, hold_attempts=hold_calls, protected_status=protected,
        independent_pre_repair_baseline=baseline_repeat, exact_target_graph=graph,
        independently_checked_stages=checked, full_endpoint_comparisons=comparisons,
        aggregate_guard_assessment=guard(metrics, locked, repeatable, True),
        candidate_adopted=False, timing_accepted=False, manufacturing_approval=False,
        scope='One residual net repair and ten exact bounded hold endpoint attempts with setup permission false, original Liberty/SDC limits, actual SRAM placement, two independently reproduced baselines and two independent final GRT reloads. Limited logical proof is separately mandatory; final routing, RC, DRC/LVS and production qualification remain outside this diagnostic.')


def specification():
    return shared.DiagnosticSpec(name='candidate_residual_repair', sources=SOURCES,
        entrypoint=ENTRY, step=STEP, validator=validate_diagnostic)


def validate_parent_contract(producer, locked):
    require(producer['status'] == 'COMPLETE_DIAGNOSTIC_ONLY'
            and producer['diagnostic']['native']['candidate_files'] == locked['candidate_files'],
            'Parent candidate identity differs')
    equal_metrics(producer['diagnostic']['native']['timing_metrics']['reload_repeat'], locked['baseline_metrics'])
    require(producer['diagnostic']['independently_checked_stages']['reload_repeat']['fingerprints'] == locked['baseline_fingerprints'],
            'Parent canonical fingerprints differ')
    references = producer['diagnostic']['aggregate_guard_assessment']['reference_metrics']
    require(references == dict(selected_c10=locked['original_selected_metrics'],
                              matched_c10=locked['original_matched_metrics'],
                              combined_parent=locked['combined_parent_metrics'], candidate_before=locked['electrical_first_metrics']),
            'Historical producer guards changed')
    require(producer['diagnostic']['independently_checked_stages']['candidate_before']['fingerprints']['placement']
            == locked['graph_evidence']['native_instance_witness']['member_pin']['sha256'],
            'Native SRAM identity witness is not the original producer placement')


def prepare_overlay(output, record):
    """Only the cloud downloads full original evidence and replays its validator."""
    require(os.environ.get('GITHUB_ACTIONS') == 'true', 'Actual candidate work is cloud-only')
    locked = lock(output/'methods'); work = Path(record['work']); trial = locked['producer']
    archive = work/'producer.zip'; common.download(trial, archive)
    capture = work/'producer'; extraction = eco.extract_zip(archive, capture)
    methods = eco.verify_producer_sources(capture, trial)
    require(eco.execute([sys.executable, capture/'methods'/trial['entrypoint'], 'validate',
        '--directory', capture, '--manifest', output/'source-manifest.json'],
        output, 'original-capture-validation') == 0, 'Original source-bound full capture validation failed')
    producer = json.loads((capture/'result.json').read_text())
    validate_parent_contract(producer, locked)
    candidate = capture/trial['candidate_prefix']
    shared.verify_evidence_files(candidate, locked['candidate_files'])
    verify_source_hold_cells(candidate/'soc_top.v', locked)
    records = output/'producer-records'; records.mkdir()
    for name in ('capture.json', 'result.json', 'source-manifest.json', 'source-config.json', 'source-state.json'):
        shutil.copyfile(capture/name, records/name)
    source_rows = {}
    for name, source in locked['native_api_source']['files'].items():
        path = records/'native-api'/name; path.parent.mkdir(parents=True, exist_ok=True)
        common.download(source, path); source_rows[name] = eco.file_pin(path)
    baseline = output/'candidate-baseline.tcl'
    baseline.write_text(baseline_script(locked))
    record.update(original_capture_validation='PASS', producer=trial, producer_methods=methods,
        producer_extraction=extraction, producer_record_files=shared.file_inventory(records),
        candidate_overlay=dict(directory=str(candidate), files=locked['candidate_files'],
                               baseline_tcl=eco.file_pin(baseline)), native_api_sources=source_rows)
    common.save(output/'result.json', record)
    return candidate


def verify_overlay(output, record):
    locked = lock(output/'methods')
    require(record.get('original_capture_validation') == 'PASS' and record.get('producer') == locked['producer'],
            'Missing original candidate capture replay')
    overlay = record['candidate_overlay']; candidate = Path(overlay['directory'])
    require(overlay['files'] == locked['candidate_files'], 'Candidate overlay changed')
    shared.verify_evidence_files(candidate, overlay['files'])
    verify_source_hold_cells(candidate/'soc_top.v', locked)
    common.verify_file(output/'candidate-baseline.tcl', overlay['baseline_tcl'])
    return candidate


def native_environment(argv):
    targeted.specification = specification
    targeted.configure_native_environment(argv)
    output = Path(argv[argv.index('--force-run-dir')+1]).resolve().parent
    record = json.loads((output/'result.json').read_text()); candidate = verify_overlay(output, record)
    os.environ.update(NSSOC_ELECTRICAL_CANDIDATE_ODB=str(candidate/'soc_top.odb'),
        NSSOC_ELECTRICAL_CANDIDATE_SDC=str(candidate/'soc_top.sdc'),
        NSSOC_ELECTRICAL_ODB_SHA=record['candidate_overlay']['files']['soc_top.odb']['sha256'],
        NSSOC_ELECTRICAL_SDC_SHA=record['candidate_overlay']['files']['soc_top.sdc']['sha256'],
        NSSOC_ELECTRICAL_BASELINE_TCL=str(output/'candidate-baseline.tcl'))


def logic_proofs(output, record, manifest, candidate, repaired):
    work = Path(record['work']); methods = output/'methods'; app = work/'runtime.AppImage'
    before, liberty, macro = eco.bundle_inputs(work/'bundle', manifest)
    proofs = {}
    for name, left, right in (('parent-logic', before, candidate/'soc_top.v'),
                             ('electrical-logic', candidate/'soc_top.v', repaired)):
        command = [app, 'python', methods/eco.CHECKER, left, right,
                   '--liberty', liberty, '--macro-verilog', macro, '--output', output/name]
        shared.execute(list(map(str, command)), output, record, name, shared.clean_environment())
        proof = json.loads((output/name/'result.json').read_text())
        require(proof.get('status') == 'PASS within scope', 'Missing limited logical proof result')
        proofs[name] = dict(result=proof, files=shared.file_inventory(output/name),
                            before=eco.file_pin(left), after=eco.file_pin(right))
    return proofs


def worker(output, spec=None):
    output = Path(output); record = json.loads((output/'result.json').read_text()); spec = specification()
    try:
        require(record['status'] == 'PREPARED', 'Electrical worker requires prepared original C10 inputs')
        manifest = shared.verify_inputs(output, record, spec)
        candidate = prepare_overlay(output, record)
        work, methods = Path(record['work']), output/'methods'; app = str(work/'runtime.AppImage')
        policy = common.load_policy(work/'bundle', manifest)
        original_pins = policy.state_pins(output/'prepared/state.json')
        env = shared.clean_environment(); env['NSSOC_HOLD_DIAGNOSTIC_HELPER'] = str(methods/'hw/soc/pnr/timing_hold_reproducibility.tcl')
        controls = [app, 'python', str(methods/'sw/tests/hold_reproducibility_native.py'),
            str(output/'native-controls'), '--helper', str(methods/'hw/soc/pnr/timing_hold_reproducibility.tcl'),
            '--step', str(methods/'hw/soc/pnr/timing_hold_diagnostic_step.tcl'),
            '--fixture', str(methods/'sw/tests/timing_hold_reproducibility_native.tcl'),
            '--pdk-root', str(work/'bundle'/manifest['pdk_root'])]
        shared.execute(controls, output, record, 'native-controls', env)
        common.save(output/'native-control-validation.json', shared.validate_controls(output/'native-controls/result.json', record['method_files']))
        _, liberty, _ = eco.bundle_inputs(work/'bundle', manifest)
        shared.execute([app, 'python', str(methods/'sw/tests/eco_logic_native.py'), '--checker', str(methods/eco.CHECKER),
            '--liberty', str(liberty), '--output', str(output/'logic-controls')], output, record, 'logic-controls', env)
        require(json.loads((output/'logic-controls/result.json').read_text())['status'] == 'PASS_NATIVE_ECO_CONTROLS',
                'Native equation controls incomplete')
        shared.verify_inputs(output, record, spec); verify_overlay(output, record)
        command = [app, 'python', str(methods/ENTRY), '_native_flow', '--flow', 'HoldDiagnostics',
            '--manual-pdk', '--pdk-root', str(work/'bundle'/manifest['pdk_root']), '--pdk', manifest['pdk'],
            '--force-run-dir', str(output/'run'), '--from', 'OpenROAD.ResizerTimingPostGRT',
            '--to', 'OpenROAD.ResizerTimingPostGRT', '--with-initial-state', str(output/'prepared/state.json'),
            str(output/'prepared/config.json')]
        shared.execute(command, output, record, 'native-diagnostic', env)
        shared.verify_inputs(output, record, spec); verify_overlay(output, record); policy.verify_pins(original_pins)
        steps = list((output/'run').glob('*-openroad-resizertimingpostgrt'))
        require(len(steps) == 1, 'Missing unique electrical native step')
        source_sdc = Path(json.loads((output/'prepared/state.json').read_text())['sdc'])
        corners = json.loads((output/'source-config.json').read_text())['PNR_CORNERS']
        diagnostic = validate_diagnostic(steps[0], common.sha(source_sdc), corners)
        record['diagnostic'] = diagnostic; common.save(output/'result.json', record)
        proofs = logic_proofs(output, record, manifest, candidate, steps[0]/'candidate/soc_top.v')
        shared.verify_inputs(output, record, spec); verify_overlay(output, record); policy.verify_pins(original_pins)
        record['logic_proofs'] = proofs
        validate_proof_inputs(record, lock(output/'methods'), manifest)
        record.update(status='COMPLETE_DIAGNOSTIC_ONLY', completed=common.now(),
            sdc_sha256=common.sha(source_sdc), output_files=shared.file_inventory(output/'run'),
            control_output_files=shared.file_inventory(output/'native-controls'), logic_proofs=proofs,
            logic_control_files=shared.file_inventory(output/'logic-controls'))
        common.save(output/'result.json', record)
        return 0
    except BaseException as error:
        record.update(status='FAILED_PRESERVED', error=str(error), recorded=common.now())
        common.save(output/'result.json', record); print(str(error), file=sys.stderr); return 1


def validate_proof_inputs(row, locked, manifest):
    parent_proof, electrical = (row['logic_proofs'][name] for name in ('parent-logic', 'electrical-logic'))
    expected_parent = locked['candidate_files']['soc_top.v']
    expected_after = row['diagnostic']['native']['candidate_files']['soc_top.v']
    require(parent_proof['before'] == manifest['files'][eco.BEFORE]
            and parent_proof['after'] == electrical['before'] == expected_parent
            and electrical['after'] == expected_after, 'Logical proof input chain differs from original and exported netlists')
    for proof in (parent_proof, electrical):
        require(proof['result'].get('status') == 'PASS within scope', 'Missing limited logical proof result')
        sources = proof['result'].get('sources', {})
        for pin in (proof['before'], proof['after'], manifest['files'][eco.STANDARD], manifest['files'][eco.MACRO]):
            require(pin['sha256'] in sources.values(), 'Logical proof does not bind required input bytes')
    return True


def validate_capture(directory, manifest_path=None, spec=None):
    directory = Path(directory)
    row = BASE_VALIDATE(directory, manifest_path, specification())
    locked = lock(directory/'methods')
    require(row['producer'] == locked['producer'] and row['original_capture_validation'] == 'PASS', 'Original producer verification missing')
    shared.verify_evidence_files(directory/'producer-records', row['producer_record_files'])
    validate_parent_contract(json.loads((directory/'producer-records/result.json').read_text()), locked)
    require(row['candidate_overlay']['files'] == locked['candidate_files'], 'Source candidate changed')
    common.verify_file(directory/'candidate-baseline.tcl', row['candidate_overlay']['baseline_tcl'])
    shared.verify_evidence_files(directory/'logic-controls', row['logic_control_files'])
    require(set(row['logic_proofs']) == {'parent-logic', 'electrical-logic'}, 'Missing both actual limited ECO proofs')
    for name, proof in row['logic_proofs'].items():
        shared.verify_evidence_files(directory/name, proof['files'])
        require(json.loads((directory/name/'result.json').read_text()) == proof['result']
                and proof['result'].get('status') == 'PASS within scope'
                and row['native_runs'][name]['returncode'] == 0, 'Logical proof failed or source differed')
    validate_proof_inputs(row, locked, json.loads((directory/'source-manifest.json').read_text()))
    return row


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '_native_flow': native_environment(sys.argv)
    shared.worker = worker
    shared.capture = parent.capture
    shared.validate_capture = validate_capture
    return shared.main(specification())


if __name__ == '__main__':
    raise SystemExit(main())
