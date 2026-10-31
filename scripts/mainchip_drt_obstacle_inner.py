#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""One owned read-only OpenDB observation with unchanged exit-checked supervision."""
import json,os,signal,sys,threading,time
from pathlib import Path
sys.path.insert(0,"/work/tail-source/scripts")
import mainchip_drt_obstacle_contract as k
import mainchip_fixed_engine_route_tail_contract as c
import mainchip_bulk_postdrt_antenna_inner as original
from mainchip_witness_engine_build import fingerprint
OUT=Path("/work/out");INPUTS=Path("/work/obstacle-inputs")
SCRIPT="/work/tail-source/scripts/mainchip_drt_obstacle_native.py"
ENGINE="/work/engine/openroad"
def usage():
    root=Path("/sys/fs/cgroup")
    return {n:(root/n).read_text().strip()for n in("memory.max","memory.swap.max","memory.current","memory.stat","memory.events","memory.peak","cpu.max","pids.max")}
def check_usage(value):
    k.q.require(value["memory.max"]==str(c.MEMORY)and value["memory.swap.max"]=="0"and value["pids.max"]==str(c.PIDS),"unchanged resource limits")
    quota,period=value["cpu.max"].split();k.q.require(quota!="max"and int(quota)==2*int(period),"unchanged CPU quota")
def runtime():
    paths=set()
    for line in(OUT/"obstacle-ldd.stdout").read_text().splitlines():
        k.q.require("not found"not in line,"runtime dependency absent")
        for token in line.split():
            if token.startswith("/")and Path(token).is_file():paths.add(token)
    observed={path:fingerprint(Path(path))for path in sorted(paths)}
    c.atomic_record(OUT/"obstacle-runtime-observed.json",observed)
    return c.runtime_match(c.decode(Path("/work/runtime-dependencies.json").read_bytes()),observed)
def main():
    report=dict(status="IN_PROGRESS",commands=[],terminal_errors=[],**k.FLAGS)
    sup=None;beat=None;handlers={};primary=None;started=time.monotonic();config=None
    try:
        k.native_authorization()
        k.q.require(not any(n in os.environ for n in("GH_TOKEN","GITHUB_TOKEN")),"credential-free native container")
        request=k.q.decode(Path("/work/obstacle-request.json").read_bytes())
        context=k.context(os.environ,request["source"])
        k.q.require(context==request["context"]and request["read_only"]is True,"actual source request")
        config=k.q.decode(Path("/work/tail-source/scripts/mainchip-drt-obstacle-readback-inputs.json").read_bytes())
        k.validate_config(config)
        report["context"]=context;report["cgroup_initial"]=usage();check_usage(report["cgroup_initial"])
        k.q.require(fingerprint(Path(ENGINE))==c.ENGINE,"exact frozen native ELF")
        for name,pin in config["selected_members"].items():k.q.require(fingerprint(INPUTS/name)==pin,"native selected input "+name)
        k.q.require(fingerprint(INPUTS/"hosted-analysis.json")==config["analysis_result"]["pin"],"qualified analysis bytes")
        original.run(report,"obstacle-version",[ENGINE,"-version"],30)
        original.run(report,"obstacle-ldd",["ldd",ENGINE],30)
        report["runtime_before"]=runtime()
        sup=original.supervision.supervisor();sup.OUT=OUT/"obstacle-supervisor";sup.TRACE=OUT/"obstacle-supervision"
        sup.OUT.mkdir();sup.TRACE.mkdir()
        k.q.require((sup.SECONDS,sup.MIN_AVAILABLE_KIB,sup.MAX_GROUP_RSS_KIB)==(1200,2097152,10485760),"unchanged phase memory/deadline guards")
        for sig in(signal.SIGINT,signal.SIGTERM):handlers[sig]=signal.signal(sig,sup.interrupted)
        beat=threading.Thread(target=sup.heartbeat,daemon=True);beat.start()
        argv=[ENGINE,"-no_init","-exit","-python",SCRIPT]
        original.supervised_run(report,"obstacle-endpoint-observation",argv,1200,sup,cwd=INPUTS)
        native=k.q.decode((OUT/"obstacle-native/result.json").read_bytes())
        k.q.require(native["status"]=="COMPLETE_PREROUTE_ENDPOINT_OBSTACLE_OBSERVATION"and native["terminal_errors"]==[]
          and native["input_odb_unchanged"]is True and native["read_only"]is True,"complete read-only native observation")
        k.q.require(native["complete_selected_marker_count"]==434 and native["all_net_count"]==143820
          and native["all_instance_count"]==154480 and native["actual_added_diode_A_connections"]==1351,"complete current native census")
        k.q.require(all(native[n]is False for n in k.FLAGS),"native observation cannot accept physical cause/timing")
        k.q.require([r["label"]for r in report["commands"]]==["obstacle-version","obstacle-ldd","obstacle-endpoint-observation"],"exact read-only command set")
        report["native_complete"]=True
    except BaseException as exc:primary=exc;report["error"]=c.error_record("obstacle-observation",exc)
    finally:
        original.stop_supervision(report,sup,beat)
        for sig,previous in handlers.items():c.attempt(report,"restore-signal-"+str(sig),lambda sig=sig,previous=previous:signal.signal(sig,previous))
        c.attempt(report,"engine-unchanged",lambda:k.q.require(fingerprint(Path(ENGINE))==c.ENGINE,"ELF changed"))
        c.attempt(report,"source-unchanged",k.source_gate)
        if config is not None:
            for name,pin in config["selected_members"].items():
                c.attempt(report,"input-unchanged:"+name,lambda name=name,pin=pin:k.q.require(fingerprint(INPUTS/name)==pin,"selected input changed"))
            c.attempt(report,"analysis-unchanged",lambda:k.q.require(fingerprint(INPUTS/"hosted-analysis.json")==config["analysis_result"]["pin"],"analysis input changed"))
        if(OUT/"obstacle-ldd.stdout").is_file():c.attempt(report,"runtime-after",lambda:report.update(runtime_after=runtime()))
        def final_usage():
            last=usage();report["cgroup_terminal"]=last;check_usage(last)
            first=dict(x.split()for x in report["cgroup_initial"]["memory.events"].splitlines())
            current=dict(x.split()for x in last["memory.events"].splitlines())
            k.q.require(all(first.get(n,"0")==current.get(n,"0")for n in("oom","oom_kill","oom_group_kill")),"no OOM event")
        if"cgroup_initial"in report:c.attempt(report,"terminal-cgroup",final_usage)
        report["elapsed_seconds"]=time.monotonic()-started
        report["status"]="COMPLETE_READONLY_OBSTACLE_ENGINE"if primary is None and not report["terminal_errors"]and report.get("native_complete")else"FAIL_READONLY_OBSTACLE_ENGINE"
        c.finish_record(OUT/"obstacle-inner-result.json",report,"FAIL_READONLY_OBSTACLE_ENGINE",primary)
    return 0 if report["status"]=="COMPLETE_READONLY_OBSTACLE_ENGINE"else 1
if __name__=="__main__":sys.exit(main())
