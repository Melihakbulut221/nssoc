#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Separate authority for a newly compiled FIXED-guard ELF; no inherited ELF acceptance."""
import json,os,re
from pathlib import Path
import mainchip_witness_engine_build_contract as old
from mainchip_witness_engine_build_contract import (
 require,digest,decode,secure_file,validate_image,create_argv,validate_container,
 validate_terminal,error_record,atomic_record,inventory,attempt,finish_record,
 validate_build_configuration,REPOSITORY,UPSTREAM,IMAGE,IMAGE_ID,MEMORY,CPUS,PIDS,GITLINKS)
import mainchip_fixed_neardrc_repair as repair
import mainchip_two_signal_internal_witness as observer

METHOD="scripts/mainchip-fixed-engine-build-methods.json"
BRANCH="codex/mainchip-fixed-engine-build"
GROUP="mainchip-fixed-neardrc-engine-build"
PRIOR="scripts/mainchip-fixed-neardrc-repair-methods.json"
PRIOR_SHA="381818adb4005c15ac2a5ff4c0d400b82c0467f16ca63b0a00d5aed5f2e0a526"
PRIOR_COUNT=857
OLD_BUILD_METHOD="scripts/mainchip-internal-witness-engine-build-methods.json"
OLD_BUILD_SHA="d4e9b849aaa9559784972a3d6f401ff7f4f9b4165bcb91480559df92cd270303"
ROUTER="src/drt/src/TritonRoute.cpp"
FLEX="src/drt/src/dr/FlexDR_init.cpp"
DERIVED_ROUTER="385e2d9f681c0039c8caa7c49a4b8bf72570c97d6be808533475486f102be7fd"
HEADER_SHA="8107a009d7db32e56a355b3c40c9f3e94dc2cd40df2afc575a8e7c652e63ff62"
PROJECTION={
 "inner.py":("scripts/mainchip_witness_engine_build_inner.py","2e46ee1770261ab31689148b0b45c1c7a8b180141c55d7d717f832ce93e31caa"),
 "mainchip_witness_engine_build_contract.py":("scripts/mainchip_witness_engine_build_contract.py","fff2cf22b44cf39680c1fdeb4884b86e03a3b6d0d8c6683a61d82163121340cb")}
LIMITS=dict(memory_bytes=MEMORY,nano_cpus=CPUS,pids=PIDS,build_seconds=10800,min_free_disk_bytes=32*1024**3)
FALSE=("native_routing_authorized","native_probe_authorized","rc_sta_execution_authorized",
 "physical_acceptance","timing_accepted","full_phy_accepted","observer_equivalence_qualified",
 "runtime_qualified","runtime_root_cause_established","automatic_retry_authorized")

def method(root):
    m=decode(secure_file(root,METHOD).read_bytes())
    require(m["schema"]=="mainchip-fixed-engine-build-v1","new build schema")
    require(m["source_unit_complete"]is True and all(type(m[k])is bool for k in
      ("source_controls_authorized","engine_build_authorized","controller_ready")),"typed new build authority")
    require(all(m[k]is False for k in FALSE)and m["qualified_engine"]is None,"build-only scope")
    require(m["limits"]==LIMITS and m["upstream"]==UPSTREAM and m["image"]==IMAGE
      and m["image_id"]==IMAGE_ID,"unchanged build inputs/resources")
    require(m["derived_router_sha256"]==DERIVED_ROUTER and
      m["fixed_guard_sha256"]==repair.PATCHED_SHA,"new source derivative identity")
    prior_raw=secure_file(root,PRIOR).read_bytes();require(digest(prior_raw)==PRIOR_SHA,"prior method changed")
    prior=decode(prior_raw)
    require(len(prior["protected"])==PRIOR_COUNT and
      all(m["protected"].get(p)==h for p,h in prior["protected"].items()),"inherited857 source protection")
    require(m["protected"].get(PRIOR)==PRIOR_SHA and m["protected"].get(OLD_BUILD_METHOD)==OLD_BUILD_SHA,
      "historical authority files unprotected")
    required=("scripts/mainchip_fixed_engine_build.py","scripts/mainchip_fixed_engine_build_contract.py",
      "scripts/check_mainchip_fixed_engine_build.py",".github/workflow-templates/mainchip-fixed-engine-build.yml",
      "docs/evidence/mainchip-fixed-engine-build-source-review-20261029.json")
    require(all(p in m["protected"]for p in required),"new source unit pin omitted")
    require(digest(secure_file(root,OLD_BUILD_METHOD).read_bytes())==OLD_BUILD_SHA,"old build authority changed")
    expected=decode(secure_file(root,OLD_BUILD_METHOD).read_bytes())["upstream_primary"]
    expected=dict(expected,**{FLEX:repair.ORIGINAL_SHA,ROUTER:observer.ORIGINAL_SHA})
    require(m["upstream_primary"]==expected,"exact upstream patch inputs")
    for p,h in m["protected"].items():
        require(type(h)is str and re.fullmatch("[0-9a-f]{64}",h)and
          digest(secure_file(root,p).read_bytes())==h,"protected new build source: "+p)
    return m

