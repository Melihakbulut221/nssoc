#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted-only immutable final-marker text selection; never executes CAD."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

REPOSITORY = "Melihakbulut221/nssoc"
BRANCH = "codex/mainchip-net459-neighborhood-plan"
GROUP = "mainchip-final-marker-readback"
ROOT = Path(__file__).resolve().parent.parent
PRODUCER_SOURCE = "8e9223b0be6e644d4c5684b94b13c2888c531e79"
PRODUCER_RUN = 40894408041
PRODUCER_RELEASE = 427992502
PRODUCER_TAG = "cloud-results-40894408041-1-mainchip-fixed-engine-route-tail-on-audit"
PRODUCER_WORKFLOW = ".github/workflows/mainchip-fixed-engine-route-tail.yml"
JOBS = {123519510524:"source-controls",123520714945:"preserve-source-job-log",
 123520805697:"route-only (on)",123520805825:"route-only (off)",
 123557468469:"audit-only (off)",123557468578:"audit-only (on)",123574151200:"comparison"}
ASSETS = {'outputs.json': {'id': 689123081, 'name': 'outputs.json', 'bytes': 21497, 'sha256': '07032f779bc1f664fe58da6953287ab7d66f880d8e24adf725b27a00f6f7209a'}, 'parts.json': {'id': 689123210, 'name': 'parts.json', 'bytes': 493, 'sha256': 'e5730258718841c8ad1627e20256e7352535036c0d971064e6d627566a15d787'}, 'route-tail-evidence.tar.gz.part000': {'id': 689123749, 'name': 'route-tail-evidence.tar.gz.part000', 'bytes': 536870912, 'sha256': '36912384bebd31427e9d0de8d29a55706e2c8105c420ab6853261dd00c76c5bf'}, 'route-tail-evidence.tar.gz.part001': {'id': 689125024, 'name': 'route-tail-evidence.tar.gz.part001', 'bytes': 215797044, 'sha256': '0037a9862e74a652261d2c6eae510bdf24a89420bbd0364d01a524c545ed92d6'}}
SELECTED = {'case-result.json': {'bytes': 135954, 'sha256': 'b2439801f4635b92c0e9b408a48d1945232faa2c3c397003c33b79773df8fb25'}, 'writer-raw.json': {'bytes': 55794, 'sha256': '240b5f370a9c2a87850805f4c04b3dfb867f26cf89666bbccdd3356929902d90'}, 'work/initial-drc-markers.json': {'bytes': 1614, 'sha256': '03583e7e6d24efc7be21bc7399778e4d463312906476bb87fd0f28a5a948aa1c'}, 'work/initial-drc.rpt': {'bytes': 143, 'sha256': '529f5939d90f251dc00b3733e8c1762450575e8d3278bb3836598de14aaf52b3'}, 'work/initial-drc-reread.rpt': {'bytes': 143, 'sha256': '529f5939d90f251dc00b3733e8c1762450575e8d3278bb3836598de14aaf52b3'}, 'work/fixed-routing.drc': {'bytes': 143, 'sha256': '529f5939d90f251dc00b3733e8c1762450575e8d3278bb3836598de14aaf52b3'}, 'work/drc-audit-result.json': {'bytes': 2771, 'sha256': '61ae15342c34e1de16aa6d594886a88a962b9c6e7635e5662f9edffb01075573'}, 'work/unfix-audit-result.json': {'bytes': 2507, 'sha256': 'b6d6125af92c9ff3921305bea8e07520e0d143444daa9f383e93650a02b35a7c'}, 'work/route-audit-result.json': {'bytes': 811, 'sha256': 'b433964de3ed9ce204e11796cf9b892f8a4ff34d724bd169f6e61783335850c8'}, 'work/original-gate-after-final-two-net-drc/result.json': {'bytes': 627, 'sha256': '1f02b809252c7be5856cbd992b5c425d99c8e1daf7188232e0dc58afa6b9eb6e'}, 'supervision/drc-audit.command.json': {'bytes': 1275, 'sha256': '7f8fc69583d16fe598e86ef9ecfdb083b94ec1f91cec62b6a9cce3d82158b439'}, 'supervision/drc-audit.stdout': {'bytes': 285, 'sha256': 'ee72cf880ca9700fd51d4a6754bd20c6f3973e71b95345af0139544519dabad1'}, 'supervision/drc-audit.stderr': {'bytes': 0, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}, 'supervision/full-original-class-read-only-DRT.command.json': {'bytes': 1240, 'sha256': 'afb20450428cf6d1f5a5937233753a72e60a78b71dfacacd77f701155befd84d'}, 'supervision/full-original-class-read-only-DRT.stdout': {'bytes': 4158, 'sha256': '4e67e060eb2bd0aaaccac7abafb65b2be38b4ab4b555a9222333a880cc1b848e'}, 'supervision/full-original-class-read-only-DRT.stderr': {'bytes': 0, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}}
ARCHIVE = {'bytes': 752667956, 'sha256': '86232efc223698eee1a52fa55866ba08bd791763967ed6a5fdb2bd11fd55a08f'}
MEMBER_COUNT = 145
MEMBER_BYTES = 5763445029
CHUNK_BYTES = 24576

