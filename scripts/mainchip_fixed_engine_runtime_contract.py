#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Current FIXED-guard ELF runtime authority; no routing or physical acceptance."""
import os
from pathlib import Path
import re
import mainchip_fixed_engine_runtime_admission as admission
import mainchip_built_engine_runtime_contract as frozen
import mainchip_fixed_engine_build_contract as qualified_build
import mainchip_witness_engine_build_contract as core
from mainchip_witness_engine_build_contract import (
    require, secure_file, digest, decode, atomic_record, attempt, finish_record,
    error_record, IMAGE, IMAGE_ID, MEMORY, CPUS, PIDS, create_argv,
    validate_image, validate_container)

ROOT=Path(__file__).resolve().parent.parent
METHOD="scripts/mainchip-fixed-engine-runtime-probe-methods.json"
GROUP="mainchip-fixed-engine-runtime-probe"
BRANCH="codex/mainchip-fixed-engine-runtime-probe"
SCHEMA="mainchip-fixed-engine-runtime-probe-v1"
REPOSITORY=core.REPOSITORY
PRIOR=admission.METHOD
PRIOR_SHA='6ca26990c04240c2274af3a51a3019a9584c78e76c3f3dc3351b03905a850819'
PREFIX=admission.PREFIX+"direct/"
RUNTIME_SOURCE=PREFIX+"runtime-dependencies.json"
ENGINE_RUN=admission.RUN
ENGINE_SOURCE=admission.SOURCE
ENGINE_RELEASE=admission.RELEASE
ENGINE_TAG=admission.TAG
ENGINE=admission.ENGINE
INPUT=admission.INPUT
INPUT_MEMBER=frozen.INPUT_MEMBER
LIMITS=frozen.LIMITS
INPUT_CONTROLS={'run': 40850943370, 'source': 'c902dccdab9b3d1d5a750cb198ea7dcb2665a40d', 'method_sha256': '6ca26990c04240c2274af3a51a3019a9584c78e76c3f3dc3351b03905a850819', 'receipt_sha256': 'f2ecda3a930ba3e071a9de280b4c5362133bc2adfe95097b90c1db575e592dcc'}
PROOF_PREFIX='docs/evidence/mainchip-fixed-engine-runtime-input-controls-terminal-20261029/'
INPUT_PROOF={'docs/evidence/mainchip-fixed-engine-runtime-input-controls-terminal-20261029/123369954420.job.json': {'bytes': 3026, 'sha256': 'f8c50444e280076a864f9e114b479d8c5e0ac5928354ca0279777347ccfc0d61'}, 'docs/evidence/mainchip-fixed-engine-runtime-input-controls-terminal-20261029/123369954420.job.log': {'bytes': 40451, 'sha256': '4635674f768bcf4fdee986b7f0f8c77c6a0ce28a8fa780367b3d38d95b1a87e1'}, 'docs/evidence/mainchip-fixed-engine-runtime-input-controls-terminal-20261029/123370156446.job.json': {'bytes': 1976, 'sha256': 'f1b2e7378271ca8d2997435b22e4105570f450fa22a17da3accefe78fc5ee431'}, 'docs/evidence/mainchip-fixed-engine-runtime-input-controls-terminal-20261029/123370156446.job.log': {'bytes': 7543, 'sha256': '1eafa6b93b7adc6dac8b48638e7c47146ac9117e26a67e8432240d549ee45f2d'}, 'docs/evidence/mainchip-fixed-engine-runtime-input-controls-terminal-20261029/artifacts.json': {'bytes': 1893, 'sha256': '6cd5529786cf747bdb6480f64f2a1079ec97d3c13b726ceb6345e071b0605bc0'}, 'docs/evidence/mainchip-fixed-engine-runtime-input-controls-terminal-20261029/controls/context.json': {'bytes': 249, 'sha256': '7051ba70f5195d87daba6c506ed9dbbab13f8d7b01f8bbddbfd625141ee51958'}, 'docs/evidence/mainchip-fixed-engine-runtime-input-controls-terminal-20261029/controls/result.json': {'bytes': 10797, 'sha256': 'dde906d116dadad235e01a0b0954c254a1824233e0e841523e3ebbebc7300618'}, 'docs/evidence/mainchip-fixed-engine-runtime-input-controls-terminal-20261029/controls/stderr.log': {'bytes': 0, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}, 'docs/evidence/mainchip-fixed-engine-runtime-input-controls-terminal-20261029/controls/stdout.log': {'bytes': 0, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}, 'docs/evidence/mainchip-fixed-engine-runtime-input-controls-terminal-20261029/index.json': {'bytes': 751, 'sha256': '044f369f256619b071baecc591f6d9fe0c37bd95388a5c2b26b5392bc460c5fe'}, 'docs/evidence/mainchip-fixed-engine-runtime-input-controls-terminal-20261029/jobs.json': {'bytes': 5651, 'sha256': '9a8d041a5b5453eb4a470b85013e9a07b42951fe6e11883fc07b71ade3e097ac'}, 'docs/evidence/mainchip-fixed-engine-runtime-input-controls-terminal-20261029/receipt.json': {'bytes': 3575, 'sha256': 'f2ecda3a930ba3e071a9de280b4c5362133bc2adfe95097b90c1db575e592dcc'}, 'docs/evidence/mainchip-fixed-engine-runtime-input-controls-terminal-20261029/run.json': {'bytes': 14444, 'sha256': '32235d143adb90ad983965ad8cfd17b969d8bc20ae58bcc85f586bb28a4a9782'}}
NEW_FILES=['scripts/mainchip_fixed_engine_runtime_contract.py', 'scripts/mainchip_fixed_engine_runtime_inner.py', 'scripts/check_mainchip_fixed_engine_runtime_probe.py', 'docs/evidence/mainchip-fixed-engine-runtime-probe-contract-review-20261029.json']
AUTH_FALSE=("native_routing_authorized","engine_build_authorized",
    "rc_sta_execution_authorized","physical_acceptance","timing_accepted",
    "full_phy_accepted","observer_equivalence_qualified","runtime_qualified")
