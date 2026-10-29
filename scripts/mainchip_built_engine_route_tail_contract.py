#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Same frozen prefix and built ELF; two diagnostic tails, never physical acceptance."""
import os
import re
from pathlib import Path
import mainchip_built_engine_route_prefix_contract as previous
from mainchip_built_engine_route_prefix_contract import (
 require, secure_file, digest, decode, atomic_record, attempt, finish_record, error_record,
 IMAGE, IMAGE_ID, MEMORY, CPUS, PIDS, create_argv, validate_image, validate_container,
 engine_extract, runtime_match, ENGINE, INPUT, REPOSITORY)
from mainchip_witness_engine_build import fingerprint
from ensure_cloud_tested_source_release import validate_release
METHOD="scripts/mainchip-built-engine-route-tail-methods.json"
BRANCH="codex/mainchip-built-engine-route-tail-observer"
BASE_GROUP="mainchip-built-engine-route-tail"
MODE_ENV="NSSOC_ROUTE_TAIL_MODE"
STAGE_ENV="NSSOC_ROUTE_TAIL_STAGE"
MODES=("off","on")
PREFIX="docs/evidence/mainchip-canonical-prefix-terminal-20261029"
PREFIX_RUN=40789053922
PREFIX_SOURCE="e16c7f46a3b8f61c23507cdab8d60c4d9d4d3d8d"
PREFIX_RELEASE=427309454
PREFIX_TAG="cloud-results-40789053922-1-mainchip-built-engine-route-prefix"
FROZEN_COUNT=746
FROZEN_BYTES=4096412802
LIMITS=dict(memory_bytes=MEMORY,nano_cpus=CPUS,pids=PIDS,
 route_seconds=14400,phase_seconds=1200,min_free_disk_bytes=32*1024**3,
 archive_expanded_limit=8*1024**3,max_group_rss_kib=10485760,min_available_kib=2097152,
 route=dict(driver_seconds=14700,inner_seconds=15000,container_seconds=15180),
 audit=dict(driver_seconds=6300,inner_seconds=6600,container_seconds=6780))
PHASES=("one-two-signal-routing-attempt","route-audit","paired-original-class-return",
        "unfix-audit","full-original-class-read-only-DRT","drc-audit")
STATUSES={"route-audit":"PASS_ONLY_TWO_SIGNAL_DELTA_ALL_OTHERS_FIXED",
 "unfix-audit":"PASS_ORIGINAL_CLASS_TWO_SIGNAL_REPAIR_REQUIRES_DRC",
 "drc-audit":"COMPLETE_TWO_SIGNAL_ATTEMPT_ORIGINAL_CLASS_DRC_NOT_ACCEPTANCE"}
COMPARE_FILES=("routed-fixed.odb","routed-fixed.def","routed-audit.def",
 "repaired.odb","expected-original-class.def","repaired-audit.def",
 "drc-before.def","drc-after.def","drc-observed.odb","measured-audit.def")
WITNESS_ENV="NNSOC_DRT_INTERNAL_WITNESS_DIR"

def mode(env):
    value=env.get(MODE_ENV)
    require(value in (*MODES,"compare"),"tail mode")
    return value

def stage(env):
    value=env.get(STAGE_ENV)
    require(value in ("route","audit","compare"),"tail stage")
    require((mode(env)=="compare")== (value=="compare"),"mode/stage pair")
    return value

def group(value,stage):
    require(value in (*MODES,"compare"),"tail group mode")
    require(stage in ("route","audit","compare") and ((value=="compare")== (stage=="compare")),"tail group stage")
    return BASE_GROUP+"-compare" if value=="compare" else BASE_GROUP+"-"+value+"-"+stage

def stage_limits(value):
    require(value in ("route","audit"),"native stage limits")
    return LIMITS[value]


def context(env):
    # Same qualified container name/token syntax; matrix jobs have independent hosts.
    other=dict(env);other["GITHUB_REF"]="refs/heads/"+previous.BRANCH
    require(env.get("GITHUB_REF")=="refs/heads/"+BRANCH,"tail branch")
    ctx=previous.context(other);ctx["mode"]=mode(env);ctx["stage"]=stage(env)
    return ctx

