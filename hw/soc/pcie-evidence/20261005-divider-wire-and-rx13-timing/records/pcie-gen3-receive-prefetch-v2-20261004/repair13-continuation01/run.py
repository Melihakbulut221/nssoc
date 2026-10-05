# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Observe an existing owned route; run exact dependent stages once, no timeout."""
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
import threading
import time

ROOT = Path('/home/hasanmelih/Documents/ChatGPT/nnsoc')
B = ROOT / 'hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004'
HERE = Path(__file__).resolve().parent
MANIFEST = HERE / 'manifest.json'
DRT = Path('/dev/shm/nssoc-rx-prefetch-v2-repair13-drt-01')
RC = Path('/dev/shm/nssoc-rx-prefetch-v2-repair13-detailed-rc-01')
PEER = B / 'repair13-peer'
FLOOR = 528 * 1024**2


def pin(path):
    path = Path(path)
    with path.open('rb') as stream:
        return {'bytes': path.stat().st_size,
                'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}


def require(value, reason):
    if not value:
        raise ValueError(reason)


def atomic(path, record):
    path = Path(path)
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('w') as out:
        json.dump(record, out, indent=2)
        out.write('\n')
        out.flush()
        os.fsync(out.fileno())
    os.replace(temporary, path)


def limits():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_AS, (int(2.5 * 1024**3),) * 2)
    os.sched_setaffinity(0, {8})


def read_live_result():
    # Original DRT producer writes this receipt directly. A concurrent partial
    # JSON write is retried while its exact owner identity still exists.
    try:
        return json.loads((DRT / 'result.json').read_text())
    except json.JSONDecodeError:
        return None


