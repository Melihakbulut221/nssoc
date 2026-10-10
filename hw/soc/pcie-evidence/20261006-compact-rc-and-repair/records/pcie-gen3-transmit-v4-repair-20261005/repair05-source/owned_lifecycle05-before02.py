# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Birth-bound cleanup of only an owned, still-running failed native group."""
from pathlib import Path
import os
import signal
import subprocess
import time


def identity(pid):
    try:
        fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
    except FileNotFoundError:
        return None
    return dict(pid=pid, process_group=int(fields[2]), start_ticks=fields[19])


def owned_popen(*args, **kwargs):
    assert kwargs.get('start_new_session') is True
    old = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM})
    try:
        process = subprocess.Popen(*args, **kwargs)
        process.nssoc_owned_identity = identity(process.pid)
        assert process.nssoc_owned_identity is not None
        assert process.nssoc_owned_identity['process_group'] == process.pid
        return process
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, old)


def stop_failed_group(process, grace_seconds=2.0):
    owned = process.nssoc_owned_identity
    if process.poll() is not None:
        return
    if identity(process.pid) != owned:
        raise RuntimeError('Owned process identity differs; refusing group signals')
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    deadline = time.monotonic() + grace_seconds
    while process.poll() is None and time.monotonic() < deadline:
        time.sleep(.05)
    if process.poll() is None and identity(process.pid) == owned:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    process.wait()
