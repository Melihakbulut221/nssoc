#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""One bounded setup repair invocation with full hold exports; never adopt it."""
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
import compare_full_hold_endpoints as endpoints
import run_cloud_hold_diagnostic as shared

STAGES = ('matched_before', 'after_repair_native', 'after_setup', 'after_full_update')
COMPLETE_MARKER = 'NSSOC_SETUP_HOLD_PROBE_COMPLETE_NO_ADOPTION'
BEGIN_MARKER = 'NSSOC_SETUP_HOLD_PROBE_REPAIR_BEGIN'
END_MARKER = 'NSSOC_SETUP_HOLD_PROBE_REPAIR_END'
REPAIR_COMMAND = ['repair_timing', '-setup', '-setup_margin', '0.1',
                  '-max_iterations', '1', '-max_passes', '1',
                  '-max_repairs_per_pass', '4', '-repair_tns', '100',
                  '-max_buffer_percent', '40', '-skip_buffer_removal',
                  '-skip_size_down', '-skip_last_gasp', '-skip_crit_vt_swap', '-verbose']
SOURCES = shared.SOURCES + (
    '.github/workflows/timing-setup-probe.yml',
    'scripts/run_cloud_setup_probe.py', 'scripts/compare_full_hold_endpoints.py',
    'hw/soc/pnr/timing_setup_hold_probe_step.tcl',
)


def validate_repair(row, log):
    invocation = row.get('repair_invocation', {})
    if invocation.get('command') != REPAIR_COMMAND:
        raise ValueError('Probe does not use the exact reviewed setup command')
    for key, expected in {'call_count': 1, 'max_passes': 1,
                          'max_repairs_per_pass': 4, 'max_iterations': 1}.items():
        if type(invocation.get(key)) is not int or invocation[key] != expected:
            raise ValueError('Probe repair call/pass bounds differ')
    if invocation.get('allow_setup_violations') is not False:
        raise ValueError('Setup violation permission is not part of the probe')
    if any(invocation.get(key) is not True for key in ('skip_last_gasp', 'skip_crit_vt_swap')):
        raise ValueError('Post-loop setup repair sweeps must remain disabled')
    if invocation.get('native_setup_buffer_percentage_enforced') is not False:
        raise ValueError('Native max_buffer_percent does not bound setup repair')
    counts = {key: shared.exact_count(invocation.get(key)) for key in
              ('initial_instance_count', 'actual_instance_count', 'global_instance_growth_budget', 'actual_instance_growth')}
    if (counts['initial_instance_count'] < 32
            or counts['global_instance_growth_budget'] != counts['initial_instance_count']*2//5
            or counts['actual_instance_growth'] != counts['actual_instance_count']-counts['initial_instance_count']
            or counts['actual_instance_growth'] > counts['global_instance_growth_budget']):
        raise ValueError('Invalid or exceeded post-call net-instance-growth budget')
    started, finished, elapsed = (invocation.get(name) for name in ('started_ms', 'finished_ms', 'elapsed_ms'))
    if (any(type(value) is not int or value < 0 for value in (started, finished, elapsed))
            or finished < started or elapsed != finished-started):
        raise ValueError('Invalid native repair interval')
    if not isinstance(invocation.get('granularity'), str) or not invocation['granularity']:
        raise ValueError('Native pass granularity must be explicit')
    command_marker = 'NSSOC_SETUP_HOLD_PROBE_REPAIR_COMMAND ' + ' '.join(REPAIR_COMMAND)
    for marker in (BEGIN_MARKER, command_marker, END_MARKER, COMPLETE_MARKER):
        if log.splitlines().count(marker) != 1:
            raise ValueError('Missing or repeated native probe marker')
    if not log.index(BEGIN_MARKER) < log.index(command_marker) < log.index(END_MARKER) < log.index(COMPLETE_MARKER):
        raise ValueError('Native probe markers are reordered')
    return invocation


