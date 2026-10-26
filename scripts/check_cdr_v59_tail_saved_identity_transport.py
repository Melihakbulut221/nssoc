#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Actual archive and publication file seams; only remote transport is synthetic."""
import copy
import hashlib
import io
import json
import os
import sys
import threading
from pathlib import Path
import tarfile
import tempfile
import types
from unittest import mock
import cdr_v59_tail_saved_identity as s
import cloud_cdr_v59_tail_saved_identity as d
from cloud_chunked_results import pack

def archive_controls():
    positives=[];refusals=[]
    helper=s.extraction_helpers()
    def expect(label,callback,kind,message=None):
        try:callback()
        except kind as error:
            if message is not None:assert str(error)==message,(label,str(error))
            refusals.append(label)
        else:raise AssertionError("Accepted "+label)
    with tempfile.TemporaryDirectory() as td:
        root=Path(td);original=root/"original";original.mkdir()
        (original/"empty").write_bytes(b"");(original/".hidden").write_bytes(b"hidden")
        (original/"selected.json").write_text('{"status":"synthetic"}\n')
        expected={p.name:s.sha(p) for p in original.iterdir()}
        transport=root/"parts";transport.mkdir()
        manifest=pack(original,"synthetic-complete-input",transport,64)
        assert len(manifest["parts"])>1
        proof=helper.exact_extract(manifest,transport,root/"restored",expected)
        assert proof["regular_members"]==3 and s.verify_inputs(root/"restored",expected)["files"]==3
        positives.append("actual_multipart_full_hidden_empty_extract")
        extra=copy.deepcopy(expected);extra["missing"]="0"*64
        expect("missing_member",lambda:helper.exact_extract(manifest,transport,root/"missing",extra),
          AssertionError,"Missing native member")
        fewer={k:v for k,v in expected.items() if k!=".hidden"}
        expect("unexpected_unselected_member",lambda:helper.exact_extract(manifest,transport,root/"unexpected",fewer),
          AssertionError,"Unexpected native member")
        bad=dict(expected);bad[".hidden"]="0"*64
        expect("changed_unselected_member",lambda:helper.exact_extract(manifest,transport,root/"changed",bad),
          AssertionError,".hidden")
        part=transport/manifest["parts"][0]["name"];saved=part.read_bytes();part.write_bytes(bytes([saved[0]^1])+saved[1:])
        expect("changed_transport",lambda:helper.exact_extract(manifest,transport,root/"transport-bad",expected),
          AssertionError,"Changed evidence part");part.write_bytes(saved)
        (root/"restored"/"extra").write_bytes(b"x")
        expect("post_restore_extra",lambda:s.verify_inputs(root/"restored",expected),AssertionError,
          "Changed complete restored member inventory")
        (root/"restored"/"extra").unlink()
        (root/"restored"/".hidden").unlink();(root/"restored"/".hidden").symlink_to(original/".hidden")
        expect("post_restore_symlink",lambda:s.verify_inputs(root/"restored",expected),AssertionError,".hidden")
    assert len(positives)==1 and len(refusals)==6
    return {"status":"PASS_ARCHIVE_ADMISSION_FILE_CONTROLS","positives":positives,"refusals":refusals}

