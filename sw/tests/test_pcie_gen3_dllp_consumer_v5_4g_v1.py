# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Separate replay resource admission and actual process-group failure controls."""

import importlib.util
import ast
import json
import lzma
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "scripts/replay_pcie_gen3_dllp_consumer_v5_4g_v1.py"
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("consumer_replay4g", SOURCE)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


@pytest.fixture
def baseline_fixture(tmp_path, monkeypatch):
    """Only acquisition is synthetic; exercise production pin checks unchanged.

    The actual failed native baseline is checked separately before launch.
    A clean checkout must not require those historical /dev/shm files.
    """
    for name, data in {
        "source.v": b"fixture source\n",
        "runtime": b"fixture runtime identity\n",
        "mapped.v": b"fixture mapped bytes\n",
        "map.ys": b"fixture recipe\n",
        "abc.script": b"fixture ABC\n",
        "map.log": b"fixture prior map log\n",
        "simulation.log": b"fixture compiler std::bad_alloc\n",
    }.items():
        (tmp_path / name).write_bytes(data)
    raw = b'{"fixture":"not a real cell mapping"}\n'
    (tmp_path / "mapped.json").write_bytes(raw)
    (tmp_path / "mapped.json.xz").write_bytes(lzma.compress(raw))
    old = dict(
        status="FAIL",
        mapped_cells=128490,
        expected_tests=6,
        commands=[dict(returncode=0), dict(returncode=2)],
        inputs={str(tmp_path / "source.v"): M.pin(tmp_path / "source.v")},
        runtime={str(tmp_path / "runtime"): M.pin(tmp_path / "runtime")},
        mapped_inputs={
            str(tmp_path / n): M.pin(tmp_path / n)
            for n in ("mapped.v", "mapped.json", "map.ys", "abc.script")
        },
    )
    result = tmp_path / "result.json"
    result.write_text(json.dumps(old))
    monkeypatch.setattr(M, "BASE", tmp_path)
    monkeypatch.setattr(M, "BASE_RESULT_SHA", M.pin(result)["sha256"])
    return tmp_path


def test_producer_keeps_exact_real_baseline_acquisition():
    tree = ast.parse(SOURCE.read_text())
    literal = next(
        n.value
        for n in tree.body
        if isinstance(n, ast.Assign) and n.targets[0].id == "BASE_RESULT_SHA"
    )
    assert (
        ast.literal_eval(literal)
        == "16882e7a6859a2d6147704b79d0b25901283f1ea6dc6d06680ad13d98594a724"
    )
    main = next(
        n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main"
    )
    assert any(
        isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name)
        and n.func.id == "baseline"
        for n in ast.walk(main)
    )


def test_frozen_resource_profile_and_six_case_acquisition(baseline_fixture):
    old, inventory, cases = M.baseline()
    assert old["status"] == "FAIL" and old["mapped_cells"] == 128490
    assert len(cases) == 6 and old["commands"][1]["returncode"] == 2
    assert M.AS_LIMIT == 4 * 1024**3
    assert M.ENTRY_MEMORY == 8 * 1024**3 and M.RUN_MEMORY == 2 * 1024**3
    assert M.ENTRY_SCRATCH >= 1.3 * 1024**3 and M.RUN_SCRATCH == 528 * 1024**2
    assert "synthesis_performed=False" in SOURCE.read_text()
    assert len(inventory) == 9


@pytest.mark.parametrize(
    "filename",
    ["result.json", "source.v", "runtime", "mapped.v", "map.ys", "mapped.json.xz"],
)
def test_acquisition_fixture_mutations_rejected(baseline_fixture, filename):
    M.baseline()
    (baseline_fixture / filename).write_bytes(b"actual mutated fixture bytes")
    with pytest.raises((RuntimeError, lzma.LZMAError)):
        M.baseline()


@pytest.mark.parametrize("entry", [False, True])
@pytest.mark.parametrize("field", ["memory_available_bytes", "scratch_free_bytes"])
def test_each_resource_boundary(entry, field):
    values = dict(
        memory_available_bytes=M.ENTRY_MEMORY if entry else M.RUN_MEMORY,
        scratch_free_bytes=M.ENTRY_SCRATCH if entry else M.RUN_SCRATCH,
    )
    M.check_resources(values, entry)
    values[field] -= 1
    with pytest.raises(RuntimeError, match="floor"):
        M.check_resources(values, entry)


