#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""One isolated C10 syndrome buffer trial, with rejected views and no adoption."""
import argparse
import csv
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
import compare_full_hold_endpoints as endpoints
import run_cloud_hold_diagnostic as shared
import run_cloud_targeted_hold as targeted
import run_timing_experiments as policy

STAGES = ('matched_before', 'after_buffer', 'after_full_update')
HELPER = 'hw/soc/pnr/timing_xor_buffer_helpers.tcl'
FIXTURE = 'sw/tests/timing_xor_buffer_native.tcl'
SOURCES = targeted.SOURCES + (
    '.github/workflows/timing-xor-buffer.yml', 'scripts/run_cloud_xor_buffer.py',
    HELPER, FIXTURE, 'hw/soc/pnr/timing_xor_buffer_step.tcl',
)
MARKERS = ('NSSOC_XOR_NATIVE_GATE_PASS_BEFORE_C10_LOAD', 'NSSOC_XOR_INSERT_BEGIN',
           'NSSOC_XOR_INSERT_END', 'NSSOC_XOR_BUFFER_COMPLETE_NO_ADOPTION')
CANDIDATE = 'REJECTED_PENDING_INDEPENDENT_TIMING_AND_PHYSICAL_VALIDATION'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def graph(path):
    with Path(path).open() as stream:
        reader = csv.DictReader(stream, delimiter='\t')
        require(reader.fieldnames == ['kind', 'name', 'master', 'pin', 'net'], 'Unexpected graph columns')
        data = {}
        for row in reader:
            require(set(row) == set(reader.fieldnames) and None not in row.values(), 'Malformed graph row')
            key = (row['kind'], row['name'], row['pin'])
            require(key not in data and row['kind'] in {'instance', 'pin', 'net', 'port'}, 'Duplicate/unknown graph object')
            data[key] = (row['master'], row['net'])
    require(data, 'Empty connectivity graph')
    return data


def verify_contraction(before_path, after_path, insertion):
    before, after = graph(before_path), graph(after_path)
    require(all(insertion.get(k) == v for k, v in dict(original_net='_017423_',
        driver='_071517_/X', sink='_071519_/A', master='sg13g2_buf_2').items()), 'Wrong XOR target identity')
    buffer, new = insertion.get('buffer'), insertion.get('new_net')
    require(isinstance(buffer, str) and buffer.startswith('nssoc_xor_buf2')
            and isinstance(new, str) and new.startswith('nssoc_xor_bufnet'), 'Unexpected inserted object names')
    instances = {k[1]: v[0] for k, v in before.items() if k[0] == 'instance'}
    require(instances.get('_071517_') == 'sg13g2_xor2_1'
            and instances.get('_071519_') == 'sg13g2_xnor2_1', 'Original XOR masters differ')
    require(type(insertion.get('initial_instances')) is int and insertion['initial_instances'] == len(instances), 'Wrong initial graph instance count')
    require(('instance', buffer, '') not in before and ('net', new, '') not in before, 'Inserted objects already existed')
    require(after.get(('instance', buffer, '')) == ('sg13g2_buf_2', ''), 'Inserted master differs')
    require(after.get(('net', new, '')) == ('SIGNAL', ''), 'Inserted signal net missing')
    a, x = after.get(('pin', buffer, 'A')), after.get(('pin', buffer, 'X'))
    require(a is not None and x is not None and a[0] == 'INPUT:SIGNAL' and x[0] == 'OUTPUT:SIGNAL'
            and {a[1], x[1]} == {'_017423_', new}, 'Inserted buffer is not the exact directed branch')
    require(before.get(('pin', '_071517_', 'X')) == ('OUTPUT:SIGNAL', '_017423_')
            and before.get(('pin', '_071519_', 'A')) == ('INPUT:SIGNAL', '_017423_'), 'Original target pins differ')
    require(after.get(('pin', '_071517_', 'X')) == ('OUTPUT:SIGNAL', a[1])
            and after.get(('pin', '_071519_', 'A')) == ('INPUT:SIGNAL', x[1]), 'Inserted buffer direction reversed')
    def members(data, net):
        return {k for k, v in data.items() if k[0] in {'pin', 'port'} and v[1] == net}
    require(members(before, '_017423_') == {('pin', '_071517_', 'X'), ('pin', '_071519_', 'A')}, 'Original target is not single sink')
    require(members(after, a[1]) == {('pin', '_071517_', 'X'), ('pin', buffer, 'A')}
            and members(after, x[1]) == {('pin', buffer, 'X'), ('pin', '_071519_', 'A')}, 'Extra buffered branch load')
    for pin, kind in (('VDD', 'POWER'), ('VSS', 'GROUND')):
        original = before.get(('pin', '_071517_', pin))
        require(original is not None and original[0] == 'INOUT:'+kind and original[1]
                and before.get(('net', original[1], '')) == (kind, '')
                and after.get(('pin', buffer, pin)) == original, 'Inserted buffer power is floating or differs')
    contracted = {}
    for key, (master, net) in after.items():
        if key[0] in {'instance', 'pin'} and key[1] == buffer:
            if key[0] == 'pin' and key[2] not in {'A', 'X'}:
                require(master.endswith((':POWER', ':GROUND')), 'Unexpected extra buffer signal pin')
            continue
        if key == ('net', new, ''):
            continue
        contracted[key] = (master, '_017423_' if net == new else net)
    require(contracted == before, 'Buffer contraction changed original cells, pins, nets or top ports')
    return dict(original_instance_count=len(instances), inserted_instances=1,
                inserted_signal_nets=1, full_original_graph_preserved=True,
                noninverting_cell='sg13g2_buf_2')


