# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual processes cover leader-first exit, inherited masks, and group ownership."""
from pathlib import Path
import ctypes
import os
import signal
import sys
import time
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import owned_lifecycle05 as m


def until(predicate):
    deadline = time.monotonic() + 10
    while not predicate():
        assert time.monotonic() < deadline, 'Control fixture did not become ready'
        time.sleep(.01)


@pytest.fixture(autouse=True)
def reap_orphans():
    assert ctypes.CDLL(None).prctl(36, 1, 0, 0, 0) == 0  # child subreaper
    yield
    while True:
        try:
            pid, _ = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            break
        if not pid:
            break


def spawn(code):
    return m.owned_popen([sys.executable, '-c', code], start_new_session=True)


def parent_with_child(tmp_path, parent_end):
    ready = tmp_path / 'child-ready'
    code = f'''import os,signal,time,pathlib
pid=os.fork()
if pid==0:
 signal.signal(signal.SIGTERM, signal.SIG_IGN)
 pathlib.Path({str(ready)!r}).write_text(str(os.getpid()))
 while True: time.sleep(.01)
while not pathlib.Path({str(ready)!r}).exists(): time.sleep(.01)
{parent_end}
'''
    p = spawn(code)
    until(ready.exists)
    return p, int(ready.read_text())


@pytest.mark.parametrize('code', [0, 7])
def test_no_descendant_exit(code):
    p = spawn(f'import sys;sys.exit({code})')
    assert p.wait() == code
    assert p.poll() == code
    m.stop_failed_group(p)


def test_leader_term_child_ignores_term(tmp_path):
    p, child = parent_with_child(tmp_path, 'while True: time.sleep(.01)')
    try:
        m.stop_failed_group(p, grace_seconds=.05)
        assert p.returncode == -signal.SIGTERM
        assert not m.live_members(p.pid)
        assert m.identity(child) is None or child not in m.live_members(p.pid)
    finally:
        m.stop_failed_group(p, grace_seconds=.01)


@pytest.mark.parametrize('exitcode', [0, 9])
def test_leader_already_exited_before_poll(tmp_path, exitcode):
    p, _ = parent_with_child(tmp_path, f'os._exit({exitcode})')
    try:
        until(lambda: p.anchored() is not None)
        assert m.identity(p.pid) == p.nssoc_owned_identity  # zombie still reserves PID
        with pytest.raises(RuntimeError, match='live descendants'):
            p.poll()
        assert p.returncode == exitcode
        assert not m.live_members(p.pid)
    finally:
        m.stop_failed_group(p, grace_seconds=.01)


def test_unrelated_group_survives(tmp_path):
    unrelated = spawn('import time;time.sleep(60)')
    owned, _ = parent_with_child(tmp_path, 'while True: time.sleep(.01)')
    try:
        m.stop_failed_group(owned, grace_seconds=.05)
        assert unrelated.poll() is None
    finally:
        m.stop_failed_group(unrelated, grace_seconds=.01)
        m.stop_failed_group(owned, grace_seconds=.01)


def test_forged_identity_refused():
    p = spawn('import time;time.sleep(60)')
    real = p.nssoc_owned_identity.copy()
    try:
        p.nssoc_owned_identity['start_ticks'] = '-1'
        with pytest.raises(RuntimeError, match='refusing'):
            m.stop_failed_group(p, grace_seconds=.01)
        p.nssoc_owned_identity = real
        assert p.poll() is None
    finally:
        p.nssoc_owned_identity = real
        m.stop_failed_group(p, grace_seconds=.01)


def test_preexec_limits_and_mask_restore(tmp_path):
    limits = tmp_path / 'limits'
    old = signal.pthread_sigmask(signal.SIG_BLOCK, set())
    p = m.owned_popen([sys.executable, '-c',
        'import signal;assert signal.SIGTERM not in signal.pthread_sigmask(signal.SIG_BLOCK,set())'],
        start_new_session=True, preexec_fn=lambda: limits.write_text('applied'))
    assert p.wait() == 0
    assert limits.read_text() == 'applied'
    assert signal.pthread_sigmask(signal.SIG_BLOCK, set()) == old
