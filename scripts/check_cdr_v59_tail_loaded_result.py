#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Preserve actual historical verdicts and exercise current result admission; no numerical execution."""
import ast,copy,json,os,traceback
from unittest import mock
import cdr_v59_tail_loaded_admission as a
import cdr_v59_tail_loaded_result as g

def original_assertion_refusal(fn,report,case,code,assertion):
    path=a.regular(a.ROOT,g.ORIGINAL);text=path.read_text()
    node=[n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)and n.name=="validate_result"][0]
    derived=ast.get_source_segment(text,node).replace(g.OLD_INVENTORY,g.NEW_INVENTORY)
    matches=[n for n in ast.walk(ast.parse(derived))if isinstance(n,ast.Assert)
      and ast.dump(n.test)==ast.dump(ast.parse(assertion,mode="eval").body)]
    assert len(matches)==1,assertion
    try:fn(report,case,False,code)
    except AssertionError as error:
        assert error.args==(),(assertion,error.args)
        frames=[];tb=error.__traceback__
        while tb is not None:
            frames.append((tb.tb_frame.f_code.co_name,tb.tb_frame.f_code.co_filename,tb.tb_lineno));tb=tb.tb_next
        assert ("validate_result",str(path)+"::current3823",matches[0].lineno)in frames,(assertion,frames)
        return {"source":g.ORIGINAL,"derived_line":matches[0].lineno,"exact_original_assertion":assertion}
    raise AssertionError("Original predicate accepted changed input: "+assertion)

def historical_controls():
    c=a.descriptor();fn,derivation=g.validator();rows=[];fault=None
    for prior in c["original_electrical"]["prior_cases"]:
        spec=prior["native_result"];path=a.regular(a.ROOT,spec["path"])
        assert path.stat().st_size==spec["bytes"]and a.sha(path)==spec["sha256"]
        original=json.loads(path.read_bytes());report=copy.deepcopy(original)
        assert report["case"]==prior["case"]and report["status"]==prior["status"]
        old_inventory=copy.deepcopy(report["current_saved_input_integrity"])
        report["current_saved_input_integrity"]={"files":3823,"all_hashes_unchanged":True,"exact_inventory":True}
        # Only the inventory fixture changes; every measured value and numerical
        # verdict stays exact. Returncode zero is deliberate to reach status gates.
        reverse=copy.deepcopy(report);reverse["current_saved_input_integrity"]=old_inventory
        assert reverse==original
        with mock.patch.dict(os.environ,{"GITHUB_SHA":original["source_head"]}):
            if prior["intentional_fault_case"]:
                assert prior["original_case_verdict_passed"]is True and original["actual_fault_detected"]is True
                assert fn(report,prior["case"],False,0)is True
                frame=None
                if prior["case"]=="clock_stopped":fault=copy.deepcopy(report)
            else:
                assert prior["original_case_verdict_passed"]is False
                frame=original_assertion_refusal(fn,report,prior["case"],0,
                  "r['status']=='PASS_WHOLE_MIM_PD500_LOADED_SCREEN_NOT_CLOSED_LOOP_OR_PHY_SIGNOFF'")
        rows.append({"case":prior["case"],"original_status":original["status"],"native_sha256":spec["sha256"],
          "original_passed":prior["original_case_verdict_passed"],"original_assertion_frame":frame,
          "all_measured_values_unchanged":True})
    assert len(rows)==10 and sum(x["original_passed"]for x in rows)==2 and fault is not None
    return {"cases":rows,"eight_rejections_and_two_fault_detections_retained":True,
      "only_inventory_fixture_projection":True,"zero_code_used_to_reach_original_status_predicate":True,
      "derivation":derivation},fault

