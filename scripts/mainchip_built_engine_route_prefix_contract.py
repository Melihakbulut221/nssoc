#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Actual built-engine shared routing preparation; no router launch is authorized."""
import os
from pathlib import Path
import re
import mainchip_built_engine_runtime_contract as previous
from mainchip_built_engine_runtime_contract import (
 require,secure_file,digest,decode,atomic_record,attempt,finish_record,error_record,
 IMAGE,IMAGE_ID,MEMORY,CPUS,PIDS,create_argv,validate_image,validate_container,
 expected_engine,engine_envelope,engine_extract,runtime_match,ENGINE,INPUT,INPUT_MEMBER,PREFIX,REPOSITORY,
 ENGINE_RUN,ENGINE_RELEASE,ENGINE_TAG)
METHOD="scripts/mainchip-built-engine-route-prefix-methods.json"
GROUP="mainchip-built-engine-route-prefix"
BRANCH="codex/mainchip-built-engine-route-prefix"
LIMITS=dict(memory_bytes=MEMORY,nano_cpus=CPUS,pids=PIDS,phase_seconds=1200,
 inner_seconds=5400,container_seconds=5580,min_free_disk_bytes=24*1024**3,
 max_group_rss_kib=10485760,min_available_kib=2097152)
PHASES=("ownership","prepare-fixed","paired-all-nontarget-fixed-import","fixed-audit")
PASS_STATUSES={
 "ownership":"COMPLETE_READ_ONLY_OWNERSHIP_NOT_ROUTING_ACCEPTANCE",
 "prepare-fixed":"PREPARED_ALL_NONTARGET_FIXED_ENCODING",
 "fixed-audit":"PASS_ACTUAL_ALL_NONTARGET_FIXED_BEFORE_ONE_ATTEMPT"}
CANONICAL_OUT="/work/out/work"
def context(env):
    require(env.get("GITHUB_ACTIONS")=="true" and env.get("RUNNER_OS")=="Linux","hosted Linux only")
    require(env.get("GITHUB_REPOSITORY")==REPOSITORY,"repository identity")
    require(env.get("GITHUB_RUN_ATTEMPT")=="1","no retry")
    require(re.fullmatch("[1-9][0-9]*",env.get("GITHUB_RUN_ID","")) is not None,"run identity")
    require(re.fullmatch("[0-9a-f]{40}",env.get("GITHUB_SHA","")) is not None,"source identity")
    require(env.get("GITHUB_REF")=="refs/heads/"+BRANCH,"route prefix branch")
    token=env["GITHUB_RUN_ID"]+"-1"
    return dict(name="nssoc-witness-build-"+token,source=env["GITHUB_SHA"],token=token)
def method(root):
    m=decode(secure_file(root,METHOD).read_bytes())
    require(m["schema"]=="mainchip-built-engine-route-prefix-v1","method schema")
    require(m["limits"]==LIMITS and m["image"]==IMAGE and m["image_id"]==IMAGE_ID,"limits/image")
    require(m["engine"]==ENGINE and m["input"]==INPUT,"input identities")
    require(type(m["native_prefix_authorized"]) is bool,"authorization type")
    for k in ("native_routing_authorized","rc_sta_execution_authorized","physical_acceptance","observer_equivalence_qualified"):
        require(m[k] is False,"prefix scope")
    require(m["phases"]==list(PHASES),"only exact shared prefix")
    old=previous.method(root)
    require(m["inherited_protected_count"]==len(old["protected"]),"inherited map count")
    require(all(m["protected"].get(p)==h for p,h in old["protected"].items()),"inherited source removed")
    for p,h in m["protected"].items():
        require(re.fullmatch("[0-9a-f]{64}",h) is not None and digest(secure_file(root,p).read_bytes())==h,"protected source: "+p)
    return m
def command(phase,executable,out=CANONICAL_OUT):
    require(type(phase) is str and phase in PHASES,"unapproved prefix phase")
    require(executable=="/work/engine/openroad" and out==CANONICAL_OUT,"canonical native paths")
    if phase=="paired-all-nontarget-fixed-import":
        return [executable,"-no_init","-exit",out+"/fixed.tcl"]
    return [executable,"-no_init","-exit","-python","/work/source/scripts/mainchip_built_engine_route_prefix_native.py"]
def prefix_complete(records,ownership):
    import mainchip_two_signal_repair as repair
    require(set(records)==set(PASS_STATUSES),"prefix result census")
    for phase,status in PASS_STATUSES.items():
        row=records[phase]
        require(row["status"]==status and row["accepted"] is False and row["timing_accepted"] is False
                and row["full_phy_accepted"] is False,"prefix phase status/scope")
    repair.require_actionable(ownership)
    first=records["ownership"]
    require(first["original_gate"]["result"]["clock_or_fixed_nets"]==1691
            and first["original_gate"]["result"]["all_source_clock_and_fixed_records_preserved"] is True,"original clock gate")
    fixed=records["fixed-audit"]
    require(fixed["router_census"]["two_routed_nonfixed_guided_names"]==list(repair.TARGETS),"two-target routing boundary")
    return dict(status="PASS_PREPARED_SHARED_PREFIX_NOT_ROUTING_ACCEPTANCE",
                original_clock_count=1691,only_mutable=list(repair.TARGETS),
                native_routing_executed=False,physical_acceptance=False,observer_equivalence_qualified=False)
