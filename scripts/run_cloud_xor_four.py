#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Four fixed, measured C10 buffer targets; frozen pair utilities, no adoption."""
import argparse
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
import run_cloud_xor_pair as pair

shared, targeted, endpoints = pair.shared, pair.targeted, pair.endpoints
require = pair.require
STAGES = ('matched_before', 'after_first', 'after_second', 'after_third', 'after_fourth', 'after_full_update')
HELPER = 'hw/soc/pnr/timing_xor_four_helpers.tcl'
FIXTURE = 'sw/tests/timing_xor_four_native.tcl'
SOURCES = pair.SOURCES + ('.github/workflows/timing-xor-four.yml', 'scripts/run_cloud_xor_four.py',
                         HELPER, FIXTURE, 'hw/soc/pnr/timing_xor_four_step.tcl')
MARKERS = ('NSSOC_XOR_FOUR_NATIVE_GATE_PASS_BEFORE_C10_LOAD', 'NSSOC_XOR_INSERT_BEGIN',
           'NSSOC_XOR_INSERT_END', 'NSSOC_XNOR_INSERT_BEGIN', 'NSSOC_XNOR_INSERT_END',
           'NSSOC_FIXED_3_INSERT_BEGIN', 'NSSOC_FIXED_3_INSERT_END',
           'NSSOC_FIXED_4_INSERT_BEGIN', 'NSSOC_FIXED_4_INSERT_END', 'NSSOC_XOR_FOUR_COMPLETE_NO_ADOPTION')
TARGETS = {
    3: dict(driver='_072567_/Y', sink='_072570_/A', original_net='_018473_',
            driver_master='sg13g2_xnor2_1', sink_master='sg13g2_xnor2_1', prefix='nssoc_rf30_buf'),
    4: dict(driver='_074829_/Y', sink='_074831_/B', original_net='_020735_',
            driver_master='sg13g2_nand4_1', sink_master='sg13g2_xor2_1', prefix='nssoc_addr_buf'),
}
CANDIDATE = pair.CANDIDATE
capture = pair.capture


def verify_extra(before_path, after_path, row, index):
    require(type(index) is int and index in TARGETS and type(row.get('index')) is int
            and row['index'] == index, 'Only exact third/fourth target indices allowed')
    t = TARGETS[index]
    require(all(row.get(k) == t[k] for k in ('driver', 'sink', 'original_net'))
            and row.get('master') == 'sg13g2_buf_2', 'Wrong fixed target identity')
    before, after = pair.graph(before_path), pair.graph(after_path)
    buffer, new, net = row.get('buffer'), row.get('new_net'), t['original_net']
    require(isinstance(buffer, str) and buffer.startswith(t['prefix'])
            and isinstance(new, str) and new.startswith(t['prefix']+'net'), 'Wrong fixed object names')
    instances = {k[1]: v[0] for k, v in before.items() if k[0] == 'instance'}
    require(type(row.get('initial_instances')) is int and row['initial_instances'] == len(instances), 'Wrong fixed original cell count')
    require(('instance', buffer, '') not in before and ('net', new, '') not in before, 'Fixed objects already existed')
    driver_name, driver_pin = t['driver'].split('/')
    sink_name, sink_pin = t['sink'].split('/')
    driver, sink = ('pin', driver_name, driver_pin), ('pin', sink_name, sink_pin)
    require(instances.get(driver_name) == t['driver_master'] and instances.get(sink_name) == t['sink_master'], 'Fixed original masters differ')
    require(before.get(driver) == ('OUTPUT:SIGNAL', net) and before.get(sink) == ('INPUT:SIGNAL', net), 'Fixed original pins differ')
    def members(data, n):
        return {k for k, v in data.items() if k[0] in {'pin', 'port'} and v[1] == n}
    require(members(before, net) == {driver, sink}, 'Fixed target must have one exact sink')
    require(after.get(('instance', buffer, '')) == ('sg13g2_buf_2', '')
            and after.get(('net', new, '')) == ('SIGNAL', '')
            and after.get(('pin', buffer, 'A')) == ('INPUT:SIGNAL', new)
            and after.get(('pin', buffer, 'X')) == ('OUTPUT:SIGNAL', net)
            and after.get(driver) == ('OUTPUT:SIGNAL', new)
            and after.get(sink) == ('INPUT:SIGNAL', net), 'Fixed buffer direction/identity differs')
    require(members(after, new) == {driver, ('pin', buffer, 'A')}
            and members(after, net) == {sink, ('pin', buffer, 'X')}, 'Fixed branch extra/missing load')
    for pin, kind in (('VDD', 'POWER'), ('VSS', 'GROUND')):
        original = before.get(('pin', driver_name, pin))
        require(original is not None and original[0] == 'INOUT:'+kind and original[1]
                and before.get(('net', original[1], '')) == (kind, '')
                and after.get(('pin', buffer, pin)) == original, 'Fixed buffer power differs')
    contracted = {}
    for key, (master, connection) in after.items():
        if key[0] in {'instance', 'pin'} and key[1] == buffer:
            if key[0] == 'pin' and key[2] not in {'A', 'X'}:
                require(master.endswith((':POWER', ':GROUND')), 'Unexpected fixed buffer signal pin')
            continue
        if key == ('net', new, ''):
            continue
        contracted[key] = (master, net if connection == new else connection)
    require(contracted == before, 'Fixed contraction changed unrelated logic')
    return len(instances)


