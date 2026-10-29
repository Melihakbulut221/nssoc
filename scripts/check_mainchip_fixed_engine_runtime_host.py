#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted source-only checks of current control binding and failure-preserving publication."""
import argparse,ast,contextlib,copy,io,json,os,subprocess,tarfile,tempfile,traceback
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import cloud_mainchip_fixed_engine_runtime as h
import mainchip_fixed_engine_runtime_contract as c
ROOT=Path(__file__).resolve().parent.parent

def environment(run="771"):
    return dict(GITHUB_ACTIONS="true",RUNNER_ENVIRONMENT="github-hosted",RUNNER_OS="Linux",
      GITHUB_REPOSITORY=c.REPOSITORY,GITHUB_EVENT_NAME="workflow_dispatch",GITHUB_RUN_ATTEMPT="1",
      GITHUB_SHA="a"*40,GITHUB_RUN_ID=run,GITHUB_REF="refs/heads/"+c.BRANCH)

def reservation(ctx,assets=()):
    return dict(release_id=19,externally_reserved=True,creation_attempted=False,assets_overwritten=False,
      target_verified=True,tested_source=ctx["source"],tag="cloud-results-"+ctx["token"]+"-"+c.GROUP,
      existing_assets=list(assets))

def encoded(value):return (json.dumps(value,sort_keys=True,indent=2)+"\n").encode()

def source_records(root,ctx,runtime):
    expected_context=dict(source=ctx["source"],run_id=int(ctx["token"].split("-")[0]),attempt=1,
      source_controls_only=True,native_executed=False)
    host=dict(status="PASS_FIXED_ENGINE_RUNTIME_HOST_SOURCE_CONTROLS",current_context=expected_context,
      native_executed=False,runtime_qualified=False,physical_acceptance=False,
      publication=dict(count=7),source_records=dict(positive_count=1,refusal_count=13))
    originals={"runtime-probe-controls.json":encoded(runtime),"runtime-host-controls.json":encoded(host)}
    for name,raw in originals.items():(root/name).write_bytes(raw)
    result=h.control_evidence(root,ctx)
    assert result=={name:dict(bytes=len(raw),sha256=c.digest(raw))for name,raw in originals.items()}
    cases=[]
    mutations=[
      ("runtime-probe-controls.json",("current_context","source"),"b"*40,"current control context"),
      ("runtime-probe-controls.json",("current_context","run_id"),999,"current control context"),
      ("runtime-probe-controls.json",("current_context","attempt"),2,"current control context"),
      ("runtime-probe-controls.json",("native_executed",),True,"current controls native scope"),
      ("runtime-probe-controls.json",("status",),"FAIL","current runtime source controls"),
      ("runtime-probe-controls.json",("original_runtime_controls","refusal_count"),22,"original runtime lifecycle controls"),
      ("runtime-probe-controls.json",("producer_input_controls","refusal_count"),73,"current producer input controls"),
      ("runtime-host-controls.json",("current_context","source"),"b"*40,"current control context"),
      ("runtime-host-controls.json",("status",),"FAIL","current host controls"),
      ("runtime-host-controls.json",("publication","count"),6,"current host controls"),
      ("runtime-host-controls.json",("native_executed",),True,"current controls native scope")]
    for name,keys,bad,reason in mutations:
        value=c.decode(originals[name]);target=value
        for key in keys[:-1]:target=target[key]
        target[keys[-1]]=bad;(root/name).write_bytes(encoded(value));caught=None
        try:h.control_evidence(root,ctx)
        except (ValueError,AssertionError)as exc:
            assert reason in str(exc);caught=repr(exc)
        finally:(root/name).write_bytes(originals[name])
        assert caught;cases.append(dict(file=name,path=list(keys),refused=caught))
    name="runtime-host-controls.json";p=root/name
    for mode in ("missing","symlink"):
        p.unlink()
        if mode=="symlink":p.symlink_to("runtime-probe-controls.json")
        caught=None
        try:h.control_evidence(root,ctx)
        except (ValueError,AssertionError,FileNotFoundError)as exc:caught=repr(exc)
        finally:
            if p.is_symlink():p.unlink()
            p.write_bytes(originals[name])
        assert caught;cases.append(dict(file=name,mode=mode,refused=caught))
    assert len(cases)==13
    return dict(positive_count=1,refusal_count=len(cases),refusals=cases,
      synthetic_host_control_record=True,actual_runtime_control_record_used=True,native_executed=False)

