#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Original loaded-result predicates with the exact new saved-capsule inventory."""
import ast,hashlib,json,os
import cdr_drain_m1_loaded_admission as a

ORIGINAL="scripts/cloud_cdr_v59_loaded_stage.py"
ORIGINAL_SHA="8a73b595e6e84c0e92020edcc62d618c07463b0819f20096f2d6122763e9107b"
OLD_INVENTORY="dict(files=5549,all_hashes_unchanged=True)"
NEW_INVENTORY="dict(files=2680,all_hashes_unchanged=True,exact_inventory=True)"
PREPARATION_PASS="PASS_PD500_LOADED_PREPARATION_AND13_BINDING_CONTROLS_NO_TRANSIENT"
CASE_PASS="PASS_WHOLE_MIM_PD500_LOADED_SCREEN_NOT_CLOSED_LOOP_OR_PHY_SIGNOFF"

def validator():
    path=a.regular(a.ROOT,ORIGINAL)
    a.require(a.sha(path)==ORIGINAL_SHA,"Original loaded stage changed")
    text=path.read_text()
    nodes=[n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)and n.name=="validate_result"]
    a.require(len(nodes)==1,"Original loaded result validator missing")
    original=ast.get_source_segment(text,nodes[0])
    a.require(original.count(OLD_INVENTORY)==1,"Original loaded inventory predicate changed")
    derived=original.replace(OLD_INVENTORY,NEW_INVENTORY)
    a.require(derived.count(NEW_INVENTORY)==1 and derived.replace(NEW_INVENTORY,OLD_INVENTORY)==original,
      "Loaded validator inventory derivation is not exact")
    scope={"os":os}
    exec(compile(derived,str(path)+"::current2680","exec"),scope)
    return scope["validate_result"],{
      "original_source":ORIGINAL,"original_source_sha256":ORIGINAL_SHA,
      "original_function_sha256":hashlib.sha256(original.encode()).hexdigest(),
      "derived_function_sha256":hashlib.sha256(derived.encode()).hexdigest(),
      "only_substitution":{"before":OLD_INVENTORY,"after":NEW_INVENTORY}}

def validate(report,case,prepare,code,prepared=None):
    a.require(case in a.CASES and type(prepare)is bool and(not prepare or case=="nominal_early"),
      "Invalid original loaded case mode")
    original,derivation=validator();original(report,case,prepare,code)
    a.require(report["terminal_finalization_complete"]is True and report["terminal_inventory_complete"]is True
      and not report["terminal_errors"],"Loaded worker terminal evidence incomplete")
    actions=report["terminal_actions"]
    a.require([x["action"]for x in actions]==["protected_sources","complete_saved_inputs",
      "preserve_preexisting_atomic_fragment","complete_output_inventory"]and all(x["completed"]is True for x in actions),
      "Loaded worker terminal action set changed")
    a.require(report["terminal_save_attempted"]is True and report["active_primary_exception_before_terminal"]is None,
      "Loaded worker has a terminal primary failure")
    d=a.source_guard();full=a.full_map(d)
    remote=a.validate_live(d["run.json"],d["jobs.json"],d["release.json"],d["tag-ref.json"],d)
    proof=report["composition_source"]
    expected={k:v for k,v in a.composition_proof(d,None,remote).items()if k!="full_archive"}
    a.exact({k:v for k,v in proof.items()if k!="full_archive"},expected,
      "Loaded current width/graph/RC provenance changed")
    # The raw result is a capsule member; the separately authenticated direct
    # summary adds publication-driver.log and cannot substitute for that member.
    a.require(a.RAW_SHA!=a.SUMMARY_SHA and full["result.json"]==a.RAW_SHA
      and full[a.MODEL_MEMBER]==a.MODEL_SHA and full[a.PLANES_MEMBER]==a.PLANES_SHA,
      "Loaded exact raw result/model/planes changed")
    archive=proof["full_archive"]
    a.require(type(archive["regular_members"])is int and archive["regular_members"]==2680
      and archive["full_inventory_verified"]is True,"Loaded complete archive proof changed")
    a.exact({name:row["sha256"]for name,row in archive["complete_member_hashes"].items()},full,
      "Loaded complete archive proof changed")
    plane=report["native_plane_source"]
    a.exact(plane,a.plane_proof(d),
      "Loaded current plane/model binding changed")
    interface=d["direct/composition.json"]["interface"]
    external={name:"0"if name in ("avss","sub","wire_cref")else name for name in interface}
    a.require(report["binding"]["interface"]==external and report["binding"]["ports"]==[external[name]for name in interface],
      "Loaded current ordered interface changed")
    if not prepare:
        a.require(type(prepared)is dict,"Same-run preparation report required")
        validate(prepared,"nominal_early",True,0)
        a.require(prepared["composition_source"]["summary_sha256"]==proof["summary_sha256"]
          and prepared["composition_source"]["stage_sha256"]==proof["stage_sha256"]
          and prepared["composition_source"]["raw_result_sha256"]==proof["raw_result_sha256"]
          and prepared["native_plane_source"]==plane,"Preparation/current composition differs")
        a.require(report["vectors"]==prepared["vectors"]and report["vector_census"]==prepared["vector_census"],
          "Original acquired preparation vector census changed")
        a.require(report["native_save_commands"]==prepared["native_save_commands"],"Original native save command order changed")
    return {"original_validator_derivation":derivation,"all_original_electrical_predicates_retained":True,
      "complete_current_members":2680,"acquired_vectors":report["vector_census"],
      "original_status":report["status"],"case":case,"preparation_only":prepare,
      "fresh_RC_run":a.RUN,"fresh_RC_source":a.HEAD,"raw_result_sha256":a.RAW_SHA,
      "publication_summary_sha256":a.SUMMARY_SHA,"current_width_run":41000358737,"current_graph_run":41003747027,"accepted":False,"full_phy_accepted":False}
