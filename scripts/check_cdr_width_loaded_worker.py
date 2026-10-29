#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted source/result controls; never import the numerical worker or acquire native data."""
import argparse,ast,copy,hashlib,json,os,traceback
from pathlib import Path
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
REVIEW="docs/evidence/cdr-width-loaded-worker-derivation-review-20261029.json"

def read(path,digest):
    p=ROOT/path
    assert p.is_file()and not p.is_symlink(),path
    data=p.read_bytes();assert hashlib.sha256(data).hexdigest()==digest,path
    return data

def derivation_controls():
    audit=json.loads((ROOT/REVIEW).read_bytes());results={}
    for label in ("worker","result"):
        unit=audit["derivations"][label]
        before=read(unit["baseline"]["path"],unit["baseline"]["sha256"])
        after=read(unit["generated"]["path"],unit["generated"]["sha256"])
        text=before.decode()
        for change in unit["exact_reversible_edits"]:
            assert text.count(change["before"])==1
            text=text.replace(change["before"],change["after"])
        assert text.encode()==after
        for change in reversed(unit["exact_reversible_edits"]):
            assert text.count(change["after"])==1
            text=text.replace(change["after"],change["before"])
        assert text.encode()==before
        results[label]={"exact_forward_reverse":True,"literal_edits":len(unit["exact_reversible_edits"])}
    coordinate=audit["frozen_numerical_block_coordinate_source"]
    original=read(coordinate["path"],coordinate["sha256"])
    unit=audit["derivations"]["worker"]
    old=read(unit["baseline"]["path"],unit["baseline"]["sha256"])
    new=read(unit["generated"]["path"],unit["generated"]["sha256"])
    for row in audit["unchanged_numerical_blocks"]:
        block=b"".join(original.splitlines(keepends=True)[row["start_line"]-1:row["end_line"]])
        assert len(block)==row["bytes"]and hashlib.sha256(block).hexdigest()==row["sha256"]
        assert old.count(block)==new.count(block)==1
    functions=lambda raw:{n.name:ast.dump(n)for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef)}
    bf,af=functions(old),functions(new)
    assert bf.keys()==af.keys()and[k for k in bf if bf[k]!=af[k]]==["main"]
    terminal=audit["unchanged_terminal_helper"];read(terminal["path"],terminal["sha256"])
    assert "loaded_terminal.finalize(out,r,save,current_inputs)"in new.decode()
    assert "import cdr_v59_tail_loaded_terminal as loaded_terminal"in new.decode()
    results.update(numerical_blocks=6,numerical_bytes=sum(x["bytes"]for x in audit["unchanged_numerical_blocks"]),
      only_worker_function_changed="main",terminal_helper_unchanged=True)
    return results

def original_refusal(fn,report,case,prepare,code,expression,g):
    path=ROOT/g.ORIGINAL;text=read(g.ORIGINAL,g.ORIGINAL_SHA).decode()
    node=next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)and n.name=="validate_result")
    body=ast.get_source_segment(text,node).replace(g.OLD_INVENTORY,g.NEW_INVENTORY)
    matches=[n for n in ast.walk(ast.parse(body))if isinstance(n,ast.Assert)
      and ast.dump(n.test)==ast.dump(ast.parse(expression,mode="eval").body)]
    assert len(matches)==1
    try:fn(report,case,prepare,code)
    except AssertionError as error:
        assert error.args==()
        frames=[];tb=error.__traceback__
        while tb is not None:
            frames.append((tb.tb_frame.f_code.co_name,tb.tb_frame.f_code.co_filename,tb.tb_lineno));tb=tb.tb_next
        assert ("validate_result",str(path)+"::current6647",matches[0].lineno)in frames
        return {"assertion":expression,"derived_line":matches[0].lineno}
    raise AssertionError("Original result predicate accepted altered evidence")

