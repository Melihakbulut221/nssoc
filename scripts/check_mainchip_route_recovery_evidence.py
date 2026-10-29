#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted source-only qualification of authentic failed-route metadata.

No archive, runtime, restore, routing or network calls. All metadata mutations
are synthetic copies of authenticated complete original records. The original
read-only helper code runs unchanged; source_guard is cached only after its real
complete positive and real copied-file missing/tampered controls.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from unittest.mock import patch
import mainchip_route_recovery_evidence as e

JOBS_PATH="docs/evidence/mainchip-route-recovery-original-complete-jobs-20261029.json"
JOBS_BYTES=14176
JOBS_SHA="5fc8fefdf83148919ed9efb92e10edde8b1e411040890aa22549ca098b384085"
MODULE_SHA="f28a7356221788738d2a4520bc67e2654faf1d31ba08ecdb072c226afb48a802"
NEW_SOURCE="0123456789abcdef0123456789abcdef01234567"
NEW_RUN=40808800490


def demand(ok,reason):
    if not ok:raise AssertionError(reason)


def reject(name,call,reason,frame,rows,kind=AssertionError):
    try:call()
    except Exception as exc:
        frames=[];tb=exc.__traceback__
        while tb:
            frames.append(tb.tb_frame.f_code);tb=tb.tb_next
        demand(type(exc)is kind and exc.args==(reason,),
          (name,"wrong refusal",type(exc).__name__,repr(exc.args),reason))
        demand(frame in frames,(name,"did not reach actual production function"))
        rows.append(dict(name=name,error_type=kind.__name__,reason=reason,
          actual_function=frame.co_name))
    else:raise AssertionError((name,"mutation was accepted"))


def setpath(row,path,value):
    for key in path[:-1]:row=row[key]
    row[path[-1]]=value


def guard_controls(original,negative,positive):
    # Real temporary files, only on the hosted runner. Original checkout is read-only.
    names=set(original["old_method"]["protected"])|set(e.REQUIRED_DOCS)|{e.METHOD}
    protected=sorted(original["old_method"]["protected"])[0]
    document=sorted(e.REQUIRED_DOCS)[0]
    with tempfile.TemporaryDirectory(prefix="recovery-source-guard-")as tmp:
        root=Path(tmp)
        for name in sorted(names):
            dest=root/name;dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(e.regular(name),dest)
        with patch.object(e,"ROOT",root):
            clean=e.source_guard()
            demand(e.canonical(clean)==e.canonical(original),"copied source guard differs")
            positive.append(dict(name="complete_copied_source_guard",protected=687,documents=26))
            for label,name,reason in (("method",e.METHOD,"Changed original route method"),
              ("protected",protected,"Changed original protected source: "+protected),
              ("document",document,"Changed preserved failure evidence: "+document)):
                p=root/name;raw=p.read_bytes()
                try:
                    p.write_bytes(raw+b"\nsynthetic tamper\n")
                    reject("tampered_"+label,e.source_guard,reason,e.source_guard.__code__,negative)
                    p.unlink()
                    reject("missing_"+label,e.source_guard,"Nonregular source evidence",
                      e.source_guard.__code__,negative)
                finally:p.write_bytes(raw)


def assert_projection(mode,value):
    case=e.CASES[mode]
    demand(value["mode"]==mode and value["old_context"]==dict(source=e.SOURCE,mode=mode,
      stage="route",run_id=e.RUN,engine=value["original_engine"]),"historical context")
    demand(type(value["old_context"]["run_id"])is int and
      value["old_audit_context"]==dict(value["old_context"],stage="audit"),"typed old audit context")
    demand(value["original_run"]["conclusion"]==value["original_job"]["conclusion"]=="failure"
      and value["original_job"]["failed_step"]==7 and value["original_audits_executed"]is False,
      "borrowed success")
    for key in ("execution_authorized","reroute_authorized","audit_authorized",
      "observer_equivalence_qualified","physical_acceptance","timing_accepted","full_phy_accepted",
      "native_archive_acquired","native_member_bytes_reacquired"):
        demand(value[key]is False,("borrowed authority",key))
    demand(value["new_execution_identity_must_be_separate"]is True and value["metadata_only"]is True,
      "metadata scope")
    demand(len(value["outer_expected_files"])==case["outer_files"] and
      len(value["handoff_inventory"]["files"])==case["handoff_files"] and
      len(value["canonical_projection"])==case["projection_files"] and
      len(value["original_frozen_inventory"]["files"])==746 and
      value["old_method"]["protected_count"]==687,"complete inventory counts")
    demand(len(value["release"]["assets"])==21 and len(value["required_original_audit_phases"])==5,
      "complete retained assets/audits")
    demand(value["old_context"]["source"]!=NEW_SOURCE and value["old_context"]["run_id"]!=NEW_RUN,
      "old/new context collapsed")
    return dict(mode=mode,canonical_sha256=hashlib.sha256(e.canonical(value)).hexdigest(),
      outer_files=len(value["outer_expected_files"]),handoff_files=len(value["handoff_inventory"]["files"]),
      old_source=value["old_context"]["source"],old_run=value["old_context"]["run_id"],
      old_job=value["original_job"]["id"],original_conclusion="failure",execution_authorized=False)


