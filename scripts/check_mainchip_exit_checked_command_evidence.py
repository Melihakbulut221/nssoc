#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted-only command-record qualification; native process/proc/clock I/O stays synthetic."""
import argparse,copy,hashlib,json,os,sys,tempfile,traceback
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
import mainchip_exit_checked_command_evidence as evidence

ROOT=Path(__file__).resolve().parents[1]
PRODUCER={
 "scripts/mainchip_exit_checked_supervision.py":"1907842d5eb506102a7d7cf9562fcf330e45d9a36e3cffad6658e9c1450b54b5",
 "scripts/check_mainchip_exit_checked_supervision.py":"91b024d2a8be8bba40ee7e97392a7e4d9bddc2047dee9c42f0fa11c8e60f4001"}

def require(value,reason):
    if not value:raise AssertionError(reason)

def capture(fixture,name,known_child=False,**kwargs):
    """Retain the existing fixture's owned TemporaryDirectory until its real records are read."""
    actual_directory=tempfile.TemporaryDirectory;held=[];clock_holder={}
    actual_process=fixture.Process
    class Retained:
        def __init__(self,*a,**k):
            self.owned=actual_directory(*a,**k);held.append(self.owned)
        def __enter__(self):return self.owned.__enter__()
        def __exit__(self,*args):return False
    def process(clock,*args):
        clock_holder["clock"]=clock
        return actual_process(clock,*args)
    class ExitingKnownChild:
        def __eq__(self,other):
            return other=="live_child"and clock_holder["clock"].value<.095
    try:
        with ExitStack()as stack:
            stack.enter_context(patch.object(fixture.tempfile,"TemporaryDirectory",Retained))
            if known_child:
                stack.enter_context(patch.object(fixture,"Process",side_effect=process))
                kwargs["fault"]=ExitingKnownChild()
            result=fixture.synthetic_case(name,**kwargs)
        matches=[Path(d.name)for d in held if (Path(d.name)/(name+".command.json")).is_file()]
        require(len(matches)==1,"one actual producer command record")
        root=matches[0];raw=(root/(name+".command.json")).read_bytes()
        record=json.loads(raw);events_raw=(root/"events.jsonl").read_bytes()
        events=[json.loads(line)for line in events_raw.splitlines()]
        rows=[x for x in events if x["event"]=="memory_terminal_resolution"]
        if record.get("memory_terminal_resolution")is not None:
            require(len(rows)==1 and rows[0]["resolution"]==record["memory_terminal_resolution"]
              and rows[0]["memory_read_error"]==record["memory_read_error"],"actual event/command diagnostic equality")
        else:require(not rows,"ordinary command has no resolution event")
        return record,{"fixture_result":result,"command_sha256":hashlib.sha256(raw).hexdigest(),
          "events_sha256":hashlib.sha256(events_raw).hexdigest(),"actual_supervised_and_snapshot":True,
          "only_process_proc_clock_io_synthetic":True,"production_functions_modified":False,
          "known_child_exits_within_original_deadline":known_child}
    finally:
        for directory in held:directory.cleanup()

def reject(name,record,seconds,reason=None):
    before=json.dumps(record,sort_keys=True)
    try:evidence.validate(record,seconds)
    except (ValueError,KeyError,TypeError)as error:
        require(before==json.dumps(record,sort_keys=True),"validator changed rejected input")
        if reason is not None:require(reason in str(error),(name,reason,repr(error)))
        frames=[];tb=error.__traceback__
        while tb is not None:
            frames.append((tb.tb_frame.f_code.co_name,tb.tb_frame.f_code.co_filename));tb=tb.tb_next
        require(("validate",evidence.__file__)in frames,"actual validator rejection frame")
        return {"name":name,"error":repr(error),"input_unchanged":True}
    raise AssertionError("Accepted tampered command: "+name)

