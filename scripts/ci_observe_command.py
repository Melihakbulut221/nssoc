#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Stream one unchanged CI command and retain bounded, owned cleanup evidence."""
import argparse
import ctypes
import errno
import hashlib
import json
import math
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import time

BUDGET_SECONDS = 21600
FINALIZATION_RESERVE_SECONDS = 180
TERM_SECONDS = 3.0
KILL_SECONDS = 3.0


def atomic_json(path, value):
    temp = path.with_name(path.name + '.pending')
    with temp.open('w', encoding='utf-8') as stream:
        json.dump(value, stream, sort_keys=True, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def identity():
    return {k: os.environ.get(k) for k in
            ('GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT', 'GITHUB_SHA', 'GITHUB_JOB')}


def budget_deadline(path):
    if path is None:
        return None, {'mode': 'no_wall_deadline', 'per_test_deadline_added': False}
    record = json.loads(Path(path).read_text(encoding='utf-8'))
    if record.get('schema') != 'nssoc-ci-job-budget-v1' or record.get('identity') != identity():
        raise ValueError('budget source/run/job identity')
    if record.get('maximum_seconds') != BUDGET_SECONDS or record.get('finalization_reserve_seconds') != FINALIZATION_RESERVE_SECONDS:
        raise ValueError('unchanged six-hour budget and explicit finalization reserve')
    origin = record.get('monotonic_origin_ns')
    now = time.monotonic_ns()
    if type(origin) is not int or not 0 < origin <= now:
        raise ValueError('actual earlier monotonic origin')
    deadline = origin / 1e9 + BUDGET_SECONDS - FINALIZATION_RESERVE_SECONDS
    return deadline, {**record, 'loaded_monotonic_ns': now,
                      'remaining_seconds': deadline - now / 1e9,
                      'per_test_deadline_added': False}


def proc_record(pid):
    try:
        text = Path('/proc', str(pid), 'stat').read_text()
        tail = text.rsplit(')', 1)[1].split()
        return {'pid': int(pid), 'ppid': int(tail[1]), 'state': tail[0],
                'start_ticks': int(tail[19]), 'session': int(tail[3])}
    except (FileNotFoundError, ProcessLookupError):
        return None


def descendants(owner):
    rows = {}
    for path in Path('/proc').iterdir():
        if path.name.isdigit():
            row = proc_record(int(path.name))
            if row is not None:
                rows[row['pid']] = row
    owned = {owner}
    while True:
        new = {pid for pid, row in rows.items() if row['ppid'] in owned} - owned
        if not new:
            break
        owned.update(new)
    return [rows[pid] for pid in sorted(owned - {owner}) if pid in rows]


def enable_subreaper():
    if sys.platform != 'linux':
        raise RuntimeError('Linux subreaper and /proc ownership are required')
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(36, 1, 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
        raise OSError(ctypes.get_errno(), 'PR_SET_CHILD_SUBREAPER')


class Journal:
    def __init__(self, path):
        self.stream = path.open('x', encoding='utf-8')
        self.sequence = 0

    def write(self, event, **data):
        self.sequence += 1
        value = {'sequence': self.sequence, 'event': event,
                 'monotonic_ns': time.monotonic_ns(), **data}
        self.stream.write(json.dumps(value, sort_keys=True, allow_nan=False) + '\n')
        self.stream.flush()
        os.fsync(self.stream.fileno())


def cleanup(process, journal):
    """Only signal descendants whose current PID/starttime still matches."""
    owner = os.getpid()
    sent = set()
    for sig, seconds in ((signal.SIGTERM, TERM_SECONDS), (signal.SIGKILL, KILL_SECONDS)):
        stop = time.monotonic() + seconds
        while True:
            process.poll()
            rows = descendants(owner)
            for row in rows:
                if row['state'] == 'Z' and row['ppid'] == owner and row['pid'] != process.pid:
                    try:
                        os.waitpid(row['pid'], os.WNOHANG)
                    except ChildProcessError:
                        pass
                    continue
                key = (row['pid'], row['start_ticks'], int(sig))
                if row['state'] == 'Z' or key in sent:
                    continue
                live = proc_record(row['pid'])
                if live is None or live['start_ticks'] != row['start_ticks']:
                    continue
                try:
                    pidfd = os.pidfd_open(row['pid'])
                except ProcessLookupError:
                    continue
                try:
                    bound = proc_record(row['pid'])
                    if bound is None or bound['start_ticks'] != row['start_ticks']:
                        continue
                    journal.write('SIGNAL_OWNED_DESCENDANT', signal=int(sig), ownership=row, pidfd_bound=True)
                    try:
                        signal.pidfd_send_signal(pidfd, sig)
                    except ProcessLookupError:
                        pass
                    sent.add(key)
                finally:
                    os.close(pidfd)
            process.poll()
            remaining = descendants(owner)
            if not remaining:
                return {'complete': True, 'signals_sent': len(sent), 'remaining': []}
            if time.monotonic() >= stop:
                break
            time.sleep(0.025)
    process.poll()
    remaining = descendants(owner)
    return {'complete': not remaining, 'signals_sent': len(sent), 'remaining': remaining}



class ProgressEcho:
    """Read append-only child events from outside pytest's capture machinery."""
    def __init__(self, path):
        self.path = path
        self.offset = 0
        self.pending = b''

    def poll(self):
        if not self.path.is_file():
            return
        with self.path.open('rb') as stream:
            stream.seek(self.offset)
            raw = stream.read()
        self.offset += len(raw)
        self.pending += raw
        complete = self.pending.split(b'\n')
        self.pending = complete.pop()
        for raw in complete:
            row = json.loads(raw)
            if row['event'] in ('TEST_START', 'TEST_FINISH', 'INTERRUPTED', 'INTERNAL_ERROR'):
                print('[pytest-progress] ' + raw.decode('utf-8'), flush=True)


def observe(argv, out, label, pytest_progress=False, budget_file=None):
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    journal = Journal(out / 'supervision.jsonl')
    process = None
    selector = selectors.DefaultSelector()
    output = (out / 'command.log').open('xb')
    primary = None
    signals = []
    previous_handlers = {}
    result = {'schema': 'nssoc-ci-command-observation-v1', 'identity': identity(),
              'label': label, 'requested_argv': list(argv), 'started': False,
              'command_returncode': None, 'reason': None, 'cleanup': None,
              'pytest_progress': pytest_progress, 'status': 'RUNNING'}
    digest = hashlib.sha256()
    output_bytes = 0
    child_env = dict(os.environ)
    progress_echo = ProgressEcho(out / 'pytest' / 'events.jsonl')
    try:
        deadline, budget = budget_deadline(budget_file)
        result['budget'] = budget
        journal.write('PREPARED', argv=argv, budget=budget, identity=identity())
        atomic_json(out / 'result.json', result)
        if deadline is not None and time.monotonic() >= deadline:
            result['reason'] = 'job_finalization_reserve_reached_before_start'
            raise TimeoutError(result['reason'])
        enable_subreaper()
        if pytest_progress:
            if len(argv) < 3 or argv[1:3] != ['-m', 'pytest']:
                raise ValueError('progress is only added to an explicit python -m pytest command')
            child_env['NSSOC_PYTEST_PROGRESS'] = str(out / 'pytest')
            child_env['PYTHONUNBUFFERED'] = '1'
            argv = [*argv, '-p', 'scripts.ci_pytest_progress',
                    '--junitxml=' + str(out / 'pytest-junit.xml')]
        result['executed_argv'] = list(argv)
        for sig in (signal.SIGINT, signal.SIGTERM):
            previous_handlers[sig] = signal.signal(sig, lambda number, frame: signals.append(number))
        process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   env=child_env, start_new_session=True)
        result['started'] = True
        result['leader'] = proc_record(process.pid)
        journal.write('STARTED', leader=result['leader'])
        atomic_json(out / 'result.json', result)
        os.set_blocking(process.stdout.fileno(), False)
        selector.register(process.stdout, selectors.EVENT_READ)
        last_census = 0.0
        last_flush = time.monotonic()
        seen = set()
        while True:
            now = time.monotonic()
            if now - last_census >= 0.25:
                for row in descendants(os.getpid()):
                    key = (row['pid'], row['start_ticks'])
                    if key not in seen:
                        journal.write('OWNED_DESCENDANT_OBSERVED', ownership=row)
                        seen.add(key)
                if pytest_progress:
                    progress_echo.poll()
                last_census = now
            for key, _ in selector.select(0.05):
                data = os.read(key.fd, 65536)
                if data:
                    output.write(data)
                    digest.update(data)
                    output_bytes += len(data)
                    sys.stdout.buffer.write(data)
                    sys.stdout.buffer.flush()
                else:
                    selector.unregister(key.fileobj)
            if now - last_flush >= 1:
                output.flush()
                os.fsync(output.fileno())
                last_flush = now
            if signals:
                result['reason'] = 'external_signal'
                result['received_signals'] = list(signals)
                break
            if deadline is not None and time.monotonic() >= deadline:
                result['reason'] = 'job_finalization_reserve_reached'
                break
            if process.poll() is not None:
                result['reason'] = 'command_exited'
                break
    except BaseException as exc:
        primary = exc
        result['primary_error'] = {'type': type(exc).__name__, 'message': str(exc)}
    finally:
        try:
            if process is not None:
                journal.write('CLEANUP_BEGIN', reason=result['reason'], leader_pid=process.pid)
                result['cleanup'] = cleanup(process, journal)
                # Cleanup closes inherited pipe writers, including helpers with their own sessions.
                drain_until = time.monotonic() + 2.0
                while selector.get_map() and time.monotonic() < drain_until:
                    for key, _ in selector.select(0.05):
                        data = os.read(key.fd, 65536)
                        if data:
                            output.write(data)
                            digest.update(data)
                            output_bytes += len(data)
                            sys.stdout.buffer.write(data)
                            sys.stdout.buffer.flush()
                        else:
                            selector.unregister(key.fileobj)
                result['output_pipe_eof'] = not bool(selector.get_map())
                result['command_returncode'] = process.poll()
            else:
                result['cleanup'] = {'complete': True, 'signals_sent': 0, 'remaining': []}
            if pytest_progress and (out / 'pytest' / 'events.jsonl').is_file():
                from ci_pytest_progress import finalize
                progress_echo.poll()
                result['pytest_finalization'] = finalize(out / 'pytest')
        except BaseException as exc:
            result['cleanup_or_finalization_error'] = {'type': type(exc).__name__, 'message': str(exc)}
            if primary is None:
                primary = exc
        finally:
            for sig, handler in previous_handlers.items():
                signal.signal(sig, handler)
            selector.close()
            output.flush()
            os.fsync(output.fileno())
            output.close()
            result['output'] = {'bytes': output_bytes, 'sha256': digest.hexdigest()}
            result['completed_monotonic_ns'] = time.monotonic_ns()
            normal = (primary is None and result['reason'] == 'command_exited'
                      and (result.get('cleanup') or {}).get('complete') is True
                      and result.get('output_pipe_eof', True))
            result['status'] = 'PASS' if normal and result['command_returncode'] == 0 else 'FAIL'
            result['exit_code'] = (result['command_returncode'] if normal and 0 <= result['command_returncode'] <= 255 else 125)
            atomic_json(out / 'result.json', result)
            journal.write('FINAL', result=result)
            journal.stream.close()
    return result['exit_code']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    parser.add_argument('--label', required=True)
    parser.add_argument('--pytest-progress', action='store_true')
    parser.add_argument('--budget-file', default=os.environ.get('NSSOC_CI_BUDGET_FILE'))
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        parser.error('an explicit command is required')
    return observe(command, args.out, args.label, args.pytest_progress, args.budget_file)


if __name__ == '__main__':
    raise SystemExit(main())