def verify_four(paths, insertions):
    require(len(paths) == 5 and isinstance(insertions, list) and len(insertions) == 4, 'Exactly four prescribed insertions required')
    proof = pair.verify_pair(*paths[:3], insertions[:2])
    initial = proof['original_instance_count']
    for index in (3, 4):
        require(verify_extra(paths[index-1], paths[index], insertions[index-1], index) == initial+index-1,
                'Four-buffer cumulative graph count differs')
    return dict(original_instance_count=initial, inserted_instances=4, inserted_signal_nets=4,
                full_original_graph_preserved=True, noninverting_cell='sg13g2_buf_2')


def validate_gate(step, methods):
    gate = json.loads((step/'xor-four-gate.json').read_text())
    require(gate.get('status') == 'PASS_NATIVE_XOR_FOUR_GATE' and gate.get('returncode') == 0
            and gate.get('native_identity') == targeted.NATIVE_IDENTITY, 'Four-buffer native/runtime gate failed')
    require(gate.get('fixture_sha256') == shared.common.sha(methods/FIXTURE)
            and gate.get('helper_sha256') == shared.common.sha(methods/HELPER), 'Four-buffer native gate sources differ')
    control = step/'xor-four-control'
    row = json.loads((control/'result.json').read_text())
    require(row.get('status') == 'PASS_NATIVE_XOR_FOUR_CONTROL', 'Native four-target fixture failed')
    flags = ('first_missing_sink_rejected', 'first_wrong_sink_rejected', 'missing_api_rejected', 'extra_fanout_rejected', 'duplicate_rejected', 'missing_sink_rejected',
             'wrong_sink_rejected', 'extra_second_sink_rejected', 'floating_power_rejected',
             'wrong_power_rejected', 'second_duplicate_rejected', 'original_graph_preserved',
             'constraints_preserved', 'supply_connections_preserved')
    require(all(row.get(k) is True for k in flags), 'Missing first/pair native negative control')
    controls = row.get('extra_target_controls')
    require(isinstance(controls, list) and len(controls) == 2, 'Missing third/fourth controls')
    for index, c in zip((3, 4), controls, strict=True):
        require(type(c.get('index')) is int and c['index'] == index
                and all(c.get(k) is True for k in ('missing_sink_rejected', 'wrong_sink_rejected',
                    'extra_sink_rejected', 'floating_power_rejected', 'duplicate_rejected', 'wrong_power_rejected')),
                'Missing fixed target native negative control')
    require(sorted(row.get('corners', [])) == ['fast', 'slow', 'typical'], 'Missing native fixture corner')
    require(all(row.get(k) is False for k in ('timing_accepted', 'candidate_adopted', 'manufacturing_approval')), 'Native fixture cannot adopt candidate')
    require(shared.common.sha(control/'before.sdc') == shared.common.sha(control/'after.sdc')
            and shared.common.sha(control/'before.tsv') == shared.common.sha(control/'contracted.tsv'), 'Native fixture constraints/graph changed')
    require((step/'xor-four-control.log').read_text().splitlines().count('PASS_NATIVE_XOR_FOUR_CONTROL_NO_CHIP_ACCEPTANCE') == 1, 'Missing native four-target completion')
    for corner in row['corners']:
        require('Corner: '+corner in (control/(corner+'.rpt')).read_text(), 'Missing actual native corner report')
    proof = verify_four([control/(n+'.tsv') for n in ('before', 'first', 'second', 'third', 'after')], row['insertions'])
    return dict(native=gate, fixture=row, contraction=proof)


