#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted source and storage-failure controls; never acquires native inputs."""
import ast,contextlib,hashlib,json,os,subprocess,tempfile,traceback,types
from pathlib import Path
from unittest.mock import patch
import cdr_current_eight_drain_loaded_admission as a
import check_cdr_current_eight_drain_loaded as frozen
import cloud_cdr_eight_drain_storage_stage_v1 as stage
ROOT=Path(__file__).resolve().parents[1]
METHOD="scripts/cdr-eight-drain-storage-methods-v1.json"
BRANCH="codex/cdr-eight-drain-storage-preflight-v1"
FALSE=("native_execution_authorized","native_acquisition_authorized","simulation_authorized","electrical_accepted","physical_accepted","full_phy_accepted")

def require(value,message):
    if not value:raise AssertionError(message)

def source():
    e=os.environ
    require(e.get("GITHUB_ACTIONS")=="true"and e.get("RUNNER_ENVIRONMENT")=="github-hosted"and e.get("RUNNER_OS")=="Linux","Hosted Linux only")
    require(e.get("GITHUB_REPOSITORY")=="Melihakbulut221/nssoc"and e.get("GITHUB_REF")=="refs/heads/"+BRANCH,"Exact source branch")
    require(e.get("GITHUB_EVENT_NAME")=="workflow_dispatch"and e.get("GITHUB_RUN_ATTEMPT")=="1","Manual first attempt")
    require(subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()==e["GITHUB_SHA"],"Checkout HEAD differs")
    m=json.loads((ROOT/METHOD).read_bytes())
    require(m["branch"]==BRANCH and m["schema"]=="cdr-eight-drain-storage-source-v1","Method identity")
    require(all(m[k]is False for k in FALSE),"Source-only authority")
    for name,digest in m["protected_sha256"].items():
        p=ROOT/name;require(p.is_file()and not p.is_symlink(),"Required regular source: "+name)
        with p.open("rb")as stream:require(hashlib.file_digest(stream,"sha256").hexdigest()==digest,"Source digest: "+name)
    original=json.loads((ROOT/"scripts/cdr-current-eight-drain-loaded-methods.json").read_bytes())
    require(len(original["protected_sha256"])==1961,"Frozen complete closure")
    require(all(m["protected_sha256"].get(n)==h for n,h in original["protected_sha256"].items()),"Dropped frozen source")
    require(stage.NATIVE_EXECUTION_AUTHORIZED is False,"Native entry activated")
    require(subprocess.check_output(["git","config","--get","core.sparseCheckout"],text=True).strip()=="true","Sparse checkout absent")
    require(subprocess.check_output(["git","config","--get","core.sparseCheckoutCone"],text=True).strip()=="false","Noncone checkout absent")
    require(subprocess.check_output(["git","config","--get","remote.origin.partialclonefilter"],text=True).strip()=="blob:none","Partial clone absent")
    return m

