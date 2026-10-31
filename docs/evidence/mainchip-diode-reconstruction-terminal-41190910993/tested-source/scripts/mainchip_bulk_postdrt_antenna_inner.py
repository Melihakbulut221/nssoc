#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Owned single bulk repair/route cycle with pinned runtime and strict supervision."""
import hashlib,json,os,signal,subprocess,sys,time,threading
from pathlib import Path
sys.path.insert(0,"/work/tail-source/scripts")
import mainchip_fixed_engine_route_tail_contract as c
import mainchip_bulk_postdrt_antenna as p
import mainchip_exit_checked_supervision as supervision
import mainchip_exit_checked_command_evidence as command_evidence
import cloud_mainchip_original_clock_restoration as stream_contract
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
        c.attempt(report,label+":progress",lambda:write("bulk-postdrt-inner-progress.json",report))
    if primary is not None:raise primary
    c.require(len(report["terminal_errors"])==first_error,label+" terminal errors")


ENGINE="/work/engine/openroad"
SCRIPT="/work/tail-source/scripts/mainchip_bulk_postdrt_antenna_native.py"
WORK=OUT/"work/bulk-postdrt-antenna"
DATA=OUT/"bulk-postdrt-antenna"
PHASE_COMMANDS={
 "prepare":("native","prepare",1200),
 "baseline-check":("tcl","baseline-check.tcl",1200),
 "baseline-audit":("native","baseline-audit",1200),
 "repair":("tcl","repair.tcl",1200),
 "insertion-audit":("native","insertion-audit",1200),
 "fixed-import":("tcl","fixed-import.tcl",1200),
 "fixed-audit":("native","fixed-audit",1200),
 "route":("tcl","route.tcl",14400),
 "restore-plan":("native","restore-plan",1200),
 "restore-import":("tcl","restore.tcl",1200),
 "restored-audit":("native","restored-audit",1200),
 "final-check":("tcl","final-check.tcl",1200),
 "final-audit":("native","final-audit",1200)}
INPUTS={
 "input":Path("/work/current-input.odb"),
 "donor":Path("/work/routing-inputs/clock/selected/source/geometry/routed/work/before-guide-read.odb"),
 "environment":Path("/work/routing-inputs/global/run/1-nssoc-repairfreshglobal/_env.tcl"),
 "original_tcl":Path("/work/routing-inputs/global/run/1-nssoc-repairfreshglobal/fresh_fanout_native.tcl"),
 "work":WORK,"out":DATA}

def stop_supervision(report,sup,beat):
    before=len(report["terminal_errors"])
    if sup is not None:
        c.attempt(report,"owned-native-process-cleanup",lambda:sup.stop_process(sup.ACTIVE))
        c.attempt(report,"heartbeat-stop",lambda:sup.STOP.set())
        def join():
            if beat is not None:
                beat.join(timeout=5);c.require(not beat.is_alive(),"heartbeat remained live")
        c.attempt(report,"heartbeat-join",join)
    return dict(complete=len(report["terminal_errors"])==before,errors=report["terminal_errors"][before:])

def supervised_run(report,label,argv,seconds,sup,cwd=WORK):
    """Original exit-checked RSS/deadline supervisor plus exact terminal evidence."""
    p.require(seconds in(1200,14400),"original phase or route deadline")
    row=dict(label=label,argv=argv,requested_timeout_seconds=seconds,returncode=None)
    report["commands"].append(row);primary=None;first_error=len(report["terminal_errors"])
    path=sup.TRACE/(label+".command.json")
    try:
        sup.supervised(argv,label,seconds=seconds,cwd=cwd)
        record=c.decode(c.secure_file(sup.TRACE,path.name).read_bytes())
        stream_contract.terminal_stream(record,sup.TRACE,label)
        proof=command_evidence.validate(record,seconds)
        p.require(record["argv"]==argv,"actual supervised argv")
        row.update(returncode=record["returncode"],supervision_record=record,command_evidence=proof)
    except BaseException as exc:
        primary=exc;row["error"]=c.error_record(label,exc)
    finally:
        if path.is_file():
            def preserve():
                raw=c.secure_file(sup.TRACE,path.name).read_bytes();record=c.decode(raw)
                row.update(supervision_record=record,returncode=record["returncode"],command_record_pin=p.pin(raw))
            c.attempt(report,label+":retain-full-command",preserve)
        c.attempt(report,label+":progress",lambda:write("bulk-postdrt-inner-progress.json",report))
    if primary is not None:raise primary
    c.require(len(report["terminal_errors"])==first_error,label+" supervision preservation failed")

def phase_command(kind,name,work=WORK):
    p.require(kind in("native","tcl"),"phase command kind")
    if kind=="native":
        return [ENGINE,"-no_init","-exit","-python",SCRIPT]
    p.require(name in("baseline-check.tcl","repair.tcl","fixed-import.tcl","route.tcl","restore.tcl","final-check.tcl"),"known Tcl")
    return [ENGINE,"-no_init","-exit",str(work/name)]

