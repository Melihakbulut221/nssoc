#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Repair exact C10 setup/hold, export isolated state, and verify two fresh reloads.

Unchanged native controls, input pins and historical acceptance guards remain
mandatory. Successful execution is evidence completion, never timing signoff.
"""
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
import run_cloud_targeted_hold as targeted

shared = targeted.shared
endpoints = targeted.endpoints
policy = targeted.policy
require = targeted.require
STAGES = ('matched_before', 'after_hold', 'reload_first', 'reload_repeat')
SOURCES = targeted.SOURCES + (
    '.github/workflows/timing-combined-repair.yml',
    'scripts/run_cloud_combined_repair.py',
    'hw/soc/pnr/timing_combined_repair_step.tcl',
    'hw/soc/pnr/timing_combined_repair_helpers.tcl',
    'hw/soc/pnr/timing_combined_reload.tcl',
)
BASE_CAPTURE = shared.capture
VIEW_NAMES = {'soc_top.odb', 'soc_top.def', 'soc_top.sdc', 'soc_top.v'}


def capture(output, destination):
    """Extend only this new producer's capture with its two isolated large views."""
    output, destination = Path(output), Path(destination)
    row = BASE_CAPTURE(output, destination)
    for path in sorted((output/'run').glob('*-openroad-resizertimingpostgrt/candidate/*')):
        require(path.name in VIEW_NAMES and path.is_file() and not path.is_symlink(),
                'Unexpected candidate output')
        if path.suffix not in {'.odb', '.def'}:
            continue
        target = destination/path.relative_to(output)
        target.parent.mkdir(parents=True, exist_ok=True)
        with path.open('rb') as source, target.open('xb') as sink:
            size = os.fstat(source.fileno()).st_size
            remaining = size
            while remaining:
                data = source.read(min(1024**2, remaining))
                if not data:
                    break
                sink.write(data)
                remaining -= len(data)
        row['files'][str(path.relative_to(output))] = dict(
            bytes=target.stat().st_size, sha256=shared.common.sha(target),
            observed_source_bytes=size, source_truncated_during_copy=bool(remaining))
    row['candidate_export_scope'] = 'Isolated unadopted candidate; result.json determines rejection/review status.'
    shared.common.save(destination/'capture.json', row)
    return row


def measured(row):
    for key in ('setup_wns_seconds', 'hold_wns_seconds', 'setup_tns_seconds', 'hold_tns_seconds'):
        require(shared.seconds(row.get(key)) is not None, 'Missing finite timing metric')
    targeted.integers(row, ('recorded_ms', 'instance_count', *policy.COUNTS))
    result = {key[:-8]+'_ns': row[key]*1e9 for key in (
        'setup_wns_seconds', 'hold_wns_seconds', 'setup_tns_seconds', 'hold_tns_seconds')}
    result.update({key: row[key] for key in policy.COUNTS})
    return result


def guard_assessment(metrics, source, repeatable):
    before, final = measured(metrics['matched_before']), measured(metrics['reload_repeat'])
    original = policy.no_regression(source, final)
    matched = policy.no_regression(before, final)
    setup = policy.improved(before, final, 'setup')
    hold = policy.improved(before, final, 'hold')
    reviewable = repeatable and original and matched and setup and hold
    return dict(source_selected_metrics=source, matched_before=before, canonical_reloaded=final,
        no_regression_from_selected_c10=original, no_regression_from_matched_before=matched,
        setup_improved=setup, hold_improved=hold, exact_reload_repeatable=repeatable,
        aggregate_estimate_guard_passed=reviewable,
        disposition='ISOLATED_IMPROVEMENT_REQUIRES_SIGNOFF' if reviewable else 'REJECTED_ISOLATED_CANDIDATE',
        zero_violations=all(final[k] == 0 for k in policy.COUNTS),
        timing_accepted=False, candidate_adopted=False, manufacturing_approval=False,
        note='Unchanged historical guards are applied to fresh reloaded estimated timing. '
             'A rejected export may support a separately reviewed continuation; it is never the selected checkpoint.')