def current_fixture(fault):
    c=a.descriptor();p=c["actual_fresh_RC"];r=copy.deepcopy(fault)
    r["source_head"]=os.environ["GITHUB_SHA"]
    r.update(terminal_finalization_complete=True,terminal_inventory_complete=True,terminal_save_attempted=True,
      terminal_errors=[],active_primary_exception_before_terminal=None)
    r["terminal_actions"]=[{"action":name,"completed":True}for name in (
      "protected_sources","complete_saved_inputs","preserve_preexisting_atomic_fragment","complete_output_inventory")]
    r["composition_source"]={"run":p["run"]["id"],"source_head":p["run"]["head_sha"],
      "summary_sha256":p["snapshots"]["summary.json"]["sha256"],"stage_sha256":p["snapshots"]["MIM-precision-result.json"]["sha256"],
      "original_physical_run":40369539200,"original_physical_status":"FAIL_ADDITIVE_TAIL_WIRE_PHYSICAL",
      "original_eight_electrical_rejections_and_two_fault_detections_preserved":True,
      "geometry_regenerated":False,"extraction_rerun":False,"simulation_preaccepted":False,
      "full_archive":{"regular_members":3823,"full_inventory_verified":True,
        "complete_member_hashes":{name:{"sha256":digest,"synthetic_size_not_consumed_here":True}for name,digest in p["expected_files"].items()}}}
    r["native_plane_source"]={"current_mim_source":p["snapshots"]["MIM-precision-result.json"]["sha256"],
      "native_planes_sha256":p["expected_files"]["mim/precise/source/native-planes.json"],
      "fresh_layout_sha256":p["expected_files"]["mim/precise/source/parent/layout/result.json"],
      "native_binding_sha256":p["expected_files"]["binding/binding.json"]}
    external={name:"0"if name in ("avss","sub","wire_cref")else name for name in p["interface"]}
    r["binding"]["interface"]=external;r["binding"]["ports"]=[external[name]for name in p["interface"]]
    preparation=copy.deepcopy(r);preparation.update(case="nominal_early",status=g.PREPARATION_PASS,transient_executed=False)
    return r,preparation

