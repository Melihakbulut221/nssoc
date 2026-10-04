# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual parent-only SIGTERM while native and owned publisher are blocked."""

import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]


def test_parent_sigterm_reaps_owned_native_and_publisher(tmp_path):
    native = tmp_path / "native"
    native.write_text(
        '#!/usr/bin/env python3\nimport time\nf=open("stream.fifo","wb",buffering=0)\nf.write(b"ready")\ntime.sleep(60)\n'
    )
    native.chmod(0o755)
    marker = tmp_path / "late-marker"
    identity = tmp_path / "publisher.json"
    child = (
        "import os,signal,time,json; from pathlib import Path; "
        "signal.signal(signal.SIGTERM,signal.SIG_IGN); "
        "deadline=time.monotonic()+8; "
        f"Path({str(identity)!r}).write_text(json.dumps(dict(pid=os.getpid(),deadline=deadline))); "
        f'time.sleep(max(0,deadline-time.monotonic())); Path({str(marker)!r}).write_text("escaped")'
    )
    body = f"""
import sys
from pathlib import Path
sys.path.insert(0, {str(ROOT / "scripts")!r})
import characterize_pcie_pll_loop_stream_v1 as m
m.n.NG=Path({str(native)!r})
def consume(stream,owner):
    assert stream.read(5)==b'ready'
    publisher=owner.launch('publisher',[sys.executable,'-c',{child!r}])
    owner.wait(publisher)
m.native_wait(Path({str(tmp_path)!r}),consume)
"""
    with (tmp_path / "controller.log").open("w") as log:
        controller = subprocess.Popen(
            [sys.executable, "-c", body],
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            until = time.monotonic() + 10
            while (
                not identity.exists()
                and controller.poll() is None
                and time.monotonic() < until
            ):
                time.sleep(0.02)
            assert identity.exists()
            observed = json.loads(identity.read_text())
            # Only the controller PID receives TERM, not the child groups.
            os.kill(controller.pid, signal.SIGTERM)
            assert controller.wait(timeout=12) == 1
            time.sleep(max(0, observed["deadline"] + 0.1 - time.monotonic()))
            assert not marker.exists()
        finally:
            if controller.poll() is None:
                controller.kill()
                controller.wait()
            ledger = tmp_path / "owned-processes.json"
            if ledger.exists():
                for process in json.loads(ledger.read_text())["processes"]:
                    try:
                        os.killpg(process["process_group"], signal.SIGKILL)
                    except ProcessLookupError:
                        pass
    record = json.loads((tmp_path / "owned-processes.json").read_text())
    assert record["status"] == "CANCELLED"
    assert record["reason"] == "Parent received SIGTERM"
    assert len(record["processes"]) == 2
    assert (
        json.loads((tmp_path / "execution.json").read_text())["returncode"] is not None
    )
    assert "Parent received SIGTERM" in (tmp_path / "controller.log").read_text()