def validate_gate(step, methods):
    gate = json.loads((step/'xor-gate.json').read_text())
    require(gate.get('status') == 'PASS_NATIVE_XOR_GATE' and gate.get('returncode') == 0, 'Native XOR gate failed')
    require(gate.get('native_identity') == targeted.NATIVE_IDENTITY, 'Native runtime chain differs')
    require(gate.get('fixture_sha256') == shared.common.sha(methods/FIXTURE)
            and gate.get('helper_sha256') == shared.common.sha(methods/HELPER), 'XOR gate sources differ')
    control = step/'xor-control'
    row = json.loads((control/'result.json').read_text())
    require(row.get('status') == 'PASS_NATIVE_XOR_BUFFER_CONTROL', 'Native XOR fixture failed')
    require(all(row.get(k) is True for k in ('missing_api_rejected', 'extra_fanout_rejected',
        'duplicate_rejected', 'original_graph_preserved', 'constraints_preserved', 'supply_connections_preserved')), 'Missing native negative control')
    require(sorted(row.get('corners', [])) == ['fast', 'slow', 'typical'], 'Tiny XOR fixture missing corner')
    require(all(row.get(k) is False for k in ('timing_accepted', 'candidate_adopted', 'manufacturing_approval')), 'Unsafe control acceptance')
    require(shared.common.sha(control/'before.sdc') == shared.common.sha(control/'after.sdc'), 'Fixture constraints changed')
    require(shared.common.sha(control/'before.tsv') == shared.common.sha(control/'contracted.tsv'), 'Native fixture graph proof differs')
    require((step/'xor-control.log').read_text().splitlines().count('PASS_NATIVE_XOR_BUFFER_CONTROL_NO_CHIP_ACCEPTANCE') == 1, 'Missing fixture native completion')
    for corner in row['corners']:
        require('Corner: '+corner in (control/(corner+'.rpt')).read_text(), 'Missing actual corner path report')
    return dict(native=gate, fixture=row,
                contraction=verify_contraction(control/'before.tsv', control/'after.tsv', row['insertion']))


def aggregate_policy(metrics, source):
    values = {}
    for name, data in metrics.items():
        values[name] = {key[:-8]+'_ns': data[key]*1e9 for key in
                       ('setup_wns_seconds', 'hold_wns_seconds', 'setup_tns_seconds', 'hold_tns_seconds')}
        values[name].update({key: data[key] for key in policy.COUNTS})
    before, after = values[STAGES[0]], values[STAGES[-1]]
    return dict(source_selected_metrics=source, matched_before=before, after_full_update=after,
                no_regression_from_matched_before=policy.no_regression(before, after),
                no_regression_from_selected_c10=policy.no_regression(source, after),
                aggregate_estimate_guard_passed=policy.eligible(before, after, source, 'setup'),
                setup_improved=policy.improved(before, after, 'setup'),
                candidate_adopted=False, timing_accepted=False)