def current_controls(fault):
    r,preparation=current_fixture(fault)
    assert g.validate(preparation,"nominal_early",True,0)["case"]=="nominal_early"
    assert g.validate(r,"clock_stopped",False,0,preparation)["case"]=="clock_stopped"
    cases=[]
    def reject(name,mutate,reason):
        report,prepared=copy.deepcopy((r,preparation));before=json.dumps([report,prepared],sort_keys=True)
        mutate(report,prepared);assert json.dumps([report,prepared],sort_keys=True)!=before,name
        try:g.validate(report,"clock_stopped",False,0,prepared)
        except AssertionError as error:
            assert error.args==(reason,),(name,error.args)
            tb=error.__traceback__;frames=[]
            while tb is not None:
                frames.append((tb.tb_frame.f_code.co_name,tb.tb_frame.f_code.co_filename));tb=tb.tb_next
            assert ("validate",g.__file__)in frames,(name,frames)
        else:raise AssertionError("Accepted "+name)
        cases.append({"name":name,"reason":reason})
    faults=[
      ("terminal_incomplete",lambda q,p:q.__setitem__("terminal_finalization_complete",False),"Loaded worker terminal evidence incomplete"),
      ("inventory_incomplete",lambda q,p:q.__setitem__("terminal_inventory_complete",False),"Loaded worker terminal evidence incomplete"),
      ("terminal_error",lambda q,p:q["terminal_errors"].append({"error":"injected"}),"Loaded worker terminal evidence incomplete"),
      ("terminal_action_missing",lambda q,p:q["terminal_actions"].pop(),"Loaded worker terminal action set changed"),
      ("save_not_attempted",lambda q,p:q.__setitem__("terminal_save_attempted",False),"Loaded worker has a terminal primary failure"),
      ("active_primary",lambda q,p:q.__setitem__("active_primary_exception_before_terminal",{"error":"injected"}),"Loaded worker has a terminal primary failure"),
      ("wrong_fresh_run",lambda q,p:q["composition_source"].__setitem__("run",1),"Loaded fresh composition source changed"),
      ("wrong_fresh_source",lambda q,p:q["composition_source"].__setitem__("source_head","0"*40),"Loaded fresh composition source changed"),
      ("wrong_fresh_summary",lambda q,p:q["composition_source"].__setitem__("summary_sha256","0"*64),"Loaded fresh composition source changed"),
      ("old_physical_failure_relabelled",lambda q,p:q["composition_source"].__setitem__("original_physical_status","PASS"),"Original physical or electrical failure lost"),
      ("old_electrical_failure_lost",lambda q,p:q["composition_source"].__setitem__("original_eight_electrical_rejections_and_two_fault_detections_preserved",False),"Original physical or electrical failure lost"),
      ("unexpected_geometry",lambda q,p:q["composition_source"].__setitem__("geometry_regenerated",True),"Loaded preparation scope changed"),
      ("archive_member_missing",lambda q,p:q["composition_source"]["full_archive"]["complete_member_hashes"].pop(next(iter(q["composition_source"]["full_archive"]["complete_member_hashes"]))),"Loaded complete archive proof changed"),
      ("archive_member_changed",lambda q,p:q["composition_source"]["full_archive"]["complete_member_hashes"][next(iter(q["composition_source"]["full_archive"]["complete_member_hashes"]))].__setitem__("sha256","0"*64),"Loaded complete archive proof changed"),
      ("wrong_current_planes",lambda q,p:q["native_plane_source"].__setitem__("native_planes_sha256","0"*64),"Loaded current plane/model binding changed"),
      ("ordered_public_ports_swapped",lambda q,p:q["binding"]["ports"].__setitem__(slice(19,21),list(reversed(q["binding"]["ports"][19:21]))),"Loaded current ordered interface changed"),
      ("prepared_vectors_changed",lambda q,p:p["vectors"].__setitem__(0,p["vectors"][0]+"_changed"),"Original acquired preparation vector census changed"),
      ("prepared_save_order_changed",lambda q,p:p["native_save_commands"].__setitem__(0,p["native_save_commands"][0]+" changed"),"Original native save command order changed")]
    for name,mutate,reason in faults:reject(name,mutate,reason)
    try:g.validate(r,"clock_stopped",False,0,None)
    except AssertionError as error:assert error.args==("Same-run preparation report required",)
    else:raise AssertionError("Accepted missing same-run preparation")
    cases.append({"name":"missing_preparation","reason":"Same-run preparation report required"})
    fn,_=g.validator()
    original_faults=[
      ("native_OFF_count",lambda q:q.__setitem__("native_flags_verified",123),
       "r['returncode']==0 and not r['diagnostics']and r['native_flags_verified']==124"),
      ("zero_OP_boundary",lambda q:q.__setitem__("zero_source_op_maximum",1e-9),
       "0<=r['zero_source_op_maximum']<1e-9"),
      ("intentional_fault_not_detected",lambda q:q.__setitem__("actual_fault_detected",False),
       "r['actual_fault_detected']if case in ('clock_stopped','vi_bias_off')else r['devices_passed']and r['data_passed']and r['vi']['passed']"),
      ("missing_binding_fault",lambda q:q["binding_controls"]["rejected"].pop(),
       "len(r['source_bits'])==256 and len(r['binding_controls']['rejected'])==13"),
      ("missing_native_MIM",lambda q:q["native_caps"].pop(next(iter(q["native_caps"]))),
       "len(r['devices'])==124 and len(r['mos_devices'])==50 and len(r['native_caps'])==7")]
    for name,mutate,assertion in original_faults:
        report=copy.deepcopy(r);before=json.dumps(report,sort_keys=True);mutate(report)
        assert json.dumps(report,sort_keys=True)!=before
        frame=original_assertion_refusal(fn,report,"clock_stopped",0,assertion)
        cases.append({"name":name,**frame})
    assert len(cases)==24
    return {"positive_modes":["synthetic_current_preparation","synthetic_current_fault_case"],
      "rejected":cases,"actual_current_simulation_claimed":False,
      "fixture_scope":"Historical clock-stopped measured values plus explicit synthetic current-source/terminal metadata. No normal old rejected case is converted to a passed electrical result."}

def controls():
    assert a.methods()["source_controls_authorized"]is True
    historical,fault=historical_controls()
    return {"status":"PASS_ORIGINAL_LOADED_RESULT_PREDICATES_AND_CURRENT_BINDINGS",
      "historical":historical,"current":current_controls(fault),
      "all_original_numerical_thresholds_unchanged":True,"numerical_worker_executed":False,
      "archive_accessed":False,"simulator_executed":False}

def main():
    try:result=controls()
    except BaseException as error:
        result={"status":"FAIL_LOADED_RESULT_CONTROLS","error":repr(error),"traceback":traceback.format_exc()}
        print(json.dumps(result,indent=2,sort_keys=True));raise
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=="__main__":main()
