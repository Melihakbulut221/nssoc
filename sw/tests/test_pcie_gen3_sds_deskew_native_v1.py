# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Source conservation plus real parent-only TERM with an exited tool leader."""

import ast
import gzip
import importlib.util
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT / "scripts/check_pcie_gen3_lane_align_native_v4.py"
NEW = ROOT / "scripts/check_pcie_gen3_sds_deskew_native_v1.py"


@pytest.fixture
def method(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("deskew_native_v1", NEW)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("size", [0, 71, 3 * 1024**2])
def test_closed_vvp_full_lossless_recovery(tmp_path, method, size):
    p = tmp_path / "sim.vvp"
    p.write_bytes((bytes(range(256)) * ((size + 255) // 256))[:size])
    expected = method.pin(p)
    row = method.compress_closed_vvp(p)
    assert not p.exists()
    assert row["raw"] == row["full_decompressed_readback"] == expected
    recovered = tmp_path / "recovered.vvp"
    recovered.write_bytes(gzip.decompress(Path(row["compressed_path"]).read_bytes()))
    assert method.pin(recovered) == expected


def test_corrupt_decompressed_payload_preserves_raw(tmp_path, method, monkeypatch):
    p = tmp_path / "sim.vvp"
    p.write_bytes(b"exact compiled bytes")
    monkeypatch.setattr(method.gzip, "open", lambda *a, **k: io.BytesIO(b"wrong"))
    with pytest.raises(ValueError, match="readback differs"):
        method.compress_closed_vvp(p)
    assert p.read_bytes() == b"exact compiled bytes"
    assert not p.with_suffix(".vvp.gz").exists()


def test_changed_raw_during_compression_is_never_unlinked(tmp_path, method):
    p = tmp_path / "sim.vvp"
    p.write_bytes(b"before")
    calls = 0

    def change():
        nonlocal calls
        calls += 1
        if calls == 2:
            p.write_bytes(b"modified during readback")

    with pytest.raises(ValueError, match="changed"):
        method.compress_closed_vvp(p, change)
    assert p.read_bytes() == b"modified during readback"


@pytest.mark.parametrize("existing", [".vvp.gz", ".vvp.gz.partial"])
def test_no_compressed_capture_overwrite(tmp_path, method, existing):
    p = tmp_path / "sim.vvp"
    p.write_bytes(b"new")
    other = p.with_suffix(existing)
    other.write_bytes(b"old")
    with pytest.raises(ValueError, match="Fresh immutable"):
        method.compress_closed_vvp(p)
    assert other.read_bytes() == b"old" and p.read_bytes() == b"new"


def test_symlink_cannot_be_reclaimed(tmp_path, method):
    target = tmp_path / "target"
    target.write_bytes(b"owned elsewhere")
    link = tmp_path / "sim.vvp"
    link.symlink_to(target)
    with pytest.raises(ValueError, match="regular"):
        method.compress_closed_vvp(link)
    assert link.is_symlink() and target.read_bytes() == b"owned elsewhere"


def test_resource_failure_preserves_raw_and_partial(tmp_path, method):
    p = tmp_path / "sim.vvp"
    p.write_bytes(b"raw data")
    calls = 0

    def fail():
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("Shared storage floor breached")

    with pytest.raises(RuntimeError, match="floor"):
        method.compress_closed_vvp(p, fail)
    assert p.read_bytes() == b"raw data" and p.with_suffix(".vvp.gz.partial").exists()


def test_unlink_failure_retains_both_exact_copies(tmp_path, method, monkeypatch):
    p = tmp_path / "sim.vvp"
    p.write_bytes(b"retained")
    original = Path.unlink

    def fail(path, *a, **k):
        if path == p:
            raise OSError("injected unlink failure")
        return original(path, *a, **k)

    monkeypatch.setattr(Path, "unlink", fail)
    with pytest.raises(OSError, match="unlink"):
        method.compress_closed_vvp(p)
    assert p.read_bytes() == gzip.decompress(p.with_suffix(".vvp.gz").read_bytes())


def test_frozen_oracle_pins_and_complete_native_case_counts(method):
    assert method.pin(method.RTL)["sha256"] == method.RTL_SHA
    assert method.pin(method.TEST)["sha256"] == method.TEST_SHA
    spec = importlib.util.spec_from_file_location("sds_oracle", method.TEST)
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)
    assert len(oracle.CASES) == 20
    assert sum(not oracle.fixture(c)[2] for c in oracle.CASES) == 3
    assert len(oracle.MUTANTS) == 10
    assert set(oracle.MUTANTS) == set(method.MUTANT_DIAGNOSTICS)
    assert method.FLOOR == 528 * 1024**2
    assert method.OWNED_LIMIT == 320 * 1024**2


def test_vvp_compression_follows_successful_execute_return():
    tree = ast.parse(NEW.read_text())
    main = next(
        n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main"
    )
    native = next(
        n
        for n in main.body
        if isinstance(n, ast.FunctionDef) and n.name == "native_run"
    )
    statements = native.body
    completed = next(
        i
        for i, n in enumerate(statements)
        if isinstance(n, ast.Assign)
        and isinstance(n.targets[0], ast.Name)
        and n.targets[0].id == "completed"
    )
    preserved = next(
        i
        for i, n in enumerate(statements)
        if isinstance(n, ast.Assign)
        and isinstance(n.targets[0], ast.Name)
        and n.targets[0].id == "preserved"
    )
    assert completed < preserved
    assert statements[completed].value.func.id == "execute"
    assert statements[preserved].value.func.id == "compress_closed_vvp"


def test_native_mapping_and_lifecycle_functions_unchanged():
    modules = []
    for path in (OLD, NEW):
        main = next(
            n
            for n in ast.parse(path.read_text()).body
            if isinstance(n, ast.FunctionDef) and n.name == "main"
        )
        modules.append(
            {
                n.name: ast.dump(n, include_attributes=False)
                for n in main.body
                if isinstance(n, ast.FunctionDef)
            }
        )
    for name in ("mapped", "limit", "save"):
        assert modules[0][name] == modules[1][name], name


def test_execute_only_adds_explicit_expected_exit_code_gate():
    functions = []
    for path in (OLD, NEW):
        main = next(n for n in ast.parse(path.read_text()).body
                    if isinstance(n, ast.FunctionDef) and n.name == "main")
        execute = next(n for n in main.body
                       if isinstance(n, ast.FunctionDef) and n.name == "execute")
        functions.append(ast.unparse(execute))
    expected = functions[0].replace(
        "def execute(command, log, requested=None):",
        "def execute(command, log, requested=None, allowed_exit_codes=(0,)):",
    ).replace("status='LAUNCHING')", "status='LAUNCHING', allowed_exit_codes=list(allowed_exit_codes))")
    expected = expected.replace("if p.returncode:", "if p.returncode not in allowed_exit_codes:")
    assert functions[1] == expected


@pytest.mark.parametrize("returncode,stdout,passes", [
    (1, "FATAL: /owned/tb.v:50: FAULT_DETECTED_TOO_LATE\n       Time: 270000 Scope: tb\n", True),
    (0, "FATAL: /owned/tb.v:50: FAULT_DETECTED_TOO_LATE\n", False),
    (2, "FATAL: /owned/tb.v:50: FAULT_DETECTED_TOO_LATE\n", False),
    (-15, "", False),
    (1, "FATAL: /owned/tb.v:50: SOME_UNRELATED_FAULT\n", False),
    (1, "FATAL: /owned/tb.v:50: FAULT_DETECTED_TOO_LATE trailing\n", False),
    (1, "FATAL: /owned/tb.v:50: FAULT_DETECTED_TOO_LATE\nFATAL: second\n", False),
    (1, "native runtime error, no intended assertion\n", False),
])
def test_mutant_requires_exact_expected_native_fatal(method, returncode, stdout, passes):
    result = subprocess.CompletedProcess([], returncode, stdout, "")
    if passes:
        method.validate_mutant_exit(result, "FAULT_DETECTED_TOO_LATE")
    else:
        with pytest.raises(RuntimeError, match="Wrong native mutant"):
            method.validate_mutant_exit(result, "FAULT_DETECTED_TOO_LATE")


def test_specific_diagnostics_equal_frozen_oracle(method):
    tree = ast.parse(method.TEST.read_text())
    test = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                and n.name == "test_actual_hardware_fault_is_observable")
    assignment = next(n for n in test.body if isinstance(n, ast.Assign)
                      and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "diagnostics")
    assert ast.literal_eval(assignment.value) == method.MUTANT_DIAGNOSTICS


def test_inherited_compression_and_storage_functions_byte_ast_identity():
    modules = []
    for path in (OLD, NEW):
        modules.append({n.name: ast.dump(n, include_attributes=False)
                        for n in ast.parse(path.read_text()).body if isinstance(n, ast.FunctionDef)})
    for name in ("pin", "directory_bytes", "identity", "compress_closed_vvp", "atomic", "interrupted"):
        assert modules[0][name] == modules[1][name], name


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
import check_pcie_gen3_sds_deskew_native_v1 as m
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