def historical_controls(a,g):
    contract=a.old.descriptor();fn,proof=g.validator();rows=[];fault=None
    for prior in contract["original_electrical"]["prior_cases"]:
        spec=prior["native_result"];raw=read(spec["path"],spec["sha256"]);assert len(raw)==spec["bytes"]
        original=json.loads(raw);report=copy.deepcopy(original)
        old_inventory=copy.deepcopy(report["current_saved_input_integrity"])
        report["current_saved_input_integrity"]={"files":6647,"all_hashes_unchanged":True,"exact_inventory":True}
        reverse=copy.deepcopy(report);reverse["current_saved_input_integrity"]=old_inventory
        assert reverse==original
        with mock.patch.dict(os.environ,{"GITHUB_SHA":original["source_head"]}):
            if prior["intentional_fault_case"]:
                assert prior["original_case_verdict_passed"]is True and original["actual_fault_detected"]is True
                assert fn(report,prior["case"],False,0)is True;frame=None
                if prior["case"]=="clock_stopped":fault=copy.deepcopy(report)
            else:
                assert prior["original_case_verdict_passed"]is False
                frame=original_refusal(fn,report,prior["case"],False,0,
                  "r['status']=='PASS_WHOLE_MIM_PD500_LOADED_SCREEN_NOT_CLOSED_LOOP_OR_PHY_SIGNOFF'",g)
        rows.append({"case":prior["case"],"original_status":original["status"],
          "native_sha256":spec["sha256"],"original_passed":prior["original_case_verdict_passed"],
          "original_assertion_frame":frame,"all_measured_values_unchanged":True})
    assert len(rows)==10 and sum(x["original_passed"]for x in rows)==2 and fault is not None
    return {"cases":rows,"eight_rejections_and_two_fault_detections_retained":True,
      "inventory_projection_only":True,"zero_code_used_to_reach_status_predicate":True,
      "original_validator_derivation":proof},fault

def synthetic_current(fault,a,d,remote):
    report=copy.deepcopy(fault)
    report["source_head"]=os.environ["GITHUB_SHA"]
    report.update(terminal_finalization_complete=True,terminal_inventory_complete=True,terminal_save_attempted=True,
      terminal_errors=[],active_primary_exception_before_terminal=None)
    report["terminal_actions"]=[{"action":n,"completed":True}for n in (
      "protected_sources","complete_saved_inputs","preserve_preexisting_atomic_fragment","complete_output_inventory")]
    archive={"regular_members":6647,"full_inventory_verified":True,
      "complete_member_hashes":{n:{"sha256":h}for n,h in d["complete-native-restore-map.json"].items()}}
    # This invokes the real pure six-tuple constructor with authentic JSON maps.
    # No path is opened and no archive/planes/model bytes are acquired. The
    # inventory and terminal/composition metadata represent a synthetic fixture.
    view=a.loaded_view(Path("/synthetic-not-restored"),d,archive,remote,None)
    report["composition_source"]=view[1];report["native_plane_source"]=view[5]
    external={n:"0"if n in ("avss","sub","wire_cref")else n for n in d["direct/composition.json"]["interface"]}
    report["binding"]["interface"]=external
    report["binding"]["ports"]=[external[n]for n in d["direct/composition.json"]["interface"]]
    preparation=copy.deepcopy(report)
    preparation.update(case="nominal_early",status="PASS_PD500_LOADED_PREPARATION_AND13_BINDING_CONTROLS_NO_TRANSIENT",transient_executed=False)
    return report,preparation

