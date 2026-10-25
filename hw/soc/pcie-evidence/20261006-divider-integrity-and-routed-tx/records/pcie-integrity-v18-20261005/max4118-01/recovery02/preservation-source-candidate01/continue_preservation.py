# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Observe exact recovery owner then preserve closed observed/owned profiles."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import time

C = Path(__file__).resolve().parent
B = C.parent
ROOT = B.parents[4]
sys.path.insert(0, str(ROOT / 'scripts'))
import characterize_pcie_clock_trim_stream_v2 as life


def pin(path):
    path = Path(path)
    with path.open('rb') as stream:
        return dict(bytes=path.stat().st_size,
                    sha256=hashlib.file_digest(stream, 'sha256').hexdigest())


def load(path):
    return json.loads(Path(path).read_text())


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def main():
    assert os.sched_getaffinity(0) == {2}
    assert not (C / 'preservation-status.json').exists()
    policy = load(C / 'preservation-policy.json')
    for p, value in policy['pins'].items():
        assert pin(p) == value, p
    peer = load(C / 'preservation-source-peer.json')
    assert peer['status'] == 'PASS_SOURCE_ONLY_V18_MAX4118_RECOVERY_PRESERVATION'
    assert peer['policy'] == pin(C / 'preservation-policy.json') and not peer['findings']
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == policy['boot_id']
    life.FAILURE_GRACE_SECONDS = 15.0  # Frozen V3 publisher owns one-second cleanup.
    owner = life.ProcessOwner(C / 'preservation-owner.json')
    record = dict(status='WAITING_EXISTING_MAX4118_RECOVERY_CONTROLLER',
                  observer=life.process_identity(os.getpid()), observed=policy['controller'],
                  policy=pin(C / 'preservation-policy.json'), peer=pin(C / 'preservation-source-peer.json'),
                  stages=[], healthy_elapsed_watchdog=None)

    def save():
        record['utc'] = datetime.datetime.now(datetime.UTC).isoformat()
        life.atomic(C / 'preservation-status.json', record)

    def verify():
        owner.check()
        for p, value in policy['pins'].items():
            assert pin(p) == value, p
        assert shutil.disk_usage(B).free >= 1024**3
        assert shutil.disk_usage('/dev/shm').free >= 512 * 1024**2

    def stage(name, command):
        verify()
        row = dict(name=name, command=command, status='RUNNING')
        record['stages'].append(row)
        record['status'] = 'RUNNING_' + name
        save()
        with (C / (name + '.log')).open('x') as log:
            p = owner.launch('publisher' if name == 'publish' else 'native', command,
                             cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                             preexec_fn=limits,
                             env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
            row['identity'] = life.process_identity(p.pid)
            save()
            while p.poll() is None:
                owner.check()
                assert shutil.disk_usage(B).free >= 512 * 1024**2
                time.sleep(0.2)
            code = owner.complete(p)
            owner.check()
        row.update(returncode=code, status='COMPLETE' if code == 0 else 'FAILED_RETAINED',
                   log=pin(C / (name + '.log')))
        save()
        assert code == 0, (name, code)
        verify()

    save()
    try:
        with owner:
            while True:
                owner.check()
                current = life.process_identity(policy['controller']['pid'])
                same = current and current['start_ticks'] == policy['controller']['start_ticks'] and current['state'] != 'Z'
                if not same:
                    break
                time.sleep(5)
            verify()
            terminal = load(C / 'status.json')
            assert terminal['controller'] == policy['controller']
            assert terminal['boot_id'] == policy['boot_id']
            assert terminal['status'] in {'COMPLETE_TWO_PROFILES_XML_VERIFIED_REQUIRES_RECOVERY_AWARE_SEAL',
                                           'CLOSED_TWO_PROFILES_FAILURE_RETAINED_REQUIRES_RECOVERY_AWARE_SEAL'}
            assert not terminal['current_external'] and not terminal['current_owned']
            stage('seal', [sys.executable, str(C / 'seal.py')])
            archive = B / 'pcie-integrity-v18-max4118-complete-20261005.tar.xz'
            validation = B / 'pcie-integrity-v18-max4118-validation-20261005.json'
            package = B / 'pcie-integrity-v18-max4118-package-20261005.json'
            captures = [archive, validation, package]
            expected = {p.name: pin(p) for p in captures}
            record['sealed_capture'] = expected
            save()
            stage('publish', [sys.executable, str(ROOT / 'scripts/publish_pcie_native_capture_v3.py'),
                              '--out', str(B / 'release.json'), *map(str, captures)])
            release = load(B / 'release.json')
            assert release['status'] == 'PASS_IMMUTABLE_RELEASE_ROUNDTRIPS'
            assert len(release['assets']) == 3
            assert {a['name']: {k: a[k] for k in ('bytes', 'sha256')} for a in release['assets']} == expected
            assert all(a['authenticated_roundtrip'] and a['anonymous_roundtrip'] for a in release['assets'])
            assert {p.name: pin(p) for p in captures} == expected
            # Publisher's own immutable metadata and both independent readbacks
            # remain the publication gate; no asset overwrite is requested.
            record['status'] = 'COMPLETE_PUBLIC_CAPTURE_FINITE_DELIVERY_REVIEW_REQUIRED'
            record['release'] = pin(B / 'release.json')
            record['functional_status'] = load(validation)['status']
            owner.check()
        owner.check()
    except BaseException as error:
        record.update(status='FAILED_OR_STOPPED_PRESERVATION_RETAINED', error=repr(error))
        raise
    finally:
        record['stop_reason'] = owner.reason
        save()


if __name__ == '__main__':
    main()