def function(source,name):
    nodes=[n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef)and n.name==name]
    assert len(nodes)==1
    return ast.get_source_segment(source,nodes[0])

def derivation(root):
    original=c.secure_file(root,"scripts/cloud_mainchip_built_engine_runtime.py").read_text()
    repaired=c.secure_file(root,"scripts/cloud_mainchip_fixed_engine_runtime.py").read_text()
    build=c.secure_file(root,"scripts/mainchip_fixed_engine_build.py").read_text()
    unchanged=("owned_work","restore_input","publish_asset")
    assert all(function(original,n)==function(repaired,n)for n in unchanged)
    probe=function(original,"probe")
    substitutions=[
      ('c.require(m["native_probe_authorized"] is True,"native runtime probe not authorized")','c.authorize_native(m)'),
      ('schema="built-engine-runtime-host-v1"','schema="fixed-engine-runtime-host-v1"'),
      ('c.require(not proof["existing_assets"],"release not empty before native probe")','c.validate_reservation(proof,ctx,True)'),
      ('shutil.copyfile(ROOT/"runtime-probe-controls.json",out/"runtime-probe-controls.json")','report["current_source_controls"]=control_evidence(ROOT,ctx)\n        write(out/"current-source-controls.json",report["current_source_controls"])\n        for name in ("runtime-probe-controls.json","runtime-host-controls.json"):\n            shutil.copyfile(c.secure_file(ROOT,name),out/name)'),
      ('ROOT/"scripts/mainchip_built_engine_runtime_inner.py"','ROOT/"scripts/mainchip_fixed_engine_runtime_inner.py"')]
    for before,after in substitutions:
        assert probe.count(before)==1;probe=probe.replace(before,after)
    old_terminal="c.require(all(x[\"returncode\"]==0 and x[\"timed_out\"] is False for x in inner[\"commands\"]),\"native command failure\")"
    new_terminal="c.require(all(x[\"returncode\"]==0 and x[\"timed_out\"] is False for x in inner[\"commands\"]),\"native command failure\")\n        expected=c.expected_engine(ROOT)\n        c.runtime_match(expected[\"runtime\"],c.decode((out/\"runtime-observed.json\").read_bytes()))\n        c.require(fingerprint(work/\"runtime-dependencies.json\")==fingerprint(c.secure_file(ROOT,c.RUNTIME_SOURCE)),\"runtime expectation file changed\")"
    assert probe.count(old_terminal)==1;probe=probe.replace(old_terminal,new_terminal)
    assert probe==function(repaired,"probe")
    restore=function(original,"restore_engine")
    restore=restore.replace('"/jobs?per_page=100"','"/attempts/1/jobs?per_page=100"')
    restore=restore.replace('shutil.copyfile(c.secure_file(ROOT,c.PREFIX+"runtime-dependencies.json"),work/"runtime-dependencies.json")',
      'shutil.copyfile(c.secure_file(ROOT,c.RUNTIME_SOURCE),work/"runtime-dependencies.json")\n    shutil.copyfile(work/"runtime-dependencies.json",out/"runtime-dependencies.json")')
    assert restore==function(repaired,"restore_engine")
    publisher=function(build,"publish")
    start=publisher.index("        optional=(");end=publisher.index("        plan=c.direct_plan",start)
    publisher=publisher[:start]+"        optional=(\"host-result.json\",\"inner-result.json\",\"method.json\",\"runtime-probe-controls.json\",\n          \"runtime-host-controls.json\",\"api-identity-census.json\",\"release-reservation.json\",\n          \"container-initial.json\",\"container-terminal.json\",\"runtime-dependencies.json\",\n          \"runtime-observed.json\",\"engine-restoration.json\",\"input-restoration.json\",\n          \"engine-source-envelope.json\",\"current-source-controls.json\",\"publication-availability.json\")\n"+publisher[end:]
    publisher=publisher.replace("engine-evidence.tar.gz","runtime-probe-evidence.tar.gz").replace("FIXED_ENGINE_PUBLICATION_FALLBACK","FIXED_RUNTIME_PUBLICATION_FALLBACK")
    assert publisher==function(repaired,"publish")
    return dict(unchanged_functions=list(unchanged),probe_substitutions=len(substitutions)+1,
      original_probe_lifecycle_preserved=True,original_input94_restoration_unchanged=True,
      fixed_build_publisher_preserved_except_runtime_names=True,native_executed=False)