def publication_controls():
    positives=[];refusals=[]
    environment={"GITHUB_ACTIONS":"true","GITHUB_REPOSITORY":"Melihakbulut221/nssoc",
      "GITHUB_RUN_ID":"999999991","GITHUB_RUN_ATTEMPT":"1","GITHUB_SHA":"a"*40}
    def one(mode,attack=None):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td);out=base/"out";out.mkdir();transport=base/"publication"
            result={"status":"RUNNING_SYNTHETIC" if mode=="interrupted" else "FAIL_SYNTHETIC",
              "source_head":"a"*40,"run_id":999999991,"run_attempt":1,
              "original_run":s.RUN,"original_status":"FAIL_ADDITIVE_TAIL_WIRE_PHYSICAL",
              "original_failure_preserved":True,"read_only_identity_verified":False,
              "automatic_retry":False,"geometry_generated":False,"extraction_executed":False,
              "simulation_executed":False,"physical_accepted":False,"electrical_accepted":False,
              "qualified_pex":False,"full_phy_accepted":False}
            if mode=="oversized":result["full_untruncated"]="x"*(4*1024**2+1)
            s.write(out/"result.json",result);(out/".hidden").write_bytes(b"h");(out/"empty").write_bytes(b"")
            s.write(out/"original-identity.json",{"partial":True,"synthetic":True})
            if mode=="malformed_failed":(out/"original-identity.json").write_bytes(b'{"interrupted":')
            if attack=="malformed_success":
                for name in d.DIRECT:s.write(out/name,{"synthetic":True})
                (out/"original-identity.json").write_bytes(b'{"interrupted":')
                result.update(status=d.PASS,read_only_identity_verified=True)
            result["outputs"]={p.relative_to(out).as_posix():s.sha(p) for p in out.rglob("*") if p.is_file() and p!=out/"result.json"}
            metadata={
              "source":("source_head","b"*40),"run":("run_id",1),"result_attempt":("run_attempt",2),
              "original_failure":("original_failure_preserved",False),"acceptance":("physical_accepted",True),
              "engine":("simulation_executed",True),"status":("status",d.PASS),"outputs":("outputs",{})}
            if attack in metadata:
                key,value=metadata[attack];result[key]=value
            s.write(out/"result.json",result)
            tag="cloud-results-999999991-1-"+s.GROUP
            remote={"id":123,"tag_name":tag,"target_commitish":"a"*40,"draft":False,"prerelease":True,"assets":[]}
            ref={"ref":"refs/tags/"+tag,"object":{"type":"commit","sha":"a"*40}}
            calls=[]
            def api(path,missing=False):
                if path=="releases/tags/"+tag:return copy.deepcopy(remote)
                if path=="git/ref/tags/"+tag:return copy.deepcopy(ref)
                raise AssertionError("Unexpected remote lookup")
            def upload(argv,**kwargs):
                assert argv[:4]==["gh","release","upload",tag] and argv[-2:]==["-R","Melihakbulut221/nssoc"]
                p=Path(argv[4]);calls.append(p.name)
                remote["assets"].append({"id":len(remote["assets"])+1,"name":p.name,
                  "size":p.stat().st_size,"digest":"sha256:"+s.sha(p),"browser_download_url":"https://example.invalid/"+p.name})
                return types.SimpleNamespace(returncode=0)
            if attack=="root_link":
                out.rename(base/"real");out.symlink_to(base/"real",target_is_directory=True)
            if attack=="report_link":
                report=out/"result.json";report.rename(base/"report");report.symlink_to(base/"report")
            if attack=="descendant_link":(out/"bad").symlink_to(out/"empty")
            if attack=="attempt":environment_override={"GITHUB_RUN_ATTEMPT":"2"}
            else:environment_override={}
            original_release=d.publisher.release
            injected=ValueError("exact synthetic publication transport failure")
            with mock.patch.dict(os.environ,{**environment,**environment_override},clear=False),               mock.patch.object(d,"OUT",out),mock.patch.object(d,"TRANSPORT",transport),               mock.patch.object(d.shutil,"disk_usage",return_value=types.SimpleNamespace(free=32*1024**3)),               mock.patch.object(d.release,"api",api),mock.patch.object(d.publisher.subprocess,"run",upload):
                if attack=="transport":
                    with mock.patch.object(d.publisher,"publish",side_effect=injected) as published:
                        try:d.publish(result)
                        except ValueError as error:assert error is injected
                        else:raise AssertionError("Transport failure accepted")
                        assert published.call_count==1 and published.call_args.args[1]==tag
                        assert published.call_args.args[0]==transport/(s.GROUP+"-999999991-1.summary.json")
                    assert d.publisher.release is original_release
                    assert s.read_json(transport/"publication.json")["status"]=="FAIL_PUBLICATION"
                    refusals.append("exact_transport_error_preserved");return
                if attack:
                    try:d.publish(result)
                    except AssertionError as error:
                        if attack=="malformed_success":
                            assert str(error)=="Malformed direct JSON cannot qualify successful readback: original-identity.json"
                    else:raise AssertionError("Accepted "+attack)
                    assert not calls and not transport.exists()
                    refusals.append(attack);return
                proof=d.publish(result)
                assert proof["status"]=="PASS_FULL_SAVED_READBACK_EVIDENCE_PUBLISHED"
                assert d.publisher.release is original_release
                summary=transport/(s.GROUP+"-999999991-1.summary.json")
                assert summary.read_bytes()==(out/"result.json").read_bytes()
                manifest=s.read_json(transport/(s.GROUP+"-999999991-1.parts.json"))
                expected={str(p.relative_to(out)):s.sha(p) for p in out.rglob("*") if p.is_file()}
                restored=base/"recovered"
                s.extraction_helpers().exact_extract(manifest,transport,restored,expected)
                assert (restored/"result.json").read_bytes()==(out/"result.json").read_bytes()
                assert (restored/".hidden").read_bytes()==b"h" and (restored/"empty").stat().st_size==0
                assert len(calls)==len(proof["assets"])==4
                binding=next(v for v in proof["direct_asset_bindings"] if v["asset_suffix"]=="original-identity.json")
                assert binding["sha256"]==s.sha(out/"original-identity.json") and binding["qualified_as_success"] is False
                assert binding["json_syntax_checked_for_success"] is False
                assert (transport/(s.GROUP+"-999999991-1.original-identity.json")).read_bytes()==(out/"original-identity.json").read_bytes()
                if mode=="malformed_failed":
                    assert (restored/"original-identity.json").read_bytes()==b'{"interrupted":'
                    assert proof["failed_direct_outputs_preserved_as_raw_bytes"] is True
                positives.append(mode)
    for mode in ("failed","interrupted","oversized","malformed_failed"):one(mode)
    for attack in ("root_link","report_link","descendant_link","attempt","transport","source","run","result_attempt",
      "original_failure","acceptance","engine","status","outputs","malformed_success"):one("failed",attack)
    assert len(positives)==4 and len(refusals)==14
    return {"status":"PASS_ACTUAL_RESERVED_PUBLICATION_WRAPPER_CONTROLS","positives":positives,"refusals":refusals,
      "real_pack_and_complete_extract":True,"qualified_publisher_used":True,"remote_transport_only_mocked":True}

