#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Run isolated C10 timing readback controls and measurements, never adopt a chip.

Only the existing pinned input materialization is reused. The new diagnostic
methods are copied and hashed separately, and a native control gate runs before
loading the full design. Detached work is observed without an elapsed-time kill.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import struct
import sys
import time

sys.dont_write_bytecode = True
import run_cloud_timing_experiment as common

GIB = common.GIB
TERMINAL = {'COMPLETE_DIAGNOSTIC_ONLY', 'FAILED_PRESERVED'}
SOURCES = ('.github/workflows/timing-hold-diagnostic.yml',
           'scripts/run_cloud_hold_diagnostic.py', 'scripts/run_cloud_timing_experiment.py',
           'hw/soc/pnr/timing_hold_reproducibility.tcl',
           'hw/soc/pnr/timing_hold_diagnostic_step.tcl',
           'sw/tests/hold_reproducibility_native.py',
           'sw/tests/timing_hold_reproducibility_native.tcl')
COMPLETE_MARKER = 'NSSOC_HOLD_DIAGNOSTIC_COMPLETE_NO_ADOPTION'
STAGES = ('reload_no_parasitics', 'grt_rebuilt_before_dpl', 'matched_before',
          'same_state_repeat', 'arrivals_recomputed', 'full_timing_recomputed',
          'parasitics_reestimated', 'incremental_no_repair')
FINGERPRINT_FILES = {'constraints': 'constraints.sdc', 'netlist': 'connectivity.v',
                     'placement': 'placement.tsv', 'routing': 'routes.txt',
                     'parasitics': 'parasitics.tsv.gz'}
CONTROL_CASES = {'complete_coverage', 'bad_coverage', 'corrupt_units', 'route_mutation'}
# OpenSTA 857316ff Unit::scale and SWIG unit_scale use C++ float. This is the
# exact native representation, not an engineering tolerance or a slack conversion.
NATIVE_NS_SCALE_SECONDS = struct.unpack('!f', struct.pack('!f', 1e-9))[0]
UNIT_REPRESENTATION = 'IEEE-754 binary32 promoted to Tcl double'




def method_root():
    return Path(__file__).resolve().parents[1]


def file_inventory(root):
    result = {}
    for path in sorted(Path(root).rglob('*')):
        if path.is_symlink():
            raise ValueError('Evidence must not contain symlinks')
        if path.is_file() and path.suffix != '.tmp':
            result[str(path.relative_to(root))] = dict(bytes=path.stat().st_size, sha256=common.sha(path))
    return result


def stage_methods(root, destination):
    destination.mkdir(exist_ok=False)
    inventory = {}
    for name in SOURCES:
        source = Path(root)/name
        if source.is_symlink() or not source.is_file():
            raise ValueError('Missing or symlink diagnostic source: '+name)
        target = destination/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        target.chmod(0o444)
        inventory[name] = dict(bytes=target.stat().st_size, sha256=common.sha(target))
    return inventory


def validate_methods(root, inventory):
    if set(inventory) != set(SOURCES):
        raise ValueError('Diagnostic source inventory changed')
    common.verify_bundle(root, inventory)