def saved_controls(mode,original,negative):
    c,h=e.helpers()
    source_path=sorted(original["old_method"]["protected"])[0]
    frozen="input-transport/selected/supervision/actual-runtime-version.command.json"
    mutations=[
      ("borrowed_receipt_authority",["receipt.json","native_reroute_authorized_by_this_note"],True,
       "Failure receipt scope changed",AssertionError,e._validate_saved.__code__),
      ("new_source_as_old_host",["host-result.json","source"],NEW_SOURCE,
       "route identity",ValueError,h.route_records.__code__),
      ("new_run_as_old_case",["case-result.json","run_id"],NEW_RUN,
       "route body completion",ValueError,h.route_records.__code__),
      ("incomplete_cleanup",["host-result.json","terminal_actions",0,"completed"],False,
       "Incomplete host cleanup",AssertionError,e.actions.__code__),
      ("new_source_as_old_handoff",["route-handoff-inventory.json","source"],NEW_SOURCE,
       "handoff lineage",ValueError,h.validate_manifest.__code__),
      ("untyped_member_bytes",["route-handoff-inventory.json","files","engine/openroad","bytes"],True,
       "handoff file receipt",ValueError,h.validate_manifest.__code__),
      ("changed_frozen_input",["route-handoff-inventory.json","files",frozen,"sha256"],"0"*64,
       "Original frozen input changed",AssertionError,e._validate_saved.__code__),
      ("changed_frozen_source",["route-handoff-inventory.json","files","tail-source/"+source_path,"sha256"],"0"*64,
       "Frozen687 source/method projection is incomplete or changed",AssertionError,e._validate_saved.__code__),
      ("nested_archive_hash",["route-handoff.json","archive","sha256"],"0"*64,
       "Nested archive/inventory receipt mismatch",AssertionError,e._validate_saved.__code__),
      ("ordered_part_hash",["parts.json","parts",0,"sha256"],"0"*64,
       "route part asset join",ValueError,h.part_manifest.__code__),
    ]
    for label,path,value,reason,kind,frame in mutations:
        changed=copy.deepcopy(original);setpath(changed["cases"][mode],path,value)
        demand(e.canonical(changed)!=e.canonical(original),(label,"no-op"))
        with patch.object(e,"source_guard",return_value=changed):
            reject(mode+"_"+label,lambda:e.validate_saved_case(mode),reason,frame,negative,kind)
    changed=copy.deepcopy(original)
    del changed["cases"][mode]["route-handoff-inventory.json"]["files"]["tail-source/"+source_path]
    with patch.object(e,"source_guard",return_value=changed):
        reject(mode+"_missing_full_member",lambda:e.validate_saved_case(mode),"complete handoff census",
          h.validate_manifest.__code__,negative,ValueError)


