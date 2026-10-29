#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted source controls. Native/Git/Docker/upload collaborators are synthetic.
Actual new build/main/finally, exact source derivations, ownership and archive code run.
No full engine compilation, runtime probe, native database or routing qualification.
"""
import argparse,contextlib,copy,io,json,os,subprocess,tarfile,tempfile,traceback
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import mainchip_fixed_engine_build as h
import mainchip_fixed_engine_build_contract as c
import check_mainchip_witness_engine_build as old_checks

ROOT=Path(__file__).resolve().parents[1]
PRIMARY={'.gitmodules': 'docs/evidence/mainchip-internal-witness-engine-build-primary-20261028/.gitmodules', 'Dockerfile': 'docs/evidence/mainchip-internal-witness-engine-build-primary-20261028/Dockerfile', 'docs/user/Build.md': 'docs/evidence/mainchip-internal-witness-engine-build-primary-20261028/docs/user/Build.md', 'etc/Build.sh': 'docs/evidence/mainchip-internal-witness-engine-build-primary-20261028/etc/Build.sh', 'etc/DependencyInstaller.sh': 'docs/evidence/mainchip-internal-witness-engine-build-primary-20261028/etc/DependencyInstaller.sh', 'etc/DockerTag.sh': 'docs/evidence/mainchip-internal-witness-engine-build-primary-20261028/etc/DockerTag.sh', 'CMakeLists.txt': 'docs/evidence/mainchip-internal-witness-engine-build-primary-20261028/CMakeLists.txt', 'src/drt/src/TritonRoute.cpp': 'docs/evidence/mainchip-two-signal-current-readback-bounded-diagnosis-20261028-primary/TritonRoute.cpp', 'src/drt/src/dr/FlexDR_init.cpp': 'docs/evidence/mainchip-two-signal-ownership-primary-20261026/src/drt/src/dr/FlexDR_init.cpp'}

def encoded(value):return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
def refuse(name,call,rows):
    try:call()
    except (ValueError,AssertionError,KeyError)as exc:rows.append(dict(name=name,error=repr(exc)))
    else:raise AssertionError("mutation accepted: "+name)

def environment(run="771"):
    return dict(GITHUB_ACTIONS="true",RUNNER_ENVIRONMENT="github-hosted",RUNNER_OS="Linux",
      GITHUB_REPOSITORY=c.REPOSITORY,GITHUB_EVENT_NAME="workflow_dispatch",GITHUB_RUN_ATTEMPT="1",
      GITHUB_SHA="a"*40,GITHUB_RUN_ID=run,GITHUB_REF="refs/heads/"+c.BRANCH)

def reservation(ctx,assets=()):
    return dict(release_id=19,externally_reserved=True,creation_attempted=False,assets_overwritten=False,
      target_verified=True,tested_source=ctx["source"],tag="cloud-results-"+ctx["token"]+"-"+c.GROUP,
      existing_assets=list(assets))

def image():return dict(Id=c.IMAGE_ID,Architecture="amd64",Os="linux",RepoDigests=[c.IMAGE])

def container(ctx,work,running=False):
    return dict(Name="/"+ctx["name"],Id="b"*64,Image=c.IMAGE_ID,Path="/usr/bin/python3",Args=["/work/inner.py"],
      Config=dict(Image=c.IMAGE,Labels={"nssoc.build.source":ctx["source"],"nssoc.build.token":ctx["token"]},
        User="1001:1001",WorkingDir="/work/source",Env=["PYTHONDONTWRITEBYTECODE=1"]),
      HostConfig=dict(NetworkMode="none",ReadonlyRootfs=True,Privileged=False,Memory=c.MEMORY,MemorySwap=c.MEMORY,
        NanoCpus=c.CPUS,PidsLimit=c.PIDS,CapDrop=["ALL"],SecurityOpt=["no-new-privileges"],
        Tmpfs={"/tmp":"rw,nosuid,nodev,size=268435456"},Binds=None,Devices=[],DeviceRequests=None,
        PidMode="",IpcMode="private"),
      Mounts=[dict(Type="bind",Source=str(work),Destination="/work",RW=True)],
      State=dict(Running=running,Pid=7 if running else 0,ExitCode=0,OOMKilled=False,Error=""))

def fixture_root(destination,method):
    destination.mkdir()
    for name in set(method["protected"])|{c.METHOD}:
        src=c.secure_file(ROOT,name);out=destination/name;out.parent.mkdir(parents=True,exist_ok=True)
        os.link(src,out)
    for name in ("engine-build-controls.json","internal-witness-controls.json","fixed-engine-controls.json"):
        (destination/name).write_bytes(encoded(dict(explicit_synthetic_control_transport=True)))
    return destination

def put_method(root,value):
    p=root/c.METHOD;p.unlink();p.write_bytes(encoded(value))

def source_controls(method,root):
    rows=[];disabled=copy.deepcopy(method)
    for k in ("source_controls_authorized","engine_build_authorized","controller_ready"):disabled[k]=False
    put_method(root,disabled);assert c.method(root)==disabled
    refuse("disabled execution",lambda:c.authorize(c.method(root)),rows)
    enabled=copy.deepcopy(disabled)
    for k in ("source_controls_authorized","engine_build_authorized","controller_ready"):enabled[k]=True
    put_method(root,enabled);c.authorize(c.method(root))
    for base in (disabled,enabled):
        for key in ("source_controls_authorized","engine_build_authorized","controller_ready"):
            bad=copy.deepcopy(base);bad[key]=1;put_method(root,bad)
            refuse("typed "+key+str(base["engine_build_authorized"]),lambda:c.method(root),rows)
    for key in c.FALSE:
        bad=copy.deepcopy(enabled);bad[key]=True;put_method(root,bad)
        refuse("scope "+key,lambda:c.method(root),rows)
    bad=copy.deepcopy(enabled);del bad["protected"]["scripts/mainchip_fixed_engine_build.py"]
    put_method(root,bad);refuse("new source unit pin omitted",lambda:c.method(root),rows)
    put_method(root,enabled)
    for key,value in (("GITHUB_REF","refs/heads/old"),("GITHUB_RUN_ATTEMPT","2"),
      ("GITHUB_EVENT_NAME","push"),("GITHUB_SHA","x"),("RUNNER_ENVIRONMENT","self-hosted")):
        env=environment();env[key]=value;refuse("context "+key,lambda env=env:c.context(env),rows)
    ctx=c.context(environment());proof=reservation(ctx)
    assert c.validate_reservation(proof,ctx,True)==proof
    for key,value in (("tested_source","b"*40),("tag","wrong"),("release_id",True),("creation_attempted",True),
      ("existing_assets",[{"name":"occupied"}])):
        bad=dict(proof);bad[key]=value
        refuse("reservation "+key,lambda bad=bad:c.validate_reservation(bad,ctx,True),rows)
    return dict(status="PASS_REAL_NEW_AUTHORITY_CONTROLS",refusals=rows),enabled

class NativeTransport:
    """Only synthetic Git acquisition, Docker/native subprocess and inspection."""
    def __init__(self,root,base,ctx,mode):
        self.root=root;self.base=base;self.ctx=ctx;self.mode=mode
        self.work=base/(c.GROUP+"-"+ctx["token"]);self.calls=[];self.exists=False;self.running=False
        self.body_error=OSError("synthetic native transport failure")
        self.stop_error=OSError("synthetic owned stop failure")
        self.progress_error=OSError("synthetic create progress write failure")
        self.save_error=OSError("synthetic final atomic replace failure")
        self.create_progress_failed=False
        self.real_write=h.write;self.real_replace=os.replace
    def revision(self,path):
        for rel,(_,rev)in c.GITLINKS.items():
            if str(path).endswith("/"+rel):return rev
        return c.UPSTREAM
    def tracked(self,path):
        if path==self.work/"source":return sorted(PRIMARY)+list(c.GITLINKS)
        return ["fixture-dependency.txt"]
    def query(self,argv,**kwargs):
        if argv[:2]==["docker","inspect"]:
            assert self.exists
            return encoded([container(self.ctx,self.work,self.running)])
        assert argv[0]=="git"and argv[1]=="-C",argv
        path=Path(argv[2])
        if argv[3:]==["ls-files","-z"]:return b"\0".join(x.encode()for x in self.tracked(path))+b"\0"
        assert argv[3:]==["rev-parse","HEAD"],argv
        return self.revision(path)+"\n" if kwargs.get("text")else (self.revision(path)+"\n").encode()
    def runner(self,argv,stdout,stderr,timeout):
        self.calls.append(list(argv));data=b""
        if argv[0]=="git":
            if argv[1]=="init":pass
            else:
                assert argv[1]=="-C";path=Path(argv[2]);op=argv[3:]
                if op[:1]==["checkout"]:
                    if path==self.work/"source":
                        for rel,snapshot in PRIMARY.items():
                            target=path/rel;target.parent.mkdir(parents=True,exist_ok=True)
                            target.write_bytes(c.secure_file(self.root,snapshot).read_bytes())
                    else:(path/"fixture-dependency.txt").write_bytes(b"synthetic dependency fixture\n")
                elif op==["rev-parse","HEAD"]:data=(self.revision(path)+"\n").encode()
                elif op==["ls-tree","-r","HEAD"]:
                    if path==self.work/"source":
                        data="".join("160000 commit "+rev+"\t"+rel+"\n"for rel,(_,rev)in c.GITLINKS.items()).encode()
                else:assert op[0]in("remote","fetch"),op
        elif argv[0]=="docker":
            op=argv[1]
            if op=="container":
                data=(self.ctx["name"]+"\n").encode()if self.exists else b""
            elif op=="version":data=b"synthetic Docker version\n"
            elif op=="pull":pass
            elif op=="image":data=encoded([image()])
            elif op=="create":
                self.exists=True;data=("b"*64+"\n").encode()
            elif op=="start":
                self.running=self.mode in ("stop_failure","body_and_stop")
                out=self.work/"out";(out/"partial-native.stdout").write_bytes(b"synthetic complete available stdout\n")
                cg={"memory.max":str(c.MEMORY),"memory.swap.max":"0","pids.max":str(c.PIDS),
                  "memory.events":{"oom":0,"oom_kill":0,"oom_group_kill":0},"memory.peak":"1","cpu.max":"200000 100000"}
                (out/"openroad").write_bytes(b"explicit synthetic ELF bytes, not executable\n")
                inner=dict(status="PASS_COMPLETE_OPENROAD_BUILD_AND_INTERFACE_SMOKE_ONLY",terminal_errors=[],
                  compiled_complete_project=True,physical_acceptance=False,observer_equivalence_qualified=False,
                  cgroup_initial=cg,cgroup_terminal=cg,binary=h.fingerprint(out/"openroad"),
                  synthetic_native_collaborator=True)
                (out/"inner-result.json").write_bytes(encoded(inner))
                if self.mode=="source_mutation":
                    with (self.work/"source"/c.FLEX).open("ab")as f:f.write(b"\n")
                if self.mode=="projection_mutation":
                    with (self.work/"inner.py").open("ab")as f:f.write(b"\n")
                if self.mode in ("body_failure","body_and_stop","body_and_save"):raise self.body_error
            elif op=="stop":
                if self.mode in ("stop_failure","body_and_stop"):raise self.stop_error
                self.running=False
            elif op=="kill":self.running=False
            elif op=="rm":self.exists=False
            else:raise AssertionError(argv)
        else:raise AssertionError("unapproved native fixture transport: "+str(argv))
        stdout.write(data);stdout.flush()
        return SimpleNamespace(returncode=0)
    def write(self,path,value):
        if self.mode=="create_progress_failure"and Path(path).name=="host-progress.json"and self.exists and not self.create_progress_failed:
            self.create_progress_failed=True;raise self.progress_error
        return self.real_write(path,value)
    def replace(self,src,dst):
        if self.mode in ("save_failure","body_and_save")and Path(dst).name=="host-result.json":raise self.save_error
        return self.real_replace(src,dst)

def lifecycle_controls(root,enabled,base):
    cases=[]
    modes=("success","body_failure","create_progress_failure","stop_failure","body_and_stop",
      "source_mutation","projection_mutation","save_failure","body_and_save","wrong_reservation")
    original_command=h.execute_command
    for index,mode in enumerate(modes):
        env=environment(str(800+index));env["RUNNER_TEMP"]=str(base)
        ctx=c.context(env);transport=NativeTransport(root,base,ctx,mode);proof=reservation(ctx)
        old=dict(status="PASS_ENGINE_BUILD_SOURCE_CONTROLS",positive_count=7,refusal_count=45,lifecycle=dict(count=25),
          synthetic_control_report_transport=True)
        fixed=dict(status="PASS_FIXED_ENGINE_BUILD_SOURCE_CONTROLS",current_source=ctx["source"],current_token=ctx["token"],
          unchanged_build_controls=old,actual_engine_compilation=False,native_payload_acquired=False,
          runtime_qualified=False,routing_qualified=False,physical_acceptance=False,synthetic_control_report_transport=True)
        witness=dict(status="PASS",positive_count=4,refusal_count=29,engine_compiled=False,native_executed=False,
          physical_acceptance=False,synthetic_control_report_transport=True)
        for n,r in (("fixed-engine-controls.json",fixed),("engine-build-controls.json",old),("internal-witness-controls.json",witness)):
            (root/n).write_bytes(encoded(r))
        if index==0:
            assert c.control_evidence(root,ctx)
            provenance=[]
            for name,key,badvalue in (("fixed-engine-controls.json","current_source","b"*40),
              ("fixed-engine-controls.json","current_token","999-1"),
              ("fixed-engine-controls.json","actual_engine_compilation",True),
              ("engine-build-controls.json","positive_count",6)):
                target=root/name;original=target.read_bytes();bad=c.decode(original);bad[key]=badvalue
                target.write_bytes(encoded(bad))
                try:refuse("actual control record "+key,lambda:c.control_evidence(root,ctx),provenance)
                finally:target.write_bytes(original)
            assert len(provenance)==4
        if mode=="wrong_reservation":proof["tested_source"]="b"*40
        capture=io.StringIO();caught=None;result=None
        with contextlib.ExitStack()as stack:
            stack.enter_context(patch.dict(os.environ,env,clear=False))
            stack.enter_context(patch.object(h,"ROOT",root))
            stack.enter_context(patch.object(h.reservation,"wait",return_value=proof))
            stack.enter_context(patch.object(h.subprocess,"check_output",side_effect=transport.query))
            stack.enter_context(patch.object(h,"execute_command",side_effect=lambda *a,**k:original_command(*a,**k,runner=transport.runner)))
            stack.enter_context(patch.object(h.shutil,"disk_usage",return_value=SimpleNamespace(free=64*1024**3)))
            stack.enter_context(patch.object(h,"write",side_effect=transport.write))
            stack.enter_context(patch.object(c.old.os,"replace",side_effect=transport.replace))
            stack.enter_context(contextlib.redirect_stdout(capture))
            try:result=h.build()
            except BaseException as exc:caught=exc
        out=transport.work/"out";terminal=out/"host-result.json"
        if mode in ("save_failure","body_and_save"):
            lines=[x for x in capture.getvalue().splitlines()if x.startswith("ENGINE_BUILD_TERMINAL_FALLBACK ")]
            assert len(lines)==1
            report=json.loads(lines[0].split(" ",1)[1])["complete_unsaved_record"]
            assert any(n.startswith("host-result.json.")and n.endswith(".tmp")for n in report["available_outputs_after_save_failure"])
            assert caught is (transport.body_error if mode=="body_and_save"else transport.save_error)
        else:
            report=c.decode(terminal.read_bytes())
            if mode in ("body_failure","body_and_stop"):assert caught is transport.body_error
            elif mode=="create_progress_failure":assert caught is transport.progress_error
            elif mode=="wrong_reservation":
                assert isinstance(caught,ValueError)and not transport.calls
            else:assert caught is None
        assert not transport.exists and report["physical_acceptance"]is False
        assert report["runtime_qualified"]is False and report["qualified_engine"]is None
        if mode=="success":
            assert result==0 and report["status"]=="PASS_COMPILED_ENGINE_INTERFACE_ONLY"
            delta=c.decode((out/"source-derivation.json").read_bytes())
            assert set(delta["changed_paths"])=={c.ROUTER,c.FLEX}and delta["fixed_guard_reverse_byte_exact"]is True
            assert c.validate_projection(transport.work)
        else:
            assert report["status"]=="FAIL_ENGINE_BUILD"
        if mode in ("stop_failure","body_and_stop"):
            assert any(a[:2]==["docker","kill"]for a in transport.calls)
            assert any(x["action"]=="terminal-inspect"and x["completed"]for x in report["terminal_actions"])
        if mode!="wrong_reservation":
            assert "source-derivation.json"in report.get("available_outputs",report.get("available_outputs_after_save_failure",{}))
        cases.append(dict(mode=mode,status=report["status"],caught=None if caught is None else repr(caught),
          cleanup_confirmed=not transport.exists,synthetic_external_transport=True,
          actual_build_body_and_finally=True,real_native_compilation=False))
    return dict(status="PASS_ACTUAL_DERIVED_BUILD_LIFECYCLE_CONTROLS",cases=cases,count=len(cases),
      current_control_provenance_refusals=provenance)

def derivation_controls(root,base,enabled):
    source=base/"derivation";source.mkdir();out=base/"derivation-out";out.mkdir()
    for rel,snapshot in PRIMARY.items():
        target=source/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(c.secure_file(root,snapshot).read_bytes())
    def observed(path):
        return {rel:h.fingerprint(path/rel)for rel in PRIMARY}
    with patch.object(h,"ROOT",root),patch.object(h,"snapshot",side_effect=observed):
        before=observed(source);after=h.derive_sources(source,out,enabled)
    rows=[];proof=c.source_delta(before,after)
    assert proof["all_other_tracked_bytes_unchanged"]is True
    mutations=[]
    bad=copy.deepcopy(after);bad.pop(c.FLEX);mutations.append(("missing source",bad))
    bad=copy.deepcopy(after);bad["CMakeLists.txt"]["sha256"]="0"*64;mutations.append(("unrelated source delta",bad))
    bad=copy.deepcopy(after);bad[c.FLEX]=copy.deepcopy(before[c.FLEX]);mutations.append(("guard absent",bad))
    bad=copy.deepcopy(after);bad[c.ROUTER]["sha256"]="0"*64;mutations.append(("observer changed",bad))
    for name,bad in mutations:refuse(name,lambda bad=bad:c.source_delta(before,bad),rows)
    for destination in c.PROJECTION:
        work=base/("projection-"+destination.replace(".","-"));work.mkdir()
        with patch.object(h,"ROOT",root):h.project_inner(work)
        (work/destination).write_bytes(b"wrong projection")
        refuse("projection "+destination,lambda work=work:c.validate_projection(work),rows)
    original=c.secure_file(root,c.repair.SNAPSHOT).read_bytes()
    refuse("wrong FlexDR source",lambda:c.repair.derive(original+b"\n"),rows)
    return dict(status="PASS_REAL_SOURCE_DERIVATION_AND_PROJECTION",proof=proof,refusals=rows)

def publication_controls(root,base):
    cases=[]
    for index,mode in enumerate(("empty_terminal","missing_terminal","upload_failure","conflicting_asset","source_corruption","source_and_upload_failure")):
        env=environment(str(900+index));env["RUNNER_TEMP"]=str(base);ctx=c.context(env)
        capture=io.StringIO();uploads=[];assets=[];failure=OSError("synthetic upload failure")
        source_errors=[];real_method=c.method;changed=root/c.repair.SNAPSHOT;original=changed.read_bytes()
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
                uploads.append(p.name);assets.append(dict(name=p.name,size=len(raw),digest="sha256:"+c.digest(raw)))
                return SimpleNamespace(returncode=0)
            if mode=="conflicting_asset":
                assets.append(dict(name="inner-result.json",size=1,digest="sha256:"+"0"*64))
                proof["existing_assets"]=copy.deepcopy(assets)
            caught=None
            if mode in ("source_corruption","source_and_upload_failure"):
                changed.unlink();changed.write_bytes(original+b"\n")
            try:
                with patch.object(c,"method",side_effect=checked_method),patch.object(h.reservation,"wait",return_value=proof),patch.object(h.reservation.release,"api",side_effect=read),patch.object(h.subprocess,"run",side_effect=upload),contextlib.redirect_stdout(capture):
                    try:result=h.publish()
                    except BaseException as exc:caught=exc
            finally:
                if mode in ("source_corruption","source_and_upload_failure"):
                    changed.write_bytes(original)
            plan=c.decode((out/"direct-publication-plan.json").read_bytes())
            if mode=="upload_failure":assert caught is failure
            elif mode=="conflicting_asset":assert isinstance(caught,ValueError)
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
            else:assert caught is None and result==0
            assert "host-result.json"not in uploads
            with tarfile.open(work/"engine-evidence.tar.gz","r:gz")as archive:
                assert archive.extractfile("empty.stderr").read()==b""
                assert archive.extractfile("partial.stdout").read()==b"complete partial stdout\n"
                if mode!="missing_terminal":assert archive.extractfile("host-result.json").read()==b""
            row=next(x for x in plan["files"]if x["name"]=="host-result.json")
            assert row["disposition"]==("absent"if mode=="missing_terminal"else"archive_only_empty")
            cases.append(dict(mode=mode,complete_empty_archive_member=True,original_terminal_bytes_unchanged=True,
              zero_byte_direct_upload=False,synthetic_cloud_transport=True,error=None if caught is None else repr(caught)))
    return dict(status="PASS_ACTUAL_FAILURE_AND_EMPTY_PUBLICATION_CONTROLS",cases=cases,count=len(cases))

def controls():
    method=c.method(ROOT);ctx=c.context(os.environ)
    assert method["source_controls_authorized"]is True,"new source controls disabled"
    report=dict(status="RUNNING",current_source=ctx["source"],current_token=ctx["token"],
      actual_engine_compilation=False,native_payload_acquired=False,runtime_qualified=False,
      routing_qualified=False,physical_acceptance=False)
    # These old controls execute the same protected production helpers and explicit
    # synthetic boundaries. They do not grant this new method any native authority.
    report["unchanged_build_controls"]=old_checks.controls()
    with tempfile.TemporaryDirectory(prefix="fixed-engine-controls-",dir=ROOT)as temp:
        base=Path(temp);root=fixture_root(base/"root",method)
        report["authority"],enabled=source_controls(method,root)
        report["derivation"]=derivation_controls(root,base,enabled)
        report["lifecycle"]=lifecycle_controls(root,enabled,base)
        report["publication"]=publication_controls(root,base)
    report["status"]="PASS_FIXED_ENGINE_BUILD_SOURCE_CONTROLS"
    return report

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,required=True);args=parser.parse_args()
    report=None;primary=None
    try:report=controls()
    except BaseException as exc:
        primary=exc;report=dict(status="FAIL_FIXED_ENGINE_BUILD_SOURCE_CONTROLS",error=repr(exc),
          traceback=traceback.format_exc(),actual_engine_compilation=False,physical_acceptance=False)
    try:c.atomic_record(args.output,report)
    except BaseException:
        if primary is None:raise
        try:print(json.dumps(report,sort_keys=True),flush=True)
        except BaseException:pass
    if primary is not None:raise primary
    print(json.dumps(report,sort_keys=True))

if __name__=="__main__":main()