def require(value, reason):
    if not value:
        raise AssertionError(reason)

def digest(raw):
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())

def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2)+"\n").encode()

def decode(raw):
    def unique(pairs):
        result={}
        for key,value in pairs:
            require(key not in result,"duplicate JSON key: "+key)
            result[key]=value
        return result
    return json.loads(raw.decode("utf-8"),object_pairs_hook=unique)

def context(env):
    require(env.get("GITHUB_ACTIONS")=="true","hosted only")
    require(env.get("GITHUB_EVENT_NAME")=="workflow_dispatch","manual only")
    require(env.get("GITHUB_REPOSITORY")==REPOSITORY,"repository")
    require(env.get("GITHUB_REF")=="refs/heads/"+BRANCH,"readback branch")
    require(env.get("GITHUB_RUN_ATTEMPT")=="1","attempt one only")
    run=env.get("GITHUB_RUN_ID",""); source=env.get("GITHUB_SHA","")
    require(re.fullmatch(r"[1-9][0-9]*",run) is not None,"run ID")
    require(re.fullmatch(r"[0-9a-f]{40}",source) is not None,"immutable source")
    return dict(source=source,run_id=int(run),attempt=1,
                group=GROUP,token=run+"-1",native_executed=False)

def api(path):
    return decode(subprocess.check_output(["gh","api","repos/"+REPOSITORY+"/"+path],timeout=120))

def release_binding(info,ref,tag,source):
    require(type(info.get("id"))is int and info["id"]>0,"release ID")
    require(info.get("tag_name")==tag and info.get("target_commitish")==source,"release source")
    require(info.get("draft")is False and info.get("prerelease")is True,"evidence release")
    require(ref.get("ref")=="refs/tags/"+tag and
      ref.get("object",{}).get("type")=="commit" and
      ref["object"].get("sha")==source,"tag object")
    assets=info["assets"]
    require(len({a["id"]for a in assets})==len(assets) and
            len({a["name"]for a in assets})==len(assets),"duplicate release asset")
    return {a["name"]:a for a in assets}

def reservation(ctx,proof,info,ref):
    tag="cloud-results-"+ctx["token"]+"-"+GROUP
    assets=release_binding(info,ref,tag,ctx["source"])
    require(proof.get("tag")==tag and proof.get("tested_source")==ctx["source"] and
            proof.get("release_id")==info["id"],"reservation identity")
    require(proof.get("target_verified")is True and proof.get("assets_overwritten")is False,
            "reservation verification")
    require(proof.get("externally_reserved")is True and proof.get("creation_attempted")is False,
            "externally reserved only")
    require(proof.get("existing_assets")==[] and assets=={},"fresh reservation required")
    return dict(release_id=info["id"],tag=tag,source=ctx["source"],verified_before_acquisition=True)