def validate_diagnostic(step, source_sdc_sha, expected_corners):
    step = Path(step)
    row = json.loads((step/'setup-probe.json').read_text())
    if row.get('schema') != 1 or row.get('status') != 'COMPLETE_DIAGNOSTIC_ONLY':
        raise ValueError('Incomplete setup probe')
    if any(row.get(key) is not False for key in ('timing_accepted', 'candidate_adopted', 'manufacturing_approval', 'thresholds_changed')):
        raise ValueError('A setup probe cannot grant acceptance')
    if type(row.get('sram_macro_count')) is not int or row['sram_macro_count'] != 32 or row.get('sram_placement_preserved') is not True:
        raise ValueError('The original 32 SRAM placements must remain fixed')
    repair = validate_repair(row, (step/'openroad-resizertimingpostgrt.log').read_text())
    if json.loads((step/'repair-invocation.json').read_text()) != repair:
        raise ValueError('Probe repair receipt differs from the native standalone record')
    if row.get('provisional_stages') != ['after_repair_native']:
        raise ValueError('Pre-legalization route/cache stage must be explicitly provisional')
    stages = row.get('stages', [])
    if tuple(stage.get('name') for stage in stages) != STAGES:
        raise ValueError('Missing, reordered or extra setup probe stage')
    checked, loaded = {}, {}
    for stage in stages:
        name = stage['name']
        checked[name] = shared.validate_stage(step/name, stage, source_sdc_sha)
        loaded[name] = endpoints.load_stage(step, stage, expected_corners, source_sdc_sha)
    metrics = row.get('timing_metrics', {})
    if set(metrics) != set(STAGES):
        raise ValueError('Missing setup/electrical measurement stage')
    for name in STAGES:
        measurements = metrics[name]
        for field in ('setup_wns_seconds', 'hold_wns_seconds', 'setup_tns_seconds', 'hold_tns_seconds'):
            if shared.seconds(measurements.get(field)) is None:
                raise ValueError('Missing finite timing metric')
        for field in ('recorded_ms', 'setup_violating_endpoints', 'hold_violating_endpoints',
                      'slew_violations', 'capacitance_violations', 'instance_count'):
            shared.exact_count(measurements.get(field))
        placement = list(shared.read_rows(step/name/'placement.tsv',
                         ['instance', 'master', 'x_dbu', 'y_dbu', 'orientation', 'status']))
        if len({item['instance'] for item in placement}) != len(placement) or measurements['instance_count'] != len(placement):
            raise ValueError('Recorded instance count differs from full placement inventory')
        growth = measurements['instance_count']-repair['initial_instance_count']
        if growth < 0 or growth > repair['global_instance_growth_budget']:
            raise ValueError('A setup probe stage exceeds the fixed net-instance-growth budget')
    if (metrics['matched_before']['instance_count'] != repair['initial_instance_count']
            or metrics['after_repair_native']['instance_count'] != repair['actual_instance_count']):
        raise ValueError('Repair call instance counts differ from captured stages')
    expected_budget = dict(initial_instance_count=repair['initial_instance_count'],
        global_buffer_budget=repair['global_instance_growth_budget'],
        after_repair_instance_count=repair['actual_instance_count'],
        final_instance_count=metrics['after_full_update']['instance_count'],
        maximum_observed_growth=max(repair['actual_instance_growth'],
            metrics['after_full_update']['instance_count']-repair['initial_instance_count']), within_budget=True)
    if row.get('buffer_budget') != expected_budget:
        raise ValueError('Budget receipt differs from independently counted instances')
    first = checked[STAGES[0]]
    if set(first['corner_names']) != set(expected_corners) or not expected_corners:
        raise ValueError('Probe corners differ from selected C10 configuration')
    if any(value['endpoint_names'] != first['endpoint_names'] or value['corner_names'] != first['corner_names'] for value in checked.values()):
        raise ValueError('Probe endpoint or corner identities changed')
    if checked['after_setup']['fingerprints'] != checked['after_full_update']['fingerprints']:
        raise ValueError('Timing cache update mutated physical/parasitic state')
    comparisons = {
        'native_repair_effect': endpoints.compare(loaded['matched_before'], loaded['after_repair_native']),
        'legalization_and_rc_effect': endpoints.compare(loaded['after_repair_native'], loaded['after_setup']),
        'setup_effect': endpoints.compare(loaded['matched_before'], loaded['after_setup']),
        'cache_update_effect': endpoints.compare(loaded['after_setup'], loaded['after_full_update']),
        'setup_effect_after_cache_update': endpoints.compare(loaded['matched_before'], loaded['after_full_update']),
    }
    for value in checked.values():
        del value['endpoint_names']
    return dict(native=row, independently_checked_stages=checked, repair_invocation=repair,
                full_endpoint_comparisons=comparisons, candidate_adopted=False,
                timing_accepted=False, manufacturing_approval=False, thresholds_changed=False,
                scope='One setup invocation bounded by max_iterations=1, max_passes=1, max_repairs_per_pass=4, '
                      'disabled last-gasp/critical-VT sweeps and a post-call net-instance-growth guard. '
                      'This does not guarantee only four total physical changes and never promotes a candidate.')


def specification():
    return shared.DiagnosticSpec(name='setup_hold_probe', sources=SOURCES,
                                 entrypoint='scripts/run_cloud_setup_probe.py',
                                 step='hw/soc/pnr/timing_setup_hold_probe_step.tcl',
                                 validator=validate_diagnostic)


if __name__ == '__main__':
    raise SystemExit(shared.main(specification()))