def method(root):
    m=decode(secure_file(root,METHOD).read_bytes())
    require(m["schema"]=="mainchip-built-engine-route-tail-v1","tail method schema")
    require(m["source_unit_complete"] is True,"incomplete split source unit")
    require(m["limits"]==LIMITS and m["engine"]==ENGINE and m["input"]==INPUT
        and m["image"]==IMAGE and m["image_id"]==IMAGE_ID,"tail identities/limits")
    require(m["phases"]==list(PHASES) and m["modes"]==list(MODES),"tail scope")
    for k in ("source_controls_authorized","native_tail_authorized","native_route_authorized","native_audit_authorized"):
        require(type(m[k]) is bool,"authorization type")
    require(not m["native_tail_authorized"] or m["source_controls_authorized"],"split authorization")
    require(m["native_handoff_split_complete"] is True,"route/audit handoff split required")
    require(m["native_tail_authorized"]==m["native_route_authorized"]==m["native_audit_authorized"],
        "inconsistent stage authorizations")
    for k in ("rc_sta_execution_authorized","physical_acceptance","timing_accepted",
              "full_phy_accepted","observer_equivalence_qualified","automatic_retry_authorized"):
        require(m[k] is False,"no acceptance or continuation")
    old=previous.method(root)
    require(len(old["protected"])==645 and m["inherited_protected_count"]==645,"prefix pin count")
    require(all(m["protected"].get(p)==h for p,h in old["protected"].items()),"prefix pin changed")
    for p,h in m["protected"].items():
        require(re.fullmatch("[0-9a-f]{64}",h) is not None
            and digest(secure_file(root,p).read_bytes())==h,"protected source: "+p)
    return m

def saved(root,suffix):
    return decode(secure_file(root,PREFIX+"."+suffix+".json").read_bytes())

def prefix_contract(root):
    run=saved(root,"run");jobs=saved(root,"jobs");rel=saved(root,"release");tag=saved(root,"tag")
    envelope(root,run,jobs,rel,tag)
    host=saved(root,"host-result");inner=saved(root,"inner-result");native=saved(root,"native-prefix-result")
    require(host["status"]=="PASS_ACTUAL_ROUTING_PREFIX_READY_NO_ROUTING"
        and inner["status"]=="PASS_BUILT_ELF_ACTUAL_SHARED_PREFIX"
        and native["status"]=="PASS_ACTUAL_BUILT_ENGINE_SHARED_PREFIX","prefix terminal status")
    require(all(not x["terminal_errors"] for x in (host,inner,native)),"prefix terminal errors")
    require(host["source"]==PREFIX_SOURCE and native["complete_shared_prefix"],"prefix actual body")
    require(all(x["returncode"]==0 and not x["timed_out"] for x in inner["commands"]),"prefix inner commands")
    state=host["container_terminal"]["State"]
    require(not state["Running"] and not state["OOMKilled"] and state["ExitCode"]==0 and not state["Error"],"prefix container")
    previous.prefix_complete(native["phase_results"],native["phase_results"]["ownership"]["native_ownership"])
    require(native["phase_results"]["fixed-audit"]["timing_contract"]==dict(
        accepted=False,clock_periods_ns=[20,4,8,8],derating_percent=5,new_RC_STA_required=True),
        "original timing contract")
    require(native["phase_results"]["ownership"]["initial_original_class_DRT"]["marker_count"]==3,
        "original three-short input")
    frozen=saved(root,"frozen-prefix");inv=saved(root,"frozen-prefix-inventory")
    require(frozen["files"]==FROZEN_COUNT and frozen["unpacked_bytes"]==FROZEN_BYTES
        and len(inv["files"])==FROZEN_COUNT and sum(x["bytes"] for x in inv["files"].values())==FROZEN_BYTES,"full frozen census")
    require(inv["canonical_root"]=="/work" and inv["original_engine"]==ENGINE and inv["original_input"]==INPUT,"frozen identity")
    require(inv["files"]["out/work/fixed.odb"]["sha256"]=="45dc1b634fafaba4dda8475430ea1a82a69a355dfac6a6b2bbdf63529777e431"
        and inv["files"]["out/work/repair.tcl"]["sha256"]=="ea723ae478c019c45ce79f33c6a4abb65d298c053abd32c35c4376902be02c2d","frozen prepared identities")
    return inv