def main():
    require(not (HERE / 'result.json').exists(), 'Fresh controller receipt')
    manifest = json.loads(MANIFEST.read_text())
    require(manifest['inputs'] == {p: pin(p) for p in manifest['inputs']},
            'Exact frozen continuation inputs')
    require(sorted(os.sched_getaffinity(0)) == [8], 'Controller CPU8')
    require(Path('/proc/sys/kernel/random/boot_id').read_text().strip() == manifest['boot_id'], 'Same recorded boot identity')
    # Reuse only the exact previously tested lifecycle class/helpers. The outer
    # failure grace is 15s so the RC wrapper can finish its own 5s group cleanup.
    life_path = Path(manifest['lifecycle_source'])
    tree = ast.parse(life_path.read_text())
    names = {'Cancelled', 'process_identity', 'group_members', 'ProcessOwner'}
    selected = [node for node in tree.body
                if isinstance(node, (ast.FunctionDef, ast.ClassDef))
                and node.name in names]
    require(len(selected) == 4, 'Exact lifecycle definitions')
    namespace = dict(os=os, Path=Path, threading=threading, signal=signal,
                     subprocess=subprocess, time=time, atomic=atomic,
                     require=require, FAILURE_GRACE_SECONDS=15.0)
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(life_path), 'exec'),
         namespace)
    identity = namespace['process_identity']
    record = dict(status='WAITING_EXISTING_EXACT_RX13_DRT01',
                  utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  controller_identity=identity(os.getpid()),
                  manifest=pin(MANIFEST), inputs=manifest['inputs'], stages=[],
                  original_DRT_owned_by_this_controller=False,
                  elapsed_watchdog_seconds=None, qualified_rc=False,
                  physical_acceptance=False)

    def save():
        atomic(HERE / 'result.json', record)

    def sources_unchanged():
        require(manifest['inputs'] == {p: pin(p) for p in manifest['inputs']},
                'Continuation source or runtime drift')

    save()
    with namespace['ProcessOwner'](HERE / 'owned-processes.json') as owner:
        try:
            missing_since = None
            while True:
                owner.check()
                current = read_live_result()
                if current:
                    require(current['pid'] == manifest['route_native']['pid'],
                            'Same native route PID in receipt')
                observed = identity(manifest['route_owner']['pid'])
                exact_owner = (observed is not None
                               and str(observed['start_ticks'])
                               == str(manifest['route_owner']['start_ticks'])
                               and observed['state'] != 'Z')
                if current and current['status'] != 'RUNNING':
                    break
                native = identity(manifest['route_native']['pid'])
                if native is not None:
                    require(str(native['start_ticks']) ==
                            str(manifest['route_native']['start_ticks']),
                            'Native route PID has not been reused')
                if not exact_owner:
                    if missing_since is None:
                        missing_since = time.monotonic()
                    # A dead/reused owner is failure; this is never an elapsed
                    # limit on a healthy route and sends no signal to old PIDs.
                    require(time.monotonic() - missing_since < 10,
                            'Route owner gone without terminal result')
                else:
                    missing_since = None
                owner.cancelled.wait(2)
            require(current['status'] ==
                    'COMPLETE_RX13_SIGNAL_DRT_ZERO_ROUTER_DRC_SAME_NETLIST__RC_REQUIRED'
                    and current['returncode'] == 0, 'Successful exact DRT required')
            require(current['inputs'] == manifest['route_inputs'], 'Same route inputs')
            require(current['inputs'] == {p: pin(p) for p in current['inputs']},
                    'All route inputs unchanged')
            require(current['outputs'] == {n: pin(DRT / n) for n in current['outputs']},
                    'All route outputs unchanged')
            require((DRT / 'router-drc.rpt').stat().st_size == 0, 'Zero router DRC')
            require((DRT / 'routed.v').read_bytes() ==
                    Path(manifest['candidate_netlist']).read_bytes(), 'Same proved netlist')
            record['route_terminal'] = pin(DRT / 'result.json')
            save()

            def run_stage(name, command, log, kind='native'):
                sources_unchanged()
                require(shutil.disk_usage('/dev/shm').free >= 1024**3,
                        '1GiB entry scratch floor')
                record['status'] = 'RUNNING_' + name
                stage = dict(name=name, command=command, log=str(log),
                             source_pins_before=manifest['inputs'])
                record['stages'].append(stage)
                save()
                with log.open('x') as output:
                    process = owner.launch(kind, command, cwd=ROOT,
                                           stdout=output, stderr=subprocess.STDOUT,
                                           preexec_fn=limits)
                    stage['identity'] = identity(process.pid)
                    save()
                    while process.poll() is None:
                        owner.check()
                        require(shutil.disk_usage('/dev/shm').free >= FLOOR,
                                '528MiB continuous scratch floor')
                        owner.cancelled.wait(.5)
                    stage['returncode'] = owner.complete(process)
                    owner.check()
                    require(shutil.disk_usage('/dev/shm').free >= FLOOR,
                            '528MiB terminal scratch floor')
                stage['log_pin'] = pin(log)
                sources_unchanged()
                stage['source_pins_after'] = manifest['inputs']
                save()
                require(stage['returncode'] == 0, name + ' nonzero exit')

            python = manifest['python']
            require(not RC.exists(), 'Fresh exact RC output')
            run_stage('RX13_NOMINAL_RC',
                      [python, str(B / 'detailed_rc_repair13.py')],
                      B / 'repair13-source/detailed-rc.log')
            result = json.loads((RC / 'result.json').read_text())
            require(result['status'] == 'COMPLETE_UNQUALIFIED_NOMINAL_RC_REVIEW_REQUIRED',
                    'Actual complete RC required')
            require(not (PEER / 'review.json').exists(), 'Fresh saved-output review')
            run_stage('RX13_SAVED_OUTPUT_REVIEW', [python, str(PEER / 'review.py')],
                      PEER / 'review.log')
            require(not (PEER / 'package.json').exists(), 'Fresh full capsule')
            run_stage('RX13_COMPLETE_CAPTURE_SEAL', [python, str(PEER / 'seal.py')],
                      PEER / 'seal.log')
            package = json.loads((PEER / 'package.json').read_text())
            require(package['status'] == 'PASS_COMPLETE_IMMUTABLE_MEMBER_READBACK',
                    'Complete archive/member readback')
            archive = Path(package['archive']['path'])
            require(pin(archive) == {k: package['archive'][k] for k in ('bytes', 'sha256')},
                    'Sealed archive unchanged')
            binding = PEER / 'pcie-rx-repair13-continuation-binding-20261005.json'
            require(not binding.exists(), 'Fresh immutable execution binding')
            atomic(binding, dict(status='PASS_EXACT_DEPENDENT_STAGES_BEFORE_PUBLICATION',
                                 controller=pin(Path(__file__)), manifest=manifest,
                                 stages=record['stages'],
                                 route_terminal=record['route_terminal'],
                                 extraction=pin(RC / 'result.json'),
                                 review=pin(PEER / 'review.json'),
                                 package=pin(PEER / 'package.json'),
                                 full_package_manifest=package,
                                 physical_acceptance=False, qualified_rc=False))
            validation = PEER / 'pcie-rx-repair13-finite-physical-validation-20261005.json'
            release = PEER / 'release.json'
            run_stage('RX13_PUBLIC_IMMUTABLE_PRESERVATION',
                      [python, str(ROOT / 'scripts/publish_pcie_native_capture_v3.py'),
                       '--out', str(release), str(archive), str(validation), str(binding)],
                      PEER / 'publication.log', kind='publisher')
            public = json.loads(release.read_text())
            require(public['status'] == 'PASS_IMMUTABLE_RELEASE_ROUNDTRIPS'
                    and len(public['assets']) == 3, 'All three public assets verified')
            record.update(status='COMPLETE_RX13_FINITE_ROUTE_RC_REVIEW_PUBLICATION',
                          native_timing=json.loads((PEER / 'review.json').read_text())
                          ['nominal_rc_cell_corner_slack_ns'], release=pin(release))
            save()
        except BaseException as error:
            record.update(status='FAILED_RETAINED_NO_DEPENDENT_BYPASS', error=repr(error))
            save()
            raise
    # A stop delivered during final complete/save/context teardown must propagate.
    try:
        owner.check()
    except BaseException as error:
        record.update(status='FAILED_RETAINED_NO_DEPENDENT_BYPASS', error=repr(error))
        save()
        raise
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
