#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted source-only controls. All subprocess/DB/inner-main I/O is synthetic."""
import argparse
import contextlib
import copy
import io
import itertools
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
import mainchip_fixed_engine_runtime_contract as c
import mainchip_fixed_engine_runtime_inner as inner
import check_mainchip_fixed_engine_runtime_admission as input_checker
import check_mainchip_built_engine_runtime as original_checker

ROOT=Path(__file__).resolve().parent.parent
OLD_INNER="scripts/mainchip_built_engine_runtime_inner.py"
NEW_INNER="scripts/mainchip_fixed_engine_runtime_inner.py"
NATIVE="scripts/mainchip_built_engine_runtime_native.py"
OLD_INNER_SHA="eda9ff604f07c417cebe0cfefac5352d02ea1d52350c91b643aab3a769d53a40"
NATIVE_SHA="2d2fdbe766a331b5ba574b949cf8a74e88213dc0b3468317db6c1550d26130cd"
INNER_EDITS=(
    ("import mainchip_built_engine_runtime_contract as c","import mainchip_fixed_engine_runtime_contract as c"),
    ("from mainchip_built_engine_runtime_contract import MEMORY,PIDS,require","from mainchip_fixed_engine_runtime_contract import MEMORY,PIDS,require"),
    ('schema="built-engine-runtime-inner-v1"','schema="fixed-engine-runtime-inner-v1"'),
    ('        c.method(WORK/"source")\n','        c.authorize_native(c.method(WORK/"source"))\n'),
)


def derivation(old,new,native):
    assert c.digest(old)==OLD_INNER_SHA,"frozen inner hash"
    assert c.digest(native)==NATIVE_SHA,"unchanged native lifecycle/census body"
    value=old.decode()
    for before,after in INNER_EDITS:
        assert value.count(before)==1 and after not in value,("unique inner edit",before)
        value=value.replace(before,after,1)
    assert value.encode()==new,"exact derived inner source"
    for before,after in reversed(INNER_EDITS):
        assert value.count(after)==1
        value=value.replace(after,before,1)
    assert value.encode()==old,"byte-exact inner reversal"
    return dict(old_sha256=c.digest(old),new_sha256=c.digest(new),native_sha256=c.digest(native),
                exact_reversible_edits=4,numerical_census_body_unchanged=True)


def blank_report():
    return dict(schema="fixed-engine-runtime-inner-v1",status="IN_PROGRESS",
                physical_acceptance=False,observer_equivalence_qualified=False,
                native_routing_executed=False,terminal_errors=[],commands=[])


def run_controls():
    results=[]
    for mode in ("complete","body_failure","timeout","progress_failure","body_and_progress","cleanup_failure"):
        with tempfile.TemporaryDirectory()as temp:
            out=Path(temp);report=blank_report();events=[]
            body=RuntimeError("actual run body sentinel");progress=OSError("actual progress sentinel")
            class Process:
                pid=12345
                returncode=0 if mode in ("complete","progress_failure")else None
                waits=0
                def poll(self):return self.returncode
                def wait(self,timeout):
                    self.waits+=1;events.append("wait")
                    if mode in ("body_failure","body_and_progress")and self.waits==1:raise body
                    if self.returncode is None:raise subprocess.TimeoutExpired("synthetic",timeout)
                    return self.returncode
            proc=Process()
            def killpg(pid,sig):
                assert pid==proc.pid;events.append(sig.name)
                if mode=="cleanup_failure"and sig==signal.SIGTERM:raise OSError("stop sentinel")
                proc.returncode=-int(sig)
            def write(name,value):
                if mode in ("progress_failure","body_and_progress"):raise progress
                c.atomic_record(out/name,value)
            clock=iter(itertools.count())
            caught=None
            with patch.multiple(inner,OUT=out,report=report,DEADLINE=100,
                                time=SimpleNamespace(monotonic=lambda:next(clock)),
                                cgroup=lambda:dict(synthetic=True),write=write):
                try:inner.run("fixture",["synthetic-child"],timeout=1 if mode in ("timeout","cleanup_failure")else 100,
                              popen=lambda *a,**k:proc,killpg=killpg)
                except BaseException as exc:caught=exc
            if mode in ("body_failure","body_and_progress"):assert caught is body
            elif mode=="progress_failure":assert caught is progress
            elif mode in ("timeout","cleanup_failure"):assert type(caught)is TimeoutError
            else:assert caught is None
            actions=[x["action"]for x in report["terminal_actions"]]
            assert actions==["child-terminate","child-wait-after-terminate","child-kill-if-live","child-final-wait"]
            assert (out/"fixture.stdout").is_file()and(out/"fixture.stderr").is_file()
            if mode=="cleanup_failure":
                assert "SIGKILL"in events and report["terminal_errors"]
                assert [x["completed"]for x in report["terminal_actions"]]==[False,False,True,True]
            if mode=="body_and_progress":
                assert any(x["action"]=="inner-progress"for x in report["terminal_errors"])
            results.append(dict(case=mode,synthetic_process_and_cgroup=True,terminal_actions=actions,
                                primary=None if caught is None else type(caught).__name__,
                                stdout_bytes=(out/"fixture.stdout").stat().st_size,
                                stderr_bytes=(out/"fixture.stderr").stat().st_size))
    return results