def current_controls(a,g,fault):
    d=a.source_guard()
    remote=a.validate_live(d["run.json"],d["jobs.json"],d["release.json"],d["tag-ref.json"],d)
    report,preparation=synthetic_current(fault,a,d,remote)
    # Authenticate the complete docs once, then reuse that exact immutable
    # in-memory object for repeated pure result checks. No transport is replaced.
    cases=[]
    with mock.patch.object(a,"source_guard",return_value=d):
        assert g.validate(preparation,"nominal_early",True,0)["complete_current_members"]==6647
        assert g.validate(report,"clock_stopped",False,0,preparation)["fresh_RC_run"]==a.RUN
        def reject(name,mutate,reason):
            r,p=copy.deepcopy((report,preparation));before=json.dumps([r,p],sort_keys=True)
            mutate(r,p);assert json.dumps([r,p],sort_keys=True)!=before,name
            try:g.validate(r,"clock_stopped",False,0,p)
            except AssertionError as error:
                assert error.args==(reason,),(name,error.args)
                frames=[];tb=error.__traceback__
                while tb is not None:
                    frames.append((tb.tb_frame.f_code.co_name,tb.tb_frame.f_code.co_filename));tb=tb.tb_next
                assert ("validate",g.__file__)in frames,(name,frames)
            else:raise AssertionError("Accepted "+name)
            cases.append({"name":name,"reason":reason})
        provenance="Loaded current width/graph/RC provenance changed"
        faults=[
          ("wrong_RC_run",lambda r,p:r["composition_source"].__setitem__("run",1),provenance),
          ("wrong_RC_source",lambda r,p:r["composition_source"].__setitem__("source_head","0"*40),provenance),
          ("raw_summary_substitution",lambda r,p:r["composition_source"].__setitem__("raw_result_sha256",a.SUMMARY_SHA),provenance),
          ("wrong_MIM_stage",lambda r,p:r["composition_source"].__setitem__("stage_sha256","0"*64),provenance),
          ("wrong_width",lambda r,p:r["composition_source"].__setitem__("original_width_run",1),provenance),
          ("wrong_graph",lambda r,p:r["composition_source"].__setitem__("original_graph_run",1),provenance),
          ("old_graph_count",lambda r,p:r["composition_source"].__setitem__("complete_graph_members",3823),provenance),
          ("current_root_count",lambda r,p:r["composition_source"].__setitem__("current_members",76),provenance),
          ("lost_historical_failure",lambda r,p:r["composition_source"].__setitem__("historical_failed_geometry_and_electrical_reports_retained",False),provenance),
          ("preaccepted_simulation",lambda r,p:r["composition_source"].__setitem__("simulation_preaccepted",True),provenance),
          ("wrong_reservation",lambda r,p:r["composition_source"]["reservation"].__setitem__("synthetic_wrong",True),provenance),
          ("changed_live_producer",lambda r,p:r["composition_source"]["live_producer"].__setitem__("assets",19),provenance),
          ("old_archive_count",lambda r,p:r["composition_source"]["full_archive"].__setitem__("regular_members",3823),"Loaded complete archive proof changed"),
          ("partial_archive",lambda r,p:r["composition_source"]["full_archive"].__setitem__("full_inventory_verified",False),"Loaded complete archive proof changed"),
          ("missing_member",lambda r,p:r["composition_source"]["full_archive"]["complete_member_hashes"].pop(a.MODEL_MEMBER),"Loaded complete archive proof changed"),
          ("changed_raw_member",lambda r,p:r["composition_source"]["full_archive"]["complete_member_hashes"]["result.json"].__setitem__("sha256",a.SUMMARY_SHA),"Loaded complete archive proof changed"),
          ("changed_model",lambda r,p:r["composition_source"]["full_archive"]["complete_member_hashes"][a.MODEL_MEMBER].__setitem__("sha256","0"*64),"Loaded complete archive proof changed"),
          ("old_planes",lambda r,p:r["native_plane_source"].__setitem__("native_planes_sha256","0"*64),"Loaded current plane/model binding changed"),
          ("terminal_incomplete",lambda r,p:r.__setitem__("terminal_finalization_complete",False),"Loaded worker terminal evidence incomplete"),
          ("terminal_errors",lambda r,p:r["terminal_errors"].append({"error":"synthetic"}),"Loaded worker terminal evidence incomplete"),
          ("missing_terminal_action",lambda r,p:r["terminal_actions"].pop(),"Loaded worker terminal action set changed"),
          ("save_unattempted",lambda r,p:r.__setitem__("terminal_save_attempted",False),"Loaded worker has a terminal primary failure"),
          ("active_primary",lambda r,p:r.__setitem__("active_primary_exception_before_terminal",{"error":"synthetic"}),"Loaded worker has a terminal primary failure"),
          ("ports_swapped",lambda r,p:r["binding"]["ports"].reverse(),"Loaded current ordered interface changed"),
          ("prepared_vectors",lambda r,p:p["vectors"].__setitem__(0,p["vectors"][0]+"_changed"),"Original acquired preparation vector census changed"),
          ("prepared_save_order",lambda r,p:p["native_save_commands"].__setitem__(0,p["native_save_commands"][0]+" changed"),"Original native save command order changed")]
        for item in faults:reject(*item)
        try:g.validate(report,"clock_stopped",False,0,None)
        except AssertionError as error:assert error.args==("Same-run preparation report required",)
        else:raise AssertionError("Missing preparation accepted")
        cases.append({"name":"missing_preparation","reason":"Same-run preparation report required"})
    fn,_=g.validator()
    original_cases=[
      ("OFF_flags",lambda r:r.__setitem__("native_flags_verified",123),
       "r['returncode']==0 and not r['diagnostics']and r['native_flags_verified']==124"),
      ("OP_limit",lambda r:r.__setitem__("zero_source_op_maximum",1e-9),"0<=r['zero_source_op_maximum']<1e-9"),
      ("fault_not_detected",lambda r:r.__setitem__("actual_fault_detected",False),
       "r['actual_fault_detected']if case in ('clock_stopped','vi_bias_off')else r['devices_passed']and r['data_passed']and r['vi']['passed']"),
      ("lost_binding_refusal",lambda r:r["binding_controls"]["rejected"].pop(),
       "len(r['source_bits'])==256 and len(r['binding_controls']['rejected'])==13"),
      ("lost_MIM",lambda r:r["native_caps"].pop(next(iter(r["native_caps"]))),
       "len(r['devices'])==124 and len(r['mos_devices'])==50 and len(r['native_caps'])==7")]
    for name,mutate,expression in original_cases:
        r=copy.deepcopy(report);mutate(r)
        cases.append({"name":name,**original_refusal(fn,r,"clock_stopped",False,0,expression,g)})
    assert len(cases)==32
    return {"positive":2,"refusal":len(cases),"cases":cases,"complete_metadata_members":6647,
      "synthetic_current_reports":True,"actual_current_simulation_claimed":False,
      "fixture_scope":"Historical clock-stopped measurements with explicit synthetic current provenance/terminal/inventory metadata; authentic complete RC JSON documents. No old normal rejection is converted to a passed result."}