def prepare(manifest_path, output, work):
    output = common.fresh_directory(output)
    record = dict(status='PREPARING', recorded=common.now(), timing_accepted=False,
                  manufacturing_approval=False, candidate_adopted=False,
                  selected_checkpoint_preserved=True, native_elapsed_watchdog=False,
                  github_source_commit=os.environ.get('GITHUB_SHA'), diagnostic_only=True)
    common.save(output/'result.json', record)
    try:
        manifest_path = Path(manifest_path).resolve()
        manifest = common.validate_manifest(json.loads(manifest_path.read_text()))
        shutil.copyfile(manifest_path, output/'source-manifest.json')
        work = common.fresh_directory(work)
        required = manifest['archive']['bytes'] + sum(x['bytes'] for x in manifest['files'].values()) + common.RUNTIME_BYTES + 3*GIB
        sample = common.resource_sample(work)
        if sample['available_memory_bytes'] < 9*GIB or sample['free_disk_bytes'] < required:
            raise ValueError(f'Cloud resource guard failed: {sample}; disk required {required}')
        methods = stage_methods(method_root(), output/'methods')
        record.update(resources_before=sample, work=str(work), manifest_sha256=common.sha(manifest_path),
                      bundle_sha256=manifest['archive']['sha256'], method_files=methods,
                      selected_source_metrics=manifest['selected_source_metrics'],
                      runtime_sha256=common.RUNTIME_SHA256,
                      initial_state_template_sha256=manifest['files'][manifest['initial_state']]['sha256'],
                      config_template_sha256=manifest['files'][manifest['config']]['sha256'])
        common.save(output/'result.json', record)
        common.download(manifest['archive'], work/'input.tar.gz')
        common.restore(work/'input.tar.gz', work/'bundle', manifest['files'])
        common.download(manifest['runtime'], work/'runtime.AppImage')
        (work/'runtime.AppImage').chmod(0o755)
        prepared = output/'prepared'
        prepared.mkdir()
        for key, name in [('config', 'config.json'), ('initial_state', 'state.json')]:
            raw_path = work/'bundle'/manifest[key]
            shutil.copyfile(raw_path, output/('source-'+name))
            raw = json.loads(raw_path.read_text())
            common.save(prepared/name, common.translate(raw, work/'bundle', manifest['files']))
        policy = common.load_policy(work/'bundle', manifest)
        if policy.completed_slacks((work/'bundle'/manifest['source_log']).read_text()) != manifest['selected_source_metrics']:
            raise ValueError('Source C10 metrics do not match the published completion log')
        policy.state_pins(prepared/'state.json')
        (output/'run').mkdir()
        record.update(status='PREPARED', prepared_sha256={name: common.sha(prepared/name) for name in ('config.json', 'state.json')})
        common.save(output/'result.json', record)
        command = [sys.executable, '-B', str(output/'methods/scripts/run_cloud_hold_diagnostic.py'), '_worker', '--output', str(output)]
        with (output/'worker.log').open('xb') as log:
            child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                     start_new_session=True, close_fds=True)
        common.save(output/'launch.json', dict(command=command, pid=child.pid,
                    identity=policy.snapshot(child.pid), recorded=common.now()))
        return record
    except BaseException as error:
        record.update(status='FAILED_PRESERVED', error=str(error), recorded=common.now())
        common.save(output/'result.json', record)
        raise


def verify_inputs(output, record):
    manifest = common.validate_manifest(json.loads((output/'source-manifest.json').read_text()))
    if common.sha(output/'source-manifest.json') != record['manifest_sha256']:
        raise ValueError('Manifest changed')
    if record['bundle_sha256'] != manifest['archive']['sha256'] or record['selected_source_metrics'] != manifest['selected_source_metrics']:
        raise ValueError('Selected source identity changed')
    work = Path(record['work'])
    common.verify_bundle(work/'bundle', manifest['files'])
    common.verify_file(work/'runtime.AppImage', manifest['runtime'])
    validate_methods(output/'methods', record['method_files'])
    for key, name in [('config', 'config.json'), ('initial_state', 'state.json')]:
        path = output/'prepared'/name
        if common.sha(path) != record['prepared_sha256'][name]:
            raise ValueError('Prepared input changed')
        common.verify_file(output/('source-'+name), manifest['files'][manifest[key]])
        original = json.loads((work/'bundle'/manifest[key]).read_text())
        if json.loads(path.read_text()) != common.translate(original, work/'bundle', manifest['files']):
            raise ValueError('Prepared input differs from the immutable template')
    return manifest


def clean_environment():
    env = os.environ.copy()
    for key in list(env):
        if key.startswith(('NSSOC_TIMING_', 'NSSOC_HOLD_')) or key == 'NSSOC_CRITICAL_PLACEMENT_SCRIPT':
            del env[key]
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    return env


