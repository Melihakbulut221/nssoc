#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Compare complete pinned native hold exports without changing acceptance rules."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import struct

NATIVE_NS = struct.unpack('!f', struct.pack('!f', 1e-9))[0]
REPRESENTATION = 'IEEE-754 binary32 promoted to Tcl double'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def file_pin(path):
    with path.open('rb') as stream:
        return dict(bytes=path.stat().st_size, sha256=hashlib.file_digest(stream, 'sha256').hexdigest())


def numeric(value):
    if value == 'UNCONSTRAINED':
        return None
    require(isinstance(value, str) and value.strip() == value and bool(value), 'Malformed slack')
    result = float(value)
    require(math.isfinite(result), 'Nonfinite slack')
    return result


def table(path, fields):
    with path.open(newline='') as stream:
        reader = csv.DictReader(stream, delimiter='\t')
        require(reader.fieldnames == fields, 'Unexpected table fields')
        for row in reader:
            require(None not in row and None not in row.values(), 'Truncated table')
            yield row


def load_stage(root, stage, expected_corners, expected_sdc_sha256):
    """Verify endpoint tables, native record, constraints, and native census."""
    name = stage.get('name')
    require(isinstance(name, str) and re.fullmatch(r'[a-z][a-z0-9_]*', name), 'Unsafe stage name')
    require(len(set(expected_corners)) == len(expected_corners) > 0, 'Expected corners missing or duplicated')
    require(re.fullmatch(r'[0-9a-f]{64}', expected_sdc_sha256), 'Invalid expected SDC digest')
    directory = Path(root)/name
    inventory = {}
    for filename in ('native.json', 'constraints.sdc', 'endpoints.tsv', 'hold-endpoints.tsv'):
        path = directory/filename
        require(not path.is_symlink(), 'Symlink evidence is unsupported')
        actual = file_pin(path)
        require(actual == stage['files'][filename], 'Evidence bytes differ: '+filename)
        inventory[filename] = actual
    native = json.loads((directory/'native.json').read_text())
    require(native == {key: val for key, val in stage.items() if key not in ('files', 'fingerprints')},
            'Stage record differs from native receipt')
    require(inventory['constraints.sdc']['sha256'] == expected_sdc_sha256
            == stage['fingerprints']['constraints'], 'Timing constraints differ')
    require(stage.get('all_endpoint_coverage') is True and stage.get('vertex_path_semantics_match') is True,
            'Native endpoint coverage not established')
    require(stage.get('time_unit_seconds') == 1e-9 and stage.get('native_time_unit_seconds') == NATIVE_NS
            and stage.get('time_unit_representation') == REPRESENTATION and stage.get('value_units') == 'seconds'
            and stage.get('numeric_format') == '%.17g', 'Invalid native time units or precision')
    endpoints = {}
    for row in table(directory/'endpoints.tsv', ['endpoint', 'global_vertex_slack_seconds']):
        endpoint = row['endpoint']
        require(endpoint and endpoint not in endpoints, 'Missing or duplicate endpoint')
        endpoints[endpoint] = numeric(row['global_vertex_slack_seconds'])
    require(bool(endpoints), 'Empty endpoint census')
    for field in ('endpoint_count', 'engine_endpoint_count', 'exported_endpoint_count'):
        require(type(stage.get(field)) is int and stage[field] == len(endpoints), 'Incomplete endpoint count')
    negative = sum(v is not None and v < 0 for v in endpoints.values())
    for field in ('negative_vertex_endpoints', 'engine_negative_vertex_endpoints'):
        require(type(stage.get(field)) is int and stage[field] == negative, 'Negative endpoint count differs')
    corner_records = stage['corners']
    require(len(corner_records) == len(expected_corners), 'Corner count differs')
    require({row['name'] for row in corner_records} == set(expected_corners), 'Incomplete corner census')
    paths = {corner: {} for corner in expected_corners}
    for row in table(directory/'hold-endpoints.tsv',
                     ['corner', 'endpoint', 'min_rise_seconds', 'min_fall_seconds', 'min_seconds']):
        corner, endpoint = row['corner'], row['endpoint']
        require(corner in paths and endpoint in endpoints, 'Unknown corner or endpoint')
        require(endpoint not in paths[corner], 'Duplicate endpoint/corner pair')
        triplet = tuple(numeric(row[field]) for field in ('min_rise_seconds', 'min_fall_seconds', 'min_seconds'))
        finite = [value for value in triplet[:2] if value is not None]
        require(triplet[2] == (min(finite) if finite else None), 'Rise/fall minimum differs')
        paths[corner][endpoint] = triplet
    for by_endpoint in paths.values():
        require(set(by_endpoint) == set(endpoints), 'Incomplete endpoint/corner Cartesian product')
    for endpoint, slack in endpoints.items():
        finite = [paths[corner][endpoint][2] for corner in paths if paths[corner][endpoint][2] is not None]
        require(slack == (min(finite) if finite else None), 'Global vertex versus corner values differ')
    recomputed = {}
    for corner in corner_records:
        values = [paths[corner['name']][endpoint][2] for endpoint in sorted(endpoints)]
        finite = [value for value in values if value is not None]
        negative_values = [value for value in finite if value < 0]
        folded = 0.0
        for value in negative_values:
            folded += value
        require(corner['constrained_endpoints'] == len(finite)
                and corner['unrepresented_endpoints'] == len(values)-len(finite)
                and corner['negative_path_endpoints'] == len(negative_values), 'Corner counts differ')
        require(corner['fixed_order_tns_seconds'] == folded, 'Fixed-order sum differs')
        require(bool(finite) and corner['native_wns_seconds'] == min(finite), 'Native WNS differs from complete export')
        for key in ('native_tns_seconds_before', 'native_tns_seconds_after'):
            require(type(corner[key]) in (int, float) and math.isfinite(corner[key]), 'Invalid native TNS')
        recomputed[corner['name']] = dict(
            constrained=len(finite), unconstrained=len(values)-len(finite), negative=len(negative_values),
            fsum_seconds=math.fsum(negative_values), fixed_order_seconds=folded,
            wns_seconds=min(finite), native_tns_before_seconds=corner['native_tns_seconds_before'],
            native_tns_after_seconds=corner['native_tns_seconds_after'])
    for phase in ('before', 'after'):
        require(stage[f'native_global_tns_seconds_{phase}'] == min(
            c[f'native_tns_seconds_{phase}'] for c in corner_records), 'Global native TNS is not minimum corner TNS')
    return dict(name=name, endpoints=endpoints, paths=paths, summary=recomputed,
                pins=inventory, sdc_sha256=expected_sdc_sha256)


