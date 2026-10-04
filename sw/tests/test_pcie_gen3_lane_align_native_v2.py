# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Source conservation plus real parent-only TERM with an exited tool leader."""

import ast
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT / "scripts/check_pcie_gen3_lane_align_native_v1.py"
NEW = ROOT / "scripts/check_pcie_gen3_lane_align_native_v2.py"


def test_metrology_and_native_pipeline_unchanged():
    assert (
        hashlib.sha256(OLD.read_bytes()).hexdigest()
        == "ade53646cc5400f8e1765b7f20c052e6368728982d1173c4db88b074416d70d0"
    )
    old, new = ast.parse(OLD.read_text()), ast.parse(NEW.read_text())
    handler = next(
        n
        for n in new.body
        if isinstance(n, ast.FunctionDef) and n.name == "interrupted"
    )
    new.body.remove(handler)
    main = next(
        n for n in new.body if isinstance(n, ast.FunctionDef) and n.name == "main"
    )
    # Exclude only the explicitly reviewed lifetime handler installation and
    # frozen-parent acquisition binding; everything executable else is equal.
    assert ast.unparse(main.body[0]) == "signal.signal(signal.SIGTERM, interrupted)"
    main.body.pop(0)
    parent_asserts = [
        n
        for n in main.body
        if isinstance(n, ast.Assert) and "ade53646" in ast.unparse(n)
    ]
    assert len(parent_asserts) == 1
    main.body.remove(parent_asserts[0])
    inputs = next(
        n
        for n in main.body
        if isinstance(n, ast.Assign) and ast.unparse(n.targets[0]) == "inputs"
    )
    parent = [
        n
        for n in inputs.value.elts
        if ast.unparse(n) == "ROOT / 'scripts/check_pcie_gen3_lane_align_native_v1.py'"
    ]
    assert len(parent) == 1
    inputs.value.elts.remove(parent[0])
    assert ast.dump(old, include_attributes=False) == ast.dump(
        new, include_attributes=False
    )


def identity(pid):
    try:
        s = Path(f"/proc/{pid}/stat").read_text()
    except (FileNotFoundError, ProcessLookupError):
        return None
    f = s[s.rfind(")") + 2 :].split()
    return f[0], int(f[19])


def test_parent_term_kills_descendant_after_tool_leader_exits(tmp_path):
    tools = tmp_path / "tools"
    tools.mkdir()
    for name in ("iverilog", "vvp"):
        (tools / name).write_text("synthetic tool inventory only\n")
    tool = tools / "yosys"
    tool.write_text("""#!/usr/bin/python3
import os,signal,time,json
from pathlib import Path
leader=os.getpid()
child=os.fork()
if child==0:
 signal.signal(signal.SIGTERM,signal.SIG_IGN)
 s=Path('/proc/self/stat').read_text()
 start=int(s[s.rfind(')')+2:].split()[19])
 deadline=time.monotonic()+8
 Path('descendant.json').write_text(json.dumps(dict(pid=os.getpid(),start=start,group=os.getpgrp(),leader=leader,deadline=deadline)))
 while time.monotonic()<deadline:time.sleep(.02)
 Path('late-write').write_text('escaped group')
 time.sleep(30)
else:
 while True:time.sleep(.1)
""")
    tool.chmod(0o755)
    lib, models = tmp_path / "fake.lib", tmp_path / "fake.v"
    lib.write_text("test double; no foundry model\n")
    models.write_text("test double; no simulation\n")
    harness = tmp_path / "harness.py"
    harness.write_text(f"""
import sys,shutil
from pathlib import Path
sys.path.insert(0,{str(ROOT / "scripts")!r})
import check_pcie_gen3_lane_align_native_v2 as m
original=m.pin
def fake_gate_pin(p):
 p=Path(p)
 if p==Path({str(lib)!r}):return dict(bytes=p.stat().st_size,sha256=m.LIB_SHA)
 if p==Path({str(models)!r}):return dict(bytes=p.stat().st_size,sha256=m.MODEL_SHA)
 return original(p)
m.pin=fake_gate_pin
# Resource/library acquisition doubles only: exercise actual production
# launch/wait/TERM/finally/KILL code without PDK or any native simulator.
m.shutil.disk_usage=lambda _:shutil._ntuple_diskusage(4*1024**3,1024**3,3*1024**3)
m.main()
""")
    out = tmp_path / "capture"
    command = [
        sys.executable,
        str(harness),
        "--out",
        str(out),
        "--tools",
        str(tools),
        "--liberty",
        str(lib),
        "--models",
        str(models),
    ]
    with (tmp_path / "parent.log").open("w") as log:
        parent = subprocess.Popen(
            command,
            cwd=tmp_path,
            stdout=log,
            stderr=subprocess.STDOUT,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            start_new_session=True,
        )
        child = None
        try:
            deadline = time.monotonic() + 15
            while not (tmp_path / "descendant.json").exists():
                assert parent.poll() is None, (tmp_path / "parent.log").read_text()
                assert time.monotonic() < deadline
                time.sleep(0.02)
            child = json.loads((tmp_path / "descendant.json").read_text())
            assert (
                identity(child["pid"])[1] == child["start"]
                and child["group"] == child["leader"]
            )
            parent.send_signal(signal.SIGTERM)
            assert parent.wait(timeout=12) != 0
            deadline = time.monotonic() + 2
            while True:
                now = identity(child["pid"])
                if now is None or now[1] != child["start"] or now[0] == "Z":
                    break
                assert time.monotonic() < deadline, "Original descendant still alive"
                time.sleep(0.02)
            while time.monotonic() <= child["deadline"] + 0.15:
                time.sleep(0.02)
            assert not (tmp_path / "late-write").exists()
            r = json.loads((out / "result.json").read_text())
            assert (
                r["status"] == "FAIL_RETAINED"
                and "External process signal 15" in r["error"]
            )
            (tmp_path / "lifetime-observation.json").write_text(
                json.dumps(
                    dict(
                        child=child,
                        final_identity=identity(child["pid"]),
                        late_write=False,
                        parent_returncode=parent.returncode,
                        physics_run=False,
                        acquisition_gates_mocked=True,
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
                    os.killpg(child["group"], signal.SIGKILL)
                except ProcessLookupError:
                    pass