expected_engine=admission.expected_engine
engine_envelope=admission.engine_envelope
engine_extract=admission.engine_extract
runtime_match=admission.runtime_match
direct_plan=qualified_build.direct_plan


def context(env):
    require(env.get("GITHUB_ACTIONS")=="true" and env.get("RUNNER_OS")=="Linux"
            and env.get("RUNNER_ENVIRONMENT")=="github-hosted","hosted Linux only")
    require(env.get("GITHUB_REPOSITORY")==REPOSITORY,"repository identity")
    require(env.get("GITHUB_EVENT_NAME")=="workflow_dispatch","manual runtime probe only")
    require(env.get("GITHUB_RUN_ATTEMPT")=="1","no retry")
    require(re.fullmatch("[1-9][0-9]*",env.get("GITHUB_RUN_ID",""))is not None,"run identity")
    require(re.fullmatch("[0-9a-f]{40}",env.get("GITHUB_SHA",""))is not None,"source identity")
    require(env.get("GITHUB_REF")=="refs/heads/"+BRANCH,"runtime probe branch")
    token=env["GITHUB_RUN_ID"]+"-1"
    # Inherited Docker ownership name only; this job performs no compilation.
    return dict(name="nssoc-witness-build-"+token,source=env["GITHUB_SHA"],token=token)


def validate_method(m,prior):
    require(m["schema"]==SCHEMA and m["branch"]==BRANCH and m["group"]==GROUP,"method identity")
    require(m["limits"]==LIMITS and m["image"]==IMAGE and m["image_id"]==IMAGE_ID,"runtime limits/image")
    require(m["engine"]==ENGINE and m["input"]==INPUT,"immutable native inputs")
    require(m["producer_input_controls"]==INPUT_CONTROLS,"qualified input source-controls binding")
    require(m["prior_method_sha256"]==PRIOR_SHA,"prior method binding")
    for key in ("source_controls_authorized","native_probe_authorized","controller_ready"):
        require(type(m[key])is bool,"typed runtime authority: "+key)
    require(m["controller_ready"]==m["native_probe_authorized"],"native/controller agreement")
    require(not m["native_probe_authorized"]or m["source_controls_authorized"],"native requires source controls")
    for key in AUTH_FALSE:require(m[key]is False,"read-only runtime scope: "+key)
    require(m["qualified_engine"]is None and m["qualified_routing_engine"]is None,"no runtime or routing qualification transfer")
    require(len(prior["protected"])==925 and m["inherited_protected_count"]==925,"inherited 925 source map")
    require(all(m["protected"].get(p)==h for p,h in prior["protected"].items()),"inherited source protection removed")
    require(set(NEW_FILES)<=set(m["protected"]),"required new runtime source pins")
    require(m["protected"].get(PRIOR)==PRIOR_SHA,"protected prior method")
    for path,row in INPUT_PROOF.items():
        require(m["protected"].get(path)==row["sha256"],"protected full input-controls proof: "+path)
    return m


