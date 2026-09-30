# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Guarded signals affect only synthetic children owned by this test process."""

import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import timing_process_guard as guard


def wait_state(pid, states):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        current = guard.snapshot(pid)
        if current is not None and current["state"] in states:
            return current
        time.sleep(.01)
    raise AssertionError(f"Synthetic process {pid} did not reach {states}")


def wait_exec_identity(child):
    """Wait for this fixture's exec transition, without relaxing signal guards."""
    deadline = time.monotonic() + 5
    previous = None
    last = None
    while time.monotonic() < deadline:
        code = child.poll()
        if code is not None:
            raise AssertionError(f"Synthetic child exited before stable exec identity: {code}")
        try:
            last = guard.snapshot(child.pid)
        except guard.ProcessGuardError:
            last = None
        if (last is not None and last["state"] in {"R", "S"}
                and last["command"] == child.args and last["group"] == child.pid):
            current = (last["birth"], tuple(last["command"]), last["group"])
            if current == previous:
                return last
            previous = current
        else:
            previous = None
        time.sleep(.005)
    raise AssertionError(f"Synthetic child did not reach stable exec identity: {last}")


@pytest.fixture
def sleeper():
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"], start_new_session=True)
    try:
        wait_exec_identity(child)
        yield child
    finally:
        if child.poll() is None:
            child.send_signal(signal.SIGCONT)
            child.terminate()
        child.wait(timeout=5)


def test_fixture_waits_for_two_stable_exec_observations(monkeypatch):
    child = SimpleNamespace(pid=123, args=["synthetic", "sleep"], poll=lambda: None)
    ready = dict(state="S", command=child.args, group=child.pid, birth="99")
    observations = iter([ready | {"command": []}, ready, ready])
    monkeypatch.setattr(guard, "snapshot", lambda pid: next(observations))
    monkeypatch.setattr(time, "sleep", lambda seconds: None)
    assert wait_exec_identity(child) == ready


def test_fixture_exec_wait_has_a_bounded_deadline(monkeypatch):
    child = SimpleNamespace(pid=123, args=["synthetic", "sleep"], poll=lambda: None)
    times = iter(range(7))
    monkeypatch.setattr(time, "monotonic", lambda: next(times))
    monkeypatch.setattr(time, "sleep", lambda seconds: None)
    monkeypatch.setattr(guard, "snapshot", lambda pid: dict(state="R", command=[]))
    with pytest.raises(AssertionError, match="did not reach stable exec identity"):
        wait_exec_identity(child)


def test_fixture_exec_wait_rejects_an_exited_child():
    child = SimpleNamespace(pid=123, args=["synthetic", "sleep"], poll=lambda: 7)
    with pytest.raises(AssertionError, match="exited before stable exec identity: 7"):
        wait_exec_identity(child)


def test_stat_parser_handles_spaces_and_parentheses():
    fields = ["0"] * 50
    fields[0], fields[1], fields[2], fields[19], fields[49] = "Z", "77", "123", "999", str(7 << 8)
    parsed = guard._parse_stat("123 (a ) tricky ( name) " + " ".join(fields))
    assert parsed == dict(pid=123, state="Z", parent=77, group=123, birth="999", exit_status_raw=7 << 8)


@pytest.mark.skipif(not hasattr(signal, "pidfd_send_signal"), reason="Linux pidfd signal required")
def test_guarded_stop_continue_real_child(sleeper):
    identity = guard.snapshot(sleeper.pid)
    assert identity["parent"] == os.getpid() and identity["group"] == sleeper.pid
    assert identity["command"] == sleeper.args
    guard.send_signal(identity, signal.SIGSTOP, allowed_states={"R", "S"})
    stopped = wait_state(sleeper.pid, {"T"})
    assert stopped["birth"] == identity["birth"]
    guard.send_signal(identity, signal.SIGCONT, allowed_states={"T"})
    wait_state(sleeper.pid, {"R", "S"})


@pytest.mark.parametrize("change", [
    {"birth": "0"}, {"command": ["wrong-command"]}, {"group": 0}, {"parent": 0}, {"boot_id": "wrong-boot"},
])
def test_identity_mismatch_never_sends_signal(sleeper, monkeypatch, change):
    identity = guard.snapshot(sleeper.pid) | change
    calls = []
    monkeypatch.setattr(signal, "pidfd_send_signal", lambda *args: calls.append(args), raising=False)
    with pytest.raises(guard.ProcessGuardError):
        guard.send_signal(identity, signal.SIGSTOP)
    assert not calls and guard.snapshot(sleeper.pid)["state"] != "T"


@pytest.mark.parametrize("identity", [{}, {"pid": 123, "birth": "9"}, {"pid": 123, "birth": "9", "command": []}])
def test_partial_identity_is_rejected(identity):
    with pytest.raises(guard.ProcessGuardError):
        guard.send_signal(identity, signal.SIGSTOP)


def test_self_and_unexpected_state_refused(sleeper):
    with pytest.raises(guard.ProcessGuardError, match="calling process"):
        guard.send_signal(guard.snapshot(os.getpid()), signal.SIGSTOP)
    with pytest.raises(guard.ProcessGuardError, match="Unexpected process state"):
        guard.send_signal(guard.snapshot(sleeper.pid), signal.SIGCONT, allowed_states={"T"})


def test_absent_pid_and_real_zombie_exit():
    child = subprocess.Popen([sys.executable, "-c", "raise SystemExit(7)"])
    try:
        zombie = wait_state(child.pid, {"Z"})  # Do not poll/wait before observing stat.
        assert zombie["exit_status_raw"] == 7 << 8
        assert zombie["command"] == []
        assert os.waitstatus_to_exitcode(zombie["exit_status_raw"]) == 7
    finally:
        child.wait(timeout=5)
    assert guard.snapshot(child.pid) is None


def test_children_and_descendants_find_only_synthetic_child(sleeper):
    parent = guard.snapshot(os.getpid())
    direct = {item["pid"] for item in guard.children(os.getpid())}
    recursive = {item["pid"] for item in guard.descendants(parent)}
    assert sleeper.pid in direct and sleeper.pid in recursive
    assert os.getpid() not in recursive


def test_pidfd_recheck_rejects_identity_change(sleeper, monkeypatch):
    identity = guard.snapshot(sleeper.pid)
    observations = iter([identity, identity | {"birth": "1"}])
    calls = []
    monkeypatch.setattr(guard, "snapshot", lambda pid: next(observations))
    monkeypatch.setattr(signal, "pidfd_send_signal", lambda *args: calls.append(args), raising=False)
    with pytest.raises(guard.ProcessGuardError, match="changed birth"):
        guard.send_signal(identity, signal.SIGSTOP)
    assert not calls
