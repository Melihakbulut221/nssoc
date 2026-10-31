#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only continuation of admitted saved diodes through one detailed route."""
import os,sys,json,time,signal,threading
from pathlib import Path
sys.path.insert(0,"/work/tail-source/scripts")
import mainchip_bulk_postdrt_antenna_inner as base
import cloud_mainchip_saved_diode_routing as qualification_host
import mainchip_saved_diode_routing as plan
import mainchip_container_floorplan_import as container
from mainchip_bulk_postdrt_antenna_inner import (
 c,p,supervision,command_evidence,stream_contract,fingerprint,OUT,write,run,
 ENGINE,WORK,DATA,INPUTS,stop_supervision,supervised_run,preserve_available)
SCRIPT="/work/tail-source/scripts/mainchip_saved_diode_routing_native.py"
def run_route_cycle(report,runner,preserver):
    def invoke(name):
        if name in plan.PREPARATION:
            os.environ["NSSOC_SAVED_DIODE_ROUTE_PHASE"]=name
            runner(report,"bulk-postdrt-route-continuation-"+name,[ENGINE,"-no_init","-exit","-python",SCRIPT],1200)
            terminal=c.decode(c.secure_file(DATA,"route-continuation-"+name+"-terminal.json").read_bytes())
            p.require(terminal["phase"]=="route-continuation-"+name and terminal["complete"]is True
              and terminal["error"]is None and terminal["terminal_errors"]==[],"actual preparation terminal")
            p.require(all(terminal[k]is False for k in p.FLAGS),"preparation acceptance scope")
            return dict(complete=True,native_terminal=terminal)
        return container.execute_phase(base,report,name,*base.PHASE_COMMANDS[name],runner=runner,script=SCRIPT,engine=ENGINE)
    def restore(states):
        if states["fixed-import"]=="not_started":
            return dict(complete=True,applicable=False,reason="fixed overlay import never started")
        if states["restored-audit"]=="complete":
            return dict(complete=True,applicable=True,already_restored_and_audited=True)
        steps=[]
        for label,kind,name in(
          ("cleanup-class-plan","native","failure-restore-plan"),
          ("cleanup-class-import","tcl","restore.tcl"),
          ("cleanup-class-audit","native","failure-restored-audit")):
            steps.append(container.execute_phase(base,report,label,kind,name,1200,runner=runner,script=SCRIPT,engine=ENGINE))
        restoration=c.decode(c.secure_file(DATA,"class-restoration-plan.json").read_bytes())
        p.require(restoration["failure_cleanup"]is True and type(restoration["used_pre_route_fallback"])is bool,"actual failure restoration")
        return dict(complete=True,applicable=True,steps=steps,plan=restoration,restored_failure_not_success=True)
    def record(name,value):
        report["route_cycle"]=value;write("bulk-postdrt-"+name,value)
    return plan.run_phases({name:lambda name=name:invoke(name)for name in plan.PHASES},restore,preserver,record)

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
        qualification_host.authorize_native(qualification_host.source_gate())
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
        report["route_cycle"]=run_route_cycle(report,runner,preserve_after_supervisor_stop)
        report["saved_diode_routing_result"]=c.decode(c.secure_file(DATA,"saved-diode-routing-result.json").read_bytes())
        report["actual_physical_repair_calls"]=0
        report["actual_route_calls"]=1
        report["actual_reconstruction_calls"]=0
        report["saved_diode_routing_complete"]=True
        report["bounded_cycle_qualified"]=report["saved_diode_routing_result"]["bounded_cycle_qualified"]
        report["native_complete"]=True
    except BaseException as exc:primary=exc;report["error"]=c.error_record("bulk-postdrt-antenna",exc)
    finally:
        stop_supervision(report,sup,beat)
        c.attempt(report,"namespace-owned-output-census",lambda:write("bulk-postdrt-namespace-available-output.json",preserve_available()))
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
        report["status"]="COMPLETE_SAVED_DIODE_ROUTING_ENGINE"if primary is None and not report["terminal_errors"]and report.get("native_complete")else"FAIL_SAVED_DIODE_ROUTING_ENGINE"
        c.finish_record(OUT/"bulk-postdrt-inner-result.json",report,"FAIL_SAVED_DIODE_ROUTING_ENGINE",primary)
    return 0 if report["status"]=="COMPLETE_SAVED_DIODE_ROUTING_ENGINE"else 1
if __name__=="__main__":sys.exit(main())
