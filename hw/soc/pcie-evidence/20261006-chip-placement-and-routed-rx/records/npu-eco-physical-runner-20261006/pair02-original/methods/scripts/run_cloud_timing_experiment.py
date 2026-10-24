#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Run a pinned C10 setup A/B on independent cloud hosts, never accept signoff.

The worker is detached so bounded observer waits can publish progress without
stopping native work. There is no native elapsed-time kill. GitHub's unavoidable
six-hour hosted-job limit may still interrupt a job; partial snapshots are NOT
restart checkpoints. Only completed, guarded measurements qualify for comparison.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path, PurePosixPath
import resource
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.parse
import urllib.request

PROFILES = ('setup_baseline', 'setup_batch4')
METHODS = ('timing_experiment_flow.py', 'timing_experiment_step.tcl',
           'timing_repair_experiment.tcl', 'run_timing_experiments.py',
           'timing_process_guard.py')
SLACKS = ('setup_wns_ns', 'hold_wns_ns', 'setup_tns_ns', 'hold_tns_ns')
COUNTS = ('setup_violating_endpoints', 'hold_violating_endpoints',
          'slew_violations', 'capacitance_violations')
RUNTIME_SHA256 = 'd6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
RUNTIME_BYTES = 1398053408
GIB = 1024**3
TERMINAL = {'COMPLETE_ESTIMATE_ONLY', 'FAILED_PRESERVED'}


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, record):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(record, indent=2) + '\n')
    temporary.replace(path)


def safe_relative(name):
    if not isinstance(name, str) or not name or '\\' in name or '\x00' in name:
        raise ValueError('Invalid bundle path')
    value = PurePosixPath(name)
    if value.is_absolute() or '..' in value.parts or str(value) != name or name == '.':
        raise ValueError(f'Unsafe/noncanonical bundle path: {name}')
    return value


def pin(entry):
    if (not isinstance(entry, dict) or type(entry.get('bytes')) is not int or entry['bytes'] < 0
            or not isinstance(entry.get('sha256'), str) or len(entry['sha256']) != 64
            or any(c not in '0123456789abcdef' for c in entry['sha256'])):
        raise ValueError('Expected exact file bytes and lowercase SHA256')


def validate_manifest(record):
    if record.get('schema') != 1 or record.get('pdk') != 'ihp-sg13g2':
        raise ValueError('Unsupported timing bundle schema/PDK')
    files = record.get('files')
    if not isinstance(files, dict) or not files:
        raise ValueError('Missing bundle file inventory')
    for name, entry in files.items():
        safe_relative(name)
        pin(entry)
    for key in ('config', 'initial_state', 'source_log'):
        if str(safe_relative(record[key])) not in files:
            raise ValueError(f'Missing pinned {key}')
    methods = str(safe_relative(record['methods_dir']))
    for name in METHODS:
        if f'{methods}/{name}' not in files:
            raise ValueError(f'Missing pinned method {name}')
    pdk = str(safe_relative(record['pdk_root']))
    if not any(n.startswith(pdk + '/ihp-sg13g2/') for n in files):
        raise ValueError('Missing materialized PDK')
    for key in ('archive', 'runtime'):
        pin(record[key])
        url = urllib.parse.urlparse(record[key]['url'])
        if url.scheme != 'https' or url.hostname != 'github.com' or '/releases/download/' not in url.path:
            raise ValueError('Pinned downloads must use HTTPS GitHub release assets')
    if record['runtime']['sha256'] != RUNTIME_SHA256 or record['runtime']['bytes'] != RUNTIME_BYTES:
        raise ValueError('Unexpected LibreLane 3.0.5 x86_64 runtime')
    source = record['selected_source_metrics']
    if set(source) != {'setup_wns_ns', 'hold_wns_ns'}:
        raise ValueError('Expected the completed C10 setup/hold WNS proof')
    if any(isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v) for v in source.values()):
        raise ValueError('Non-finite source metrics')
    return record