def validate_metrics(data, checked):
    for key in ('setup_wns_seconds', 'hold_wns_seconds', 'setup_tns_seconds', 'hold_tns_seconds'):
        require(shared.seconds(data.get(key)) is not None, 'Missing finite XOR timing metric')
    for key in (*policy.COUNTS, 'instance_count'):
        shared.exact_count(data.get(key))
    require(data['hold_violating_endpoints'] == checked['negative_vertex_endpoints'],
            'Reported hold count differs from complete native endpoint export')


def validate_diagnostic(step, source_sdc_sha, expected_corners):
    step = Path(step)
    output = step.parent.parent
    gate = validate_gate(step, output/'methods')
    row = json.loads((step/'xor-buffer.json').read_text())
    require(row.get('schema') == 1 and row.get('status') == 'COMPLETE_DIAGNOSTIC_ONLY', 'Incomplete XOR trial')
    require(all(row.get(k) is False for k in ('candidate_adopted', 'timing_accepted', 'manufacturing_approval', 'thresholds_changed')), 'XOR trial cannot accept a chip')
    require(row.get('candidate_status') == CANDIDATE, 'Candidate must remain explicitly rejected')
    require(row.get('sram_macro_count') == 32 and row.get('sram_placement_preserved') is True
            and row.get('original_graph_preserved') is True and row.get('supply_connections_preserved') is True, 'Missing original design invariants')
    log = (step/'openroad-resizertimingpostgrt.log').read_text()
    require(all(log.splitlines().count(marker) == 1 for marker in MARKERS)
            and [log.index(marker) for marker in MARKERS] == sorted(log.index(marker) for marker in MARKERS), 'Missing or reordered XOR native markers')
    stages = row.get('stages', [])
    require(tuple(s.get('name') for s in stages) == STAGES, 'Incomplete XOR stages')
    checked, loaded = {}, {}
    for stage in stages:
        name = stage['name']
        checked[name] = shared.validate_stage(step/name, stage, source_sdc_sha)
        loaded[name] = endpoints.load_stage(step, stage, expected_corners, source_sdc_sha)
    first = checked[STAGES[0]]
    require(first['endpoint_count'] == 23527 and first['negative_vertex_endpoints'] == 113
            and sorted(first['corner_names']) == targeted.BASELINE_CENSUS['corners'], 'Original C10 baseline differs')
    require(all(c['endpoint_names'] == first['endpoint_names'] and c['corner_names'] == first['corner_names'] for c in checked.values()), 'XOR endpoint/corner identities changed')
    require(checked['after_buffer']['fingerprints'] == checked['after_full_update']['fingerprints'], 'Full timing update changed physical state')
    contraction = verify_contraction(step/'graph-before.tsv', step/'graph-after.tsv', row['insertion'])
    require(shared.common.sha(step/'graph-before.tsv') == shared.common.sha(step/'graph-contracted.tsv'), 'Native full graph contraction differs')
    metrics = row.get('timing_metrics', {})
    require(set(metrics) == set(STAGES), 'Missing XOR timing measurements')
    macro_reference = None
    for name in STAGES:
        data = metrics[name]
        validate_metrics(data, checked[name])
        placement = list(shared.read_rows(step/name/'placement.tsv', ['instance', 'master', 'x_dbu', 'y_dbu', 'orientation', 'status']))
        require(len({p['instance'] for p in placement}) == len(placement) == data['instance_count'], 'XOR instance count differs from raw placement')
        expected = contraction['original_instance_count'] + (name != STAGES[0])
        require(data['instance_count'] == expected, 'XOR ECO must add exactly one cell')
        macros = sorted((p['instance'], p['master'], p['x_dbu'], p['y_dbu'], p['orientation']) for p in placement
                        if p['master'] in {'SP6TSRAM512x64', 'DP8TSRAMDP256x16'})
        require(len(macros) == 32, 'Raw SRAM inventory differs')
        if macro_reference is None:
            macro_reference = macros
        require(macros == macro_reference, 'Raw SRAM placement changed')
    candidate = row.get('candidate_files', {})
    require(set(candidate) == {'soc_top.odb', 'soc_top.def', 'soc_top.v', 'soc_top.sdc'}, 'Incomplete rejected candidate views')
    shared.verify_evidence_files(step/'rejected-candidate', candidate)
    require(candidate['soc_top.sdc']['sha256'] == source_sdc_sha, 'Rejected candidate constraints changed')
    require(candidate['soc_top.v']['sha256'] == checked['after_full_update']['fingerprints']['netlist'], 'Rejected candidate netlist differs')
    source = json.loads((output/'source-manifest.json').read_text())['selected_source_metrics']
    comparisons = {
        'buffer_effect': endpoints.compare(loaded['matched_before'], loaded['after_buffer']),
        'cache_update_effect': endpoints.compare(loaded['after_buffer'], loaded['after_full_update']),
        'buffer_effect_after_full_update': endpoints.compare(loaded['matched_before'], loaded['after_full_update']),
    }
    for data in checked.values():
        del data['endpoint_names']
    return dict(native=row, native_control=gate, contraction=contraction,
                independently_checked_stages=checked, full_endpoint_comparisons=comparisons,
                aggregate_policy=aggregate_policy(metrics, source), candidate_adopted=False,
                timing_accepted=False, manufacturing_approval=False, thresholds_changed=False,
                scope='One buf2 branch ECO; rejected ODB/DEF retained for explicit future verification. No routing/RC/LVS/signoff acceptance.')


