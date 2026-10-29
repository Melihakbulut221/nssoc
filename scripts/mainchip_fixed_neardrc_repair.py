#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact NEARDRC source repair and read-only authentic audit-case comparison."""
import hashlib,json,os,re
from pathlib import Path
import mainchip_built_engine_route_tail_contract as c
import mainchip_route_audit_recovery_contract as recovery
from ensure_cloud_tested_source_release import validate_release

ROOT=Path(__file__).resolve().parents[1]
METHOD="scripts/mainchip-fixed-neardrc-repair-methods.json"
LEGACY_METHOD="scripts/mainchip-route-audit-recovery-methods.json"
LEGACY_SHA="5bef5d2a2541f9d7f27cfa226f577f2907fed293ae81e8beb21fefb4e4b23fa5"
UPSTREAM="dcf36133a369abc8f3c5e5738cd4d82e4903c0e0"
SNAPSHOT="docs/evidence/mainchip-two-signal-ownership-primary-20261026/src/drt/src/dr/FlexDR_init.cpp"
ORIGINAL_SHA="cf48ce2c745723c9c73a3431938f26eb9b87ee4c663a0ad8b7d6e185eb511723"
PATCHED_SHA="9f3778069d8678fdf733086aa83b37fb746437e883a80ac5a8e94c343d8ffc22"
BEFORE=b'  for (const auto& net : ripUpNets) {\n    for (const auto& fig : net->getRouteConnFigs()) {\n'
AFTER=b'  for (const auto& net : ripUpNets) {\n    if (net->getFrNet()->isFixed()) {\n      continue;\n    }\n    for (const auto& fig : net->getRouteConnFigs()) {\n'
PREFIX="docs/evidence/mainchip-route-audit-recovery-native-terminal-20261029/"
RECEIPT_SHA="3bcfe35ba886f04e2871d2f575b252f5d50fc623b3683a599563e34bc1f1022e"
AUDIT_SOURCE="4c6c705642da5883ae42fbeac539782cfdb94413"
AUDIT_RUN=40821586610
ROUTE_SOURCE="dd2115212b8ccd1176a2e67995d3e54b0a4248dc"
ROUTE_RUN=40808800489
JOB_IDS={"source-controls":123275062656,"audit-only (on)":123275294416,"audit-only (off)":123275294417}
RELEASES={"off":427487104,"on":427487132}
FALSE=("native_engine_build_authorized","native_routing_authorized","native_restore_authorized",
 "native_audit_authorized","physical_acceptance","timing_accepted","full_phy_accepted",
 "runtime_root_cause_established","automatic_retry_authorized")
require=c.require

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def record_bytes(name,raw,expected):
    require(type(expected["bytes"])is int and expected["bytes"]>=0 and
      len(raw)==expected["bytes"]and digest(raw)==expected["sha256"],"changed complete proof: "+name)
    return raw

def source_guard():
    method=json.loads(c.secure_file(ROOT,METHOD).read_bytes())
    require(method["schema"]=="mainchip-fixed-neardrc-source-v1","repair method schema")
    require(type(method["source_controls_authorized"])is bool and
      all(type(method[k])is bool and method[k]is False for k in FALSE),"source-only repair authority")
    legacy_raw=c.secure_file(ROOT,LEGACY_METHOD).read_bytes()
    require(digest(legacy_raw)==LEGACY_SHA,"changed original739 method")
    require(method["protected"].get(LEGACY_METHOD)==LEGACY_SHA,"legacy method not protected")
    legacy=json.loads(legacy_raw)
    require(len(legacy["protected"])==739 and all(method["protected"].get(p)==h
      for p,h in legacy["protected"].items()),"original739 protection changed")
    receipt_raw=c.secure_file(ROOT,PREFIX+"receipt.json").read_bytes()
    require(digest(receipt_raw)==RECEIPT_SHA,"changed complete terminal receipt")
    receipt=json.loads(receipt_raw)
    require(len(receipt["files"])==109,"incomplete terminal proof census")
    for name,entry in receipt["files"].items():
        require(name.startswith(PREFIX)and method["protected"].get(name)==entry["sha256"],
          "terminal proof unprotected")
        record_bytes(name,c.secure_file(ROOT,name).read_bytes(),entry)
    require(method["protected"].get(PREFIX+"receipt.json")==RECEIPT_SHA,"receipt not protected")
    for p,h in method["protected"].items():
        require(type(h)is str and re.fullmatch("[0-9a-f]{64}",h)and
          digest(c.secure_file(ROOT,p).read_bytes())==h,"changed repair source: "+p)
    require(digest(c.secure_file(ROOT,SNAPSHOT).read_bytes())==ORIGINAL_SHA,"upstream snapshot changed")
    return method

