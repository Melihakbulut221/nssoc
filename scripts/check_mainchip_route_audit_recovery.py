#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted synthetic transport/native-I/O controls; no engine or route launch."""
import argparse
from contextlib import ExitStack,redirect_stdout
import copy
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
import mainchip_route_audit_recovery_contract as a
import mainchip_route_audit_recovery_restore as r
import cloud_mainchip_route_audit_recovery as host
import mainchip_route_recovery_evidence as e
import mainchip_built_engine_route_tail_handoff as h
import mainchip_built_engine_route_tail_contract as c
import mainchip_witness_engine_build as build


def demand(ok,reason):
    if not ok:raise AssertionError(reason)


def env_for(mode,root):
    return dict(GITHUB_ACTIONS="true",RUNNER_OS="Linux",GITHUB_REPOSITORY=c.REPOSITORY,
      GITHUB_EVENT_NAME="workflow_dispatch",GITHUB_REF="refs/heads/"+a.BRANCH,GITHUB_RUN_ATTEMPT="1",
      GITHUB_SHA=os.environ["GITHUB_SHA"],GITHUB_RUN_ID=os.environ["GITHUB_RUN_ID"],NSSOC_RECOVERY_MODE=mode,RUNNER_TEMP=str(root))


def refusal(call,reason,frame,kind=ValueError):
    try:call()
    except BaseException as exc:
        codes=[];tb=exc.__traceback__
        while tb:codes.append(tb.tb_frame.f_code);tb=tb.tb_next
        demand(type(exc)is kind and exc.args==(reason,)and frame in codes,
          ("wrong refusal",type(exc).__name__,exc.args,reason,[x.co_name for x in codes]))
        return dict(reason=reason,actual_function=frame.co_name)
    raise AssertionError("accepted negative")


def context_controls():
    result=[]
    with tempfile.TemporaryDirectory()as tmp:
        env=env_for("off",Path(tmp));ctx=a.context(env);demand(a.validate_context(ctx)==ctx,"valid context")
        for key,value,reason in (
          ("GITHUB_SHA",e.SOURCE,"historical and current execution must differ"),
          ("GITHUB_RUN_ID",str(e.RUN),"historical and current execution must differ"),
          ("GITHUB_RUN_ATTEMPT","2","recovery branch/first attempt"),
          ("NSSOC_RECOVERY_MODE","route","recovery mode"),
          ("GITHUB_EVENT_NAME","push","manual repository identity")):
            changed=dict(env);changed[key]=value
            result.append(refusal(lambda:a.context(changed),reason,a.context.__code__))
        changed=dict(ctx);changed["attempt"]=True
        result.append(refusal(lambda:a.validate_context(changed),"typed new host context",a.validate_context.__code__))
    return dict(positive=1,refusals=result)


def read_fixture(mode,data,jobs):
    d=data["cases"][mode];case=e.CASES[mode]
    tag=d["release-snapshot.json"]["tag_name"]
    values={"actions/runs/"+str(e.RUN):d["run-snapshot.json"],
      "actions/runs/"+str(e.RUN)+"/attempts/1/jobs?per_page=100":jobs,
      "releases/"+str(case["release"]):d["release-snapshot.json"],
      "git/ref/tags/"+tag:d["tag.json"]}
    def read(endpoint):
        demand(endpoint in values,("unexpected cloud read",endpoint));return copy.deepcopy(values[endpoint])
    return read


