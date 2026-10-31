#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted-only immutable RC capsule readback; no extraction or numerical execution."""
import argparse,hashlib,io,json,os,re,subprocess,sys,tarfile,time,traceback,zipfile
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
BRANCH="codex/cdr-current-rc-terminal-readback"
GROUP="cdr-current-rc-terminal-readback"
INPUT="scripts/cdr-current-rc-terminal-readback-inputs.json"
INPUT_SHA="6ffc3e683c564eff5f763b0628ebd28012ec3db5ffc1afa67878c0d534e7d2e5"
MANIFEST="scripts/cdr-current-rc-terminal-readback-pins.json"
OUT=ROOT/"cloud-cdr-current-rc-terminal-readback"
def require(ok,why):
    if not ok:raise AssertionError(why)
def digest(b):return hashlib.sha256(b).hexdigest()
def encoded(v):return(json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+"\n").encode()
def exact(a,b,why):require(encoded(a)==encoded(b),why)
def parse(raw):return json.loads(raw,parse_constant=lambda value:(_ for _ in()).throw(ValueError(value)))
def write(path,raw):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    require(not path.exists()and not path.is_symlink(),"Refuse existing output: "+str(path))
    path.write_bytes(raw)
def context(env=None):
    e=os.environ if env is None else env
    for key,value in {"GITHUB_ACTIONS":"true","RUNNER_ENVIRONMENT":"github-hosted","RUNNER_OS":"Linux",
      "GITHUB_REPOSITORY":"Melihakbulut221/nssoc","GITHUB_EVENT_NAME":"workflow_dispatch",
      "GITHUB_RUN_ATTEMPT":"1","GITHUB_REF":"refs/heads/"+BRANCH}.items():require(e.get(key)==value,"Wrong hosted context: "+key)
    require(re.fullmatch("[0-9a-f]{40}",e.get("GITHUB_SHA",""))is not None,"Invalid source")
    require(re.fullmatch("[1-9][0-9]*",e.get("GITHUB_RUN_ID",""))is not None,"Invalid run")
    return {"source":e["GITHUB_SHA"],"run":int(e["GITHUB_RUN_ID"]),"attempt":1}
def source_guard():
    raw=(ROOT/INPUT).read_bytes();require(digest(raw)==INPUT_SHA,"Inputs changed")
    cfg=parse(raw);pins=parse((ROOT/MANIFEST).read_bytes())
    require(pins["schema"]=="cdr-current-rc-terminal-readback-pins-v1","Manifest schema")
    require(set(pins["files"])=={INPUT,"scripts/cloud_cdr_current_rc_terminal_readback.py","scripts/check_cdr_current_rc_terminal_readback.py"},"Protected source set")
    for name,h in pins["files"].items():
        p=ROOT/name;require(p.is_file()and not p.is_symlink()and digest(p.read_bytes())==h,"Protected source changed: "+name)
    require(cfg["schema"]=="cdr-current-eight-drain-terminal-readback-inputs-v1","Inputs schema")
    return cfg,pins
def raw_api(path):
    require(type(path)is str and not path.startswith(("/","http")),"API path")
    return subprocess.check_output(["gh","api","repos/Melihakbulut221/nssoc/"+path])
def api(path):return parse(raw_api(path))
def reservation(info,ref,ctx,empty):
    tag="cloud-results-"+str(ctx["run"])+"-1-"+GROUP
    require(info["tag_name"]==tag and info["target_commitish"]==ctx["source"]and info["draft"]is False
      and info["prerelease"]is True,"Wrong reserved release")
    require(type(info["id"])is int and info["id"]>0 and ref["object"]["type"]=="commit"
      and ref["object"]["sha"]==ctx["source"],"Wrong reserved tag")
    if empty:require(info["assets"]==[],"Reserved release is not empty")
    return {"tag":tag,"release_id":info["id"],"source":ctx["source"],"run":ctx["run"],"attempt":1,
      "externally_reserved":True,"creation_attempted":False,"assets_overwritten":False}
