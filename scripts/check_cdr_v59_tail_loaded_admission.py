#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted-only actual JSON admission and synthetic regular-file controls; no archives/native."""
import ast,copy,json,tempfile
from pathlib import Path
import cdr_v59_tail_loaded_admission as a

def reject(name,call,reason,rows):
    try:call()
    except AssertionError as error:
        assert error.args==(reason,),(name,error.args,reason)
        rows.append({"name":name,"reason":reason})
    else:raise AssertionError("Accepted "+name)

def controls():
    method=a.methods();c=a.descriptor();snap=a.snapshots();rows=[];positives=[]
    # Both disabled and enabled authorization shapes are real validator inputs.
    disabled=copy.deepcopy(method)
    for k in a.AUTH:disabled[k]=False
    disabled["controller_readiness"]=False
    controls_only=copy.deepcopy(disabled);controls_only["source_controls_authorized"]=True;controls_only["workflow_dispatch_authorized"]=True
    preparation=copy.deepcopy(controls_only);preparation.update(preparation_authorized=True,controller_readiness=True)
    enabled=copy.deepcopy(preparation);enabled.update(native_execution_authorized=True,simulation_authorized=True)
    for m in (disabled,controls_only,preparation,enabled):assert a.validate_authorizations(m)is True
    positives.append({"name":"four_actual_authorization_modes","modes":4})
    auth=[
      ("boolean_type",disabled,{"source_controls_authorized":1},"Authorization fields must be strict booleans"),
      ("geometry",disabled,{"geometry_generation_authorized":True},"Forbidden geometry/extraction/acceptance authorization"),
      ("split_native",disabled,{"native_execution_authorized":True},"Split simulator authorization"),
      ("simulation_without_preparation",enabled,{"preparation_authorized":False},"Simulation requires preparation authorization"),
      ("enabled_without_controls",enabled,{"source_controls_authorized":False},"Execution requires source controls, dispatch and readiness"),
      ("enabled_without_dispatch",enabled,{"workflow_dispatch_authorized":False},"Execution requires source controls, dispatch and readiness"),
      ("enabled_without_readiness",enabled,{"controller_readiness":False},"Execution requires source controls, dispatch and readiness"),
      ("missing_case",disabled,{"cases":list(a.CASES[:-1])},"Original ten cases changed")]
    for name,base,change,reason in auth:
        m=copy.deepcopy(base);m.update(change)
        assert json.dumps(m,sort_keys=True)!=json.dumps(base,sort_keys=True)
        reject(name,lambda:a.validate_authorizations(m),reason,rows)
    assert a.validate_reports(c,snap)is True
    positives.append({"name":"complete_actual_fresh_RC_reports_and_exact_frozen_pipeline",
      "producer_run":40576801174,"members":len(c["actual_fresh_RC"]["expected_files"]),
      "pipeline_source_sha256":a.PIPELINE_SHA,"saved_source_context":c["actual_fresh_RC"]["run"]["head_sha"]})
    def change_binding(s,fn):
        fn(s["binding.json"]);s["binding-result.json"]["binding"]=copy.deepcopy(s["binding.json"])
    def change_contract(s,fn):
        fn(s["composition.json"]);s["MIM-precision-result.json"]["composition"]["contract"]=copy.deepcopy(s["composition.json"])
    def duplicate_devices(s):
        change_binding(s,lambda b:b["devices"].__setitem__(0,copy.deepcopy(b["devices"][1])))
    faults=[
      ("wrong_producer",lambda q,s:q["actual_fresh_RC"]["run"].__setitem__("id",1),"Wrong fresh RC producer"),
      ("outer_status",lambda q,s:s["summary.json"].__setitem__("status","PASS"),"Fresh RC terminal identity changed"),
      ("incomplete_pipeline",lambda q,s:s["summary.json"].__setitem__("fresh_RC_pipeline_complete",False),"Fresh RC completion missing"),
      ("simulation_claim",lambda q,s:s["summary.json"].__setitem__("simulation_executed",True),"Fresh RC scope changed"),
      ("physical_failure_relabel",lambda q,s:s["summary.json"].__setitem__("original_physical_status","PASS"),"Original physical failure lost"),
      ("failed_owned_command",lambda q,s:s["summary.json"]["commands"][0].__setitem__("returncode",1),"Fresh RC owned command failed"),
      ("incomplete_outer_map",lambda q,s:q["actual_fresh_RC"]["expected_files"].pop("result.json"),"Complete fresh RC member map changed"),
      ("changed_parts",lambda q,s:s["parts.json"].__setitem__("bytes",1),"Fresh RC parts changed"),
      ("extra_MIM_output",lambda q,s:s["MIM-precision-result.json"]["outputs"].__setitem__("extra","0"*64),"Complete nested output count changed"),
      ("changed_binding_output",lambda q,s:s["binding-result.json"]["outputs"].__setitem__(next(iter(s["binding-result.json"]["outputs"])),"0"*64),"Complete nested output join changed"),
      ("wrong_nested_source",lambda q,s:s["MIM-precision-result.json"].__setitem__("source_head","0"*40),"Nested producer source changed"),
      ("wrong_binding_summary",lambda q,s:s["summary.json"].__setitem__("binding_result_sha256","0"*64),"Binding summary hash changed"),
      ("wrong_wire_summary",lambda q,s:s["summary.json"].__setitem__("wire_RC_result_sha256","0"*64),"Wire RC summary hash changed"),
      ("wrong_MIM_summary",lambda q,s:s["summary.json"]["completed_pipeline"].__setitem__("summary_sha256","0"*64),"MIM summary hash changed"),
      ("wrong_composition",lambda q,s:s["composition.json"]["counts"].__setitem__("R",1),"Composition report differs"),
      ("old_RC_census",lambda q,s:change_contract(s,lambda d:d["counts"].__setitem__("R",24574)),"Current model census changed"),
      ("sorted_ports",lambda q,s:change_contract(s,lambda d:d.__setitem__("interface",sorted(d["interface"]))),"Current ordered native ports changed"),
      ("binding_copy_changed",lambda q,s:s["binding.json"]["census"].__setitem__("rppd",97),"Current complete binding differs"),
      ("wrong_native_classes",lambda q,s:change_binding(s,lambda b:b["census"].__setitem__("rppd",97)),"Current device classes changed"),
      ("duplicate_native_identity",lambda q,s:duplicate_devices(s),"Current device identities changed"),
      ("wrong_composition_identity",lambda q,s:change_contract(s,lambda d:d["device_records"].__setitem__(0,copy.deepcopy(d["device_records"][1]))),"Composition device identities changed"),
      ("lost_same_run_integrity",lambda q,s:s["MIM-precision-result.json"]["current_input_integrity"].__setitem__("all_fresh_source_inputs_unchanged",False),"Same-run input integrity changed"),
      ("missing_wire_fault",lambda q,s:s["MIM-precision-result.json"]["variants"]["precise"]["audit"]["wire_controls"]["cases"].pop(),"Original MIM audit controls changed"),
      ("missing_composition_fault",lambda q,s:s["MIM-precision-result.json"]["composition"]["controls"].pop(),"Original composition controls changed"),
      ("double_MIM_projection",lambda q,s:change_contract(s,lambda d:d.__setitem__("native_extracted_mim_cards_projected_once",False)),"Intrinsic versus wire composition changed")]
    for name,mutate,reason in faults:
        q=copy.deepcopy(c);s=copy.deepcopy(snap);before=json.dumps([q,s],sort_keys=True)
        mutate(q,s);assert json.dumps([q,s],sort_keys=True)!=before,name
        reject(name,lambda:a.validate_reports(q,s),reason,rows)
    # Mutate actual saved native predicates after the new admission joins, then
    # require the precise unchanged original validator assertion frame.
    frozen_faults=[
      ("original_mask_gate","actual_mim_masks_exact","c['native_binding']['actual_mim_devices']==7 and c['native_binding']['actual_mim_masks_exact']"),
      ("original_all978_gate","all978points_match_original_native_clusters_and_physical_components","c['native_binding']['all978points_match_original_native_clusters_and_physical_components']")]
    frozen_text=a.regular(a.ROOT,a.PIPELINE_SOURCE).read_text();frozen_tree=ast.parse(frozen_text)
    for name,key,assertion in frozen_faults:
        s=copy.deepcopy(snap);assert s["MIM-precision-result.json"]["variants"]["precise"]["capture"]["native_binding"][key]is True
        s["MIM-precision-result.json"]["variants"]["precise"]["capture"]["native_binding"][key]=False
        matches=[n for n in ast.walk(frozen_tree)if isinstance(n,ast.Assert)and ast.dump(n.test)==ast.dump(ast.parse(assertion,mode="eval").body)]
        assert len(matches)==1
        try:a.validate_reports(c,s)
        except AssertionError as error:
            assert error.args==()
            frames=[];tb=error.__traceback__
            while tb is not None:
                frames.append((tb.tb_frame.f_code.co_name,tb.tb_frame.f_code.co_filename,tb.tb_lineno));tb=tb.tb_next
            assert ("validate_pipeline",str(a.ROOT/a.PIPELINE_SOURCE),matches[0].lineno)in frames,(name,frames)
            rows.append({"name":name,"reason":"Exact original assertion","source":a.PIPELINE_SOURCE,"line":matches[0].lineno,"assertion":assertion})
        else:raise AssertionError("Accepted "+name)
    p=c["actual_fresh_RC"];run=copy.deepcopy(p["run"]);jobs={"total_count":len(p["jobs"]),"jobs":copy.deepcopy(p["jobs"])}
    info=copy.deepcopy(p["release"]);info["assets"]=copy.deepcopy(p["assets"])
    ref={"ref":"refs/tags/"+info["tag_name"],"object":{"type":"commit","sha":run["head_sha"]}}
    a.validate_remote(c,run,jobs,info,ref)
    positives.append({"name":"actual_saved_run_jobs_assets_identity_metadata","jobs":len(jobs["jobs"]),"assets":len(info["assets"])})
    remote=[
      ("live_source",lambda r,j,i:r.__setitem__("head_sha","0"*40),"Live producer run changed"),
      ("missing_job",lambda r,j,i:j["jobs"].pop(),"Live producer job count changed"),
      ("duplicate_job",lambda r,j,i:j["jobs"].__setitem__(0,copy.deepcopy(j["jobs"][1])),"Duplicate live producer job"),
      ("failed_job",lambda r,j,i:j["jobs"][0].__setitem__("conclusion","failure"),"Live producer job changed"),
      ("wrong_release",lambda r,j,i:i.__setitem__("id",1),"Live producer release changed"),
      ("wrong_asset_digest",lambda r,j,i:i["assets"][0].__setitem__("digest","sha256:"+"0"*64),"Live producer assets changed")]
    for name,mutate,reason in remote:
        r,j,i=copy.deepcopy((run,jobs,info));mutate(r,j,i)
        reject(name,lambda:a.validate_remote(c,r,j,i,ref),reason,rows)
    with tempfile.TemporaryDirectory()as td:
        root=Path(td)/"bundle";root.mkdir();(root/".hidden").write_bytes(b"hidden");(root/"empty").write_bytes(b"")
        expected={n:a.sha(root/n)for n in (".hidden","empty")}
        assert a.verify_exact_files(root,expected)=={"files":2,"all_hashes_unchanged":True,"exact_inventory":True}
        positives.append({"name":"actual_regular_hidden_empty_inventory","files":2})
        (root/"extra").write_bytes(b"extra")
        reject("extra_member",lambda:a.verify_exact_files(root,expected),"Complete restored member map changed",rows);(root/"extra").unlink()
        (root/".hidden").write_bytes(b"changed")
        reject("changed_member",lambda:a.verify_exact_files(root,expected),"Complete restored member map changed",rows);(root/".hidden").write_bytes(b"hidden")
        (root/"empty").unlink()
        reject("missing_member",lambda:a.verify_exact_files(root,expected),"Complete restored member map changed",rows)
        (root/"empty").symlink_to(root/".hidden")
        reject("symlink_member",lambda:a.verify_exact_files(root,expected),"Symlink in restored inventory",rows)
    assert len(positives)==4 and len(rows)==45,(len(positives),len(rows))
    return {"status":"PASS_ACTUAL_TAIL_LOADED_METADATA_AND_REGULAR_INVENTORY_CONTROLS",
      "positive_groups":positives,"rejected":rows,"complete_actual_JSON_used":True,
      "frozen_pipeline_validator_executed_on_saved_report":True,"numerical_controller_executed":False,
      "archive_restore_controls_pending":True,"source_initialization_closure_pending":True,
      "archive_downloaded":False,"simulator_executed":False}

def main():
    try:result=controls()
    except BaseException as error:
        import traceback
        result={"status":"FAIL_TAIL_LOADED_ADMISSION_CONTROLS","error":repr(error),"traceback":traceback.format_exc()}
        print(json.dumps(result,sort_keys=True,indent=2));raise
    print(json.dumps(result,sort_keys=True,indent=2))

if __name__=="__main__":main()
