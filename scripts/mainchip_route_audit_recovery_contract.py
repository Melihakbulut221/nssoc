#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Separate new audit authority from immutable failed route-publication history."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import mainchip_route_recovery_evidence as evidence
import mainchip_built_engine_route_tail_contract as old

ROOT=Path(__file__).resolve().parents[1]
BRANCH="codex/mainchip-route-audit-only-recovery"
METHOD="scripts/mainchip-route-audit-recovery-methods.json"
CONTROLS="route-audit-recovery-controls.json"
MODES=("off","on")
GROUP="mainchip-route-audit-only-recovery"
FALSE_FLAGS=("native_routing_authorized","observer_equivalence_qualified","physical_acceptance",
 "timing_accepted","full_phy_accepted","automatic_retry_authorized","rc_sta_execution_authorized")
REQUIRE_FALSE=("physical_acceptance","timing_accepted","full_phy_accepted","observer_equivalence_qualified")
require=old.require


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()


def source_guard(root=ROOT):
    root=Path(root)
    require(root.resolve()==ROOT,"recovery source root")
    original=evidence.source_guard()
    raw=old.secure_file(root,METHOD).read_bytes();m=json.loads(raw)
    require(m["schema"]=="mainchip-route-audit-only-recovery-v1","recovery method schema")
    require(m["historical_source"]==evidence.SOURCE and m["historical_run"]==evidence.RUN
      and m["historical_method_sha256"]==evidence.METHOD_SHA,"historical source binding")
    for key in ("source_controls_authorized","native_restore_authorized","native_audit_authorized",*FALSE_FLAGS):
        require(type(m[key])is bool,"typed recovery authority: "+key)
    require(all(m[k]is False for k in FALSE_FLAGS),"no reroute or acceptance")
    require(m["native_restore_authorized"]==m["native_audit_authorized"]
      and (not m["native_audit_authorized"]or m["source_controls_authorized"]),"split recovery authority")
    require(m["modes"]==list(MODES) and m["audit_phases"]==list(old.PHASES[1:])
      and m["audit_limits"]==old.stage_limits("audit") and m["phase_seconds"]==1200,
      "original audit phases/budgets")
    require(m["engine"]==old.ENGINE and m["input"]==old.INPUT
      and m["image"]==old.IMAGE and m["image_id"]==old.IMAGE_ID,"unchanged actual ELF/runtime")
    require(m["inherited_original_protected_count"]==687
      and all(m["protected"].get(p)==h for p,h in original["old_method"]["protected"].items()),
      "original687 protected source changed")
    for p,h in m["protected"].items():
        require(type(h)is str and re.fullmatch("[0-9a-f]{64}",h)
          and evidence.sha(old.secure_file(root,p))==h,"changed recovery source: "+p)
    return m


def group(mode,stage="audit"):
    require(type(mode)is str and mode in MODES and stage=="audit","audit-only group")
    return GROUP+"-"+mode


def context(env):
    require(env.get("GITHUB_ACTIONS")=="true"and env.get("RUNNER_OS")=="Linux","hosted Linux only")
    require(env.get("GITHUB_REPOSITORY")==old.REPOSITORY and env.get("GITHUB_EVENT_NAME")=="workflow_dispatch",
      "manual repository identity")
    require(env.get("GITHUB_REF")=="refs/heads/"+BRANCH and env.get("GITHUB_RUN_ATTEMPT")=="1",
      "recovery branch/first attempt")
    require(re.fullmatch("[0-9a-f]{40}",env.get("GITHUB_SHA",""))is not None
      and re.fullmatch("[1-9][0-9]*",env.get("GITHUB_RUN_ID",""))is not None,"new source/run identity")
    mode=env.get("NSSOC_RECOVERY_MODE")
    require(type(mode)is str and mode in MODES,"recovery mode")
    require(env["GITHUB_SHA"]!=evidence.SOURCE and int(env["GITHUB_RUN_ID"])!=evidence.RUN,
      "historical and current execution must differ")
    token=env["GITHUB_RUN_ID"]+"-1"
    return dict(source=env["GITHUB_SHA"],run_id=int(env["GITHUB_RUN_ID"]),attempt=1,
      mode=mode,stage="audit",token=token,name="nssoc-witness-build-"+token,
      branch=BRANCH,group=group(mode),historical_source=evidence.SOURCE,historical_run=evidence.RUN)


def validate_context(ctx):
    env=dict(GITHUB_ACTIONS="true",RUNNER_OS="Linux",GITHUB_REPOSITORY=old.REPOSITORY,
      GITHUB_EVENT_NAME="workflow_dispatch",GITHUB_REF="refs/heads/"+BRANCH,GITHUB_RUN_ATTEMPT="1",
      GITHUB_SHA=ctx["source"],GITHUB_RUN_ID=str(ctx["run_id"]),NSSOC_RECOVERY_MODE=ctx["mode"])
    require(type(ctx["run_id"])is int and type(ctx["attempt"])is int
      and canonical(ctx)==canonical(context(env)),"typed new host context")
    return ctx


def authorize(ctx):
    validate_context(ctx);m=source_guard()
    require(m["native_audit_authorized"]is True and m["native_restore_authorized"]is True,
      "new recovery native authority disabled")
    require(subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==ctx["source"],
      "recovery checkout identity")
    proof=json.loads(old.secure_file(ROOT,CONTROLS).read_bytes())
    require(proof["status"]=="PASS_AUDIT_RECOVERY_SOURCE_CONTROLS"
      and proof["source"]==ctx["source"]and type(proof["run_id"])is int and proof["run_id"]==ctx["run_id"]
      and proof["attempt"]==1 and proof["method_sha256"]==evidence.sha(ROOT/METHOD),
      "actual current-source recovery controls required")
    return m


def old_context(mode):
    return evidence.expected_case(mode)["old_audit_context"]
