#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Actual cloud publisher and archive paths with explicitly synthetic remote assets."""
import copy, json, os, subprocess, tempfile, types
from pathlib import Path
from unittest.mock import patch
import cdr_v59_tail_headroom_admission as a
import cloud_cdr_v59_tail_headroom_readback as worker

def controls():
    method=a.methods();a.cloud_guard(method,readback=False)
    allowed=copy.deepcopy(method);allowed["readback_authorized"]=True
    modes=("new","existing_identical","missing_terminal","conflict","wrong_source",
           "replaced_release","bad_post_digest","extra_asset")
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
            original_run=subprocess.run
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
                uploads.append(path.name)
                remote["assets"].append(entry(path,"0"*64 if mode=="bad_post_digest"else None))
                if mode=="extra_asset"and not any(x["name"]=="unexpected.txt"for x in remote["assets"]):
                    remote["assets"].append(dict(id=19999,name="unexpected.txt",size=1,digest="sha256:"+"1"*64))
                return types.SimpleNamespace(returncode=0)
            error=None;proof=None
            with patch.object(a,"ROOT",base),patch.object(worker.waiter,"wait",return_value={"synthetic":True}),\
                 patch.object(worker.release,"api",side_effect=fake_api),\
                 patch.object(worker.publisher.subprocess,"run",side_effect=fake_run),\
                 patch.object(worker.publisher.time,"sleep",side_effect=AssertionError("unexpected retry sleep")):
                try:proof=worker.publish(root,case,allowed)
                except (AssertionError,RuntimeError)as caught:error=caught
            expected_success=mode in ("new","existing_identical","missing_terminal")
            assert (error is None)==expected_success,(mode,repr(error))
            assert worker.publisher.release.__module__=="migrate_outputs_to_cloud","publisher hook not restored"
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
            rows.append(dict(case=mode,expected_publication_success=expected_success,
                actual_error=repr(error)if error else None,uploads=uploads,
                remote_asset_names=[x["name"]for x in remote["assets"]],
                partial_evidence_retained=(root/"partial-native-frames.bin").read_bytes()==b"explicitly synthetic partial diagnostic",
                actual_pack_and_publisher_executed=True,real_network_or_native_capture=False))
    return dict(status="PASS_ACTUAL_TAIL_HEADROOM_PUBLICATION_SOURCE_CONTROLS",
        cases=rows,positive_count=3,refusal_count=5,synthetic_remote_explicit=True,
        actual_capture_read=False,simulator_executed=False,accepted=False)
if __name__=="__main__":
    print(json.dumps(controls(),indent=2,sort_keys=True),flush=True)