def execute(command, output, record, name, env):
    """Wait for healthy native work without a timeout or process signals."""
    sample = common.resource_sample(output)
    if sample['available_memory_bytes'] < 9*GIB or sample['free_disk_bytes'] < 3*GIB:
        raise ValueError(f'Native resource reserve failed before {name}: {sample}')
    started = time.monotonic()
    record.update(status='RUNNING', phase=name, recorded=common.now(), command=command,
                  native_address_space_limit_bytes=8*GIB, resources_before_native=sample)
    common.save(output/'result.json', record)
    with (output/(name+'.log')).open('xb') as log:
        child = subprocess.Popen(command, cwd=output, env=env, stdout=log, stderr=subprocess.STDOUT,
                                 stdin=subprocess.DEVNULL, close_fds=True, preexec_fn=common.limits)
        record['native_pid'] = child.pid
        common.save(output/'result.json', record)
        while child.poll() is None:
            record.update(phase_elapsed_seconds=time.monotonic()-started, recorded=common.now())
            common.save(output/'result.json', record)
            time.sleep(15)
    row = dict(command=command, returncode=child.returncode, elapsed_seconds=time.monotonic()-started,
               completed=common.now(), resources_before=sample)
    record.setdefault('native_runs', {})[name] = row
    common.save(output/'result.json', record)
    if child.returncode:
        raise RuntimeError(f'{name} failed with exit {child.returncode}')
    return row


def verify_evidence_files(root, inventory):
    if not isinstance(inventory, dict) or not inventory:
        raise ValueError('Missing native evidence inventory')
    for name, pin in inventory.items():
        path = Path(root)/str(common.safe_relative(name))
        if any(parent.is_symlink() for parent in path.parents) or not path.resolve().is_relative_to(Path(root).resolve()):
            raise ValueError('Symlink or escaped native evidence')
        common.pin(pin)
        common.verify_file(path, pin)
    return inventory


def validate_controls(path, methods):
    path = Path(path)
    row = json.loads(path.read_text())
    if row.get('status') != 'PASS_NATIVE_HOLD_DIAGNOSTIC_CONTROLS':
        raise ValueError('Native control gate did not pass')
    if set(row.get('cases', {})) != CONTROL_CASES or any(value.get('passed') is not True for value in row['cases'].values()):
        raise ValueError('Incomplete native control inventory')
    expected_methods = {name: methods[name]['sha256'] for name in SOURCES if name.endswith(('.tcl', 'hold_reproducibility_native.py'))}
    if row.get('method_sha256') != expected_methods:
        raise ValueError('Native controls used different methods')
    verify_evidence_files(path.parent, row.get('files'))
    native = json.loads((path.parent/'native/fixture.json').read_text())
    if native.get('status') != 'PASS_NATIVE_HOLD_FIXTURE_NATIVE_ONLY' or native.get('cases') != row['cases']:
        raise ValueError('Native fixture receipt does not substantiate the control cases')
    stages = native.get('stages', [])
    expected_stages = ('original', 'repeat', 'arrivals', 'full_update', 'rerouted_mutation')
    if tuple(stage.get('name') for stage in stages) != expected_stages:
        raise ValueError('Missing native control stages')
    sdc_sha = stages[0]['files']['constraints.sdc']['sha256']
    checked = [validate_stage(path.parent/'native'/stage['name'], stage, sdc_sha) for stage in stages]
    if any(set(stage['corner_names']) != {'fast','slow','typical'} for stage in checked):
        raise ValueError('Native controls did not cover all three corners')
    if any(stage['fingerprints'] != checked[0]['fingerprints'] for stage in checked[1:4]):
        raise ValueError('Native control no-op unexpectedly mutated physical state')
    if checked[-1]['fingerprints']['routing'] == checked[0]['fingerprints']['routing']:
        raise ValueError('Native route mutation control did not exercise changed routes')
    return row


def seconds(value):
    if value == 'UNCONSTRAINED':
        return None
    if isinstance(value, bool):
        raise ValueError('Boolean timing value')
    number = float(value)
    if not math.isfinite(number) or abs(number) >= 1e20:
        raise ValueError('Nonfinite timing value or unlabelled unconstrained sentinel')
    return number


def exact_count(value):
    if type(value) is not int or value < 0:
        raise ValueError('Invalid native census count')
    return value