def wait_reservation(ctx):
    tag="cloud-results-"+str(ctx["run"])+"-1-"+GROUP
    for attempt in range(60):
        try:return reservation(api("releases/tags/"+tag),api("git/ref/tags/"+tag),ctx,True)
        except subprocess.CalledProcessError:
            if attempt==59:raise
            time.sleep(5)
    raise AssertionError("Reservation missing")
def producer_check(cfg,run,jobs,release,ref):
    p=cfg["producer"]
    for key,value in {"id":p["run"],"head_sha":p["source"],"head_branch":p["branch"],"workflow_id":p["workflow_id"],
      "run_attempt":1,"event":"workflow_dispatch","status":"completed","conclusion":"success"}.items():
        require(run[key]==value and type(run[key])is type(value),"Producer run differs: "+key)
    require(jobs["total_count"]==len(jobs["jobs"])==len(cfg["jobs"]),"Producer job count")
    rows=[]
    for j in jobs["jobs"]:
        row={k:j[k]for k in ("id","name","head_sha","run_id","run_attempt","status","conclusion")}
        row["steps"]=[{k:s[k]for k in ("number","name","status","conclusion")}for s in j["steps"]];rows.append(row)
    exact(sorted(rows,key=lambda j:j["id"]),sorted(cfg["jobs"],key=lambda j:j["id"]),"Producer jobs/steps changed")
    require(all(j["status"]=="completed"and j["conclusion"]=="success"for j in rows),"Producer job failed")
    require(release["id"]==p["release_id"]and release["tag_name"]==p["tag"]and release["target_commitish"]==p["source"]
      and release["draft"]is False and release["prerelease"]is True,"Producer release differs")
    require(ref["object"]["type"]=="commit"and ref["object"]["sha"]==p["source"],"Producer tag changed")
    fields=("id","name","size","digest","state","browser_download_url")
    exact(sorted([{k:a[k]for k in fields}for a in release["assets"]],key=lambda a:a["id"]),
      sorted(cfg["assets"],key=lambda a:a["id"]),"Producer asset set changed")
    return True
def validate_snapshot(cfg,snapshots):
    require(set(snapshots)=={"run","jobs","release","tag"},"Producer snapshot namespace")
    return producer_check(cfg,snapshots["run"],snapshots["jobs"],snapshots["release"],snapshots["tag"])

def validate_parts(cfg,parts):
    exact(parts,cfg["parts"],"Parts manifest changed")
    require(parts["format"]=="ordered-tar-gzip-parts-v1"and parts["source_directory"]==cfg["root"],"Archive format/root")
    require(parts["parts"]and [r["index"]for r in parts["parts"]]==list(range(len(parts["parts"]))),"Part order")
    assets={a["name"]:a for a in cfg["assets"]}
    for row in parts["parts"]:
        require(row["name"]==parts["stem"]+".tar.gz.part"+str(row["index"]).zfill(4),"Part basename")
        a=assets[row["name"]];require(a["size"]==row["bytes"]and a["digest"]=="sha256:"+row["sha256"],"Part asset join")
    require(sum(r["bytes"]for r in parts["parts"])==parts["bytes"],"Part total")
def validate_summary(cfg,summary):
    require(summary["status"]==cfg["summary_status"]and summary["source_head"]==cfg["producer"]["source"]
      and summary["run_id"]==cfg["producer"]["run"]and summary["run_attempt"]==1,"Summary producer identity")
    require(len(summary["outputs"])==cfg["summary_output_count"]and"result.json"not in summary["outputs"],"Summary inventory count")
    for key in ("binding_executed","extraction_executed","fresh_RC_pipeline_complete","terminal_finalization_complete"):
        require(summary[key]is True,"Incomplete native pipeline: "+key)
    for key,value in cfg["expected_scope"].items():require(summary[key]is value,"Changed producer acceptance scope")
    require([c["label"]for c in summary["commands"]]==cfg["phase_labels"],"Phase order")
    for c in summary["commands"]:
        require(c["returncode"]==0 and c["supervision_failure"]is None and c["memory_read_error"]is None
          and not c["process_group_cleanup"]["remaining_live"]and not c["process_group_cleanup"]["signals"],"Native command failed")
    require(all(a["completed"]is True for a in summary["terminal_actions"])and not summary.get("terminal_errors"),"Native finalization")
    require(summary["outputs"][cfg["model_member"]]==cfg["model_sha256"],"Model hash")
    for path in cfg["captures"]:
        if path!="result.json":require(summary["outputs"][path]==cfg["planes_sha256"],"Planes hash")