def lifecycle_controls():
    """Call the actual main/run/execute/finally/publisher with synthetic runtime transport."""
    records=[]
    environment={"GITHUB_ACTIONS":"true","GITHUB_REPOSITORY":"Melihakbulut221/nssoc",
      "GITHUB_RUN_ID":"999999992","GITHUB_RUN_ATTEMPT":"1","GITHUB_SHA":"a"*40}
    method=s.methods()
    for mode in ("complete","native_failure","partial_json","integrity_failure","cleanup_failure"):
        with tempfile.TemporaryDirectory(prefix="cdr-identity-main-") as td:
            base=Path(td);out=base/"out";transport=base/"publication";app=base/"fixture-app"
            app.write_bytes(b"explicit mocked launcher; never executed\n");app_sha=s.sha(app)
            expected={};input_bytes={}
            for name,member in d.EXPORTS.items():input_bytes[member]=(json.dumps({"synthetic_saved_input":name})+"\n").encode()
            input_bytes[".hidden"]=b"hidden";input_bytes["empty"]=b""
            for member,raw in input_bytes.items():expected[member]=hashlib.sha256(raw).hexdigest()
            changed_member=next(iter(d.EXPORTS.values()))
            state={"events":[],"cleanup_calls":[],"heartbeat_done":False}
            cleanup_error=ValueError("exact synthetic owned cleanup failure")
            class Owned:
                ACTIVE=None
                def __init__(self):
                    self.TRACE=out/"supervision";self.STOP=threading.Event()
                def interrupted(self,*args):raise RuntimeError("synthetic signal interruption")
                def heartbeat(self):
                    self.STOP.wait(30);state["heartbeat_done"]=True
                def stop_process(self,process):
                    state["cleanup_calls"].append(process)
                    if mode=="cleanup_failure":raise cleanup_error
                    return {"remaining_live":[],"synthetic_runtime_transport":True}
                def supervised(self,argv,label,seconds,cwd):
                    assert seconds==1200 and cwd==base and label in d.SECONDS
                    state["events"].append(label);code=0
                    if label=="restore-complete-saved931-capsule":
                        assert list(argv)==[sys.executable,d.__file__,"--restore-worker"]
                        root=out/"restored";root.mkdir()
                        for member,raw in input_bytes.items():
                            p=root/member;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
                        s.write(out/"archive-verification.json",{"synthetic_transport":True,"members":len(expected)})
                    else:
                        assert list(argv)==[app,"python",base/"scripts/cdr_v59_tail_saved_identity_native.py",
                          "--root",out/"restored","--out",out]
                        if mode=="native_failure":
                            s.write(out/"original-identity.json",{"synthetic_partial":True})
                            s.write(out/"raw-hierarchy-diagnostic.json",{"synthetic_runtime_transport":True,
                              "qualified":False,"status":"DIAGNOSTIC_ONLY_BEFORE_UNCHANGED_RAW_HIERARCHY_ASSERTIONS"})
                            code=2
                        else:
                            for name in d.DIRECT:
                                if name!="archive-verification.json":s.write(out/name,{"synthetic_native_transport":True})
                            s.write(out/"identity-comparison.json",{
                              "status":"PASS_READ_ONLY_SAVED_NATIVE_IDENTITIES_NO_TOPOLOGY_GATE_CHANGE",
                              "physical_accepted":False,"electrical_accepted":False,"qualified_pex":False,
                              "topology_comparator_modified":False})
                            s.write(out/"acquired-witness-controls.json",{
                              "status":"PASS_COMPLETE_ACQUIRED_WITNESS_MUTATION_CONTROLS",
                              "positive_copies":12,"refusals":["synthetic"]*12,"saved_native_inputs_mutated":False})
                            if mode=="partial_json":(out/"identity-comparison.json").write_bytes(b'{"interrupted":')
                            if mode=="integrity_failure":(out/"restored"/changed_member).write_bytes(b'{"corrupt":')
                    streams={"stdout":("synthetic "+label+"\n").encode(),"stderr":b""}
                    record={"label":label,"returncode":code,"supervision_failure":None,
                      "process_group_cleanup":{"remaining_live":[]},"synthetic_runtime_transport":True}
                    for name,raw in streams.items():
                        p=self.TRACE/(label+"."+name);p.write_bytes(raw)
                        record[name+"_bytes"]=len(raw);record[name+"_sha256"]=s.sha(p)
                    s.write(self.TRACE/(label+".command.json"),record)
            owned=Owned()
            def supervisor(*args):
                assert args==(base,out,out/"supervision",s.methods,method["protected_sha256"][d.runtime.SAMPLER])
                return owned
            def probe(path,digest,folder):
                assert path==app and digest==app_sha and s.sha(path)==digest
                folder.mkdir();value={"accepted":True,"explicit_mocked_runtime_transport":True}
                s.write(folder/"result.json",value);return value
            def launcher(root,gate,digest):
                assert (root,gate,digest)==(base,s.methods,method["protected_sha256"][d.runtime.PROBE])
                return types.SimpleNamespace(probe=probe)
            tag="cloud-results-999999992-1-"+s.GROUP
            remote={"id":124,"tag_name":tag,"target_commitish":"a"*40,"draft":False,"prerelease":True,"assets":[]}
            ref={"ref":"refs/tags/"+tag,"object":{"type":"commit","sha":"a"*40}}
            uploaded={}
            def api(path,missing=False):
                if path=="releases/tags/"+tag:return copy.deepcopy(remote)
                if path=="git/ref/tags/"+tag:return copy.deepcopy(ref)
                raise AssertionError("Unexpected remote lookup in lifecycle fixture")
            def upload(argv,**kwargs):
                assert argv[:4]==["gh","release","upload",tag] and argv[-2:]==["-R","Melihakbulut221/nssoc"]
                path=Path(argv[4]);uploaded[path.name]=path.read_bytes()
                remote["assets"].append({"id":len(remote["assets"])+1,"name":path.name,"size":path.stat().st_size,
                  "digest":"sha256:"+s.sha(path),"browser_download_url":"https://example.invalid/"+path.name})
                return types.SimpleNamespace(returncode=0)
            real_wait=d.wait
            def reserved(group,env):
                return real_wait(group,env,api,lambda seconds:None,lambda *a,**k:None)
            signals={sig:d.signal.getsignal(sig) for sig in (d.signal.SIGINT,d.signal.SIGTERM)}
            previous_release=d.publisher.release
            with (mock.patch.dict(os.environ,{**environment,"CLOUD_APPIMAGE":str(app)},clear=False),
              mock.patch.object(sys,"argv",["saved-identity-controller"]),
              mock.patch.object(d,"ROOT",base),mock.patch.object(d,"OUT",out),mock.patch.object(d,"TRANSPORT",transport),
              mock.patch.object(d,"APP_SHA",app_sha),mock.patch.object(d,"wait",reserved),
              mock.patch.object(s,"authorize",return_value=method),
              mock.patch.object(s,"expected_files",return_value=expected),
              mock.patch.object(d.runtime,"supervisor",supervisor),mock.patch.object(d.runtime,"launcher",launcher),
              mock.patch.object(d.shutil,"disk_usage",return_value=types.SimpleNamespace(free=32*1024**3)),
              mock.patch.object(d.release,"api",api),mock.patch.object(d.publisher.subprocess,"run",upload)):
                if mode=="complete":d.main()
                else:
                    expected_status={"native_failure":"FAIL_SAVED_IDENTITY_READBACK","partial_json":"FAIL_SAVED_IDENTITY_READBACK",
                      "integrity_failure":"FAIL_SAVED_INPUT_INTEGRITY","cleanup_failure":"FAIL_TERMINAL_CLEANUP"}[mode]
                    try:d.main()
                    except AssertionError as error:assert str(error)==expected_status,(mode,repr(error))
                    else:raise AssertionError("Actual main accepted "+mode)
                result=s.read_json(out/"result.json")
                publication=s.read_json(transport/"publication.json")
                assert publication["status"]=="PASS_FULL_SAVED_READBACK_EVIDENCE_PUBLISHED"
                assert d.publisher.release is previous_release
                assert state["events"]==list(d.SECONDS) and state["cleanup_calls"]==[None]
                assert owned.STOP.is_set() and state["heartbeat_done"] is True
                assert {sig:d.signal.getsignal(sig) for sig in signals}==signals
                assert len(result["commands"])==2
                actual={p.relative_to(out).as_posix():s.sha(p) for p in out.rglob("*") if p.is_file() and p!=out/"result.json"}
                assert result["outputs"]==actual and all(not p.is_symlink() for p in out.rglob("*"))
                stem=s.GROUP+"-999999992-1"
                assert uploaded[stem+".summary.json"]==(out/"result.json").read_bytes()
                manifest=s.read_json(transport/(stem+".parts.json"))
                inventory={**actual,"result.json":s.sha(out/"result.json")}
                restored=base/"published-complete-roundtrip"
                s.extraction_helpers().exact_extract(manifest,transport,restored,inventory)
                assert {p.relative_to(restored).as_posix():s.sha(p) for p in restored.rglob("*") if p.is_file()}==inventory
                assert len(uploaded)==len(publication["assets"]) and len(uploaded)>=3
                for binding in publication["direct_asset_bindings"]:
                    raw=(out/binding["output_member"]).read_bytes()
                    assert uploaded[stem+"."+binding["asset_suffix"]]==raw
                    assert binding["sha256"]==hashlib.sha256(raw).hexdigest()
                    assert binding["qualified_as_success"] is (mode=="complete")
                if mode=="complete":
                    assert result["status"]==d.PASS and result["read_only_identity_verified"] is True
                    assert len(publication["direct_asset_bindings"])==len(d.DIRECT)+len(d.EXPORTS)==12
                else:
                    assert result["status"]==expected_status and result["read_only_identity_verified"] is False
                    assert publication["failed_direct_outputs_preserved_as_raw_bytes"] is True
                if mode=="native_failure":
                    assert result["error"]=="AssertionError()" and result["commands"][1]["returncode"]==2
                    assert uploaded[stem+".raw-hierarchy-diagnostic.json"]==(out/"raw-hierarchy-diagnostic.json").read_bytes()
                    diagnostic_binding=next(v for v in publication["direct_asset_bindings"]
                      if v["asset_suffix"]=="raw-hierarchy-diagnostic.json")
                    assert diagnostic_binding["qualified_as_success"] is False
                    assert "execute" in result["traceback"] and "cloud_cdr_v59_tail_saved_identity.py" in result["traceback"]
                if mode=="partial_json":
                    assert result["error"].startswith("JSONDecodeError(")
                    assert uploaded[stem+".identity-comparison.json"]==b'{"interrupted":'
                if mode=="integrity_failure":
                    assert result["integrity_error"]==repr(AssertionError(changed_member))
                    bound=next(v for v in publication["direct_asset_bindings"] if v["output_member"]=="restored/"+changed_member)
                    assert bound["matches_original_saved_input"] is False and bound["qualified_as_success"] is False
                    assert uploaded[stem+"."+bound["asset_suffix"]]==b'{"corrupt":'
                else:assert result["saved_inputs_unchanged"]=={"files":len(expected),"all_hashes_unchanged":True}
                if mode=="cleanup_failure":assert result["cleanup_error"]==repr(cleanup_error)
                assert all(result[k] is False for k in ("geometry_generated","extraction_executed","simulation_executed",
                  "physical_accepted","electrical_accepted","qualified_pex","full_phy_accepted","automatic_retry"))
                records.append({"case":mode,"actual_main_status":result["status"],"source_inventory_files":len(expected),
                  "complete_terminal_inventory_files":len(inventory),"complete_published_roundtrip":True,
                  "assets":len(uploaded),"all_partial_direct_bytes_exact":True,
                  "owned_cleanup_attempted":True,"heartbeat_stopped":True,"signal_handlers_restored":True,
                  "runtime_transport_explicitly_mocked":True,"actual_main_run_execute_finally_and_publisher":True})
    assert len(records)==5
    return {"status":"PASS_ACTUAL_OUTER_MAIN_LIFECYCLE_CONTROLS","positive_count":1,"refusal_count":4,
      "cases":records,"native_or_CAD_executed":False}

def main():
    assert s.methods()["source_controls_authorized"] is True
    out=s.ROOT/"hw/soc/out/cdr-v59-tail-saved-identity-transport-controls";out.mkdir(parents=True,exist_ok=False)
    r={"status":"RUNNING_TRANSPORT_CONTROLS"};s.write(out/"result.json",r)
    try:
        r["archive"]=archive_controls();s.write(out/"result.json",r)
        r["publication"]=publication_controls();s.write(out/"result.json",r)
        r["lifecycle"]=lifecycle_controls();r["status"]="PASS_TRANSPORT_CONTROLS"
    except BaseException as error:r.update(status="FAIL_TRANSPORT_CONTROLS",error=repr(error));raise
    finally:s.write(out/"result.json",r);print(json.dumps(r,indent=2))
if __name__=="__main__":main()