def context(env):
    require(env.get("GITHUB_ACTIONS")=="true"and env.get("RUNNER_ENVIRONMENT")=="github-hosted"
      and env.get("RUNNER_OS")=="Linux"and env.get("GITHUB_REPOSITORY")==REPOSITORY,"hosted source context")
    require(env.get("GITHUB_EVENT_NAME")=="workflow_dispatch"and env.get("GITHUB_RUN_ATTEMPT")=="1",
      "first manual build attempt")
    require(env.get("GITHUB_REF")=="refs/heads/"+BRANCH,"new build branch")
    require(re.fullmatch("[0-9a-f]{40}",env.get("GITHUB_SHA",""))is not None and
      re.fullmatch("[1-9][0-9]*",env.get("GITHUB_RUN_ID",""))is not None,"current source/run identity")
    token=env["GITHUB_RUN_ID"]+"-1"
    return dict(name="nssoc-witness-build-"+token,source=env["GITHUB_SHA"],token=token)

def authorize(m):
    require(m["source_controls_authorized"]is True and m["engine_build_authorized"]is True
      and m["controller_ready"]is True,"new build execution disabled")

def validate_reservation(proof,ctx,empty):
    require(type(proof["release_id"])is int and proof["release_id"]>0 and
      proof["externally_reserved"]is True and proof["creation_attempted"]is False and
      proof["assets_overwritten"]is False and proof["target_verified"]is True,"reserved-only build publication")
    require(proof["tested_source"]==ctx["source"]and
      proof["tag"]=="cloud-results-"+ctx["token"]+"-"+GROUP,"new source/tag reservation")
    require(type(proof["existing_assets"])is list and(not empty or proof["existing_assets"]==[]),
      "release must be empty before acquisition")
    return proof

def source_delta(original,derived):
    require(type(original)is dict and type(derived)is dict and len(original)>2
      and set(original)==set(derived),"complete tracked source census")
    changed={p for p in original if original[p]!=derived[p]}
    require(changed=={ROUTER,FLEX},"only observer and FIXED repair may change")
    for p,oldhash,newhash in ((ROUTER,observer.ORIGINAL_SHA,DERIVED_ROUTER),
      (FLEX,repair.ORIGINAL_SHA,repair.PATCHED_SHA)):
        for row in (original[p],derived[p]):
            require(set(row)=={"bytes","sha256"}and type(row["bytes"])is int and row["bytes"]>0,
              "tracked regular source identity")
        require(original[p]["sha256"]==oldhash and derived[p]["sha256"]==newhash,"source delta hashes")
    return dict(original_files=len(original),derived_files=len(derived),changed_paths=sorted(changed),
      source_hashes={p:dict(original=original[p],derived=derived[p])for p in sorted(changed)},
      all_other_tracked_bytes_unchanged=True,header_sha256=HEADER_SHA,
      old_engine_acceptance_reused=False,full_engine_compilation_required=True)

def validate_projection(work):
    rows={}
    for destination,(source,h)in PROJECTION.items():
        p=secure_file(Path(work),destination)
        require(digest(p.read_bytes())==h,"immutable inner projection changed")
        rows[destination]=dict(source=source,bytes=p.stat().st_size,sha256=h)
    return rows

def direct_plan(out,names):
    rows=[]
    for name in names:
        p=Path(out)/name;require(not p.is_symlink(),"direct publication symlink")
        row=dict(name=name,archive_member=name,present=p.is_file())
        if row["present"]:
            raw=p.read_bytes();row.update(bytes=len(raw),sha256=digest(raw),
              disposition="direct"if raw else"archive_only_empty")
        else:row["disposition"]="absent"
        rows.append(row)
    require(len({r["name"]for r in rows})==len(rows),"duplicate direct publication member")
    return dict(schema="fixed-engine-direct-publication-plan-v1",files=rows,
      empty_files_retained_in_full_archive=True,missing_terminal_is_not_acceptance=True)

def control_evidence(root,ctx):
    names=("fixed-engine-controls.json","engine-build-controls.json","internal-witness-controls.json")
    raw={n:secure_file(root,n).read_bytes()for n in names}
    records={n:decode(b)for n,b in raw.items()};r=records[names[0]];old=records[names[1]];w=records[names[2]]
    require(r["status"]=="PASS_FIXED_ENGINE_BUILD_SOURCE_CONTROLS"and
      r["current_source"]==ctx["source"]and r["current_token"]==ctx["token"],"current actual new controls binding")
    require(all(r[k]is False for k in ("actual_engine_compilation","native_payload_acquired",
      "runtime_qualified","routing_qualified","physical_acceptance")),"source controls scope")
    require(r["unchanged_build_controls"]==old and old["status"]=="PASS_ENGINE_BUILD_SOURCE_CONTROLS"
      and(old["positive_count"],old["refusal_count"],old["lifecycle"]["count"])==(7,45,25),"original build controls join")
    require(w["status"]=="PASS"and(w["positive_count"],w["refusal_count"])==(4,29)
      and all(w[k]is False for k in ("engine_compiled","native_executed","physical_acceptance")),"original observer controls")
    return {n:dict(bytes=len(b),sha256=digest(b))for n,b in raw.items()}
