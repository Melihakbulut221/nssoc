# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual parent-only TERM must reap the independently sessioned tool group."""

import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/check_pcie_gen3_block_cdc_v1.py"


def identity(pid):
    try:
        text = Path(f"/proc/{pid}/stat").read_text()
    except (FileNotFoundError, ProcessLookupError):
        return None
    fields = text[text.rfind(")") + 2 :].split()
    return fields[0], int(fields[19])


def test_parent_term_cleans_actual_term_ignoring_tool(tmp_path):
    tools = tmp_path / "tools"
    tools.mkdir()
    for name in ("iverilog", "vvp"):
        (tools / name).write_text("unused runtime pin\n")
    fake = tools / "make"
    fake.write_text("""#!/usr/bin/python3
import json,os,signal,time
from pathlib import Path
signal.signal(signal.SIGTERM,signal.SIG_IGN)
s=Path('/proc/self/stat').read_text();identity=int(s[s.rfind(')')+2:].split()[19])
deadline=time.monotonic()+8
Path('child.json').write_text(json.dumps(dict(pid=os.getpid(),start=identity,deadline=deadline)))
while time.monotonic()<deadline:time.sleep(.05)
Path('late-write').write_text('SURVIVED')
time.sleep(30)
""")
    fake.chmod(0o755)
    out = tmp_path / "capture"
    with (tmp_path / "parent.log").open("w") as log:
        parent = subprocess.Popen(
            [
                sys.executable,
                str(SCRIPT),
                "--out",
                str(out),
                "--iverilog-dir",
                str(tools),
            ],
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            start_new_session=True,
        )
        child = None
        try:
            deadline = time.monotonic() + 15
            while not (out / "child.json").exists():
                assert parent.poll() is None, (tmp_path / "parent.log").read_text()
                assert time.monotonic() < deadline, "Synthetic tool never entered"
                time.sleep(0.02)
            child = json.loads((out / "child.json").read_text())
            assert identity(child["pid"])[1] == child["start"]
            parent.send_signal(signal.SIGTERM)
            assert parent.wait(timeout=12) != 0
            deadline = time.monotonic() + 2
            while True:
                now = identity(child["pid"])
                if now is None or now[1] != child["start"] or now[0] == "Z":
                    break
                assert time.monotonic() < deadline, "Original child still alive"
                time.sleep(0.02)
            while time.monotonic() <= child["deadline"] + 0.15:
                time.sleep(0.02)
            assert not (out / "late-write").exists(), "Child escaped cleanup"
            record = json.loads((out / "result.json").read_text())
            assert (
                record["status"] == "FAIL"
                and "External process signal 15" in record["error"]
            )
            (tmp_path / "lifetime-observation.json").write_text(
                json.dumps(
                    dict(
                        child=child,
                        final_identity=identity(child["pid"]),
                        late_write=False,
                        parent_returncode=parent.returncode,
                    ),
                    indent=2,
                )
                + "\n"
            )
        finally:
            if parent.poll() is None:
                os.killpg(parent.pid, signal.SIGKILL)
                parent.wait()
            if child is not None:
                try:
                    os.killpg(child["pid"], signal.SIGKILL)
                except ProcessLookupError:
                    pass
