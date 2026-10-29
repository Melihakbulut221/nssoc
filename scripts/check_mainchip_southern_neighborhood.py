#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted synthetic acquisition guards; no native archive or CAD acquisition."""
import argparse,base64,copy,hashlib,io,json,os,tarfile,tempfile,zlib
from pathlib import Path
from unittest.mock import patch
import cloud_mainchip_southern_neighborhood as w
NAMESPACE_REPLACEMENTS=[('mainchip_current_neighborhood', 'mainchip_southern_neighborhood'), ('current-neighborhood', 'southern-neighborhood'), ('CURRENT_NEIGHBORHOOD', 'SOUTHERN_NEIGHBORHOOD'), ('CURRENT_SERIALIZED_NEIGHBORHOOD', 'SOUTHERN_SERIALIZED_NEIGHBORHOOD'), ('current-readback', 'southern-readback'), ('current-owned-container', 'southern-owned-container'), ('current-version', 'southern-version'), ('current-ldd', 'southern-ldd'), ('current-runtime-observed', 'southern-runtime-observed')]
ORIGINAL_SOURCES={'scripts/cloud_mainchip_current_neighborhood.py': {'bytes': 15721, 'sha256': 'be8cd2bd652cade446a9f5b676b7ac326a8ff0a37a487d4671686f92f53776ee'}, 'scripts/mainchip_current_neighborhood_inner.py': {'bytes': 5891, 'sha256': 'ab0fad9c7020b19ed47541c2ef95abf08b93f70a6bcdadd76a2b46bcbc4a1dee'}, 'scripts/mainchip_current_neighborhood_native.py': {'bytes': 13112, 'sha256': '8e4220fee60e69a95b0be7e3d148cf0316aad2c970877944005f0aa35aa50061'}, 'scripts/check_mainchip_current_neighborhood.py': {'bytes': 17183, 'sha256': '4c7a775cbd3a09a3ac876ec449cb5ab22c1a9ebd578fb48ee1b39b5845666714'}}
TRACK_API_EXPECTED={'commit': 'dcf36133a369abc8f3c5e5738cd4d82e4903c0e0', 'files': {'src/odb/include/odb/db.h': {'bytes': 272666, 'sha256': '142810acc2b0495b10c988b59e4d450e54dc27b2569687391588bfe1fad78bda'}, 'src/odb/src/db/dbTrackGrid.cpp': {'bytes': 9875, 'sha256': 'a9e6606ab63618334fb1cecb97fc3db15027afc1b3ba5eedb5415a7048b518c9'}, 'src/odb/src/swig/common/odb.i': {'bytes': 2787, 'sha256': '3083e86b4dec8286c00a6e0720755b115612ea626d2a1b62582f9fa23c5fcb34'}, 'src/odb/src/swig/python/dbtypes.i': {'bytes': 10337, 'sha256': '5ce9798bad0c1bce78b13d4dd0c934b90b02e41162f1641e78ccd3b08e9886db'}, 'src/odb/src/swig/common/dbtypes_common.i': {'bytes': 746, 'sha256': '294a71cf3ac647c76aca42b956bf60bc9325f0805246aa52c7df57f6bae970fb'}, 'src/odb/src/swig/common/containers.i': {'bytes': 3225, 'sha256': '91fb4249ac32658a8765ed0a2e2ad0b58ddc213cb1fce4829175785ee3ebb1fa'}}, 'api': 'dbBlock.getTrackGrids; dbTrackGrid.getNumGridPatternsX/Y; getGridPatternX/Y(i)', 'declared_outputs': ['origin,count,step', 'origin,count,step,first_mask,samemask'], 'overload_selection_not_assumed': True}
TRACK_MAIN_INSERT='        tracks=track_grid_readback(block)\n        save("track-grids.json",tracks)\n        result=collect_current(db,block)\n        result["track_grid_observation"]=dict(file=fingerprint(OUT/"track-grids.json"),\n            complete=tracks["complete"],status=tracks["status"],clearance_qualified=False)'
OLD_SCOPE='Actual current full-database census with selected all-layer geometry in a fixed 10um padded observation window and full three-net material. Rule radius and repair feasibility remain unqualified until exported rules are reviewed.'
NEW_SCOPE='Actual current full-database census with selected all-layer geometry in the southern-extended [937420,1773500,957620,1800560] DBU window and full three-net material. Track patterns are observed only when the pinned declared binding shape is available. Rule radius, legal track placement and repair feasibility remain unqualified.'