def live_controls(mode,original,jobs,negative,positive):
    d=original["cases"][mode]
    baseline=dict(run=d["run-snapshot.json"],jobs=jobs,release=d["release-snapshot.json"],ref=d["tag.json"])
    def call(row):return e.validate_live(mode,**row)
    # First positive traverses the real source_guard and every saved-case join.
    result=call(baseline)
    assert_projection(mode,result["saved_case"])
    demand(result["original_run_conclusion"]==result["original_job_conclusion"]=="failure" and
      result["original_audits_skipped"]is True and result["execution_authorized"]is False,
      "live failure status not retained")
    positive.append(dict(name=mode+"_complete_failed_live_binding",old_job=e.CASES[mode]["job"],
      full_job_count=5,release_id=e.CASES[mode]["release"],original_conclusion="failure"))
    index=next(i for i,j in enumerate(jobs["jobs"])if j["id"]==e.CASES[mode]["job"])
    step=next(i for i,s in enumerate(jobs["jobs"][index]["steps"])if s["number"]==5)
    rows=[
      ("wrong_source",["run","head_sha"],NEW_SOURCE,"Original run must remain terminal failure",e.failed_run),
      ("wrong_run",["run","id"],NEW_RUN,"Original run must remain terminal failure",e.failed_run),
      ("bool_attempt",["run","run_attempt"],True,"Untyped original run identity",e.failed_run),
      ("borrowed_success",["run","conclusion"],"success","Original run must remain terminal failure",e.failed_run),
      ("wrong_job_source",["jobs","jobs",index,"head_sha"],NEW_SOURCE,"Wrong original job source/attempt",e.validate_live),
      ("wrong_route_step",["jobs","jobs",index,"steps",step,"conclusion"],"failure","Original route steps changed",e.failed_route_job),
      ("wrong_asset_hash",["release","assets",0,"digest"],"sha256:"+"0"*64,"Historical retained asset set changed",e.release_binding),
      ("wrong_asset_id",["release","assets",0,"id"],1,"Historical retained asset set changed",e.release_binding),
      ("bool_asset_size",["release","assets",0,"size"],True,"Malformed retained asset identity",e.asset_map),
      ("wrong_tag_source",["ref","object","sha"],NEW_SOURCE,"Wrong historical lightweight source tag",e.release_binding),
    ]
    for label,path,value,reason,frame in rows:
        changed=copy.deepcopy(baseline);setpath(changed,path,value)
        demand(e.canonical(changed)!=e.canonical(baseline),(label,"no-op"))
        with patch.object(e,"source_guard",return_value=original):
            reject(mode+"_live_"+label,lambda:call(changed),reason,frame.__code__,negative)
    for label,key,reason,frame in (
      ("missing_job","jobs","Wrong complete original job set",e.validate_live),
      ("missing_asset","release","Incomplete or duplicate retained release assets",e.asset_map)):
        changed=copy.deepcopy(baseline)
        changed[key]["jobs"if key=="jobs"else"assets"].pop()
        with patch.object(e,"source_guard",return_value=original):
            reject(mode+"_live_"+label,lambda:call(changed),reason,frame.__code__,negative)


def controls():
    positive=[];negative=[]
    demand(e.sha(e.regular("scripts/mainchip_route_recovery_evidence.py"))==MODULE_SHA,
      "changed actual evidence implementation")
    raw=e.regular(JOBS_PATH).read_bytes()
    demand(e.record(raw)==dict(bytes=JOBS_BYTES,sha256=JOBS_SHA),"changed full original jobs fixture")
    jobs=json.loads(raw)
    original=e.source_guard()
    demand(original["historical_method_authorizations_reusable"]is False and
      original["execution_authorized"]is False,"source guard authority")
    positive.append(dict(name="actual_complete_source_guard",protected=687,documents=26))
    guard_controls(original,negative,positive)
    for mode in ("off","on"):
        expected=e.expected_case(mode);saved=e.validate_saved_case(mode)
        demand(e.canonical(expected)==e.canonical(saved),"public metadata APIs differ")
        for name,row in (("expected_case",expected),("validate_saved_case",saved)):
            positive.append(dict(name=mode+"_"+name,**assert_projection(mode,row)))
        saved_controls(mode,original,negative)
        live_controls(mode,original,jobs,negative,positive)
    for value in (True,"compare"):
        reject("invalid_mode_"+repr(value),lambda:e.expected_case(value),"Unknown original route mode",
          e.select.__code__,negative)
    demand(len(positive)==8 and len(negative)==54,"changed control census")
    return dict(schema="mainchip-route-recovery-evidence-controls-v1",
      status="PASS_READ_ONLY_RECOVERY_EVIDENCE_SOURCE_CONTROLS",positive_count=len(positive),
      refusal_count=len(negative),positives=positive,refusals=negative,
      original_source=e.SOURCE,original_run=e.RUN,original_method_sha256=e.METHOD_SHA,
      current_source=os.environ.get("GITHUB_SHA"),current_run=os.environ.get("GITHUB_RUN_ID"),
      current_attempt=os.environ.get("GITHUB_RUN_ATTEMPT"),
      complete_jobs_fixture=dict(path=JOBS_PATH,bytes=JOBS_BYTES,sha256=JOBS_SHA),
      original_job_outcomes="both route jobs failed publication; audits and comparison skipped",
      synthetic_faults=True,actual_original_metadata=True,metadata_only=True,
      archive_acquired=False,runtime_invoked=False,restore_invoked=False,
      reroute_authorized=False,audit_authorized=False,observer_equivalence_qualified=False,
      physical_acceptance=False)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",required=True)
    args=parser.parse_args();path=Path(args.output)
    report=dict(schema="mainchip-route-recovery-evidence-controls-v1",status="RUNNING",
      current_source=os.environ.get("GITHUB_SHA"),current_run=os.environ.get("GITHUB_RUN_ID"))
    try:report=controls()
    except BaseException as exc:
        report.update(status="FAIL",error_type=type(exc).__name__,error=repr(exc));raise
    finally:
        raw=(json.dumps(report,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(raw)
        print(raw.decode(),end="")


if __name__=="__main__":main()