def read_rows(path, headers):
    with path.open(newline='') as stream:
        rows = csv.DictReader(stream, delimiter='\t')
        if rows.fieldnames != headers:
            raise ValueError('Unexpected native table columns: '+str(path))
        for row in rows:
            if None in row or any(value is None for value in row.values()):
                raise ValueError('Truncated or malformed native table')
            yield row


def validate_stage(directory, row, source_sdc_sha):
    inventory = verify_evidence_files(directory, row.get('files'))
    mandatory = set(FINGERPRINT_FILES.values()) | {'native.json', 'endpoints.tsv', 'hold-endpoints.tsv'}
    if not mandatory <= set(inventory):
        raise ValueError('Missing native stage evidence')
    native = json.loads((directory/'native.json').read_text())
    if native != {key:value for key,value in row.items() if key not in ('files','fingerprints')}:
        raise ValueError('Stage receipt differs from its native raw record')
    if row.get('all_endpoint_coverage') is not True:
        raise ValueError('Incomplete native endpoint coverage')
    if (row.get('value_units') != 'seconds' or row.get('time_unit_seconds') != 1e-9
            or row.get('native_time_unit_seconds') != NATIVE_NS_SCALE_SECONDS
            or row.get('time_unit_representation') != UNIT_REPRESENTATION
            or row.get('numeric_format') != '%.17g'
            or row.get('raw_getters') != 'SWIG Slack delayAsFloat -> Tcl double, SI seconds'):
        raise ValueError('Expected SI-second values, nominal ns units and the exact native float32 scale')
    if inventory['constraints.sdc']['sha256'] != source_sdc_sha:
        raise ValueError('Timing constraints changed')
    expected_fingerprints = {name: inventory[filename]['sha256'] for name, filename in FINGERPRINT_FILES.items()}
    if row.get('fingerprints') != expected_fingerprints:
        raise ValueError('Stage fingerprint does not identify its actual raw bytes')
    endpoints = {}
    for data in read_rows(directory/'endpoints.tsv', ['endpoint', 'global_vertex_slack_seconds']):
        name = data['endpoint']
        if not name or name in endpoints:
            raise ValueError('Missing or duplicate native endpoint')
        endpoints[name] = seconds(data['global_vertex_slack_seconds'])
    count = len(endpoints)
    if count == 0 or any(exact_count(row.get(key)) != count for key in ('endpoint_count','engine_endpoint_count','exported_endpoint_count')):
        raise ValueError('Native endpoint census is incomplete')
    negative = sum(value is not None and value < 0 for value in endpoints.values())
    if any(exact_count(row.get(key)) != negative for key in ('negative_vertex_endpoints','engine_negative_vertex_endpoints')):
        raise ValueError('Native violating endpoint count disagrees with full export')
    corners = row.get('corners', [])
    names = [corner['name'] for corner in corners]
    if not names or len(set(names)) != len(names) or any(not isinstance(name,str) or not name for name in names):
        raise ValueError('Missing or duplicate native corner')
    summary = {name: dict(seen=set(), constrained=0, negative=0, folded=0., slacks=[]) for name in names}
    global_from_paths = {endpoint:None for endpoint in endpoints}
    for data in read_rows(directory/'hold-endpoints.tsv', ['corner','endpoint','min_rise_seconds','min_fall_seconds','min_seconds']):
        corner, name = data['corner'], data['endpoint']
        if corner not in summary or name not in endpoints or name in summary[corner]['seen']:
            raise ValueError('Unknown or duplicate corner endpoint')
        target = summary[corner]
        target['seen'].add(name)
        rise, fall, slack = [seconds(data[key]) for key in ('min_rise_seconds','min_fall_seconds','min_seconds')]
        valid = [value for value in (rise, fall) if value is not None]
        if slack != (min(valid) if valid else None):
            raise ValueError('Corner endpoint minimum inconsistent with rise/fall')
        if slack is not None:
            previous = global_from_paths[name]
            global_from_paths[name] = slack if previous is None else min(previous,slack)
            target['constrained'] += 1
            if slack < 0:
                target['negative'] += 1
                target['folded'] += slack
                target['slacks'].append(slack)
    for name, vertex_slack in endpoints.items():
        if global_from_paths[name] != vertex_slack:
            raise ValueError(f'Unsupported or incomplete global-vs-PathEnd coverage: {name}: '
                             f'vertex={vertex_slack!r}, corner_min={global_from_paths[name]!r}')
    reductions = {}
    for corner in corners:
        name, data = corner['name'], summary[corner['name']]
        if data['seen'] != set(endpoints):
            raise ValueError('Incomplete full endpoint by corner Cartesian census')
        if (exact_count(corner['constrained_endpoints']) != data['constrained']
                or exact_count(corner['unrepresented_endpoints']) != count-data['constrained']
                or exact_count(corner['negative_path_endpoints']) != data['negative']):
            raise ValueError('Corner endpoint counts disagree with exported evidence')
        fixed = seconds(corner['fixed_order_tns_seconds'])
        if fixed != data['folded']:
            raise ValueError('Fixed-order endpoint sum disagrees with exported rows')
        values = {key: seconds(corner[key]) for key in ('native_tns_seconds_before','native_tns_seconds_after','native_wns_seconds')}
        if any(value is None for value in values.values()):
            raise ValueError('Missing native timing aggregate')
        reductions[name] = dict(exported_negative_endpoints=data['negative'],
            fixed_order_tns_seconds=data['folded'], math_fsum_tns_seconds=math.fsum(data['slacks']),
            native_tns_seconds_before=values['native_tns_seconds_before'],
            native_tns_seconds_after=values['native_tns_seconds_after'],
            native_minus_fixed_seconds=values['native_tns_seconds_after']-fixed)
    return dict(endpoint_count=count, negative_vertex_endpoints=negative,
                corner_names=names, fingerprints=expected_fingerprints, reductions=reductions,
                endpoint_names=sorted(endpoints))