def restore_case(mode,data,jobs,fault=None):
    """Real cloned restore body; only cloud/native byte transport/hash/extract are doubles.

    Complete authentic maps and all old source files are real. Native members are
    explicit tiny markers; their cryptographic receipts are a simulated I/O seam.
    This qualifies call/context/refusal flow, never archive bytes or restoration.
    """
    saved=e.expected_case(mode);events=[];sentinel=OSError("synthetic "+str(fault))
    with tempfile.TemporaryDirectory(prefix="audit-restore-control-")as tmp:
        work=Path(tmp)/"work";out=work/"out";out.mkdir(parents=True)
        env=env_for(mode,Path(tmp));ctx=a.context(env);read=read_fixture(mode,data,jobs)
        assets={x["name"]:x for x in data["cases"][mode]["release-snapshot.json"]["assets"]}
        registered={};actual_fp=build.fingerprint;marker=b"EXPLICIT_SYNTHETIC_NATIVE_TRANSPORT\n"
        def put(path,raw,receipt=None):
            path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
            if receipt is not None:registered[path]=(raw,receipt)
        def fingerprint(path):
            path=Path(path)
            if path in registered:
                raw,expected=registered[path];demand(path.read_bytes()==raw,"synthetic payload modified");return expected
            if path==work/"route-transport/route-outer.tar.gz":
                demand(path.read_bytes()==marker*len(saved["outer_archive_manifest"]["parts"]),"joined transport ordering")
                return saved["outer_archive_manifest"]["archive"]
            if path.is_relative_to(work):
                relative=path.relative_to(work).as_posix()
                if relative in saved["canonical_projection"]:
                    prior=work/"route-restored"/relative
                    demand(path.read_bytes()==prior.read_bytes(),"copied native projection differs")
                    return saved["canonical_projection"][relative]
            return actual_fp(path)
        def fetch(url,digest,path):
            path=Path(path);events.append("fetch:"+path.name);asset=assets[path.name]
            demand(url==asset["browser_download_url"]and digest==asset["digest"][7:],"selected asset identity")
            if fault=="transport"and path.name.startswith("route-tail-evidence"):raise sentinel
            if path.parent.name=="records":
                row=saved["records"][path.name];raw=(a.ROOT/row["repository_path"]).read_bytes()
                demand(e.record(raw)=={k:row[k]for k in ("bytes","sha256")},"actual direct record")
                put(path,raw)
            else:put(path,marker,dict(bytes=asset["size"],sha256=digest))
        def extract(stream,dest,expected,selected,limit):
            which="outer"if Path(dest).name=="outer"else"nested";events.append("extract:"+which)
            demand(expected==(saved["outer_expected_files"]if which=="outer"else saved["handoff_inventory"]["files"]),
              "complete authentic extraction map")
            demand(tuple(expected)==selected and limit==c.LIMITS["archive_expanded_limit"],"complete bounded extraction request")
            if fault==which:raise sentinel
            dest=Path(dest);dest.mkdir()
            for name,receipt in expected.items():
                p=dest/name;short=name.removeprefix("out/")
                if which=="nested"and name.startswith("tail-source/"):
                    raw=(a.ROOT/name[len("tail-source/"):]).read_bytes()
                    demand(e.record(raw)==receipt,"exact original source in synthetic extraction")
                elif (which=="outer"or name.startswith("out/"))and short in saved["records"]:
                    raw=(a.ROOT/saved["records"][short]["repository_path"]).read_bytes()
                elif name=="out/frozen-prefix-inventory.json":raw=(a.ROOT/(c.PREFIX+".frozen-prefix-inventory.json")).read_bytes()
                else:raw=marker+name.encode()
                put(p,raw,receipt)
            return dict(all_files=expected,all_regular_members_verified=True,
              unpacked_bytes=sum(x["bytes"]for x in expected.values()),synthetic_native_IO=True)
        def frozen(base,inv):
            for name,row in inv["files"].items():demand(fingerprint(Path(base)/name)==row,"synthetic complete native projection")
            return dict(files=len(inv["files"]),bytes=sum(x["bytes"]for x in inv["files"].values()))
        proxy=SimpleNamespace(**vars(c));proxy.engine_extract=extract;proxy.frozen_unchanged=frozen
        with ExitStack()as stack:
            stack.enter_context(patch.object(h,"c",proxy));stack.enter_context(patch.object(h,"fingerprint",side_effect=fingerprint))
            stack.enter_context(patch.object(r,"c",proxy))
            before=dict(os.environ);caught=None
            try:value=r.restore(work,out,a.ROOT,ctx,env,read=read,fetch=fetch)
            except BaseException as exc:caught=exc
            demand(dict(os.environ)==before,"restore restamped process environment")
        demand((out/"route-source-envelope.json").is_file(),"original failure envelope not durable before transport")
        if fault:
            demand(caught is sentinel,"restore masked transport/extract primary")
        else:
            if caught is not None:raise caught
            demand(value["source"]==e.SOURCE and value["run_id"]==e.RUN and value["new_host_context"]==ctx,
              "old/new restored contexts")
            demand(value["original_route_job_conclusion"]=="failure"and value["original_audit_jobs_conclusion"]=="skipped",
              "changed original outcomes")
            demand(c.decode((work/"route-projection.json").read_bytes())==dict(files=saved["canonical_projection"]),"full projection")
            for p,digest in data["old_method"]["protected"].items():
                demand(e.sha(work/"tail-source"/p)==digest,"original projected source bytes changed")
            demand(e.sha(work/"tail-source"/e.METHOD)==e.METHOD_SHA,"original execution method changed")
            bad=dict(saved["old_audit_context"],source=ctx["source"])
            refusal(lambda:r.historical_live(read,bad,{"GITHUB_RUN_ID":str(e.RUN)},ctx),
              "exact isolated historical restore context",r.historical_live.__code__)
        return dict(mode=mode,fault=fault,events=events,same_exception=fault is not None,
          full_outer=len(saved["outer_expected_files"]),full_nested=len(saved["handoff_inventory"]["files"]),
          actual_original_source_objects=687,synthetic_native_byte_IO=True)


