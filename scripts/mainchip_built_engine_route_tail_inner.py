#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Pinned container: reuse compiled ELF, authenticate runtime, read actual chip."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
sys.path.insert(0,"/work/tail-source/scripts")
sys.path.insert(0,"/work/source/scripts")
import mainchip_built_engine_route_tail_contract as c
from mainchip_built_engine_route_tail_contract import MEMORY,PIDS,require
from mainchip_witness_engine_build import fingerprint
WORK=Path("/work")
OUT=WORK/"out"
START=time.monotonic()
DEADLINE=START+c.LIMITS["inner_seconds"]
report=dict(schema="built-engine-route-tail-inner-v1",status="IN_PROGRESS",
            physical_acceptance=False,observer_equivalence_qualified=False,
            native_tail_requested=False,terminal_errors=[],commands=[])
def write(name,value):c.atomic_record(OUT/name,value)

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



def stop_child(proc, report, killpg=os.killpg):
    def terminate():
        if proc.poll() is None: killpg(proc.pid, signal.SIGTERM)
    def wait():
        proc.wait(timeout=10)
    def kill():
        if proc.poll() is None: killpg(proc.pid, signal.SIGKILL)
    c.attempt(report, "child-terminate", terminate)
    c.attempt(report, "child-wait-after-terminate", wait)
    c.attempt(report, "child-kill-if-live", kill)
    c.attempt(report, "child-final-wait", wait)


def run(label, argv, timeout=None, popen=subprocess.Popen, killpg=os.killpg):
    require(time.monotonic() < DEADLINE, "runtime probe deadline exhausted")
    before=time.monotonic(); primary=None; progress_error=None
    entry=dict(label=label,argv=argv,returncode=None,timed_out=False)
    report["commands"].append(entry); proc=None
    try:
        with (OUT/(label+".stdout")).open("wb") as stdout, (OUT/(label+".stderr")).open("wb") as stderr:
            proc=popen(argv,stdout=stdout,stderr=stderr,start_new_session=True,
                env={**os.environ,"LC_ALL":"C.UTF-8","PYTHONDONTWRITEBYTECODE":"1"})
            limit=min(DEADLINE,before+timeout) if timeout else DEADLINE
            with (OUT/"cgroup-samples.jsonl").open("a") as samples:
                while proc.poll() is None:
                    samples.write(json.dumps(cgroup(),sort_keys=True)+"\n");samples.flush()
                    left=limit-time.monotonic()
                    if left<=0:
                        entry["timed_out"]=True
                        raise TimeoutError(label)
                    try: proc.wait(timeout=min(10,left))
                    except subprocess.TimeoutExpired: pass
            entry["returncode"]=proc.returncode
            require(proc.returncode==0,label+" failed")
    except BaseException as exc:
        primary=exc;entry["error"]=c.error_record(label,exc)
    finally:
        if proc is not None:
            stop_child(proc,report,killpg)
            entry["returncode"]=proc.returncode
        entry["elapsed_seconds"]=time.monotonic()-before
        try: write("inner-progress.json",report)
        except BaseException as exc:
            progress_error=exc
            report["terminal_errors"].append(c.error_record("inner-progress",exc))
    if primary is not None: raise primary
    if progress_error is not None: raise progress_error


def finish_cgroup():
    report["cgroup_terminal"] = cgroup()
    first, last = report["cgroup_initial"], report["cgroup_terminal"]
    require(last["memory.max"] == str(MEMORY) and last["memory.swap.max"] == "0"
            and last["pids.max"] == str(PIDS), "terminal cgroup limits")
    for key in ("oom", "oom_kill", "oom_group_kill"):
        require(last["memory.events"].get(key,0) == first["memory.events"].get(key,0), "cgroup OOM")
    quota, period = last["cpu.max"].split()
    require(quota != "max" and int(quota) == 2*int(period), "terminal CPU quota")


def dependencies():
    runtime=c.decode((WORK/"runtime-dependencies.json").read_bytes())
    paths=set()
    for line in (OUT/"ldd.stdout").read_text().splitlines():
        require("not found" not in line,"missing runtime dependency")
        for token in line.split():
            if token.startswith("/") and Path(token).is_file():paths.add(token)
    actual={p:fingerprint(Path(p))for p in sorted(paths)}
    proof=c.runtime_match(runtime,actual)
    write("runtime-observed.json",actual)
    return proof

def main():
    primary=None
    try:
        require(not any(k in os.environ for k in ("GH_TOKEN","GITHUB_TOKEN","NNSOC_DRT_INTERNAL_WITNESS_DIR")),"native environment scope")
        require(not (WORK/"build").exists() and not (WORK/"source/src/Main.cc").exists(),"engine build tree must be absent")
        c.method(WORK/"tail-source")
        report["cgroup_initial"]=cgroup()
        finish_cgroup()
        executable=str(WORK/"engine/openroad")
        require(fingerprint(Path(executable))==c.ENGINE,"ELF identity")
        require(fingerprint(WORK/"input.odb")==c.INPUT,"input identity")
        run("version",[executable,"-version"],30)
        run("ldd",["ldd",executable],30)
        report["runtime_before"]=dependencies()
        script=OUT/"interface-smoke.tcl"
        script.write_text('foreach cmd {detailed_route read_db write_db read_lef read_def write_def} {\n'
                          '  if {[llength [info commands $cmd]] != 1} {error "missing command $cmd"}\n'
                          '}\nputs "PASS_COMPLETE_OPENROAD_TCL_INTERFACES"\nexit\n')
        run("tcl-smoke",[executable,"-no_init","-exit",str(script)],60)
        require("PASS_COMPLETE_OPENROAD_TCL_INTERFACES" in (OUT/"tcl-smoke.stdout").read_text(),"Tcl smoke marker")
        report["native_tail_requested"]=True
        run("route-tail",["/usr/bin/python3",
            "/work/tail-source/scripts/mainchip_built_engine_route_tail_driver.py"],c.LIMITS["driver_seconds"])
        native=c.decode((OUT/"case-result.json").read_bytes())
        require(native["status"]=="PASS_COMPLETE_ROUTE_TAIL_DIAGNOSTIC"
                and native["complete_tail"] and not native["terminal_errors"],"actual shared prefix")
        report["complete_actual_native_probe"]=True
    except BaseException as exc:
        primary=exc;report["failure"]=c.error_record("runtime-route-tail",exc)
    finally:
        if (OUT/"ldd.stdout").is_file():c.attempt(report,"runtime-identity-after",lambda:report.update(runtime_after=dependencies()))
        c.attempt(report,"ELF-unchanged",lambda:require(fingerprint(WORK/"engine/openroad")==c.ENGINE,"ELF changed"))
        c.attempt(report,"input-unchanged",lambda:require(fingerprint(WORK/"input.odb")==c.INPUT,"input changed"))
        c.attempt(report,"source-unchanged",lambda:c.method(WORK/"tail-source"))
        if "cgroup_initial"in report:c.attempt(report,"terminal-cgroup",finish_cgroup)
        report["elapsed_seconds"]=time.monotonic()-START
        report["status"]=("PASS_BUILT_ELF_ACTUAL_ROUTE_TAIL"
            if report.get("complete_actual_native_probe") and primary is None and not report["terminal_errors"]
            else "FAIL_BUILT_ELF_ACTUAL_ROUTE_TAIL")
        c.finish_record(OUT/"inner-result.json",report,"FAIL_BUILT_ELF_ACTUAL_ROUTE_TAIL",primary)
    return 0 if report["status"].startswith("PASS_")else 1
if __name__=="__main__":sys.exit(main())
