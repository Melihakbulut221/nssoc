#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Joint immutable saved-geometry admission for fresh RC; all dispatch gates default off."""
import json
import os
from pathlib import Path,PurePosixPath
import re
import shutil
import cdr_v59_tail_saved_identity as frozen
import cdr_v59_tail_fresh_rc_semantic as semantic
import ensure_cloud_tested_source_release as release
from run_cloud_tx_layout_repair import fetch,sha

ROOT=Path(__file__).resolve().parents[1]
METHOD=ROOT/"scripts/cdr-v59-tail-fresh-rc-methods.json"
CONTRACT="docs/evidence/cdr-v59-tail-fresh-rc-admission-contract-20261027.json"
PREFIX="docs/evidence/cdr-v59-tail-typed-serialization-readback-terminal-20261027"
OUT=ROOT/"hw/soc/out/cloud-cdr-v59-tail-fresh-rc"
SCOPE="CURRENT_SAVED_TAIL_GEOMETRY_FRESH_500_BINDING_WIRE_RC_SEVEN_MIM_BOTH_ORDERS"
NATIVE_FLAGS=("native_execution_authorized","binding_authorized","wire_rc_authorized","mim_extraction_authorized","native_extraction_authorized")
ALWAYS_FALSE=("geometry_generation_authorized","simulation_authorized","accepted","physical_accepted",
              "electrical_accepted","qualified_pex","full_phy_accepted","automatic_retry")
CENSUS={"rppd":98,"cap_cmim":7,"npn13g2":124,"ptap1":221,"sg13_lv_nmos":50}

def require(value,message):
    if not value:raise AssertionError(message)

def read_json(path):
    return json.loads(path.read_bytes())

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n")
    tmp.replace(path)

def relative(name):
    require(isinstance(name,str) and name!="" and chr(92) not in name,"Invalid relative path")
    p=PurePosixPath(name)
    require(p.as_posix()==name and not p.is_absolute() and ".." not in p.parts and "." not in p.parts,
      "Unsafe relative path")
    return p

def regular(root,name):
    rel=relative(name);path=root
    require(root.is_dir() and not root.is_symlink(),"Root is not a real directory")
    for part in rel.parts:
        path=path/part
        require(not path.is_symlink(),"Symlink in protected path")
    require(path.is_file(),"Missing regular protected file")
    return path

def validate_authorizations(m):
    require(m["scope"]==SCOPE,"Wrong fresh RC scope")
    for key in NATIVE_FLAGS+ALWAYS_FALSE+("source_controls_authorized","controller_readiness"):
        require(type(m[key]) is bool,"Non-boolean authorization")
    require(len({m[k] for k in NATIVE_FLAGS})==1,"Split fresh RC authorization")
    require(all(m[k] is False for k in ALWAYS_FALSE),"Unsupported engineering authorization")
    return m

def methods():
    m=validate_authorizations(read_json(METHOD))
    for name,digest in m["protected_sha256"].items():
        require(re.fullmatch("[0-9a-f]{64}",digest) is not None,"Invalid protected digest")
        require(sha(regular(ROOT,name))==digest,"Protected source or evidence changed: "+name)
    return m

def contract():
    m=methods()
    require(m["contract"]==CONTRACT,"Wrong admission contract path")
    c=read_json(regular(ROOT,CONTRACT))
    validate_maps(c)
    return c

def authorize():
    m=methods()
    require(os.environ.get("GITHUB_ACTIONS")=="true" and os.environ.get("GITHUB_RUN_ATTEMPT")=="1",
      "Hosted first attempt required")
    require(str(ROOT)=="/home/runner/work/nssoc/nssoc","Wrong qualified canonical root")
    require(m["controller_readiness"] is True and all(m[k] is True for k in NATIVE_FLAGS),
      "Fresh RC execution not authorized")
    return m

