# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Own a native group until its descendants end, retaining its unreaped leader.

All callers use this wrapper's poll/wait. WNOWAIT keeps the leader PID reserved
even after leader exit, so a group signal cannot address a reused process group.
Only failure cleanup has a grace deadline; healthy native work has none.
"""
from pathlib import Path
import os
import signal
import subprocess
import time


def identity(pid):
    try:
        fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
    except (FileNotFoundError, ProcessLookupError):
        return None
    return dict(pid=pid, process_group=int(fields[2]), session=int(fields[3]),
                start_ticks=fields[19])


def live_members(group):
    members = []
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():
            continue
        try:
            fields = (path / 'stat').read_text().rsplit(')', 1)[1].split()
        except (FileNotFoundError, ProcessLookupError):
            continue
        if int(fields[2]) == group and fields[0] != 'Z':
            members.append(int(path.name))
    return members


class OwnedProcess:
    def __init__(self, process):
        self._process = process
        self.pid = process.pid
        self.nssoc_owned_identity = identity(self.pid)
        assert self.nssoc_owned_identity is not None
        assert self.nssoc_owned_identity['process_group'] == self.pid
        assert self.nssoc_owned_identity['session'] == self.pid

    @property
    def returncode(self):
        return self._process.returncode

    def anchored(self):
        if identity(self.pid) != self.nssoc_owned_identity:
            raise RuntimeError('Owned unreaped leader differs; refusing group signals')
        # Also prove this is still our waitable child, without reaping it.
        return os.waitid(os.P_PID, self.pid,
                         os.WEXITED | os.WNOHANG | os.WNOWAIT)

    def poll(self):
        if self.returncode is not None:
            return self.returncode
        ended = self.anchored()
        if ended is None:
            return None
        if live_members(self.pid):
            stop_failed_group(self)
            raise RuntimeError('Owned leader exited with live descendants; cleaned group')
        # No process can fork more children after all group members have exited.
        return self._process.wait()

    def wait(self):
        while self.poll() is None:
            time.sleep(.05)
        return self.returncode


def owned_popen(*args, **kwargs):
    assert kwargs.get('start_new_session') is True
    old = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM})
    limits = kwargs.pop('preexec_fn', None)

    def child_setup():
        # Do not make TERM-ignoring children accidentally by inheriting our mask.
        signal.pthread_sigmask(signal.SIG_SETMASK, old)
        if limits is not None:
            limits()

    try:
        process = subprocess.Popen(*args, preexec_fn=child_setup, **kwargs)
        return OwnedProcess(process)
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, old)


def stop_failed_group(process, grace_seconds=2.0):
    if process.returncode is not None:
        return  # Wrapper only reaps after the group has no live descendants.
    old = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM})
    try:
        process.anchored()
        os.killpg(process.pid, signal.SIGTERM)
        deadline = time.monotonic() + grace_seconds
        try:
            while live_members(process.pid) and time.monotonic() < deadline:
                time.sleep(.01)
        finally:
            # The leader remains unreaped through both signals, even if TERM
            # already killed it and an Icarus descendant ignored TERM.
            process.anchored()
            os.killpg(process.pid, signal.SIGKILL)
        while live_members(process.pid):
            time.sleep(.01)
        process._process.wait()
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, old)