def envelope(root,run,jobs,release,tag):
    require(run["id"]==PREFIX_RUN and run["head_sha"]==PREFIX_SOURCE and run["run_attempt"]==1
        and run["status"]=="completed" and run["conclusion"]=="success","prefix run")
    actual={(x["id"],x["name"],x["conclusion"]) for x in jobs["jobs"]}
    require(len(jobs["jobs"])==2 and actual=={(123169424619,"source-controls","success"),(123169585175,"native-prefix","success")},"prefix jobs")
    require(release["id"]==PREFIX_RELEASE and release["tag_name"]==PREFIX_TAG
        and release["draft"] is False and release["prerelease"] is True,"prefix release")
    require(tag["object"]["type"]=="commit" and tag["object"]["sha"]==PREFIX_SOURCE,"prefix lightweight tag")
    validate_release(release,tag,PREFIX_TAG,PREFIX_SOURCE)
    expected=saved(root,"release")
    project=lambda r:{a["name"]:(a["id"],a["size"],a["digest"]) for a in r["assets"]}
    require(len(release["assets"])==22 and project(release)==project(expected),"complete prefix assets")
    return dict(run=PREFIX_RUN,source=PREFIX_SOURCE,release=PREFIX_RELEASE,tag=PREFIX_TAG,all_assets=project(release))

def frozen_unchanged(work,inv):
    for p,row in inv["files"].items():
        require(fingerprint(secure_file(work,p))==row,"frozen input changed: "+p)
    return dict(files=len(inv["files"]),bytes=sum(x["bytes"] for x in inv["files"].values()))

def command(phase):
    require(phase in PHASES,"unapproved tail phase")
    root="/work/out/work";elf="/work/engine/openroad"
    scripts={"one-two-signal-routing-attempt":"repair.tcl",
       "paired-original-class-return":"unfix.tcl","full-original-class-read-only-DRT":"final-drc.tcl"}
    if phase in scripts:return [elf,"-no_init","-exit",root+"/"+scripts[phase]]
    return [elf,"-no_init","-exit","-python","/work/tail-source/scripts/mainchip_built_engine_route_tail_native.py"]

def complete(records):
    import mainchip_two_signal_repair as repair
    require(set(records)==set(STATUSES),"tail result census")
    for phase,status in STATUSES.items():
        r=records[phase]
        require(r["status"]==status and r["accepted"] is False
            and r["timing_accepted"] is False and r["full_phy_accepted"] is False,"tail original status/scope")
    gate=repair.require_complete(records["drc-audit"])
    return dict(original_audits_complete=True,original_gate=gate,
        physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)

def compare_cases(off,on):
    for value,case in (("off",off),("on",on)):
        require(case["schema"]=="built-engine-route-tail-case-v1" and case["mode"]==value
            and case["status"]=="PASS_COMPLETE_ROUTE_TAIL_DIAGNOSTIC" and not case["terminal_errors"],"complete tail case")
        require(case["stage"]=="audit" and case["route_lineage"]["authenticated_complete_route"] is True,
            "audited route lineage")
        require(case["engine"]==ENGINE and case["frozen_input"]==off["frozen_input"],"same frozen input and ELF")
        require(case["prefix_source"]==PREFIX_SOURCE and case["prefix_run"]==PREFIX_RUN,"same prefix")
        require(case["original_audits"]["original_audits_complete"] is True,"original audits")
        require(case["physical_acceptance"] is False and case["timing_accepted"] is False
            and case["full_phy_accepted"] is False,"comparison acceptance scope")
        require(set(case["geometry_files"])==set(COMPARE_FILES),"complete geometry projection")
    require(off["source"]==on["source"] and off["run_id"]==on["run_id"],"same successor source/run")
    require(off["observer"]=={"enabled":False,"witness_files":0},"off environment")
    require(on["observer"]["enabled"] is True and on["observer"]["writer_raw_join"] is True
        and on["observer"]["diagnosis"]["status"]=="COMPLETE_DIAGNOSTIC_ONLY"
        and len(on["observer"]["diagnosis"]["stages"])==4,"on complete witness")
    geometry_equal=off["geometry_files"]==on["geometry_files"]
    drc_equal=off["complete_drc"]==on["complete_drc"]
    return dict(schema="built-engine-route-tail-comparison-v1",
        status="PASS_OBSERVER_OFF_ON_OUTPUT_EQUIVALENCE_ONLY" if geometry_equal and drc_equal
            else "FAIL_OBSERVER_OFF_ON_OUTPUT_EQUIVALENCE",
        source=off["source"],run_id=off["run_id"],engine=ENGINE,
        frozen_input=off["frozen_input"],geometry_files_equal=geometry_equal,
        complete_original_class_DRC_equal=drc_equal,
        actual_off_DRC=off["complete_drc"],actual_on_DRC=on["complete_drc"],
        observed_equivalence=geometry_equal and drc_equal,
        physical_acceptance=False,timing_accepted=False,full_phy_accepted=False,
        root_cause_established=False,automatic_continuation_authorized=False)