def storage_controls():
    rows=[]
    def context(root):
        out=root/"out";out.mkdir()
        return dict(case="vi_bias_off",prepare=False,group="cdr-current-eight-drain-loaded-vi_bias_off",output=out,worker=root/"worker",transport=root/"transport",label="storage-fixture",seconds=7200)
    def check(label,free,source_bytes=0):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);ctx=context(root)
            if label=="copy":
                ctx["worker"].mkdir()
                with(ctx["worker"]/"sparse-fixture").open("wb")as f:f.truncate(source_bytes)
            with patch.object(stage,"ROOT",root),patch.object(stage.shutil,"disk_usage",return_value=types.SimpleNamespace(free=free)):
                error=None
                try:r=stage.storage(ctx,label)
                except stage.StorageRefusal as ex:error=ex;r=ex.record
                record=json.loads((ctx["output"]/"storage-checks"/(label+".json")).read_bytes())
                require(record==r and r["free_bytes"]==free,"Measured storage record differs")
                expected=16*1024**3 if label=="initial"else max(4*1024**3,2*source_bytes+1024**3)
                require(r["required_bytes"]==expected and r["sufficient"]is(free>=expected),"Original storage boundary changed")
                require((error is None)==(free>=expected),"Storage refusal boundary changed")
                if error:require(str(error)=="Insufficient full loaded evidence storage","Primary reason changed")
            rows.append(dict(label=label,free=free,required=expected,refused=error is not None))
    for n in (16*1024**3-1,16*1024**3,16*1024**3+1):check("initial",n)
    for label in ("copy","publication"):
        for n in (4*1024**3-1,4*1024**3):check(label,n)
    for n in (5*1024**3-1,5*1024**3):check("copy",n,2*1024**3)
    with tempfile.TemporaryDirectory()as td:
        root=Path(td);ctx=context(root)
        with patch.object(stage,"ROOT",root),patch.object(stage.shutil,"disk_usage",return_value=types.SimpleNamespace(free=16*1024**3)):
            stage.storage(ctx,"initial")
            before=(ctx["output"]/"storage-checks"/"initial.json").read_bytes()
            try:stage.storage(ctx,"initial")
            except FileExistsError:pass
            else:raise AssertionError("Storage receipt overwritten")
            require((ctx["output"]/"storage-checks"/"initial.json").read_bytes()==before,"Original storage receipt changed")
    rows.append(dict(label="receipt_overwrite_refused"))
    with tempfile.TemporaryDirectory()as td:
        root=Path(td);ctx=context(root);target=root/"elsewhere";target.mkdir()
        (ctx["output"]/"storage-checks").symlink_to(target,target_is_directory=True)
        with patch.object(stage,"ROOT",root),patch.object(stage.shutil,"disk_usage",return_value=types.SimpleNamespace(free=16*1024**3)):
            try:stage.storage(ctx,"initial")
            except AssertionError:pass
            else:raise AssertionError("Symlink journal accepted")
        require(not list(target.iterdir()),"Symlink target was written")
    rows.append(dict(label="symlink_journal_refused"))
    with tempfile.TemporaryDirectory()as td:
        root=Path(td);ctx=context(root);ctx["output"].rmdir();published=[]
        with patch.dict(os.environ,{"GITHUB_SHA":"a"*40,"GITHUB_RUN_ID":"12345"}),patch.object(stage,"ROOT",root),patch.object(stage.a,"authorize",return_value={}),patch.object(stage.shutil,"disk_usage",return_value=types.SimpleNamespace(free=16*1024**3-1)),patch.object(stage,"execute",side_effect=AssertionError("Native execution forbidden"))as execute,patch.object(stage,"fetch_preparation",side_effect=AssertionError("Native preparation acquisition forbidden"))as fetch,patch.object(stage,"publish",side_effect=lambda c,r:published.append(json.loads((c["output"]/"result.json").read_bytes()))):
            try:stage.run_case(ctx,{})
            except stage.StorageRefusal as ex:require(ex.record["free_bytes"]==16*1024**3-1,"Primary record lost")
            else:raise AssertionError("Refused storage became PASS")
            require(execute.call_count==fetch.call_count==0,"Native function reached after storage refusal")
        r=json.loads((ctx["output"]/"result.json").read_bytes())
        require(r["body_error"]["type"]=="StorageRefusal"and "Insufficient full loaded evidence storage"in r["body_error"]["error"],"Primary failure lost")
        require(r["status"]=="FAIL_OR_REJECTED_CURRENT_TAIL_LOADED_CASE"and r["native_case_passed"]is False,"Storage became acceptance")
        require(len(r["storage"])==1 and r["storage"][0]["required_bytes"]==16*1024**3,"Initial storage not retained")
        require("storage-checks/initial.json"in r["outputs"]and len(published)==1,"Complete failed outer result not published")
        require(all(r[k]is False for k in ("accepted","cdr_accepted","qualified_pex","full_phy_accepted","physical_accepted")),"Failure acceptance changed")
    rows.append(dict(label="actual_outer_lifecycle_retains_primary_refusal_and_inventory_no_native_calls"))
    try:stage.main()
    except SystemExit as error:require("Native execution disabled"in str(error),"Wrong CLI refusal")
    else:raise AssertionError("Native CLI enabled")
    rows.append(dict(label="native_cli_refused"))
    return dict(cases=rows,count=len(rows),native_executed=False)

def candidate_publication_controls():
    scope=dict(frozen.publication_controls.__dict__)
    scope.update(a=a,s=stage,execution=types.SimpleNamespace(env=frozen.env))
    for name in ("records","archive_check","fixture","controls"):
        fn=getattr(frozen.publication_controls,name)
        scope[name]=types.FunctionType(fn.__code__,scope,fn.__name__,fn.__defaults__,fn.__closure__)
    r=scope["controls"]()
    require((r["publication_cases"],r["actual_lifecycle_cases"])==(15,2),"Complete original publisher controls")
    return r

def main():
    out=ROOT/"hw/soc/out/cdr-eight-drain-storage-source-controls";out.mkdir(parents=True,exist_ok=False)
    result=dict(status="FAIL_STORAGE_SOURCE_CONTROLS",source=os.environ.get("GITHUB_SHA"),source_controls_only=True,native_executed=False,native_acquisition=False,full_phy_accepted=False)
    primary=None
    try:
        m=source()
        result["frozen_original"]=frozen.controls()
        result["storage"]=storage_controls()
        result["candidate_publication"]=candidate_publication_controls()
        result["protected_files"]=len(m["protected_sha256"])
        result["status"]="PASS_STORAGE_SOURCE_CONTROLS_NOT_NATIVE_OR_ELECTRICAL_ACCEPTANCE"
    except BaseException as error:
        primary=error;result.update(error=repr(error),traceback=traceback.format_exc())
    finally:
        raw=(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
        (out/"result.json").write_bytes(raw);print(raw.decode(),end="",flush=True)
    if primary is not None:raise primary

if __name__=="__main__":main()