def download(entry, path):
    """Never execute or unpack a release asset before exact size/hash validation."""
    with urllib.request.urlopen(entry['url'], timeout=60) as source, Path(path).open('xb') as output:
        count = 0
        while data := source.read(1024**2):
            count += len(data)
            if count > entry['bytes']:
                raise ValueError('Download exceeds pinned size')
            output.write(data)
    verify_file(path, entry)


def verify_file(path, entry):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size != entry['bytes'] or sha(path) != entry['sha256']:
        raise ValueError(f'Missing/changed pinned input: {path}')


def restore(archive, root, inventory):
    root = Path(root)
    root.mkdir(exist_ok=False)
    seen = set()
    with tarfile.open(archive, 'r|gz') as source:
        for member in source:
            name = str(safe_relative(member.name))
            if (not member.isfile() or member.issparse() or name not in inventory
                    or name in seen or member.size != inventory[name]['bytes']):
                raise ValueError(f'Unexpected or unsafe archive member: {name}')
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as output:
                shutil.copyfileobj(source.extractfile(member), output, length=1024**2)
            verify_file(path, inventory[name])
            path.chmod(0o444)
            seen.add(name)
    if seen != set(inventory):
        raise ValueError('Archive inventory is incomplete')


def verify_bundle(root, inventory):
    for name, entry in inventory.items():
        verify_file(Path(root) / name, entry)
    actual = set()
    for path in Path(root).rglob('*'):
        if path.is_symlink():
            raise ValueError('Bundle acquired a symlink')
        if path.is_file():
            actual.add(str(path.relative_to(root)))
    if actual != set(inventory):
        raise ValueError('Bundle acquired unlisted files')


def translate(value, root, inventory):
    """Only complete @BUNDLE@ paths change; no general string substitution."""
    if isinstance(value, dict):
        return {k: translate(v, root, inventory) for k, v in value.items()}
    if isinstance(value, list):
        return [translate(v, root, inventory) for v in value]
    if not isinstance(value, str):
        return value
    if value.startswith('@BUNDLE@/'):
        name = str(safe_relative(value[len('@BUNDLE@/'):]))
        if name not in inventory and not any(n.startswith(name + '/') for n in inventory):
            raise ValueError(f'Unpinned bundle reference: {name}')
        path = Path(root) / name
        if not path.exists() or path.is_symlink():
            raise ValueError(f'Missing bundle reference: {name}')
        return str(path)
    if '@BUNDLE@' in value or value.startswith('/'):
        raise ValueError(f'Untranslated/ambiguous absolute input path: {value}')
    return value


def load_policy(bundle, manifest):
    methods = Path(bundle) / manifest['methods_dir']
    # Imports must not add __pycache__ files to the hash-pinned bundle.
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(methods))
    spec = importlib.util.spec_from_file_location('nssoc_cloud_pinned_policy', methods/'run_timing_experiments.py')
    policy = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(policy)
    finally:
        sys.path.pop(0)
    return policy


def fresh_directory(path):
    path = Path(os.path.abspath(path))
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Symlink output/work ancestor rejected')
    path.mkdir(parents=True, exist_ok=False)
    return path


def resource_sample(directory):
    available = next(int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines()
                     if line.startswith('MemAvailable:'))
    return dict(available_memory_bytes=available, free_disk_bytes=shutil.disk_usage(directory).free)