def compare(before, after):
    require(set(before['endpoints']) == set(after['endpoints']), 'Endpoint identities changed; pair is not directly comparable')
    require(set(before['paths']) == set(after['paths']), 'Corner identities changed')
    require(before['sdc_sha256'] == after['sdc_sha256'], 'Different constraint contracts')
    columns = ('rise', 'fall', 'min')
    changes, summary = [], {}
    for corner in sorted(before['paths']):
        counts = {column: dict(changed=0, regressed=0, improved=0,
                              finite_to_unconstrained=0, unconstrained_to_finite=0) for column in columns}
        for endpoint in sorted(before['endpoints']):
            left, right = before['paths'][corner][endpoint], after['paths'][corner][endpoint]
            if left != right:
                changes.append(dict(corner=corner, endpoint=endpoint, before_seconds=left, after_seconds=right))
            for index, column in enumerate(columns):
                a, b = left[index], right[index]
                if a == b:
                    continue
                counts[column]['changed'] += 1
                if a is None:
                    counts[column]['unconstrained_to_finite'] += 1
                elif b is None:
                    counts[column]['finite_to_unconstrained'] += 1
                else:
                    counts[column]['regressed' if b < a else 'improved'] += 1
        a, b = before['summary'][corner], after['summary'][corner]
        summary[corner] = dict(columns=counts, before=a, after=b,
                               fsum_delta_seconds=b['fsum_seconds']-a['fsum_seconds'],
                               fsum_delta_fs=(b['fsum_seconds']-a['fsum_seconds'])/1e-15,
                               native_tns_after_delta_seconds=b['native_tns_after_seconds']-a['native_tns_after_seconds'])
    return dict(schema=1, status='COMPLETE_ENDPOINT_COMPARISON_DIAGNOSTIC_ONLY',
                timing_accepted=False, candidate_adopted=False, manufacturing_approval=False, thresholds_changed=False,
                before_stage=before['name'], after_stage=after['name'], endpoint_count=len(before['endpoints']),
                endpoint_corner_count=len(before['endpoints'])*len(before['paths']),
                before_verified_files=before['pins'], after_verified_files=after['pins'],
                sdc_sha256=before['sdc_sha256'], corners=summary, changed_endpoint_corner_count=len(changes),
                global_endpoint_value_changes=sum(before['endpoints'][n] != after['endpoints'][n] for n in before['endpoints']),
                all_changed_endpoint_corners=changes,
                scope='All native exported identities and corner/rise/fall/min values are compared exactly. UNCONSTRAINED means no finite exported path, not a passing timing endpoint. Native regression guards remain separate and unchanged.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for side in ('before', 'after'):
        parser.add_argument('--'+side+'-root', type=Path, required=True)
        parser.add_argument('--'+side+'-receipt', type=Path, required=True)
        parser.add_argument('--'+side+'-stage', required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--expected-sdc-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), 'Output must be new')
    config = json.loads(args.config.read_text())
    loaded = {}
    for side in ('before', 'after'):
        receipt = json.loads(getattr(args, side+'_receipt').read_text())
        stages = [s for s in receipt['stages'] if s['name'] == getattr(args, side+'_stage')]
        require(len(stages) == 1, 'Stage not unique in receipt')
        loaded[side] = load_stage(getattr(args, side+'_root'), stages[0], config['PNR_CORNERS'], args.expected_sdc_sha256)
    record = compare(loaded['before'], loaded['after'])
    record['source_inputs'] = {key: file_pin(getattr(args, key)) for key in ('before_receipt', 'after_receipt', 'config')}
    with args.output.open('x') as stream:
        json.dump(record, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(record['status'])


if __name__ == '__main__':
    main()
