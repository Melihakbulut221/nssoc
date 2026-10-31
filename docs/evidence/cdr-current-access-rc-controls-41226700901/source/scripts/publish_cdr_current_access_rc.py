#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Publish complete read-only RC outputs to an independently reserved exact-source release."""
import argparse,hashlib,importlib,json,os,re,subprocess,sys,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REPO="Melihakbulut221/nssoc"
BRANCH="codex/cdr-current-access-rc-readback"
MANIFEST="scripts/cdr-current-access-rc-source-pins.json"
PACK_SHA="fe414dcd92c233554a82a2151232bab8803e6ec7863df3872fbde009d3905816"
def require(ok,message):
    if not ok:raise AssertionError(message)
def encode(obj):
    return (json.dumps(obj,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
def fingerprint(path):
    require(path.is_file() and not path.is_symlink(),"regular publication file")
    with path.open("rb")as f:digest=hashlib.file_digest(f,"sha256").hexdigest()
    return dict(bytes=path.stat().st_size,sha256=digest)
def write(path,obj):
    require(not path.is_symlink(),"publication receipt symlink")
    temp=path.with_name(path.name+".tmp")
    with temp.open("xb")as f:f.write(encode(obj))
    os.replace(temp,path)
def context(env,case):
    require(env.get("GITHUB_ACTIONS")=="true" and env.get("GITHUB_EVENT_NAME")=="workflow_dispatch","hosted manual only")
    require(env.get("GITHUB_REPOSITORY")==REPO and env.get("GITHUB_REF")=="refs/heads/"+BRANCH,"repository/branch")
    require(env.get("GITHUB_RUN_ATTEMPT")=="1","attempt one")
    require(case in ("nominal_early","nominal_late"),"case")
    source=env.get("GITHUB_SHA","");run=env.get("GITHUB_RUN_ID","")
    require(re.fullmatch("[0-9a-f]{40}",source) and re.fullmatch("[1-9][0-9]*",run),"source/run identity")
    group="cdr-current-access-rc-readback-"+case
    return dict(source=source,run=int(run),attempt=1,case=case,group=group,tag="cloud-results-"+run+"-1-"+group)
def source_guard(ctx,root=ROOT):
    require(subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip()==ctx["source"],"exact checkout")
    raw=(root/MANIFEST).read_bytes()
    require(raw==subprocess.check_output(["git","show",ctx["source"]+":"+MANIFEST],cwd=root),"manifest changed")
    m=json.loads(raw)
    require(m["schema"]=="cdr-current-access-rc-source-pins-v1","manifest schema")
    for name,pin in m["files"].items():require(fingerprint(root/name)==pin,"publication source changed: "+name)
    require(m["files"]["scripts/cloud_chunked_results.py"]["sha256"]==PACK_SHA,"qualified pack source")
    return m
def inventory(root):
    require(root.is_dir() and not root.is_symlink(),"owned output directory")
    files={}
    for p in sorted(root.rglob("*")):
        require(not p.is_symlink(),"output symlink")
        if p.is_dir():continue
        require(p.is_file(),"special output file")
        name=p.relative_to(root).as_posix()
        require(name and "\\"not in name and ".."not in Path(name).parts,"output name")
        files[name]=fingerprint(p)
    require(files,"empty output tree")
    return files
def prepare(ctx,root,out,pack):
    require(not out.exists() and not out.is_symlink(),"publication directory new")
    require(not out.resolve().is_relative_to(root.resolve()),"publication outside output tree")
    files=inventory(root);out.mkdir()
    stem=ctx["group"]+"-"+str(ctx["run"])+"-1"
    index=dict(schema="complete-cdr-wave-replay-output-index-v1",context=ctx,files=files,
      original_capture_replayed_is_not_electrical_acceptance=True,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
    write(out/"complete-output-index.json",index)
    manifest=pack(root,stem,out,256*1024**2)
    require(inventory(root)==files,"output changed during archive")
    require(manifest["source_directory"]==root.name and manifest["verification"]==dict(parts=len(manifest["parts"]),bytes=manifest["bytes"],sha256=manifest["sha256"],all_parts_and_combined_bytes_verified=True),"complete archive verification")
    paths=[out/"complete-output-index.json",out/(stem+".parts.json")]
    paths.extend(out/row["name"]for row in manifest["parts"])
    require(len(paths)==len({p.name for p in paths}) and all(fingerprint(p)["bytes"]>0 for p in paths),"nonempty distinct upload assets")
    for row,path in zip(manifest["parts"],paths[2:]):
        require(fingerprint(path)=={k:row[k]for k in("bytes","sha256")},"archive part identity")
    return paths,dict(files=files,archive={k:manifest[k]for k in("bytes","sha256")},parts=manifest["parts"],complete_empty_streams_preserved=True)
def api(path):
    return json.loads(subprocess.check_output(["gh","api","repos/"+REPO+"/"+path]))
def validate_release(ctx,proof,info,ref):
    require(info.get("id")==proof.get("release_id") and type(info.get("id"))is int and info["id"]>0,"reserved release ID")
    require(info.get("tag_name")==ctx["tag"] and info.get("target_commitish")==ctx["source"],"reserved release source")
    require(info.get("draft")is False and info.get("prerelease")is True,"public prerelease")
    require(ref.get("ref")=="refs/tags/"+ctx["tag"] and ref.get("object",{}).get("type")=="commit" and ref["object"].get("sha")==ctx["source"],"immutable tag")
    require(proof.get("tag")==ctx["tag"] and proof.get("tested_source")==ctx["source"] and proof.get("target_verified")is True and proof.get("externally_reserved")is True and proof.get("creation_attempted")is False and proof.get("assets_overwritten")is False and proof.get("existing_assets")==[],"independent reservation")
    rows=info.get("assets");require(isinstance(rows,list),"asset list")
    require(all(type(x.get("id"))is int and x["id"]>0 for x in rows),"asset IDs")
    require(len(rows)==len({x["name"]for x in rows})==len({x["id"]for x in rows}),"duplicate release assets")
    return {x["name"]:x for x in rows}
def upload(ctx,path):
    return subprocess.run(["gh","release","upload",ctx["tag"],str(path),"--repo",REPO],capture_output=True)
def publish(ctx,proof,paths,out,api_call=api,upload_call=upload):
    expected={p.name:fingerprint(p)for p in paths}
    require(len(expected)==len(paths),"duplicate upload names")
    require(all(re.fullmatch("[A-Za-z0-9_.-]+",p.name) and expected[p.name]["bytes"]>0 for p in paths),"upload filenames/nonempty")
    def state():
        return validate_release(ctx,proof,api_call("releases/tags/"+ctx["tag"]),api_call("git/ref/tags/"+ctx["tag"]))
    receipt=dict(status="RUNNING_COMPLETE_REPLAY_PUBLICATION",context=ctx,assets=[],overwrites=False,creation_attempted=False,complete=False)
    primary=None
    try:
        require(state()=={},"release not empty before publication")
        for index,path in enumerate(paths):
            require(fingerprint(path)==expected[path.name],"asset changed before upload")
            result=upload_call(ctx,path)
            (out/("upload-%03d.stdout"%index)).write_bytes(result.stdout)
            (out/("upload-%03d.stderr"%index)).write_bytes(result.stderr)
            current=state()
            require(set(current)=={p.name for p in paths[:index+1]},"unexpected or missing publication assets")
            for p in paths[:index+1]:
                row=current[p.name];pin=expected[p.name]
                require(row.get("state")=="uploaded" and row.get("size")==pin["bytes"] and row.get("digest")=="sha256:"+pin["sha256"],"uploaded bytes not verified: "+p.name)
            require(fingerprint(path)==expected[path.name],"asset changed after upload")
            a=current[path.name]
            receipt["assets"].append(dict(id=a["id"],name=path.name,**expected[path.name],upload_returncode=result.returncode,uncertain_upload_reconciled=result.returncode!=0))
            write(out/"publication-receipt.json",receipt)
        receipt.update(status="PASS_COMPLETE_REPLAY_OUTPUT_PUBLICATION_ONLY",complete=True)
    except BaseException as error:
        primary=error;receipt.update(status="FAIL_COMPLETE_REPLAY_PUBLICATION",error=repr(error),traceback=traceback.format_exc())
    finally:
        try:write(out/"publication-receipt.json",receipt)
        except BaseException as error:
            print(json.dumps(dict(unsaved_publication_receipt=receipt,save_error=repr(error)),sort_keys=True),flush=True)
            if primary is None:primary=error
    if primary is not None:raise primary
    return receipt
def main():
    parser=argparse.ArgumentParser();parser.add_argument("--case",required=True);parser.add_argument("--output",type=Path,required=True);parser.add_argument("--publication",type=Path,required=True);parser.add_argument("--reservation",type=Path,required=True)
    a=parser.parse_args();ctx=context(os.environ,a.case)
    source_guard(ctx)
    module=importlib.import_module("cloud_chunked_results")
    require(Path(module.__file__).resolve()==(ROOT/"scripts/cloud_chunked_results.py").resolve(),"pack module shadow")
    proof=json.loads(a.reservation.read_bytes())
    try:
        paths,index=prepare(ctx,a.output,a.publication,module.pack)
        source_guard(ctx)
        receipt=publish(ctx,proof,paths,a.publication)
        require(inventory(a.output)==index["files"],"published original output changed")
        source_guard(ctx)
        print(json.dumps(dict(receipt,archive=index["archive"],complete_file_count=len(index["files"]),physical_acceptance=False,timing_accepted=False,full_phy_accepted=False),sort_keys=True),flush=True)
    except BaseException as error:
        failure=dict(status="FAIL_REPLAY_OUTPUT_PRESERVATION",error=repr(error),traceback=traceback.format_exc(),context=ctx,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
        print(json.dumps(failure,sort_keys=True),flush=True)
        try:
            if a.publication.is_dir()and not a.publication.is_symlink():write(a.publication/"preservation-failure.json",failure)
        except BaseException as secondary:
            print(json.dumps(dict(primary=repr(error),secondary_preservation_error=repr(secondary))),flush=True)
        raise
if __name__=="__main__":main()