def start(manifest_path, profile, output, work):
    if profile not in PROFILES:
        raise ValueError('Only the original setup A/B profiles are allowed')
    output = fresh_directory(output)
    record = dict(status='PREPARING', recorded=now(), profile=profile,
                  timing_accepted=False, manufacturing_approval=False,
                  selected_checkpoint_preserved=True, native_elapsed_watchdog=False)
    save(output/'result.json', record)
    try:
        manifest_path = Path(manifest_path).resolve()
        manifest = validate_manifest(json.loads(manifest_path.read_text()))
        shutil.copyfile(manifest_path, output/'source-manifest.json')
        work = fresh_directory(work)
        required = manifest['archive']['bytes'] + sum(x['bytes'] for x in manifest['files'].values()) + RUNTIME_BYTES + 3*GIB
        sample = resource_sample(work)
        if sample['available_memory_bytes'] < 9*GIB or sample['free_disk_bytes'] < required:
            raise ValueError(f'Cloud resource guard failed: {sample}; disk required {required}')
        record.update(resources_before=sample, manifest_sha256=sha(manifest_path),
                      bundle_sha256=manifest['archive']['sha256'],
                      initial_state_template_sha256=manifest['files'][manifest['initial_state']]['sha256'],
                      config_template_sha256=manifest['files'][manifest['config']]['sha256'],
                      selected_source_metrics=manifest['selected_source_metrics'],
                      method_sha256={name: manifest['files'][manifest['methods_dir']+'/'+name]['sha256'] for name in METHODS},
                      runner_sha256=sha(Path(__file__)), runtime_sha256=RUNTIME_SHA256)
        save(output/'result.json', record)
        download(manifest['archive'], work/'input.tar.gz')
        restore(work/'input.tar.gz', work/'bundle', manifest['files'])
        download(manifest['runtime'], work/'runtime.AppImage')
        (work/'runtime.AppImage').chmod(0o755)
        prepared = output/'prepared'
        prepared.mkdir()
        for key, filename in [('config', 'config.json'), ('initial_state', 'state.json')]:
            raw = json.loads((work/'bundle'/manifest[key]).read_text())
            save(prepared/filename, translate(raw, work/'bundle', manifest['files']))
        policy = load_policy(work/'bundle', manifest)
        metrics = policy.completed_slacks((work/'bundle'/manifest['source_log']).read_text())
        if metrics != manifest['selected_source_metrics']:
            raise ValueError('Selected source metrics do not match completed C10 log')
        policy.state_pins(prepared/'state.json')
        # The native CLI rejects a missing --force-run-dir directory.
        (output/'run').mkdir()
        record.update(status='PREPARED', work=str(work), source_log_sha256=manifest['files'][manifest['source_log']]['sha256'],
                      prepared_sha256={name: sha(prepared/name) for name in ('state.json', 'config.json')})
        save(output/'result.json', record)
        command = [sys.executable, '-B', str(Path(__file__).resolve()), '_worker', '--output', str(output)]
        with (output/'worker.log').open('xb') as log:
            child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                     start_new_session=True, close_fds=True)
        identity = policy.snapshot(child.pid)
        save(output/'launch.json', dict(command=command, pid=child.pid, identity=identity, recorded=now()))
        return record
    except BaseException as error:
        record.update(status='FAILED_PRESERVED', error=str(error), recorded=now())
        save(output/'result.json', record)
        raise


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (8*GIB, 8*GIB))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def validate_measurement(value, profile, phase):
    if value.get('profile') != profile or value.get('phase') != phase or value.get('signoff') is not False or value.get('parasitics') != 'global_route_estimates':
        raise ValueError('Unexpected measurement scope/profile/phase')
    for key in SLACKS + COUNTS + ('area_um2', 'instance_count', 'utilization_fraction'):
        v = value[key]
        if isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v):
            raise ValueError(f'Invalid measurement {key}')
        if key in COUNTS + ('instance_count',) and (v < 0 or int(v) != v):
            raise ValueError(f'Invalid count {key}')
        if key in ('area_um2', 'utilization_fraction') and v < 0:
            raise ValueError(f'Invalid physical metric {key}')
    return value


def portable_state(value, output, bundle):
    if isinstance(value, dict):
        return {k: portable_state(v, output, bundle) for k, v in value.items()}
    if isinstance(value, list):
        return [portable_state(v, output, bundle) for v in value]
    if isinstance(value, str) and value.startswith('/'):
        path = Path(value)
        for root, token in [(output, '@RESULT@'), (bundle, '@BUNDLE@')]:
            if path.is_relative_to(root):
                return token+'/'+str(path.relative_to(root))
        raise ValueError(f'Unpinned external output-state dependency: {value}')
    return value


