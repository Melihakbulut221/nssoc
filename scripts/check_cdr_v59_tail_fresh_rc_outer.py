#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted controls enter the actual outer driver; numerical/remote transports are synthetic."""
import argparse
import copy
from contextlib import contextmanager,ExitStack
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import types
from unittest.mock import patch
import cloud_cdr_v59_tail_fresh_rc as d
import check_cdr_v59_tail_fresh_rc_workers as workers

s=d.source
a=d.stages
ENV={**workers.ENV,"GITHUB_REPOSITORY":"Melihakbulut221/nssoc"}
class FixtureFailure(RuntimeError):pass

@contextmanager
def remote():
    tag="cloud-results-101-1-"+d.GROUP
    value={"id":123,"tag_name":tag,"target_commitish":ENV["GITHUB_SHA"],
      "draft":False,"prerelease":True,"assets":[]}
    ref={"ref":"refs/tags/"+tag,"object":{"type":"commit","sha":ENV["GITHUB_SHA"]}}
    uploaded={};lookups=[]
    def api(path,missing=False):
        lookups.append(path)
        if path=="releases/tags/"+tag:return copy.deepcopy(value)
        if path=="git/ref/tags/"+tag:return copy.deepcopy(ref)
        raise AssertionError("Unexpected fixture remote API: "+path)
    def upload(argv,**kwargs):
        assert argv[:4]==["gh","release","upload",tag] and argv[-2:]==["-R","Melihakbulut221/nssoc"]
        path=Path(argv[4]);assert path.name not in uploaded
        uploaded[path.name]=path.read_bytes()
        value["assets"].append({"id":len(uploaded),"name":path.name,"size":path.stat().st_size,
          "digest":"sha256:"+s.sha(path),"browser_download_url":"https://example.invalid/"+path.name})
        return types.SimpleNamespace(returncode=0)
    real_wait=d.wait
    def wait(group,env):return real_wait(group,env,api,lambda seconds:None,lambda *args,**kw:None)
    with patch.dict(os.environ,ENV),patch.object(d.release,"api",api),patch.object(d.publisher.subprocess,"run",upload),patch.object(d,"wait",wait):
        yield {"tag":tag,"assets":uploaded,"lookups":lookups,"release":value,"ref":ref}

def assert_roundtrip(out,transport,remote,successful):
    result=s.read_json(out/"result.json")
    proof=s.read_json(transport/"publication.json")
    assert proof["status"]=="PASS_COMPLETE_FRESH_RC_EVIDENCE_PUBLISHED"
    stem=d.GROUP+"-101-1";summary=transport/(stem+".summary.json")
    assert summary.read_bytes()==(out/"result.json").read_bytes()==remote["assets"][summary.name]
    manifest=s.read_json(transport/(stem+".parts.json"))
    expected=a.inventory(out)
    recovered=out.parent/"published-roundtrip"
    s.frozen.extraction_helpers().exact_extract(manifest,transport,recovered,expected)
    assert a.inventory(recovered)==expected
    assert len(remote["assets"])==len(proof["assets"])
    for row in proof["direct_asset_bindings"]:
        raw=(out/row["output_member"]).read_bytes()
        assert remote["assets"][stem+"."+row["asset_suffix"]]==raw
        assert row["sha256"]==s.sha(out/row["output_member"])
        assert row["qualified_as_success"] is successful and row["JSON_syntax_checked"] is successful
    return {"complete_files":len(expected),"assets":len(remote["assets"]),"all_original_bytes_roundtripped":True,
      "successful":successful,"direct":proof["direct_asset_bindings"]}

