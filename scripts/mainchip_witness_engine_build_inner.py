#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud container: full native build and interface smoke, no chip/route run."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import traceback
from build_contract import MEMORY, PIDS, require

WORK = Path("/work")
OUT = WORK / "out"
START = time.monotonic()
DEADLINE = START + 10800
report = dict(schema="mainchip-witness-engine-inner-v1", status="IN_PROGRESS",
              compiled_complete_project=False, physical_acceptance=False,
              observer_equivalence_qualified=False, terminal_errors=[], commands=[])

def write(name, value):
    (OUT / name).write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")

def hash_file(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024*1024), b""):
            h.update(b)
    return dict(bytes=p.stat().st_size, sha256=h.hexdigest())

def cgroup():
    root = Path("/sys/fs/cgroup")
    keys = ("memory.current", "memory.peak", "memory.max", "memory.swap.max",
            "memory.events", "cpu.max", "cpu.stat", "pids.current", "pids.max", "pids.events")
    r = {}
    for key in keys:
        raw = (root / key).read_text().strip()
        r[key] = {k: int(v) for k,v in (line.split() for line in raw.splitlines())} if key in (
            "memory.events", "cpu.stat", "pids.events") else raw
    r["elapsed_seconds"] = time.monotonic() - START
    return r

def run(label, argv, timeout=None):
    require(time.monotonic() < DEADLINE, "build deadline exhausted")
    before = time.monotonic()
    entry = dict(label=label, argv=argv, returncode=None, timed_out=False)
    report["commands"].append(entry)
    proc = None
    try:
        with (OUT / (label+".stdout")).open("wb") as stdout, (OUT / (label+".stderr")).open("wb") as stderr:
            proc = subprocess.Popen(argv, stdout=stdout, stderr=stderr, start_new_session=True,
                                    env={**os.environ, "LC_ALL":"C.UTF-8", "PYTHONDONTWRITEBYTECODE":"1"})
            limit = min(DEADLINE, before + timeout) if timeout else DEADLINE
            with (OUT / "cgroup-samples.jsonl").open("a") as samples:
                while proc.poll() is None:
                    samples.write(json.dumps(cgroup(), sort_keys=True)+"\n"); samples.flush()
                    left = limit - time.monotonic()
                    if left <= 0:
                        entry["timed_out"] = True
                        raise TimeoutError(label)
                    try:
                        proc.wait(timeout=min(10, left))
                    except subprocess.TimeoutExpired:
                        pass
            entry["returncode"] = proc.returncode
            require(proc.returncode == 0, label+" failed")
    finally:
        if proc is not None and proc.poll() is None:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=10)
        if proc is not None:
            entry["returncode"] = proc.returncode
        entry["elapsed_seconds"] = time.monotonic() - before
        write("inner-progress.json", report)

def terminal(name, action):
    try:
        action()
    except Exception as exc:
        report["terminal_errors"].append(dict(action=name, error=repr(exc), traceback=traceback.format_exc()))

def finish_cgroup():
    report["cgroup_terminal"] = cgroup()
    first, last = report["cgroup_initial"], report["cgroup_terminal"]
    require(last["memory.max"] == str(MEMORY) and last["memory.swap.max"] == "0"
            and last["pids.max"] == str(PIDS), "terminal cgroup limits")
    for key in ("oom", "oom_kill", "oom_group_kill"):
        require(last["memory.events"].get(key,0) == first["memory.events"].get(key,0), "cgroup OOM")
    quota, period = last["cpu.max"].split()
    require(quota != "max" and int(quota) == 2*int(period), "terminal CPU quota")

def preserve_build_records():
    for relative in ("CMakeCache.txt", "compile_commands.json", "openroad_build.log"):
        p = WORK / "build" / relative
        if p.is_file():
            shutil.copyfile(p, OUT / relative)
    binpath = WORK / "build/bin/openroad"
    if binpath.is_file():
        shutil.copyfile(binpath, OUT / "openroad")
        os.chmod(OUT / "openroad", 0o755)
        report["binary"] = hash_file(OUT / "openroad")

