#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Current-input adapters for exact inherited numerical workers; no legacy archive identity."""
import json
import os
from pathlib import Path
import shutil
import cdr_v59_tail_fresh_rc_admission as source
import cdr_v59_binding_rc_source as numerical
from run_cloud_tx_layout_repair import sha

ROOT=source.ROOT
OUT=source.OUT
RESTORE=OUT/"restore"
CAPSULE=RESTORE/"saved"
PIN=RESTORE/"joint-admission.json"
ANALYSIS=ROOT/"hw/soc/out/cloud-cdr-v59-tail-access-physical/candidate"
BINDING=OUT/"binding"
RC_STAGE=OUT/"wire-stage"
MIM_OUT=OUT/"mim"
HANDOFF=MIM_OUT/"inputs/fresh-stage-manifest.json"
WORKERS={"binding":"scripts/cloud_cdr_v59_tail_fresh_binding.py",
 "rc":"scripts/cloud_cdr_v59_tail_fresh_wire_rc.py",
 "capture":"scripts/cloud_cdr_v59_tail_fresh_mim_capture.py",
 "audit":"scripts/cloud_cdr_v59_tail_fresh_mim_audit.py",
 "precision":"scripts/cloud_cdr_v59_tail_fresh_mim_precision.py"}
PASS={"binding":"PASS_PD500_NATIVE_MODEL_BINDING_14_FAULTS_AND_NATIVE_CONTACT_ORACLE_REQUIRES_WIRE_COMPOSITION_AND_WAVES",
 "rc":"PASS_PD500_FRESH_NATIVE_WIRE_RC_AND13_CONTROLS_REQUIRES_LOADED_CLOSED_LOOP"}

def require(value,message):
    if not value:raise AssertionError(message)

def methods():
    return source.methods()

def authorize(stage=None):
    require(stage in (None,"binding","rc"),"Unknown fresh numerical stage")
    return source.authorize()

def inventory(root):
    require(root.is_dir() and not root.is_symlink(),"Numerical inventory root is not a real directory")
    result={}
    for path in sorted(root.rglob("*")):
        require(not path.is_symlink() and (path.is_file() or path.is_dir()),"Nonregular numerical output")
        if path.is_file():result[path.relative_to(root).as_posix()]=sha(path)
    return result

def verify_table(root,expected,exact=True):
    for name,digest in expected.items():
        require(sha(source.regular(root,name))==digest,"Numerical input digest changed: "+name)
    if exact:require(inventory(root)==expected,"Complete numerical inventory changed")
    return {"files":len(expected),"all_hashes_unchanged":True}

def copy_table(root,destination,expected):
    require(not destination.exists() and not destination.is_symlink(),"Numerical projection destination exists")
    verify_table(root,expected)
    for parent in (destination,*destination.parents):require(not parent.is_symlink(),"Projection destination ancestry is a symlink")
    destination.mkdir(parents=True)
    for name,digest in expected.items():
        path=destination/source.relative(name);path.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source.regular(root,name),path)
        require(sha(path)==digest,"Numerical projection copy changed")
    return verify_table(destination,expected)

def validate_summary(pin):
    c=source.contract()
    require(pin==source.read_json(PIN),"Current admission pin bytes/data changed")
    require(pin==source.qualify_saved(CAPSULE,c),"Current joint geometry admission no longer reproduces")
    return pin

def verify_saved_inputs(pin):
    validate_summary(pin);c=source.contract()
    saved=source.verify_saved(CAPSULE,c)
    original=verify_table(ANALYSIS,c["canonical_candidate"]["expected_sha256"],exact=False)
    return {"saved_outer955":saved,"original_candidate184":original,
      "all_original_saved_and_current_input_hashes_unchanged":True}

def restore_for_binding(pin,selected,out):
    validate_summary(pin);c=source.contract()
    require(out==BINDING,"Wrong fresh binding output")
    required=["wire/device-locations01.json","parent/layout/result.json","parent/layout/schematic.cir",
      "parent/physical/lvs_flat/extracted.cir","parent/physical/lvs_flat/audit.json","parent/physical/lvs_flat/result.lvsdb"]
    require(selected==required,"Fresh binding selection changed")
    expected=c["canonical_candidate"]["expected_sha256"]
    destination=out/"inputs";require(not destination.exists(),"Fresh binding inputs exist")
    destination.mkdir()
    for name in selected:
        original=source.regular(ANALYSIS,name);require(sha(original)==expected[name],"Current binding input changed")
        target=destination/source.relative(name);target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(original,target);require(sha(target)==expected[name],"Binding input copy changed")
    verify_table(destination,{n:expected[n] for n in selected})
    return {"outputs":expected},{"original_failed_physical_run":40369539200,
      "original_failed_physical_status":"FAIL_ADDITIVE_TAIL_WIRE_PHYSICAL",
      "complete_original_candidate_outputs":expected,
      "unchanged_current_metadata_sha256":{n:expected[n] for n in ("result.json","parent/layout/result.json","wire/anchors08.json")},
      "typed_saved_readback_run":40542841034,"joint_admission_sha256":sha(PIN),
      "actual_current_source_sha256":{n:expected[n] for n in selected},
      "saved_integrity":verify_saved_inputs(pin),"historical_binding_reused":False}