def synthetic_pipeline(mim):
    variants={}
    for name in ("precise","precise_reversed"):
        root=mim/name;root.mkdir(parents=True,exist_ok=True)
        c={"native_order_variant":name,"sources_unchanged":True,
          "capture":{"status":"NATIVE_COMPLETE_AWAITING_RC_AUDIT","returncode":0},
          "native_binding":{"actual_mim_devices":7,"actual_mim_masks_exact":True,
            "original_metal_and_vias_unchanged":True,"all978points_match_original_native_clusters_and_physical_components":True,
            "point_changes":[{"synthetic":i}for i in range(7)]},
          "controls":[{"rejected":True}for _ in range(5)],
          "intrinsic_capture_binding":{"physical_components":113,"physical_points":978,
            "native_mim_devices":[{"synthetic":i}for i in range(7)]}}
        audit={"sources_unchanged":True,"audit":{"status":"PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY"},
          "wire_controls":{"cases":[{"rejected":True}for _ in range(13)]},
          "intrinsic_controls":[{"rejected":True}for _ in range(9)]}
        s.write(root/"result.json",c);s.write(root/"audit-stage/result.json",audit)
        variants[name]={"capture":c,"audit":audit}
    composition={"contract":{"counts":{"devices":500},"intrinsic_mim_models_in_final_netlist":7,
      "all_raw_wire_tokens_preserved":True},
      "controls":[{"rejected":True}for _ in range(21)],
      "non_cascading_count_derivation":{"reverse_reconstruction_exact":True}}
    s.write(mim/"composition/composition.json",composition["contract"])
    result={"status":d.PIPELINE_PASS,"source_head":ENV["GITHUB_SHA"],"sources_unchanged":True,
      "both_native_orders_verified":True,"native_rc_and_device_records_equal_in_both_orders":True,
      "qualified_pex":False,"full_phy_accepted":False,"closed_loop":False,"loaded_simulation_passed":False,
      "variants":variants,"composition":composition,
      "count_derivation_controls":{"positive_collision_cases":[0,1,2,3],"rejected":[0,1,2,3]}}
    result["outputs"]=a.inventory(mim)
    s.write(mim/"result.json",result)
    return result

def pipeline_controls():
    positives=[];refusals=[]
    with tempfile.TemporaryDirectory()as folder,patch.dict(os.environ,ENV):
        root=Path(folder)
        with patch.object(a,"MIM_OUT",root),patch.object(a,"verify_restored",return_value={"synthetic":True}):
            report=synthetic_pipeline(root)
            got=d.validate_completed_pipeline()
            assert got["complete_output_files"]==len(report["outputs"])
            assert got["original_physical_failure_relabelled"]is False and got["qualified_pex"]is False
            positives.append("actual_frozen_pipeline_and_complete_file_maps")
            cases=[
              ("wrong_source",lambda x:x.update(source_head="2"*40)),
              ("missing_order",lambda x:x["variants"].pop("precise_reversed")),
              ("R_C_order_changed",lambda x:x.update(native_rc_and_device_records_equal_in_both_orders=False)),
              ("MIM_masks",lambda x:x["variants"]["precise"]["capture"]["native_binding"].update(actual_mim_masks_exact=False)),
              ("old_metal",lambda x:x["variants"]["precise"]["capture"]["native_binding"].update(original_metal_and_vias_unchanged=False)),
              ("point_join",lambda x:x["variants"]["precise"]["capture"]["native_binding"].update(all978points_match_original_native_clusters_and_physical_components=False)),
              ("wire_fault",lambda x:x["variants"]["precise"]["audit"]["wire_controls"]["cases"].pop()),
              ("intrinsic_fault",lambda x:x["variants"]["precise"]["audit"]["intrinsic_controls"][0].update(rejected=False)),
              ("composition_fault",lambda x:x["composition"]["controls"].pop()),
              ("raw_tokens",lambda x:x["composition"]["contract"].update(all_raw_wire_tokens_preserved=False)),
              ("loaded_claim",lambda x:x.update(loaded_simulation_passed=True))]
            validator=d.pipeline_validator()
            for label,change in cases:
                bad=copy.deepcopy(report);change(bad)
                assert json.dumps(bad,sort_keys=True)!=json.dumps(report,sort_keys=True)
                try:validator(bad,0)
                except AssertionError as error:
                    tb=error.__traceback__
                    while tb.tb_next:tb=tb.tb_next
                    assert tb.tb_frame.f_code.co_name=="validate_pipeline"
                    assert Path(tb.tb_frame.f_code.co_filename)==d.ROOT/d.PIPELINE_SOURCE
                else:raise AssertionError("Accepted pipeline mutation "+label)
                refusals.append(label)
            (root/"unlisted").write_bytes(b"unlisted")
            try:d.validate_completed_pipeline()
            except AssertionError as error:assert str(error)=="Complete fresh MIM output map changed"
            else:raise AssertionError("Accepted unlisted fresh MIM output")
            refusals.append("complete_fresh_output_inventory");(root/"unlisted").unlink()
            original=(root/"composition/composition.json").read_bytes()
            s.write(root/"composition/composition.json",{"synthetic_different_contract":True})
            report["outputs"]["composition/composition.json"]=s.sha(root/"composition/composition.json")
            s.write(root/"result.json",report)
            try:d.validate_completed_pipeline()
            except AssertionError as error:assert str(error)=="Fresh composition differs from completed pipeline"
            else:raise AssertionError("Accepted changed composition at valid output digest")
            refusals.append("composition_semantics_after_valid_digest")
    assert len(positives)==1 and len(refusals)==13
    return {"positive":positives,"refusals":refusals,"synthetic_native_reports":True}