def lifecycle_controls(ctx,proof,rel,ref):
    """Real host/inner paths; cloud, Docker and child process I/O are synthetic."""
    import contextlib,sys,types
    import mainchip_southern_neighborhood_inner as inner
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
            path="scripts/mainchip_southern_neighborhood_inner.py"
            original=w.ROOT/path;target=repo/path;target.parent.mkdir();target.write_bytes(original.read_bytes())
            (repo/w.c.METHOD).write_bytes(b"{}")
            manifest=dict(schema="southern-neighborhood-pins-v1",files={path:w.f.file_digest(target)})
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
                if label=="southern-owned-container":
                    (out/"southern-readback-inner-result.json").write_bytes(w.f.encode(dict(
                        status="PASS_SOUTHERN_NEIGHBORHOOD_ENGINE_READBACK",terminal_errors=[],synthetic_io=True)))
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
                    assert result["status"]=="PASS_SOUTHERN_SERIALIZED_NEIGHBORHOOD_READBACK_ONLY"
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
                assert (out/"southern-readback-inner-progress.json").is_file()
            done.append("actual inner run "+mode)
    assert len(done)==13
    return done


def southern_derivation(sources=None):
    """Compare actual source text; never import the native odb entry point."""
    import ast
    sources={}if sources is None else sources
    def read(path):
        return sources[path]if path in sources else (w.ROOT/path).read_text()
    def fn(text,name):
        tree=ast.parse(text)
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name==name)
        return "\n".join(text.splitlines()[node.lineno-1:node.end_lineno])
    def rename(text):
        for old,new in NAMESPACE_REPLACEMENTS:text=text.replace(old,new)
        return text
    for path,pin in ORIGINAL_SOURCES.items():
        assert w.f.digest(read(path).encode())==pin,("qualified original source",path)
    host=read("scripts/cloud_mainchip_southern_neighborhood.py")
    inner=read("scripts/mainchip_southern_neighborhood_inner.py")
    native=read("scripts/mainchip_southern_neighborhood_native.py")
    checker=read("scripts/check_mainchip_southern_neighborhood.py")
    assert host==rename(read("scripts/cloud_mainchip_current_neighborhood.py")),"host derivation"
    assert inner==rename(read("scripts/mainchip_current_neighborhood_inner.py")),"inner derivation"
    assert fn(checker,"lifecycle_controls")==fn(rename(read(
        "scripts/check_mainchip_current_neighborhood.py")),"lifecycle_controls"),"13 lifecycle controls changed"
    old=rename(read("scripts/mainchip_current_neighborhood_native.py"))
    old_functions={n.name for n in ast.parse(old).body if isinstance(n,ast.FunctionDef)}
    assert {n.name for n in ast.parse(native).body if isinstance(n,ast.FunctionDef)}==old_functions|{
        "track_pattern","track_grid_readback"},"native function scope"
    for name in old_functions-{"main"}:assert fn(native,name)==fn(old,name),("native body",name)
    def literals(text):
        values={}
        for node in ast.parse(text).body:
            if not (isinstance(node,ast.Assign)and len(node.targets)==1
              and isinstance(node.targets[0],ast.Name)
              and node.targets[0].id in ("WINDOW","INPUT","TRACK_API")):continue
            name=node.targets[0].id;value=node.value
            if name=="INPUT":
                assert isinstance(value,ast.Call)and isinstance(value.func,ast.Name)
                assert value.func.id=="dict"and not value.args and {k.arg for k in value.keywords}=={"bytes","sha256"}
                values[name]={k.arg:ast.literal_eval(k.value)for k in value.keywords}
            else:values[name]=ast.literal_eval(value)
        return values
    values=literals(native)
    assert values["WINDOW"]==[937420,1773500,957620,1800560],"southern window"
    assert values["INPUT"]==literals(old)["INPUT"]==w.CURRENT,"current audited ODB"
    assert values["TRACK_API"]==TRACK_API_EXPECTED,"pinned track API"
    original_main=fn(old,"main")
    expected=original_main.replace("        result=collect_current(db,block)",TRACK_MAIN_INSERT)
    assert expected!=original_main
    expected=expected.replace(OLD_SCOPE,NEW_SCOPE)
    assert fn(native,"main")==expected,"native main derivation"
    expected_native=old.replace("WINDOW=[937420,1779520,957620,1800560]",
                               "WINDOW=[937420,1773500,957620,1800560]")
    expected_native=expected_native.replace("\ndef layers_for_window(db):",
        "\nTRACK_API="+repr(TRACK_API_EXPECTED)+"\n\ndef layers_for_window(db):")
    start=native.index("\ndef track_pattern(")-1;end=native.index("def main():",start)
    assert native[start:start+2]=="\n\n","new native functions boundary"
    new_functions=native[start:end]
    expected_native=expected_native.replace("\ndef main():",new_functions+"def main():")
    expected_native=expected_native.replace(original_main,expected)
    assert native==expected_native,"complete native derivation"
    namespace={}
    selected=[n for n in ast.parse(native).body if isinstance(n,ast.FunctionDef)
        and n.name in ("track_pattern","track_grid_readback")]
    namespace.update({k:values[k]for k in ("WINDOW","INPUT","TRACK_API")})
    # Only actual pure track functions are compiled in hosted controls.
    # No native module imports, source main(), ODB, geometry, or native assets.
    exec(compile(ast.Module(body=selected,type_ignores=[]),"<synthetic-track-functions>","exec"),namespace)
    return namespace