def source_context():
    method=source_guard()
    require(method["source_controls_authorized"]is True,"repair source controls disabled")
    require(os.environ.get("GITHUB_ACTIONS")=="true"and os.environ.get("RUNNER_ENVIRONMENT")=="github-hosted"
      and os.environ.get("GITHUB_REPOSITORY")=="Melihakbulut221/nssoc"
      and os.environ.get("GITHUB_EVENT_NAME")=="workflow_dispatch"
      and os.environ.get("GITHUB_RUN_ATTEMPT")=="1","first hosted source-only context required")
    return method

def derive(raw=None):
    if raw is None:raw=c.secure_file(ROOT,SNAPSHOT).read_bytes()
    require(type(raw)is bytes and digest(raw)==ORIGINAL_SHA,"exact original C++ required")
    require(raw.count(BEFORE)==1 and raw.count(AFTER)==0,"unique original repair block required")
    candidate=raw.replace(BEFORE,AFTER)
    require(digest(candidate)==PATCHED_SHA and candidate.count(AFTER)==1 and
      candidate.replace(AFTER,BEFORE)==raw,"single-block byte reversal failed")
    return candidate

def original_function(raw):
    require(digest(raw)in (ORIGINAL_SHA,PATCHED_SHA),"unprotected function source")
    start=b"void FlexDRWorker::initRipUpNetsFromMarkers()\n"
    end=b"void FlexDRWorker::initNets(const frDesign* design)\n"
    require(raw.count(start)==raw.count(end)==1,"unique actual function boundaries")
    a=raw.index(start);b=raw.index(end,a)
    body=raw[a:b]
    require(body.rstrip().endswith(b"}")and body.count(BEFORE)+body.count(AFTER)==1,
      "actual repair function boundary changed")
    return body

def read_saved():
    source_guard()
    names=("host-result.json","case-result.json","inner-result.json","recovery-host-context.json",
      "current-host-request.json","frozen-native-request.json","outputs.json","release.json","tag.json","parts.json")
    value={name:json.loads(c.secure_file(ROOT,PREFIX+name+".json").read_bytes())
      for name in ("receipt","run","jobs")}
    for mode in ("off","on"):
        value[mode]={name:json.loads(c.secure_file(ROOT,PREFIX+mode+"/"+name).read_bytes())for name in names}
    return value

