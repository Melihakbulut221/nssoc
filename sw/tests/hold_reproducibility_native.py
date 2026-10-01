#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Cloud-first native gate for the immutable hold diagnostic, never signoff."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


def sha(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def validate_stage(root, stage):
    directory = root/stage['name']
    for name, entry in stage['files'].items():
        path = directory/name
        assert path.stat().st_size == entry['bytes'] and sha(path) == entry['sha256']
    with (directory/'endpoints.tsv').open() as source:
        vertices = list(csv.DictReader(source, delimiter='\t'))
    names = [row['endpoint'] for row in vertices]
    assert len(names) == len(set(names)) == stage['engine_endpoint_count']
    negative = sum(row['global_vertex_slack_seconds'] != 'UNCONSTRAINED'
                   and float(row['global_vertex_slack_seconds']) < 0 for row in vertices)
    assert negative == stage['engine_negative_vertex_endpoints']
    with (directory/'hold-endpoints.tsv').open() as source:
        paths = list(csv.DictReader(source, delimiter='\t'))
    assert len(paths) == len(names)*3
    assert {(r['corner'], r['endpoint']) for r in paths} == {
        (corner, name) for corner in ('fast', 'slow', 'typical') for name in names}
    assert stage['time_unit_seconds'] == 1e-9 and stage['value_units'] == 'seconds'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--helper', required=True, type=Path)
    parser.add_argument('--step', required=True, type=Path)
    parser.add_argument('--fixture', required=True, type=Path)
    parser.add_argument('--pdk-root', required=True, type=Path)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    sources = {
        'hw/soc/pnr/timing_hold_reproducibility.tcl': args.helper.resolve(),
        'hw/soc/pnr/timing_hold_diagnostic_step.tcl': args.step.resolve(),
        'sw/tests/timing_hold_reproducibility_native.tcl': args.fixture.resolve(),
        'sw/tests/hold_reproducibility_native.py': Path(__file__).resolve(),
    }
    pins = {name: sha(path) for name, path in sources.items()}
    result = dict(status='FAIL_PRESERVED_NATIVE_HOLD_DIAGNOSTIC_CONTROLS',
                  method_sha256=pins, cases={}, timing_accepted=False,
                  candidate_adopted=False, manufacturing_approval=False)
    try:
        tool = shutil.which('openroad')
        if tool is None:
            raise ValueError('Run this native fixture inside the pinned AppImage Python')
        result['native_executable_sha256'] = sha(tool)
        command = [tool, '-exit', str(args.fixture.resolve())]
        result['command'] = command
        env = {**os.environ, 'NSSOC_PDK_ROOT': str(args.pdk_root.resolve()),
               'NSSOC_TEST_OUT': str(out/'native'),
               'NSSOC_HOLD_DIAGNOSTIC_HELPER': str(args.helper.resolve())}
        with (out/'native.log').open('x') as stream:
            process = subprocess.run(command, env=env, stdout=stream, stderr=subprocess.STDOUT)
        result['returncode'] = process.returncode
        if process.returncode:
            raise ValueError('Native control failed; log and partial outputs preserved')
        native = json.loads((out/'native/fixture.json').read_text())
        assert native['status'] == 'PASS_NATIVE_HOLD_FIXTURE_NATIVE_ONLY'
        assert set(native['cases']) == {'complete_coverage', 'bad_coverage', 'corrupt_units', 'route_mutation'}
        assert all(row['passed'] is True for row in native['cases'].values())
        assert len(native['stages']) == 5
        for stage in native['stages']:
            validate_stage(out/'native', stage)
        assert {name: sha(path) for name, path in sources.items()} == pins
        result['cases'] = native['cases']
        result['status'] = 'PASS_NATIVE_HOLD_DIAGNOSTIC_CONTROLS'
    except (OSError, ValueError, KeyError, AssertionError, subprocess.SubprocessError) as error:
        result['error'] = str(error)
    result['files'] = {str(path.relative_to(out)): dict(bytes=path.stat().st_size, sha256=sha(path))
                       for path in sorted(out.rglob('*')) if path.is_file()}
    with (out/'result.json').open('x') as target:
        json.dump(result, target, indent=2)
        target.write('\n')
    print(result['status'])
    return 0 if result['status'] == 'PASS_NATIVE_HOLD_DIAGNOSTIC_CONTROLS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