def worker(output):
    output = Path(output).resolve()
    record = json.loads((output/'result.json').read_text())
    try:
        if record['status'] != 'PREPARED' or record['runner_sha256'] != sha(Path(__file__)):
            raise ValueError('Worker requires its immutable prepared record')
        manifest = validate_manifest(json.loads((output/'source-manifest.json').read_text()))
        if sha(output/'source-manifest.json') != record['manifest_sha256']:
            raise ValueError('Manifest changed')
        work, profile = Path(record['work']), record['profile']
        if profile not in PROFILES or record['selected_source_metrics'] != manifest['selected_source_metrics']:
            raise ValueError('Worker profile/source proof changed')
        bundle = work/'bundle'
        verify_bundle(bundle, manifest['files'])
        verify_file(work/'runtime.AppImage', manifest['runtime'])
        for name, expected in record['prepared_sha256'].items():
            if sha(output/'prepared'/name) != expected:
                raise ValueError('Materialized input changed')
        for key, name in [('config', 'config.json'), ('initial_state', 'state.json')]:
            original = json.loads((bundle/manifest[key]).read_text())
            if json.loads((output/'prepared'/name).read_text()) != translate(original, bundle, manifest['files']):
                raise ValueError('Materialized input differs from pinned template')
        policy = load_policy(bundle, manifest)
        input_pins = policy.state_pins(output/'prepared/state.json')
        command = [str(work/'runtime.AppImage'), 'python', str(bundle/manifest['methods_dir']/'timing_experiment_flow.py'),
                   '--flow', 'TimingExperiments', '--manual-pdk', '--pdk-root', str(bundle/manifest['pdk_root']),
                   '--pdk', manifest['pdk'], '--force-run-dir', str(output/'run'),
                   '--from', 'OpenROAD.ResizerTimingPostGRT', '--to', 'OpenROAD.ResizerTimingPostGRT',
                   '--with-initial-state', str(output/'prepared/state.json'), str(output/'prepared/config.json')]
        env = os.environ.copy()
        # Do not inherit another timing recipe/profile from an external runner.
        for key in list(env):
            if key.startswith('NSSOC_TIMING_') or key == 'NSSOC_CRITICAL_PLACEMENT_SCRIPT':
                del env[key]
        env.update(NSSOC_TIMING_EXPERIMENT_PROFILE=profile, PYTHONDONTWRITEBYTECODE='1')
        started = time.monotonic()
        record.update(status='RUNNING', command=command, started=now(), recorded=now(), native_address_space_limit_bytes=8*GIB)
        save(output/'result.json', record)
        with (output/'native.log').open('xb') as log:
            child = subprocess.Popen(command, cwd=output, env=env, stdout=log, stderr=subprocess.STDOUT, preexec_fn=limits)
            record['native_pid'] = child.pid
            save(output/'result.json', record)
            while child.poll() is None:
                record.update(elapsed_seconds=time.monotonic()-started, recorded=now())
                save(output/'result.json', record)
                time.sleep(15)
        record.update(returncode=child.returncode, elapsed_seconds=time.monotonic()-started, completed=now())
        if child.returncode:
            raise RuntimeError(f'Native experiment failed with exit {child.returncode}')
        verify_bundle(bundle, manifest['files'])
        policy.verify_pins(input_pins)
        verify_file(work/'runtime.AppImage', manifest['runtime'])
        if sha(Path(__file__)) != record['runner_sha256'] or sha(output/'source-manifest.json') != record['manifest_sha256']:
            raise ValueError('Runner/manifest changed during native execution')
        for name, expected in record['prepared_sha256'].items():
            if sha(output/'prepared'/name) != expected:
                raise ValueError('Materialized config/state changed during native execution')
        steps = list((output/'run').glob('*-openroad-resizertimingpostgrt'))
        if len(steps) != 1:
            raise ValueError('Missing/ambiguous completed native timing step')
        step = steps[0]
        log = (step/'openroad-resizertimingpostgrt.log').read_text()
        for marker in (f'EXPERIMENT_COMPLETE_REQUIRES_ROUTING_RCX_STA_EQUIVALENCE {profile}',
                       'ALL_32_HARD_MACRO_MASTERS_LOCATIONS_ORIENTATIONS_PRESERVED',
                       'EXPERIMENT_NATIVE_TIMING_CONSTRAINTS_BYTE_IDENTICAL'):
            if log.count(marker) != 1:
                raise ValueError(f'Missing unique native completion marker: {marker}')
        sdcs = [step/'experiment-before.sdc', step/'experiment-after.sdc', step/'soc_top.sdc']
        source_sdc = Path(json.loads((output/'prepared/state.json').read_text())['sdc'])
        if len({sha(p) for p in sdcs + [source_sdc]}) != 1:
            raise ValueError('Native before/after/output timing constraints differ')
        before = validate_measurement(policy.measurement(step/'experiment-before.json'), profile, 'before')
        after = validate_measurement(policy.measurement(step/'experiment-after.json'), profile, 'after')
        output_pins = policy.state_pins(step/'state_out.json')
        save(output/'portable-state.json', portable_state(json.loads((step/'state_out.json').read_text()), output, bundle))
        record.update(status='COMPLETE_ESTIMATE_ONLY', before=before, after=after,
                      eligible_estimate=policy.eligible(before, after, manifest['selected_source_metrics'], 'setup'),
                      sdc_sha256=sha(sdcs[0]), output_sha256=output_pins,
                      output_state=str(step/'state_out.json'),
                      inherited_views_are_not_new_signoff=True, cloud_output_root=str(output))
        record['setup_gain_per_hour'] = policy.setup_rates(record)
        save(output/'result.json', record)
    except BaseException as error:
        record.update(status='FAILED_PRESERVED', error=str(error), recorded=now())
        save(output/'result.json', record)
        print(str(error), file=sys.stderr)
        return 1
    return 0


