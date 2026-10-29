#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Pinned offline container, exact ELF/runtime, read-only current-chip diagnosis."""
import hashlib,json,os,signal,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,"/work/tail-source/scripts")
import mainchip_fixed_engine_route_tail_contract as c
from mainchip_witness_engine_build import fingerprint
OUT=Path("/work/out")
def write(name,value):c.atomic_record(OUT/name,value)
def run(report,label,argv,timeout):
    """Actual child lifecycle; cleanup and progress errors cannot replace the primary."""
    row=dict(label=label,argv=argv,returncode=None);report["commands"].append(row)
    before=time.monotonic();first_error=len(report["terminal_errors"]);p=None;primary=None
    try:
        with (OUT/(label+".stdout")).open("xb")as so,(OUT/(label+".stderr")).open("xb")as se:
            p=subprocess.Popen(argv,stdout=so,stderr=se,start_new_session=True,
              env={**os.environ,"LC_ALL":"C.UTF-8","PYTHONDONTWRITEBYTECODE":"1"})
            p.wait(timeout=timeout);row["returncode"]=p.returncode
            c.require(p.returncode==0,label+" failed")
    except BaseException as exc:
        primary=exc;row["error"]=c.error_record(label,exc)
    finally:
        if p is not None:
            def signal_if_live(sig):
                if p.poll()is None:os.killpg(p.pid,sig)
            def wait_if_live():
                if p.poll()is None:p.wait(timeout=10)
            # A failed stop cannot suppress the independent wait/kill/reap attempts.
            c.attempt(report,label+":stop",lambda:signal_if_live(signal.SIGTERM))
            c.attempt(report,label+":wait-after-stop",wait_if_live)
            c.attempt(report,label+":kill-if-live",lambda:signal_if_live(signal.SIGKILL))
            c.attempt(report,label+":wait-after-kill",wait_if_live)
            def terminal():
                row["returncode"]=p.poll();c.require(row["returncode"]is not None,"child remains live")
            c.attempt(report,label+":terminal-child",terminal)
        row["elapsed_seconds"]=time.monotonic()-before
        c.attempt(report,label+":progress",lambda:write("prune-inner-progress.json",report))
    if primary is not None:raise primary
    c.require(len(report["terminal_errors"])==first_error,label+" terminal errors")

def main():
    report=dict(status="IN_PROGRESS",commands=[],terminal_errors=[],
      physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
    primary=None;started=time.monotonic()
    def runtime():
        paths=set()
        for line in (OUT/"prune-ldd.stdout").read_text().splitlines():
            c.require("not found"not in line,"missing runtime dependency")
            for token in line.split():
                if token.startswith("/")and Path(token).is_file():paths.add(token)
        observed={p:fingerprint(Path(p))for p in sorted(paths)}
        write("prune-runtime-observed.json",observed)
        return c.runtime_match(c.decode(Path("/work/runtime-dependencies.json").read_bytes()),observed)
    def usage():
        root=Path("/sys/fs/cgroup")
        return {name:(root/name).read_text().strip()for name in
          ("memory.max","memory.swap.max","memory.events","memory.peak","cpu.max","pids.max")}
    def check_usage(value):
        c.require(value["memory.max"]==str(c.MEMORY) and value["memory.swap.max"]=="0"
          and value["pids.max"]==str(c.PIDS),"resource limits")
        quota,period=value["cpu.max"].split();c.require(quota!="max"and int(quota)==2*int(period),"CPU quota")
    try:
        c.require(not any(k in os.environ for k in ("GH_TOKEN","GITHUB_TOKEN")),"credential-free native process")
        report["cgroup_initial"]=usage();check_usage(report["cgroup_initial"])
        c.require(fingerprint(Path("/work/engine/openroad"))==c.ENGINE,"ELF identity")
        run(report,"prune-version",["/work/engine/openroad","-version"],30)
        run(report,"prune-ldd",["ldd","/work/engine/openroad"],30)
        report["runtime_before"]=runtime()
        engine="/work/engine/openroad";script="/work/tail-source/scripts/mainchip_net459_diode_prune_native.py"
        work=Path("/work/out/work/net459-diode-prune")
        def native(phase):
            os.environ["NSSOC_NET459_PRUNE_PHASE"]=phase
            run(report,"prune-"+phase,[engine,"-no_init","-exit","-python",script],2400)
        native("prepare")
        run(report,"prune-baseline-ant",[engine,"-no_init","-exit",str(work/"baseline-ant.tcl")],2400)
        run(report,"prune-import",[engine,"-no_init","-exit",str(work/"import.tcl")],1200)
        native("audit-import")
        run(report,"prune-candidate-check",[engine,"-no_init","-exit",str(work/"candidate-check.tcl")],3600)
        native("audit-measured")
        r=c.decode((OUT/"net459-diode-prune/result.json").read_bytes())
        c.require(r["status"]=="COMPLETE_BOUNDED_CANDIDATE_CHECKS"
          and r["exact_remaining_chip_preserved"]and r["all_1691_original_clocks_preserved"]
          and r["explicit_two_instance_delta"]and not r["physical_acceptance"],"complete actual candidate checks")
        report["candidate_checks_passed"]=r["bounded_candidate_checks_passed"]
        report["native_complete"]=True
    except BaseException as exc:primary=exc;report["error"]=c.error_record("net459-prune",exc)
    finally:
        c.attempt(report,"engine-unchanged",lambda:c.require(fingerprint(Path("/work/engine/openroad"))==c.ENGINE,"ELF changed"))
        if (OUT/"prune-ldd.stdout").is_file():
            c.attempt(report,"runtime-after",lambda:report.update(runtime_after=runtime()))
        def finish():
            value=usage();report["cgroup_terminal"]=value;check_usage(value)
            first=dict(x.split()for x in report["cgroup_initial"]["memory.events"].splitlines())
            last=dict(x.split()for x in value["memory.events"].splitlines())
            c.require(all(first.get(k,"0")==last.get(k,"0")for k in ("oom","oom_kill","oom_group_kill")),"OOM")
        if "cgroup_initial"in report:c.attempt(report,"terminal-cgroup",finish)
        report["elapsed_seconds"]=time.monotonic()-started
        report["status"]="COMPLETE_NET459_DIODE_PRUNE_ENGINE"if primary is None and not report["terminal_errors"]and report.get("native_complete")else"FAIL_NET459_DIODE_PRUNE_ENGINE"
        c.finish_record(OUT/"prune-inner-result.json",report,"FAIL_NET459_DIODE_PRUNE_ENGINE",primary)
    return 0 if report["status"]=="COMPLETE_NET459_DIODE_PRUNE_ENGINE"else 1
if __name__=="__main__":sys.exit(main())
