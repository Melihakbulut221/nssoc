#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Join actual width topology proof to the exact saved graph for future fresh RC.

Read-only evidence API. Historical comparison authority is not new authority.
No network, native archive acquisition, extraction, simulation or source mutation.
"""
import hashlib
import json
import re
from pathlib import Path
import cdr_width_graph_evidence as graph

ROOT=Path(__file__).resolve().parents[1]
PREFIX="docs/evidence/cdr-width-topology-native-terminal-20261029."
RECEIPT=PREFIX+"receipt.json"
RECEIPT_RECORD=dict(bytes=4864,sha256="0fdcd4f01a12b1add058f51a624a02e3fe46c34e79bd76e14b1a59fa22a11c67")
METHOD="scripts/cdr-selector-width-topology-methods.json"
METHOD_RECORD=dict(bytes=160228,sha256="8b928cad1642ccc3bca4b03884e013ff9d4cd12d41d66ac563fb190ddbb83027")
GRAPH_SOURCE_SHA="8d44abc419a5b163254098a2b27032744244c194abbd0127bf576e938cc18b6b"
RUN=40815684037
HEAD="214ec651fd501de7e2f49a38509b184a1fd66f8d"
BRANCH="codex/cdr-width-native-topology"
WORKFLOW=".github/workflows/cdr-selector-width-topology-cloud.yml"
RELEASE=427455233
TAG="cloud-results-40815684037-1-cdr-selector-width-topology"
STEM="cdr-selector-width-topology-40815684037-1."
DOCUMENTS=("direct-publication-plan.json","driver.log","expected-roots.json","jobs.json",
 "native-controls.json","native-job.log","native-synthetic.json","parts.json","release.json",
 "restore.json","run.json","runtime.json","source-controls-job.log","source-controls-result.json",
 "summary.json","tag.json")
JOBS={123256070161:"source-controls",123256248814:"topology"}
FALSE=("physical_accepted","electrical_accepted","qualified_pex","full_phy_accepted",
 "simulation_executed","automatic_retry")
BINDING_FILES=("wire/device-locations01.json","parent/layout/result.json","parent/layout/schematic.cir",
 "parent/physical/lvs_flat/extracted.cir","parent/physical/lvs_flat/audit.json",
 "parent/physical/lvs_flat/result.lvsdb")
ACTIONS=("owned_process_cleanup","stop_heartbeat","join_heartbeat","restore_signal_2",
 "restore_signal_15","terminal_resource_sample","protected_source_integrity",
 "complete_saved_input_integrity","complete_output_inventory")
COMMANDS=("restore-complete-graph-capsule","native-synthetic-controls","actual-native-comparison-and-faults")


def require(value,message):
    if not value:raise AssertionError(message)


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def record(raw):
    return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def regular(name):
    return graph.regular(ROOT,graph.member(name))


def source_guard():
    require(Path(graph.__file__).resolve()==ROOT/"scripts/cdr_width_graph_evidence.py"
      and graph.sha(regular("scripts/cdr_width_graph_evidence.py"))==GRAPH_SOURCE_SHA,
      "Changed original graph evidence implementation")
    method_raw=regular(METHOD).read_bytes()
    require(record(method_raw)==METHOD_RECORD,"Changed historical topology method")
    method=json.loads(method_raw)
    require(method["schema"]=="cdr-selector-width-topology-v1"
      and len(method["protected_sha256"])==1085,"Wrong historical method closure")
    for name,h in method["protected_sha256"].items():
        require(type(h)is str and re.fullmatch("[0-9a-f]{64}",h)
          and graph.sha(regular(name))==h,"Changed historical source: "+name)
    raw=regular(RECEIPT).read_bytes()
    require(record(raw)==RECEIPT_RECORD,"Changed width proof receipt")
    receipt=json.loads(raw)
    require(set(receipt["files"])=={PREFIX+n for n in DOCUMENTS},"Incomplete width proof document map")
    docs={}
    for name in DOCUMENTS:
        raw=regular(PREFIX+name).read_bytes()
        require(record(raw)==receipt["files"][PREFIX+name],"Changed complete width proof: "+name)
        docs[name]=raw.decode("utf-8")if name.endswith(".log")else json.loads(raw)
    return dict(receipt=receipt,topology=docs,graph=graph.source_guard(),
      historical_method_authority_reused=False,execution_authorized=False)


def asset_map(release):
    rows=release["assets"]
    require(type(rows)is list and len(rows)==11
      and len({r["id"]for r in rows})==len({r["name"]for r in rows})==11,
      "Incomplete topology release asset set")
    result={}
    for row in rows:
        require(type(row["id"])is int and type(row["size"])is int and row["size"]>0
          and row["state"]=="uploaded"and re.fullmatch("sha256:[0-9a-f]{64}",row["digest"]),
          "Malformed topology asset")
        result[graph.member(row["name"])]=dict(id=row["id"],bytes=row["size"],sha256=row["digest"][7:])
    return result


def live_topology(run,jobs,release,tag,saved):
    require(type(run["id"])is int and type(run["run_attempt"])is int,
      "Untyped topology run identity")
    require((run["id"],run["head_sha"],run["head_branch"],run["run_attempt"],run["event"],
      run["path"],run["status"],run["conclusion"])==
      (RUN,HEAD,BRANCH,1,"workflow_dispatch",WORKFLOW,"completed","success"),
      "Wrong completed native topology run")
    require(type(jobs["total_count"])is int and jobs["total_count"]==len(jobs["jobs"])==2
      and {j["id"]for j in jobs["jobs"]}==set(JOBS),"Wrong complete topology jobs")
    for job in jobs["jobs"]:
        require(type(job["id"])is int and type(job["run_id"])is int and type(job["run_attempt"])is int
          and job["name"]==JOBS[job["id"]]and job["run_id"]==RUN and job["run_attempt"]==1
          and job["head_sha"]==HEAD and job["head_branch"]==BRANCH
          and job["status"]=="completed"and job["conclusion"]=="success",
          "Incomplete native topology job")
        require(all(s["status"]=="completed"and s["conclusion"]=="success"for s in job["steps"]),
          "Topology job step failed")
        original=next(j for j in saved["jobs.json"]["jobs"]if j["id"]==job["id"])
        fields=("number","name","status","conclusion")
        require([{k:s[k]for k in fields}for s in job["steps"]]==
          [{k:s[k]for k in fields}for s in original["steps"]],"Topology job steps changed")
    require(type(release["id"])is int and release["id"]==RELEASE and release["tag_name"]==TAG
      and release["target_commitish"]==HEAD and release["draft"]is False and release["prerelease"]is True,
      "Wrong topology release")
    require(tag["ref"]=="refs/tags/"+TAG and tag["object"]["type"]=="commit"
      and tag["object"]["sha"]==HEAD,"Wrong topology lightweight source tag")
    assets=asset_map(release)
    require(assets==asset_map(saved["release.json"]),"Topology release identity changed")
    return dict(run_id=RUN,source_head=HEAD,release_id=RELEASE,tag=TAG,assets=assets,
      original_native_proof_passed=True,execution_authorized=False)


def hash_map(value,count,message):
    require(type(value)is dict and len(value)==count,message)
    for name,h in value.items():
        graph.member(name)
        require(type(h)is str and re.fullmatch("[0-9a-f]{64}",h),message)
    return value


def complete_inventory(value,expected):
    require(type(value)is dict and set(value)==set(expected),"Incomplete saved full inventory")
    for name,row in value.items():
        require(type(row)is dict and set(row)=={"bytes","sha256"}and type(row["bytes"])is int
          and row["bytes"]>=0 and row["sha256"]==expected[name],"Changed saved full inventory member")


def qualify(data):
    """Join authenticated original bytes; no recreation of geometry or witness."""
    d=data["topology"];receipt=data["receipt"];s=d["summary.json"]
    full,roots=graph.maps(data["graph"])
    live=live_topology(d["run.json"],d["jobs.json"],d["release.json"],d["tag.json"],d)
    require(receipt["schema"]=="width-native-topology-actual-terminal-v1"
      and receipt["run_id"]==RUN and receipt["source"]==HEAD and receipt["release_id"]==RELEASE
      and receipt["actual_native_width_specific_proof_passed"]is True,
      "Wrong actual width proof receipt scope")
    require(receipt["archive_terminal_result_is_not_direct_summary_bytes"]is True
      and receipt["fresh_RC_executed"]is receipt["electrical_accepted"]is receipt["qualified_pex"]is
      receipt["full_phy_accepted"]is receipt["graph_equivalence_accepted"]is False,
      "Borrowed RC or broader acceptance")
    require((s["source_head"],s["run_id"],s["run_attempt"],s["source_graph_head"],s["source_graph_run"])==
      (HEAD,RUN,1,graph.HEAD,graph.RUN),"Width and graph source lineage changed")
    require(type(s["run_id"])is int and type(s["run_attempt"])is int
      and s["status"]=="PASS_WIDTH_TOPOLOGY_REQUIRES_FRESH_RC_AND_ELECTRICAL"
      and s["native_width_comparison_passed"]is s["terminal_finalization_complete"]is s["topology_started"]is True,
      "Incomplete width topology terminal")
    require(all(s[k]is False for k in FALSE+("fresh_RC_executed","graph_equivalence_accepted",
      "native_DRC_executed","native_LVS_executed"))and s["original_failure_preserved"]is True,
      "Width proof scope changed")
    require(s["complete_input_members"]==4103 and s["consumed_view"]=="graph-input"
      and s["candidate_gds_sha256"]==graph.GDS_SHA,"Wrong actual consumed graph")
    require([c["label"]for c in s["commands"]]==list(COMMANDS),"Incomplete native command sequence")
    for command in s["commands"]:
        require(command["returncode"]==0 and command["supervision_failure"]is None
          and command["memory_read_error"]is None and command["process_group_cleanup"]["remaining_live"]==[]
          and command["maximum_group_rss_kib"]==10485760 and command["minimum_available_kib"]==2097152,
          "Incomplete native topology command")
    require([a["action"]for a in s["terminal_actions"]]==list(ACTIONS)
      and all(a["completed"]is True for a in s["terminal_actions"]),"Incomplete topology terminal cleanup")
    terminal=s["terminal_evidence"]
    require(terminal["owned_process_cleanup"]["remaining_live"]==[]
      and terminal["protected_source_integrity"]==dict(protected_files=1085),
      "Incomplete original process or source integrity")
    reservation=s["reservation"]
    require(reservation["release_id"]==RELEASE and reservation["tag"]==TAG
      and reservation["tested_source"]==HEAD and reservation["externally_reserved"]is True
      and reservation["target_verified"]is True and reservation["assets_overwritten"]is False,
      "Wrong original topology reservation")
    restore=d["restore.json"];view=restore["view"]
    require(s["restore"]==restore and s["candidate"]["view"]==view
      and terminal["complete_saved_input_integrity"]==view,"Original saved graph views differ")
    require(view["status"]=="PASS_EXACT_SAVED_GRAPH_EVIDENCE_JOINS_ONLY"
      and view["complete_members"]==4103 and view["inventory_sha256"]==digest(full)
      and view["original_report_bytes_unchanged"]is True,"Incomplete restored graph proof")
    complete_inventory(view["complete_member_hashes"],full)
    complete_inventory(restore["extracted"]["complete_member_hashes"],full)
    require(restore["extracted"]["regular_members"]==4103
      and restore["extracted"]["full_inventory_verified"]is True
      and restore["complete_original_capsule_retained"]is restore["original_release_unmodified"]is True,
      "Incomplete native input restoration")
    require(d["expected-roots.json"]==roots,"Width root maps differ from original graph")
    outputs=hash_map(s["outputs"],4124,"Incomplete topology output map")
    require({n[len("graph-input/"):]:h for n,h in outputs.items()if n.startswith("graph-input/")}==full,
      "Original complete graph changed in topology archive")
    native=d["native-controls.json"];synthetic=d["native-synthetic.json"];comparison=native["comparison"]
    require(native["status"]=="PASS_ACTUAL_WIDTH_NATIVE_FAULT_CONTROLS"
      and native["positive_complete_comparisons"]==2 and len(native["native_refusals"])==9
      and native["native_original_inputs_unchanged"]is True,"Incomplete actual native fault controls")
    ident=native["identity_controls"]
    require(ident["status"]=="PASS_COMPLETE_ACQUIRED_WITNESS_MUTATION_CONTROLS"
      and ident["positive_copies"]==12 and len(ident["refusals"])==12
      and ident["saved_native_inputs_mutated"]is False,"Incomplete original acquired identity controls")
    require((synthetic["status"],synthetic["positive_cases"],synthetic["rejected_cases"])==
      ("PASS_WIDTH_TOPOLOGY_SYNTHETIC_CONTROLS",3,20)
      and synthetic["actual_pya_geometry_functions_exercised"]is True
      and synthetic["actual_saved_candidate_read"]is False,"Incomplete native synthetic controls")
    require(comparison["status"]=="PASS_WIDTH_SPECIFIC_NATIVE_IDENTITY_EXACT_UNION_AND_OWNERSHIP"
      and comparison["scope"]=="READ_ONLY_WIDTH_COMPARISON_ONLY"
      and comparison["contract_sha256"]=="cc92ad1c6368219f4df0faf4989e7b2a77a1dab92898f4c92c6a69e4ead67106",
      "Wrong exact width comparison")
    require(comparison["original_topology_comparator_modified"]is False
      and comparison["old_tail_bus_policy_used_for_acceptance"]is False
      and comparison["native_device_ids_not_remapped"]is comparison["raw_public_pin_order_retained"]is True,
      "Changed native identity policy")
    for side,table in roots.items():
        require(comparison["inputs"][side]==dict(member_count=len(table),inventory_sha256=digest(table),files=table),
          "Native proof is not bound to complete current graph map")
    identity=comparison["identity"]
    require({k:identity[k]for k in ("devices","terminals","native_nets","ports","anchors")}==
      dict(devices=500,terminals=1446,native_nets=238,ports=25,anchors=978),
      "Incomplete native identity census")
    require(identity["native_port_ids_preserved_as_evidence_not_assumed_equal"]is True
      and identity["all_levels_and_instance_ordinals_and_transforms_equal"]is True
      and identity["topology_comparator_modified"]is False,"Native identity evidence changed")
    geometry=comparison["geometry"];owned=comparison["owned_union"]
    require(len(geometry["typed_additions"])==26 and len(geometry["placed_additions"])==52
      and geometry["original_raw_multiplicity_text_properties_hierarchy_preserved"]is True,
      "Incomplete native width geometry proof")
    require(owned["component_count"]==113 and owned["checked_component_layers"]==len(owned["rows"])==1469
      and len(owned["changed"])==8,"Incomplete material ownership proof")
    for report in (native,synthetic,comparison):
        require(all(report[k]is False for k in FALSE),"Borrowed acceptance from topology comparison")
    for side,key in (("old","original_acquired_witness"),("fresh","fresh_acquired_witness")):
        witness=comparison[key]
        require(len(witness["full_inventory"])==4928 and len(witness["paths"])==500
          and len(witness["native_pins"])==25,"Incomplete original acquired witness")
    plan=d["direct-publication-plan.json"]
    require(plan["schema"]=="complete-archive-direct-publication-v1"
      and plan["empty_bytes_replaced"]is False and plan["zero_byte_files_preserved_in_archive"]is True,
      "Changed complete publication scope")
    proof=receipt["files"]
    require(plan["summary_sha256"]==proof[PREFIX+"summary.json"]["sha256"]
      and plan["parts_sha256"]==proof[PREFIX+"parts.json"]["sha256"],"Publication report hashes changed")
    require({p["suffix"]for p in plan["files"]}==
      {"native-synthetic.json","native-controls.json","expected-roots.json","restore.json","runtime.json","driver.log"},
      "Incomplete direct publication plan")
    for item in plan["files"]:
        row=proof[PREFIX+item["suffix"]]
        require(row==dict(bytes=item["bytes"],sha256=item["sha256"])
          and item["disposition"]=="direct_and_archive"and outputs[item["member"]]==item["sha256"],
          "Direct proof not bound to full output map")
    require(s["candidate"]["native_controls_sha256"]==proof[PREFIX+"native-controls.json"]["sha256"]
      and s["candidate"]["synthetic_sha256"]==proof[PREFIX+"native-synthetic.json"]["sha256"],
      "Candidate actual proof hashes changed")
    parts=d["parts.json"]
    require(parts["source_directory"]=="cloud-cdr-selector-width-topology"and parts["bytes"]==758790884
      and parts["sha256"]=="077cfc732758b7264b989aacfb36d32c7ee88dd9aa2a744053d84ad56d1ee27f",
      "Wrong topology archive record")
    assets=live["assets"]
    for item in parts["parts"]:
        require(assets[item["name"]]["bytes"]==item["bytes"]
          and assets[item["name"]]["sha256"]==item["sha256"],"Native proof archive part changed")
    for name in ("summary.json","parts.json","direct-publication-plan.json",
      "native-synthetic.json","native-controls.json","expected-roots.json","restore.json","runtime.json","driver.log"):
        require({k:assets[STEM+name][k]for k in ("bytes","sha256")}==proof[PREFIX+name],
          "Published native proof report changed")
    controls=d["source-controls-result.json"]
    require(controls["status"]=="PASS_WIDTH_STAGE_SOURCE_CONTROLS_ONLY"
      and controls["tests"]==13 and controls["errors"]==controls["failures"]==0
      and controls["native_execution"]is False,"Incomplete actual source qualification")
    require(d["runtime.json"]==s["runtime_smoke"]and d["runtime.json"]["accepted"]is True
      and d["runtime.json"]["returncode"]==0 and d["runtime.json"]["cleanup"]["remaining_live"]==[],
      "Incomplete native runtime proof")
    current=roots["fresh"]
    require(all(n in current for n in BINDING_FILES),"Current binding input missing")
    require("result.json"not in current,"Unexpected synthetic current root result")
    return dict(status="PASS_WIDTH_NATIVE_PROOF_BOUND_TO_ORIGINAL_GRAPH_FOR_FUTURE_RC",
      graph_source=graph.HEAD,graph_run=graph.RUN,topology_source=HEAD,topology_run=RUN,
      complete_graph_files=full,current_files=current,original_files=roots["old"],
      current_binding_files={n:current[n]for n in BINDING_FILES},
      canonical_analysis_path=graph.PRODUCER_ROOT+graph.FRESH.rstrip("/"),
      original_reports_must_remain_byte_identical=True,current_root_result_must_not_be_fabricated=True,
      topology_direct_summary_is_not_archive_raw_result=True,
      native_proof_archive_is_not_geometry_input=True,metadata_only=True,
      historical_native_width_proof_passed=True,execution_authorized=False,
      archive_acquired=False,extraction_executed=False,simulation_executed=False,
      historical_authority_reused=False,physical_accepted=False,electrical_accepted=False,
      qualified_pex=False,full_phy_accepted=False)


def validate_saved():
    return qualify(source_guard())


def validate_live(topology_metadata,graph_metadata):
    data=source_guard()
    result=qualify(data)
    current=live_topology(**topology_metadata,saved=data["topology"])
    original=graph.validate_live(**graph_metadata)
    return dict(saved=result,topology_live=current,graph_live=original,
      execution_authorized=False,archive_acquired=False)


def validate_restored(root):
    result=validate_saved()
    before=graph.tree(Path(root))
    view=graph.validate_restored(Path(root))
    require({n:r["sha256"]for n,r in before.items()}==result["complete_graph_files"],
      "Restored graph differs from width-qualified graph")
    require(graph.tree(Path(root))==before,"Read-only RC admission mutated input")
    return dict(saved=result,view=view,execution_authorized=False,
      archive_acquired=False,extraction_executed=False,simulation_executed=False)