def observation(output):
    output = Path(output)
    if not (output/'result.json').is_file():
        return dict(status='NO_RESULT_INCOMPLETE', terminal=True)
    record = json.loads((output/'result.json').read_text())
    status = record['status']
    if status in TERMINAL:
        return dict(status=status, terminal=True)
    if (output/'launch.json').is_file():
        launch = json.loads((output/'launch.json').read_text())
        try:
            fields = Path(f'/proc/{launch["pid"]}/stat').read_text().rsplit(') ', 1)[1].split()
            identity = launch.get('identity')
            if fields[0] == 'Z' or (identity and fields[19] != identity['birth']):
                return dict(status='WORKER_GONE_INCOMPLETE', terminal=True)
        except FileNotFoundError:
            return dict(status='WORKER_GONE_INCOMPLETE', terminal=True)
    return dict(status=status, terminal=False)


def wait(output, seconds=None, github_output=None):
    if seconds is not None and (not math.isfinite(seconds) or seconds < 0):
        raise ValueError('Observer wait duration must be nonnegative')
    started = time.monotonic()
    while True:
        result = observation(output)
        if result['terminal'] or (seconds is not None and time.monotonic()-started >= seconds):
            result.update(recorded=now(), worker_was_not_signaled=True)
            save(Path(output)/'observer.json', result)
            if github_output:
                with Path(github_output).open('a') as stream:
                    stream.write('terminal='+str(result['terminal']).lower()+'\n')
            print(json.dumps(result))
            return result
        time.sleep(min(15, max(0, seconds-(time.monotonic()-started))) if seconds is not None else 15)


def capture(output, destination):
    """Copy immutable evidence while worker continues; partial files are labelled."""
    output, destination = Path(output).resolve(), Path(destination).resolve()
    if destination.is_relative_to(output):
        raise ValueError('Snapshot destination must be outside worker output')
    destination = fresh_directory(destination)
    observed = observation(output)
    complete = observed['status'] == 'COMPLETE_ESTIMATE_ONLY'
    copied = {}
    for path in sorted(output.rglob('*')):
        if path.is_symlink():
            raise ValueError('Unexpected symlink in worker output')
        if not path.is_file() or path.suffix == '.tmp':
            continue
        if not complete and path.suffix not in ('.log', '.rpt', '.json', '.sdc'):
            continue
        relative = str(path.relative_to(output))
        target = destination/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with path.open('rb') as source, target.open('xb') as sink:
            # Fixed open-FD size makes each append-only log snapshot bounded.
            initial_size = os.fstat(source.fileno()).st_size
            remaining = initial_size
            while remaining:
                data = source.read(min(1024**2, remaining))
                if not data:
                    break
                sink.write(data)
                remaining -= len(data)
        copied[relative] = dict(bytes=target.stat().st_size, sha256=sha(target),
                                observed_source_bytes=initial_size, source_truncated_during_copy=bool(remaining))
    receipt = dict(recorded=now(), observation=observed, files=copied,
                   complete_candidate_views=complete, restart_checkpoint_accepted=False,
                   snapshot_is_atomic_across_files=False,
                   partial_native_database_excluded=not complete,
                   timing_accepted=False, manufacturing_approval=False)
    save(destination/'capture.json', receipt)
    return receipt