def test_real_input_mutation_rejected(tmp_path):
    p = tmp_path / "mapped.v"
    p.write_text("original")
    inventory = {str(p): M.pin(p)}
    M.verify_pins(inventory)
    p.write_text("mutated")
    with pytest.raises(RuntimeError, match="Pinned input changed"):
        M.verify_pins(inventory)


@pytest.mark.parametrize("fault", ["duplicate", "skipped", "failure", "missing"])
def test_exact_case_result_controls(tmp_path, fault):
    p = tmp_path / "results.xml"
    names = ["case" + str(i) for i in range(6)]

    def write(names, inner=""):
        p.write_text(
            "<testsuite>"
            + "".join(f'<testcase name="{n}">{inner}</testcase>' for n in names)
            + "</testsuite>"
        )

    write(names)
    assert M.validate_results(p, names) == dict(passed=6, failed=0, skipped=0)
    if fault == "duplicate":
        write(names[:-1] + names[:1])
    elif fault == "missing":
        write(names[:-1])
    else:
        write(names, "<" + fault + "/>")
    with pytest.raises(RuntimeError):
        M.validate_results(p, names)


def identity(pid):
    try:
        text = Path(f"/proc/{pid}/stat").read_text()
    except (FileNotFoundError, ProcessLookupError):
        return None
    fields = text[text.rfind(")") + 2 :].split()
    return fields[0], int(fields[19])


@pytest.mark.parametrize(
    "mode",
    [
        "parent_sigterm",
        "save_io_error",
        "memory_floor",
        "scratch_floor",
        "leader_exits_first",
    ],
)
def test_actual_group_cleanup_on_failure(tmp_path, mode):
    worker = tmp_path / "worker.py"
    worker.write_text(
        """import json,os,signal,time
from pathlib import Path
signal.signal(signal.SIGTERM,signal.SIG_IGN)
if MODE=='leader_exits_first':
    if os.fork():
        signal.signal(signal.SIGTERM,lambda s,f:exit(0))
        while True:time.sleep(.02)
s=Path('/proc/self/stat').read_text();start=int(s[s.rfind(')')+2:].split()[19]);deadline=time.monotonic()+8
Path('child.json').write_text(json.dumps(dict(pid=os.getpid(),group=os.getpgrp(),start=start,deadline=deadline)))
while time.monotonic()<deadline:time.sleep(.02)
Path('late-write').write_text('ESCAPED')
time.sleep(30)
""".replace("MODE", repr(mode))
    )
    runner = tmp_path / "runner.py"
    runner.write_text(f"""import os,sys,signal,time
from pathlib import Path
sys.path.insert(0,{str(ROOT / "scripts")!r})
import replay_pcie_gen3_dllp_consumer_v5_4g_v1 as m
out=Path.cwd();record={{}};mode={mode!r}
signal.signal(signal.SIGTERM,m.interrupted)
def snapshot():
    values=dict(memory_available_bytes=16*1024**3,scratch_free_bytes=4*1024**3)
    if (out/'child.json').exists():
        if mode=='memory_floor':values['memory_available_bytes']=m.RUN_MEMORY-1
        if mode=='scratch_floor':values['scratch_free_bytes']=m.RUN_SCRATCH-1
    return values
m.resource_snapshot=snapshot
def save():
    if mode=='save_io_error':
        while not (out/'child.json').exists():time.sleep(.01)
        raise OSError('injected ledger I/O failure')
m.execute([{sys.executable!r},{str(worker)!r}],out,dict(os.environ),record,save)
""")
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
            if mode in ("parent_sigterm", "leader_exits_first"):
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
            diagnostic = (tmp_path / "parent.log").read_text()
            expected = {
                "parent_sigterm": "External process signal",
                "leader_exits_first": "External process signal",
                "save_io_error": "injected ledger I/O failure",
                "memory_floor": "MemAvailable floor",
                "scratch_floor": "Shared scratch floor",
            }[mode]
            assert expected in diagnostic
            (tmp_path / "observation.json").write_text(
                json.dumps(
                    dict(
                        mode=mode,
                        child=child,
                        final_identity=identity(child["pid"]),
                        parent_returncode=parent.returncode,
                        exact_cause=expected,
                        late_write=False,
                        observed_after_deadline=True,
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