def validate_maps(c):
    outer=c["transport"]["expected_sha256"];prior=c["original_physical"]["expected_sha256"]
    candidate=c["canonical_candidate"]["expected_sha256"]
    require(len(outer)==955 and len(prior)==931 and len(candidate)==184,"Wrong complete archive/view census")
    for table in (outer,prior,candidate):
        for name,digest in table.items():
            relative(name)
            require(isinstance(digest,str) and re.fullmatch("[0-9a-f]{64}",digest) is not None,"Invalid manifest digest")
    require({k[len("restored/"):]:v for k,v in outer.items() if k.startswith("restored/")}==prior,
      "Complete nested original physical manifest changed")
    require({k[len("candidate/"):]:v for k,v in prior.items() if k.startswith("candidate/")}==candidate,
      "Complete current candidate view changed")
    require(outer["result.json"]==c["transport"]["summary"]["sha256"] and
      prior["result.json"]==c["original_physical"]["summary"]["sha256"],"Summary identity changed")
    require(c["canonical_candidate"]["root"]=="hw/soc/out/cloud-cdr-v59-tail-access-physical/candidate",
      "Qualified candidate root changed")
    for row in c["canonical_candidate"]["anchor_consumed_paths"]:
        prefix=c["canonical_candidate"]["root"]+"/"
        require(row["canonical_relative_path"].startswith(prefix),"Anchor input escaped current candidate")
        name=row["canonical_relative_path"][len(prefix):]
        require(candidate[name]==row["sha256"]==outer[row["capsule_member"]],"Anchor input identity changed")
        require(row["original_absolute_path"]=="/home/runner/work/nssoc/nssoc/"+row["canonical_relative_path"],
          "Anchor original absolute path changed")
    require(len(c["canonical_candidate"]["anchor_consumed_paths"])==9,"Incomplete anchor input map")
    return c

def validate_saved_summary(summary,c):
    require((summary["run_id"],summary["source_head"],summary["run_attempt"],summary["status"])==
      (40542841034,"352e326e554e5c0f44b0e0a949a4eb707c72b038",1,
       "PASS_SAVED_IDENTITY_READBACK_ORIGINAL_PHYSICAL_FAILURE_RETAINED"),"Wrong saved readback identity/status")
    require(summary["original_run"]==40369539200 and
      summary["original_status"]=="FAIL_ADDITIVE_TAIL_WIRE_PHYSICAL","Original physical failure relabelled")
    require(summary["original_failure_preserved"] is summary["read_only_identity_verified"] is True,
      "Missing actual saved identity qualification")
    for key in ("automatic_retry","geometry_generated","extraction_executed","simulation_executed",
                "physical_accepted","electrical_accepted","qualified_pex","full_phy_accepted"):
        require(summary[key] is False,"Saved readback claimed unsupported work or acceptance")
    require([(r["label"],r["returncode"]) for r in summary["commands"]]==[
      ("restore-complete-saved931-capsule",0),("read-only-saved-native-identities",0)],
      "Saved native command sequence changed")
    for command in summary["commands"]:
        require(command["supervision_failure"] is None and not command["process_group_cleanup"]["remaining_live"],
          "Saved native command did not terminate cleanly")
    require({**summary["outputs"],"result.json":c["transport"]["summary"]["sha256"]}==
      c["transport"]["expected_sha256"],"Saved outer member map changed")
    return summary

def validate_physical(report):
    require(report["status"]=="PASS_NATIVE_PDK_CDR_PD500_DRC_LVS_AND_FAULT_CONTROLS","Native physical subreport failed")
    steps=report["steps"]
    faults=("v59_old_length","gain_gate_disconnected","gain_tail_width","missing_gain_hbt",
      "old_sampler_input_width","old_retime_width","wrong_follower_polarity","old_data_header_length",
      "wrong_finger_count","missing_hbt","q_open","rail_short","offgrid")
    require(set(steps)=={"drc","lvs","lvs_flat",*faults},"Incomplete physical gate/fault set")
    drc=steps["drc"]
    require(drc["status"]==drc["measurement"]["status"]=="PASS" and
      drc["execution"]["returncode"]==0 and drc["measurement"]["process_returncode"]==0 and
      drc["measurement"]["markers"]==0 and drc["measurement"]["category_count"]==560 and
      drc["measurement"]["report_sha256"]=="65323bd352a208ac709ce75e782faf3b6dd9291cce44ddb14ee15e01d5e919b0",
      "Original full560-category DRC gate changed")
    for name in ("lvs","lvs_flat"):
        row=steps[name];audit=row["audit"]
        require(row["status"]=="PASS" and row["execution"]["returncode"]==0 and row["audit_execution"]["returncode"]==0,
          "Original deep/flat LVS execution failed")
        require(audit["status"]=="PASS within comparison scope" and not audit["reasons"] and
          not audit["extraction_diagnostics"] and audit["circuit_status_counts"]=={"Match":1},
          "Original LVS comparison failed")
        require(len(audit["circuits"])==1 and audit["circuits"][0]["status"]=="Match" and
          audit["circuits"][0]["layout_devices_recursive"]==audit["circuits"][0]["schematic_devices_recursive"]==500
          and row["native_primitive_census"]==CENSUS,"Original complete500 LVS census changed")
    for name in faults:require(steps[name]["status"]=="REJECTED_EXPECTED_FAULT","Original native physical fault not rejected")
    require(report["serial_phy_complete"] is report["main_chip_integrated"] is report["qualified_pex"] is False,
      "Original physical scope changed")
    return {"DRC_categories":560,"markers":0,"deep_and_flat_devices":500,"native_faults":13}