def validate_live(run,jobs,release,ref):
    require(run.get("id")==PRODUCER_RUN and run.get("run_attempt")==1 and
      run.get("head_sha")==PRODUCER_SOURCE and run.get("head_branch")=="codex/mainchip-fixed-engine-route-tail",
      "producer run identity")
    require(run.get("event")=="workflow_dispatch" and run.get("path")==PRODUCER_WORKFLOW,
            "producer workflow")
    require(run.get("status")=="completed" and run.get("conclusion")=="success","producer terminal")
    rows=jobs["jobs"]
    require(jobs.get("total_count")==len(JOBS) and len(rows)==len(JOBS) and
            {r["id"]:r["name"]for r in rows}==JOBS,"complete producer jobs")
    for row in rows:
        require(row.get("run_id")==PRODUCER_RUN and row.get("head_sha")==PRODUCER_SOURCE and
          row.get("status")=="completed" and row.get("conclusion")=="success","producer job binding")
    assets=release_binding(release,ref,PRODUCER_TAG,PRODUCER_SOURCE)
    require(release["id"]==PRODUCER_RELEASE,"producer release")
    for name,pin in ASSETS.items():
        a=assets.get(name,{})
        require(a.get("id")==pin["id"] and a.get("size")==pin["bytes"] and
                a.get("digest")=="sha256:"+pin["sha256"] and a.get("state")=="uploaded",
                "producer asset: "+name)
    return dict(source=PRODUCER_SOURCE,run_id=PRODUCER_RUN,attempt=1,
      release_id=PRODUCER_RELEASE,tag=PRODUCER_TAG,jobs=JOBS,assets=ASSETS,
      producer_workflow_success=True,physical_acceptance=False)

def checked_path(name):
    require(type(name)is str and name and "\\" not in name and "\x00" not in name,"archive path type")
    p=PurePosixPath(name)
    require(not p.is_absolute() and p.as_posix()==name and
            all(x not in ("",".","..")for x in p.parts),"unsafe archive path: "+name)
    return p

def validate_map(files):
    require(type(files)is dict and files,"member map")
    for name,row in files.items():
        checked_path(name)
        require(set(row)=={"bytes","sha256"} and type(row["bytes"])is int and row["bytes"]>=0 and
                type(row["sha256"])is str and re.fullmatch(r"[0-9a-f]{64}",row["sha256"]),
                "member fingerprint: "+name)
        for parent in PurePosixPath(name).parents:
            if str(parent)!=".":
                require(str(parent)not in files,"file/directory collision")
    return files

def metadata(outputs_raw,parts_raw):
    require(digest(outputs_raw)=={k:ASSETS["outputs.json"][k]for k in ("bytes","sha256")},"outputs bytes")
    require(digest(parts_raw)=={k:ASSETS["parts.json"][k]for k in ("bytes","sha256")},"parts bytes")
    outputs=decode(outputs_raw); parts=decode(parts_raw)
    require(set(outputs)=={"files","mode","stage","source","physical_acceptance"} and
      outputs["mode"]=="on" and outputs["stage"]=="audit" and outputs["source"]==PRODUCER_SOURCE and
      outputs["physical_acceptance"]is False,"output context")
    files=dict(validate_map(outputs["files"]))
    require("outputs.json"not in files and "parts.json"not in files,"publication map sequencing")
    files["outputs.json"]=digest(outputs_raw)
    require(len(files)==MEMBER_COUNT and sum(x["bytes"]for x in files.values())==MEMBER_BYTES,
            "complete archive census")
    require({k:files[k]for k in SELECTED}==SELECTED,"selected exact map")
    expected_parts=[{k:ASSETS["route-tail-evidence.tar.gz.part%03d"%i][k]
                     for k in ("name","bytes","sha256")}for i in range(2)]
    require(parts==dict(archive=ARCHIVE,parts=expected_parts),"complete part manifest")
    require(sum(p["bytes"]for p in expected_parts)==ARCHIVE["bytes"],"archive size")
    return files,parts

