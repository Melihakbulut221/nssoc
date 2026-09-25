# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bound complete measurement process groups, including stubborn descendants."""
import os
import signal
import subprocess
import time


def terminate_group(child, grace=5.0):
    try:
        os.killpg(child.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    deadline = time.monotonic() + grace
    while time.monotonic() < deadline:
        child.poll()
        try:
            os.killpg(child.pid, 0)
        except ProcessLookupError:
            break
        time.sleep(min(.05, max(0, deadline-time.monotonic())))
    # A reaped parent does not imply its process group is gone. Always address
    # the group again, including when the parent exited promptly on SIGTERM.
    try:
        os.killpg(child.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    child.wait()


def bounded_run(command, *, stdout, timeout, preexec_fn=None, grace=5.0):
    child = subprocess.Popen(command, stdout=stdout, stderr=subprocess.STDOUT,
                             start_new_session=True, preexec_fn=preexec_fn)
    try:
        code = child.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        terminate_group(child, grace)
        code = 124
    except BaseException:
        terminate_group(child, grace)
        raise
    return subprocess.CompletedProcess(command, code)
