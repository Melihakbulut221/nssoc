#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Six original tail phases; observer environment scoped only to detailed_route."""
import os
from pathlib import Path
import signal
import sys
import threading
sys.path.insert(0,"/work/tail-source/scripts")
sys.path.insert(0,"/work/source/scripts")
import mainchip_built_engine_route_tail_contract as c
import cloud_mainchip_original_clock_restoration as old
import cloud_mainchip_two_signal_repair as controller
import mainchip_two_signal_internal_witness as witness
from mainchip_witness_engine_build import fingerprint
WORK=Path("/work")

def execute_tail(execute,read):
    records={}
    for phase in c.PHASES:
        execute(phase,c.command(phase))
        if phase in c.STATUSES:
            row=read(phase)
            c.require(row["status"]==c.STATUSES[phase],"original tail phase failed")
            records[phase]=row
    return records

def observer_result(work,mode):
    directory=work/"out/witness"
    raw=c.decode(c.secure_file(work,"out/writer-raw.json").read_bytes())
    c.require(raw["status"]=="PASS_READ_ONLY_SAVED_WRITER_RAW"
        and raw["routed_odb"]==fingerprint(c.secure_file(work,"out/work/routed-fixed.odb")),"writer ODB binding")
    if mode=="off":
        c.require(not directory.exists(),"off case wrote witness")
        return dict(enabled=False,witness_files=0)
    c.require(directory.is_dir() and not directory.is_symlink(),"witness directory")
    names=[stage+".jsonl" for stage in witness.STAGES]
    c.require(sorted(x.name for x in directory.iterdir())==sorted(names),"exact four witness files")
    data={s:c.secure_file(directory,s+".jsonl").read_bytes() for s in witness.STAGES}
    diagnosis=witness.compare(data)
    after=witness.parse_stage(data["after_writer"],"after_writer")
    expected={name:[[r["opcode"],r["data"]] for r in after["nets"][name]["raw"]] for name in witness.NAMES}
    c.require(raw["raw_pairs"]==expected,"after-writer raw opcodes differ from serialized ODB")
    return dict(enabled=True,writer_raw_join=True,diagnosis=diagnosis,writer_record=raw)