def southern_controls():
    import types
    positive=[];refused=[]
    ns=southern_derivation();positive.append("exact namespace derivation, widened window, unchanged census and lifecycle")
    def reject(name,action):
        try:action()
        except (AssertionError,ValueError,TypeError):refused.append(name)
        else:raise AssertionError("did not refuse "+name)
    parse=ns["track_pattern"];observe=ns["track_grid_readback"]
    assert parse([-100,3,20])["raw_output"]==[-100,3,20]
    positive.append("declared three-output list")
    assert parse((10,2,20,1,True))["same_mask"]is True
    positive.append("declared five-output tuple with bool")
    assert parse([10,1,0,0,0])["same_mask"]is False
    positive.append("declared int-output same-mask 0")
    class Layer:
        def __init__(self,name):self.name=name
        def getName(self):return self.name
    class Grid:
        def __init__(self,name,x,y):self.name=name;self.values={"X":x,"Y":y}
        def getTechLayer(self):return Layer(self.name)
        def getNumGridPatternsX(self):return len(self.values["X"])
        def getNumGridPatternsY(self):return len(self.values["Y"])
        def getGridPatternX(self,i):return self.values["X"][i]
        def getGridPatternY(self,i):return self.values["Y"][i]
    class Block:
        def __init__(self,grids):self.grids=grids
        def getDbUnitsPerMicron(self):return 1000
        def getTrackGrids(self):return self.grids
    grids=[Grid("Metal5",[[100,2,40]],[[200,2,80,0,False]]),
           Grid("TopMetal1",[[300,3,2280]],[[400,4,2280,1,1]])]
    complete=observe(Block(grids))
    assert complete["complete"]and complete["grid_count"]==2 and not complete["clearance_qualified"]
    assert complete["grids"][1]["patterns"]["Y"][0]["raw_output"]==[400,4,2280,1,1]
    assert complete["observation_window_dbu"]==[937420,1773500,957620,1800560]
    assert complete["source_database"]==w.CURRENT
    positive.append("actual reader complete synthetic two-layer patterns")
    unavailable=types.SimpleNamespace(getDbUnitsPerMicron=lambda:1000)
    row=observe(unavailable)
    assert not row["complete"]and not row["numeric_tracks_exported"]and row["grids"]==[]
    positive.append("unavailable block API emits no inferred numeric tracks")
    row=observe(Block([types.SimpleNamespace(getTechLayer=lambda:Layer("Metal5"))]))
    assert not row["complete"]and row["errors"]and row["grids"]==[]
    positive.append("unavailable pattern API emits availability only")
    row=observe(Block([grids[0],Grid("TopMetal1",[[1,2]],[])]))
    assert not row["complete"]and not row["numeric_tracks_exported"]and row["grids"]==[]
    positive.append("unsupported output shape discards partial numeric census")
    class Failing(Block):
        def getTrackGrids(self):raise RuntimeError("synthetic API error")
    row=observe(Failing([]))
    assert not row["complete"]and row["errors"][0]["error"]=="synthetic API error"and row["grids"]==[]
    positive.append("API read error retained without numeric inference")
    for name,value in [
      ("null",None),("short",[1,2]),("four outputs",[1,2,3,4]),("six outputs",[1,2,3,4,0,6]),
      ("boolean origin",[True,2,3]),("float count",[1,2.0,3]),("negative count",[1,-1,3]),
      ("negative step",[1,2,-3]),("zero multiple-track step",[1,2,0]),
      ("boolean mask",[1,2,3,True,False]),("negative mask",[1,2,3,-1,False]),
      ("nonboolean mask flag",[1,2,3,1,2]),("string output","1,2,3"),
      ("string mask flag",[1,2,3,1,"false"])]:
        reject("pattern:"+name,lambda value=value:parse(value))
    npath="scripts/mainchip_southern_neighborhood_native.py"
    hpath="scripts/cloud_mainchip_southern_neighborhood.py"
    native=(w.ROOT/npath).read_text();host=(w.ROOT/hpath).read_text()
    for name,path,text in [
      ("old window",npath,native.replace("1773500","1779520")),
      ("wrong current ODB",npath,native.replace(w.CURRENT["sha256"],"0"*64)),
      ("reduced census",npath,native.replace("143820","143819")),
      ("changed host lifecycle",hpath,host.replace("2700)","2699)"))]:
        assert text!=(native if path==npath else host)
        reject("source:"+name,lambda path=path,text=text:southern_derivation({path:text}))
    assert len(positive)==9 and len(refused)==18
    return dict(positive=positive,refusals=refused,positive_count=len(positive),refusal_count=len(refused),
        actual_native_function_bodies=True,native_imports_executed=False,
        all_track_objects_synthetic=True,native_track_api_qualified=False)

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
    extension=southern_controls()
    lifecycle=lifecycle_controls(ctx,proof,rel,ref)
    assert len(passed)==3 and len(refused)==17 and len(lifecycle)==13
    result=dict(status="PASS_SOUTHERN_NEIGHBORHOOD_SOURCE_CONTROLS",current_context=ctx,
      southern=extension,
      lifecycle=lifecycle,lifecycle_count=len(lifecycle),lifecycle_native_and_cloud_io_synthetic=True,
      positive=passed,refusals=refused,positive_count=len(passed),refusal_count=len(refused),
      all_archives_synthetic=True,native_archive_acquired=False,native_executed=False,
      physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    result=dict(status="FAIL_SOUTHERN_NEIGHBORHOOD_SOURCE_CONTROLS",terminal_errors=[],
        native_archive_acquired=False,native_executed=False,physical_acceptance=False)
    primary=None
    try:result.update(controls(w.context(os.environ)))
    except BaseException as exc:primary=exc
    finally:
        a.output.parent.mkdir(parents=True,exist_ok=True)
        w.c.finish_record(a.output,result,"FAIL_SOUTHERN_NEIGHBORHOOD_SOURCE_CONTROLS",primary)
    print(json.dumps(result,sort_keys=True))
if __name__=="__main__":main()