def lifecycle_case(kind,data):
    """Actual cloned old probe and real create/cleanup/final writer; Docker/native I/O doubles."""
    saved=e.expected_case("off");primary=RuntimeError("body transport sentinel");stop=OSError("owned stop sentinel")
    progress=OSError("create progress sentinel");save=OSError("terminal replace sentinel")
    events=[];state={"created":False,"removed":False,"running":False,"last":None}
    with tempfile.TemporaryDirectory(prefix="audit-host-control-")as tmp:
        env=env_for("off",Path(tmp));ctx=a.context(env);work=Path(tmp)/(a.group("off")+"-"+ctx["token"])
        def restored(w,out,root,current,current_env):
            a.validate_context(current);demand(current==ctx and a.context(current_env)==ctx,"real current restore context")
            c.atomic_record(out/"recovery-host-context.json",ctx)
            if kind=="restore_failure":raise primary
            for p in [*data["old_method"]["protected"],e.METHOD]:
                path=w/"tail-source"/p;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a.ROOT/p,path)
            (w/"native-fixture").write_bytes(b"synthetic lifecycle only")
            inv=dict(files={"native-fixture":build.fingerprint(w/"native-fixture")})
            c.atomic_record(w/"frozen-manifest.json",inv);c.atomic_record(w/"route-projection.json",inv)
            return dict(synthetic_native_IO=True)
        info=copy.deepcopy(data["cases"]["off"]["host-result.json"]["container_terminal"])
        info["Name"]="/"+ctx["name"];info["Config"]["Labels"].update({"nssoc.build.source":ctx["source"],"nssoc.build.token":ctx["token"]})
        for mount in info["Mounts"]:
            if mount["Type"]=="bind":mount["Source"]=str(work)
        identity=info["Id"]
        def inspection():
            value=copy.deepcopy(info);value["State"].update(Running=state["running"],Pid=321 if state["running"]else 0,
              OOMKilled=False,ExitCode=0,Error="")
            return value
        def terminal_native():
            inner=dict(stage="audit",status="PASS_BUILT_ELF_ACTUAL_AUDIT_STAGE",terminal_errors=[],
              commands=[dict(returncode=0,timed_out=False)])
            lineage=dict(source=e.SOURCE,run_id=e.RUN,mode="off",authenticated_complete_route=True,
              original_run_conclusion="failure",original_route_job_conclusion="failure",original_audit_jobs_conclusion="skipped",
              original_audits_succeeded=False,future_audits_are_new_execution=True,new_host_context=ctx)
            case=dict(saved["old_audit_context"],status="PASS_COMPLETE_ROUTE_TAIL_DIAGNOSTIC",terminal_errors=[],
              route_lineage=lineage,commands=[dict(label=p,requested_timeout_seconds=1200,returncode=0,supervision_failure=None)for p in c.PHASES[1:]],
              route_command=data["cases"]["off"]["case-result.json"]["commands"][0],
              physical_acceptance=False,observer_equivalence_qualified=False,timing_accepted=False,full_phy_accepted=False)
            c.atomic_record(work/"out/inner-result.json",inner);c.atomic_record(work/"out/case-result.json",case)
        def docker(argv,stdout,stderr,timeout):
            demand(argv[0]=="docker","no non-Docker execution in lifecycle fixture");verb=argv[1];state["last"]=verb;events.append(verb)
            raw=b""
            if verb=="pull":raw=b"synthetic immutable image available\n"
            elif verb=="image":raw=json.dumps([dict(Id=c.IMAGE_ID,Architecture="amd64",Os="linux",RepoDigests=[c.IMAGE])]).encode()
            elif verb=="container":raw=(ctx["name"]+"\n").encode()if state["created"]and not state["removed"]else b""
            elif verb=="create":
                demand(argv==c.create_argv(ctx,work,os.getuid(),os.getgid()),"actual owned create argv")
                state["created"]=True;raw=identity.encode()
            elif verb=="start":
                state["running"]=True
                if kind in ("body_stop_failure","body_save_failure"):raise primary
                terminal_native()
                if kind!="stop_failure":state["running"]=False
            elif verb=="stop":raise stop
            elif verb=="kill":state["running"]=False
            elif verb=="rm":state["removed"]=True
            else:raise AssertionError(("unexpected Docker operation",argv))
            stdout.write(raw);return SimpleNamespace(returncode=0)
        def command(report,out,label,argv,timeout=120):
            return build.execute_command(report,out,label,argv,timeout,runner=docker)
        actual_check_output=subprocess.check_output
        def inspect_cmd(argv,timeout=None,cwd=None,text=False):
            if argv==["git","rev-parse","HEAD"]:
                demand(cwd==a.ROOT and text is True,"real checkout context call")
                return actual_check_output(argv,cwd=cwd,text=text)
            demand(argv[:2]==["docker","inspect"]and argv[2]in (identity,ctx["name"]),"owned inspect only")
            return json.dumps([inspection()]).encode()
        actual_replace=os.replace
        def replace(src,dst):
            name=Path(dst).name
            if kind=="create_progress_failure"and name=="host-progress.json"and state["last"]=="create":raise progress
            if kind in ("terminal_save_failure","body_save_failure")and name=="host-result.json":raise save
            return actual_replace(src,dst)
        capture=io.StringIO();caught=None
        with ExitStack()as stack:
            stack.enter_context(patch.dict(os.environ,env,clear=True))
            stack.enter_context(patch.object(r,"restore",side_effect=restored))
            stack.enter_context(patch.object(host.reservation,"wait",return_value={"existing_assets":[],"release_id":1}))
            stack.enter_context(patch.object(subprocess,"check_output",side_effect=inspect_cmd))
            stack.enter_context(patch.object(os,"replace",side_effect=replace))
            stack.enter_context(redirect_stdout(capture))
            call=host.cloned_probe(ctx,saved);call.__globals__["execute_command"]=command
            try:code=call()
            except BaseException as exc:caught=exc
        if kind in ("restore_failure","body_stop_failure","body_save_failure"):demand(caught is primary,"lost lifecycle primary")
        elif kind=="create_progress_failure":demand(caught is progress,"lost create progress primary")
        elif kind=="terminal_save_failure":demand(caught is save,"lost real atomic save primary")
        else:demand(caught is None,"unexpected lifecycle exception")
        if kind in ("terminal_save_failure","body_save_failure"):
            line=next(x for x in capture.getvalue().splitlines()if x.startswith("ENGINE_BUILD_TERMINAL_FALLBACK "))
            report=json.loads(line.split(" ",1)[1])["complete_unsaved_record"]
            demand(any(x.startswith("host-result.json.")and x.endswith(".tmp")for x in report["available_outputs_after_save_failure"]),"actual atomic fragment omitted")
        else:report=c.decode((work/"out/host-result.json").read_bytes())
        demand(report["new_host_context"]==ctx and report["frozen_native_context"]==saved["old_audit_context"]
          and report["original_audits_succeeded"]is False,"terminal old/new contexts")
        if state["created"]:demand(state["removed"]and not state["running"],"owned container cleanup omitted")
        if kind in ("body_stop_failure","stop_failure"):demand("kill"in events and "rm"in events,"stop failure skipped kill/remove")
        demand(report["status"]==("PASS_OWNED_AUDIT_STAGE_DIAGNOSTIC"if kind=="complete"else"FAIL_OWNED_ROUTE_TAIL"),"lifecycle result")
        demand("one-two-signal-routing-attempt"not in events,"reroute invoked")
        return dict(case=kind,events=events,status=report["status"],exact_primary_retained=caught is not None,
          real_cloned_probe=True,real_owned_cleanup=True,synthetic_Docker_and_native_IO=True)