def asset_download(asset,path):
    require(asset["state"]=="uploaded"and type(asset["size"])is int and asset["size"]>0,"Invalid asset")
    require(re.fullmatch("sha256:[0-9a-f]{64}",asset["digest"])is not None,"Invalid asset digest")
    require(Path(asset["name"]).name==asset["name"],"Invalid asset basename")
    require(not path.exists()and not path.is_symlink(),"Refuse existing input")
    with path.open("xb")as stream:
        subprocess.run(["gh","api","-H","Accept: application/octet-stream",
          "repos/Melihakbulut221/nssoc/releases/assets/"+str(asset["id"])],stdout=stream,check=True)
    with path.open("rb")as stream:h=hashlib.file_digest(stream,"sha256").hexdigest()
    require(path.stat().st_size==asset["size"]and asset["digest"]=="sha256:"+h,"Downloaded asset changed")
    return {"id":asset["id"],"name":asset["name"],"bytes":asset["size"],"sha256":h}
def inspect_archive(fileobj,root,expected,captures):
    require("result.json"not in expected and set(captures)=={"result.json","mim/precise/source/native-planes.json","mim/precise_reversed/source/native-planes.json"},"Exact capture set")
    seen=set();members={};selected={};directories=[]
    with tarfile.open(fileobj=fileobj,mode="r|gz")as archive:
        for m in archive:
            name=m.name.rstrip("/")if m.isdir()else m.name
            p=PurePosixPath(name)
            require(name and not p.is_absolute()and str(p)==name and".."not in p.parts and"\\"not in name
              and p.parts[0]==root and name not in seen,"Invalid/duplicate archive path: "+m.name)
            seen.add(name)
            if m.isdir():directories.append(name);continue
            require(m.isreg()and not m.sparse and len(p.parts)>1,"Nonregular archive member: "+name)
            relative=str(PurePosixPath(*p.parts[1:]))
            require(relative in expected or relative=="result.json","Unexpected archive member: "+relative)
            require(m.size>=0,"Negative archive member size")
            keep=relative in captures
            if keep:require(m.size<=16*1024**2,"Selected JSON too large")
            h=hashlib.sha256();size=0;pieces=[]
            stream=archive.extractfile(m);require(stream is not None,"Missing member stream")
            with stream:
                while True:
                    b=stream.read(1024**2)
                    if not b:break
                    size+=len(b);h.update(b)
                    if keep:pieces.append(b)
            require(size==m.size,"Archive member truncated")
            value=h.hexdigest()
            if relative in expected:require(value==expected[relative],"Archive member hash changed: "+relative)
            members[relative]={"bytes":size,"sha256":value}
            if keep:
                raw=b"".join(pieces);require(type(parse(raw))is dict,"Selected JSON must be object");selected[relative]=raw
    require(set(members)==set(expected)|{"result.json"},"Incomplete archive member set")
    require(set(selected)==set(captures),"Missing selected JSON")
    require(root in directories,"Missing GNU tar root directory")
    return members,selected,directories