def validate_diagnostic(step, source_sdc_sha, expected_corners):
    """Reconstruct coverage and sums; no precision difference grants eligibility."""
    row = json.loads((step/'hold-diagnostic.json').read_text())
    if row.get('schema') != 1 or row.get('status') != 'COMPLETE_DIAGNOSTIC_ONLY':
        raise ValueError('Unexpected diagnostic schema/completion')
    if any(row.get(key) is not False for key in ('timing_accepted','candidate_adopted','manufacturing_approval')):
        raise ValueError('A diagnostic cannot make an acceptance claim')
    if row.get('sram_macro_count') != 32 or row.get('sram_placement_preserved') is not True:
        raise ValueError('Missing fixed 32-SRAM placement proof')
    stages = row.get('stages', [])
    if tuple(stage.get('name') for stage in stages) != STAGES:
        raise ValueError('Missing, reordered or extra diagnostic stage')
    log = (step/'openroad-resizertimingpostgrt.log').read_text()
    if log.count(COMPLETE_MARKER) != 1:
        raise ValueError('Missing unique native diagnostic completion marker')
    checked = {stage['name']: validate_stage(step/stage['name'], stage, source_sdc_sha) for stage in stages}
    first = checked[STAGES[0]]
    if set(first['corner_names']) != set(expected_corners) or not expected_corners:
        raise ValueError('Native corner census differs from the selected configuration')
    if any(value['endpoint_names'] != first['endpoint_names'] or value['corner_names'] != first['corner_names'] for value in checked.values()):
        raise ValueError('Stage endpoint or corner census changed')
    reference = checked['matched_before']['fingerprints']
    for name in ('same_state_repeat','arrivals_recomputed','full_timing_recomputed'):
        if checked[name]['fingerprints'] != reference:
            raise ValueError('No-op stage changed geometry, netlist, constraints, routes or parasitics')
    # Initial preparation may remove physical-only fillers; preserve that boundary.
    # All constraints remain exact, and matched preparation onward cannot alter logic.
    for name, value in checked.items():
        if value['fingerprints']['constraints'] != reference['constraints']:
            raise ValueError('Readback stage changed timing constraints')
        if name in STAGES[2:] and value['fingerprints']['netlist'] != reference['netlist']:
            raise ValueError('Matched/no-repair stage changed logical connectivity')
        del value['endpoint_names']
    return dict(native=row, independently_checked_stages=checked, candidate_adopted=False,
                timing_accepted=False, manufacturing_approval=False, thresholds_changed=False)


