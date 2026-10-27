#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted source-only derivation, complete handoff and actual worker-entry controls."""
import argparse
import ast
import copy
from contextlib import ExitStack,contextmanager
import importlib.util
import hashlib
import io
import tarfile
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch
import cdr_v59_tail_fresh_rc_legacy as a
from run_cloud_tx_layout_repair import sha

ROOT=Path(__file__).resolve().parents[1]
AUDIT="docs/evidence/cdr-v59-tail-fresh-rc-numerical-worker-derivation-20261027.json"
ENV={"GITHUB_SHA":"1"*40,"GITHUB_RUN_ID":"101","GITHUB_RUN_ATTEMPT":"1","GITHUB_ACTIONS":"true","PYTHONDONTWRITEBYTECODE":"1"}
SAVED={"synthetic_saved_integrity_boundary":True}
class BoundaryStop(RuntimeError):pass

def reject(label,fn,message,kind=AssertionError):
    try:fn()
    except kind as error:
        assert str(error)==message,(label,type(error).__name__,str(error),message)
        return {"case":label,"rejected":True,"type":type(error).__name__,"reason":str(error)}
    raise AssertionError("Accepted "+label)

def derivation(record=None,overrides=None):
    record=record or json.loads((ROOT/AUDIT).read_text());overrides=overrides or {}
    result=[]
    for row in record["derivations"]:
        old=(ROOT/row["original_path"]).read_text()
        new=overrides.get(row["stage"],(ROOT/row["derived_path"]).read_text())
        assert sha(ROOT/row["original_path"])==row["original_sha256"]
        actual=old
        for edit in row["edits"]:
            assert actual.count(edit["before"])==1,"Original derivation span is not unique"
            actual=actual.replace(edit["before"],edit["after"])
        assert new==actual,"Exact numerical derivation changed"
        reverse=new
        for edit in reversed(row["edits"]):
            assert reverse.count(edit["after"])==1,"Derived span is not unique"
            reverse=reverse.replace(edit["after"],edit["before"])
        assert reverse==old,"Original worker bytes did not reverse"
        oldtree=ast.parse(old);newtree=ast.parse(new)
        olddefs={n.name:n for n in oldtree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
        newdefs={n.name:n for n in newtree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
        assert olddefs.keys()==newdefs.keys()
        changed=[n for n in olddefs if ast.dump(olddefs[n],include_attributes=False)!=ast.dump(newdefs[n],include_attributes=False)]
        assert changed==row["changed_function_ASTs"]
        for name in row["byte_exact_functions"]:
            assert ast.get_source_segment(old,olddefs[name])==ast.get_source_segment(new,newdefs[name])
        result.append({"stage":row["stage"],"reversed_byte_exact":True,"changed_ASTs":changed,
          "exact_numerical_functions":row["byte_exact_functions"]})
    return result

def derivation_controls():
    positive=derivation();negative=[]
    mutations={
      "binding":("len(ports)==len(set(ports))==25","len(ports)==len(set(ports))==24"),
      "rc":("original_devices=500","original_devices=499"),
      "capture":("L.dbu==.001","L.dbu==.002"),
      "audit":("len(r['wire_controls']['cases'])==13","len(r['wire_controls']['cases'])==12"),
      "precision":("for variant in ('precise','precise_reversed'):","for variant in ('precise',):")}
    for stage,(old,new) in mutations.items():
        text=a.derived(stage).read_text()
        assert text.count(old)==1,(stage,old,text.count(old))
        negative.append(reject(stage+"_numeric_or_order_change",lambda stage=stage,text=text,old=old,new=new:
          derivation(overrides={stage:text.replace(old,new)}),"Exact numerical derivation changed"))
    return {"positive":positive,"negative":negative}

def put(path,value):
    if isinstance(value,bytes):path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(value)
    else:a.source.write(path,value)

@contextmanager
def fixture():
    with tempfile.TemporaryDirectory() as directory,ExitStack() as stack:
        root=Path(directory);out=root/"out";current=root/"canonical";saved=root/"saved"
        for path in (out,current,saved):path.mkdir()
        binding=out/"binding";rc=out/"wire-stage";mim=out/"mim"
        for path in (binding,rc):path.mkdir()
        graph={"native_device_count":500,"native_terminal_count":1446,"wire_component_count":113}
        anchors={"logical_anchor_count":978,"physical_anchor_count":978,"public_ports":25,
          "dispositions":{"ACTUAL_TERMINAL_METAL_POINT_REFERENCE":953,"RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE":493}}
        put(current/"wire/native05/result.json",graph);put(current/"wire/anchors08.json",anchors)
        put(current/".hidden",b"unchanged original");put(current/"empty",b"")
        original=a.inventory(current);put(current/"wire/fresh-rc.spice",b"* synthetic handoff, no native RC\nR1 a b 1\nC1 a b 2e-15\n")
        for path in (binding,rc):
            put(path/".hidden",b"retain");put(path/"empty",b"")
        devices=[{"native_id":i,"native_model":"rppd","model":"rppd","native_parameters":{},"parameters":{}} for i in range(1,501)]
        for ident in a.numerical.TARGETS:
            devices[ident-1].update(native_parameters={"w":"4","l":"5","ps":"0","b":"0","m":"1"},
              parameters={"w":"4u","l":"5u"})
        bound={"devices":devices,"census":a.numerical.CENSUS,"native_ports":["p"+str(i) for i in range(25)],
          "node_map":{str(i):str(i) for i in range(114)}}
        put(binding/"binding.json",bound)
        common={"source_head":ENV["GITHUB_SHA"],"sources_unchanged":True,"qualified_pex":False,"full_phy_accepted":False,
          "closed_loop":False,"saved_capsule_integrity":SAVED}
        binding_report=dict(common,status=a.PASS["binding"],binding=bound,controls=[{"rejected":True}for _ in range(14)],
          target_length_controls={"actual_fresh_binding":True,"rejected":list(range(6))},
          native_contact_comparisons=[{"explicitly_synthetic":True}for _ in range(221)],
          contact_model_controls={"rejected_geometry":list(range(3)),"rejected_compact_models":list(range(3))},
          native_simulation_passed=False,wire_rc_included=False)
        rc_report=dict(common,status=a.PASS["rc"],geometry=graph,anchors=anchors,
          capture={"returncode":0,"status":"NATIVE_COMPLETE_AWAITING_RC_AUDIT"},
          audit={"status":"PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY","original_devices":500,"geometry_probes":978,
            "physical_wire_components":113,"actual_exported_resistors":1,"actual_exported_capacitors":1},
          controls={"status":"PASS_REAL_NATIVE_BASELINE_AND13_RAW_CORRUPTION_CONTROLS","cases":[{"rejected":True}for _ in range(13)]},
          new_current_view_outputs={"wire/fresh-rc.spice":sha(current/"wire/fresh-rc.spice")},
          terminal_output_inventory_complete=True,terminal_output_errors=[])
        for folder,report in ((binding,binding_report),(rc,rc_report)):
            report["outputs"]=a.inventory(folder);put(folder/"result.json",report)
        pin=root/"joint-admission.json";put(pin,{"explicit_synthetic_saved_admission":True})
        values={"OUT":out,"ANALYSIS":current,"BINDING":binding,"RC_STAGE":rc,"MIM_OUT":mim,"CAPSULE":saved,
          "PIN":pin,"HANDOFF":mim/"inputs/fresh-stage-manifest.json"}
        for name,value in values.items():stack.enter_context(patch.object(a,name,value))
        stack.enter_context(patch.dict(os.environ,ENV))
        stack.enter_context(patch.object(a,"verify_saved_inputs",return_value=SAVED))
        stack.enter_context(patch.object(a.source,"contract",return_value={"canonical_candidate":{"expected_sha256":original}}))
        yield {"root":root,"current":current,"original":original,"binding":binding,"rc":rc,"mim":mim,
          "binding_report":binding_report,"rc_report":rc_report,"pin":pin}

def report_controls():
    positives=[];negatives=[]
    with fixture() as f:
        for stage in ("binding","rc"):
            got=a.stage_report(stage);assert got==f[stage+"_report"]
            positives.append({"stage":stage,"actual_validator":True,"synthetic_report_not_native_qualification":True})
        cases=[
          ("binding","source",lambda x:x.update(source_head="2"*40),"Fresh numerical stage failed or wrong source"),
          ("binding","status",lambda x:x.update(status="FAIL"),"Fresh numerical stage failed or wrong source"),
          ("binding","scope",lambda x:x.update(qualified_pex=True),"Numerical stage acceptance changed"),
          ("binding","fault",lambda x:x["controls"][0].update(rejected=False),"Fresh14 binding faults changed"),
          ("binding","target_fault",lambda x:x["target_length_controls"]["rejected"].pop(),"Fresh target-length faults changed"),
          ("binding","contact",lambda x:x["native_contact_comparisons"].pop(),"Fresh contact oracle/faults changed"),
          ("binding","simulation",lambda x:x.update(native_simulation_passed=True),"Binding scope changed"),
          ("rc","geometry",lambda x:x["geometry"].update(native_device_count=499),"Fresh RC geometry/anchor source mismatch"),
          ("rc","capture",lambda x:x["capture"].update(returncode=1),"Fresh RC capture incomplete"),
          ("rc","audit",lambda x:x["audit"].update(geometry_probes=977),"Fresh strict RC audit changed"),
          ("rc","boolean_R_count",lambda x:x["audit"].update(actual_exported_resistors=True),"Fresh actual R/C counts invalid"),
          ("rc","zero_C_count",lambda x:x["audit"].update(actual_exported_capacitors=0),"Fresh actual R/C counts invalid"),
          ("rc","fault_count",lambda x:x["controls"]["cases"].pop(),"Fresh13 raw RC faults changed"),
          ("rc","fresh_output",lambda x:x["new_current_view_outputs"].clear(),"Fresh complete current output-map changed")]
        for stage,label,mutate,message in cases:
            value=copy.deepcopy(f[stage+"_report"]);mutate(value);put(f[stage]/"result.json",value)
            negatives.append(reject(label,lambda stage=stage:a.stage_report(stage),message))
            put(f[stage]/"result.json",f[stage+"_report"])
        put(f["binding"]/"unexpected",b"unlisted")
        negatives.append(reject("unlisted_complete_stage_file",lambda:a.stage_report("binding"),"Fresh complete stage output inventory changed"))
    assert len(positives)==2 and len(negatives)==15
    return {"positive":positives,"negative":negatives}

def handoff_controls():
    positives=[];negative=[]
    with fixture() as f:
        f["mim"].mkdir();h=a.restore_inputs()
        assert h["binding"]["run"]==h["rc"]["run"]==101
        assert h["binding"]["source_head"]==h["rc"]["source_head"]==ENV["GITHUB_SHA"]
        assert h["complete_current_view_files"]==a.inventory(f["current"])
        assert len(h["complete_current_view_files"])==5
        assert h["historical763_1136_1127_counts_reused"] is False
        for order in ("precise","precise_reversed"):
            out=f["mim"]/order;out.mkdir()
            prior,proof,bound,bproof,binding=a.project_for_capture(out)
            assert prior==f["rc_report"] and bound==f["binding_report"] and binding==bound["binding"]
            assert proof["summary_sha256"]==h["rc"]["summary_sha256"]
            assert bproof["summary_sha256"]==a.binding_pin()["summary_sha256"]
            assert (out/"source/empty").read_bytes()==(out/"model-binding/empty").read_bytes()==b""
            assert (out/"source/.hidden").read_bytes()==b"unchanged original"
            assert (out/"model-binding/.hidden").read_bytes()==b"retain"
            a.verify_projection(out)
            positives.append({"order":order,"complete_source":a.inventory(out/"source"),
              "complete_binding":a.inventory(out/"model-binding"),"actual_copy_and_verification":True})
        for label,key,value in (("wrong_run","run",102),("wrong_source","source_head","2"*40)):
            bad=copy.deepcopy(h);bad[key]=value;put(a.HANDOFF,bad)
            negative.append(reject(label,a.verify_restored,"Fresh handoff source/run mismatch"));put(a.HANDOFF,h)
        bad=copy.deepcopy(h);bad["historical763_1136_1127_counts_reused"]=True;put(a.HANDOFF,bad)
        negative.append(reject("historical_identity",a.verify_restored,"Historical bundle relabelled"));put(a.HANDOFF,h)
        negative.append(reject("repeat_handoff",a.restore_inputs,"Fresh MIM handoff already exists or root missing"))
        negative.append(reject("wrong_order",lambda:a.project_for_capture(f["mim"]/"reordered"),"Wrong fresh native order"))
        negative.append(reject("wrong_order_parent",lambda:a.project_for_capture(f["root"]/"precise"),"Wrong fresh native order"))
        out=f["mim"]/"precise"
        negative.append(reject("repeat_projection",lambda:a.project_for_capture(out),"Numerical projection destination exists"))
        p=out/"source/wire/fresh-rc.spice";old=p.read_bytes();p.write_bytes(old+b"corrupt")
        negative.append(reject("projected_current_corrupt",lambda:a.verify_projection(out),"Numerical input digest changed: wire/fresh-rc.spice"));p.write_bytes(old)
        p=out/"model-binding/.hidden";old=p.read_bytes();p.write_bytes(b"corrupt")
        negative.append(reject("projected_unselected_binding_corrupt",lambda:a.verify_projection(out),"Numerical input digest changed: .hidden"));p.write_bytes(old)
        p=out/"source/unlisted";p.write_bytes(b"unlisted")
        negative.append(reject("projected_extra",lambda:a.verify_projection(out),"Complete numerical inventory changed"));p.unlink()
        p=out/"source/empty";p.unlink();p.symlink_to(out/"source/.hidden")
        negative.append(reject("projected_symlink",lambda:a.verify_projection(out),"Symlink in protected path"))
    assert len(positives)==2 and len(negative)==11
    return {"positive":positives,"negative":negative,
      "scope":"Actual complete inventory and both-order copy APIs with explicit synthetic stages; not extracted native RC."}

def load_worker(stage):
    path=a.derived(stage)
    spec=importlib.util.spec_from_file_location("_tail_worker_fixture_"+stage,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def main_entry_controls():
    results=[]
    # Exact current worker main() is entered; transport stops occur before archives/CAD.
    with tempfile.TemporaryDirectory() as directory,ExitStack() as stack:
        root=Path(directory);current=root/"canonical";current.mkdir();saved=root/"saved";saved.mkdir()
        pin=root/"joint.json";put(pin,{"fixture":True})
        selected=["wire/device-locations01.json","parent/layout/result.json","parent/layout/schematic.cir",
          "parent/physical/lvs_flat/extracted.cir","parent/physical/lvs_flat/audit.json","parent/physical/lvs_flat/result.lvsdb"]
        required=list(dict.fromkeys(selected+["result.json","wire/anchors08.json"]))
        for name in required:put(current/name,("synthetic bytes "+name).encode())
        expected=a.inventory(current)
        for name,value in {"ANALYSIS":current,"CAPSULE":saved,"PIN":pin,"BINDING":root/"binding"}.items():stack.enter_context(patch.object(a,name,value))
        stack.enter_context(patch.object(a.source,"contract",return_value={"canonical_candidate":{"expected_sha256":expected}}))
        stack.enter_context(patch.object(a,"validate_summary",return_value={"fixture":True}))
        stack.enter_context(patch.object(a,"verify_saved_inputs",return_value=SAVED))
        stack.enter_context(patch.object(a,"authorize",return_value=None))
        stack.enter_context(patch.dict(os.environ,ENV))
        binding=load_worker("binding");stop=BoundaryStop("STOP_BEFORE_FIRST_BINDING_ARCHIVE")
        with patch.object(binding,"OUT",a.BINDING),patch.object(binding,"PIN",pin),patch.object(binding,"validate_source",return_value=None),patch.object(binding,"validate_methods",return_value=None),patch.object(binding.sys,"argv",[str(binding.__file__)]),patch.object(binding,"fetch",side_effect=stop) as network,patch.object(binding.reports,"OUT",a.BINDING):
            try:binding.main()
            except BoundaryStop as error:assert error is stop
            else:raise AssertionError("Binding did not stop before archive")
            assert network.call_count==1
        r=json.loads((a.BINDING/"result.json").read_text())
        assert r["status"]=="FAIL_OR_ERROR" and r["error"]==repr(stop) and r["saved_capsule_integrity"]==SAVED
        assert r["physical_source"]["complete_original_candidate_outputs"]==expected
        assert r["physical_source"]["original_failed_physical_status"]=="FAIL_ADDITIVE_TAIL_WIRE_PHYSICAL"
        assert a.inventory(a.BINDING/"inputs")=={n:expected[n]for n in selected}
        results.append({"stage":"binding","actual_main":True,"actual_selected_copy":True,"full_failure_saved":True,"network_calls":1})
    # Fresh precision entry executes actual handoff before the first numerical helper.
    with fixture() as f:
        precision=load_worker("precision");stop=BoundaryStop("STOP_AFTER_FRESH_HANDOFF")
        with patch.object(precision,"OUT",f["mim"]),patch.object(precision,"check",return_value={}),patch.object(a,"authorize",return_value=None),patch.object(precision,"count_controls",side_effect=stop) as boundary:
            try:precision.main()
            except BoundaryStop as error:assert error is stop
            else:raise AssertionError("Precision did not reach handoff boundary")
            boundary.assert_called_once()
        r=json.loads((f["mim"]/"result.json").read_text())
        assert r["status"]=="FAIL_OR_ERROR" and r["error"]==repr(stop)
        assert r["current_input_restoration"]==a.handoff()
        assert r["outputs"]["inputs/fresh-stage-manifest.json"]==sha(a.HANDOFF)
        results.append({"stage":"precision","actual_main":True,"actual_handoff":True,"full_failure_saved":True,"native_calls":0})
    assert len(results)==2
    return results


def rc_full_main_case(mode,old_worker=None):
    """Actual complete main, real temp transport files and unchanged method adaptation; no CAD."""
    assert mode in ("success","inventory","source_corruption","body_inventory")
    worker=load_worker("rc") if old_worker is None else old_worker
    with tempfile.TemporaryDirectory() as directory,ExitStack() as stack:
        root=Path(directory);current=root/"canonical";current.mkdir()
        saved=root/"saved";saved.mkdir();stage=root/"stage";pin=root/"joint.json";put(pin,{"synthetic":True})
        graph={"native_device_count":500,"native_terminal_count":1446,"wire_component_count":113}
        anchors={"logical_anchor_count":978,"physical_anchor_count":978,"public_ports":25,
          "dispositions":{"ACTUAL_TERMINAL_METAL_POINT_REFERENCE":953,"RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE":493}}
        put(current/"wire/native05/result.json",graph)
        put(current/"source-identity",b"explicit synthetic current input")
        anchors["inputs"]={str(current/"wire/native05/result.json"):sha(current/"wire/native05/result.json"),
          str(current/"source-identity"):sha(current/"source-identity")}
        put(current/"wire/anchors08.json",anchors);original=a.inventory(current)
        put(root/"protected-source.py",b"# exact fixture source\n")
        method=json.loads((ROOT/"scripts/cdr-v59-tail-fresh-rc-methods.json").read_text())
        method["protected_sha256"]={"protected-source.py":sha(root/"protected-source.py")}
        methodpath=root/"method.json";put(methodpath,method)
        entries={"runtime/lib/fixture.so":b"synthetic runtime never loaded","tech/fixture.tech":b"synthetic technology never loaded"}
        entries["manifest.json"]=(json.dumps({"files":{n:{"sha256":hashlib.sha256(b).hexdigest()}for n,b in entries.items()}})+"\n").encode()
        packed=io.BytesIO()
        with tarfile.open(fileobj=packed,mode="w:gz") as tar:
            for name,data in entries.items():
                info=tarfile.TarInfo(name);info.size=len(data);tar.addfile(info,io.BytesIO(data))
        archive=packed.getvalue();raw=b"# synthetic parser never executed\n"
        put(root/"docs/evidence/pcie-magic-cloud-runtime-20261013.json",{"receipt":{"url":"fixture://runtime","sha256":hashlib.sha256(archive).hexdigest()}})
        put(root/"docs/evidence/pcie-tx-cloud-extraction-input-20261013.json",{"raw_parser":{"url":"fixture://parser","sha256":hashlib.sha256(raw).hexdigest()}})
        put(root/"docs/evidence/cdr-v4-rc-inputs-20261017.json",(ROOT/"docs/evidence/cdr-v4-rc-inputs-20261017.json").read_bytes())
        for name,value in {"ANALYSIS":current,"CAPSULE":saved,"RC_STAGE":stage,"PIN":pin}.items():stack.enter_context(patch.object(a,name,value))
        stack.enter_context(patch.object(a.source,"ROOT",root));stack.enter_context(patch.object(a.source,"METHOD",methodpath))
        gate_errors=[];contract_errors=[]
        def checked_saved(_):
            try:a.source.methods()
            except BaseException as error:gate_errors.append(error);raise
            a.verify_table(current,original,exact=False)
            return SAVED
        def checked_contract():
            try:a.source.methods()
            except BaseException as error:contract_errors.append(error);raise
            return {"canonical_candidate":{"expected_sha256":original}}
        stack.enter_context(patch.object(a.source,"contract",side_effect=checked_contract))
        stack.enter_context(patch.object(a,"verify_saved_inputs",side_effect=checked_saved))
        stack.enter_context(patch.object(a,"validate_summary",return_value={"synthetic":True}))
        stack.enter_context(patch.object(a,"authorize",return_value=None))
        stack.enter_context(patch.dict(os.environ,ENV))
        fetches=[];commands=[]
        def transport(url,digest,path):
            data={"fixture://runtime":archive,"fixture://parser":raw}[url]
            assert hashlib.sha256(data).hexdigest()==digest
            put(Path(path),data);fetches.append(url)
        def subprocess_call(command,**kwargs):
            command=list(map(str,command));commands.append(command)
            if command[1:3]==["-m","py_compile"]:
                assert len(command)==6
            elif command[1].endswith("/run-rc01.py"):
                if mode=="body_inventory":return 1
                put(current/"wire/rc03/result.json",{"returncode":0,"status":"NATIVE_COMPLETE_AWAITING_RC_AUDIT"})
                put(current/"wire/rc03/wires.spice",b"* synthetic RC fixture, never native\nR1 a b 1\nC1 a b 2e-15\n")
            elif command[1].endswith("/audit-rc48.py"):
                put(current/"wire/audit.json",{"status":"PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY"})
            elif command[1].endswith("/mutations48.py"):
                put(current/"wire/native-mutations01.json",{"status":"PASS_REAL_NATIVE_BASELINE_AND13_RAW_CORRUPTION_CONTROLS","cases":[{"synthetic":True}for _ in range(13)]})
                if mode=="source_corruption":put(root/"protected-source.py",b"# changed actual protected fixture bytes\n")
            else:raise AssertionError("Unexpected synthetic native command "+repr(command))
            return 0
        injected=RuntimeError("INJECTED_CURRENT_OUTPUT_INVENTORY_FAILURE")
        if mode in ("inventory","body_inventory"):stack.enter_context(patch.object(a,"new_current_outputs",side_effect=injected))
        for name,value in {"ROOT":root,"OUT":current,"STAGE":stage,"PIN":pin}.items():stack.enter_context(patch.object(worker,name,value))
        stack.enter_context(patch.object(worker,"validate_source",return_value=None))
        stack.enter_context(patch.object(worker,"validate_methods",side_effect=a.source.methods))
        stack.enter_context(patch.object(worker,"fetch",side_effect=transport))
        stack.enter_context(patch.object(worker.subprocess,"call",side_effect=subprocess_call))
        stack.enter_context(patch.object(worker.reports,"OUT",stage))
        caught=None
        try:worker.main()
        except BaseException as error:caught=error
        report=json.loads((stage/"result.json").read_text())
        assert fetches==["fixture://runtime","fixture://parser"]
        assert len(commands)==(2 if mode=="body_inventory" else 4)
        if old_worker is not None:
            assert mode=="inventory" and caught is injected
            assert report["status"]=="RUNNING" and "terminal_output_errors" not in report
            assert "sources_unchanged" not in report
        elif mode=="success":
            assert caught is None and report["status"]==a.PASS["rc"]
            assert report["terminal_output_inventory_complete"] is True and report["terminal_output_errors"]==[]
        elif mode=="inventory":
            assert caught is injected and report["status"]=="FAIL_V59_TERMINAL_OUTPUT_INVENTORY"
            assert report["terminal_output_errors"][0]["error"]==repr(injected)
            assert report["active_primary_exception_before_inventory"] is None
        elif mode=="body_inventory":
            assert type(caught) is AssertionError and caught.args==(("native-extraction",1),)
            assert report["status"]=="FAIL_OR_ERROR" and report["error"]==repr(caught)
            assert report["active_primary_exception_before_inventory"]==repr(caught)
            assert report["terminal_output_errors"][0]["error"]==repr(injected)
        else:
            assert len(gate_errors)==2 and len(contract_errors)==1
            assert caught is gate_errors[-1]
            assert str(caught)=="Protected source or evidence changed: protected-source.py"
            assert report["status"]=="FAIL_V59_SAVED_INPUT_INTEGRITY"
            assert report["error"]==repr(gate_errors[0]) and report["integrity_error"]==repr(gate_errors[1])
            assert report["active_primary_exception_before_inventory"]==repr(caught)
            assert report["terminal_output_errors"][0]["error"]==repr(contract_errors[0])
        if old_worker is None:
            assert report["outputs"]=={n:h for n,h in a.inventory(stage).items() if n!="result.json"}
            assert report["terminal_output_inventory_complete"] is (mode=="success")
        return {"mode":mode,"old_worker":old_worker is not None,"actual_main":True,
          "saved_status":report["status"],"error":repr(caught)if caught is not None else None,
          "complete_stage_files":a.inventory(stage),"terminal_output_errors":report.get("terminal_output_errors"),
          "fixture_transport_and_native_subprocesses_are_synthetic":True}

def rc_terminal_controls():
    path=ROOT/"docs/evidence/cdr-v59-tail-fresh-wire-RC-pre-finalization-20261027.py"
    assert sha(path)=="0456b951b669dbe49395635b93bb74defb2d8aefda8fb77f7a813db025cfb8a9"
    spec=importlib.util.spec_from_file_location("_tail_previous_RC_finally",path)
    old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    reproduced=rc_full_main_case("inventory",old)
    cases=[rc_full_main_case(mode)for mode in ("success","inventory","source_corruption","body_inventory")]
    return {"cases":cases,"exact_previous_stale_failure":reproduced,"positive":1,
      "expected_current_failures":3,"original_failure_reproduced":True}

def controls():
    a.methods()
    d=derivation_controls();r=report_controls();h=handoff_controls();entries=main_entry_controls();terminal=rc_terminal_controls()
    result={"status":"PASS_DISABLED_FRESH_NUMERICAL_DERIVATION_AND_SYNTHETIC_HANDOFF_CONTROLS",
      "derivation":d,"report_schema":r,"handoff":h,"actual_main_entries":entries,"RC_terminal":terminal,
      "positive_groups":8,"refusals":34,"authored_native_execution":False,
      "synthetic_stages_are_not_actual_native_qualification":True,
      "unfinished_entry_scopes":["MIM capture main after full projection","MIM audit main after source/hash guards"]}
    assert len(d["negative"])+len(r["negative"])+len(h["negative"])+terminal["expected_current_failures"]==34
    a.methods();return result

def main():
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path,required=True);args=p.parse_args()
    a.source.write(args.out,controls())

if __name__=="__main__":main()