def download(pin,path):
    # This function is called only in a hosted runner after reservation validation.
    require(not path.exists(),"download no overwrite")
    with path.open("xb")as stream:
        subprocess.run(["gh","api","-H","Accept: application/octet-stream",
          "repos/"+REPOSITORY+"/releases/assets/"+str(pin["id"])],
          stdout=stream,check=True,timeout=1800)
    require(file_digest(path)=={k:pin[k]for k in ("bytes","sha256")},"download fingerprint: "+pin["name"])

def file_digest(path):
    h=hashlib.sha256(); size=0
    with path.open("rb")as stream:
        while True:
            block=stream.read(1024*1024)
            if not block:break
            size+=len(block);h.update(block)
    return dict(bytes=size,sha256=h.hexdigest())

def combine_parts(paths,manifest,destination):
    require(not destination.exists(),"archive no overwrite")
    with destination.open("xb")as output:
        for path,row in zip(paths,manifest["parts"],strict=True):
            require(file_digest(path)=={k:row[k]for k in ("bytes","sha256")},"part fingerprint")
            with path.open("rb")as stream:shutil.copyfileobj(stream,output,1024*1024)
    require(file_digest(destination)==manifest["archive"],"complete archive fingerprint")

def select_archive(archive,expected,selected,out):
    """Hash every regular member, retain only declared text. No tar.extract calls."""
    validate_map(expected)
    require(set(selected)<=set(expected),"unknown selected member")
    require(not out.exists() and not out.is_symlink(),"selected output must be new")
    out.mkdir(parents=True)
    directories={str(p)for name in expected for p in PurePosixPath(name).parents if str(p)!="."}
    seen=set(); observed={}; retained={}
    with tarfile.open(archive,"r|gz")as tar:
        for member in tar:
            name=member.name; checked_path(name)
            require(name not in seen,"duplicate archive member: "+name);seen.add(name)
            if member.isdir():
                require(name in directories,"unexpected archive directory: "+name)
                continue
            require(member.isfile() and not member.issparse(),"link/special/sparse archive entry: "+name)
            require(name in expected,"unexpected archive member: "+name)
            row=expected[name]
            require(member.size==row["bytes"],"member declared size: "+name)
            h=hashlib.sha256(); size=0; chunks=[] if name in selected else None
            stream=tar.extractfile(member)
            require(stream is not None,"missing archive stream")
            with stream:
                while True:
                    block=stream.read(1024*1024)
                    if not block:break
                    size+=len(block);require(size<=row["bytes"],"member size overrun");h.update(block)
                    if chunks is not None:chunks.append(block)
            found=dict(bytes=size,sha256=h.hexdigest())
            require(found==row,"member fingerprint: "+name);observed[name]=found
            if chunks is not None:
                raw=b"".join(chunks)
                require(len(raw)<=2*1024*1024,"selected text bound")
                text=raw.decode("utf-8");require("\x00"not in text,"selected text NUL")
                path=out/name;path.parent.mkdir(parents=True,exist_ok=True)
                with path.open("xb")as target:target.write(raw)
                retained[name]=found
    require(observed==expected,"missing archive members")
    require(set(retained)==set(selected),"missing selected members")
    return dict(full_members=observed,selected=retained,full_archive_verified=True,
      native_members_extracted=False,selected_bytes=sum(x["bytes"]for x in retained.values()))

def write_new(path,raw):
    require(not path.exists() and not path.is_symlink(),"evidence no overwrite")
    with path.open("xb")as stream:stream.write(raw)

def emit(out,writer=print):
    rows={}
    for path in sorted(out.rglob("*")):
        require(not path.is_symlink() and (path.is_dir()or path.is_file()),"evidence special file")
        if path.is_file():rows[path.relative_to(out).as_posix()]=file_digest(path)
    writer("FINAL_MARKER_READBACK_INDEX "+json.dumps(rows,sort_keys=True),flush=True)
    for name,row in rows.items():
        raw=(out/name).read_bytes()
        pieces=[raw[i:i+CHUNK_BYTES]for i in range(0,len(raw),CHUNK_BYTES)]or[b""]
        for index,piece in enumerate(pieces):
            writer("FINAL_MARKER_READBACK_CHUNK "+json.dumps(dict(name=name,index=index,
              chunks=len(pieces),bytes=row["bytes"],sha256=row["sha256"],
              base64=base64.b64encode(piece).decode()),sort_keys=True),flush=True)
    return rows