def validate_diagnostic(step, source_sdc_sha, expected_corners):
    step = Path(step); output = step.parent.parent
    gate = validate_gate(step, output/'methods')
    row = json.loads((step/'xor-four.json').read_text())
    require(row.get('schema') == 1 and row.get('status') == 'COMPLETE_DIAGNOSTIC_ONLY'
            and row.get('candidate_status') == CANDIDATE, 'Incomplete/reclassified four-buffer trial')
    require(all(row.get(k) is False for k in ('candidate_adopted', 'timing_accepted', 'manufacturing_approval', 'thresholds_changed')), 'Four-buffer trial cannot accept chip')
    require(row.get('sram_macro_count') == 32 and all(row.get(k) is True for k in
            ('sram_placement_preserved', 'original_graph_preserved', 'supply_connections_preserved')), 'Missing original chip invariants')
    log = (step/'openroad-resizertimingpostgrt.log').read_text()
    require(all(log.splitlines().count(m) == 1 for m in MARKERS)
            and [log.index(m) for m in MARKERS] == sorted(log.index(m) for m in MARKERS), 'Missing/reordered native four-target markers')
    stages = row.get('stages', [])
    require(tuple(s.get('name') for s in stages) == STAGES, 'Incomplete four-target stages')
    checked, loaded = {}, {}
    for stage in stages:
        name = stage['name']
        checked[name] = shared.validate_stage(step/name, stage, source_sdc_sha)
        loaded[name] = endpoints.load_stage(step, stage, expected_corners, source_sdc_sha)
    first = checked[STAGES[0]]
    require(first['endpoint_count'] == 23527 and first['negative_vertex_endpoints'] == 113
            and sorted(first['corner_names']) == targeted.BASELINE_CENSUS['corners'], 'Original C10 baseline differs')
    require(all(c['endpoint_names'] == first['endpoint_names'] and c['corner_names'] == first['corner_names'] for c in checked.values()), 'Four-target endpoint/corner identities changed')
    require(checked['after_fourth']['fingerprints'] == checked['after_full_update']['fingerprints'], 'Full cache update changed physical state')
    proof = verify_four([step/(n+'.tsv') for n in ('graph-before', 'graph-first', 'graph-second', 'graph-third', 'graph-after')], row['insertions'])
    require(shared.common.sha(step/'graph-before.tsv') == shared.common.sha(step/'graph-contracted.tsv'), 'Native four-buffer contraction differs')
    metrics = row.get('timing_metrics', {})
    require(set(metrics) == set(STAGES), 'Missing four-buffer measurements')
    macro_reference = None
    for offset, name in enumerate(STAGES):
        data = metrics[name]; pair.validate_metrics(data, checked[name])
        placement = list(shared.read_rows(step/name/'placement.tsv', ['instance', 'master', 'x_dbu', 'y_dbu', 'orientation', 'status']))
        require(len({p['instance'] for p in placement}) == len(placement) == data['instance_count']
                == proof['original_instance_count']+min(offset, 4), 'Four-target cell count differs from raw placement')
        macros = sorted((p['instance'], p['master'], p['x_dbu'], p['y_dbu'], p['orientation']) for p in placement
                        if p['master'] in {'SP6TSRAM512x64', 'DP8TSRAMDP256x16'})
        require(len(macros) == 32, 'Raw four-target SRAM inventory differs')
        if macro_reference is None:
            macro_reference = macros
        require(macros == macro_reference, 'Raw four-target SRAM placement changed')
    candidate = row.get('candidate_files', {})
    require(set(candidate) == {'soc_top.odb', 'soc_top.def', 'soc_top.v', 'soc_top.sdc'}, 'Missing rejected views')
    shared.verify_evidence_files(step/'rejected-candidate', candidate)
    require(candidate['soc_top.sdc']['sha256'] == source_sdc_sha
            and candidate['soc_top.v']['sha256'] == checked['after_full_update']['fingerprints']['netlist'], 'Candidate netlist/constraints differ')
    source = json.loads((output/'source-manifest.json').read_text())['selected_source_metrics']
    comparisons = {b: endpoints.compare(loaded[a], loaded[b]) for a, b in zip(STAGES, STAGES[1:])}
    comparisons['total'] = endpoints.compare(loaded[STAGES[0]], loaded[STAGES[-1]])
    incremental = {b: pair.aggregate_policy(dict(matched_before=metrics[a], after_full_update=metrics[b]), source)
                   for a, b in zip(STAGES, STAGES[1:])}
    for c in checked.values():
        del c['endpoint_names']
    return dict(native=row, native_control=gate, contraction=proof, independently_checked_stages=checked,
                full_endpoint_comparisons=comparisons, incremental_policy=incremental,
                aggregate_policy=pair.aggregate_policy(metrics, source), candidate_adopted=False,
                timing_accepted=False, manufacturing_approval=False, thresholds_changed=False,
                scope='Four fixed buf2 ECOs with per-target measurements; no routing/RC/LVS/signoff acceptance.')