def binding_target_controls(binding):
    methods()
    return numerical.binding_target_controls(binding)

def assert_current_candidate_ready():
    c=source.contract()
    require(CAPSULE.exists(),"Complete immutable saved955 capsule is absent")
    verify_saved_inputs(source.read_json(PIN))
    verify_table(ANALYSIS,c["canonical_candidate"]["expected_sha256"])

def restore_for_rc(pin,stage):
    validate_summary(pin);require(stage==RC_STAGE,"Wrong fresh wire RC stage")
    assert_current_candidate_ready();c=source.contract()
    graph=source.read_json(ANALYSIS/"wire/native05/result.json")
    anchors=source.read_json(ANALYSIS/"wire/anchors08.json")
    for path,digest in anchors["inputs"].items():
        require(Path(path).is_relative_to(ANALYSIS) and sha(source.regular(ANALYSIS,Path(path).relative_to(ANALYSIS).as_posix()))==digest,
          "Actual native anchor input path/hash changed")
    return {"strict_wire_graph":graph,"anchors":anchors,"outputs":c["canonical_candidate"]["expected_sha256"]},{
      "original_failed_physical_run":40369539200,"typed_saved_readback_run":40542841034,
      "joint_admission_sha256":sha(PIN),"current_candidate_files":184,
      "original_anchor_absolute_paths_preserved":True,"historical_RC_reused":False}

def new_current_outputs(pin):
    # Terminal inventory is descriptive; integrity failures are retained by the unchanged worker finally.
    original=source.contract()["canonical_candidate"]["expected_sha256"]
    return {name:digest for name,digest in inventory(ANALYSIS).items() if name not in original}

def stage_report(stage):
    require(stage in PASS,"Unknown numerical stage report")
    root={"binding":BINDING,"rc":RC_STAGE}[stage]
    report=source.read_json(source.regular(root,"result.json"))
    require(report["source_head"]==os.environ["GITHUB_SHA"] and report["status"]==PASS[stage]
      and report["sources_unchanged"] is True,"Fresh numerical stage failed or wrong source")
    for name in ("qualified_pex","full_phy_accepted","closed_loop"):require(report[name] is False,"Numerical stage acceptance changed")
    require(report["saved_capsule_integrity"]==verify_saved_inputs(source.read_json(PIN)),"Fresh stage saved-input integrity changed")
    actual=inventory(root);expected={**report["outputs"],"result.json":sha(root/"result.json")}
    require(actual==expected,"Fresh complete stage output inventory changed")
    if stage=="binding":
        bound=report["binding"]
        numerical.validate_bound_targets(bound)
        require(bound["census"]==numerical.CENSUS and len(bound["devices"])==500 and
          len(bound["native_ports"])==25 and len(bound["node_map"])==114,"Fresh complete binding census changed")
        require(source.read_json(root/"binding.json")==bound,"Fresh binding report/file mismatch")
        require(len(report["controls"])==14 and all(r["rejected"] is True for r in report["controls"]),
          "Fresh14 binding faults changed")
        require(report["target_length_controls"]["actual_fresh_binding"] is True and
          len(report["target_length_controls"]["rejected"])==6,"Fresh target-length faults changed")
        require(len(report["native_contact_comparisons"])==221 and
          len(report["contact_model_controls"]["rejected_geometry"])==
          len(report["contact_model_controls"]["rejected_compact_models"])==3,"Fresh contact oracle/faults changed")
        require(report["native_simulation_passed"] is report["wire_rc_included"] is False,"Binding scope changed")
    else:
        require(report["geometry"]==source.read_json(ANALYSIS/"wire/native05/result.json") and
          report["anchors"]==source.read_json(ANALYSIS/"wire/anchors08.json"),"Fresh RC geometry/anchor source mismatch")
        require(report["capture"]["returncode"]==0 and
          report["capture"]["status"]=="NATIVE_COMPLETE_AWAITING_RC_AUDIT","Fresh RC capture incomplete")
        audit=report["audit"]
        require(audit["status"]=="PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY" and audit["original_devices"]==500
          and audit["geometry_probes"]==978 and audit["physical_wire_components"]==113,"Fresh strict RC audit changed")
        require(type(audit["actual_exported_resistors"]) is int and type(audit["actual_exported_capacitors"]) is int
          and min(audit["actual_exported_resistors"],audit["actual_exported_capacitors"])>0,"Fresh actual R/C counts invalid")
        require(report["controls"]["status"]=="PASS_REAL_NATIVE_BASELINE_AND13_RAW_CORRUPTION_CONTROLS"
          and len(report["controls"]["cases"])==13,"Fresh13 raw RC faults changed")
        require(report["new_current_view_outputs"]==new_current_outputs(source.read_json(PIN)),
          "Fresh complete current output-map changed")
    return report

