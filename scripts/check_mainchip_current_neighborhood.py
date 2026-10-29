#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted synthetic acquisition guards; no native archive or CAD acquisition."""
import argparse,base64,copy,hashlib,io,json,os,tarfile,tempfile,zlib
from pathlib import Path
from unittest.mock import patch
import cloud_mainchip_current_neighborhood as w
def lifecycle_controls(ctx,proof,rel,ref):
    """Real host/inner paths; cloud, Docker and child process I/O are synthetic."""
    import contextlib,sys,types
    import mainchip_current_neighborhood_inner as inner
    done=[]
    def expect_exact(error,action):
        try:action()
        except BaseException as exc:assert exc is error,(type(exc),repr(exc),repr(error))
        else:raise AssertionError("primary exception was lost")
    with tempfile.TemporaryDirectory()as temp:
        base=Path(temp);serial=0
        def host_fixture(stack,mode):
            nonlocal serial
            serial+=1;root=base/str(serial);root.mkdir();repo=root/"repo";repo.mkdir()
            path="scripts/mainchip_current_neighborhood_inner.py"
            original=w.ROOT/path;target=repo/path;target.parent.mkdir();target.write_bytes(original.read_bytes())
            (repo/w.c.METHOD).write_bytes(b"{}")
            manifest=dict(schema="current-neighborhood-pins-v1",files={path:w.f.file_digest(target)})
            evidence=root/"evidence";evidence.mkdir();body_error=RuntimeError("synthetic transport primary")
            save_error=OSError("synthetic final save failure")
            copied_error=OSError("synthetic independent copy failure")
            data=b"synthetic database, not an ODB";pin=w.f.digest(data)
            def acquire(work,evidence):
                (work/"current-input.odb").write_bytes(data)
                for name,raw in (("a.json",b"{}"),("empty.stderr",b""),("z.json",b'{"last":true}')):
                    (work/"out"/name).write_bytes(raw)
                if mode in ("body-and-copy","body-and-cleanup"):raise body_error
            def restore(work,out):(work/"frozen-manifest.json").write_bytes(b"{}")
            def command(report,out,label,argv,timeout):
                report["commands"].append(dict(label=label,argv=argv,returncode=0,synthetic_io=True))
                if label=="image-inspect":return b"[{}]"
                if label=="current-owned-container":
                    (out/"current-readback-inner-result.json").write_bytes(w.f.encode(dict(
                        status="PASS_CURRENT_NEIGHBORHOOD_ENGINE_READBACK",terminal_errors=[],synthetic_io=True)))
                return b""
            def create(ctx,work,report,command,argv):report["creation_attempted"]=True;return "1"*64
            def cleanup(ctx,work,report,identity,attempted,inspect,command):
                if mode=="body-and-cleanup":raise RuntimeError("synthetic cleanup failure")
                report["container_terminal"]=dict(State=dict(Running=False,ExitCode=0,OOMKilled=False,Error=""))
            real_write=w.f.write_new
            def write(path,raw):
                if mode=="body-and-copy"and path==evidence/"native/a.json":raise copied_error
                return real_write(path,raw)
            atom_globals=w.c.finish_record.__globals__;real_atomic=atom_globals["atomic_record"]
            def atomic(path,value):
                if mode=="final-save"and Path(path).name=="result.json":raise save_error
                return real_atomic(path,value)
            for target,name,value in ((w,"ROOT",repo),(w,"CURRENT",pin),(w,"source_gate",lambda:manifest),
              (w,"acquire_current",acquire),(w.tail,"restore_prefix",restore),
              (w.c,"method",lambda root:{"protected":{}}),(w.c,"frozen_unchanged",lambda *a:None),
              (w.c,"validate_image",lambda *a:None),(w.c,"validate_container",lambda *a:None),
              (w.build,"execute_command",command),(w.build,"create_owned",create),(w.build,"cleanup_owned",cleanup),
              (w.f,"write_new",write),(w.f,"api",lambda path:rel if path.startswith("releases/")else ref),
              (w.subprocess,"check_output",lambda argv,**kw:ctx["source"] if argv[0]=="git"else b"[{}]"),
              (w.shutil,"disk_usage",lambda path:types.SimpleNamespace(free=30*1024**3))):
                stack.enter_context(patch.object(target,name,value))
            stack.enter_context(patch.dict(os.environ,{"RUNNER_TEMP":str(root)}))
            stack.enter_context(patch.dict(atom_globals,{"atomic_record":atomic}))
            return root,evidence,body_error,save_error
        for mode in ("success","body-and-copy","body-and-cleanup","final-save"):
            with contextlib.ExitStack()as stack:
                root,evidence,body_error,save_error=host_fixture(stack,mode)
                output=io.StringIO();stack.enter_context(patch("sys.stdout",output))
                if mode=="success":
                    result=w.perform(ctx,proof,evidence)
                    assert result["status"]=="PASS_CURRENT_SERIALIZED_NEIGHBORHOOD_READBACK_ONLY"
                else:
                    expect_exact(save_error if mode=="final-save"else body_error,lambda:w.perform(ctx,proof,evidence))
                work=root/(w.GROUP+"-"+ctx["token"])
                assert (work/"out/z.json").read_bytes()==b'{"last":true}'
                assert (evidence/"native/z.json").read_bytes()==b'{"last":true}'
                assert (evidence/"native/empty.stderr").read_bytes()==b""
                if mode=="body-and-copy":
                    r=w.f.decode((evidence/"result.json").read_bytes())
                    assert not r["output_preservation"]["complete"]and r["status"].startswith("FAIL_")
                    assert any(x["action"]=="preserve:a.json"for x in r["terminal_errors"])
                if mode=="body-and-cleanup":
                    r=w.f.decode((evidence/"result.json").read_bytes())
                    assert any(x["action"]=="owned-container-cleanup"for x in r["terminal_errors"])
                if mode=="final-save":
                    fallback=next(x for x in output.getvalue().splitlines()if x.startswith("ENGINE_BUILD_TERMINAL_FALLBACK "))
                    r=json.loads(fallback.split(" ",1)[1])["complete_unsaved_record"]
                    assert r["status"].startswith("FAIL_")and r["workspace_retained"]["path"]==str(work)
                    assert r["available_outputs_after_save_failure"]["native/z.json"]==w.f.file_digest(evidence/"native/z.json")
                if mode=="success":
                    owner=(work/"owner.json").read_bytes();(work/"owner.json").write_bytes(b"{}")
                    try:w.cleanup_preserved_workspace(ctx,evidence)
                    except AssertionError:pass
                    else:raise AssertionError("foreign workspace removed")
                    assert work.is_dir();(work/"owner.json").write_bytes(owner)
                    assert w.cleanup_preserved_workspace(ctx,evidence)["absent"]and not work.exists()
                    done.append("cleanup refuses wrong owner then removes exact owned workspace")
                done.append("actual perform "+mode)
        # Exercise actual CLI failure finalization, including encoder and emitter failure.
        for mode in ("save","fallback-encode","fallback-emit"):
            serial+=1;root=base/str(serial);root.mkdir();evidence=root/"main"
            reservation_path=root/"reservation.json";reservation_path.write_bytes(w.f.encode(proof))
            primary=RuntimeError("source integrity refusal")
            atom_globals=w.c.finish_record.__globals__;captured=io.StringIO()
            def fail_source():raise primary
            def fail_atomic(*a):raise OSError("failure record storage error")
            def fail_emit(*a):raise OSError("outer emitter error")
            with contextlib.ExitStack()as stack:
                stack.enter_context(patch.object(w,"source_gate",fail_source))
                acquisition=stack.enter_context(patch.object(w,"acquire_current",side_effect=AssertionError("acquisition after source refusal")))
                stack.enter_context(patch.object(w,"emit",fail_emit))
                stack.enter_context(patch.object(sys,"argv",["check","--output",str(evidence),"--reservation",str(reservation_path)]))
                stack.enter_context(patch.dict(atom_globals,{"atomic_record":fail_atomic}))
                if mode=="fallback-encode":
                    def dumps(*a,**k):raise ValueError("fallback encoding error")
                    stack.enter_context(patch.dict(atom_globals,{"json":types.SimpleNamespace(dumps=dumps)}))
                if mode=="fallback-emit":
                    class Broken(io.StringIO):
                        def write(self,*a):raise OSError("fallback output error")
                    stack.enter_context(patch("sys.stdout",Broken()))
                else:stack.enter_context(patch("sys.stdout",captured))
                expect_exact(primary,w.main)
                acquisition.assert_not_called()
                if mode=="save":
                    fallback=json.loads(next(x for x in captured.getvalue().splitlines()if x.startswith("ENGINE_BUILD_TERMINAL_FALLBACK ")).split(" ",1)[1])
                    assert fallback["complete_unsaved_record"]["primary_exception"]["error"]==repr(primary)
            done.append("actual main primary plus "+mode)
        # The actual inner run() is exercised with explicit fake subprocess I/O.
        for mode in ("zero","nonzero","timeout-stop-progress","spawn-progress","progress-only"):
            serial+=1;out=base/str(serial);out.mkdir();events=[]
            report=dict(commands=[],terminal_errors=[])
            primary=inner.subprocess.TimeoutExpired(["synthetic-child"],3)if mode=="timeout-stop-progress"else RuntimeError("synthetic spawn failure")
            class Child:
                pid=321;returncode=None
                def wait(self,timeout):
                    events.append(("wait",timeout))
                    if mode=="timeout-stop-progress"and self.returncode is None:raise primary
                    self.returncode=7 if mode=="nonzero"else 0;return self.returncode
                def poll(self):return self.returncode
            child=Child()
            def spawn(*a,**kw):
                assert kw["start_new_session"]is True
                if mode=="spawn-progress":raise primary
                return child
            def killpg(pid,sig):
                assert pid==child.pid;events.append(("signal",sig))
                if sig==inner.signal.SIGTERM:raise OSError("synthetic stop failure")
                child.returncode=-9
            real_write=inner.write
            def write(name,value):
                if mode in ("timeout-stop-progress","spawn-progress","progress-only"):raise OSError("synthetic progress save failure")
                return real_write(name,value)
            with patch.object(inner,"OUT",out),patch.object(inner.subprocess,"Popen",spawn),patch.object(inner.os,"killpg",killpg),patch.object(inner,"write",write):
                if mode in ("timeout-stop-progress","spawn-progress"):
                    expect_exact(primary,lambda:inner.run(report,"fixture",["synthetic-child"],3))
                elif mode in ("nonzero","progress-only"):
                    try:inner.run(report,"fixture",["synthetic-child"],3)
                    except ValueError as exc:
                        assert str(exc)==("fixture failed"if mode=="nonzero"else"fixture terminal errors")
                    else:raise AssertionError("inner failure admitted")
                else:inner.run(report,"fixture",["synthetic-child"],3)
            if mode=="timeout-stop-progress":
                assert ("signal",inner.signal.SIGTERM)in events and ("signal",inner.signal.SIGKILL)in events
                assert report["commands"][0]["returncode"]==-9
                assert {x["action"]for x in report["terminal_errors"]}>={"fixture:stop","fixture:wait-after-stop","fixture:progress"}
            if mode=="zero":
                assert not report["terminal_errors"]and report["commands"][0]["returncode"]==0
                assert (out/"current-readback-inner-progress.json").is_file()
            done.append("actual inner run "+mode)
    assert len(done)==13
    return done

