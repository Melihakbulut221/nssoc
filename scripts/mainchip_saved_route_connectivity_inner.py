#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Pinned original ELF/runtime, unchanged native phase supervision, read-only ODB."""
import json,os,signal,sys,threading,time
from pathlib import Path
sys.path.insert(0,"/work/tail-source/scripts")
import mainchip_fixed_engine_route_tail_contract as c
import mainchip_bulk_postdrt_antenna_inner as base
import mainchip_exit_checked_supervision as supervision
from mainchip_witness_engine_build import fingerprint
from cloud_mainchip_saved_route_connectivity import source_guard,FLAGS
OUT=Path("/work/out")
ENGINE=Path("/work/engine/openroad")
def main():
    result=dict(status="IN_PROGRESS",commands=[],terminal_errors=[],**FLAGS)
    primary=None;sup=None;beat=None;handlers={}
    def usage():
        root=Path("/sys/fs/cgroup")
        return {n:(root/n).read_text().strip()for n in("memory.max","memory.swap.max","memory.events","memory.peak","cpu.max","pids.max")}
    def check_usage(v):
        c.require(v["memory.max"]==str(c.MEMORY)and v["memory.swap.max"]=="0"and v["pids.max"]==str(c.PIDS),"same native resource limits")
        q,p=v["cpu.max"].split();c.require(q!="max"and int(q)==2*int(p),"same2CPUlimit")
    def runtime():
        paths=set()
        for line in (OUT/"connectivity-ldd.stdout").read_text().splitlines():
            c.require("not found"not in line,"missing runtime library")
            paths.update(t for t in line.split()if t.startswith("/")and Path(t).is_file())
        observed={p:fingerprint(Path(p))for p in sorted(paths)}
        return c.runtime_match(c.decode(Path("/work/runtime-dependencies.json").read_bytes()),observed)
    try:
        c.require(not any(k in os.environ for k in("GH_TOKEN","GITHUB_TOKEN")),"credential-free")
        source_guard(Path("/work/tail-source"));c.method(Path("/work/tail-source"))
        c.require(fingerprint(ENGINE)==c.ENGINE,"original ELF")
        result["cgroup_initial"]=usage();check_usage(result["cgroup_initial"])
        base.run(result,"connectivity-version",[str(ENGINE),"-version"],30)
        base.run(result,"connectivity-ldd",["ldd",str(ENGINE)],30)
        result["runtime_before"]=runtime()
        sup=supervision.supervisor();sup.OUT=OUT/"connectivity-supervisor";sup.TRACE=OUT/"connectivity-supervision"
        sup.OUT.mkdir();sup.TRACE.mkdir()
        c.require(sup.SECONDS==1200 and sup.MAX_GROUP_RSS_KIB==10485760 and sup.MIN_AVAILABLE_KIB==2097152,"original native supervisor")
        for sig in(signal.SIGINT,signal.SIGTERM):handlers[sig]=signal.signal(sig,sup.interrupted)
        beat=threading.Thread(target=sup.heartbeat,daemon=True);beat.start()
        base.supervised_run(result,"complete608-connectivity",[str(ENGINE),"-no_init","-exit","-python",
          "/work/tail-source/scripts/mainchip_saved_route_connectivity_native.py"],1200,sup,cwd=OUT)
        actual=c.decode((OUT/"connectivity/result.json").read_bytes())
        c.require(actual["status"]=="COMPLETE_NATIVE_DIODE_CONNECTIVITY_OBSERVATION"and
          actual["all608_observed"]is True and actual["source_and_input_unchanged"]is True,"complete actual native observation")
        result["native_summary"]={k:v for k,v in actual.items()if k not in("records","errors")}
        result["native_complete"]=True
    except BaseException as exc:primary=exc;result["error"]=c.error_record("native-connectivity",exc)
    finally:
        base.stop_supervision(result,sup,beat)
        for sig,handler in handlers.items():
            c.attempt(result,"restore-signal-"+str(sig),lambda sig=sig,handler=handler:signal.signal(sig,handler))
        c.attempt(result,"ELF-unchanged",lambda:c.require(fingerprint(ENGINE)==c.ENGINE,"ELF changed"))
        c.attempt(result,"source-unchanged",lambda:source_guard(Path("/work/tail-source")))
        if (OUT/"connectivity-ldd.stdout").is_file():c.attempt(result,"runtime-after",lambda:result.update(runtime_after=runtime()))
        def final_usage():
            v=usage();check_usage(v);result["cgroup_terminal"]=v
            first=dict(x.split()for x in result["cgroup_initial"]["memory.events"].splitlines())
            last=dict(x.split()for x in v["memory.events"].splitlines())
            c.require(all(first.get(k,"0")==last.get(k,"0")for k in("oom","oom_kill","oom_group_kill")),"no OOM")
        if "cgroup_initial"in result:c.attempt(result,"cgroup-terminal",final_usage)
        result["status"]="COMPLETE_SAVED_ROUTE_CONNECTIVITY_ENGINE"if primary is None and not result["terminal_errors"]and result.get("native_complete")else"FAIL_SAVED_ROUTE_CONNECTIVITY_ENGINE"
        c.finish_record(OUT/"connectivity-inner-result.json",result,"FAIL_SAVED_ROUTE_CONNECTIVITY_ENGINE",primary)
    return 0 if result["status"]=="COMPLETE_SAVED_ROUTE_CONNECTIVITY_ENGINE"else 1
if __name__=="__main__":sys.exit(main())