def lifecycle_controls():
    cases=[];method=s.methods()
    modes=("complete","native_failure","partial_JSON","source_corruption","saved_integrity",
      "cleanup_failure","body_and_cleanup","copy_failure","final_sample","publication_failure")
    for mode in modes:
        with workers.fixture()as f,ExitStack()as stack:
            base=f["root"];out=f["binding"].parent;seed=base/"seed";out.rename(seed)
            current_seed=base/"current-seed";f["current"].rename(current_seed)
            transport=base/"publication";restore=out/"restore";pin=restore/"joint-admission.json"
            app=base/"app";app.write_bytes(b"explicitly synthetic AppImage, never executed")
            app_sha=s.sha(app);body_error=FixtureFailure("NATIVE_BODY_FAILURE")
            cleanup_error=FixtureFailure("OWNED_CLEANUP_FAILURE");saved_error=FixtureFailure("SAVED_INPUT_FAILURE")
            sample_error=FixtureFailure("FINAL_SAMPLE_FAILURE");publication_error=FixtureFailure("PUBLICATION_FAILURE")
            state={"events":[],"cleanup":0,"sample":0};original_release=d.publisher.release
            protected=base/"protected.py";protected.write_bytes(b"synthetic protected source")
            controlled_method=copy.deepcopy(method);controlled_method["protected_sha256"]={"protected.py":s.sha(protected)}
            method_file=base/"methods.json";s.write(method_file,controlled_method)
            class Owned:
                ACTIVE=None
                def __init__(self):self.TRACE=out/"supervision";self.STOP=threading.Event()
                def interrupted(self,*args):raise FixtureFailure("SIGNAL")
                def heartbeat(self):self.STOP.wait(30)
                def stop_process(self,process):
                    state["cleanup"]+=1
                    if mode in ("cleanup_failure","body_and_cleanup"):raise cleanup_error
                    return {"remaining_live":[],"synthetic_runtime":True}
                def sample(self,label):
                    state["sample"]+=1;assert label=="fresh_RC_terminal"
                    if mode=="final_sample":raise sample_error
                    return {"synthetic_resource_sample":True}
                def supervised(self,argv,label,seconds,cwd):
                    assert label in d.SECONDS and seconds==1200 and cwd==base
                    state["events"].append(label);code=0
                    if label=="restore-complete-saved955-and-current184":
                        assert list(argv)==[sys.executable,d.__file__,"--restore-worker"]
                        shutil.copytree(current_seed,f["current"])
                        s.write(pin,{"status":"PASS_SYNTHETIC_SAVED_ADMISSION",
                          "original_physical_run_status":"FAIL_ADDITIVE_TAIL_WIRE_PHYSICAL"})
                        s.write(restore/"archive-verification.json",{"synthetic_transport":True})
                        s.write(restore/"canonical-candidate.json",{"synthetic_transport":True})
                    elif label=="fresh-current500-binding":
                        assert Path(argv[1]).name=="cloud_cdr_v59_tail_fresh_binding.py"
                        shutil.copytree(seed/"binding",out/"binding")
                    elif label=="fresh-current500-wire-RC":
                        assert Path(argv[1]).name=="cloud_cdr_v59_tail_fresh_wire_rc.py"
                        shutil.copytree(seed/"wire-stage",out/"wire-stage")
                    else:
                        assert Path(argv[1]).name=="cloud_cdr_v59_tail_fresh_mim_precision.py"
                        a.MIM_OUT.mkdir();a.restore_inputs()
                        for order in ("precise","precise_reversed"):
                            target=a.MIM_OUT/order;target.mkdir();a.project_for_capture(target)
                        synthetic_pipeline(a.MIM_OUT)
                        if mode in ("native_failure","body_and_cleanup"):code=7
                        if mode=="partial_JSON":
                            (a.MIM_OUT/"precise/result.json").write_bytes(b'{"interrupted":');code=7
                        if mode=="source_corruption":protected.write_bytes(b"changed protected source")
                        if mode=="copy_failure":(f["current"]/"bad-link").symlink_to(f["current"]/"empty")
                    record={"label":label,"argv":list(map(str,argv)),"returncode":code,"supervision_failure":None,
                      "process_group_cleanup":{"remaining_live":[]},"explicit_synthetic_numerical_transport":True}
                    for name,data in (("stdout",b"synthetic full stream\n"),("stderr",b"")):
                        path=self.TRACE/(label+"."+name);path.write_bytes(data)
                        record[name+"_bytes"]=len(data);record[name+"_sha256"]=s.sha(path)
                    s.write(self.TRACE/(label+".command.json"),record)
                    if code:raise body_error
            owned=Owned()
            def launcher(root,gate,digest):
                assert root==base and digest==method["protected_sha256"][d.runtime.PROBE]
                def probe(path,digest,folder):
                    assert path==app and digest==app_sha
                    value={"accepted":True,"synthetic_native_transport":True};s.write(folder/"result.json",value);return value
                return types.SimpleNamespace(probe=probe)
            checks={"count":0}
            def saved(pin_value):
                checks["count"]+=1
                if mode=="saved_integrity"and len(state["events"])==4:raise saved_error
                return workers.SAVED
            for owner,name,value in ((d,"ROOT",base),(d,"OUT",out),(d,"TRANSPORT",transport),(d,"APP_SHA",app_sha),
              (a,"RESTORE",restore),(a,"PIN",pin),(s,"ROOT",base),(s,"METHOD",method_file)):
                stack.enter_context(patch.object(owner,name,value))
            stack.enter_context(patch.object(s,"authorize",return_value=method))
            stack.enter_context(patch.object(a,"verify_saved_inputs",side_effect=saved))
            stack.enter_context(patch.object(a,"derived",side_effect=lambda stage:workers.ROOT/a.WORKERS[stage]))
            # The unchanged validator is loaded from the real protected source, not the synthetic root.
            original_regular=s.regular
            def regular(root,name):
                if root==base and name==d.PIPELINE_SOURCE:return original_regular(workers.ROOT,name)
                return original_regular(root,name)
            stack.enter_context(patch.object(s,"regular",side_effect=regular))
            supervisor_mock=stack.enter_context(patch.object(d.runtime,"supervisor",return_value=owned))
            stack.enter_context(patch.object(d.runtime,"launcher",side_effect=launcher))
            stack.enter_context(patch.object(d.shutil,"disk_usage",return_value=types.SimpleNamespace(free=64*1024**3)))
            stack.enter_context(patch.dict(os.environ,{**ENV,"CLOUD_APPIMAGE":str(app)}))
            stack.enter_context(patch.object(sys,"argv",["fresh-tail-RC"]))
            signals={sig:d.signal.getsignal(sig)for sig in (d.signal.SIGINT,d.signal.SIGTERM)}
            with remote()as transport_fixture:
                publication_mock=None
                if mode=="publication_failure":publication_mock=stack.enter_context(patch.object(d.publisher,"publish",side_effect=publication_error))
                caught=None
                try:d.main()
                except BaseException as error:caught=error
                result=s.read_json(out/"result.json")
                supervisor_mock.assert_called_once_with(base,out,out/"supervision",s.methods,method["protected_sha256"][d.runtime.SAMPLER])
                assert state["events"]==list(d.SECONDS) and state["cleanup"]==state["sample"]==1
                assert owned.STOP.is_set() and d.publisher.release is original_release
                assert {sig:d.signal.getsignal(sig)for sig in signals}==signals
                assert result["outputs"]=={n:h for n,h in a.inventory(out).items()if n!="result.json"}
                if mode=="complete":
                    assert caught is None and result["status"]==d.PASS and result["fresh_RC_pipeline_complete"]is True
                elif mode in ("native_failure","partial_JSON","body_and_cleanup"):
                    assert caught is body_error and result["error"]==repr(body_error)
                    assert result["status"]=="FAIL_FRESH_TAIL_RC" and result["fresh_RC_pipeline_complete"]is False
                elif mode=="cleanup_failure":
                    assert caught is cleanup_error and result["status"]=="FAIL_TERMINAL_FINALIZATION"
                elif mode=="final_sample":
                    assert caught is sample_error and result["status"]=="FAIL_TERMINAL_FINALIZATION"
                elif mode=="saved_integrity":
                    assert caught is saved_error and result["status"]=="FAIL_FRESH_TAIL_RC"
                elif mode=="source_corruption":
                    assert type(caught)is AssertionError and str(caught)=="Protected source or evidence changed: protected.py"
                    assert result["status"]=="FAIL_FRESH_TAIL_RC"
                elif mode=="copy_failure":
                    assert type(caught)is AssertionError and str(caught)=="Nonregular numerical output"
                    assert result["status"]=="FAIL_FRESH_TAIL_RC"
                    assert any(x["action"]=="canonical_current_evidence_copy"for x in result["terminal_errors"])
                else:
                    assert caught is publication_error
                    publication_mock.assert_called_once_with(transport/(d.GROUP+"-101-1.summary.json"),transport_fixture["tag"])
                    assert s.read_json(transport/"publication.json")["status"]=="FAIL_PUBLICATION"
                if mode=="body_and_cleanup":
                    assert any(x["error"]==repr(cleanup_error)for x in result["terminal_errors"])
                if mode in ("source_corruption","saved_integrity","native_failure","partial_JSON","body_and_cleanup"):
                    assert (out/"canonical-current-view/.hidden").read_bytes()==b"unchanged original"
                    assert (out/"canonical-current-view/empty").read_bytes()==b""
                if mode!="publication_failure":
                    roundtrip=assert_roundtrip(out,transport,transport_fixture,mode=="complete")
                    if mode=="partial_JSON":
                        stem=d.GROUP+"-101-1"
                        assert transport_fixture["assets"][stem+".precise-capture.json"]==b'{"interrupted":'
                else:roundtrip={"publication_failure_preserved":True}
                cases.append({"case":mode,"status":result["status"],"same_primary_exception_required":mode in
                  ("native_failure","partial_JSON","body_and_cleanup","saved_integrity","publication_failure"),
                  "actual_main_run_execute_finalization_publication":True,"synthetic_numerical_and_remote_transport":True,
                  "complete_output_files":len(result["outputs"]),"evidence":roundtrip})
    assert len(cases)==10
    return {"positive":1,"refusals":9,"cases":cases}

