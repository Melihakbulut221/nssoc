#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted synthetic tests of complete replay publication and failure retention."""
import argparse,copy,gzip,hashlib,io,json,os,subprocess,tarfile,tempfile,traceback
from pathlib import Path
from unittest import mock
import publish_cdr_current_eight_drain_wave_replay as p
import cloud_chunked_results as packer
def controls(ctx):
    positive=[];refusals=[];lifecycle=[]
    def refuse(name,fn,needle):
        try:fn()
        except AssertionError as error:
            assert needle in str(error),(name,str(error))
            refusals.append(dict(name=name,error=str(error)))
        else:raise AssertionError("accepted invalid fixture: "+name)
    env=dict(GITHUB_ACTIONS="true",GITHUB_EVENT_NAME="workflow_dispatch",GITHUB_REPOSITORY=p.REPO,GITHUB_REF="refs/heads/"+p.BRANCH,GITHUB_RUN_ATTEMPT="1",GITHUB_SHA="1"*40,GITHUB_RUN_ID="123")
    fake=p.context(env,"nominal_early")
    positive.append("hosted_exact_context")
    for key,value,needle in [("GITHUB_ACTIONS","false","hosted manual"),("GITHUB_EVENT_NAME","push","hosted manual"),("GITHUB_REPOSITORY","else/else","repository/branch"),("GITHUB_REF","refs/heads/main","repository/branch"),("GITHUB_RUN_ATTEMPT","2","attempt one"),("GITHUB_SHA","bad","source/run"),("GITHUB_RUN_ID","0","source/run")]:
        e=dict(env);e[key]=value;refuse("context_"+key,lambda e=e:p.context(e,"nominal_early"),needle)
    refuse("wrong_case",lambda:p.context(env,"constant_one"),"case")
    proof=dict(tag=fake["tag"],tested_source=fake["source"],release_id=10,target_verified=True,externally_reserved=True,creation_attempted=False,assets_overwritten=False,existing_assets=[])
    release=dict(id=10,tag_name=fake["tag"],target_commitish=fake["source"],draft=False,prerelease=True,assets=[])
    ref=dict(ref="refs/tags/"+fake["tag"],object=dict(type="commit",sha=fake["source"]))
    assert p.validate_release(fake,proof,release,ref)=={}
    positive.append("independent_empty_release")
    for name,key,value,needle in [("id","id",11,"release ID"),("source","target_commitish","2"*40,"release source"),("tag","tag_name","other","release source"),("draft","draft",True,"public prerelease"),("prerelease","prerelease",False,"public prerelease")]:
        x=copy.deepcopy(release);x[key]=value;refuse("release_"+name,lambda x=x:p.validate_release(fake,proof,x,ref),needle)
    for name,key,value in [("authority","externally_reserved",False),("creation","creation_attempted",True),("overwrites","assets_overwritten",True),("old_assets","existing_assets",["old"])]:
        x=copy.deepcopy(proof);x[key]=value;refuse("proof_"+name,lambda x=x:p.validate_release(fake,x,release,ref),"independent reservation")
    for name,key,value in [("type","type","tag"),("source","sha","2"*40)]:
        x=copy.deepcopy(ref);x["object"][key]=value;refuse("ref_"+name,lambda x=x:p.validate_release(fake,proof,release,x),"immutable tag")
    with tempfile.TemporaryDirectory(prefix="synthetic-replay-publication-")as temp:
        work=Path(temp);root=work/"synthetic-derived";root.mkdir()
        (root/"empty.stdout").write_bytes(b"")
        (root/"failed-native-result.json").write_text('{"status":"ORIGINAL_REJECTION_UNCHANGED","passed":false}\n')
        (root/"nested").mkdir();(root/"nested"/"source.txt").write_bytes(b"complete provenance\n")
        rawrows=b'{"row":0,"v":0.346}\n{"row":1,"v":0.347}\n'
        (root/"full-selected-contact-rows.jsonl.gz").write_bytes(gzip.compress(rawrows,mtime=0))
        baseline=p.inventory(root);assert len(baseline)==4 and baseline["empty.stdout"]["bytes"]==0
        positive.append("full_inventory_includes_empty_and_gzip")
        out=work/"transport";paths,details=p.prepare(fake,root,out,packer.pack)
        assert p.inventory(root)==baseline and details["files"]==baseline
        index=json.loads(paths[0].read_bytes());assert index["files"]==baseline
        parts=json.loads(paths[1].read_bytes())
        blob=b"".join((out/x["name"]).read_bytes()for x in parts["parts"])
        assert len(blob)==parts["bytes"] and hashlib.sha256(blob).hexdigest()==parts["sha256"]
        with tarfile.open(fileobj=io.BytesIO(blob),mode="r:gz")as tf:
            members={x.name:x for x in tf if x.isfile()}
            assert set(members)=={root.name+"/"+name for name in baseline}
            for name,pin in baseline.items():
                raw=tf.extractfile(members[root.name+"/"+name]).read()
                assert dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())==pin
            assert gzip.decompress(tf.extractfile(members[root.name+"/full-selected-contact-rows.jsonl.gz"]).read())==rawrows
        positive.append("actual_qualified_tar_roundtrip_every_file")
        refuse("existing_transport",lambda:p.prepare(fake,root,out,packer.pack),"publication directory new")
        refuse("recursive_transport",lambda:p.prepare(fake,root,root/"inside",packer.pack),"publication outside")
        empty=work/"empty";empty.mkdir();refuse("empty_tree",lambda:p.inventory(empty),"empty output tree")
        (root/"alias").symlink_to(root/"empty.stdout");refuse("symlink",lambda:p.inventory(root),"output symlink");(root/"alias").unlink()
        os.mkfifo(root/"fifo");refuse("fifo",lambda:p.inventory(root),"special output");(root/"fifo").unlink()
        def changed_pack(directory,*args):
            m=packer.pack(directory,*args);(directory/"empty.stdout").write_bytes(b"changed");return m
        refuse("mutation_during_pack",lambda:p.prepare(fake,root,work/"changed-transport",changed_pack),"output changed")
        (root/"empty.stdout").write_bytes(b"")
        def bad_pack(directory,*args):
            m=packer.pack(directory,*args);m["verification"]["all_parts_and_combined_bytes_verified"]=False;return m
        refuse("invalid_archive_proof",lambda:p.prepare(fake,root,work/"bad-transport",bad_pack),"archive verification")
        def trial(name,mode=None):
            saved=copy.deepcopy(release);calls=[];target=work/name;target.mkdir()
            if mode=="occupied":
                saved["assets"]=[dict(id=90,name="old",state="uploaded",size=1,digest="sha256:"+"0"*64)]
            def api(path):
                if path=="releases/tags/"+fake["tag"]:return copy.deepcopy(saved)
                if path=="git/ref/tags/"+fake["tag"]:return copy.deepcopy(ref)
                raise AssertionError("unexpected API: "+path)
            def upload(context,path):
                assert context==fake
                calls.append(path.name)
                row=dict(id=100+len(calls),name=path.name,state="uploaded",size=path.stat().st_size,digest="sha256:"+p.fingerprint(path)["sha256"])
                if mode=="missing":return subprocess.CompletedProcess([],1,b"upload-out",b"original-error")
                if mode=="digest":row["digest"]="sha256:"+"0"*64
                if mode=="size":row["size"]+=1
                if mode=="unfinished":row["state"]="starter"
                saved["assets"].append(row)
                if mode=="duplicate":saved["assets"].append(copy.deepcopy(row))
                if mode=="extra":saved["assets"].append(dict(id=900,name="foreign",state="uploaded",size=1,digest="sha256:"+"0"*64))
                return subprocess.CompletedProcess([],1 if mode=="uncertain"else 0,b"full upload stdout",b"full upload stderr")
            try:
                result=p.publish(fake,proof,paths,target,api,upload)
            except AssertionError as error:
                failure=json.loads((target/"publication-receipt.json").read_bytes())
                assert failure["status"]=="FAIL_COMPLETE_REPLAY_PUBLICATION" and failure["complete"]is False
                assert failure["error"]==repr(error) and "Traceback"in failure["traceback"]
                assert len(calls)==(0 if mode=="occupied"else 1)
                if calls:
                    assert (target/"upload-000.stdout").read_bytes()==(b"upload-out"if mode=="missing"else b"full upload stdout")
                    assert (target/"upload-000.stderr").read_bytes()==(b"original-error"if mode=="missing"else b"full upload stderr")
                raise
            assert result["complete"]is True and result["overwrites"]is False and result["creation_attempted"]is False
            assert len(result["assets"])==len(paths)==len(calls)
            assert all(x["uncertain_upload_reconciled"]is(mode=="uncertain")for x in result["assets"])
            return result
        trial("success");positive.append("complete_publication_exact_bytes")
        trial("uncertain","uncertain");positive.append("uncertain_upload_reconciled_without_retry")
        for mode,needle in [("occupied","release not empty"),("missing","unexpected or missing"),("digest","uploaded bytes"),("size","uploaded bytes"),("unfinished","uploaded bytes"),("duplicate","duplicate release"),("extra","unexpected or missing")]:
            refuse("publication_"+mode,lambda mode=mode:trial("fail-"+mode,mode),needle)
        lifecycle.append("failed_upload_no_retry_full_streams_preserved")
        lifecycle.append("original_rejected_result_and_empty_stream_unchanged")
        assert p.inventory(root)==baseline
        with mock.patch.object(p.subprocess,"run",return_value=subprocess.CompletedProcess([],0,b"",b""))as run:
            p.upload(fake,paths[0])
            assert run.call_args.args[0]==["gh","release","upload",fake["tag"],str(paths[0]),"--repo",p.REPO]
            assert "--clobber"not in run.call_args.args[0]
        positive.append("actual_upload_argv_no_creation_or_clobber")
        failure=ValueError("primary API failure")
        target=work/"api-failure";target.mkdir()
        def api_failure(path):raise failure
        try:p.publish(fake,proof,paths,target,api_failure,lambda *args:(_ for _ in ()).throw(AssertionError("upload must not occur")))
        except ValueError as caught:assert caught is failure
        else:raise AssertionError("API failure lost")
        assert json.loads((target/"publication-receipt.json").read_bytes())["error"]==repr(failure)
        lifecycle.append("API_primary_preserved_without_upload")
        target=work/"receipt-failure";target.mkdir()
        with mock.patch.object(p,"write",side_effect=OSError("secondary receipt failure")),mock.patch("builtins.print")as printed:
            try:p.publish(fake,proof,paths,target,api_failure)
            except ValueError as caught:assert caught is failure
            else:raise AssertionError("secondary replaced primary")
            assert printed.called and "unsaved_publication_receipt"in printed.call_args.args[0]
        lifecycle.append("secondary_receipt_failure_preserves_primary_and_stdout")
    assert len({x["name"]for x in refusals})==len(refusals)
    return dict(status="PASS_COMPLETE_REPLAY_PUBLICATION_CONTROLS",passed=True,current_context=ctx,counts=dict(positive=len(positive),refusals=len(refusals),lifecycle=len(lifecycle)),positive=positive,refusals=refusals,lifecycle=lifecycle,synthetic_inputs_only=True,actual_native_capture_acquired=False,actual_release_mutated=False,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,required=True);a=parser.parse_args()
    ctx=p.context(os.environ,"nominal_early");primary=None
    try:
        p.source_guard(ctx);result=controls(ctx);p.source_guard(ctx)
    except BaseException as error:
        primary=error;result=dict(status="FAIL_COMPLETE_REPLAY_PUBLICATION_CONTROLS",passed=False,error=repr(error),traceback=traceback.format_exc(),physical_acceptance=False)
    try:p.write(a.output,result)
    except BaseException as secondary:
        print(json.dumps(dict(result,save_error=repr(secondary)),sort_keys=True),flush=True)
        if primary is None:raise
    else:print(json.dumps(result,sort_keys=True),flush=True)
    if primary is not None:raise primary
if __name__=="__main__":main()