def validate_geometry_metadata(generation,planes):
    require(generation["status"]=="GENERATED_UNQUALIFIED_ADDITIVE_TAIL_ACCESS_WIRE" and
      generation["all_existing_cell_material_text_properties_hierarchy_preserved"] is
      generation["serialized_full_parent_verified"] is
      generation["serialized_child_material_raw_and_hierarchy_verified"] is
      generation["original349_files_and88_runtime_sources_unchanged"] is True,
      "Original additive generation/source preservation changed")
    controls=generation["native_geometry_controls"]
    require(controls["status"]=="PASS_ACTUAL_SERIALIZED_GEOMETRY_CONTROLS" and
      controls["positive_before_each_fault"]==controls["faults_rejected"]==len(controls["cases"])==11 and
      all(r["fresh_actual_baseline_passed"] is r["actual_geometry_mutated"] is r["rejected"] is True
          for r in controls["cases"]),"Original native geometry controls changed")
    require(planes["status"]=="PASS_PD500_NATIVE160_PLANES_51_NETS_19_FAULTS" and
      planes["native_terminal_count"]==1446 and len(planes["anchors"])==160 and len(planes["controls"])==19 and
      all(r["rejected"] is True for r in planes["controls"]),"Original native planes/faults changed")
    return {"native_geometry_faults":11,"planes_anchors":160,"planes_logical_pairs":51,"planes_faults":19}

def validate_live(c):
    t=c["transport"]
    run=release.api("actions/runs/"+str(t["run"]))
    jobs=release.api("actions/runs/"+str(t["run"])+"/attempts/1/jobs?per_page=100")
    require((run["id"],run["head_sha"],run["run_attempt"],run["event"],run["status"],run["conclusion"],run["path"])==
      (t["run"],t["source"],1,"workflow_dispatch","completed","success",t["workflow"]),"Wrong live saved readback run")
    require(jobs["total_count"]==len(jobs["jobs"])==2,"Wrong live saved job count")
    require({str(j["id"]):[j["name"],j["conclusion"]] for j in jobs["jobs"]}==t["jobs"],"Wrong live saved jobs")
    for job in jobs["jobs"]:
        require(job["run_id"]==t["run"] and job["head_sha"]==t["source"] and job["status"]=="completed",
          "Live saved job/source mismatch")
    info=release.api("releases/tags/"+t["tag"]);ref=release.api("git/ref/tags/"+t["tag"])
    proof=release.validate_release(info,ref,t["tag"],t["source"])
    require(info["id"]==t["release"],"Wrong saved release ID")
    recorded=read_json(ROOT/(PREFIX+"-release.json"))
    fields=("id","name","size","digest")
    projection=lambda rows:sorted([{k:r[k] for k in fields} for r in rows],key=lambda r:r["id"])
    require(projection(info["assets"])==projection(recorded["assets"]),"Saved release asset inventory changed")
    original=frozen.validate_live(release.api("actions/runs/40369539200"),
      release.api("actions/runs/40369539200/attempts/1/jobs?per_page=100"),
      release.api("releases/tags/"+c["original_physical"]["tag"]),
      release.api("git/ref/tags/"+c["original_physical"]["tag"]))
    return {"saved_readback":proof,"original_failed_physical":original}

def verify_saved(root,c):
    require(root.is_dir() and not root.is_symlink(),"Saved root is not a real directory")
    frozen.verify_inputs(root,c["transport"]["expected_sha256"])
    frozen.verify_inputs(root/"restored",c["original_physical"]["expected_sha256"])
    validate_saved_summary(read_json(root/"result.json"),c)
    frozen.validate_summary(read_json(root/"restored/result.json"))
    return {"outer_files":955,"nested_original_files":931,"all_hashes_unchanged":True}