def specification():
    return shared.DiagnosticSpec(name='xor_buffer_trial', sources=SOURCES,
        entrypoint='scripts/run_cloud_xor_buffer.py', step='hw/soc/pnr/timing_xor_buffer_step.tcl',
        validator=validate_diagnostic)


def configure_native_environment(argv):
    require(argv.count('--force-run-dir') == 1, 'One isolated XOR run directory required')
    run = Path(argv[argv.index('--force-run-dir')+1]).resolve()
    require(run.name == 'run', 'Unexpected XOR run directory')
    output = run.parent
    record = json.loads((output/'result.json').read_text())
    manifest = shared.verify_inputs(output, record, specification())
    base = json.loads((output/'native-controls/result.json').read_text())
    require(record['runtime_sha256'] == targeted.RUNTIME_SHA
            and base['command'][0] == targeted.NATIVE_IDENTITY['launcher']['path']
            and base['native_executable_sha256'] == targeted.NATIVE_IDENTITY['launcher']['sha256'], 'XOR runtime/base launcher differs')
    os.environ['NSSOC_TARGETED_PDK_ROOT'] = str(Path(record['work'])/'bundle'/manifest['pdk_root'])
    for name, pin in targeted.NATIVE_IDENTITY.items():
        for key, value in pin.items():
            os.environ[f'NSSOC_TARGETED_{name.upper()}_{key.upper()}'] = str(value)


def capture(output, destination):
    """Extend only this trial's capture with two explicitly rejected native views."""
    row = shared.capture(output, destination)
    output, destination = Path(output).resolve(), Path(destination).resolve()
    for path in sorted((output/'run').glob('*-openroad-resizertimingpostgrt/rejected-candidate/*')):
        if path.name not in {'soc_top.odb', 'soc_top.def'}:
            continue
        require(path.is_file() and not path.is_symlink(), 'Unsafe rejected candidate view')
        relative = path.relative_to(output)
        target = destination/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        require(not target.exists(), 'Rejected candidate capture collision')
        with path.open('rb') as source, target.open('xb') as sink:
            size = os.fstat(source.fileno()).st_size
            remaining = size
            while remaining:
                chunk = source.read(min(1024**2, remaining))
                if not chunk:
                    break
                sink.write(chunk)
                remaining -= len(chunk)
        row['files'][str(relative)] = dict(bytes=target.stat().st_size, sha256=shared.common.sha(target),
            observed_source_bytes=size, source_truncated_during_copy=bool(remaining))
    row['rejected_candidate_only'] = True
    shared.common.save(destination/'capture.json', row)
    return row


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '_native_flow':
        configure_native_environment(sys.argv)
    if len(sys.argv) > 1 and sys.argv[1] == 'capture':
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument('--output', type=Path, required=True)
        parser.add_argument('--destination', type=Path, required=True)
        args = parser.parse_args(sys.argv[2:])
        capture(args.output, args.destination)
        return 0
    return shared.main(specification())


if __name__ == '__main__':
    raise SystemExit(main())