def validate_readback(cfg,summary,members,selected):
    raw=parse(selected["result.json"]);full={n:r["sha256"]for n,r in members.items()}
    exact({n:h for n,h in full.items()if n!="result.json"},summary["outputs"],"All archive members/summary differ")
    require(full["result.json"]!=digest(encoded(summary)),"Raw result substituted by summary")
    exact({k:v for k,v in raw.items()if k!="outputs"},{k:v for k,v in summary.items()if k!="outputs"},"Raw/publication semantics differ")
    require("publication-driver.log"in summary["outputs"]and"publication-driver.log"not in raw["outputs"],"Publication log delta")
    exact(raw["outputs"],{n:h for n,h in summary["outputs"].items()if n!="publication-driver.log"},"Unexpected raw/publication output delta")
    left=selected["mim/precise/source/native-planes.json"];right=selected["mim/precise_reversed/source/native-planes.json"]
    require(left==right and digest(left)==cfg["planes_sha256"],"Native-order planes differ")
    plane=parse(left)
    require(plane["status"]=="PASS_PD500_NATIVE160_PLANES_51_NETS_19_FAULTS"
      and len(plane["anchors"])==160 and len({a["logical_net"]for a in plane["anchors"]})==51,"Native planes identity")
    layout=[h for n,h in plane["inputs"].items()if n.endswith("/layout/result.json")]
    require(layout==[full["mim/precise/source/parent/layout/result.json"]],"Native plane/layout join")
    require(full[cfg["model_member"]]==cfg["model_sha256"],"Observed model hash")
    return {"full_members":len(full),"raw_outputs":len(raw["outputs"]),"summary_outputs":len(summary["outputs"]),
      "raw_result_sha256":full["result.json"],"raw_result_bytes":members["result.json"]["bytes"],
      "model_sha256":full[cfg["model_member"]],"native_planes_sha256":digest(left),
      "native_plane_anchors":160,"native_plane_logical_nets":51,"both_native_order_planes_byte_equal":True,
      "only_publication_output_addition":{"publication-driver.log":summary["outputs"]["publication-driver.log"]},
      "all_member_hashes_authenticated":True,"raw_result_preserved_without_rewriting":True}

def inspect_zip(stream,captures):
    require(type(captures)is dict and captures and all(n.endswith(".json")for n in captures),"Artifact JSON capture set")
    found={};seen=set()
    with zipfile.ZipFile(stream,"r")as archive:
        for item in archive.infolist():
            name=item.filename.rstrip("/")if item.is_dir()else item.filename;p=PurePosixPath(name)
            require(name and not p.is_absolute()and str(p)==name and".."not in p.parts and"\\"not in name
              and name not in seen,"Unsafe/duplicate artifact entry")
            seen.add(name);kind=(item.external_attr>>16)&0o170000
            require(kind in (0,0o100000,0o040000),"Nonregular artifact entry")
            if name in captures:
                require(not item.is_dir()and item.file_size<=16*1024**2,"Invalid selected artifact JSON")
                raw=archive.read(item);require(len(raw)==item.file_size and type(parse(raw))is dict,"Invalid artifact JSON")
                found[name]=raw
    require(set(found)==set(captures),"Original artifact JSON missing")
    return found
def artifact_readback(cfg,work):
    spec=cfg["artifact"];live=api("actions/artifacts/"+str(spec["id"]))
    exact({k:live[k]for k in spec},spec,"Original artifact metadata changed")
    target=work/"original-native-output.zip"
    with target.open("xb")as stream:
        subprocess.run(["gh","api","repos/Melihakbulut221/nssoc/actions/artifacts/"+str(spec["id"])+"/zip"],
          stdout=stream,check=True)
    with target.open("rb")as stream:h=hashlib.file_digest(stream,"sha256").hexdigest()
    require(target.stat().st_size==spec["size_in_bytes"]and"sha256:"+h==spec["digest"],"Original artifact ZIP changed")
    with target.open("rb")as stream:selected=inspect_zip(stream,cfg["artifact_captures"])
    for name,raw in selected.items():write(OUT/cfg["artifact_captures"][name],raw)
    receipt=parse(selected["hw/soc/out/cloud-cdr-current-eight-drain-fresh-rc-publication/publication.json"])
    require(receipt["status"]=="PASS_COMPLETE_FRESH_WIDTH_RC_EVIDENCE_PUBLICATION_ONLY"
      and receipt["source_head"]==cfg["producer"]["source"]and receipt["run_id"]==cfg["producer"]["run"]
      and receipt["engineering_accepted"]is False,"Original publication receipt did not qualify")
    rows=[{"id":a["id"],"name":a["name"],"size":a["bytes"],"digest":"sha256:"+a["sha256"],"url":a["url"]}for a in receipt["assets"]]
    expected=[{"id":a["id"],"name":a["name"],"size":a["size"],"digest":a["digest"],"url":a["browser_download_url"]}for a in cfg["assets"]]
    exact(sorted(rows,key=lambda r:r["id"]),sorted(expected,key=lambda r:r["id"]),"Original publication asset join")
    after=api("actions/artifacts/"+str(spec["id"]));exact({k:after[k]for k in spec},spec,"Original artifact changed after read")
    result={"artifact":spec,"zip_sha256":h,"zip_bytes":target.stat().st_size,
      "whole_zip_authenticated":True,"native_payloads_extracted":False,
      "selected":{name:{"output":cfg["artifact_captures"][name],"bytes":len(raw),"sha256":digest(raw)}for name,raw in selected.items()},
      "original_publication_receipt_reconstructed":False}
    write(OUT/"artifact-readback.json",encoded(result));return result