def execute_phase(report,label,kind,name,seconds,work=WORK,data=DATA,runner=None):
    p.require(type(seconds)is int and seconds>0 and callable(runner),"explicit owned phase runner")
    if kind=="native":os.environ["NSSOC_BULK_PHASE"]=name
    runner(report,"bulk-postdrt-"+label,phase_command(kind,name,work),seconds)
    result=dict(complete=True,kind=kind,name=name,timeout_seconds=seconds)
    if kind=="native":
        path=data/(name+"-terminal.json");raw=c.secure_file(data,path.name).read_bytes()
        terminal=c.decode(raw)
        p.require(terminal["phase"]==name and terminal["complete"]is True
          and terminal["error"]is None and terminal["terminal_errors"]==[],"native phase terminal")
        p.require(all(terminal[k]is False for k in p.FLAGS),"native phase flags")
        result["native_terminal"]=dict(path=str(path),**p.pin(raw))
    return result

def preserve_available(out=OUT):
    """Complete owned bulk byte census, independent of later host publication."""
    files={}
    for path in sorted(out.rglob("*")):
        relative=path.relative_to(out).as_posix()
        if not relative.startswith(("work/bulk-postdrt-antenna/","bulk-postdrt-antenna/","bulk-postdrt-")):continue
        p.require(not path.is_symlink(),"owned output symlink")
        if path.is_file():files[relative]=fingerprint(path)
        else:p.require(path.is_dir(),"owned output type")
    return dict(complete=True,files=files,scope="Complete currently available owned bulk files; prior frozen prefix remains separately authenticated.",
      native_acceptance=False,**p.FLAGS)

def run_bound_cycle(report,work=WORK,data=DATA,runner=None,writer=None,preserver=None):
    """Bind actual phase commands, retaining primary failure and independent cleanup."""
    p.exact(list(PHASE_COMMANDS),list(p.PHASES),"exact phase order")
    p.require(callable(runner),"explicit owned supervised runner")
    if writer is None:writer=lambda name,value:write("bulk-postdrt-"+name,value)
    if preserver is None:preserver=preserve_available
    states={name:"not_started"for name in p.PHASES}
    report["phase_states"]=states;report["cleanup_results"]={}
    def invoke(label,kind,name,seconds):
        return execute_phase(report,label,kind,name,seconds,work,data,runner)
    def action(name):
        states[name]="started"
        try:
            result=invoke(name,*PHASE_COMMANDS[name])
            states[name]="complete";return result
        except BaseException:
            states[name]="failed";raise
    def metadata_cleanup():
        if states["repair"]=="not_started":
            value=dict(complete=True,applicable=False,reason="repair callback never started")
        else:
            p.require((work/"insertion-after-shim.odb").is_file(),"repair attempted but preserved restored-metadata ODB absent")
            value=invoke("cleanup-antenna-metadata","native","antenna-restore-audit",1200)
            value.update(applicable=True,restoration_performed_inside_original_repair_tcl=True,
              independent_saved_state_audit=True)
        report["cleanup_results"]["restore-antenna-metadata"]=value;return value
    def class_cleanup():
        if states["fixed-import"]=="not_started":
            value=dict(complete=True,applicable=False,reason="encoded fixed overlay import never started")
        elif states["restored-audit"]=="complete":
            value=dict(complete=True,applicable=True,already_restored_and_audited=True,
              proof=report["phase_states"]["restored-audit"])
        else:
            steps=[]
            steps.append(invoke("cleanup-class-plan","native","failure-restore-plan",1200))
            steps.append(invoke("cleanup-class-import","tcl","restore.tcl",1200))
            steps.append(invoke("cleanup-class-audit","native","failure-restored-audit",1200))
            raw=c.secure_file(data,"class-restoration-plan.json").read_bytes()
            plan=c.decode(raw)
            p.require(plan["failure_cleanup"]is True and type(plan["used_pre_route_fallback"])is bool,"failure class plan")
            value=dict(complete=True,applicable=True,steps=steps,plan=plan,plan_pin=p.pin(raw),
              restored_failure_not_success=True)
        report["cleanup_results"]["restore-drt-classes"]=value;return value
    def preserve():
        value=preserver();p.require(value["complete"]is True,"complete available output census")
        writer("available-output-census.json",value)
        report["cleanup_results"]["preserve-available-output"]=value;return value
    return p.run_cycle({name:lambda name=name:action(name)for name in p.PHASES},
      {"restore-antenna-metadata":metadata_cleanup,"restore-drt-classes":class_cleanup,
       "preserve-available-output":preserve},writer)

