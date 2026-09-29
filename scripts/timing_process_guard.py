#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Identity-guarded Linux process control for physical timing handovers.

Signals address one pidfd, never a process group. Pausing a controller does not
pause its child. Descendant snapshots are observations, not an atomic reservation;
pause a known idle controller and recheck before reserving physical-job resources.
"""

import ctypes
import os
from pathlib import Path
import signal


class ProcessGuardError(RuntimeError):
    """The requested process identity or state could not be proved."""


def _pidfd_open(pid):
    """Some bundled Python builds omit os.pidfd_open; libc still exposes it."""
    if hasattr(os, "pidfd_open"):
        return os.pidfd_open(pid, 0)
    library = ctypes.CDLL(None, use_errno=True)
    try:
        function = library.pidfd_open
    except AttributeError as error:
        raise ProcessGuardError("Linux pidfd_open support is required") from error
    function.argtypes = (ctypes.c_int, ctypes.c_uint)
    function.restype = ctypes.c_int
    descriptor = function(pid, 0)
    if descriptor < 0:
        number = ctypes.get_errno()
        raise OSError(number, os.strerror(number))
    return descriptor


def _parse_stat(text):
    """Linux stat's parenthesized comm can contain spaces and parentheses."""
    try:
        prefix, rest = text.rsplit(") ", 1)
        pid = int(prefix.split(" (", 1)[0])
        fields = rest.split()
        return {
            "pid": pid,
            "state": fields[0],
            "parent": int(fields[1]),
            "group": int(fields[2]),
            "birth": fields[19],
            # Field 52, encoded as for waitpid(); meaningful for a zombie.
            "exit_status_raw": int(fields[49]),
        }
    except (ValueError, IndexError) as error:
        raise ProcessGuardError("Malformed Linux process stat") from error


def snapshot(pid):
    """Return a JSON-serializable identity/state, or None for an absent PID.

``command`` is the exact argv list (empty for a zombie), ``birth`` is Linux
starttime in clock ticks, and ``exit_status_raw`` is the waitpid-encoded status.
The stat is read around cmdline to reject PID reuse or a transition to zombie.
    """
    if type(pid) is not int or pid <= 0:
        raise ProcessGuardError("A positive integer PID is required")
    directory = Path("/proc") / str(pid)
    for _ in range(3):
        try:
            before = _parse_stat((directory / "stat").read_text())
            command = (directory / "cmdline").read_bytes()
            after = _parse_stat((directory / "stat").read_text())
            boot_id = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
        except (FileNotFoundError, ProcessLookupError):
            return None
        except OSError as error:
            raise ProcessGuardError(f"Cannot inspect process {pid}") from error
        keys = ("pid", "birth", "parent", "group", "state")
        if all(before[key] == after[key] for key in keys):
            after["command"] = [os.fsdecode(arg) for arg in command.rstrip(b"\0").split(b"\0")] if command else []
            after["boot_id"] = boot_id
            return after
    raise ProcessGuardError(f"Process {pid} changed during identity inspection")


def _validate_identity(identity):
    if not isinstance(identity, dict):
        raise ProcessGuardError("An explicit process identity is required")
    if not {"pid", "birth", "command"} <= identity.keys():
        raise ProcessGuardError("Identity requires pid, birth and exact command argv")
    if type(identity["pid"]) is not int or identity["pid"] <= 1:
        raise ProcessGuardError("PID 1 and invalid PIDs cannot be controlled")
    if not isinstance(identity["birth"], str) or not identity["birth"].isdigit():
        raise ProcessGuardError("Birth must be the exact Linux starttime string")
    command = identity["command"]
    if not isinstance(command, list) or not command or not all(isinstance(arg, str) for arg in command):
        raise ProcessGuardError("A nonempty exact command argv list is required")
    for key in ("parent", "group"):
        if key in identity and (type(identity[key]) is not int or identity[key] < 0):
            raise ProcessGuardError(f"Invalid {key} identity")
    if "boot_id" in identity and not isinstance(identity["boot_id"], str):
        raise ProcessGuardError("Invalid boot identity")


def _match(identity, current):
    if current is None:
        raise ProcessGuardError(f"Process {identity['pid']} no longer exists")
    for key in ("pid", "birth", "command", "parent", "group", "boot_id"):
        if key in identity and identity[key] != current[key]:
            raise ProcessGuardError(f"Process {identity['pid']} changed {key}")


def send_signal(identity, signum, allowed_states=None):
    """Signal this exact live process through a pidfd; fail closed otherwise.

The return value is the checked pre-signal snapshot. Callers must subsequently
observe the requested state: delivery of SIGSTOP, for example, is asynchronous.
No fallback to numeric-PID os.kill is used on systems without pidfd support.
    """
    _validate_identity(identity)
    if identity["pid"] == os.getpid():
        raise ProcessGuardError("Refusing to signal the calling process")
    if not hasattr(signal, "pidfd_send_signal"):
        raise ProcessGuardError("Linux pidfd support is required")
    if not isinstance(signum, int) or signum not in signal.valid_signals():
        raise ProcessGuardError("A valid nonzero signal is required")
    if allowed_states is not None:
        allowed_states = set(allowed_states)
        if not allowed_states or not allowed_states <= set("RSDTtWXIP"):
            raise ProcessGuardError("Expected live process states must be explicit")
    _match(identity, snapshot(identity["pid"]))
    try:
        descriptor = _pidfd_open(identity["pid"])
    except OSError as error:
        raise ProcessGuardError("Could not acquire process pidfd") from error
    try:
        current = snapshot(identity["pid"])
        _match(identity, current)
        if current["state"] == "Z":
            raise ProcessGuardError("Refusing to signal a zombie")
        if allowed_states is not None and current["state"] not in allowed_states:
            raise ProcessGuardError(f"Unexpected process state {current['state']}")
        try:
            signal.pidfd_send_signal(descriptor, signum)
        except OSError as error:
            raise ProcessGuardError("Guarded process signal failed") from error
        return current
    finally:
        os.close(descriptor)


def children(pid):
    """Observe direct children created by every thread of one live process."""
    parent = snapshot(pid)
    if parent is None:
        return []
    directory = Path("/proc") / str(pid) / "task"
    child_pids = set()
    try:
        for task in directory.iterdir():
            try:
                child_pids.update(int(value) for value in (task / "children").read_text().split())
            except FileNotFoundError:
                continue  # A thread ended while inspecting the task directory.
    except FileNotFoundError:
        return []
    except OSError as error:
        raise ProcessGuardError(f"Cannot inspect children of process {pid}") from error
    result = []
    for child_pid in sorted(child_pids):
        child = snapshot(child_pid)
        if child is not None and child["parent"] == pid:
            result.append(child)
    current = snapshot(pid)
    if current is not None and current["birth"] != parent["birth"]:
        raise ProcessGuardError("Parent PID was reused during child inspection")
    return result


def descendants(identity):
    """Observe descendants with root identity checked before and after scanning."""
    _validate_identity(identity)
    _match(identity, snapshot(identity["pid"]))
    result = []
    pending = [identity["pid"]]
    seen = set(pending)
    while pending:
        for child in children(pending.pop()):
            if child["pid"] not in seen:
                seen.add(child["pid"])
                result.append(child)
                pending.append(child["pid"])
    _match(identity, snapshot(identity["pid"]))
    return result
