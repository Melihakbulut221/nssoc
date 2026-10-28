#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted actual admission/transport/lifecycle controls, with synthetic collaborators."""
import base64, copy, hashlib, io, json, os, tarfile, tempfile
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
import numpy as np
import cdr_v59_tail_headroom_admission as a
import cloud_cdr_v59_tail_headroom_readback as worker
from cloud_chunked_results import pack

def controls():
    m=a.methods()
    a.cloud_guard(m,readback=False)
    positive=[];rejected=[]
    def refuses(label,fn):
        try:fn()
        except (AssertionError,ValueError,KeyError,FileNotFoundError,RuntimeError):
            rejected.append(label)
        else:raise AssertionError("bad fixture accepted: "+label)
    def mutate(obj,path,value):
        out=copy.deepcopy(obj);here=out
        for key in path[:-1]:here=here[key]
        here[path[-1]]=value
        return out
    for case in a.CASES:
        pin,docs=a.reference(case,m)
        assert a.validate_reports(case,pin,docs)["VI_only_passed"]is(case=="cold_late")
    positive.append("all_six_actual_complete_saved_reports_and_cold_late_VI_pass")
    base_docs=a.reference("cold_late",m)[1]
    pin=m["cases"]["cold_late"]
    for path,value in [
        (("native","source_head"),"0"*40),(("native","case"),"hot_late"),
        (("native","status"),"PASS"),(("native","data_passed"),True),
        (("native","devices_passed"),True),(("native","vi","passed"),False),
        (("native","actual_fault_detected"),True),(("native","accepted"),True),
        (("native","terminal_errors"),["fault"]),(("native","terminal_finalization_complete"),False),
        (("native","current_saved_input_integrity","files"),5549),
        (("native","raw_capture","columns"),1151),(("native","raw_capture","raw_sha256"),"0"*64),
        (("native","data_offset_s"),0),(("summary","run_id"),1),
        (("summary","command","returncode"),0),(("summary","outer_terminal_errors"),["fault"]),
        (("summary","native_controller_result_sha256"),"0"*64),
        (("preparation_native","status"),"PASS_OTHER"),
        (("manifest","source_directory"),"wrong")
    ]:
        bad=mutate(base_docs,path,value)
        refuses("report:"+"/".join(path),lambda bad=bad:a.validate_reports("cold_late",pin,bad))
    for key in a.ALWAYS_FALSE:
        refuses("scope:"+key,lambda key=key:a.validate_method(mutate(m,(key,),True)))
    refuses("reordered_cases",lambda:a.validate_method(mutate(m,("case_order",),list(reversed(a.CASES)))))
    refuses("relaxed_CDR_gate",lambda:a.validate_method(mutate(m,("numerical_gates","sampler_ps"),62.5)))
    refuses("wrong_producer",lambda:a.validate_method(mutate(m,("original_run",),40219397958)))
    env=dict(GITHUB_ACTIONS="true",RUNNER_OS="Linux",GITHUB_REPOSITORY="Melihakbulut221/nssoc",
             GITHUB_RUN_ID="123",GITHUB_RUN_ATTEMPT="1",GITHUB_SHA="a"*40,
             GITHUB_REF="refs/heads/codex/fixture")
    a.cloud_guard(m,env,readback=False)
    for key in env:
        wrong=dict(env);wrong[key]="wrong"
        refuses("environment:"+key,lambda wrong=wrong:a.cloud_guard(m,wrong,readback=False))
    disabled=copy.deepcopy(m);disabled["readback_authorized"]=False
    refuses("disabled_capture_readback",lambda:a.cloud_guard(disabled,env))
    positive.append("exact_cloud_context_and_scope")

    # Real unchanged extract body, real tar pack/part verifier, explicit tiny input.
    with tempfile.TemporaryDirectory(prefix="cdr-tail-headroom-controls-")as tmp:
        root=Path(tmp);original=root/"synthetic";original.mkdir()
        (original/"native").mkdir();(original/"native/wave.raw").write_bytes(b"explicit synthetic bytes")
        summary=b'{"synthetic":true}\n';(original/"result.json").write_bytes(summary)
        (original/"unselected.txt").write_bytes(b"must also authenticate")
        outer=dict(outputs={str(p.relative_to(original)):a.sha(p)for p in original.rglob("*")
                            if p.is_file()and p.name!="result.json"})
        transport=root/"parts";transport.mkdir()
        manifest=pack(original,"fixture",transport,128)
        extract,derivation=a.adapted_function("extract",{"SELECT":("native/wave.raw",)})
        proof=extract(manifest,transport,root/"restored",outer,hashlib.sha256(summary).hexdigest())
        assert proof["all_member_hashes_verified"]==3 and derivation["function_AST_unchanged"]
        assert (root/"restored/native/wave.raw").read_bytes()==b"explicit synthetic bytes"
        bad=copy.deepcopy(outer);bad["outputs"]["unselected.txt"]="0"*64
        refuses("unselected_archive_member_changed",
                lambda:extract(manifest,transport,root/"bad-unselected",bad,hashlib.sha256(summary).hexdigest()))
        bad=copy.deepcopy(outer);bad["outputs"].pop("unselected.txt")
        refuses("unlisted_archive_member",
                lambda:extract(manifest,transport,root/"bad-extra",bad,hashlib.sha256(summary).hexdigest()))
        first=transport/manifest["parts"][0]["name"]
        first.write_bytes(first.read_bytes()+b"x")
        refuses("archive_part_extra_bytes",
                lambda:extract(manifest,transport,root/"bad-part",outer,hashlib.sha256(summary).hexdigest()))
    positive.append("actual_immutable_extract_complete_inventory_and_parts")

    # Preserve the genuine case-specific VI result through the actual replay adapter.
    original_block=a.rows.measurement_source((a.ROOT/"scripts/cloud_cdr500_v58_loaded.py").read_text())
    assert a.rows.BLOCK_SHA in ("7a9787a019bf460d31d40e23f94e76f51c9540cb0aafef465a1b82e8767ace64",)
    assert "minimum_active_vce_v" in original_block
    for case,vi in (("cold_late",True),("nominal_early",False)):
        report=dict(case=case,binding={},source_bits=[],data_offset_s=0,devices={},mos_devices={},
                    native_caps={},devices_passed=False,data_passed=False,vi=dict(passed=vi))
        measured={k:report[k]for k in ("devices_passed","data_passed","vi")}
        stub="def replay(*args):\n    return "+repr(measured)+"\n"
        with patch.object(a.rows,"measurement_source",return_value=stub):
            assert a.replay_all("synthetic-source",None,None,None,report)==measured
            bad=copy.deepcopy(report);bad["vi"]["passed"]=not vi
            refuses("replay_changed_VI:"+case,lambda bad=bad:a.replay_all("synthetic-source",None,None,None,bad))
    positive.append("actual_replay_adapter_with_explicit_synthetic_measurements")

    with tempfile.TemporaryDirectory(prefix="cdr-tail-headroom-lifecycle-")as tmp:
        root=Path(tmp)
        result=worker.initial("nominal_early")
        result["status"]="FAIL_CURRENT_PVT_SAVED_ROW_READBACK"
        primary=RuntimeError("actual-body-primary")
        (root/"partial.bin").write_bytes(b"retained failed output")
        with patch.object(a,"methods",return_value=m):
            worker.finish(root,result,primary)
        saved=a.read_json(root/"result.json")
        assert saved["active_primary_error"]==repr(primary) and saved["outputs"]["partial.bin"]["sha256"]==a.sha(root/"partial.bin")
        assert worker.publication_result(root,"nominal_early")==saved
        (root/"partial.bin").write_bytes(b"changed")
        refuses("actual_changed_partial_publication",lambda:worker.publication_result(root,"nominal_early"))
        primary_result=worker.initial("nominal_early")
        primary_result["status"]="FAIL_CURRENT_PVT_SAVED_ROW_READBACK"
        with patch.object(a,"methods",side_effect=RuntimeError("protected-source-secondary")):
            worker.finish(root,primary_result,primary)
        saved=a.read_json(root/"result.json")
        assert saved["active_primary_error"]==repr(primary) and not saved["terminal_complete"]
        assert saved["terminal_errors"][0]["action"]=="protected_sources"
        with patch.object(a,"methods",side_effect=RuntimeError("standalone-source-failure")):
            refuses("terminal_only_failure_is_fatal",lambda:worker.finish(root,worker.initial("nominal_early"),None))
        # Atomic replacement failure preserves the old record and a distinct fragment.
        actual_capture=io.StringIO()
        with redirect_stdout(actual_capture), patch.object(a,"methods",return_value=m), patch.object(worker.os,"replace",side_effect=OSError("actual-terminal-replace-failure")):
            worker.finish(root,worker.initial("nominal_early"),primary)
        envelope=json.loads(actual_capture.getvalue().split("CDR_TAIL_HEADROOM_TERMINAL_FALLBACK ",1)[1])
        fallback=json.loads(base64.b64decode(envelope["base64"],validate=True))
        assert fallback["active_primary_error"]==repr(primary)
        assert fallback["outputs"]==worker.inventory(root)
        assert any(name.startswith("result.json.tmp-")for name in fallback["outputs"])
        with patch.object(a,"methods",return_value=m), patch.object(worker,"write",side_effect=OSError("save")), patch.object(worker,"encode",side_effect=ValueError("fallback-encode")):
            worker.finish(root,worker.initial("nominal_early"),primary)
            refuses("fallback_encode_only_failure_is_fatal",lambda:worker.finish(root,worker.initial("nominal_early"),None))
        old=(root/"result.json").read_bytes()
        with patch.object(worker.os,"replace",side_effect=OSError("actual-replace-failure")):
            try:worker.write(root/"result.json",{"new":"not committed"})
            except OSError:pass
            else:raise AssertionError("replace failure missing")
        assert (root/"result.json").read_bytes()==old and list(root.glob("result.json.tmp-*"))
        capture=io.StringIO()
        with redirect_stdout(capture), patch.object(a,"methods",return_value=m), patch.object(worker,"write",side_effect=OSError("terminal-save-failure")):
            worker.finish(root,worker.initial("nominal_early"),primary)
            refuses("save_only_failure_is_fatal",lambda:worker.finish(root,worker.initial("nominal_early"),None))
        lines=capture.getvalue().splitlines()
        assert len(lines)==2
        for line in lines:
            envelope=json.loads(line.split("CDR_TAIL_HEADROOM_TERMINAL_FALLBACK ",1)[1])
            payload=base64.b64decode(envelope["base64"],validate=True)
            assert len(payload)==envelope["bytes"] and hashlib.sha256(payload).hexdigest()==envelope["sha256"]
            assert json.loads(payload)["status"]=="FAIL_READBACK_TERMINAL_SAVE"
    positive.append("actual_terminal_inventory_atomic_fragments_and_primary_preservation")

    # Publication must join actual complete frame bytes, not just a PASS label.
    with tempfile.TemporaryDirectory(prefix="cdr-tail-headroom-success-joins-")as tmp:
        root=Path(tmp)
        worker.write(root/"initial.json",worker.initial("nominal_early"))
        diagnosis=dict(selected_vectors=["v(explicit-synthetic)"],frame_rows=[0],
            original_capture=dict(raw_sha256="a"*64),electrical_accepted=False,
            cdr_accepted=False,full_phy_accepted=False)
        binary=np.asarray([[0.,0.,1.]],dtype="<f8").tobytes()
        (root/"native-frames.bin").write_bytes(binary)
        worker.write(root/"diagnosis.json",diagnosis)
        frames=dict(columns=["native_row","time","v(explicit-synthetic)"],frame_rows=[0],
            rows=1,bytes=len(binary),sha256=hashlib.sha256(binary).hexdigest(),dtype="<f8",complete=True,
            diagnosis_sha256=worker.core.digest(worker.core.canonical(diagnosis)),
            electrical_accepted=False,cdr_accepted=False,full_phy_accepted=False)
        worker.write(root/"frames.json",frames)
        worker.write(root/"restore-proof.json",dict(selected={"native/native/wave.raw":dict(sha256="a"*64)},
            all_original_outputs_verified=True,all_member_hashes_verified=3934))
        worker.write(root/"original-measurements-replayed.json",dict(readback_only=True,
            all_numerical_gates_unchanged=True,original_status="REJECTED_WHOLE_MIM_PD500_LOADED"))
        r=worker.initial("nominal_early")
        r.update(status="PASS_CURRENT_PVT_SAVED_ROW_READBACK_NOT_ACCEPTANCE",
            original_status="REJECTED_WHOLE_MIM_PD500_LOADED",terminal_complete=True,terminal_errors=[],
            all_original_measurements_reproduced=True,original_data_passed=False,
            original_devices_passed=False,original_VI_only_passed=False,
            original_wave_sha256="a"*64,diagnosis_sha256=a.sha(root/"diagnosis.json"),frames=frames)
        def refresh():
            r["outputs"]=worker.inventory(root);worker.write(root/"result.json",r)
        refresh();assert worker.publication_result(root,"nominal_early")==r
        (root/"native-frames.bin").unlink();refresh()
        refuses("success_missing_frames_even_with_refreshed_inventory",lambda:worker.publication_result(root,"nominal_early"))
        (root/"native-frames.bin").write_bytes(binary+b"x");refresh()
        refuses("success_changed_binary_even_with_refreshed_inventory",lambda:worker.publication_result(root,"nominal_early"))
        (root/"native-frames.bin").write_bytes(binary)
        incomplete=copy.deepcopy(frames);incomplete["complete"]=False
        worker.write(root/"frames.json",incomplete);r["frames"]=incomplete;refresh()
        refuses("success_incomplete_matching_frame_proof",lambda:worker.publication_result(root,"nominal_early"))
        worker.write(root/"frames.json",frames);r["frames"]=frames
        changed=copy.deepcopy(diagnosis);changed["unmeasured_annotation"]="synthetic alteration"
        worker.write(root/"diagnosis.json",changed);r["diagnosis_sha256"]=a.sha(root/"diagnosis.json");refresh()
        refuses("raw_diagnosis_hash_cannot_replace_canonical_join",lambda:worker.publication_result(root,"nominal_early"))
        worker.write(root/"diagnosis.json",diagnosis);r["diagnosis_sha256"]=a.sha(root/"diagnosis.json")
        bad=copy.deepcopy(frames);bad["frame_rows"]=[1]
        worker.write(root/"frames.json",bad);r["frames"]=bad;refresh()
        refuses("success_wrong_native_row_join",lambda:worker.publication_result(root,"nominal_early"))
        worker.write(root/"frames.json",frames);r["frames"]=frames
        (root/"original-measurements-replayed.json").unlink();refresh()
        refuses("success_missing_full_original_replay",lambda:worker.publication_result(root,"nominal_early"))
    positive.append("actual_success_publication_requires_complete_original_and_binary_proof_joins")

    return dict(status="PASS_CURRENT_TAIL_HEADROOM_SOURCE_CONTROLS_NOT_CAPTURE_ANALYSIS",
        positive=positive,refused=rejected,positive_count=len(positive),refusal_count=len(rejected),
        actual_six_original_reports_authenticated=True,
        synthetic_transport_and_measurements_explicit=True,local_execution=False,
        actual_capture_read=False,simulator_executed=False,accepted=False)
if __name__=="__main__":
    print(json.dumps(controls(),indent=2,sort_keys=True),flush=True)