def main():
    report=dict(status="IN_PROGRESS",commands=[],terminal_errors=[],**p.FLAGS)
    primary=None;started=time.monotonic();sup=None;beat=None;handlers={}
    def runtime():
        paths=set()
        for line in (OUT/"bulk-postdrt-ldd.stdout").read_text().splitlines():
            c.require("not found"not in line,"missing runtime dependency")
            for token in line.split():
                if token.startswith("/")and Path(token).is_file():paths.add(token)
        observed={path:fingerprint(Path(path))for path in sorted(paths)}
        write("bulk-postdrt-runtime-observed.json",observed)
        return c.runtime_match(c.decode(Path("/work/runtime-dependencies.json").read_bytes()),observed)
    def usage():
        root=Path("/sys/fs/cgroup")
        return {name:(root/name).read_text().strip()for name in
          ("memory.max","memory.swap.max","memory.events","memory.peak","cpu.max","pids.max")}
    def check_usage(value):
        c.require(value["memory.max"]==str(c.MEMORY)and value["memory.swap.max"]=="0"
          and value["pids.max"]==str(c.PIDS),"resource limits")
        quota,period=value["cpu.max"].split();c.require(quota!="max"and int(quota)==2*int(period),"CPU quota")
    try:
        c.require(not any(k in os.environ for k in("GH_TOKEN","GITHUB_TOKEN")),"credential-free native process")
        p.source_guard();report["cgroup_initial"]=usage();check_usage(report["cgroup_initial"])
        c.require(fingerprint(Path(ENGINE))==c.ENGINE,"ELF identity")
        c.require(fingerprint(INPUTS["input"])==p.INPUT,"current measured candidate")
        for name,path in INPUTS.items():os.environ["NSSOC_BULK_"+name.upper()]=str(path)
        run(report,"bulk-postdrt-version",[ENGINE,"-version"],30)
        run(report,"bulk-postdrt-ldd",["ldd",ENGINE],30)
        report["runtime_before"]=runtime()
        WORK.mkdir(parents=True,exist_ok=False)
        sup=supervision.supervisor();sup.OUT=OUT/"bulk-postdrt-supervisor";sup.TRACE=OUT/"bulk-postdrt-supervision"
        sup.OUT.mkdir();sup.TRACE.mkdir()
        c.require(sup.SECONDS==1200 and sup.MAX_GROUP_RSS_KIB==10485760 and sup.MIN_AVAILABLE_KIB==2097152,"original live resource guards")
        for sig in(signal.SIGINT,signal.SIGTERM):handlers[sig]=signal.signal(sig,sup.interrupted)
        beat=threading.Thread(target=sup.heartbeat,daemon=True);beat.start()
        runner=lambda report,label,argv,seconds:supervised_run(report,label,argv,seconds,sup)
        def preserve_after_supervisor_stop():
            stopped=stop_supervision(report,sup,beat)
            c.require(stopped["complete"],"supervision shutdown before stable output census")
            return preserve_available()
        report["cycle"]=run_bound_cycle(report,runner=runner,preserver=preserve_after_supervisor_stop)
        result=c.decode(c.secure_file(DATA,"result.json").read_bytes())
        c.require(result["status"]=="COMPLETE_ONE_BULK_POSTDRT_CYCLE"
          and result["declared_repair_calls"]==1 and result["declared_route_calls"]==1
          and result["requires_owned_command_proof"]is True,"complete actual bulk checks")
        labels=[row["label"]for row in report["commands"]]
        c.require(labels.count("bulk-postdrt-repair")==1 and labels.count("bulk-postdrt-route")==1,"exact actual one repair and one route")
        report["bounded_cycle_qualified"]=result["bounded_cycle_qualified"]
        report["native_complete"]=True
    except BaseException as exc:primary=exc;report["error"]=c.error_record("bulk-postdrt-antenna",exc)
    finally:
        stop_supervision(report,sup,beat)
        for sig,previous in handlers.items():
            def restore(sig=sig,previous=previous):
                signal.signal(sig,previous);return dict(signal=int(sig),restored=True)
            c.attempt(report,"restore-signal-"+str(sig),restore)
        c.attempt(report,"engine-unchanged",lambda:c.require(fingerprint(Path(ENGINE))==c.ENGINE,"ELF changed"))
        c.attempt(report,"input-unchanged",lambda:c.require(fingerprint(INPUTS["input"])==p.INPUT,"input changed"))
        if (OUT/"bulk-postdrt-ldd.stdout").is_file():
            c.attempt(report,"runtime-after",lambda:report.update(runtime_after=runtime()))
        def finish():
            value=usage();report["cgroup_terminal"]=value;check_usage(value)
            first=dict(x.split()for x in report["cgroup_initial"]["memory.events"].splitlines())
            last=dict(x.split()for x in value["memory.events"].splitlines())
            c.require(all(first.get(k,"0")==last.get(k,"0")for k in("oom","oom_kill","oom_group_kill")),"OOM")
        if "cgroup_initial"in report:c.attempt(report,"terminal-cgroup",finish)
        report["elapsed_seconds"]=time.monotonic()-started
        report["status"]="COMPLETE_BULK_POSTDRT_ENGINE"if primary is None and not report["terminal_errors"]and report.get("native_complete")else"FAIL_BULK_POSTDRT_ENGINE"
        c.finish_record(OUT/"bulk-postdrt-inner-result.json",report,"FAIL_BULK_POSTDRT_ENGINE",primary)
    return 0 if report["status"]=="COMPLETE_BULK_POSTDRT_ENGINE"else 1
if __name__=="__main__":sys.exit(main())