def publication_controls():
    positives=[];refusals=[]
    metadata={
      "source":("source_head","2"*40,"Publication source changed"),
      "run":("run_id",102,"Publication run changed"),
      "bool_run":("run_id",True,"Publication run changed"),
      "attempt":("run_attempt",2,"Publication attempt changed"),
      "bool_attempt":("run_attempt",True,"Publication attempt changed"),
      "original_run":("original_physical_run",1,"Original physical failure identity changed"),
      "original_status":("original_physical_status","PASS","Original physical failure identity changed"),
      "failure_lost":("original_failure_preserved",False,"Original physical failure identity changed"),
      "physical_claim":("physical_accepted",True,"Publication engineering scope changed"),
      "simulator_claim":("simulation_executed",True,"Publication engineering scope changed"),
      "nonboolean_execution":("extraction_executed",1,"Publication execution flag is not boolean"),
      "false_success":("status",d.PASS,"Incomplete fresh RC success"),
      "unknown_status":("status","UNKNOWN","Failed result incorrectly qualifies fresh RC"),
      "changed_inventory":("outputs",{},"Publication complete output map changed")}
    def one(mode,attack=None):
        with tempfile.TemporaryDirectory()as folder,ExitStack()as stack:
            root=Path(folder);out=root/"out";out.mkdir();transport=root/"publication"
            report=d.initial_result({},{});report.update(status="FAIL_SYNTHETIC")
            if mode=="interrupted":report["status"]="RUNNING_SYNTHETIC"
            if mode=="oversized":report["full_untruncated_diagnostic"]="x"*(4*1024**2+1)
            (out/".hidden").write_bytes(b"hidden");(out/"empty").write_bytes(b"")
            s.write(out/"wire-stage/result.json",{"synthetic":True})
            if mode=="malformed":(out/"wire-stage/result.json").write_bytes(b'{"interrupted":')
            if attack in ("malformed_success","missing_success"):
                report.update(status=d.PASS,fresh_RC_pipeline_complete=True,terminal_finalization_complete=True,
                  binding_executed=True,extraction_executed=True)
                if attack=="malformed_success":
                    for member in d.DIRECT.values():s.write(out/member,{"synthetic":True})
                    (out/"wire-stage/result.json").write_bytes(b'{"interrupted":')
            report["outputs"]=a.inventory(out)
            if attack in metadata:
                key,value,_=metadata[attack];prior=json.dumps(report,sort_keys=True);report[key]=value
                assert json.dumps(report,sort_keys=True)!=prior
            s.write(out/"result.json",report)
            if attack=="root_link":out.rename(root/"real");out.symlink_to(root/"real",target_is_directory=True)
            if attack=="report_link":
                (out/"result.json").rename(root/"report");(out/"result.json").symlink_to(root/"report")
            if attack=="descendant_link":(out/"bad").symlink_to(out/"empty")
            for owner,name,value in ((d,"OUT",out),(d,"TRANSPORT",transport)):
                stack.enter_context(patch.object(owner,name,value))
            stack.enter_context(patch.object(d.shutil,"disk_usage",return_value=types.SimpleNamespace(free=64*1024**3)))
            with remote()as fixture:
                if attack:
                    reasons={**{k:v[2]for k,v in metadata.items()},
                      "root_link":"Invalid publication roots","report_link":"Nonregular numerical output",
                      "descendant_link":"Nonregular numerical output",
                      "malformed_success":"Malformed direct JSON cannot qualify fresh RC success: wire-stage/result.json",
                      "missing_success":"Missing successful direct evidence: restore/archive-verification.json"}
                    try:d.publish(report)
                    except AssertionError as error:assert str(error)==reasons[attack],(attack,str(error),reasons[attack])
                    else:raise AssertionError("Accepted publication attack "+attack)
                    assert not fixture["assets"]and not transport.exists()
                    refusals.append(attack)
                else:
                    d.publish(report)
                    proof=assert_roundtrip(out,transport,fixture,False)
                    assert len(fixture["assets"])==4
                    assert (out.parent/"published-roundtrip/empty").read_bytes()==b""
                    if mode=="malformed":
                        assert fixture["assets"][d.GROUP+"-101-1.wire-RC-result.json"]==b'{"interrupted":'
                    positives.append({"case":mode,"proof":proof})
    with patch.dict(os.environ,ENV):
        for mode in ("failed","interrupted","oversized","malformed"):one(mode)
        for attack in (*metadata,"root_link","report_link","descendant_link","malformed_success","missing_success"):
            one("failed",attack)
    assert len(positives)==4 and len(refusals)==19
    return {"positive":positives,"refusals":refusals,"real_pack_complete_extract_and_qualified_publisher":True}

def controls():
    s.methods()
    result={"status":"RUNNING_FRESH_RC_OUTER_CONTROLS"}
    result["pipeline"]=pipeline_controls()
    result["lifecycle"]=lifecycle_controls()
    result["publication"]=publication_controls()
    result["status"]="PASS_ACTUAL_FRESH_RC_OUTER_PIPELINE_LIFECYCLE_CONTROLS"
    result["positive_groups"]=6;result["refusals"]=41
    assert len(result["pipeline"]["refusals"])+result["lifecycle"]["refusals"]+len(result["publication"]["refusals"])==41
    result["native_executed"]=False;s.methods()
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path,required=True);args=p.parse_args()
    result={"status":"RUNNING_FRESH_RC_OUTER_CONTROLS"};s.write(args.out,result)
    try:result=controls()
    except BaseException as error:result.update(status="FAIL_FRESH_RC_OUTER_CONTROLS",error=repr(error));raise
    finally:s.write(args.out,result)

if __name__=="__main__":main()