def main():
    out=WORK/"out";native=out/"work";report=dict(schema="built-engine-route-tail-case-v1",
       status="IN_PROGRESS",physical_acceptance=False,timing_accepted=False,full_phy_accepted=False,
       observer_equivalence_qualified=False,terminal_errors=[],commands=[])
    primary=None;sup=None;beat=None;handlers={};oldenv={}
    try:
        c.require(c.method(WORK/"tail-source")["native_tail_authorized"],"tail not authorized")
        c.previous.method(WORK/"source")
        inv=c.decode(c.secure_file(WORK,"frozen-manifest.json").read_bytes())
        report["frozen_input"]=c.frozen_unchanged(WORK,inv)
        report["frozen_input"]["inventory_sha256"]=fingerprint(WORK/"frozen-manifest.json")["sha256"]
        request=c.decode(c.secure_file(WORK,"request.json").read_bytes());mode=request["mode"]
        c.require(mode in c.MODES and request["engine"]==c.ENGINE,"case request")
        report.update(mode=mode,source=request["source"],run_id=request["run_id"],
            engine=c.ENGINE,prefix_source=c.PREFIX_SOURCE,prefix_run=c.PREFIX_RUN)
        c.require(not any(k in os.environ for k in ("GH_TOKEN","GITHUB_TOKEN",c.WITNESS_ENV)),"native environment scope")
        values=dict(GITHUB_ACTIONS="true",GITHUB_RUN_ATTEMPT="1",GITHUB_REPOSITORY=c.REPOSITORY,
          RUNNER_ENVIRONMENT="github-hosted",NSSOC_SIGNAL_CLOCK_SOURCE="/work/routing-inputs/clock/selected",
          NSSOC_SIGNAL_GLOBAL_SOURCE="/work/routing-inputs/global",
          NSSOC_TWO_SIGNAL_FAILED_SOURCE="/work/input-transport/selected",
          NSSOC_TWO_SIGNAL_OUT="/work/out/work",PYTHONPATH="/work/tail-source/scripts:/work/source/scripts")
        for k in (*values,"NSSOC_TWO_SIGNAL_PHASE",c.WITNESS_ENV):oldenv[k]=os.environ.get(k)
        os.environ.update(values)
        (out/"supervision").mkdir()
        if mode=="on":(out/"witness").mkdir()
        sup=old.supervisor();sup.OUT=out;sup.TRACE=out/"supervision"
        c.require(sup.SECONDS==1200 and sup.MAX_GROUP_RSS_KIB==c.LIMITS["max_group_rss_kib"]
            and sup.MIN_AVAILABLE_KIB==c.LIMITS["min_available_kib"],"original resource guard")
        for sig in (signal.SIGINT,signal.SIGTERM):handlers[sig]=signal.signal(sig,sup.interrupted)
        beat=threading.Thread(target=sup.heartbeat,daemon=True);beat.start()
        def execute(phase,argv):
            os.environ.pop(c.WITNESS_ENV,None)
            if phase in c.STATUSES:os.environ["NSSOC_TWO_SIGNAL_PHASE"]=phase
            else:os.environ.pop("NSSOC_TWO_SIGNAL_PHASE",None)
            if phase==c.PHASES[0] and mode=="on":
                os.environ[c.WITNESS_ENV]="/work/out/witness"
            try:
                report["commands"].append(controller.execute_command(sup,argv,phase))
            finally:
                os.environ.pop(c.WITNESS_ENV,None)
            if phase==c.PHASES[0]:
                report["route_log"]=controller.qualified.s.route_log(
                    c.secure_file(out,"supervision/one-two-signal-routing-attempt.stdout").read_bytes())
            c.atomic_record(out/"tail-progress.json",report)
        records=execute_tail(execute,lambda phase:c.decode(c.secure_file(native,phase+"-result.json").read_bytes()))
        report["phase_results"]=records
        report["original_audits"]=c.complete(records)
        report["complete_drc"]=records["drc-audit"]["final_DRT"]
        report["geometry_files"]={p:fingerprint(c.secure_file(native,p)) for p in c.COMPARE_FILES}
        report["observer"]=observer_result(WORK,mode)
        c.atomic_record(out/"observer-diagnosis.json",report["observer"])
        report["complete_tail"]=True
    except BaseException as exc:
        primary=exc;report["failure"]=c.error_record("actual-tail",exc)
    finally:
        if sup is not None:
            c.attempt(report,"owned-native-process-cleanup",lambda:sup.stop_process(sup.ACTIVE))
            c.attempt(report,"heartbeat-stop",lambda:sup.STOP.set())
            def join():
                if beat is not None:
                    beat.join(timeout=5);c.require(not beat.is_alive(),"heartbeat remained live")
            c.attempt(report,"heartbeat-join",join)
        for sig,previous in handlers.items():
            c.attempt(report,"restore-signal-"+str(sig),lambda sig=sig,previous=previous:signal.signal(sig,previous))
        for k,v in oldenv.items():
            if v is None:os.environ.pop(k,None)
            else:os.environ[k]=v
        c.attempt(report,"tail-source-terminal",lambda:c.method(WORK/"tail-source"))
        c.attempt(report,"frozen-input-terminal",lambda:c.frozen_unchanged(WORK,
            c.decode(c.secure_file(WORK,"frozen-manifest.json").read_bytes())))
        report["status"]=("PASS_COMPLETE_ROUTE_TAIL_DIAGNOSTIC"
            if report.get("complete_tail") and primary is None and not report["terminal_errors"]
            else "FAIL_ROUTE_TAIL_DIAGNOSTIC")
        c.finish_record(out/"case-result.json",report,"FAIL_ROUTE_TAIL_DIAGNOSTIC",primary)
    return 0 if report["status"].startswith("PASS_") else 1
if __name__=="__main__":sys.exit(main())