def worker(output):
    output = Path(output).resolve()
    record = json.loads((output/'result.json').read_text())
    try:
        if record['status'] != 'PREPARED':
            raise ValueError('Worker requires PREPARED input')
        manifest = verify_inputs(output, record)
        work, methods = Path(record['work']), output/'methods'
        app = str(work/'runtime.AppImage')
        policy = common.load_policy(work/'bundle', manifest)
        input_pins = policy.state_pins(output/'prepared/state.json')
        env = clean_environment()
        env['NSSOC_HOLD_DIAGNOSTIC_HELPER'] = str(methods/'hw/soc/pnr/timing_hold_reproducibility.tcl')
        control_command = [app, 'python', str(methods/'sw/tests/hold_reproducibility_native.py'),
                           str(output/'native-controls'), '--helper', str(methods/'hw/soc/pnr/timing_hold_reproducibility.tcl'),
                           '--step', str(methods/'hw/soc/pnr/timing_hold_diagnostic_step.tcl'),
                           '--fixture', str(methods/'sw/tests/timing_hold_reproducibility_native.tcl'),
                           '--pdk-root', str(work/'bundle'/manifest['pdk_root'])]
        execute(control_command, output, record, 'native-controls', env)
        controls = validate_controls(output/'native-controls/result.json', record['method_files'])
        common.save(output/'native-control-validation.json', controls)
        verify_inputs(output, record)
        command = [app, 'python', str(methods/'scripts/run_cloud_hold_diagnostic.py'), '_native_flow',
                   '--flow', 'HoldDiagnostics', '--manual-pdk', '--pdk-root', str(work/'bundle'/manifest['pdk_root']),
                   '--pdk', manifest['pdk'], '--force-run-dir', str(output/'run'),
                   '--from', 'OpenROAD.ResizerTimingPostGRT', '--to', 'OpenROAD.ResizerTimingPostGRT',
                   '--with-initial-state', str(output/'prepared/state.json'), str(output/'prepared/config.json')]
        execute(command, output, record, 'native-diagnostic', env)
        verify_inputs(output, record)
        policy.verify_pins(input_pins)
        steps = list((output/'run').glob('*-openroad-resizertimingpostgrt'))
        if len(steps) != 1:
            raise ValueError('Missing unique diagnostic native step')
        source_sdc = Path(json.loads((output/'prepared/state.json').read_text())['sdc'])
        validate_controls(output/'native-controls/result.json', record['method_files'])
        expected_corners = json.loads((output/'source-config.json').read_text())['PNR_CORNERS']
        diagnostic = validate_diagnostic(steps[0], common.sha(source_sdc), expected_corners)
        outputs = file_inventory(output/'run')
        record.update(status='COMPLETE_DIAGNOSTIC_ONLY', completed=common.now(), diagnostic=diagnostic,
                      sdc_sha256=common.sha(source_sdc), output_files=outputs,
                      control_output_files=file_inventory(output/'native-controls'))
        common.save(output/'result.json', record)
    except BaseException as error:
        record.update(status='FAILED_PRESERVED', error=str(error), recorded=common.now())
        common.save(output/'result.json', record)
        print(str(error), file=sys.stderr)
        return 1
    return 0


def observation(output):
    output = Path(output)
    if not (output/'result.json').is_file():
        return dict(status='NO_RESULT_INCOMPLETE', terminal=True)
    record = json.loads((output/'result.json').read_text())
    if record['status'] in TERMINAL:
        return dict(status=record['status'], terminal=True)
    # Existing observer already verifies PID birth identity and never sends signals.
    return common.observation(output)


def wait(output, seconds=None, github_output=None):
    if seconds is not None and (not math.isfinite(seconds) or seconds < 0):
        raise ValueError('Observer duration must be nonnegative and finite')
    output = Path(output)
    started = time.monotonic()
    while True:
        row = observation(output)
        if row['terminal'] or (seconds is not None and time.monotonic()-started >= seconds):
            row.update(recorded=common.now(), worker_was_not_signaled=True)
            if output.is_dir():
                common.save(output/'observer.json', row)
            if github_output:
                with Path(github_output).open('a') as stream:
                    stream.write('terminal='+str(row['terminal']).lower()+'\n')
            print(json.dumps(row))
            return row
        time.sleep(15 if seconds is None else min(15, max(0, seconds-(time.monotonic()-started))))