def specification():
    return shared.DiagnosticSpec(name='xor_four_trial', sources=SOURCES, entrypoint='scripts/run_cloud_xor_four.py',
                                 step='hw/soc/pnr/timing_xor_four_step.tcl', validator=validate_diagnostic)


def configure_native_environment(argv):
    require(argv.count('--force-run-dir') == 1, 'One isolated four-target run directory required')
    run = Path(argv[argv.index('--force-run-dir')+1]).resolve()
    require(run.name == 'run', 'Unexpected four-target run directory')
    output = run.parent; record = json.loads((output/'result.json').read_text())
    manifest = shared.verify_inputs(output, record, specification())
    base = json.loads((output/'native-controls/result.json').read_text())
    require(record['runtime_sha256'] == targeted.RUNTIME_SHA
            and base['command'][0] == targeted.NATIVE_IDENTITY['launcher']['path']
            and base['native_executable_sha256'] == targeted.NATIVE_IDENTITY['launcher']['sha256'], 'Four-target runtime/base launcher differs')
    os.environ['NSSOC_TARGETED_PDK_ROOT'] = str(Path(record['work'])/'bundle'/manifest['pdk_root'])
    for name, pin in targeted.NATIVE_IDENTITY.items():
        for key, value in pin.items():
            os.environ[f'NSSOC_TARGETED_{name.upper()}_{key.upper()}'] = str(value)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '_native_flow':
        configure_native_environment(sys.argv)
    if len(sys.argv) > 1 and sys.argv[1] == 'capture':
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument('--output', type=Path, required=True)
        parser.add_argument('--destination', type=Path, required=True)
        args = parser.parse_args(sys.argv[2:]); capture(args.output, args.destination)
        return 0
    return shared.main(specification())


if __name__ == '__main__':
    raise SystemExit(main())