def validate_batches(step, row, expected_corners):
    initial = shared.exact_count(row['initial_instance_count'])
    budget = shared.exact_count(row['global_buffer_budget'])
    require(initial >= 32 and budget == initial*2//5, 'Original cumulative growth budget differs')
    require(row.get('setup_profile') == 'setup_batch4' and row.get('setup_call_count') == 1
            and row.get('hold_batch_limit') == 4, 'Combined recipe changed')
    require(0 <= row['setup_started_ms'] <= row['setup_finished_ms'], 'Setup interval differs')
    previous = json.loads((step/'after_setup-metrics.json').read_text())
    measured(previous)
    batches = row['hold_batches']
    require(isinstance(batches, list) and len(batches) <= 4, 'Hold batch limit exceeded')
    for index, batch in enumerate(batches, 1):
        directory = step/f'hold_batch_{index}'
        require(batch['index'] == index and batch['before'] == previous, 'Hold sequence differs')
        require(json.loads((directory/'invocation.json').read_text()) == batch, 'Raw batch receipt differs')
        require(0 <= batch['started_ms'] <= batch['finished_ms'], 'Invalid hold interval')
        for kind in ('selection', 'result'):
            require(shared.common.sha(directory/f'hold-targeted-{kind}.tcldict') == batch[kind+'_sha256'],
                    'Pinned hold receipt differs')
        selection, result = batch['selection'], batch['result']
        for key, value in dict(profile='hold_guarded_targeted', corners=sorted(expected_corners),
            setup_margin_ns=0.1, hold_margin_ns=0.15, allow_setup_violations=0,
            max_buffer_fraction=0.4, max_passes_per_endpoint=1, endpoint_limit=16,
            remaining_margin_repair_required=True, signoff=False).items():
            require(selection.get(key) == value, 'Hold guard changed: '+key)
        batch_initial = batch['before']['instance_count']
        require(selection['initial_instance_count'] == batch_initial
                and selection['global_buffer_budget'] == batch_initial*2//5,
                'Local guard no longer uses its fixed batch budget')
        targets = selection['targets']
        require(selection['negative_endpoints_all_corners_before'] == batch['before']['hold_violating_endpoints']
                and selection['selected_count'] == len(targets) <= 16
                and len({r['endpoint'] for r in targets}) == len(targets)
                and [r['endpoint'] for r in result['calls']] == [r['endpoint'] for r in targets],
                'Target coverage or call sequence differs')
        require(targets == sorted(targets, key=lambda r: (r['initial_slack_ns'], r['endpoint'])),
                'Native target priority reordered')
        for target in targets:
            require(target['worst_corner'] in expected_corners and target['initial_slack_ns'] < 0,
                    'Invalid native selected endpoint')
        require(result['initial_instance_count'] == batch_initial
                and result['global_buffer_budget'] == selection['global_buffer_budget']
                and result['actual_instance_growth'] == result['actual_instance_count']-batch_initial
                and result['remaining_buffer_budget'] == result['global_buffer_budget']-result['actual_instance_growth']
                and result['remaining_margin_repair_required'] is True and result['signoff'] is False,
                'Batch result changed its guards')
        for call in result['calls']:
            require(call['status'] in {'ONE_NATIVE_PASS_COMPLETE', 'NO_LONGER_NEGATIVE', 'GLOBAL_BUFFER_BUDGET_EXHAUSTED'},
                    'Unknown hold call outcome')
            if call['status'] != 'NO_LONGER_NEGATIVE':
                require(call['actual_instance_growth'] == call['actual_instance_count']-batch_initial
                        and 0 <= call['actual_instance_count']-initial <= budget,
                        'Cumulative per-endpoint budget exceeded')
        measured(batch['after'])
        require(0 <= result['actual_instance_count']-initial <= budget
                and 0 <= batch['after']['instance_count']-initial <= budget,
                'Cumulative batch budget exceeded')
        require(json.loads((step/f'hold_batch_{index}-metrics.json').read_text()) == batch['after'],
                'Post-route hold metrics differ')
        previous = batch['after']
    require(row['hold_stop_reason'] in {'FOUR_BATCH_LIMIT', 'NO_NEGATIVE_HOLD',
        'ORIGINAL_GROWTH_BUDGET_EXHAUSTED', 'NO_HOLD_PROGRESS'}, 'Unknown stop reason')
    if row['hold_stop_reason'] == 'FOUR_BATCH_LIMIT':
        require(len(batches) == 4, 'Stopped before configured batch budget')
    elif row['hold_stop_reason'] == 'NO_NEGATIVE_HOLD':
        require(previous['hold_violating_endpoints'] == 0, 'Unsubstantiated zero hold claim')
    elif row['hold_stop_reason'] == 'ORIGINAL_GROWTH_BUDGET_EXHAUSTED':
        require(previous['instance_count']-initial == budget, 'Budget not exhausted')
    else:
        require(bool(batches) and not hold_progress(batches[-1]['before'], previous), 'Stopped despite hold improvement')
    return dict(setup_profile='setup_batch4', setup_iterations_max=100, repairs_per_pass_max=4,
        hold_batches=len(batches), hold_stop_reason=row['hold_stop_reason'],
        initial_instance_count=initial, original_global_buffer_budget=budget,
        raw_receipts_pinned=True, target_rank_scope='Native pinned recipe selects across all corners; '
        'per-batch target receipts checked, complete independent endpoint tables retained at four main stages.')


def hold_progress(before, after):
    return (after['hold_wns_seconds'] > before['hold_wns_seconds']
        or after['hold_tns_seconds'] > before['hold_tns_seconds']
        or after['hold_violating_endpoints'] < before['hold_violating_endpoints'])


def validate_diagnostic(step, source_sdc_sha, expected_corners):
    step = Path(step)
    output = step.parent.parent
    gate = targeted.validate_targeted_controls(output)
    control = json.loads((step/'startup-control.json').read_text())
    require(control.get('status') == 'PASS_TINY_INDEPENDENT_RELOAD'
            and control['pid'] != control['parent_pid']
            and control['executable_sha256'] == targeted.NATIVE_IDENTITY['actual_elf']['sha256']
            and control['odb_sha256'] == shared.common.sha(output/'native-controls/targeted/tiny-after.odb')
            and control['sdc_sha256'] == shared.common.sha(output/'native-controls/targeted/after.sdc')
            == shared.common.sha(step/'startup-control.sdc'), 'Tiny independent reload gate differs')
    require((step/'startup-control.log').read_text().splitlines().count('NSSOC_COMBINED_STARTUP_CONTROL_PASS') == 1,
            'Tiny independent reload marker missing')
    row = json.loads((step/'combined-repair.json').read_text())
    require(row.get('schema') == 1 and row.get('status') == 'COMPLETE_DIAGNOSTIC_ONLY', 'Incomplete repair')
    require(all(row.get(k) is False for k in ('candidate_adopted', 'timing_accepted', 'manufacturing_approval', 'thresholds_changed')),
            'Combined run cannot adopt or waive timing')
    require(row.get('source_checkpoint_preserved') is True and row.get('estimated_global_route_only') is True,
            'Repair scope changed')
    require(row.get('sram_macro_count') == 32 and row.get('sram_placement_preserved') is True, 'SRAM preservation missing')
    stages = row['stages']
    require(tuple(s['name'] for s in stages) == STAGES, 'Four-stage sequence differs')
    checked = {s['name']: shared.validate_stage(step/s['name'], s, source_sdc_sha) for s in stages}
    loaded = {s['name']: endpoints.load_stage(step, s, expected_corners, source_sdc_sha) for s in stages}
    targeted.validate_baseline(checked['matched_before'], row['matched_before_census'])
    metrics = row['timing_metrics']
    require(set(metrics) == set(STAGES), 'Missing full-stage metrics')
    macro_inventory = None
    for name in STAGES:
        measured(metrics[name])
        require(json.loads((step/f'{name}-stage.json').read_text()) == stages[STAGES.index(name)]
                and json.loads((step/f'{name}-metrics.json').read_text()) == metrics[name], 'Stage sidecar differs')
        require(checked[name]['endpoint_names'] == checked['matched_before']['endpoint_names']
                and checked[name]['corner_names'] == checked['matched_before']['corner_names'], 'Endpoint identities changed')
        placement = list(shared.read_rows(step/name/'placement.tsv',
            ['instance', 'master', 'x_dbu', 'y_dbu', 'orientation', 'status']))
        require(len(placement) == len({r['instance'] for r in placement}) == metrics[name]['instance_count'],
                'Instance census differs')
        macros = {r['instance']: {k: r[k] for k in ('master', 'x_dbu', 'y_dbu', 'orientation')}
            for r in placement if r['master'] in {'SP6TSRAM512x64', 'DP8TSRAMDP256x16'}}
        require(len(macros) == 32, 'Expected source32 SRAM macros')
        if macro_inventory is None:
            macro_inventory = macros
        require(macros == macro_inventory, 'SRAM placement changed')
        require(metrics[name]['hold_violating_endpoints'] == checked[name]['negative_vertex_endpoints']
                and 0 <= metrics[name]['instance_count']-row['initial_instance_count'] <= row['global_buffer_budget'],
                'Native census or original cumulative budget differs')
    require(metrics['matched_before']['instance_count'] == row['initial_instance_count'], 'Original budget anchor changed')
    batches = validate_batches(step, row, expected_corners)
    candidate = row['candidate_files']
    require(set(candidate) == VIEW_NAMES and set(shared.file_inventory(step/'candidate')) == VIEW_NAMES,
            'Candidate views missing or unexpected')
    shared.verify_evidence_files(step/'candidate', candidate)
    require(candidate['soc_top.sdc']['sha256'] == source_sdc_sha
            and candidate['soc_top.v']['sha256'] == checked['after_hold']['fingerprints']['netlist'],
            'Export constraints/netlist differ from final in-memory state')
    processes = row['independent_reload_processes']
    require(len(processes) == 2 and len({p['pid'] for p in processes}) == 2
            and len({p['parent_pid'] for p in processes}) == 1
            and all(p['pid'] != p['parent_pid'] for p in processes), 'Independent reload process identity missing')
    for name, process in zip(STAGES[-2:], processes, strict=True):
        require(json.loads((step/f'{name}-process.json').read_text()) == process
                and process['odb_sha256'] == candidate['soc_top.odb']['sha256']
                and process['sdc_sha256'] == source_sdc_sha and process['repair_invocations'] == 0
                and process['executable_sha256'] == targeted.NATIVE_IDENTITY['actual_elf']['sha256'],
                'Reload input/native identity differs')
        require((step/f'{name}.log').read_text().splitlines().count('NSSOC_COMBINED_INDEPENDENT_RELOAD_COMPLETE '+name) == 1,
                'Reload completion marker absent')
        headroom = json.loads((step/f'{name}-headroom.json').read_text())
        targeted.integers(headroom, ('available_kib', 'parent_rss_kib', 'required_kib'))
        require(headroom['required_kib'] == max(2097152, (5*headroom['parent_rss_kib']+3)//4)
                and headroom['available_kib'] >= headroom['required_kib'], 'Native replay memory headroom missing')
    comparisons = {name: endpoints.compare(loaded[a], loaded[b]) for name, a, b in (
        ('repair_effect', 'matched_before', 'after_hold'),
        ('export_reload_effect', 'after_hold', 'reload_first'),
        ('independent_reload_repeat', 'reload_first', 'reload_repeat'),
        ('canonical_repair_effect', 'matched_before', 'reload_repeat'))}
    a, b = 'reload_first', 'reload_repeat'
    repeatable = (checked[a]['fingerprints'] == checked[b]['fingerprints']
        and loaded[a]['endpoints'] == loaded[b]['endpoints'] and loaded[a]['paths'] == loaded[b]['paths']
        and measured(metrics[a]) == measured(metrics[b])
        and all(checked['after_hold']['fingerprints'][k] == checked[a]['fingerprints'][k]
                for k in ('constraints', 'netlist', 'placement')))
    source = json.loads((output/'source-manifest.json').read_text())['selected_source_metrics']
    assessment = guard_assessment(metrics, source, repeatable)
    log = (step/'openroad-resizertimingpostgrt.log').read_text().splitlines()
    markers = [targeted.GATE, 'NSSOC_COMBINED_STARTUP_CONTROL_PASS_BEFORE_C10_LOAD',
               'NSSOC_COMBINED_SETUP_BATCH4_BEGIN', 'NSSOC_COMBINED_SETUP_BATCH4_END',
               'NSSOC_COMBINED_REPAIR_COMPLETE_NO_ADOPTION']
    require(all(log.count(m) == 1 for m in markers) and [log.index(m) for m in markers] == sorted(log.index(m) for m in markers),
            'Native repair lifecycle differs')
    for value in checked.values():
        del value['endpoint_names']
    return dict(native=row, targeted_native_gate=gate, startup_independent_reload_control=control,
        independently_checked_stages=checked,
        recipe_assessment=batches, full_endpoint_comparisons=comparisons,
        aggregate_guard_assessment=assessment, candidate_files=candidate,
        candidate_exported=True, candidate_adopted=False, timing_accepted=False, manufacturing_approval=False,
        scope='Exact100-iteration batch4 setup plus up to four guarded16-target hold batches. '
        'Isolated ODB/DEF retained even when guards reject. Fresh independent reloads gate reviewability; '
        'estimated global-route timing is not final route/RC, LVS, DRC or manufacturing signoff.')


def specification():
    return shared.DiagnosticSpec(name='combined_setup_hold_repair', sources=SOURCES,
        entrypoint='scripts/run_cloud_combined_repair.py', step='hw/soc/pnr/timing_combined_repair_step.tcl',
        validator=validate_diagnostic)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '_native_flow':
        targeted.specification = specification
        targeted.configure_native_environment(sys.argv)
    shared.capture = capture
    return shared.main(specification())


if __name__ == '__main__':
    raise SystemExit(main())
