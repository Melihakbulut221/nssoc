#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Execute four original prefix phases under the qualified process supervisor."""
import json
import os
from pathlib import Path
import signal
import sys
import threading
sys.path.insert(0,"/work/source/scripts")
import mainchip_built_engine_route_prefix_contract as c
import cloud_mainchip_original_clock_restoration as old
import cloud_mainchip_two_signal_repair as controller
import mainchip_two_signal_repair as repair

def execute_prefix(execute,read,actionable):
    results={}
    for phase in c.PHASES:
        execute(phase,c.command(phase,"/work/engine/openroad"))
        if phase!="paired-all-nontarget-fixed-import":
            row=read(phase)
            c.require(row["status"]==c.PASS_STATUSES[phase],"native prefix phase did not pass")
            results[phase]=row
        if phase=="ownership":actionable()
    return results

def main():
    out=Path("/work/out");work=Path(c.CANONICAL_OUT)
    report=dict(schema="built-engine-route-prefix-native-v1",status="IN_PROGRESS",
        native_routing_executed=False,physical_acceptance=False,observer_equivalence_qualified=False,
        terminal_errors=[],commands=[])
    primary=None;sup=None;handlers={};beat=None
    try:
        c.require(c.method(Path("/work/source"))["native_prefix_authorized"] is True,"prefix not authorized")
        c.require(not work.exists(),"prefix workspace already exists");work.mkdir()
        (out/"supervision").mkdir()
        values=dict(GITHUB_ACTIONS="true",GITHUB_RUN_ATTEMPT="1",GITHUB_REPOSITORY=c.REPOSITORY,RUNNER_ENVIRONMENT="github-hosted",
            NSSOC_SIGNAL_CLOCK_SOURCE="/work/routing-inputs/clock/selected",
            NSSOC_SIGNAL_GLOBAL_SOURCE="/work/routing-inputs/global",
            NSSOC_TWO_SIGNAL_FAILED_SOURCE="/work/input-transport/selected",
            NSSOC_TWO_SIGNAL_OUT=c.CANONICAL_OUT,PYTHONPATH="/work/source/scripts")
        c.require(not any(k in os.environ for k in ("GH_TOKEN","GITHUB_TOKEN","NNSOC_DRT_INTERNAL_WITNESS_DIR")),"native environment scope")
        os.environ.update(values)
        sup=old.supervisor();sup.OUT=out;sup.TRACE=out/"supervision"
        c.require(sup.SECONDS==1200 and sup.MAX_GROUP_RSS_KIB==c.LIMITS["max_group_rss_kib"]
                  and sup.MIN_AVAILABLE_KIB==c.LIMITS["min_available_kib"],"original process/resource guards")
        for sig in (signal.SIGINT,signal.SIGTERM):handlers[sig]=signal.signal(sig,sup.interrupted)
        beat=threading.Thread(target=sup.heartbeat,daemon=True);beat.start()
        def execute(phase,argv):
            if phase=="paired-all-nontarget-fixed-import":
                os.environ.pop("NSSOC_TWO_SIGNAL_PHASE",None)
            else:os.environ["NSSOC_TWO_SIGNAL_PHASE"]=phase
            report["commands"].append(controller.execute_command(sup,argv,phase))
            c.atomic_record(out/"prefix-progress.json",report)
        def read(phase):return c.decode((work/(phase+"-result.json")).read_bytes())
        def actionable():repair.require_actionable(c.decode((work/"ownership.json").read_bytes()))
        records=execute_prefix(execute,read,actionable)
        report["prefix"]=c.prefix_complete(records,c.decode((work/"ownership.json").read_bytes()))
        report["phase_results"]=records
        report["complete_shared_prefix"]=True
    except BaseException as exc:
        primary=exc;report["failure"]=c.error_record("actual-shared-prefix",exc)
    finally:
        if sup is not None:
            c.attempt(report,"owned-native-process-cleanup",lambda:sup.stop_process(sup.ACTIVE))
            def heartbeat_stop():
                sup.STOP.set()
                if beat is not None:
                    beat.join(timeout=5)
                    c.require(not beat.is_alive(),"heartbeat remained live")
            c.attempt(report,"heartbeat-stop",heartbeat_stop)
        for sig,previous in handlers.items():c.attempt(report,"restore-signal-"+str(sig),lambda sig=sig,previous=previous:signal.signal(sig,previous))
        c.attempt(report,"protected-source-terminal",lambda:c.method(Path("/work/source")))
        report["status"]=("PASS_ACTUAL_BUILT_ENGINE_SHARED_PREFIX"
            if report.get("complete_shared_prefix") and primary is None and not report["terminal_errors"]
            else "FAIL_ACTUAL_BUILT_ENGINE_SHARED_PREFIX")
        c.finish_record(out/"native-prefix-result.json",report,"FAIL_ACTUAL_BUILT_ENGINE_SHARED_PREFIX",primary)
    return 0 if report["status"].startswith("PASS_")else 1
if __name__=="__main__":sys.exit(main())