def control_proof(ctx):
    jobs=api("actions/runs/"+str(ctx["run"])+"/attempts/1/jobs?per_page=100")
    matches=[j for j in jobs["jobs"]if j["name"]=="source-controls"]
    require(len(matches)==1,"Missing same-source controls")
    j=matches[0];require(j["status"]=="completed"and j["conclusion"]=="success"and j["head_sha"]==ctx["source"],"Source controls did not pass")
    return {"job_id":j["id"],"source":ctx["source"],"run":ctx["run"],"conclusion":"success"}
def publish(ctx,res):
    info=api("releases/"+str(res["release_id"]));ref=api("git/ref/tags/"+res["tag"])
    reservation(info,ref,ctx,True)
    outputs={str(p.relative_to(OUT)):{"bytes":p.stat().st_size,"sha256":digest(p.read_bytes())}
      for p in OUT.iterdir()if p.is_file()and not p.is_symlink()}
    write(OUT/"output-index.json",encoded({"schema":"complete-readback-output-index-v1","files":outputs,"source":ctx,"native_payloads_published":False}))
    receipt={"status":"RUNNING_READBACK_PUBLICATION","source":ctx,"reservation":res,"assets":[],"overwrite":False}
    for p in sorted(OUT.iterdir()):
        require(p.is_file()and not p.is_symlink(),"Unexpected output")
        subprocess.run(["gh","release","upload",res["tag"],str(p),"--repo","Melihakbulut221/nssoc"],check=True)
        current=api("releases/"+str(res["release_id"]));reservation(current,api("git/ref/tags/"+res["tag"]),ctx,False)
        matches=[a for a in current["assets"]if a["name"]==p.name];require(len(matches)==1,"Published asset missing")
        a=matches[0];require(a["state"]=="uploaded"and a["size"]==p.stat().st_size and a["digest"]=="sha256:"+digest(p.read_bytes()),"Published bytes changed")
        receipt["assets"].append({k:a[k]for k in ("id","name","size","digest","state")})
    receipt["status"]="PASS_EXACT_SOURCE_READBACK_PUBLICATION"
    print("CDR_RC_READBACK_PUBLICATION "+encoded(receipt).decode(),flush=True)
    return receipt