def validate_capture(result_path):
    """Tie a COMPLETE claim to its frozen files and every state dependency."""
    result_path = Path(result_path)
    root = result_path.parent
    row = json.loads(result_path.read_text())
    captured = json.loads((root/'capture.json').read_text())
    if (captured.get('complete_candidate_views') is not True
            or captured.get('observation', {}).get('status') != 'COMPLETE_ESTIMATE_ONLY'
            or captured.get('partial_native_database_excluded') is not False):
        raise ValueError('A partial progress capture cannot represent a completed candidate')
    inventory = captured['files']
    if not {'result.json', 'portable-state.json', 'source-manifest.json'} <= inventory.keys():
        raise ValueError('Final capture lacks result/state/input identity')
    for name, entry in inventory.items():
        safe_relative(name)
        pin(entry)
        if entry.get('source_truncated_during_copy') is not False:
            raise ValueError('Truncated file in completed capture')
        verify_file(root/name, entry)
    actual = {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
    if actual != set(inventory) | {'capture.json'} or any(p.is_symlink() for p in root.rglob('*')):
        raise ValueError('Final capture has unexpected files or symlinks')
    manifest = validate_manifest(json.loads((root/'source-manifest.json').read_text()))
    if sha(root/'source-manifest.json') != row['manifest_sha256']:
        raise ValueError('Captured manifest differs from experiment input')
    expected_identity = dict(bundle_sha256=manifest['archive']['sha256'],
        initial_state_template_sha256=manifest['files'][manifest['initial_state']]['sha256'],
        config_template_sha256=manifest['files'][manifest['config']]['sha256'],
        source_log_sha256=manifest['files'][manifest['source_log']]['sha256'],
        selected_source_metrics=manifest['selected_source_metrics'], runtime_sha256=RUNTIME_SHA256,
        method_sha256={name: manifest['files'][manifest['methods_dir']+'/'+name]['sha256'] for name in METHODS})
    if any(row.get(key) != value for key, value in expected_identity.items()):
        raise ValueError('Result input identities differ from its manifest')
    outroot, bundle = Path(row['cloud_output_root']), Path(row['work'])/'bundle'
    # Verify new views in the artifact; inherited views are bound to the exact
    # release bundle inventory, not mislabeled as fresh candidate signoff.
    for path, expected in row['output_sha256'].items():
        path = Path(path)
        if path.is_relative_to(outroot):
            relative = str(path.relative_to(outroot))
            if relative not in inventory or inventory[relative]['sha256'] != expected:
                raise ValueError('Required native output view is missing/changed')
        elif path.is_relative_to(bundle):
            relative = str(path.relative_to(bundle))
            if relative not in manifest['files'] or manifest['files'][relative]['sha256'] != expected:
                raise ValueError('Inherited native output view is not pinned to the input bundle')
        else:
            raise ValueError('Native output refers outside the captured result/input bundle')
    relative_state = str(Path(row['output_state']).relative_to(outroot))
    if relative_state not in inventory:
        raise ValueError('Native state view is missing')
    native = json.loads((root/relative_state).read_text())
    if row['output_state'] not in row['output_sha256']:
        raise ValueError('Native state itself lacks its output pin')
    def state_references(value):
        if isinstance(value, dict):
            return [p for v in value.values() for p in state_references(v)]
        if isinstance(value, list):
            return [p for v in value for p in state_references(v)]
        return [value] if isinstance(value, str) and value.startswith('/') else []
    if any(p not in row['output_sha256'] for p in state_references(native)):
        raise ValueError('Native state has an unpinned inherited/new dependency')
    for field in ('odb', 'def', 'nl', 'sdc'):
        if not isinstance(native.get(field), str) or native[field] not in row['output_sha256']:
            raise ValueError('Native state required view is not in its output inventory')
    portable = json.loads((root/'portable-state.json').read_text())
    if portable != portable_state(native, outroot, bundle):
        raise ValueError('Portable state differs from native state')
    return row


def compare(results, destination, manifest_path=None):
    """Independent policy check; no selection when either A/B is incomplete."""
    from run_timing_experiments import eligible, same_initial_measurements, choose_setup
    report = dict(status='INCOMPLETE_AB', timing_accepted=False, manufacturing_approval=False,
                  selected_checkpoint_preserved=True, compared_profile=None, recorded=now())
    try:
        rows = [validate_capture(path) for path in (results or [])]
        if len(rows) != 2 or {r['profile'] for r in rows} != set(PROFILES):
            raise ValueError('Exactly one completed result for each A/B profile is required')
        if any(r['status'] != 'COMPLETE_ESTIMATE_ONLY' for r in rows):
            raise ValueError('Incomplete/failed native A/B cannot select a profile')
        if manifest_path and any(r['manifest_sha256'] != sha(manifest_path) for r in rows):
            raise ValueError('Results do not use the requested pinned input manifest')
        for key in ('manifest_sha256', 'bundle_sha256', 'initial_state_template_sha256',
                    'config_template_sha256', 'method_sha256', 'runner_sha256', 'runtime_sha256',
                    'source_log_sha256', 'selected_source_metrics', 'sdc_sha256'):
            if rows[0][key] != rows[1][key]:
                raise ValueError(f'A/B input identity differs: {key}')
        for row in rows:
            before = validate_measurement(row['before'], row['profile'], 'before')
            after = validate_measurement(row['after'], row['profile'], 'after')
            if row.get('returncode') != 0 or row['eligible_estimate'] != eligible(before, after, row['selected_source_metrics'], 'setup'):
                raise ValueError('Native completion or eligibility receipt differs from recomputed guard')
        if not same_initial_measurements(rows[0]['before'], rows[1]['before']):
            raise ValueError('Fresh initial A/B timing, electrical, count or area measurements differ')
        a, b = [next(r for r in rows if r['profile'] == p) for p in PROFILES]
        selected = choose_setup(a, b)
        report.update(status='COMPLETE_ESTIMATE_COMPARISON_ONLY', same_initial_measurements=True,
                      compared_profile=selected['profile'] if selected else None,
                      comparison_recommendation_requires_routing_rcx_sta_equivalence=True,
                      eligible_profiles=[r['profile'] for r in rows if r['eligible_estimate']])
    except (KeyError, ValueError, OSError) as error:
        report.update(reason=str(error))
    save(destination, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest='mode', required=True)
    p = modes.add_parser('start')
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--profile', choices=PROFILES, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--work', type=Path, required=True)
    p = modes.add_parser('_worker')
    p.add_argument('--output', type=Path, required=True)
    p = modes.add_parser('wait')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--seconds', type=float)
    p.add_argument('--github-output', type=Path)
    p = modes.add_parser('capture')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--destination', type=Path, required=True)
    p = modes.add_parser('compare')
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--result', type=Path, action='append', default=[])
    p.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.mode == 'start':
        start(args.manifest, args.profile, args.output, args.work)
    elif args.mode == '_worker':
        raise SystemExit(worker(args.output))
    elif args.mode == 'wait':
        wait(args.output, args.seconds, args.github_output)
    elif args.mode == 'capture':
        capture(args.output, args.destination)
    elif args.mode == 'compare':
        result = compare(args.result, args.output, args.manifest)
        print(json.dumps(result))
        raise SystemExit(0 if result['status'] == 'COMPLETE_ESTIMATE_COMPARISON_ONLY' else 1)


if __name__ == '__main__':
    main()