def publication_controls(root,base):
    cases=[]
    for index,mode in enumerate(("empty_terminal","missing_terminal","upload_failure","conflicting_asset","source_corruption","source_and_upload_failure","missing_asset_id")):
        env=environment(str(900+index));env["RUNNER_TEMP"]=str(base);ctx=c.context(env)
        capture=io.StringIO();uploads=[];assets=[];failure=OSError("synthetic upload failure")
        source_errors=[];real_method=c.method;changed=root/"scripts/mainchip_fixed_engine_runtime_contract.py";original=changed.read_bytes()
        def checked_method(path):
            try:return real_method(path)
            except BaseException as exc:source_errors.append(exc);raise
        with patch.dict(os.environ,env,clear=False),patch.object(h,"ROOT",root):
            work=h.owned_work(ctx,True);out=work/"out";out.mkdir()
            (out/"empty.stderr").write_bytes(b"");(out/"partial.stdout").write_bytes(b"complete partial stdout\n")
            if mode!="missing_terminal":
                (out/"host-result.json").write_bytes(b"")
                (out/"inner-result.json").write_bytes(b"malformed original native JSON")
            proof=reservation(ctx)
            tag=proof["tag"]
            def read(endpoint):
                if endpoint=="git/ref/tags/"+tag:return dict(ref="refs/tags/"+tag,object=dict(type="commit",sha=ctx["source"]))
                assert endpoint=="releases/tags/"+tag
                return dict(id=19,tag_name=tag,target_commitish=ctx["source"],draft=False,prerelease=True,assets=copy.deepcopy(assets))
            def upload(argv,**kwargs):
                assert argv[:3]==["gh","release","upload"];p=Path(argv[4]);raw=p.read_bytes()
                assert raw,"zero-byte direct upload"
                if mode in ("upload_failure","source_and_upload_failure"):raise failure
                uploads.append(p.name);item=dict(id=100+len(assets),name=p.name,size=len(raw),digest="sha256:"+c.digest(raw))
                if mode=="missing_asset_id":item.pop("id")
                assets.append(item)
                return SimpleNamespace(returncode=0)
            if mode=="conflicting_asset":
                assets.append(dict(id=1,name="inner-result.json",size=1,digest="sha256:"+"0"*64))
                proof["existing_assets"]=copy.deepcopy(assets)
            caught=None;caught_traceback=None
            if mode in ("source_corruption","source_and_upload_failure"):
                changed.unlink();changed.write_bytes(original+b"\n")
            try:
                with patch.object(c,"method",side_effect=checked_method),patch.object(h.reservation,"wait",return_value=proof),patch.object(h.reservation.release,"api",side_effect=read),patch.object(h.subprocess,"run",side_effect=upload),contextlib.redirect_stdout(capture):
                    try:result=h.publish()
                    except BaseException as exc:caught=exc;caught_traceback=traceback.format_exc()
            finally:
                if mode in ("source_corruption","source_and_upload_failure"):
                    changed.write_bytes(original)
            plan=c.decode((out/"direct-publication-plan.json").read_bytes())
            if mode=="upload_failure":assert caught is failure
            elif mode=="conflicting_asset":assert isinstance(caught,ValueError)and str(caught)=="existing asset conflict"
            elif mode=="missing_asset_id":assert isinstance(caught,KeyError)and caught.args==("id",)
            elif mode in ("source_corruption","source_and_upload_failure"):
                assert len(source_errors)==1 and caught is source_errors[0]
                availability=c.decode((out/"publication-availability.json").read_bytes())
                assert availability["source_integrity_validated"]is False and availability["native_accepted"]is False
                assert availability["source_integrity_error"]["error"]==repr(caught)
                if mode=="source_corruption":
                    saved=c.decode((out/"publication.json").read_bytes())
                    assert saved["status"]=="PASS_PERMANENT_FAILURE_EVIDENCE_ONLY"and saved["native_accepted"]is False
                else:
                    saved=c.decode((out/"publication-failure.json").read_bytes())
                    assert saved["source_error"]["error"]==repr(caught)and saved["publication_error"]["error"]==repr(failure)
            else:assert caught is None and result==0,(mode,repr(caught),caught_traceback,capture.getvalue())
            assert "host-result.json"not in uploads
            with tarfile.open(work/"runtime-probe-evidence.tar.gz","r:gz")as archive:
                assert archive.extractfile("empty.stderr").read()==b""
                assert archive.extractfile("partial.stdout").read()==b"complete partial stdout\n"
                if mode!="missing_terminal":assert archive.extractfile("host-result.json").read()==b""
            row=next(x for x in plan["files"]if x["name"]=="host-result.json")
            assert row["disposition"]==("absent"if mode=="missing_terminal"else"archive_only_empty")
            cases.append(dict(mode=mode,complete_empty_archive_member=True,original_terminal_bytes_unchanged=True,
              zero_byte_direct_upload=False,synthetic_cloud_transport=True,error=None if caught is None else repr(caught),
              caught_traceback=caught_traceback,missing_id_regression=mode=="missing_asset_id"))
    return dict(status="PASS_ACTUAL_FAILURE_AND_EMPTY_PUBLICATION_CONTROLS",cases=cases,count=len(cases))

