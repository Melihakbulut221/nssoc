#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Let an existing separately grouped worker finish without its parent's timeout.

Linux only. Suspend only the supervising parent, never its worker/process group.
On worker exit, resume the original parent to reap the real exit status and run
its original validation. On a logged execution error, resume its error handler.
The existing parent must poll worker completion before testing its deadline,
and handle log errors before its deadline. This is a deliberate operator change
to elapsed-time policy, not a modification of tool inputs or resource limits.
"""
import argparse
import ctypes
import json
import os
from pathlib import Path
import signal
import time


def open_pidfd(pid):
    if hasattr(os, 'pidfd_open'):
        return os.pidfd_open(pid)
    # Some Python builds omit os.pidfd_open even on a supporting Linux host.
    libc = ctypes.CDLL(None, use_errno=True)
    function = libc.pidfd_open
    function.argtypes = [ctypes.c_int, ctypes.c_uint]
    function.restype = ctypes.c_int
    descriptor = function(pid, 0)
    if descriptor < 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))
    return descriptor


def process(pid):
    fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
    return dict(pid=pid, state=fields[0], parent=int(fields[1]),
                group=int(fields[2]), birth=fields[19])


def supervise(parent_pid, worker_pid, log, receipt, interval=1.0):
    parent, worker = process(parent_pid), process(worker_pid)
    if worker['parent'] != parent_pid or worker['group'] == parent['group']:
        raise ValueError('Expected a direct child in a separate process group')
    if parent['state'] in ('T', 't', 'Z'):
        raise ValueError('Parent must be a live, unsuspended controller')
    if Path(receipt).exists():
        raise ValueError('Receipt already exists')
    record = dict(status='PREPARING',parent=parent,worker=worker,
                  elapsed_time_limit_seconds=None,worker_restarted=False,
                  policy='Resume original validation after worker exit; preserve log-error handling')
    def save():
        target=Path(receipt)
        temporary=target.with_name(target.name+'.tmp')
        temporary.write_text(json.dumps(record,indent=2)+'\n')
        temporary.replace(target)
    descriptor=open_pidfd(parent_pid)
    stopped=False
    try:
        if process(parent_pid)['birth'] != parent['birth']:
            raise ValueError('Parent identity changed')
        save()
        signal.pidfd_send_signal(descriptor,signal.SIGSTOP)
        stopped=True
        while process(parent_pid)['state'] not in ('T','t'):
            time.sleep(.01)
        record['status']='WAITING_WITHOUT_DEADLINE'
        save()
        while True:
            current=process(worker_pid)
            if current['birth'] != worker['birth'] or current['parent'] != parent_pid:
                raise ValueError('Worker identity or parent changed')
            if current['state']=='Z':
                reason='Worker exited; original parent will reap and validate'
                break
            with Path(log).open('rb') as stream:
                stream.seek(max(0,Path(log).stat().st_size-65536))
                tail=stream.read()
            if b'ERROR:' in tail or b'std::bad_alloc' in tail:
                reason='Execution error logged; original parent will handle it'
                break
            time.sleep(interval)
        signal.pidfd_send_signal(descriptor,signal.SIGCONT)
        stopped=False
        record.update(status='ORIGINAL_CONTROLLER_RESUMED',reason=reason)
        save()
    except BaseException as error:
        # Do not accidentally reinstate an expired deadline while the worker is
        # running. The receipt makes an interrupted observer recoverable.
        record.update(status='OBSERVER_ERROR',error=repr(error),
                      original_controller_left_paused=stopped)
        save()
        raise
    finally:
        os.close(descriptor)
    return record


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parent',type=int,required=True)
    parser.add_argument('--worker',type=int,required=True)
    parser.add_argument('--log',type=Path,required=True)
    parser.add_argument('--receipt',type=Path,required=True)
    args=parser.parse_args()
    supervise(args.parent,args.worker,args.log,args.receipt)


if __name__=='__main__':
    main()