def perform(ctx,proof,out,read=api,fetch=download):
    current_tag="cloud-results-"+ctx["token"]+"-"+GROUP
    reserved=reservation(ctx,proof,read("releases/"+str(proof["release_id"])),
                          read("git/ref/tags/"+current_tag))
    write_new(out/"release-reservation.json",encode(dict(proof=proof,validated=reserved)))
    inputs=dict(run=read("actions/runs/"+str(PRODUCER_RUN)),
      jobs=read("actions/runs/"+str(PRODUCER_RUN)+"/attempts/1/jobs?per_page=100"),
      release=read("releases/"+str(PRODUCER_RELEASE)),
      ref=read("git/ref/tags/"+PRODUCER_TAG))
    binding=validate_live(**inputs)
    for name,value in inputs.items():write_new(out/("producer-"+name+".json"),encode(value))
    write_new(out/"producer-binding.json",encode(binding))
    temporary=tempfile.TemporaryDirectory(prefix="mainchip-final-marker-",dir=os.environ["RUNNER_TEMP"])
    primary=None
    try:
        temp=Path(temporary.name)
        require(shutil.disk_usage(temp).free>=2*ARCHIVE["bytes"]+1024**3,"cloud download disk budget")
        for name in ("outputs.json","parts.json"):
            fetch(ASSETS[name],temp/name)
            write_new(out/("producer-"+name),(temp/name).read_bytes())
        files,parts=metadata((temp/"outputs.json").read_bytes(),(temp/"parts.json").read_bytes())
        paths=[]
        for row in parts["parts"]:
            path=temp/row["name"];fetch(ASSETS[row["name"]],path);paths.append(path)
        archive=temp/"audit.tar.gz";combine_parts(paths,parts,archive)
        selection=select_archive(archive,files,SELECTED,out/"selected")
        receipt=dict(status="PASS_AUTHENTICATED_FINAL_MARKER_TEXT_READBACK",current_context=ctx,
          producer=binding,reservation=reserved,archive=ARCHIVE,**selection,
          native_executed=False,geometry_changed=False,physical_acceptance=False,
          timing_accepted=False,full_phy_accepted=False)
        write_new(out/"extraction-receipt.json",encode(receipt))
    except BaseException as exc:
        primary=exc
        raise
    finally:
        try:temporary.cleanup()
        except BaseException as cleanup_error:
            try:write_new(out/"cleanup-error.json",encode(dict(type=type(cleanup_error).__name__,error=str(cleanup_error))))
            except BaseException:pass
            if primary is None:raise
    write_new(out/"readback-result.json",encode(dict(receipt,temporary_cleanup_complete=True)))
    return receipt

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--reservation",type=Path,required=True)
    args=parser.parse_args();ctx=context(os.environ)
    head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    require(head==ctx["source"],"checkout identity")
    require(not args.output.exists() and not args.output.is_symlink(),"output no overwrite")
    args.output.mkdir(parents=True)
    primary=None
    try:
        require(args.reservation.is_file() and not args.reservation.is_symlink(),"reservation regular file")
        return perform(ctx,decode(args.reservation.read_bytes()),args.output)
    except BaseException as exc:
        primary=exc
        failure=dict(status="FAIL_FINAL_MARKER_TEXT_READBACK",current_context=ctx,
          error=dict(type=type(exc).__name__,message=str(exc)),native_executed=False,
          physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
        try:write_new(args.output/"readback-failure.json",encode(failure))
        except BaseException:
            try:print("FINAL_MARKER_READBACK_FAILURE "+json.dumps(failure,sort_keys=True),flush=True)
            except BaseException:pass
        raise
    finally:
        try:emit(args.output)
        except BaseException:
            if primary is None:raise

if __name__=="__main__":
    main()