def validate_case_bindings(value):
    run,jobs=value["run"],value["jobs"]
    require((run["id"],run["head_sha"],run["run_attempt"],run["event"],run["status"],run["conclusion"])==
      (AUDIT_RUN,AUDIT_SOURCE,1,"workflow_dispatch","completed","success"),"actual recovered audit run")
    require(run["path"]==".github/workflows/mainchip-route-audit-only-recovery.yml","actual audit workflow")
    require(jobs["total_count"]==3 and len(jobs["jobs"])==3 and
      {j["name"]:j["id"]for j in jobs["jobs"]}==JOB_IDS,"all three actual job identities")
    require(all(j["status"]=="completed"and j["conclusion"]=="success"and
      all(s["conclusion"]=="success"for s in j["steps"])for j in jobs["jobs"]),"actual audit jobs/steps incomplete")
    receipt=value["receipt"]
    require(receipt["source"]==AUDIT_SOURCE and receipt["run"]==AUDIT_RUN and
      receipt["historical_source"]==ROUTE_SOURCE and receipt["historical_run"]==ROUTE_RUN and
      receipt["historical_run_still_failed"]is True and receipt["historical_audit_jobs_still_skipped"]is True,
      "historical failure context changed")
    proofs={}
    for mode in ("off","on"):
        row=value[mode];host=row["host-result.json"];case=row["case-result.json"];inner=row["inner-result.json"]
        ctx=recovery.validate_context(row["recovery-host-context.json"])
        require(ctx["source"]==AUDIT_SOURCE and ctx["run_id"]==AUDIT_RUN and ctx["mode"]==mode,
          "new audit host context changed")
        frozen=dict(source=ROUTE_SOURCE,run_id=ROUTE_RUN,mode=mode,stage="audit",engine=c.ENGINE)
        require(row["frozen-native-request.json"]==frozen and host["frozen_native_context"]==frozen,
          "frozen route context was restamped")
        request=row["current-host-request.json"]
        require(request["host_request"]==dict(frozen,source=AUDIT_SOURCE,run_id=AUDIT_RUN)and
          request["frozen_native_request"]==frozen and request["new_host_context"]==ctx and
          request["audits_requested_as_new_execution"]is True and
          request["original_skipped_audits_succeeded"]is False,"new versus frozen audit request")
        require(host["new_host_context"]==ctx and host["source"]==AUDIT_SOURCE and host["mode"]==mode and
          host["status"]=="PASS_OWNED_AUDIT_STAGE_DIAGNOSTIC"and host["audit_execution_context_is_new"]is True and
          host["native_audit_completion_validated"]is True and host["rerouting_performed"]is False,
          "actual successful new audit host")
        require(host["original_run_conclusion"]==host["original_route_job_conclusion"]=="failure"and
          host["original_audit_jobs_conclusion"]=="skipped"and host["original_audits_succeeded"]is False,
          "original failed/skipped jobs relabelled")
        require(not host["terminal_errors"]and not inner["terminal_errors"]and not case["terminal_errors"]and
          all(r["completed"]is True for r in host["terminal_actions"]),"terminal preservation/cleanup failure")
        state=host["container_terminal"]["State"]
        require(state["Running"]is False and state["OOMKilled"]is False and state["ExitCode"]==0,
          "owned container not cleanly terminal")
        require(inner["status"]=="PASS_BUILT_ELF_ACTUAL_AUDIT_STAGE"and inner["stage"]=="audit"and
          all(r["returncode"]==0 and r["timed_out"]is False for r in inner["commands"]),"actual inner audit failed")
        require(case["source"]==ROUTE_SOURCE and case["run_id"]==ROUTE_RUN and case["mode"]==mode and
          case["stage"]=="audit"and case["complete_tail"]is True,"case frozen execution context changed")
        require(case["frozen_input"]=={'bytes': 4096412802, 'files': 746, 'inventory_sha256': 'c7b68b06075554293262760be383b69046a01a96efe936b6de6b102b5c8bbc09'},"complete746 frozen input changed")
        lineage=case["route_lineage"]
        require(lineage["new_host_context"]==ctx and lineage["old_context"]==frozen and
          lineage["future_audits_are_new_execution"]is True and lineage["original_audits_succeeded"]is False and
          lineage["original_audit_jobs_conclusion"]=="skipped","case route recovery lineage changed")
        commands=case["commands"]
        require([r["label"]for r in commands]==list(c.PHASES[1:]),"five original audit phases changed")
        require(all(r["argv"]==c.command(r["label"])and r["returncode"]==0 and
          r["requested_timeout_seconds"]==1200 and r["supervision_failure"]is None and
          not r["process_group_cleanup"]["remaining_live"]for r in commands),"original audit command/budget failed")
        require(c.complete(case["phase_results"])==case["original_audits"],"unchanged original completion gate differs")
        require(case["complete_drc"]==case["phase_results"]["drc-audit"]["final_DRT"]and
          case["complete_drc"]["marker_count"]==3 and case["complete_drc"]["zero_reported_DRT_markers"]is False,
          "original three shorts lost")
        for phase in ("route-audit","unfix-audit","drc-audit"):
            r=case["phase_results"][phase];delta=r["routing_delta"]
            require(r["native_invariants_passed"]is True and delta["changed_signal_count"]==0 and
              delta["changed_signal_names"]==[]and delta["only_two_signals_permitted"]==["net36993","net459"]and
              delta["non_NETS_bytes_exact"]is True and delta["other_records_byte_exact"]is True,"original routing invariants")
            if phase!="route-audit":
                gate=r["original_gate"]["result"]
                require(r["original1691_clock_gate_passed"]is True and gate["clock_or_fixed_nets"]==1691 and
                  gate["all_source_clock_and_fixed_records_preserved"]is True,"original1691 clock gate changed")
        for report in (host,case):
            require(all(report[k]is False for k in ("physical_acceptance","timing_accepted","full_phy_accepted",
              "observer_equivalence_qualified")),"historical report acceptance changed")
        for filename in ("case-result.json","inner-result.json","current-host-request.json","frozen-native-request.json"):
            require(host["available_outputs"][filename]==receipt["files"][PREFIX+mode+"/"+filename],
              "host report byte join changed")
        tag="cloud-results-"+str(AUDIT_RUN)+"-1-mainchip-route-audit-only-recovery-"+mode
        rel=row["release.json"]
        proof=validate_release(rel,row["tag.json"],tag,AUDIT_SOURCE)
        require(rel["id"]==RELEASES[mode],"wrong mode release")
        assets={a["name"]:a for a in rel["assets"]}
        for filename in ("host-result.json","case-result.json","inner-result.json","current-host-request.json",
                         "frozen-native-request.json","outputs.json","parts.json"):
            expected=receipt["files"][PREFIX+mode+"/"+filename];a=assets[filename]
            require(a["size"]==expected["bytes"]and a["digest"]=="sha256:"+expected["sha256"],
              "complete direct release join changed")
        parts=row["parts.json"]
        require(len(parts["parts"])==2 and sum(p["bytes"]for p in parts["parts"])==parts["archive"]["bytes"],
          "complete archive parts census changed")
        for part in parts["parts"]:
            asset=assets[part["name"]]
            require(asset["size"]==part["bytes"]and asset["digest"]=="sha256:"+part["sha256"],
              "archive part metadata join changed")
        outputs=row["outputs.json"]
        for filename,entry in outputs["files"].items():
            saved=receipt["files"].get(PREFIX+mode+"/"+filename)
            if saved is not None:
                require(saved==entry,"complete saved output map join changed")
        require(outputs["source"]==AUDIT_SOURCE and outputs["mode"]==mode and
          outputs["new_audit_execution_evidence"]is True,"new audit output context changed")
        proofs[mode]=dict(new_host=ctx,frozen_case=frozen,release=proof,original_clock_count=1691,
          original_DRT_shorts=3,target_signal_geometry_changes=0)
    return proofs

def saved_comparison(value=None):
    value=read_saved()if value is None else value
    proofs=validate_case_bindings(value)
    # The frozen comparison source and its arguments remain unchanged. Its source/run
    # fields describe the restored route context, not the newer audit host execution.
    compared=c.compare_cases(value["off"]["case-result.json"],value["on"]["case-result.json"])
    return dict(schema="authentic-recovered-audit-case-comparison-v1",comparison=compared,
      bindings=proofs,actual_audit_source=AUDIT_SOURCE,actual_audit_run=AUDIT_RUN,
      comparator_frozen_source=ROUTE_SOURCE,comparator_frozen_run=ROUTE_RUN,
      original_reports_unmodified=True,physical_acceptance=False,timing_accepted=False,
      full_phy_accepted=False,runtime_root_cause_established=False,new_native_execution=False)
