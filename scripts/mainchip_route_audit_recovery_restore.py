#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Restore authentic failed-publication handoffs without rewriting old context."""
import copy
import os
from pathlib import Path
from types import FunctionType
import mainchip_route_audit_recovery_contract as a
import mainchip_route_recovery_evidence as evidence
import mainchip_built_engine_route_tail_handoff as h
import mainchip_built_engine_route_tail_contract as c
import wait_cloud_tested_source_release as reservation
from mainchip_witness_engine_build import fingerprint


def historical_live(read,old_ctx,old_env,host_ctx):
    a.validate_context(host_ctx)
    mode=host_ctx["mode"];saved=evidence.expected_case(mode)
    c.require(a.canonical(old_ctx)==a.canonical(saved["old_audit_context"])
      and type(old_ctx["run_id"])is int and old_env=={"GITHUB_RUN_ID":str(evidence.RUN)},
      "exact isolated historical restore context")
    rid=saved["release"]["release_id"];tag=saved["release"]["tag"]
    run=read("actions/runs/"+str(evidence.RUN))
    jobs=read("actions/runs/"+str(evidence.RUN)+"/attempts/1/jobs?per_page=100")
    release=read("releases/"+str(rid));ref=read("git/ref/tags/"+tag)
    live=evidence.validate_live(mode,run,jobs,release,ref)
    job=next(j for j in jobs["jobs"]if j["id"]==saved["original_job"]["id"])
    lineage=dict(run_id=evidence.RUN,source=evidence.SOURCE,mode=mode,route_job=job,
      route_release_id=rid,route_tag=tag,route_assets=[dict(id=r["id"],name=r["name"],bytes=r["size"],digest=r["digest"])
        for r in release["assets"]],authenticated_complete_route=False,
      original_run_conclusion="failure",original_route_job_conclusion="failure",
      original_audit_jobs_conclusion="skipped",original_audits_succeeded=False,
      original_failure="HTTP400_Bad_Content_Length_zero_byte_stderr",
      successful_original_route_and_freeze=True,new_host_context=copy.deepcopy(host_ctx),
      future_audits_are_new_execution=True,live_metadata_status=live["status"],
      old_context=copy.deepcopy(old_ctx),physical_acceptance=False)
    return release,lineage


def cloned_restore(host_ctx,read):
    """One global substitution; original restore bytecode/body remains unchanged."""
    a.validate_context(host_ctx)
    def live(reader,ctx,env):return historical_live(reader,ctx,env,host_ctx)
    namespace=dict(h.restore.__globals__);namespace["live_route"]=live
    return FunctionType(h.restore.__code__,namespace,h.restore.__name__,h.restore.__defaults__,h.restore.__closure__)


def restore(work,out,root,host_ctx,env,read=None,fetch=None):
    a.validate_context(host_ctx);a.source_guard(root)
    c.require(a.canonical(a.context(env))==a.canonical(host_ctx),"current host envelope changed")
    saved=evidence.expected_case(host_ctx["mode"])
    read=reservation.release.api if read is None else read
    c.atomic_record(Path(out)/"recovery-host-context.json",host_ctx)
    c.atomic_record(Path(out)/"recovery-admission.json",dict(
      new_host_context=host_ctx,old_context=saved["old_audit_context"],
      original_run=saved["original_run"],original_job=saved["original_job"],
      old_method=saved["old_method"],expected_outer_files=saved["outer_expected_files"],
      expected_handoff_files=saved["handoff_inventory"]["files"],
      original_frozen_inventory=saved["original_frozen_inventory"],
      archive_metadata_only=True,new_native_member_bytes_verified=False,physical_acceptance=False))
    call=cloned_restore(host_ctx,read)
    c.require(call.__code__ is h.restore.__code__,"changed old restore body")
    # Only this function-call environment uses old run identity; os.environ is not changed.
    lineage=call(work,out,root,copy.deepcopy(saved["old_audit_context"]),
      {"GITHUB_RUN_ID":str(evidence.RUN)},read=read,fetch=fetch)
    projection=c.decode(c.secure_file(work,"route-projection.json").read_bytes())
    c.require(projection=={"files":saved["canonical_projection"]},"recovered complete canonical projection")
    original=c.decode(c.secure_file(work,"frozen-manifest.json").read_bytes())
    c.require(original==saved["original_frozen_inventory"],"recovered original746 input map")
    c.frozen_unchanged(work,projection)
    c.require(lineage["authenticated_complete_route"]is True
      and lineage["source"]==evidence.SOURCE and lineage["run_id"]==evidence.RUN
      and a.canonical(lineage["new_host_context"])==a.canonical(host_ctx),"restored old/new lineage")
    c.atomic_record(Path(out)/"recovery-restoration.json",dict(
      new_host_context=host_ctx,frozen_native_context=saved["old_audit_context"],
      old_run_conclusion="failure",old_job_conclusion="failure",old_audits_succeeded=False,
      complete_outer_members=len(saved["outer_expected_files"]),
      complete_nested_members=len(saved["handoff_inventory"]["files"]),
      canonical_projection_members=len(saved["canonical_projection"]),
      original_frozen_members=746,original_source_protected_members=687,
      complete_original_native_member_bytes_verified=True,rerouting_performed=False,
      original_execution_method_sha256=evidence.METHOD_SHA,
      actual_restoration=fingerprint(c.secure_file(out,"route-restoration.json")),
      physical_acceptance=False))
    return lineage