def capture(output, destination):
    """A snapshot is evidence, never an accepted or restartable checkpoint."""
    output, destination = Path(output).resolve(), Path(destination).resolve()
    if destination.is_relative_to(output):
        raise ValueError('Capture must be outside worker output')
    observed = observation(output)
    destination = common.fresh_directory(destination)
    copied = {}
    complete = observed['status'] == 'COMPLETE_DIAGNOSTIC_ONLY'
    for path in sorted(output.rglob('*')):
        if path.is_symlink():
            raise ValueError('Symlink in diagnostic output')
        if not path.is_file() or path.suffix == '.tmp':
            continue
        # Full-chip databases are never published as checkpoints. Tiny control
        # Liberty/DEF/ODB fixtures remain mandatory reproducible native evidence.
        relative = path.relative_to(output)
        if relative.parts[0] != 'native-controls' and path.suffix.lower() in {'.odb', '.def', '.gds', '.sdf', '.lib'}:
            continue
        target = destination/path.relative_to(output)
        target.parent.mkdir(parents=True, exist_ok=True)
        with path.open('rb') as source, target.open('xb') as sink:
            observed_bytes = os.fstat(source.fileno()).st_size
            remaining = observed_bytes
            while remaining:
                data = source.read(min(1024**2, remaining))
                if not data:
                    break
                sink.write(data)
                remaining -= len(data)
        copied[str(path.relative_to(output))] = dict(bytes=target.stat().st_size, sha256=common.sha(target),
             observed_source_bytes=observed_bytes, source_truncated_during_copy=bool(remaining))
    row = dict(recorded=common.now(), observation=observed, files=copied,
               complete_diagnostic_evidence=complete, snapshot_is_atomic_across_files=False,
               restart_checkpoint_accepted=False, candidate_adopted=False,
               timing_accepted=False, manufacturing_approval=False)
    common.save(destination/'capture.json', row)
    return row


def validate_capture(directory, manifest_path=None):
    """Independently recheck a completed artifact; a partial snapshot never qualifies."""
    directory = Path(directory)
    capture = json.loads((directory/'capture.json').read_text())
    if capture.get('complete_diagnostic_evidence') is not True or capture.get('observation', {}).get('status') != 'COMPLETE_DIAGNOSTIC_ONLY':
        raise ValueError('Partial evidence is not a completed diagnostic')
    inventory = verify_evidence_files(directory, capture.get('files'))
    if any(row.get('source_truncated_during_copy') is not False for row in inventory.values()):
        raise ValueError('Snapshot was truncated while copying')
    actual = set(file_inventory(directory))
    if actual != set(inventory) | {'capture.json'}:
        raise ValueError('Uninventoried snapshot files')
    row = json.loads((directory/'result.json').read_text())
    if row.get('status') != 'COMPLETE_DIAGNOSTIC_ONLY' or any(row.get(key) is not False for key in ('candidate_adopted','timing_accepted','manufacturing_approval')):
        raise ValueError('Incomplete or unsafe diagnostic result')
    manifest = common.validate_manifest(json.loads((directory/'source-manifest.json').read_text()))
    if common.sha(directory/'source-manifest.json') != row['manifest_sha256']:
        raise ValueError('Source manifest pin differs')
    if manifest_path is not None and common.sha(manifest_path) != row['manifest_sha256']:
        raise ValueError('Artifact is not from the selected published input')
    if row['bundle_sha256'] != manifest['archive']['sha256'] or row['runtime_sha256'] != common.RUNTIME_SHA256:
        raise ValueError('Bundle/runtime identity differs')
    if row['selected_source_metrics'] != manifest['selected_source_metrics']:
        raise ValueError('Selected C10 source changed')
    for key, filename in [('initial_state', 'state.json'), ('config', 'config.json')]:
        common.verify_file(directory/('source-'+filename), manifest['files'][manifest[key]])
    validate_methods(directory/'methods', row['method_files'])
    initial = json.loads((directory/'source-state.json').read_text())
    if not initial['sdc'].startswith('@BUNDLE@/'):
        raise ValueError('SDC is not a pinned bundle view')
    expected_sdc = manifest['files'][str(common.safe_relative(initial['sdc'][len('@BUNDLE@/'):]))]['sha256']
    if row['sdc_sha256'] != expected_sdc:
        raise ValueError('SDC is not the original selected view')
    for name in ('native-controls', 'native-diagnostic'):
        if row.get('native_runs', {}).get(name, {}).get('returncode') != 0:
            raise ValueError('Missing successful native phase')
    verify_evidence_files(directory/'run', row['output_files'])
    if set(file_inventory(directory/'run')) != set(row['output_files']):
        raise ValueError('Diagnostic output closure is incomplete')
    verify_evidence_files(directory/'native-controls', row['control_output_files'])
    if set(file_inventory(directory/'native-controls')) != set(row['control_output_files']):
        raise ValueError('Native control output closure is incomplete')
    validate_controls(directory/'native-controls/result.json', row['method_files'])
    steps = list((directory/'run').glob('*-openroad-resizertimingpostgrt'))
    expected_corners = json.loads((directory/'source-config.json').read_text())['PNR_CORNERS']
    if len(steps) != 1 or validate_diagnostic(steps[0], expected_sdc, expected_corners) != row['diagnostic']:
        raise ValueError('Independent diagnostic reconstruction differs')
    return row


