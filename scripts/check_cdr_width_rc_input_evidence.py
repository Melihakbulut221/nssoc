#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted source-only tests for width proof/current RC input joins."""
import argparse
import copy
import json
import os
from pathlib import Path
from unittest.mock import patch
import cdr_width_rc_input_evidence as e


def require(value,message):
    if not value:raise AssertionError(message)


def reject(name,fn,reason,rows):
    try:fn()
    except AssertionError as error:
        require(error.args==(reason,),(name,"wrong refusal",error.args,reason))
        rows.append(dict(name=name,reason=reason))
    else:raise AssertionError((name,"accepted invalid evidence"))


def change(data,path,value):
    for key in path[:-1]:data=data[key]
    data[path[-1]]=value


def controls():
    positive=[];refusals=[]
    original=e.source_guard()
    require(original["execution_authorized"]is original["historical_method_authority_reused"]is False,
      "Source guard borrowed authority")
    positive.append("complete_original1085_source_and17_proof_documents")
    result=e.validate_saved()
    require(result["status"]=="PASS_WIDTH_NATIVE_PROOF_BOUND_TO_ORIGINAL_GRAPH_FOR_FUTURE_RC"
      and len(result["complete_graph_files"])==4103 and len(result["original_files"])==605
      and len(result["current_files"])==75 and len(result["current_binding_files"])==6,
      "Incomplete actual positive join")
    require(result["current_root_result_must_not_be_fabricated"]is True
      and result["topology_direct_summary_is_not_archive_raw_result"]is True
      and result["native_proof_archive_is_not_geometry_input"]is True,
      "Archive/projection distinction lost")
    require(result["canonical_analysis_path"]==
      "/home/runner/work/nssoc/nssoc/hw/soc/out/cloud-cdr-v59-selector-column-width-graph/candidate",
      "Original absolute binding paths changed")
    for name in ("execution_authorized","archive_acquired","extraction_executed","simulation_executed",
      "historical_authority_reused","physical_accepted","electrical_accepted","qualified_pex","full_phy_accepted"):
        require(result[name]is False,"Borrowed acceptance: "+name)
    positive.append("actual_saved_width_graph_binding_4103_605_75_six_inputs")
    d=original["topology"];g=original["graph"]
    topology_metadata=dict(run=d["run.json"],jobs=d["jobs.json"],release=d["release.json"],tag=d["tag.json"])
    graph_metadata={k:g["tag"if k=="ref"else k]for k in ("run","jobs","release","ref")}
    live=e.validate_live(topology_metadata,graph_metadata)
    require(live["saved"]==result and live["execution_authorized"]is False
      and live["topology_live"]["run_id"]==40815684037 and live["graph_live"]["run_id"]==40808550817,
      "Actual complete live metadata join differs")
    positive.append("both_complete_original_live_run_job_release_bindings")
    with patch.object(e,"source_guard",return_value=original):
        require(e.validate_saved()==result,"Authenticated cached metadata differs")
    positive.append("unchanged_authenticated_metadata_cache")
    # Every semantic fault is a synthetic copy. The production qualify function
    # and original graph evidence map validators remain unchanged.
    cases=[
      ("borrowed_RC",["receipt","fresh_RC_executed"],True,"Borrowed RC or broader acceptance"),
      ("raw_result_alias",["receipt","archive_terminal_result_is_not_direct_summary_bytes"],False,"Borrowed RC or broader acceptance"),
      ("wrong_graph_lineage",["topology","summary.json","source_graph_run"],40808550818,"Width and graph source lineage changed"),
      ("new_source_as_old",["topology","summary.json","source_head"],"0"*40,"Width and graph source lineage changed"),
      ("unfinished_terminal",["topology","summary.json","terminal_finalization_complete"],False,"Incomplete width topology terminal"),
      ("borrowed_electrical",["topology","summary.json","electrical_accepted"],True,"Width proof scope changed"),
      ("changed_candidate",["topology","summary.json","candidate_gds_sha256"],"0"*64,"Wrong actual consumed graph"),
      ("failed_command",["topology","summary.json","commands",2,"returncode"],1,"Incomplete native topology command"),
      ("cleanup_live",["topology","summary.json","terminal_evidence","owned_process_cleanup","remaining_live"],[42],"Incomplete original process or source integrity"),
      ("incomplete_sources",["topology","summary.json","terminal_evidence","protected_source_integrity","protected_files"],1084,"Incomplete original process or source integrity"),
      ("changed_reservation",["topology","summary.json","reservation","tested_source"],"0"*40,"Wrong original topology reservation"),
      ("root_hash_changed",["topology","expected-roots.json","fresh","parent/layout/schematic.cir"],"0"*64,"Width root maps differ from original graph"),
      ("graph_member_changed",["topology","summary.json","outputs","graph-input/candidate/parent/layout/schematic.cir"],"0"*64,"Original complete graph changed in topology archive"),
      ("native_fault_count",["topology","native-controls.json","positive_complete_comparisons"],1,"Incomplete actual native fault controls"),
      ("identity_mutated",["topology","native-controls.json","identity_controls","saved_native_inputs_mutated"],True,"Incomplete original acquired identity controls"),
      ("synthetic_claims_actual",["topology","native-synthetic.json","actual_saved_candidate_read"],True,"Incomplete native synthetic controls"),
      ("wrong_contract",["topology","native-controls.json","comparison","contract_sha256"],"0"*64,"Wrong exact width comparison"),
      ("remap_native_ids",["topology","native-controls.json","comparison","native_device_ids_not_remapped"],False,"Changed native identity policy"),
      ("native_map_hash",["topology","native-controls.json","comparison","inputs","fresh","files","parent/layout/schematic.cir"],"0"*64,"Native proof is not bound to complete current graph map"),
      ("missing_device",["topology","native-controls.json","comparison","identity","devices"],499,"Incomplete native identity census"),
      ("changed_owner_layers",["topology","native-controls.json","comparison","owned_union","checked_component_layers"],1468,"Incomplete material ownership proof"),
      ("borrowed_comparison_acceptance",["topology","native-controls.json","comparison","electrical_accepted"],True,"Borrowed acceptance from topology comparison"),
      ("empty_bytes_replaced",["topology","direct-publication-plan.json","empty_bytes_replaced"],True,"Changed complete publication scope"),
      ("summary_raw_alias",["topology","direct-publication-plan.json","summary_sha256"],"0"*64,"Publication report hashes changed"),
      ("direct_asset_hash",["topology","direct-publication-plan.json","files",0,"sha256"],"0"*64,"Direct proof not bound to full output map"),
      ("candidate_proof_hash",["topology","summary.json","candidate","native_controls_sha256"],"0"*64,"Candidate actual proof hashes changed"),
      ("archive_hash",["topology","parts.json","sha256"],"0"*64,"Wrong topology archive record"),
      ("source_tests_failed",["topology","source-controls-result.json","failures"],1,"Incomplete actual source qualification"),
    ]
    for name,path,value,reason in cases:
        changed=copy.deepcopy(original);change(changed,path,value)
        require(e.digest(changed)!=e.digest(original),name+" no-op")
        with patch.object(e,"source_guard",return_value=changed):
            reject(name,e.validate_saved,reason,refusals)
    mutations=[
      ("wrong_live_source",["run","head_sha"],"0"*40,"Wrong completed native topology run"),
      ("wrong_live_run",["run","id"],1,"Wrong completed native topology run"),
      ("bool_live_attempt",["run","run_attempt"],True,"Untyped topology run identity"),
      ("failed_live_run",["run","conclusion"],"failure","Wrong completed native topology run"),
      ("failed_live_job",["jobs","jobs",0,"conclusion"],"failure","Incomplete native topology job"),
      ("changed_live_asset",["release","assets",0,"digest"],"sha256:"+"0"*64,"Topology release identity changed"),
      ("bool_live_asset",["release","assets",0,"size"],True,"Malformed topology asset"),
      ("changed_live_tag",["tag","object","sha"],"0"*40,"Wrong topology lightweight source tag"),
    ]
    for name,path,value,reason in mutations:
        mutated=copy.deepcopy(topology_metadata);change(mutated,path,value)
        reject(name,lambda:e.live_topology(**mutated,saved=d),reason,refusals)
    require(len(positive)==4 and len(refusals)==36,"Changed source control census")
    require(e.validate_saved()==result,"Source controls altered original authenticated evidence")
    return dict(schema="cdr-width-rc-input-evidence-controls-v1",
      status="PASS_READ_ONLY_WIDTH_RC_INPUT_EVIDENCE_CONTROLS",positives=positive,refusals=refusals,
      positive_count=len(positive),refusal_count=len(refusals),complete_original_sources=1085,
      complete_graph_members=4103,original_members=605,current_members=75,current_binding_files=6,
      original_source=e.HEAD,original_run=e.RUN,current_source=os.environ.get("GITHUB_SHA"),
      current_run=os.environ.get("GITHUB_RUN_ID"),current_attempt=os.environ.get("GITHUB_RUN_ATTEMPT"),
      metadata_only=True,synthetic_mutations=True,actual_original_metadata=True,
      original_source_and_proof_bytes_unchanged=True,native_execution=False,archive_acquired=False,
      extraction_executed=False,simulation_executed=False,full_phy_accepted=False)


def main():
    p=argparse.ArgumentParser();p.add_argument("--output",required=True);args=p.parse_args()
    result=dict(schema="cdr-width-rc-input-evidence-controls-v1",status="RUNNING",
      current_source=os.environ.get("GITHUB_SHA"),current_run=os.environ.get("GITHUB_RUN_ID"))
    try:result=controls()
    except BaseException as error:
        result.update(status="FAIL",error_type=type(error).__name__,error=repr(error));raise
    finally:
        raw=(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
        Path(args.output).write_bytes(raw);print(raw.decode(),end="")


if __name__=="__main__":main()