def main_controls(method):
    results=[]
    for mode in ("complete","body_failure","census_failure","native_disabled",
                 "source_final_failure","save_failure","body_and_save"):
        with tempfile.TemporaryDirectory()as temp:
            work=Path(temp);out=work/"out";out.mkdir()
            report=blank_report();commands=[];method_calls=[]
            body=RuntimeError("main body sentinel");save=OSError("atomic result replace sentinel")
            source_error=ValueError("source changed sentinel")
            enabled=copy.deepcopy(method);enabled.update(source_controls_authorized=True,
                native_probe_authorized=True,controller_ready=True)
            if mode=="native_disabled":enabled.update(native_probe_authorized=False,controller_ready=False)
            def method_read(root):
                assert Path(root)==work/"source";method_calls.append(str(root))
                if mode=="source_final_failure"and len(method_calls)>1:raise source_error
                return enabled
            def fingerprint(path):
                return c.ENGINE if str(path).endswith("/engine/openroad")else c.INPUT
            def group():
                return {"memory.max":str(c.MEMORY),"memory.swap.max":"0","pids.max":str(c.PIDS),
                        "memory.events":dict(oom=0,oom_kill=0,oom_group_kill=0),"cpu.max":"200000 100000"}
            def run(label,argv,timeout):
                commands.append((label,argv,timeout))
                if mode in ("body_failure","body_and_save")and label=="version":raise body
                (out/(label+".stdout")).write_text("PASS_COMPLETE_OPENROAD_TCL_INTERFACES"if label=="tcl-smoke"else"")
                (out/(label+".stderr")).write_bytes(b"")
                if label=="actual-chip-census":
                    value=dict(status="PASS_ACTUAL_DATABASE_LIFECYCLE_AND_FULL_READ_ONLY_CENSUS",
                        database_created=True,database_read=True,database_destroyed=True,
                        complete_census=True,terminal_errors=[])
                    if mode=="census_failure":value["complete_census"]=False
                    c.atomic_record(out/"api-identity-census.json",value)
            original_replace=c.core.os.replace if hasattr(c.core,"os")else os.replace
            def replace(src,dst):
                if mode in ("save_failure","body_and_save")and Path(dst)==out/"inner-result.json":raise save
                return original_replace(src,dst)
            caught=None;returncode=None;printed=io.StringIO()
            with contextlib.ExitStack()as stack:
                stack.enter_context(patch.multiple(inner,WORK=work,OUT=out,report=report,
                    START=0,run=run,fingerprint=fingerprint,cgroup=group,
                    dependencies=lambda:dict(count=104,synthetic_library_IO=True)))
                stack.enter_context(patch.object(c,"method",side_effect=method_read))
                stack.enter_context(patch.dict(os.environ,{},clear=True))
                stack.enter_context(patch("os.replace",side_effect=replace))
                stack.enter_context(contextlib.redirect_stdout(printed))
                try:returncode=inner.main()
                except BaseException as exc:caught=exc
            assert len(method_calls)==2
            labels=[x[0]for x in commands]
            if mode=="native_disabled":assert labels==[]
            elif mode in ("body_failure","body_and_save"):assert labels==["version"]
            else:
                assert labels==["version","ldd","tcl-smoke","actual-chip-census"]
                assert commands[-1][1][-1]=="/work/source/scripts/mainchip_built_engine_runtime_native.py"
                assert commands[-1][2]==1200
            if mode in ("body_failure","body_and_save"):assert caught is body
            elif mode=="save_failure":assert caught is save
            elif mode in ("census_failure","native_disabled"):assert type(caught)is ValueError
            else:assert caught is None
            if mode in ("save_failure","body_and_save"):
                fragments=list(out.glob("inner-result.json.*.tmp"))
                assert not(out/"inner-result.json").exists()and len(fragments)==1 and fragments[0].is_file()
                rows=[line for line in printed.getvalue().splitlines()if line.startswith("ENGINE_BUILD_TERMINAL_FALLBACK ")]
                assert len(rows)==1
                fallback=json.loads(rows[0].split(" ",1)[1])
                saved=fallback["complete_unsaved_record"]
                assert fallback["acceptance"]is False
                assert saved["available_outputs_after_save_failure"]==c.core.inventory(out)
                assert fragments[0].name in saved["available_outputs_after_save_failure"]
            else:saved=c.decode((out/"inner-result.json").read_bytes())
            if mode=="complete":assert returncode==0 and saved["status"]=="PASS_BUILT_ELF_RUNTIME_AND_ACTUAL_CHIP_READ_ONLY_CENSUS"
            else:assert saved["status"]=="FAIL_BUILT_ELF_RUNTIME_OR_NATIVE_CENSUS"
            assert saved["physical_acceptance"]is False and saved["native_routing_executed"]is False
            actions=[x["action"]for x in saved["terminal_actions"]]
            assert all(x in actions for x in ("ELF-unchanged","input-unchanged","source-unchanged"))
            if mode!="native_disabled":assert "terminal-cgroup"in actions
            if mode=="source_final_failure":assert returncode==1 and any(x["action"]=="source-unchanged"for x in saved["terminal_errors"])
            results.append(dict(case=mode,synthetic_native_library_transport=True,commands=labels,
                terminal_actions=actions,status=saved["status"],
                primary_identity_checked=mode in ("body_failure","body_and_save","save_failure"),
                actual_native_invocation=False))
    return results