def stage_pin(stage):
    root={"binding":BINDING,"rc":RC_STAGE}[stage]
    return {"run":int(os.environ["GITHUB_RUN_ID"]),"source_head":os.environ["GITHUB_SHA"],
      "summary_sha256":sha(root/"result.json"),"report":stage_report(stage)}

def binding_pin():
    return stage_pin("binding")

def restore_inputs():
    require(MIM_OUT.is_dir() and not HANDOFF.exists(),"Fresh MIM handoff already exists or root missing")
    bound=stage_pin("binding");rc=stage_pin("rc")
    result={"status":"PASS_FRESH_CURRENT_STAGE_HANDOFF_NO_HISTORICAL_BUNDLE_IDENTITY",
      "source_head":os.environ["GITHUB_SHA"],"run":int(os.environ["GITHUB_RUN_ID"]),
      "joint_admission_sha256":sha(PIN),"binding":bound,"rc":rc,
      "complete_binding_files":inventory(BINDING),"complete_RC_stage_files":inventory(RC_STAGE),
      "complete_current_view_files":inventory(ANALYSIS),"saved_inputs":verify_saved_inputs(source.read_json(PIN)),
      "historical763_1136_1127_counts_reused":False}
    source.write(HANDOFF,result);verify_restored()
    return result

def handoff():
    require(HANDOFF.is_file() and not HANDOFF.is_symlink(),"Missing fresh complete handoff")
    h=source.read_json(HANDOFF)
    require(h["source_head"]==os.environ["GITHUB_SHA"] and h["run"]==int(os.environ["GITHUB_RUN_ID"])
      and h["joint_admission_sha256"]==sha(PIN),"Fresh handoff source/run mismatch")
    require(h["historical763_1136_1127_counts_reused"] is False,"Historical bundle relabelled")
    return h

def verify_restored():
    h=handoff()
    require(h["binding"]==stage_pin("binding") and h["rc"]==stage_pin("rc"),"Fresh stage pin changed")
    binding=verify_table(BINDING,h["complete_binding_files"])
    rc=verify_table(RC_STAGE,h["complete_RC_stage_files"])
    current=verify_table(ANALYSIS,h["complete_current_view_files"])
    saved=verify_saved_inputs(source.read_json(PIN))
    return {"binding_complete_files":binding,"RC_complete_stage_files":rc,"current_complete_view":current,
      "saved_input_integrity":saved,"all_fresh_source_inputs_unchanged":True}

def project_for_capture(out):
    require(out.parent==MIM_OUT and out.name in ("precise","precise_reversed"),"Wrong fresh native order")
    verify_restored();h=handoff()
    copy_table(ANALYSIS,out/"source",h["complete_current_view_files"])
    copy_table(BINDING,out/"model-binding",h["complete_binding_files"])
    bound=stage_report("binding");rc=stage_report("rc")
    binding=source.read_json(out/"model-binding/binding.json")
    require(binding==bound["binding"],"Projected fresh binding changed")
    return rc,{k:v for k,v in h["rc"].items() if k!="report"},bound,{k:v for k,v in h["binding"].items() if k!="report"},binding

def verify_projection(out):
    require(out.parent==MIM_OUT and out.name in ("precise","precise_reversed"),"Wrong projected native order")
    h=handoff()
    verify_table(out/"source",h["complete_current_view_files"])
    verify_table(out/"model-binding",h["complete_binding_files"])
    return verify_restored()

def derived(stage):
    require(stage in WORKERS,"Unknown derived numerical worker")
    methods()
    return ROOT/WORKERS[stage]