def controls(ctx):
    w.source_gate();passed=[];refused=[]
    def reject(name,fn):
        try:fn()
        except (AssertionError,ValueError,KeyError,TypeError):refused.append(name)
        else:raise AssertionError("did not refuse "+name)
    env=dict(os.environ)
    for key,value in (("GITHUB_ACTIONS","false"),("GITHUB_RUN_ATTEMPT","2"),
                      ("GITHUB_REF","refs/heads/main"),("GITHUB_EVENT_NAME","push")):
        bad=dict(env);bad[key]=value;reject("context:"+key,lambda bad=bad:w.context(bad))
    tag="cloud-results-"+ctx["token"]+"-"+w.GROUP
    proof=dict(tag=tag,tested_source=ctx["source"],release_id=7,existing_assets=[],
      target_verified=True,assets_overwritten=False,externally_reserved=True,creation_attempted=False)
    rel=dict(id=7,tag_name=tag,target_commitish=ctx["source"],draft=False,prerelease=True,assets=[])
    ref=dict(ref="refs/tags/"+tag,object=dict(type="commit",sha=ctx["source"]))
    assert w.reservation(ctx,proof,rel,ref)["verified_before_acquisition"];passed.append("exact reservation")
    for key,value in (("tested_source","0"*40),("externally_reserved",False),
                      ("creation_attempted",True),("assets_overwritten",True),("existing_assets",[1])):
        bad=dict(proof);bad[key]=value;reject("reservation:"+key,lambda bad=bad:w.reservation(ctx,bad,rel,ref))
    with tempfile.TemporaryDirectory()as temp:
        root=Path(temp);serial=0
        data=b"synthetic current database bytes, never a native ODB"
        member=w.CURRENT_MEMBER;pin=w.f.digest(data)
        expected={member:pin,"other.json":w.f.digest(b"{}")}
        def archive(entries):
            nonlocal serial
            serial+=1;path=root/("case-"+str(serial)+".tgz")
            with tarfile.open(path,"w:gz")as t:
                for name,raw,kind in entries:
                    info=tarfile.TarInfo(name)
                    if kind=="link":info.type=tarfile.SYMTYPE;info.linkname="elsewhere";t.addfile(info)
                    else:info.size=len(raw);t.addfile(info,io.BytesIO(raw))
            return path
        good=[(member,data,"file"),("other.json",b"{}","file")]
        def select(entries,mapping=None):
            return w.select_database(archive(entries),expected if mapping is None else mapping,root/("input-"+str(serial)))
        with patch.object(w,"CURRENT",pin):
            got=select(good);assert got["full_archive_verified"]and got["full_members"]==expected;passed.append("complete stream")
            for name,entries in (
              ("missing",good[:1]),("duplicate",good+good[:1]),
              ("extra",good+[("extra",b"x","file")]),("wrong digest",[(member,b"x"*len(data),"file"),good[1]]),
              ("traversal",good+[("../escape",b"x","file")]),
              ("symlink",[(member,b"","link"),good[1]])):
                reject("archive:"+name,lambda entries=entries:select(entries))
            wrong=copy.deepcopy(expected);wrong[member]["sha256"]="0"*64
            reject("archive wrong selected map",lambda:select(good,wrong))
        evidence=root/"evidence";evidence.mkdir()
        (evidence/"report.json").write_bytes(b'{"accepted":false}\n')
        output=io.StringIO()
        with patch("sys.stdout",output):w.emit(evidence)
        lines=output.getvalue().splitlines()
        index=json.loads(lines[0].split(" ",1)[1]);assert index=={"report.json":w.f.file_digest(evidence/"report.json")}
        chunks=[json.loads(x.split(" ",1)[1])for x in lines[1:]]
        unpacked=zlib.decompress(b"".join(base64.b64decode(x["base64"])for x in chunks))
        assert unpacked==(evidence/"report.json").read_bytes();passed.append("complete compressed evidence")
        (evidence/"forbidden.odb").write_bytes(b"x")
        reject("native evidence refusal",lambda:w.emit(evidence))
    lifecycle=lifecycle_controls(ctx,proof,rel,ref)
    result=dict(status="PASS_CURRENT_NEIGHBORHOOD_SOURCE_CONTROLS",current_context=ctx,
      lifecycle=lifecycle,lifecycle_count=len(lifecycle),lifecycle_native_and_cloud_io_synthetic=True,
      positive=passed,refusals=refused,positive_count=len(passed),refusal_count=len(refused),
      all_archives_synthetic=True,native_archive_acquired=False,native_executed=False,
      physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    result=dict(status="FAIL_CURRENT_NEIGHBORHOOD_SOURCE_CONTROLS",terminal_errors=[],
        native_archive_acquired=False,native_executed=False,physical_acceptance=False)
    primary=None
    try:result.update(controls(w.context(os.environ)))
    except BaseException as exc:primary=exc
    finally:
        a.output.parent.mkdir(parents=True,exist_ok=True)
        w.c.finish_record(a.output,result,"FAIL_CURRENT_NEIGHBORHOOD_SOURCE_CONTROLS",primary)
    print(json.dumps(result,sort_keys=True))
if __name__=="__main__":main()