def input_controls(root=ROOT):
    raw={}
    for path,row in INPUT_PROOF.items():
        b=secure_file(root,path).read_bytes()
        require(dict(bytes=len(b),sha256=digest(b))==row,"input-controls proof bytes: "+path)
        raw[path[len(PROOF_PREFIX):]]=b
    docs={p:decode(b)for p,b in raw.items()if p.endswith(".json")}
    receipt=docs["receipt.json"];result=docs["controls/result.json"]
    run=docs["run.json"];jobs=docs["jobs.json"]["jobs"];index=docs["index.json"]
    require(receipt["files"]=={p:r for p,r in INPUT_PROOF.items()if not p.endswith("/receipt.json")},
            "complete input-controls receipt map")
    require((receipt["run"],receipt["source"],receipt["attempt"],receipt["terminal"])==
            (INPUT_CONTROLS["run"],INPUT_CONTROLS["source"],1,"success"),"input-controls terminal identity")
    require(receipt["protected_source_method_sha256"]==PRIOR_SHA and receipt["source_only"]is True,
            "input-controls original method/scope")
    require((run["id"],run["head_sha"],run["run_attempt"],run["status"],run["conclusion"])==
            (INPUT_CONTROLS["run"],INPUT_CONTROLS["source"],1,"completed","success"),"input-controls run")
    require(run["path"]==".github/workflows/mainchip-fixed-engine-runtime-input-controls.yml"
            and run["workflow_id"]==400428743 and run["event"]=="workflow_dispatch"
            and run["head_branch"]=="codex/mainchip-fixed-engine-runtime-preparation","input-controls workflow")
    require(len(jobs)==2 and {j["id"]:(j["name"],j["status"],j["conclusion"])for j in jobs}==
            {123369954420:("source-controls","completed","success"),
             123370156446:("preserve-source-job-log","completed","success")},"input-controls full successful jobs")
    for job in jobs:
        require(job==docs[str(job["id"])+".job.json"],"input-controls exact job projection")
        require(all(s["status"]=="completed"and s["conclusion"]in ("success","skipped")for s in job["steps"]),
                "input-controls job step failure")
    require(set(index)=={"context.json","result.json","stdout.log","stderr.log"},"input-controls full indexed set")
    for name,row in index.items():
        b=raw["controls/"+name]
        require(row["present"]is True and row["path"]==name and
                row["bytes"]==len(b)and row["sha256"]==digest(b),"input-controls indexed bytes")
    old_context=dict(source=INPUT_CONTROLS["source"],run_id=INPUT_CONTROLS["run"],attempt=1,
                     native_authorized=False,source_controls_only=True)
    require(result["current_context"]==old_context and
            docs["controls/context.json"]==dict(old_context,method_sha256=PRIOR_SHA),"input-controls exact context")
    require(result["status"]=="PASS_FIXED_ENGINE_RUNTIME_INPUT_SOURCE_CONTROLS"and
            result["positive_count"]==len(result["positive_cases"])==5 and
            result["refusal_count"]==len(result["refusals"])==74 and
            result["synthetic_archive"]["refusal_count"]==6,"input-controls actual 5/74/6")
    require(result["actual_metadata_validated"]is True and result["original920_sources_unchanged"]is True,
            "input-controls actual metadata")
    for key in ("actual_native_archive_restored","actual_runtime_probe_executed","new_ELF_executed",
                "native_payload_acquired","runtime_qualified","physical_acceptance"):
        require(result[key]is False,"input source tests are not native qualification")
    require(receipt["actual_native_archive_restoration_qualified"]is False and
            receipt["actual_runtime_probe_executed"]is False and receipt["runtime_qualified"]is False,
            "historical tests cannot qualify runtime")
    return dict(**INPUT_CONTROLS,complete_proof_files=len(INPUT_PROOF),positive_count=5,refusal_count=74,
                synthetic_restore_refusals=6,runtime_qualified=False)


def method(root):
    prior_raw=secure_file(root,PRIOR).read_bytes()
    require(digest(prior_raw)==PRIOR_SHA,"immutable original source-qualified method")
    prior=admission.methods(root)
    m=validate_method(decode(secure_file(root,METHOD).read_bytes()),prior)
    for path,h in m["protected"].items():
        require(isinstance(h,str)and re.fullmatch("[0-9a-f]{64}",h)is not None and
                digest(secure_file(root,path).read_bytes())==h,"protected source: "+path)
    input_controls(root)
    return m


def authorize_native(m):
    require(m["source_controls_authorized"]is True and m["native_probe_authorized"]is True
            and m["controller_ready"]is True,"native runtime probe not authorized")
    for key in AUTH_FALSE:require(m[key]is False,"native runtime cannot authorize other stages")
    return m


def validate_reservation(proof,ctx,empty):
    require(type(proof["release_id"])is int and proof["release_id"]>0 and
      proof["externally_reserved"]is True and proof["creation_attempted"]is False and
      proof["assets_overwritten"]is False and proof["target_verified"]is True,"reserved-only build publication")
    require(proof["tested_source"]==ctx["source"]and
      proof["tag"]=="cloud-results-"+ctx["token"]+"-"+GROUP,"new source/tag reservation")
    require(type(proof["existing_assets"])is list and(not empty or proof["existing_assets"]==[]),
      "release must be empty before acquisition")
    return proof