def controls(method):
    positives=[];refusals=[]
    def reject(name,fn,reason):
        try:fn()
        except (ValueError,AssertionError,KeyError,TypeError)as exc:
            assert reason in str(exc),(name,repr(exc),reason)
            refusals.append(dict(name=name,error=repr(exc)))
        else:raise AssertionError("unexpected acceptance: "+name)
    prior=c.admission.methods(ROOT)
    env=dict(GITHUB_ACTIONS="true",RUNNER_OS="Linux",RUNNER_ENVIRONMENT="github-hosted",
        GITHUB_REPOSITORY=c.REPOSITORY,GITHUB_EVENT_NAME="workflow_dispatch",
        GITHUB_RUN_ID="123",GITHUB_RUN_ATTEMPT="1",GITHUB_SHA="a"*40,GITHUB_REF="refs/heads/"+c.BRANCH)
    ctx=c.context(env);assert ctx==dict(name="nssoc-witness-build-123-1",source="a"*40,token="123-1")
    positives.append("exact_current_hosted_context")
    for key,value,reason in (
        ("GITHUB_ACTIONS","false","hosted"),("RUNNER_OS","Windows","hosted"),
        ("RUNNER_ENVIRONMENT","self-hosted","hosted"),("GITHUB_REPOSITORY","foreign/project","repository"),
        ("GITHUB_EVENT_NAME","push","manual"),("GITHUB_RUN_ATTEMPT","2","no retry"),
        ("GITHUB_RUN_ID","0","run identity"),("GITHUB_SHA","main","source identity"),
        ("GITHUB_REF","refs/heads/"+c.admission.BRANCH,"runtime probe branch")):
        reject("context "+key,lambda key=key,value=value:c.context({**env,key:value}),reason)
    baselines={}
    for enabled in (False,True):
        baseline=copy.deepcopy(method);baseline.update(source_controls_authorized=True,
            native_probe_authorized=enabled,controller_ready=enabled)
        c.validate_method(baseline,prior);baselines[enabled]=baseline
        for key in ("source_controls_authorized","native_probe_authorized","controller_ready"):
            bad=copy.deepcopy(baseline);bad[key]=int(bad[key])
            reject("typed authority "+key+"/"+str(enabled),lambda bad=bad:c.validate_method(bad,prior),"typed runtime authority")
    c.authorize_native(baselines[True])
    reject("disabled native gate",lambda:c.authorize_native(baselines[False]),"not authorized")
    disabled=copy.deepcopy(baselines[False]);disabled["source_controls_authorized"]=False
    c.validate_method(disabled,prior)
    positives.append("both_native_modes_and_disabled_source_typed_method")
    for key in c.AUTH_FALSE:
        bad=copy.deepcopy(baselines[True]);bad[key]=True
        reject("forbidden "+key,lambda bad=bad:c.validate_method(bad,prior),"read-only runtime scope")
    for key in ("qualified_engine","qualified_routing_engine"):
        bad=copy.deepcopy(baselines[True]);bad[key]={"sha256":c.ENGINE["sha256"]}
        reject("qualification transfer "+key,lambda bad=bad:c.validate_method(bad,prior),"no runtime or routing qualification")
    mutations=(
        ("image",lambda x:x.update(image="other"),"runtime limits/image"),
        ("ELF",lambda x:x["engine"].update(sha256="0"*64),"immutable native inputs"),
        ("input",lambda x:x["input"].update(sha256="0"*64),"immutable native inputs"),
        ("prior method",lambda x:x.update(prior_method_sha256="0"*64),"prior method binding"),
        ("inherited count",lambda x:x.update(inherited_protected_count=924),"inherited 925"),
        ("missing inherited pin",lambda x:x["protected"].pop(next(iter(prior["protected"]))),"inherited source protection"),
        ("changed inherited pin",lambda x:x["protected"].update({next(iter(prior["protected"])):"0"*64}),"inherited source protection"),
        ("missing proof pin",lambda x:x["protected"].pop(next(iter(c.INPUT_PROOF))),"protected full input-controls"),
        ("missing new pin",lambda x:x["protected"].pop(c.NEW_FILES[0]),"required new runtime source"),
        ("old control source",lambda x:x["producer_input_controls"].update(source="0"*40),"qualified input source-controls"),
        ("controller mismatch",lambda x:x.update(controller_ready=False),"native/controller agreement"),
        ("native without source",lambda x:x.update(source_controls_authorized=False),"native requires source"),
    )
    for label,change,reason in mutations:
        bad=copy.deepcopy(baselines[True]);change(bad)
        reject(label,lambda bad=bad:c.validate_method(bad,prior),reason)
    proof=c.input_controls(ROOT);assert proof["complete_proof_files"]==13
    positives.append("actual_complete_passed_input_controls_proof")
    reservation=dict(release_id=123,externally_reserved=True,creation_attempted=False,
        assets_overwritten=False,target_verified=True,tested_source=ctx["source"],
        tag="cloud-results-"+ctx["token"]+"-"+c.GROUP,existing_assets=[])
    c.validate_reservation(reservation,ctx,True)
    for key,value,reason in (
        ("tested_source","0"*40,"new source/tag"),("tag","cloud-results-123-1-"+c.qualified_build.GROUP,"new source/tag"),
        ("existing_assets",[{"id":1}],"empty before"),("release_id",0,"reserved-only"),
        ("creation_attempted",True,"reserved-only"),("externally_reserved",False,"reserved-only")):
        bad=copy.deepcopy(reservation);bad[key]=value
        reject("reservation "+key,lambda bad=bad:c.validate_reservation(bad,ctx,True),reason)
    with tempfile.TemporaryDirectory()as temp:
        path=next(p for p in c.INPUT_PROOF if p.endswith("/controls/result.json"))
        original=c.secure_file
        damaged=Path(temp)/"bad.json";damaged.write_bytes(original(ROOT,path).read_bytes()+b" ")
        with patch.object(c,"secure_file",side_effect=lambda root,name:damaged if name==path else original(root,name)):
            reject("actual historical proof byte corruption",lambda:c.input_controls(ROOT),"input-controls proof bytes")
    old=c.secure_file(ROOT,OLD_INNER).read_bytes();new=c.secure_file(ROOT,NEW_INNER).read_bytes()
    native=c.secure_file(ROOT,NATIVE).read_bytes();derived=derivation(old,new,native)
    for label,changed in (
        ("missing native authority",new.replace(b"c.authorize_native(c.method",b"(c.method",1)),
        ("wrong native script",new.replace(b"mainchip_built_engine_runtime_native.py",b"wrong_native.py")),
        ("changed original deadline",new.replace(b'c.LIMITS["probe_seconds"]',b"1"))):
        reject(label,lambda changed=changed:derivation(old,changed,native),"exact derived inner source")
    assert c.expected_engine is c.admission.expected_engine and c.engine_envelope is c.admission.engine_envelope
    assert c.engine_extract is c.admission.engine_extract and c.runtime_match is c.admission.runtime_match
    assert c.LIMITS is c.frozen.LIMITS and c.direct_plan is c.qualified_build.direct_plan
    positives.append("exact_inner_derivation_and_qualified_helper_identity")
    producer=input_checker.controls()
    assert producer["status"]=="PASS_FIXED_ENGINE_RUNTIME_INPUT_SOURCE_CONTROLS"and producer["positive_count"]==5
    assert producer["refusal_count"]==74 and producer["synthetic_archive"]["refusal_count"]==6
    assert producer["new_ELF_executed"]is False
    printed=io.StringIO()
    with contextlib.redirect_stdout(printed):original_checker.main()
    original=json.loads(printed.getvalue())
    assert original["status"]=="PASS_BUILT_ENGINE_RUNTIME_SOURCE_CONTROLS"
    assert(original["positive_count"],original["refusal_count"],original["lifecycle_count"])==(4,23,6)
    assert original["native_objects_executed"]is False
    run_cases=run_controls();main_cases=main_controls(method)
    assert len(positives)==4 and len(refusals)==48 and len(run_cases)==6 and len(main_cases)==7
    return dict(status="PASS_FIXED_ENGINE_RUNTIME_SOURCE_CONTROLS",
        positive_count=len(positives),positive=positives,refusal_count=len(refusals),refusals=refusals,
        process_lifecycle_count=len(run_cases),process_lifecycle=run_cases,
        inner_main_lifecycle_count=len(main_cases),inner_main_lifecycle=main_cases,
        producer_input_controls=producer,original_runtime_controls=original,
        input_controls_proof=proof,derivation=derived,native_executed=False,
        actual_native_archive_restored=False,physical_acceptance=False,runtime_qualified=False,
        source_io_and_synthetic_controls_only=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path);args=parser.parse_args()
    ctx=c.context(os.environ);method=c.method(ROOT)
    c.require(method["source_controls_authorized"]is True,"source controls not authorized")
    result=controls(method)
    result["current_context"]=dict(source=ctx["source"],run_id=int(os.environ["GITHUB_RUN_ID"]),
        attempt=1,source_controls_only=True,native_executed=False)
    raw=json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n"
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(raw)
    else:print(raw,end="")
    return 0
if __name__=="__main__":raise SystemExit(main())