def controls():
    for name,digest in PRODUCER.items():
        path=ROOT/name
        require(path.is_file()and not path.is_symlink()and hashlib.sha256(path.read_bytes()).hexdigest()==digest,
          "actual producer/checker source")
    import check_mainchip_exit_checked_supervision as fixture
    require(Path(fixture.__file__).resolve()==ROOT/"scripts/check_mainchip_exit_checked_supervision.py",
      "fixture import origin")
    require(Path(fixture.candidate.__file__).resolve()==ROOT/"scripts/mainchip_exit_checked_supervision.py",
      "producer import origin")
    source=fixture.candidate.source_guard()
    positives=[];records={};producer_records=[]
    cases=[
      ("ordinary-quick",1200,{"exit_at":0}),
      ("ordinary-fresh",1200,{"exit_at":.1,"fault":"prior_fresh"}),
      ("resolved-phase",1200,{}),
      ("resolved-route",14400,{"seconds":14400}),
      ("resolved-final-poll",1200,{"exit_at":.1}),
      ("resolved-prior-sample",1200,{"exit_at":.59,"fault":"prior_fresh"}),
      ("resolved-known-live-child",1200,{"known_child":True})]
    for name,seconds,kwargs in cases:
        record,proof=capture(fixture,name,**kwargs);before=json.dumps(record,sort_keys=True)
        checked=evidence.validate(record,seconds)
        require(before==json.dumps(record,sort_keys=True),"validator changed accepted record")
        require(checked["physical_acceptance"]is False and checked["source_authenticated"]is False
          and checked["event_authenticated"]is False and checked["requested_timeout_recorded"]is False,
          "raw record scope and caller responsibilities")
        if name=="resolved-known-live-child":
            polls=record["memory_terminal_resolution"]["polls"]
            require(any(p.get("census",{}).get("complete")is False and
              p["census"]["scans"][-1]["live"]for p in polls),"real intermediate known-live census")
        records[name]=record;producer_records.append({"name":name,**proof})
        positives.append({"name":name,"qualification":checked,"actual_producer_record":True})
    for label,seconds in (("resolved-phase",1200),("resolved-route",14400)):
        record=copy.deepcopy(records[label]);record["requested_timeout_seconds"]=seconds
        result=evidence.validate(record,seconds)
        require(result["requested_timeout_recorded"]and result["requested_timeout_bound"],"declared timeout join")
        positives.append({"name":label+"-declared","qualification":result,
          "only_synthetic_controller_enrichment":"requested_timeout_seconds"})
    baseline=records["resolved-phase"];ordinary=records["ordinary-quick"];mutations=[]
    def change(name,edit,base=baseline,seconds=1200):
        record=copy.deepcopy(base);before=json.dumps(record,sort_keys=True);edit(record)
        require(before!=json.dumps(record,sort_keys=True),"mutation changed no field: "+name)
        mutations.append(reject(name,record,seconds))
    faults=[
      ("nonzero_rc",lambda r:r.update(returncode=7)),
      ("cleanup_rc_zero_failure",lambda r:r.update(supervision_failure="memory_sample_unavailable")),
      ("changed_minimum",lambda r:r.update(minimum_available_kib=1)),
      ("changed_maximum",lambda r:r.update(maximum_group_rss_kib=999999999)),
      ("bool_pid",lambda r:r.update(pid=True)),
      ("nonfinite_total_elapsed",lambda r:r.update(elapsed_seconds=float("nan"))),
      ("declared_wrong_budget",lambda r:r.update(requested_timeout_seconds=14400)),
      ("cleanup_signal",lambda r:r["process_group_cleanup"]["signals"].append("SIGTERM")),
      ("cleanup_live",lambda r:r["process_group_cleanup"]["remaining_live"].append({"pid":r["pid"],"state":"R"})),
      ("cleanup_nonrunning_false",lambda r:r["process_group_cleanup"]["remaining_nonrunning"].append({"pid":r["pid"],"state":"R"})),
      ("wrong_error_type",lambda r:r.update(memory_read_error="CounterError('Persistent unavailable live VmRSS')")),
      ("missing_resolution",lambda r:r.update(memory_terminal_resolution=None)),
      ("unresolved",lambda r:r["memory_terminal_resolution"].update(outcome="rejected")),
      ("retained_resolution_error",lambda r:r["memory_terminal_resolution"].update(resolution_error="not resolved")),
      ("old_error_changed",lambda r:r["memory_terminal_resolution"].update(original_error="")),
      ("typed_error_changed",lambda r:r["memory_terminal_resolution"].update(original_memory_error="")),
      ("fake_fresh_RSS",lambda r:r["memory_terminal_resolution"].update(fresh_memory_sample=True)),
      ("PF_EXITING_waiver",lambda r:r["memory_terminal_resolution"].update(PF_EXITING_used_for_acceptance=True)),
      ("cleanup_started",lambda r:r["memory_terminal_resolution"].update(cleanup_started=True)),
      ("late_completion",lambda r:r["memory_terminal_resolution"].update(completed_before_cleanup=False)),
      ("resolved_nonzero_parent",lambda r:r["memory_terminal_resolution"].update(parent_returncode=7)),
      ("changed_resolution_limit",lambda r:r["memory_terminal_resolution"].update(maximum_group_rss_kib=999999999)),
      ("two_attempts",lambda r:r["memory_terminal_resolution"]["attempts"].pop()),
      ("attempt_order",lambda r:r["memory_terminal_resolution"]["attempts"][1].update(attempt=1)),
      ("attempt_not_missing",lambda r:r["memory_terminal_resolution"]["attempts"][0].update(disposition="fresh_complete")),
      ("enumeration_disappearance",lambda r:r["memory_terminal_resolution"]["attempts"][0]["enumeration_disappearances"].append({"pid":999})),
      ("low_available",lambda r:r["memory_terminal_resolution"]["attempts"][0].update(available_kib=1)),
      ("bool_available",lambda r:r["memory_terminal_resolution"]["attempts"][0].update(available_kib=True)),
      ("missing_enumerated",lambda r:r["memory_terminal_resolution"]["attempts"][0].update(enumerated=[])),
      ("wrong_group",lambda r:r["memory_terminal_resolution"]["attempts"][0]["enumerated"][0].update(pgrp=999)),
      ("reused_PID",lambda r:r["memory_terminal_resolution"]["attempts"][1]["enumerated"][0].update(starttime=1)),
      ("held_PID_reuse",lambda r:r["memory_terminal_resolution"]["attempts"][0]["observations"][0]["after"].update(starttime=1)),
      ("status_hash_changed_shape",lambda r:r["memory_terminal_resolution"]["attempts"][0]["observations"][0].update(status_sha256="bad")),
      ("missing_has_RSS",lambda r:r["memory_terminal_resolution"]["attempts"][0]["observations"][0].update(rss_kib=0)),
      ("wrong_observed_sum",lambda r:r["memory_terminal_resolution"]["observed_resource_bounds"][0].update(partial_group_rss_lower_bound_kib=1)),
      ("bool_observed_attempt",lambda r:r["memory_terminal_resolution"]["observed_resource_bounds"][0].update(attempt=True)),
      ("unvalidated_observed_bounds",lambda r:r["memory_terminal_resolution"].update(observed_resource_bounds_validated=False)),
      ("extended_snapshot",lambda r:r["memory_terminal_resolution"].update(snapshot_deadline=1.1)),
      ("late_snapshot_finish",lambda r:r["memory_terminal_resolution"].update(finished_at=.101)),
      ("nonfinite_snapshot",lambda r:r["memory_terminal_resolution"].update(snapshot_began=float("inf"))),
      ("changed_snapshot_elapsed",lambda r:r["memory_terminal_resolution"].update(elapsed_from_snapshot_start_seconds=0)),
      ("empty_polls",lambda r:r["memory_terminal_resolution"].update(polls=[])),
      ("final_parent_live",lambda r:r["memory_terminal_resolution"]["polls"][-1].update(parent_returncode=None)),
      ("unknown_final_identity",lambda r:r["memory_terminal_resolution"]["polls"][-1]["census"]["scans"][0]["unknown"].append({"pid":999})),
      ("live_final_identity",lambda r:r["memory_terminal_resolution"]["polls"][-1]["census"]["scans"][0]["live"].append(r["pid"])),
      ("missing_known_coverage",lambda r:r["memory_terminal_resolution"]["polls"][-1]["census"]["scans"][0].update(known_gone=[])),
      ("one_scan",lambda r:r["memory_terminal_resolution"]["polls"][-1]["census"]["scans"].pop()),
      ("incomplete_final_census",lambda r:r["memory_terminal_resolution"]["polls"][-1]["census"].update(complete=False)),
      ("missing_budget",lambda r:r["memory_terminal_resolution"].pop("command_budget_decision")),
      ("unavailable_budget",lambda r:r["memory_terminal_resolution"]["command_budget_decision"].update(status="unavailable")),
      ("wrong_clock",lambda r:r["memory_terminal_resolution"]["command_budget_decision"].update(clock="time.time")),
      ("late_budget",lambda r:r["memory_terminal_resolution"]["command_budget_decision"].update(within_limit=False)),
      ("wrong_phase_budget",lambda r:r["memory_terminal_resolution"]["command_budget_decision"].update(limit_seconds=14400)),
      ("nonfinite_budget",lambda r:r["memory_terminal_resolution"]["command_budget_decision"].update(observed_at=float("nan"))),
      ("false_budget_arithmetic",lambda r:r["memory_terminal_resolution"]["command_budget_decision"].update(elapsed_seconds=0)),
      ("budget_before_snapshot_finish",lambda r:r["memory_terminal_resolution"]["command_budget_decision"].update(observed_at=0)),
      ("record_before_budget",lambda r:r.update(elapsed_seconds=0))]
    for name,edit in faults:change(name,edit)
    change("ordinary_with_resolution",lambda r:r.update(memory_terminal_resolution={}),ordinary)
    change("last_sample_over_limit",lambda r:r["last_memory_sentinel_sample"].update(group_rss_kib=10485761),
      records["ordinary-fresh"])
    change("last_sample_low_available",lambda r:r["last_memory_sentinel_sample"].update(available_kib=1),
      records["resolved-prior-sample"])
    child=records["resolved-known-live-child"]
    def corrupt_child(r):
        poll=next(p for p in r["memory_terminal_resolution"]["polls"]if p.get("census",{}).get("complete")is False)
        poll["census"]["scans"][0]["group"][0]["after"]["starttime"]+=1
    change("intermediate_child_reuse",corrupt_child,child)
    def unknown_child(r):
        poll=next(p for p in r["memory_terminal_resolution"]["polls"]if p.get("census",{}).get("complete")is False)
        poll["census"]["scans"][0]["unknown"].append({"pid":999,"reason":"unanchored group identity"})
    change("intermediate_unknown_identity",unknown_child,child)
    def partial_rss(r):
        for a in r["memory_terminal_resolution"]["attempts"]:
            old=a["enumerated"][0];p=copy.deepcopy(old);p["pid"]-=1;p["starttime"]-=1
            observed={"expected":p,"before":copy.deepcopy(p),"after":copy.deepcopy(p),
              "status_sha256":"0"*64,"disposition":"measured_fresh","rss_kib":10485761}
            a["enumerated"].insert(0,p);a["observations"].insert(0,observed)
    change("observed_partial_RSS_over_limit",partial_rss)
    for limit in (1200,14400):
        for offset in (0,.01):
            late=copy.deepcopy(records["resolved-route"if limit==14400 else"resolved-phase"])
            budget=late["memory_terminal_resolution"]["command_budget_decision"]
            budget.update(observed_at=limit+offset,elapsed_seconds=limit+offset)
            late["elapsed_seconds"]=limit+offset
            mutations.append(reject("strict_deadline_"+str(limit)+"_"+str(offset),late,limit))
    for bad in (0,1201,True):
        mutations.append(reject("unsupported_budget_"+str(bad),copy.deepcopy(baseline),bad))
    regressions=[]
    for name,kwargs,reason in (
      ("original-third-attempt",{"old":True,"expected_reason":"memory_sample_unavailable"},"successful original command"),
      ("actual-pre-fix-deadline-bypass",{"seconds":1200,"start_delay":1199.94,"exit_at":1200.01,"pre_fix":True},
       "strict command deadline proof missing")):
        record,proof=capture(fixture,name,**kwargs)
        regressions.append({**reject(name,record,1200,reason),"producer":proof})
    require(len(positives)==9 and len(mutations)==70 and len(producer_records)==7 and len(regressions)==2,"authored source control count")
    return {"status":"PASS_EXIT_CHECKED_COMMAND_EVIDENCE_SOURCE_CONTROLS","positive":len(positives),
      "refusal":len(mutations),"actual_old_regressions":len(regressions),
      "positives":positives,"refusals":mutations,"regressions":regressions,"producer_records":producer_records,
      "producer_sources":PRODUCER,"frozen_source_guards":source,
      "actual_supervised_record_cases":len(producer_records)+len(regressions),
      "source_controls_only":True,"synthetic_process_proc_clock_io":True,"native_executed":False,
      "physical_acceptance":False,"full_phy_accepted":False}

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",required=True,type=Path);args=parser.parse_args()
    primary=None
    try:
        require(os.environ.get("GITHUB_ACTIONS")=="true"and os.environ.get("RUNNER_ENVIRONMENT")=="github-hosted"
          and os.environ.get("GITHUB_REPOSITORY")=="Melihakbulut221/nssoc"
          and os.environ.get("GITHUB_EVENT_NAME")=="workflow_dispatch"and os.environ.get("GITHUB_RUN_ATTEMPT")=="1",
          "hosted source-only controls")
        result=controls()
        result["current_context"]={"source":os.environ["GITHUB_SHA"],"run_id":int(os.environ["GITHUB_RUN_ID"]),
          "attempt":1,"source_controls_only":True,"native_executed":False}
    except BaseException as error:
        primary=error;result={"status":"FAIL_EXIT_CHECKED_COMMAND_EVIDENCE_SOURCE_CONTROLS",
          "error":repr(error),"traceback":traceback.format_exc(),"native_executed":False}
    try:
        raw=json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n"
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(raw);print(raw,end="")
    except BaseException:
        if primary is None:raise
        try:print(json.dumps(result,sort_keys=True,allow_nan=False),flush=True)
        except BaseException:pass
    if primary is not None:raise primary

if __name__=="__main__":main()