def publication_case(kind):
    upload_error=OSError("upload sentinel");save_error=OSError("publication save sentinel")
    source_error=OSError("changed current source sentinel")
    with tempfile.TemporaryDirectory(prefix="audit-publication-control-")as tmp:
        env=env_for("off",Path(tmp));ctx=a.context(env)
        with patch.dict(os.environ,env,clear=True):work=host.owned_work(ctx,True)
        out=work/"out";out.mkdir();(out/"supervision").mkdir()
        raw_host=b'{"status":"FAIL_SYNTHETIC_NATIVE_IO"}\n';raw_case=b'{malformed native result'
        (out/"host-result.json").write_bytes(raw_host);(out/"case-result.json").write_bytes(raw_case)
        (out/"supervision/audit.stdout").write_bytes(b"full synthetic stdout\n")
        (out/"supervision/audit.stderr").write_bytes(b"")
        (out/"owned-container-start.stderr").write_bytes(b"")
        tag="cloud-results-"+ctx["token"]+"-"+a.group("off")
        release=dict(id=900,tag_name=tag,target_commitish=ctx["source"],draft=False,prerelease=True,assets=[])
        if kind=="conflict":release["assets"].append(dict(id=1,name="host-result.json",size=1,digest="sha256:"+"0"*64))
        ref=dict(ref="refs/tags/"+tag,object=dict(type="commit",sha=ctx["source"]))
        uploads=[]
        def read(endpoint):
            if endpoint=="git/ref/tags/"+tag:return copy.deepcopy(ref)
            demand(endpoint in ("releases/tags/"+tag,"releases/900"),"only exact new release read")
            return copy.deepcopy(release)
        def upload(argv,check,timeout):
            demand(argv[:3]==["gh","release","upload"]and argv[3]==tag and argv[-2:]==["--repo",c.REPOSITORY],"exact new release upload")
            p=Path(argv[4]);receipt=build.fingerprint(p)
            demand(receipt["bytes"]>0,"zero byte direct upload")
            if kind in ("upload_failure","upload_and_save_failure")and uploads:raise upload_error
            demand(not any(x["name"]==p.name for x in release["assets"]),"clobber attempted")
            release["assets"].append(dict(id=len(release["assets"])+1,name=p.name,size=receipt["bytes"],digest="sha256:"+receipt["sha256"]))
            uploads.append(p.name);return SimpleNamespace(returncode=0)
        original_replace=os.replace
        def replace(src,dst):
            if kind=="upload_and_save_failure"and Path(dst).name=="publication.json":raise save_error
            return original_replace(src,dst)
        capture=io.StringIO();caught=None
        with ExitStack()as stack:
            stack.enter_context(patch.dict(os.environ,env,clear=True))
            stack.enter_context(patch.object(host.reservation,"wait",return_value=dict(release_id=900,
              existing_assets=[dict(name=x["name"])for x in release["assets"]])))
            stack.enter_context(patch.object(host.reservation.release,"api",side_effect=read))
            stack.enter_context(patch.object(subprocess,"run",side_effect=upload))
            stack.enter_context(patch.object(os,"replace",side_effect=replace))
            if kind=="source_failure":stack.enter_context(patch.object(a,"source_guard",side_effect=source_error))
            stack.enter_context(redirect_stdout(capture))
            try:code=host.publish()
            except BaseException as exc:caught=exc
        if kind in ("upload_failure","upload_and_save_failure"):demand(caught is upload_error,"publication masked primary")
        elif kind=="conflict":demand(type(caught)is ValueError and caught.args==("recovery asset conflict",),"no-clobber refusal")
        else:demand(caught is None,"unexpected publication error")
        demand((out/"host-result.json").read_bytes()==raw_host and (out/"case-result.json").read_bytes()==raw_case,"rewrote original result bytes")
        plan=c.decode((out/"direct-publication-plan.json").read_bytes())
        empties=[x for x in plan["files"]if x["publication"]=="archive_only_empty"]
        demand({x["path"]for x in empties}=={"supervision/audit.stderr","owned-container-start.stderr"},"empty publication plan")
        demand(all(x["bytes"]==0 and x["sha256"]==e.EMPTY for x in empties),"empty hash policy")
        with tarfile.open(work/"audit-recovery-evidence.tar.gz","r:gz")as archive:
            for row in empties:demand(archive.extractfile(row["path"]).read()==b"","empty archive stream lost")
            demand(archive.extractfile("case-result.json").read()==raw_case,"archive raw malformed result changed")
        demand(not any(x in uploads for x in ("audit.stderr","owned-container-start.stderr")),"empty uploaded directly")
        if kind=="upload_and_save_failure":
            line=next(x for x in capture.getvalue().splitlines()if x.startswith("ENGINE_BUILD_TERMINAL_FALLBACK "))
            final=json.loads(line.split(" ",1)[1])["complete_unsaved_record"]
            demand(any(p.startswith("publication.json.")and p.endswith(".tmp")for p in final["available_outputs_after_save_failure"]),"real publication fragment lost")
        else:final=c.decode((out/"publication.json").read_bytes())
        expected="PASS_PERMANENT_AUDIT_EVIDENCE_NOT_ACCEPTANCE"if kind=="complete"else"FAIL_RECOVERY_PUBLICATION"
        demand(final["status"]==expected,"publication status")
        if kind=="complete":
            before=list(uploads)
            def forbidden(*args):raise AssertionError("identical asset re-uploaded")
            reused=host.publish_asset(out/"host-result.json",ctx,900,read,forbidden)
            demand(reused["reused_identical"]is True and uploads==before,"identical no-clobber reuse")
        return dict(case=kind,status=final["status"],uploads=uploads,empty_archive_members=2,
          actual_pack=True,actual_publish=True,raw_result_bytes_unchanged=True,
          synthetic_cloud_transport=True,same_primary=kind in ("upload_failure","upload_and_save_failure"))


