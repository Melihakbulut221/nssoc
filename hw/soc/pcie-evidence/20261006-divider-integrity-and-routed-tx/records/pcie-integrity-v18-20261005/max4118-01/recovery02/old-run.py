# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Own exactly two unmodified MAX4118 pytest cases; no elapsed watchdog."""
import ctypes
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
import time

ROOT = Path(__file__).resolve().parents[5]
B = Path(__file__).resolve().parent
W = Path('/dev/shm/nssoc-integrity-v18-max4118-01')
sys.path.insert(0, str(ROOT / 'scripts'))
import characterize_pcie_clock_trim_stream_v2 as life


def pin(path):
    path = Path(path)
    with path.open('rb') as stream:
        return dict(bytes=path.stat().st_size,
                    sha256=hashlib.file_digest(stream, 'sha256').hexdigest())


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def subreaper():
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(36, 1, 0, 0, 0):  # PR_SET_CHILD_SUBREAPER
        raise OSError(ctypes.get_errno(), 'PR_SET_CHILD_SUBREAPER')


def descendants():
    """Only this controller's current process ancestry, including adopted children."""
    rows = {}
    for p in Path('/proc').iterdir():
        if p.name.isdigit():
            try:
                fields = (p / 'stat').read_text().rsplit(') ', 1)[1].split()
                rows[int(p.name)] = dict(pid=int(p.name), state=fields[0],
                    ppid=int(fields[1]), process_group=int(fields[2]), start_ticks=fields[19])
            except (FileNotFoundError, ProcessLookupError):
                pass
    owned = {os.getpid()}
    while True:
        new = {pid for pid, row in rows.items() if row['ppid'] in owned}
        if new <= owned:
            break
        owned |= new
    return [rows[pid] for pid in sorted(owned - {os.getpid()}) if pid in rows]


def same_birth(row):
    current = life.process_identity(row['pid'])
    return current is not None and current['start_ticks'] == row['start_ticks']


def cleanup_tree():
    """Terminate exact live descendants, even helpers which called setsid()."""
    record = dict(before=descendants(), signals=[], healthy_elapsed_watchdog=None)
    started = time.monotonic()
    for sig in [signal.SIGTERM, signal.SIGKILL]:
        for row in descendants():
            if row['state'] != 'Z' and same_birth(row):
                try:
                    os.kill(row['pid'], sig)
                    record['signals'].append(dict(identity=row, signal=int(sig)))
                except ProcessLookupError:
                    pass
        if sig == signal.SIGTERM:
            while time.monotonic() - started < 5:
                if not any(r['state'] != 'Z' for r in descendants()):
                    break
                time.sleep(0.02)
    record['after'] = descendants()
    return record


def guard(entry=False):
    free = shutil.disk_usage('/dev/shm').free
    available = int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines()
                         if x.startswith('MemAvailable:'))) * 1024
    own = sum(p.stat().st_size for p in W.rglob('*') if p.is_file()) if W.exists() else 0
    assert free >= (1024**3 if entry else 512 * 1024**2), ('scratch floor', free)
    assert available >= (1024**3 if entry else 512 * 1024**2), ('RAM floor', available)
    assert own <= 2 * 1024**3, ('own capture ceiling', own)
    return dict(shared_free=free, available_RAM=available, own_capture=own)


def main():
    assert os.sched_getaffinity(0) == {2}
    assert not W.exists() and not (B / 'status.json').exists()
    policy = json.loads((B / 'policy.json').read_text())
    for p, expected in policy['pins'].items():
        assert pin(p) == expected, p
    peer = json.loads((B / 'source-peer.json').read_text())
    assert peer['status'] == 'PASS_SOURCE_ONLY_V18_MAX4118_CONTROLLER'
    assert peer['policy'] == pin(B / 'policy.json') and not peer['findings']
    subreaper()
    guard(entry=True)
    W.mkdir()
    owner = life.ProcessOwner(B / 'owner.json')
    record = dict(status='STARTING', controller=life.process_identity(os.getpid()),
                  boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                  argv=sys.argv, CPU=2, policy=pin(B / 'policy.json'), peer=pin(B / 'source-peer.json'),
                  elapsed_watchdog_seconds=None, native_child_AS=2 * 1024**3,
                  stages=[], observed_descendants=[], resource=guard(), native_CPU6_untouched=True)

    def save():
        record['utc'] = datetime.datetime.now(datetime.UTC).isoformat()
        life.atomic(B / 'status.json', record)
        life.atomic(B / 'active-checkpoint.json', dict(status=record['status'],
            controller=record['controller'], boot_id=record['boot_id'], CPU=2,
            status_file=str(B / 'status.json'), owner_file=str(B / 'owner.json'),
            policy=record['policy'], RAM_root=str(W),
            next='Observe exact controller birth; never duplicate a live job. If interrupted, preserve this attempt and use a new version/root. Two functional MAX4118 cases only; native MAX150 unchanged.'))

    save()
    try:
        with owner:
            try:
                for stage in policy['stages']:
                    owner.check()
                    for p, expected in policy['pins'].items():
                        assert pin(p) == expected, p
                    guard(entry=True)
                    row = dict(name=stage['name'], command=stage['command'], status='RUNNING')
                    record['stages'].append(row)
                    record['status'] = 'RUNNING_' + stage['name']
                    save()
                    with (B / (stage['name'] + '.log')).open('x') as log:
                        process = owner.launch('native', stage['command'], cwd=ROOT,
                            stdout=log, stderr=subprocess.STDOUT, preexec_fn=limits,
                            env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'TMPDIR': str(W),
                                 'OMP_NUM_THREADS': '1', 'YOSYS_MAX_THREADS': '1',
                                 'PATH': str(ROOT / 'hw/soc/tools/cocotb-venv/bin') + ':' + os.environ['PATH']})
                        row['identity'] = life.process_identity(process.pid)
                        save()
                        seen = {}
                        last = 0
                        while process.poll() is None:
                            owner.check()
                            record['resource'] = guard()
                            for child in descendants():
                                seen[(child['pid'], child['start_ticks'])] = child
                            if time.monotonic() - last >= 5:
                                record['observed_descendants'] = list(seen.values())
                                record['current_descendants'] = descendants()
                                save()
                                last = time.monotonic()
                            time.sleep(0.1)
                        code = owner.complete(process)
                        owner.check()
                        guard()
                    row.update(returncode=code, status='COMPLETE' if code == 0 else 'FAILED_RETAINED',
                               observed_descendants=list(seen.values()), log=pin(B / (stage['name'] + '.log')))
                    save()
                    assert not any(c['state'] != 'Z' for c in descendants()), 'Live descendant after pytest exit'
                    for p, expected in policy['pins'].items():
                        assert pin(p) == expected, p
                    # A completed functional/frontend failure is retained; the
                    # second independent case may still run under fresh guards.
                owner.check()
                guard()
            except BaseException:
                record['tree_cleanup'] = cleanup_tree()
                raise
        owner.check()
        guard()
        record['status'] = ('COMPLETE_PENDING_INDEPENDENT_XML_REVIEW_AND_SEAL'
                            if all(s['returncode'] == 0 for s in record['stages'])
                            else 'FAILED_CASES_RETAINED_PENDING_REVIEW_AND_SEAL')
    except BaseException as error:
        record.update(status='INTERRUPTED_OR_RESOURCE_FAILURE_RETAINED', error=repr(error))
        raise
    finally:
        record['stop_reason'] = owner.reason
        record['current_descendants'] = descendants()
        save()


if __name__ == '__main__':
    main()
