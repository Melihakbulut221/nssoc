# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Pinned recipe plus actual failure-only process-group cleanup before native."""

import ast
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import pytest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "scripts/check_pcie_gen3_dllp_consumer_native_v5.py"


def test_exact_recipe_and_frozen_positive_sources():
    tree = ast.parse(SOURCE.read_text())
    constants = {
        n.targets[0].id: ast.literal_eval(n.value)
        for n in tree.body
        if isinstance(n, ast.Assign)
        and isinstance(n.targets[0], ast.Name)
        and n.targets[0].id in ("ABC_RECIPE", "FROZEN_SOURCES")
    }
    assert constants["ABC_RECIPE"] == "strash; balance -x; &get -n; &nf; &put\n"
    for name, digest in constants["FROZEN_SOURCES"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
    assert " -nofsm -noabc; dfflibmap" in SOURCE.read_text()


def identity(pid):
    try:
        text = Path(f"/proc/{pid}/stat").read_text()
    except (FileNotFoundError, ProcessLookupError):
        return None
    f = text[text.rfind(")") + 2 :].split()
    return (f[0], int(f[19]))


@pytest.mark.parametrize("mode", ["parent_sigterm", "save_io_error"])
def test_actual_group_cleanup_on_failure(tmp_path, mode):
    worker = tmp_path / "worker.py"
    worker.write_text("""import json,os,signal,time
from pathlib import Path
signal.signal(signal.SIGTERM,signal.SIG_IGN)
s=Path('/proc/self/stat').read_text();start=int(s[s.rfind(')')+2:].split()[19]);deadline=time.monotonic()+8
Path('child.json').write_text(json.dumps(dict(pid=os.getpid(),start=start,deadline=deadline)))
while time.monotonic()<deadline:time.sleep(.02)
Path('late-write').write_text('ESCAPED')
time.sleep(30)
""")
    tree = ast.parse(SOURCE.read_text())
    main = next(
        n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main"
    )
    execute = next(
        n for n in main.body if isinstance(n, ast.FunctionDef) and n.name == "execute"
    )
    # Execute the exact compiled production function, not a copied substitute.
    module = ast.Module(body=[execute], type_ignores=[])
    runner = tmp_path / "runner.py"
    runner.write_text(
        """import os,signal,subprocess,time,shutil
from pathlib import Path
out=Path.cwd();env=dict(os.environ);r={'commands':[]}
def limits():pass
def stop(sig,frame):raise KeyboardInterrupt('actual parent signal')
signal.signal(signal.SIGTERM,stop)
def save():
"""
        + (
            """    while not (out/'child.json').exists():time.sleep(.01)
    raise OSError('injected ledger I/O failure')
"""
            if mode == "save_io_error"
            else "    pass\n"
        )
        + ast.unparse(module)
        + f"\nexecute([{sys.executable!r},{str(worker)!r}], 'child.log')\n"
    )
    child = None
    with (tmp_path / "parent.log").open("w") as log:
        parent = subprocess.Popen(
            [sys.executable, str(runner)],
            cwd=tmp_path,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            end = time.monotonic() + 10
            while not (tmp_path / "child.json").exists():
                assert parent.poll() is None and time.monotonic() < end
                time.sleep(0.02)
            child = json.loads((tmp_path / "child.json").read_text())
            assert identity(child["pid"])[1] == child["start"]
            if mode == "parent_sigterm":
                parent.send_signal(signal.SIGTERM)
            assert parent.wait(timeout=12) != 0
            end = time.monotonic() + 2
            while True:
                current = identity(child["pid"])
                if current is None or current[1] != child["start"] or current[0] == "Z":
                    break
                assert time.monotonic() < end, "Child survived KILL/reap"
                time.sleep(0.02)
            while time.monotonic() <= child["deadline"] + 0.1:
                time.sleep(0.02)
            assert not (tmp_path / "late-write").exists()
            (tmp_path / "observation.json").write_text(
                json.dumps(
                    dict(
                        mode=mode,
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
            if child:
                try:
                    os.killpg(child["pid"], signal.SIGKILL)
                except ProcessLookupError:
                    pass