def run():
    ctx=context();cfg,pins=source_guard()
    require(not OUT.exists()and not OUT.is_symlink(),"Output already exists")
    OUT.mkdir();work=Path(os.environ["RUNNER_TEMP"])/("cdr-current-rc-terminal-readback-"+str(ctx["run"]))
    require(not work.exists()and not work.is_symlink(),"Acquisition directory already exists");work.mkdir()
    result={"status":"RUNNING_IMMUTABLE_RC_READBACK","collector":ctx,"producer":cfg["producer"],
      "native_archive_acquired_locally":False,"numerical_execution":False,"electrical_accepted":False,
      "physical_accepted":False,"full_phy_accepted":False,"automatic_retry":False}
    reserved=None;primary=None
    try:
        write(OUT/"source-manifest.json",(ROOT/MANIFEST).read_bytes())
        write(OUT/"input-contract.json",(ROOT/INPUT).read_bytes())
        write(OUT/"source-controls.json",encoded(control_proof(ctx)))
        reserved=wait_reservation(ctx);write(OUT/"reservation.json",encoded(reserved))
        snapshots={}
        paths={"run":"actions/runs/"+str(cfg["producer"]["run"]),"jobs":"actions/runs/"+str(cfg["producer"]["run"])+"/attempts/1/jobs?per_page=100",
          "release":"releases/"+str(cfg["producer"]["release_id"]),"tag":"git/ref/tags/"+cfg["producer"]["tag"]}
        for name,path in paths.items():
            raw=raw_api(path);write(OUT/("producer-"+name+".json"),raw);snapshots[name]=parse(raw)
        validate_snapshot(cfg,snapshots)
        auth=[];assets={}
        for a in cfg["assets"]:
            target=work/a["name"];auth.append(asset_download(a,target));assets[a["name"]]=target
        write(OUT/"input-asset-authentication.json",encoded({"assets":auth,"all_original_assets_verified":True,"producer":cfg["producer"]}))
        summary=parse(assets[cfg["summary_asset"]].read_bytes());validate_summary(cfg,summary)
        parts=parse(assets[cfg["parts_asset"]].read_bytes());validate_parts(cfg,parts)
        plan=parse(assets[cfg["plan_asset"]].read_bytes())
        byname={a["name"]:a for a in cfg["assets"]}
        for row in plan["files"]:
            require(row["disposition"]=="direct_and_archive","Missing original direct record")
            a=byname[parts["stem"]+"."+row["suffix"]]
            require((row["bytes"],"sha256:"+row["sha256"])==(a["size"],a["digest"])
              and summary["outputs"][row["member"]]==row["sha256"],"Direct/archive record join")
        joined=work/"joined-verified.tar.gz";whole=hashlib.sha256();total=0
        with joined.open("xb")as dst:
            for part in parts["parts"]:
                with assets[part["name"]].open("rb")as src:
                    while True:
                        b=src.read(1024**2)
                        if not b:break
                        dst.write(b);whole.update(b);total+=len(b)
        require(total==parts["bytes"]and whole.hexdigest()==parts["sha256"],"Joined archive identity")
        with joined.open("rb")as stream:members,selected,dirs=inspect_archive(stream,cfg["root"],summary["outputs"],cfg["captures"])
        measured=validate_readback(cfg,summary,members,selected)
        for name,raw in selected.items():write(OUT/cfg["captures"][name],raw)
        write(OUT/"complete-native-members.json",encoded({"schema":"authenticated-complete-native-members-v1","producer":cfg["producer"],
          "archive":{"bytes":total,"sha256":whole.hexdigest()},"sha256":{n:r["sha256"]for n,r in members.items()},"files":members,
          "directories":dirs,"regular_members":len(members),"all_members_streamed":True,"native_files_extracted":False}))
        result["original_artifact_readback"]=artifact_readback(cfg,work)
        after={name:api(path)for name,path in paths.items()};validate_snapshot(cfg,after)
        source_guard()
        result.update(status="PASS_AUTHENTICATED_COMPLETE_RC_CAPSULE_JSON_READBACK_NOT_ELECTRICAL_ACCEPTANCE",
          measurements=measured,all19assets_authenticated=len(auth)==19,producer_unchanged_after_readback=True,
          archive={"bytes":total,"sha256":whole.hexdigest(),"runner_only":True},
          selected_json={name:{"output":cfg["captures"][name],"bytes":len(raw),"sha256":digest(raw)}for name,raw in selected.items()})
    except BaseException as error:
        primary=error;result.update(status="FAIL_RC_CAPSULE_READBACK",error=repr(error),traceback=traceback.format_exc())
    finally:
        write(OUT/"readback.json",encoded(result))
        try:
            if reserved is not None:publish(ctx,reserved)
        except BaseException as error:
            print("CDR_RC_READBACK_PUBLICATION_FAILURE "+encoded({"error":repr(error),"traceback":traceback.format_exc()}).decode(),file=sys.stderr,flush=True)
            if primary is None:primary=error
    if primary is not None:raise primary
def main():
    p=argparse.ArgumentParser();p.add_argument("--source-check",action="store_true");args=p.parse_args()
    if args.source_check:
        ctx=context();cfg,pins=source_guard();print(json.dumps({"status":"PASS_SOURCE_PINS_ONLY","source":ctx,"inputs_sha256":INPUT_SHA,"files":len(pins["files"]),"native_acquisition":False}));return
    run()
if __name__=="__main__":main()