def controls():
    derivation=derivation_controls()
    import cdr_width_loaded_admission as a
    import cdr_width_loaded_result as g
    historical,fault=historical_controls(a,g)
    current=current_controls(a,g,fault)
    return {"status":"PASS_WIDTH_LOADED_WORKER_RESULT_SOURCE_CONTROLS","derivation":derivation,
      "historical":historical,"current":current,"source_controls_only":True,
      "numerical_worker_imported":False,"numerical_worker_executed":False,"native_acquisition_performed":False,
      "simulator_executed":False,"electrical_accepted":False,"full_phy_accepted":False}

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path);args=parser.parse_args()
    result=None
    try:
        assert os.environ.get("GITHUB_ACTIONS")=="true"and os.environ.get("RUNNER_ENVIRONMENT")=="github-hosted"
        assert os.environ.get("GITHUB_REPOSITORY")=="Melihakbulut221/nssoc"
        assert os.environ.get("GITHUB_EVENT_NAME")=="workflow_dispatch"and os.environ.get("GITHUB_RUN_ATTEMPT")=="1"
        result=controls()
        result["current_context"]={"source":os.environ["GITHUB_SHA"],"run_id":int(os.environ["GITHUB_RUN_ID"]),
          "attempt":1,"source_controls_only":True,"native_executed":False}
    except BaseException as error:
        result={"status":"FAIL_WIDTH_LOADED_WORKER_RESULT_SOURCE_CONTROLS","error":repr(error),
          "traceback":traceback.format_exc(),"native_executed":False}
        raise
    finally:
        if result is not None:
            text=json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n"
            if args.output:
                args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(text)
            print(text,end="")

if __name__=="__main__":main()
