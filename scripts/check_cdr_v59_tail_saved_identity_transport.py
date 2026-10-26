#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Actual archive and publication file seams; only remote transport is synthetic."""
import copy
import io
import json
import os
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
                    except AssertionError:pass
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
                positives.append(mode)
    for mode in ("failed","interrupted","oversized"):one(mode)
    for attack in ("root_link","report_link","descendant_link","attempt","transport","source","run","result_attempt",
      "original_failure","acceptance","engine","status","outputs"):one("failed",attack)
    assert len(positives)==3 and len(refusals)==13
    return {"status":"PASS_ACTUAL_RESERVED_PUBLICATION_WRAPPER_CONTROLS","positives":positives,"refusals":refusals,
      "real_pack_and_complete_extract":True,"qualified_publisher_used":True,"remote_transport_only_mocked":True}

def main():
    assert s.methods()["source_controls_authorized"] is True
    out=s.ROOT/"hw/soc/out/cdr-v59-tail-saved-identity-transport-controls";out.mkdir(parents=True,exist_ok=False)
    r={"status":"RUNNING_TRANSPORT_CONTROLS"};s.write(out/"result.json",r)
    try:
        r["archive"]=archive_controls();s.write(out/"result.json",r)
        r["publication"]=publication_controls();r["status"]="PASS_TRANSPORT_CONTROLS"
    except BaseException as error:r.update(status="FAIL_TRANSPORT_CONTROLS",error=repr(error));raise
    finally:s.write(out/"result.json",r);print(json.dumps(r,indent=2))
if __name__=="__main__":main()
