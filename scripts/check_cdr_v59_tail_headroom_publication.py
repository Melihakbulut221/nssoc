#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Actual cloud publisher and archive paths with explicitly synthetic remote assets."""
import copy, io, json, os, subprocess, tempfile, types
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
import cdr_v59_tail_headroom_admission as a
import cloud_cdr_v59_tail_headroom_readback as worker

def controls():
    method=a.methods();a.cloud_guard(method,readback=False)
    allowed=copy.deepcopy(method);allowed["readback_authorized"]=True
    modes=("new","existing_identical","missing_terminal","conflict","wrong_source",
           "replaced_release","bad_post_digest","extra_asset",
           "upload_primary_save","upload_primary_save_encode","upload_primary_save_emit",
           "save_only","save_only_encode","save_only_emit")
    rows=[]
    for mode in modes:
        with tempfile.TemporaryDirectory(prefix="cdr-tail-headroom-publication-")as temp:
            base=Path(temp);case="nominal_early";root=base/("cloud-"+worker.group(case));root.mkdir()
            (root/"partial-native-frames.bin").write_bytes(b"explicitly synthetic partial diagnostic")
            if mode!="missing_terminal":
                r=worker.initial(case)
                r.update(status="FAIL_CURRENT_PVT_SAVED_ROW_READBACK",terminal_complete=True,
                         outputs=worker.inventory(root),error="explicit synthetic failure")
                worker.write(root/"result.json",r)
            tag,head=worker.release.context(worker.group(case),os.environ)
            remote=dict(id=9001,tag_name=tag,target_commitish=head,draft=False,prerelease=True,assets=[])
            ref=dict(ref="refs/tags/"+tag,object=dict(type="commit",sha=head))
            calls=[];uploads=[];seeded=False
            original_replace=worker.os.replace
            original_release=worker.publisher.release
            real_dumps=json.dumps
            primary_mode=mode.startswith("upload_primary_save")
            terminal_mode=primary_mode or mode.startswith("save_only")
            upload_failure=RuntimeError("actual-upload-primary:"+mode)
            save_failure=OSError("actual-publication-replace:"+mode)
            encode_failure=ValueError("actual-publication-fallback-encode:"+mode)
            emit_failure=OSError("actual-publication-fallback-emit:"+mode)
            save_fragments=[];fallback_calls=[];stdout=io.StringIO()
            def failing_replace(src,dst):
                if terminal_mode and Path(dst).name=="publication.json":
                    assert Path(src).is_file()
                    save_fragments.append(dict(path=Path(src),sha256=a.sha(src),bytes=Path(src).stat().st_size))
                    raise save_failure
                return original_replace(src,dst)
            def checked_dumps(value,*args,**kwargs):
                if terminal_mode and isinstance(value,dict) and {"primary_error","save_error","proof"}<=set(value):
                    fallback_calls.append("encode")
                    if mode.endswith("_encode"):raise encode_failure
                return real_dumps(value,*args,**kwargs)
            def checked_print(value,*args,**kwargs):
                assert value.startswith("CDR_TAIL_HEADROOM_PUBLICATION_FALLBACK ")
                fallback_calls.append("emit")
                if mode.endswith("_emit"):raise emit_failure
                print(value,*args,**kwargs)
            def entry(path,digest=None):
                return dict(id=10000+len(remote["assets"]),name=path.name,size=path.stat().st_size,
                    digest="sha256:"+(digest or a.sha(path)),
                    browser_download_url="https://example.invalid/explicit-control/"+path.name)
            def fake_api(path,missing=False):
                nonlocal seeded
                calls.append(path)
                if path=="git/ref/tags/"+tag:return copy.deepcopy(ref)
                assert path=="releases/tags/"+tag
                if not seeded:
                    seeded=True
                    summary=next((base/"hw/soc/out"/(worker.group(case)+"-publication")).glob("*.summary.json"))
                    if mode in ("existing_identical","conflict"):
                        remote["assets"].append(entry(summary,"0"*64 if mode=="conflict"else None))
                answer=copy.deepcopy(remote)
                if mode=="wrong_source":answer["target_commitish"]="0"*40
                if mode=="replaced_release"and len(calls)>2:answer["id"]=9002
                return answer
            def fake_run(cmd,*args,**kwargs):
                assert cmd[:3]==["gh","release","upload"]and cmd[3]==tag and cmd[5:]==["-R","Melihakbulut221/nssoc"]
                path=Path(cmd[4]);assert path.is_file()
                assert not any(x["name"]==path.name for x in remote["assets"]),"no clobber"
                if primary_mode:raise upload_failure
                uploads.append(path.name)
                remote["assets"].append(entry(path,"0"*64 if mode=="bad_post_digest"else None))
                if mode=="extra_asset"and not any(x["name"]=="unexpected.txt"for x in remote["assets"]):
                    remote["assets"].append(dict(id=19999,name="unexpected.txt",size=1,digest="sha256:"+"1"*64))
                return types.SimpleNamespace(returncode=0)
            original_result_bytes=(root/"result.json").read_bytes() if (root/"result.json").exists() else None
            error=None;proof=None
            with patch.object(a,"ROOT",base),patch.object(worker.waiter,"wait",return_value={"synthetic":True}),\
                 patch.object(worker.release,"api",side_effect=fake_api),\
                 patch.object(worker.publisher.subprocess,"run",side_effect=fake_run),\
                 patch.object(worker.publisher.time,"sleep",side_effect=AssertionError("unexpected retry sleep")),\
                 patch.object(worker.os,"replace",side_effect=failing_replace),\
                 patch.object(worker,"json",types.SimpleNamespace(dumps=checked_dumps)),\
                 patch.object(worker,"print",side_effect=checked_print,create=True),redirect_stdout(stdout):
                try:proof=worker.publish(root,case,allowed)
                except BaseException as caught:error=caught
            expected_success=mode in ("new","existing_identical","missing_terminal")
            assert (error is None)==expected_success,(mode,repr(error))
            assert worker.publisher.release is original_release,"publisher hook not restored"
            record=worker.publication_result(root,case)
            assert not record["accepted"]and record["original_electrical_rejection"]
            if mode=="missing_terminal":
                assert record["status"]=="FAIL_BEFORE_READBACK_TERMINAL"and not record["terminal_complete"]
            if expected_success:
                assert proof["status"]=="PASS_COMPLETE_RESERVED_READBACK_PUBLICATION_NOT_ACCEPTANCE"
                assert proof["complete_asset_census_verified"]and not proof["accepted"]
                assert len(remote["assets"])==3
            if mode in ("conflict","wrong_source","replaced_release"):
                assert not uploads
            if mode=="bad_post_digest":assert len(uploads)==1
            terminal_evidence=None
            if terminal_mode:
                assert (root/"result.json").read_bytes()==original_result_bytes
                assert (root/"partial-native-frames.bin").read_bytes()==b"explicitly synthetic partial diagnostic"
                assert error is (upload_failure if primary_mode else save_failure)
                frames=[];trace=error.__traceback__
                while trace is not None:
                    frames.append((trace.tb_frame.f_code.co_name,trace.tb_frame.f_code.co_filename));trace=trace.tb_next
                assert any(name=="publish" and path==worker.__file__ for name,path in frames)
                if not primary_mode:
                    assert any(name=="write" and path==worker.__file__ for name,path in frames)
                assert len(save_fragments)==1
                fragment=save_fragments[0];path=fragment["path"]
                assert path.is_file() and a.sha(path)==fragment["sha256"] and path.stat().st_size==fragment["bytes"]
                assert not (path.parent/"publication.json").exists()
                assert fallback_calls==(["encode"] if mode.endswith("_encode") else ["encode","emit"])
                if mode.endswith(("_encode","_emit")):
                    assert stdout.getvalue()==""
                else:
                    envelope=json.loads(stdout.getvalue().split("CDR_TAIL_HEADROOM_PUBLICATION_FALLBACK ",1)[1])
                    assert envelope["primary_error"]==(repr(upload_failure)if primary_mode else None)
                    assert envelope["save_error"]==repr(save_failure)
                    assert envelope["proof"]["status"]=="FAIL_READBACK_PUBLICATION_TERMINAL_SAVE"
                    assert envelope["proof"]["status_before_terminal"]==(
                        "FAIL_READBACK_PUBLICATION"if primary_mode else "PASS_COMPLETE_RESERVED_READBACK_PUBLICATION_NOT_ACCEPTANCE")
                assert len(uploads)==(0 if primary_mode else 3)
                terminal_evidence=dict(original_exception_identity_preserved=True,
                    publisher_hook_identity_restored=True,actual_worker_publish_frame=True,
                    actual_atomic_replace_fragment= {k:v for k,v in fragment.items() if k!="path"},
                    fallback_calls=fallback_calls,full_fallback_stdout=stdout.getvalue(),
                    source_result_and_partial_output_unchanged=True)
            rows.append(dict(case=mode,expected_publication_success=expected_success,
                actual_error=repr(error)if error else None,uploads=uploads,
                remote_asset_names=[x["name"]for x in remote["assets"]],
                partial_evidence_retained=(root/"partial-native-frames.bin").read_bytes()==b"explicitly synthetic partial diagnostic",
                actual_pack_and_publisher_executed=True,real_network_or_native_capture=False,
                terminal_evidence=terminal_evidence))
    return dict(status="PASS_ACTUAL_TAIL_HEADROOM_PUBLICATION_SOURCE_CONTROLS",
        cases=rows,positive_count=3,refusal_count=11,terminal_cases=6,synthetic_remote_explicit=True,
        actual_capture_read=False,simulator_executed=False,accepted=False)
if __name__=="__main__":
    print(json.dumps(controls(),indent=2,sort_keys=True),flush=True)
