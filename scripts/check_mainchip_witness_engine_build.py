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
    return dict(status="PASS_ENGINE_BUILD_SOURCE_CONTROLS",positive_cases=positive,
        refusal_cases=refused,positive_count=len(positive),refusal_count=len(refused),
        native_executed=False,physical_acceptance=False,observer_equivalence_qualified=False)

if __name__=="__main__":
    print(json.dumps(controls(),sort_keys=True,indent=2))