def controls():
    ctx=c.context(os.environ);m=c.method(ROOT)
    c.require(m["source_controls_authorized"]is True,"source controls disabled")
    c.require(subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==ctx["source"],"current source checkout")
    runtime=c.decode(c.secure_file(ROOT,"runtime-probe-controls.json").read_bytes())
    source=derivation(ROOT)
    with tempfile.TemporaryDirectory()as temp:
        base=Path(temp);fixture=base/"source";fixture.mkdir()
        for name in [*m["protected"],c.METHOD]:
            p=fixture/name;p.parent.mkdir(parents=True,exist_ok=True);os.link(c.secure_file(ROOT,name),p)
        samples=base/"control-records";samples.mkdir()
        records=source_records(samples,ctx,runtime)
        publication=publication_controls(fixture,base)
    assert publication["count"]==7
    c.method(ROOT)
    return dict(status="PASS_FIXED_ENGINE_RUNTIME_HOST_SOURCE_CONTROLS",
      current_context=dict(source=ctx["source"],run_id=int(ctx["token"].split("-")[0]),attempt=1,
        source_controls_only=True,native_executed=False),
      publication=publication,source_records=records,derivation=source,
      native_executed=False,runtime_qualified=False,physical_acceptance=False)

def main():
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path);args=p.parse_args()
    report=controls();raw=json.dumps(report,sort_keys=True,indent=2)+"\n"
    if args.output:args.output.write_text(raw)
    else:print(raw,end="")
    return 0
if __name__=="__main__":raise SystemExit(main())