def native_flow():
    # Imports are deferred: ordinary source tests require no native tool runtime.
    from librelane.flows import Flow
    from librelane.flows.classic import Classic
    from librelane.state import State
    from librelane.steps import OpenROAD

    class DiagnosticTimingReadback(OpenROAD.ResizerTimingPostGRT):
        outputs = []  # Readback only; no new physical checkpoint is produced.

        def get_script_path(self):
            return str(method_root()/'hw/soc/pnr/timing_hold_diagnostic_step.tcl')

    @Flow.factory.register()
    class HoldDiagnostics(Classic):
        Steps = [DiagnosticTimingReadback if step == OpenROAD.ResizerTimingPostGRT else step for step in Classic.Steps]

        def run(self, initial_state, **kwargs):
            target = OpenROAD.ResizerTimingPostGRT.id
            if kwargs.get('frm') != target or kwargs.get('to') != target:
                raise ValueError(f'Diagnostic requires --from {target} --to {target}')
            original = State.save_snapshot

            def save_manifest(state, path):
                destination = Path(path)
                destination.mkdir(parents=True, exist_ok=True)
                (destination/'state.json').write_text(state.dumps())

            State.save_snapshot = save_manifest
            try:
                return super().run(initial_state, **kwargs)
            finally:
                State.save_snapshot = original

    from librelane.__main__ import cli
    sys.argv.remove('_native_flow')
    cli()


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '_native_flow':
        return native_flow()
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='mode', required=True)
    start = commands.add_parser('start')
    start.add_argument('--manifest', type=Path, required=True)
    start.add_argument('--output', type=Path, required=True)
    start.add_argument('--work', type=Path, required=True)
    job = commands.add_parser('_worker')
    job.add_argument('--output', type=Path, required=True)
    observer = commands.add_parser('wait')
    observer.add_argument('--output', type=Path, required=True)
    observer.add_argument('--seconds', type=float)
    observer.add_argument('--github-output', type=Path)
    snap = commands.add_parser('capture')
    snap.add_argument('--output', type=Path, required=True)
    snap.add_argument('--destination', type=Path, required=True)
    final = commands.add_parser('validate')
    final.add_argument('--directory', type=Path, required=True)
    final.add_argument('--manifest', type=Path, required=True)
    args = parser.parse_args()
    if args.mode == 'start':
        prepare(args.manifest, args.output, args.work)
    elif args.mode == '_worker':
        return worker(args.output)
    elif args.mode == 'wait':
        wait(args.output, args.seconds, args.github_output)
    elif args.mode == 'capture':
        capture(args.output, args.destination)
    else:
        validate_capture(args.directory, args.manifest)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