def controls():
    method=a.source_guard();data=e.source_guard()
    demand(method["native_restore_authorized"]is method["native_audit_authorized"],"native flags differ")
    jobs=json.loads((a.ROOT/"docs/evidence/mainchip-route-recovery-original-complete-jobs-20261029.json").read_bytes())
    context=context_controls()
    with tempfile.TemporaryDirectory()as tmp:
        ctx=a.context(env_for("off",Path(tmp)))
        # Both typed disabled modes must refuse before any git/transport/native call.
        synthetic=copy.deepcopy(method);synthetic.update(native_restore_authorized=False,native_audit_authorized=False)
        with patch.object(a,"source_guard",return_value=synthetic):
            authority=refusal(lambda:a.authorize(ctx),"new recovery native authority disabled",a.authorize.__code__)
    restored=[];lifecycle=[];publication=[]
    with patch.object(e,"source_guard",return_value=data):
        for mode,fault in (("off",None),("on",None),("off","transport"),("off","outer"),("on","nested")):
            restored.append(restore_case(mode,data,jobs,fault))
        for kind in ("complete","restore_failure","stop_failure","body_stop_failure","create_progress_failure",
          "terminal_save_failure","body_save_failure"):
            lifecycle.append(lifecycle_case(kind,data))
        for kind in ("complete","source_failure","upload_failure","upload_and_save_failure","conflict"):
            publication.append(publication_case(kind))
    demand((len(restored),len(lifecycle),len(publication),len(context["refusals"]))==(5,7,5,6),"case census")
    # Verify all protected checkout bytes after hosted temporary-file fixtures.
    a.source_guard()
    return dict(status="PASS_AUDIT_RECOVERY_SOURCE_CONTROLS",source=os.environ.get("GITHUB_SHA"),
      run_id=int(os.environ["GITHUB_RUN_ID"]),attempt=int(os.environ["GITHUB_RUN_ATTEMPT"]),
      method_sha256=e.sha(a.ROOT/a.METHOD),context=context,disabled_authority_refusal=authority,
      restore_cases=restored,lifecycle_cases=lifecycle,publication_cases=publication,
      original_source=e.SOURCE,original_run=e.RUN,original_failed_status_preserved=True,
      native_IO_synthetic=True,cloud_IO_synthetic=True,real_native_restoration_qualified=False,
      routing_executed=False,engine_executed=False,physical_acceptance=False,
      original_inner_driver_unchanged=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",required=True);args=parser.parse_args()
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
    report=dict(status="RUNNING",source=os.environ.get("GITHUB_SHA"))
    c.atomic_record(path,report)
    try:report=controls()
    except BaseException as exc:
        report.update(status="FAIL",error=repr(exc),error_type=type(exc).__name__);raise
    finally:
        c.atomic_record(path,report);print(json.dumps(report,sort_keys=True,allow_nan=False))


if __name__=="__main__":main()
