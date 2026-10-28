#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only source and failure-admission controls; never invokes Docker."""
import ast
import copy
import json
from pathlib import Path
import tempfile
import mainchip_witness_engine_build_contract as c

ROOT=Path(__file__).resolve().parent.parent

def controls():
    m=c.method(ROOT)
    assert m["source_controls_authorized"] is True and m["engine_build_authorized"] is True
    for path in m["protected"]:
        if path.startswith("scripts/mainchip_witness_engine_build") and path.endswith(".py"):
            ast.parse((ROOT/path).read_text(),filename=path)
    ast.parse((ROOT/"scripts/check_mainchip_witness_engine_build.py").read_text())
    env=dict(GITHUB_ACTIONS="true",RUNNER_OS="Linux",GITHUB_REPOSITORY=c.REPOSITORY,
        GITHUB_RUN_ID="123",GITHUB_RUN_ATTEMPT="1",GITHUB_SHA="a"*40,
        GITHUB_REF="refs/heads/codex/mainchip-internal-witness-engine-build")
    ctx=c.context(env); work=Path("/runner/temp/owned")
    image=dict(Id=c.IMAGE_ID,Architecture="amd64",Os="linux",RepoDigests=[c.IMAGE])
    info=dict(Name="/"+ctx["name"],Id="b"*64,Image=c.IMAGE_ID,Path="/usr/bin/python3",
        Args=["/work/inner.py"],Config=dict(Image=c.IMAGE,Labels={"nssoc.build.source":ctx["source"],
        "nssoc.build.token":ctx["token"]},User="1001:1001",WorkingDir="/work/source",
        Env=["PYTHONDONTWRITEBYTECODE=1"]),HostConfig=dict(NetworkMode="none",ReadonlyRootfs=True,
        Privileged=False,Memory=c.MEMORY,MemorySwap=c.MEMORY,NanoCpus=c.CPUS,PidsLimit=c.PIDS,
        CapDrop=["ALL"],SecurityOpt=["no-new-privileges"],Tmpfs={"/tmp":"rw,nosuid,nodev,size=268435456"},
        Binds=None,Devices=[],DeviceRequests=None,PidMode="",IpcMode="private"),
        Mounts=[dict(Type="bind",Source=str(work),Destination="/work",RW=True)],
        State=dict(Running=False,Pid=0,ExitCode=0,OOMKilled=False,Error=""))
    cg={"memory.max":str(c.MEMORY),"memory.swap.max":"0","pids.max":str(c.PIDS),
        "memory.events":{"oom":0,"oom_kill":0,"oom_group_kill":0},
        "memory.peak":"1048576","cpu.max":"200000 100000"}
    inner=dict(status="PASS_COMPLETE_OPENROAD_BUILD_AND_INTERFACE_SMOKE_ONLY",terminal_errors=[],
        compiled_complete_project=True,physical_acceptance=False,observer_equivalence_qualified=False,
        cgroup_initial=copy.deepcopy(cg),cgroup_terminal=copy.deepcopy(cg))
    assert c.validate_image(image)
    assert c.validate_container(info,ctx,work,True)
    normalized=copy.deepcopy(info);normalized["HostConfig"]["SecurityOpt"]=["no-new-privileges:true"]
    assert c.validate_container(normalized,ctx,work,True)
    assert c.validate_terminal(info,inner)
    argv=c.create_argv(ctx,work,1001,1001)
    assert "--privileged" not in argv and argv[-2:]==[c.IMAGE,"/work/inner.py"]
    positive=["protected_complete_source","immutable_image","owned_isolated_container",
        "docker_securityopt_normalization","terminal_success_scope_only","resource_argv"]
    refused=[]
    def reject(label,fn,reason):
        try:fn()
        except ValueError as exc:
            assert str(exc)==reason,(label,str(exc),reason);refused.append(label)
        else:raise AssertionError("accepted "+label)
    for key,value,reason in [
        ("GITHUB_ACTIONS","false","hosted Linux only"),("RUNNER_OS","Windows","hosted Linux only"),
        ("GITHUB_REPOSITORY","other/repo","repository identity"),
        ("GITHUB_RUN_ATTEMPT","2","no automatic retry"),("GITHUB_RUN_ID","0","run identity"),
        ("GITHUB_SHA","main","immutable tested source"),("GITHUB_REF","refs/heads/main","build branch")]:
        changed=dict(env);changed[key]=value
        reject("context:"+key,lambda:c.context(changed),reason)
    for key,value,reason in [("Id","sha256:"+"c"*64,"image configuration"),
        ("Architecture","arm64","image configuration"),("RepoDigests",["mutable:tag"],"immutable image digest")]:
        changed=copy.deepcopy(image);changed[key]=value
        reject("image:"+key,lambda:c.validate_image(changed),reason)
    for key,value,reason in [
        ("Memory",c.MEMORY+1,"container resource binding"),("MemorySwap",-1,"container resource binding"),
        ("NanoCpus",3_000_000_000,"container resource binding"),("PidsLimit",0,"container resource binding"),
        ("NetworkMode","host","container isolation"),("ReadonlyRootfs",False,"container isolation"),
        ("Privileged",True,"container isolation"),("CapDrop",[],"container privileges"),
        ("SecurityOpt",[],"container privileges"),("Tmpfs",{},"container temporary storage"),
        ("Devices",[{"PathOnHost":"/dev/mem"}],"unexpected device or bind"),
        ("PidMode","host","container namespace")]:
        changed=copy.deepcopy(info);changed["HostConfig"][key]=value
        reject("container:"+key,lambda:c.validate_container(changed,ctx,work),reason)
    changed=copy.deepcopy(info);changed["Config"]["User"]="0:0"
    reject("root_user",lambda:c.validate_container(changed,ctx,work),"container user/workdir")
    changed=copy.deepcopy(info);changed["Config"]["Labels"]["nssoc.build.source"]="d"*40
    reject("wrong_owner",lambda:c.validate_container(changed,ctx,work),"container ownership")
    changed=copy.deepcopy(info);changed["Mounts"][0]["Source"]="/"
    reject("mount_escape",lambda:c.validate_container(changed,ctx,work),"container mounts")
    changed=copy.deepcopy(info);changed["State"]["Running"]=True
    reject("live_terminal",lambda:c.validate_container(changed,ctx,work,True),"container still running")
    for key,value in [("OOMKilled",True),("ExitCode",1),("Error","error")]:
        changed=copy.deepcopy(info);changed["State"][key]=value
        reject("terminal:"+key,lambda:c.validate_terminal(changed,inner),"container terminal failure")
    for key,value,reason in [("physical_acceptance",True,"build scope"),
        ("observer_equivalence_qualified",True,"build scope"),("compiled_complete_project",False,"build scope"),
        ("status","PASS","inner build failure"),("terminal_errors",["missing evidence"],"inner build failure")]:
        changed=copy.deepcopy(inner);changed[key]=value
        reject("inner:"+key,lambda:c.validate_terminal(info,changed),reason)
    for key,value,reason in [("memory.max","max","native cgroup limits"),
        ("memory.swap.max","max","native cgroup limits"),("pids.max","max","native cgroup limits"),
        ("memory.peak",str(c.MEMORY+1),"native memory peak"),("cpu.max","max 100000","native CPU quota")]:
        changed=copy.deepcopy(inner);changed["cgroup_terminal"][key]=value
        reject("cgroup:"+key,lambda:c.validate_terminal(info,changed),reason)
    for key in ("oom","oom_kill","oom_group_kill"):
        changed=copy.deepcopy(inner);changed["cgroup_terminal"]["memory.events"][key]=1
        reject("cgroup:"+key,lambda:c.validate_terminal(info,changed),"native cgroup OOM")
    reject("duplicate_json",lambda:c.decode('{"a":1,"a":2}'),"duplicate JSON key")
    with tempfile.TemporaryDirectory(prefix="engine-build-source-controls-")as folder:
        root=Path(folder);(root/"real").write_text("real");(root/"link").symlink_to(root/"real")
        assert c.secure_file(root,"real").read_text()=="real";positive.append("regular_file")
        reject("path_escape",lambda:c.secure_file(root,"../outside"),"path escape")
        reject("path_symlink",lambda:c.secure_file(root,"link"),"path symlink")
    lifecycle=lifecycle_controls()
    return dict(status="PASS_ENGINE_BUILD_SOURCE_CONTROLS",lifecycle=lifecycle,positive_cases=positive,
        refusal_cases=refused,positive_count=len(positive),refusal_count=len(refused),
        native_executed=False,physical_acceptance=False,observer_equivalence_qualified=False)