def main():
    OUT.mkdir(exist_ok=True)
    try:
        report["cgroup_initial"] = cgroup()
        first = report["cgroup_initial"]
        require(first["memory.max"] == str(MEMORY) and first["memory.swap.max"] == "0"
                and first["pids.max"] == str(PIDS), "initial cgroup limits")
        quota, period = first["cpu.max"].split()
        require(quota != "max" and int(quota) == 2*int(period), "initial CPU quota")
        run("compiler", ["g++", "--version"], 30)
        run("cmake-version", ["cmake", "--version"], 30)
        run("packages", ["dpkg-query", "-W", "-f=$"+"{binary:Package}\t$"+"{Version}\n"], 60)
        prefix = Path("/etc/openroad_deps_prefixes.txt")
        require(prefix.is_file(), "pinned dependency prefixes missing")
        shutil.copyfile(prefix, OUT / "openroad_deps_prefixes.txt")
        run("complete-build", ["bash", "etc/Build.sh", "-no-gui", "-no-tests", "-threads=2",
            "-dir=/work/build", "-cmake=-DCMAKE_BUILD_TYPE=Release -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=OFF -DBUILD_PYTHON=ON -DGPU=OFF"])
        executable = str(WORK / "build/bin/openroad")
        require(Path(executable).is_file(), "complete executable missing")
        run("version", [executable, "-version"], 30)
        (OUT / "interface-smoke.tcl").write_text(
            'foreach cmd {detailed_route read_db write_db read_lef read_def write_def} {\n'
            '  if {[llength [info commands $cmd]] != 1} {error "missing command $cmd"}\n'
            '}\nputs "PASS_COMPLETE_OPENROAD_TCL_INTERFACES"\nexit\n')
        run("tcl-smoke", [executable, "-no_init", "-exit", str(OUT / "interface-smoke.tcl")], 60)
        require("PASS_COMPLETE_OPENROAD_TCL_INTERFACES" in (OUT/"tcl-smoke.stdout").read_text(), "Tcl smoke marker")
        (OUT / "interface-smoke.py").write_text(
            'import odb, openroad\n'
            'assert callable(odb.dbDatabase.create)\n'
            'assert callable(openroad.Tech) and callable(openroad.Design)\n'
            'print("PASS_COMPLETE_OPENROAD_PYTHON_INTERFACES")\n')
        run("python-smoke", [executable, "-no_init", "-exit", "-python", str(OUT / "interface-smoke.py")], 60)
        require("PASS_COMPLETE_OPENROAD_PYTHON_INTERFACES" in (OUT/"python-smoke.stdout").read_text(), "Python smoke marker")
        run("ldd", ["ldd", executable], 30)
        require("not found" not in (OUT/"ldd.stdout").read_text(), "missing runtime dependency")
        dependencies = {}
        for line in (OUT/"ldd.stdout").read_text().splitlines():
            for token in line.split():
                if token.startswith("/") and Path(token).is_file():
                    dependencies[token] = hash_file(Path(token))
        require(bool(dependencies), "missing runtime linkage record")
        write("runtime-dependencies.json", dependencies)
        report["compiled_complete_project"] = True
    except Exception as exc:
        report["failure"] = dict(error=repr(exc), traceback=traceback.format_exc())
    finally:
        terminal("preserve-build-records", preserve_build_records)
        terminal("terminal-cgroup", finish_cgroup)
        report["elapsed_seconds"] = time.monotonic() - START
        report["status"] = ("PASS_COMPLETE_OPENROAD_BUILD_AND_INTERFACE_SMOKE_ONLY"
                            if report["compiled_complete_project"] and not report["terminal_errors"]
                            and "failure" not in report else "FAIL_ENGINE_BUILD_OR_INTERFACE_SMOKE")
        write("inner-result.json", report)
    return 0 if report["status"].startswith("PASS_") else 1

if __name__ == "__main__":
    sys.exit(main())