def qualify_saved(root,c):
    verify_saved(root,c)
    raw=read_json(root/"raw-hierarchy-proof.json")
    require(raw["status"]=="PASS_EXACT17_SERIALIZED_ADDITIONS_WITH_ALL_ORIGINAL_RAW_RECORDS" and
      raw["contract_sha256"]=="d6b2d367bff2036d97e62b28d2bf37d8be1a878770b594ab8e0286a92c88205e",
      "Wrong exact typed serialization proof")
    require(raw["all_original_raw_records_and_multiplicities_preserved"] is
      raw["all_original_properties_text_and_hierarchy_preserved"] is raw["original_failure_preserved"] is True,
      "Original raw records or hierarchy not preserved")
    require(raw["blanket_normalization_applied"] is raw["area_only_equality_used"] is
      raw["original_exact_guard_passed"] is raw["physical_accepted"] is raw["electrical_accepted"] is False,
      "Typed serialization scope changed")
    require(len(raw["cells"])==140 and len(raw["native_typed_additions"])==17,"Incomplete typed raw material proof")
    rejection=read_json(root/"original-raw-guard-rejection.json")
    require(rejection["function"]=="raw_hierarchy_proof" and rejection["line"]==290 and
      rejection["error"]=="AssertionError('Original shape/text/properties or exact added records changed')" and
      rejection["original_guard_passed"] is False and rejection["original_failure_preserved"] is True,
      "Original raw guard failure changed")
    comparison_rejection=read_json(root/"original-comparator-rejection.json")
    require(comparison_rejection["function"]=="compare" and comparison_rejection["line"]==107 and
      comparison_rejection["error"]=="AssertionError()" and
      comparison_rejection["original_comparator_sha256"]==semantic.TOPOLOGY_SHA,"Original topology failure changed")
    old=read_json(root/"original-identity.json");new=read_json(root/"current-identity.json")
    for side,value in (("old",old),("new",new)):
        for field in ("graph","locations","anchors"):
            require(value[field]==read_json(root/"restored"/frozen.SIDES[side][field]),
              "Acquired witness does not match actual saved "+side+" "+field)
        require(value["full_inventory"]==read_json(root/"restored"/frozen.SIDES[side]["inventory"]),
          "Acquired complete native PCell inventory changed")
    geometry=validate_geometry_metadata(read_json(root/"restored/candidate/result.json"),
      read_json(root/"restored/candidate/native-planes.json"))
    physical=validate_physical(read_json(root/"restored/candidate/parent/physical/result.json"))
    supplemental=semantic.compare_pair(old,new)
    return {"status":"PASS_JOINT_SAVED_GEOMETRY_RC_ADMISSION_ORIGINAL_FAILURE_RETAINED",
      "complete_inputs":{"outer":955,"nested_original":931,"current_candidate":184},
      "original_native_physical_gates":physical,"original_generation_and_planes":geometry,"supplemental_topology":supplemental,
      "typed_raw_material_proof_sha256":sha(root/"raw-hierarchy-proof.json"),
      "original_physical_run_status":"FAIL_ADDITIVE_TAIL_WIRE_PHYSICAL",
      "physical_accepted":False,"electrical_accepted":False,"qualified_pex":False,"full_phy_accepted":False}

def materialize_candidate(saved,c,destination):
    spec=c["canonical_candidate"];expected=spec["expected_sha256"]
    require(len(expected)==184,"Wrong current view census")
    require(not destination.exists() and not destination.is_symlink(),"Canonical candidate already exists")
    for name,digest in expected.items():
        require(sha(regular(saved,spec["member_prefix"]+name))==digest,"Candidate source digest changed")
    for ancestor in (destination,*destination.parents):
        require(not ancestor.is_symlink(),"Symlink in candidate destination ancestry")
    destination.mkdir(parents=True)
    for name,digest in expected.items():
        target=destination/relative(name)
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(regular(saved,spec["member_prefix"]+name),target)
        require(sha(target)==digest,"Candidate copy digest changed")
    frozen.verify_inputs(destination,expected)
    return {"files":184,"all_original_candidate_bytes_unchanged":True,"destination":str(destination)}

def restore(out):
    authorize();c=contract();out.mkdir(parents=True,exist_ok=False)
    live=validate_live(c)
    transport=out/"transport";transport.mkdir()
    t=c["transport"];base="https://github.com/Melihakbulut221/nssoc/releases/download/"+t["tag"]+"/"
    stem="cdr-v59-tail-saved-identity-40542841034-1"
    fetch(base+stem+".summary.json",t["summary"]["sha256"],transport/"summary.json")
    require((transport/"summary.json").read_bytes()==regular(ROOT,t["summary"]["path"]).read_bytes(),
      "Saved summary bytes changed")
    fetch(base+stem+".parts.json",t["parts"]["sha256"],transport/"parts.json")
    parts=read_json(transport/"parts.json")
    require(parts==t["archive"],"Saved complete archive manifest changed")
    for part in parts["parts"]:fetch(base+part["name"],part["sha256"],transport/part["name"])
    extracted=frozen.extraction_helpers().exact_extract(parts,transport,out/"saved",t["expected_sha256"])
    require(extracted["regular_members"]==955,"Incomplete saved extraction")
    write(out/"archive-verification.json",{"live":live,"archive":extracted,
      "maps":verify_saved(out/"saved",c),"original_failure_preserved":True})
    proof=qualify_saved(out/"saved",c)
    write(out/"joint-admission.json",proof)
    copied=materialize_candidate(out/"saved",c,ROOT/c["canonical_candidate"]["root"])
    write(out/"canonical-candidate.json",copied)
    verify_saved(out/"saved",c)
    return proof