def lifecycle_controls():
    import contextlib
    import io
    import os
    import signal
    import subprocess
    from types import SimpleNamespace
    from unittest import mock
    import mainchip_witness_engine_build as host
    import mainchip_witness_engine_build_inner as inner
    cases=[]
    def raised(fn, exact=None, kind=BaseException):
        try: fn()
        except kind as exc:
            if exact is not None: assert exc is exact
            return exc
        raise AssertionError("expected actual helper refusal")
    def report():
        return dict(status="IN_PROGRESS",commands=[],terminal_errors=[],creation_attempted=False,
                    physical_acceptance=False,observer_equivalence_qualified=False)
    ctx=dict(name="nssoc-witness-build-123-1",source="a"*40,token="123-1")
    cache="\n".join(k+":BOOL="+v for k,v in (
        ("LINK_TIME_OPTIMIZATION","OFF"),("CMAKE_INTERPROCEDURAL_OPTIMIZATION","OFF"),
        ("BUILD_PYTHON","ON"),("BUILD_GUI","OFF"),("ENABLE_TESTS","OFF")))
    commands=[dict(command="g++ -std=c++20 -c source.cpp")]
    assert c.validate_build_configuration(cache,commands)["compile_commands_no_flto"]
    cases.append("actual_cache_flags")
    raised(lambda:c.validate_build_configuration(cache.replace("LINK_TIME_OPTIMIZATION:BOOL=OFF",
        "LINK_TIME_OPTIMIZATION:BOOL=ON"),commands),kind=ValueError)
    cases.append("original_release_lto_default_refused")
    raised(lambda:c.validate_build_configuration(cache,[dict(arguments=["g++","-flto=auto","-c","x.cpp"])]),kind=ValueError)
    cases.append("actual_compile_lto_refused")
    with tempfile.TemporaryDirectory(prefix="engine-actual-lifecycle-") as folder:
        root=Path(folder)
        for body_failure in (True,False):
            out=root/("command-"+str(body_failure));out.mkdir();r=report()
            primary=RuntimeError("command-primary");progress=OSError("progress-write")
            def runner(argv,**kwargs):
                kwargs["stdout"].write(b"complete command prefix\n")
                if body_failure: raise primary
                return SimpleNamespace(returncode=0)
            with mock.patch.object(host,"write",side_effect=progress):
                raised(lambda:host.execute_command(r,out,"actual",["synthetic"],runner=runner),
                       primary if body_failure else progress)
            assert (out/"actual.stdout").read_bytes()==b"complete command prefix\n"
            assert r["terminal_errors"][-1]["action"]=="host-progress"
            cases.append("host_primary_progress" if body_failure else "host_progress_only")

        def docker_info(work):
            return dict(Name="/"+ctx["name"],Id="b"*64,Image=c.IMAGE_ID,Path="/usr/bin/python3",
                Args=["/work/inner.py"],Config=dict(Image=c.IMAGE,
                Labels={"nssoc.build.source":ctx["source"],"nssoc.build.token":ctx["token"]},
                User="1001:1001",WorkingDir="/work/source",Env=["PYTHONDONTWRITEBYTECODE=1"]),
                HostConfig=dict(NetworkMode="none",ReadonlyRootfs=True,Privileged=False,
                Memory=c.MEMORY,MemorySwap=c.MEMORY,NanoCpus=c.CPUS,PidsLimit=c.PIDS,
                CapDrop=["ALL"],SecurityOpt=["no-new-privileges"],Tmpfs={"/tmp":"rw,nosuid,nodev,size=268435456"},
                Binds=None,Devices=[],DeviceRequests=None,PidMode="",IpcMode="private"),
                Mounts=[dict(Type="bind",Source=str(work),Destination="/work",RW=True)],
                State=dict(Running=False,Pid=0,ExitCode=0,OOMKilled=False,Error=""))

        for mode in ("progress","client_timeout"):
            work=root/("create-"+mode);(work/"out").mkdir(parents=True);r=report()
            state={"exists":False};info=docker_info(work);calls=[]
            primary=OSError("post-create-progress") if mode=="progress" else subprocess.TimeoutExpired("docker create",120)
            def runner(argv,**kwargs):
                calls.append(list(argv))
                if argv[:2]==["docker","create"]:
                    state["exists"]=True;kwargs["stdout"].write((info["Id"]+"\n").encode())
                    if mode=="client_timeout": raise primary
                elif argv[:2]==["docker","rm"]:
                    state["exists"]=False
                elif argv[:3]==["docker","container","ls"]:
                    kwargs["stdout"].write((ctx["name"]+"\n").encode() if state["exists"] else b"")
                return SimpleNamespace(returncode=0)
            def invoke(label,argv,timeout=120):
                return host.execute_command(r,work/"out",label,argv,timeout,runner)
            original_write=host.write
            def writer(path,value):
                if mode=="progress" and path.name=="host-progress.json" and r["commands"][-1]["label"]=="owned-container-create":
                    raise primary
                return original_write(path,value)
            def inspect_one(identity):
                assert identity in (ctx["name"],info["Id"]) and state["exists"]
                return copy.deepcopy(info)
            with mock.patch.object(host,"write",side_effect=writer):
                raised(lambda:host.create_owned(ctx,work,r,invoke,c.create_argv(ctx,work,1001,1001)),primary)
            assert r["creation_attempted"] is True
            assert c.decode((work/"out/create-attempt.json").read_bytes())["creation_attempted"] is True
            host.cleanup_owned(ctx,work,r,None,True,inspect_one,invoke)
            assert not state["exists"] and r["owned_container_recovery"]["id"]==info["Id"]
            assert (work/"out/container-terminal.json").is_file()
            assert any(x[:2]==["docker","rm"] for x in calls)
            cases.append("actual_create_"+mode+"_owned_recovery")

        work=root/"preexisting";(work/"out").mkdir(parents=True);r=report();called=[]
        def names_only(label,argv,timeout):
            called.append(label);return (ctx["name"]+"\n").encode()
        raised(lambda:host.create_owned(ctx,work,r,names_only,c.create_argv(ctx,work,1001,1001)),kind=ValueError)
        assert not r["creation_attempted"] and not (work/"out/create-attempt.json").exists()
        host.cleanup_owned(ctx,work,r,None,False,lambda _:(_ for _ in ()).throw(AssertionError("must not inspect")),
                           lambda *args:(_ for _ in ()).throw(AssertionError("must not clean")))
        assert called==["names-before-owned-create"]
        cases.append("preexisting_name_never_owned")

        work=root/"wrong-owner";(work/"out").mkdir(parents=True);r=report();info=docker_info(work)
        info["Config"]["Labels"]["nssoc.build.source"]="c"*40;called=[]
        host.cleanup_owned(ctx,work,r,None,True,lambda _:copy.deepcopy(info),lambda *args:called.append(args))
        assert not called and r["terminal_errors"][0]["action"]=="recover-owned-container"
        cases.append("wrong_owner_never_cleaned")

        work=root/"stop-failure";(work/"out").mkdir(parents=True);r=report();info=docker_info(work)
        info["State"].update(Running=True,Pid=1234);state={"exists":True,"inspects":0};called=[]
        stop_error=RuntimeError("owned stop failed");inspect_error=OSError("post-stop inspect failed")
        def inspect_one(identity):
            assert state["exists"];state["inspects"]+=1
            if state["inspects"]==3:raise inspect_error
            return copy.deepcopy(info)
        def invoke(label,argv,timeout):
            called.append(label)
            if label=="owned-stop":raise stop_error
            if label=="owned-kill":info["State"].update(Running=False,Pid=0,ExitCode=137)
            if label=="owned-container-remove":state["exists"]=False
            return b""
        host.cleanup_owned(ctx,work,r,info["Id"],True,inspect_one,invoke)
        assert not state["exists"] and "owned-kill" in called and "owned-container-remove" in called
        assert c.decode((work/"out/container-terminal.json").read_bytes())["State"]["ExitCode"]==137
        assert {x["action"] for x in r["terminal_errors"]}>={"owned-stop","post-stop-inspect"}
        cases.append("stop_and_inspect_failures_still_kill_and_remove")

        for mode in ("save_only","body_and_save","save_and_refresh"):
            out=root/mode;out.mkdir();path=out/"host-result.json"
            path.write_bytes(b'{"status":"PRIOR"}\n')
            (out/"host-result.json.tmp").write_bytes(b"older immutable fragment")
            (out/"partial.log").write_bytes(b"exact partial output\n")
            r=report();r["status"]="PASS_COMPILED_ENGINE_INTERFACE_ONLY"
            primary=RuntimeError("original body") if mode=="body_and_save" else None
            save=OSError("real atomic replace");refresh=OSError("inventory refresh");saved_inventory=c.inventory
            def inv(*args,**kwargs):
                if mode=="save_and_refresh" and not args[1:]:raise refresh
                return saved_inventory(*args,**kwargs)
            capture=io.StringIO()
            with mock.patch.object(c.os,"replace",side_effect=save),mock.patch.object(c,"inventory",side_effect=inv),contextlib.redirect_stdout(capture):
                raised(lambda:c.finish_record(path,r,"FAIL_ENGINE_BUILD",primary),primary or save)
            fallback=json.loads(capture.getvalue().split("ENGINE_BUILD_TERMINAL_FALLBACK ",1)[1])
            body=fallback["complete_unsaved_record"]
            assert body["status"]=="FAIL_ENGINE_BUILD" and fallback["acceptance"] is False
            assert path.read_bytes()==b'{"status":"PRIOR"}\n'
            assert (out/"host-result.json.tmp").read_bytes()==b"older immutable fragment"
            fragments=[p for p in out.glob("host-result.json.*.tmp")]
            assert len(fragments)==1 and fragments[0].stat().st_size>0
            if mode=="save_and_refresh":
                assert body["terminal_errors"][-1]["action"]=="post-save-inventory"
            else:
                assert body["available_outputs_after_save_failure"]==saved_inventory(out)
                assert fragments[0].name in body["available_outputs_after_save_failure"]
            assert any(x.name=="atomic_record" for x in __import__("traceback").extract_tb(save.__traceback__))
            cases.append("actual_atomic_"+mode)

        out=root/"saved";out.mkdir();r=report();r["status"]="FAIL_ENGINE_BUILD"
        c.finish_record(out/"host-result.json",r,"FAIL_ENGINE_BUILD")
        assert c.decode((out/"host-result.json").read_bytes())==r
        cases.append("actual_atomic_saved_terminal")

        out=root/"inner-run";out.mkdir();r=report();primary=RuntimeError("native child observation")
        cleanup=OSError("TERM failure");progress=OSError("inner progress")
        class Process:
            pid=987654;returncode=None
            def poll(self):return self.returncode
            def wait(self,timeout):
                if self.returncode is None:raise subprocess.TimeoutExpired("synthetic owned child",timeout)
                return self.returncode
        proc=Process();signals=[]
        def killpg(pid,sig):
            assert pid==proc.pid;signals.append(sig)
            if sig==signal.SIGTERM:raise cleanup
            proc.returncode=-9
        with mock.patch.multiple(inner,OUT=out,report=r),mock.patch.object(inner,"cgroup",side_effect=primary),mock.patch.object(inner,"write",side_effect=progress):
            raised(lambda:inner.run("child",["synthetic"],popen=lambda *a,**k:proc,killpg=killpg),primary)
        assert signals==[signal.SIGTERM,signal.SIGKILL] and proc.returncode==-9
        assert {x["action"] for x in r["terminal_errors"]}>={"child-terminate","inner-progress"}
        cases.append("actual_inner_run_primary_cleanup_progress")

        # Complete host main/finally; external admission and reservation are explicit synthetic collaborators.
        work=root/"host-entry";work.mkdir();primary=RuntimeError("reservation transport")
        save=OSError("actual host final replace");before={s:signal.getsignal(s) for s in (signal.SIGTERM,signal.SIGINT)}
        capture=io.StringIO();real_replace=os.replace
        def replace(src,dst):
            if Path(dst).name=="host-result.json":raise save
            return real_replace(src,dst)
        with mock.patch.object(c,"context",return_value=ctx),mock.patch.object(c,"method",return_value={"source_controls_authorized":True,"engine_build_authorized":True}),mock.patch.object(host,"owned_work",return_value=work),mock.patch.object(host.reservation,"wait",side_effect=primary),mock.patch.object(c.os,"replace",side_effect=replace),contextlib.redirect_stdout(capture):
            raised(host.build,primary)
        body=json.loads(capture.getvalue().split("ENGINE_BUILD_TERMINAL_FALLBACK ",1)[1])["complete_unsaved_record"]
        assert body["status"]=="FAIL_ENGINE_BUILD" and body["creation_attempted"] is False
        assert all(signal.getsignal(s)==v for s,v in before.items())
        assert any(k.startswith("host-result.json.") for k in body["available_outputs_after_save_failure"])
        cases.append("actual_host_main_body_and_final_save")

        work=root/"inner-entry";out=work/"out";out.mkdir(parents=True)
        r=report();r["compiled_complete_project"]=False;primary=RuntimeError("compiler transport");save=OSError("inner final replace")
        cg={"memory.max":str(c.MEMORY),"memory.swap.max":"0","pids.max":str(c.PIDS),
            "memory.events":{"oom":0,"oom_kill":0,"oom_group_kill":0},"cpu.max":"200000 100000"}
        capture=io.StringIO()
        with mock.patch.multiple(inner,WORK=work,OUT=out,report=r),mock.patch.object(inner,"cgroup",return_value=cg),mock.patch.object(inner,"run",side_effect=primary),mock.patch.object(c.os,"replace",side_effect=save),contextlib.redirect_stdout(capture):
            raised(inner.main,primary)
        body=json.loads(capture.getvalue().split("ENGINE_BUILD_TERMINAL_FALLBACK ",1)[1])["complete_unsaved_record"]
        assert body["status"]=="FAIL_ENGINE_BUILD_OR_INTERFACE_SMOKE"
        assert {a["action"] for a in body["terminal_actions"]}>={"preserve-build-records","terminal-cgroup"}
        cases.append("actual_inner_main_body_and_final_save")

        out=root/"missing-terminal";out.mkdir();(out/"partial.stdout").write_bytes(b"available")
        availability=host.terminal_availability(out)
        assert all(not x["present"] for x in availability["source_records"].values())
        assert availability["missing_or_malformed_records_do_not_block_preservation"]
        assert c.inventory(out)["partial.stdout"]["sha256"]==c.digest(b"available")
        (out/"host-result.json").write_bytes(b'{"status":')
        assert "parse_error" in host.terminal_availability(out)["source_records"]["host-result.json"]
        cases.append("absent_and_truncated_terminal_preserved")

        tag="cloud-results-"+ctx["token"]+"-"+c.GROUP
        for mode in ("new","identical","wrong_source","wrong_release","conflict","post_digest"):
            out=root/("publication-"+mode);out.mkdir();path=out/"direct.json";path.write_bytes(b'{"complete":true}\n')
            info=dict(id=5,tag_name=tag,target_commitish=ctx["source"],draft=False,prerelease=True,assets=[])
            ref=dict(ref="refs/tags/"+tag,object=dict(type="commit",sha=ctx["source"]));uploads=[]
            if mode in ("identical","conflict"):
                info["assets"]=[dict(id=9,name=path.name,size=path.stat().st_size,digest="sha256:"+c.digest(path.read_bytes()))]
                if mode=="conflict":info["assets"][0]["digest"]="sha256:"+"c"*64
            if mode=="wrong_source":ref["object"]["sha"]="c"*40
            if mode=="wrong_release":info["id"]=6
            def read(api_path):
                return copy.deepcopy(info if api_path.startswith("releases/") else ref)
            def upload(actual_tag,p):
                assert actual_tag==tag;uploads.append(p.name)
                info["assets"].append(dict(id=9,name=p.name,size=p.stat().st_size,
                    digest="sha256:"+("c"*64 if mode=="post_digest" else c.digest(p.read_bytes()))))
            if mode in ("new","identical"):
                answer=host.publish_asset(path,ctx,5,read,upload)
                assert answer["reused_identical"] is (mode=="identical")
                assert uploads==([] if mode=="identical" else [path.name])
            else:
                error=raised(lambda:host.publish_asset(path,ctx,5,read,upload))
                if mode=="wrong_source":
                    assert type(error) is AssertionError
                    assert any(x.name=="validate_release" for x in __import__("traceback").extract_tb(error.__traceback__))
                else:
                    reason={"wrong_release":"reserved release identity","conflict":"existing asset conflict",
                            "post_digest":"published asset mismatch"}[mode]
                    assert type(error) is ValueError and error.args==(reason,)
                assert uploads==([path.name] if mode=="post_digest" else [])
            cases.append("actual_reserved_publication_"+mode)
        # Actual publisher assembly with only synthetic output bytes and fake remote transport.
        work=root/"missing-terminal-publication";out=work/"out";out.mkdir(parents=True)
        (out/"partial.stdout").write_bytes(b"complete available failure stream\n")
        info=dict(id=5,tag_name=tag,target_commitish=ctx["source"],draft=False,prerelease=True,assets=[])
        ref=dict(ref="refs/tags/"+tag,object=dict(type="commit",sha=ctx["source"]))
        calls=[]
        def remote_read(api_path):
            return copy.deepcopy(info if api_path.startswith("releases/") else ref)
        def remote_upload(argv,**kwargs):
            assert argv[:3]==["gh","release","upload"] and argv[3]==tag
            p=Path(argv[4]);calls.append(p.name)
            info["assets"].append(dict(id=100+len(calls),name=p.name,size=p.stat().st_size,
                digest="sha256:"+c.digest(p.read_bytes())))
            return SimpleNamespace(returncode=0)
        capture=io.StringIO()
        with mock.patch.object(c,"context",return_value=ctx),mock.patch.object(c,"method",return_value={}),mock.patch.object(host,"owned_work",return_value=work),mock.patch.object(host.reservation,"wait",return_value=dict(release_id=5,existing_assets=[])),mock.patch.object(host.reservation.release,"api",side_effect=remote_read),mock.patch.object(host.subprocess,"run",side_effect=remote_upload),contextlib.redirect_stdout(capture):
            assert host.publish()==0
        availability=c.decode((out/"publication-availability.json").read_bytes())
        assert all(not item["present"] for item in availability["source_records"].values())
        outputs=c.decode((out/"outputs.json").read_bytes())
        assert outputs["files"]["partial.stdout"]["sha256"]==c.digest(b"complete available failure stream\n")
        assert outputs["physical_acceptance"] is False
        assert set(calls)=={"outputs.json","parts.json","publication-availability.json","engine-evidence.tar.gz.part000"}
        with host.tarfile.open(work/"engine-evidence.tar.gz","r:gz") as packed:
            assert packed.extractfile("partial.stdout").read()==b"complete available failure stream\n"
        assert c.decode((out/"publication.json").read_bytes())["status"]=="PASS_PERMANENT_RELEASE_PUBLICATION"
        cases.append("actual_missing_terminal_failure_publication")
    assert len(cases)==25 and len(set(cases))==25
    return dict(status="PASS_ACTUAL_ENGINE_LIFECYCLE_SOURCE_CONTROLS",cases=cases,count=len(cases),
                external_transport="Explicit synthetic Docker/native/remote collaborators; actual production helpers, file writers and main/finally paths.",
                native_executed=False,real_container_or_compiler_executed=False)

if __name__=="__main__":
    print(json.dumps(controls(),sort_keys=True,indent=2))
