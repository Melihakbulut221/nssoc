#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted-only adapter tests; every native/cloud boundary is explicitly synthetic."""
import argparse,ast,copy,json,os,subprocess,sys,tempfile,traceback
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import mainchip_bulk_postdrt_antenna as p
import mainchip_bulk_postdrt_antenna_inner as inner
import cloud_mainchip_bulk_postdrt_antenna as host
import check_mainchip_bulk_postdrt_antenna as prior

def actual_native_functions():
    path=Path(__file__).with_name("mainchip_bulk_postdrt_antenna_native.py")
    nodes=[n for n in ast.parse(path.read_bytes()).body
      if isinstance(n,ast.FunctionDef)and n.name in("phase","collect_checks")]
    p.require(len(nodes)==2,"two actual native audit functions")
    scope=dict(p=p,c=p.clock,Path=Path,json=json,ant=p.antenna,router=p.router,
      CATEGORY="NSSOC_ONE_BULK_POSTDRT_ANTENNA_DRC",
      save=lambda path,value:path.write_bytes(p.encode(value)))
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),"exec"),scope)
    return scope

def audit_case(phase,mutation):
    """Run actual native audit branches; only database/DRC/geometry I/O is synthetic."""
    with tempfile.TemporaryDirectory(prefix="bulk-audit-control-")as directory:
        root=Path(directory);work=root/"work";data=root/"out";work.mkdir();data.mkdir()
        before,inserted,protected=prior.fixture()
        for row in(before,inserted):row["clock_record_pins"]={name:{"synthetic":True}for name in protected}
        plan=p.admit_insertions(before,inserted,protected,[])
        restored=copy.deepcopy(inserted);restored["nets"]["data"]["wire"]["pin"]["sha256"]="b"*64
        fixed=copy.deepcopy(inserted)
        records=[]
        for name,row in inserted["nets"].items():
            terms="".join(" ( "+t[0]+" "+t[1]+" )"for t in row["identity"]["terminals"])
            records.append("- "+name+terms+" + USE "+row["identity"]["sigtype"]+
              "\n  + ROUTED Metal1 ( 0 0 ) ( 1 0 ) ;\n")
        raw=("VERSION 5.8 ;\nNETS "+str(len(records))+" ;\n"+"".join(records)+"END NETS\nEND DESIGN\n").encode()
        routed=raw.replace(b"- data ( ANTENNA_1573 A ) ( ANTENNA_NEW A ) + USE SIGNAL\n  + ROUTED Metal1 ( 0 0 ) ( 1 0 )",
          b"- data ( ANTENNA_1573 A ) ( ANTENNA_NEW A ) + USE SIGNAL\n  + ROUTED Metal1 ( 0 0 ) ( 2 0 )")
        p.require(routed!=raw,"actual fixture mutable DEF changed")
        fixed_raw,classes=p.fixed_plan(raw,["data"])
        for name in classes:
            fixed["nets"][name]["encoded"]["metadata"]="FIXED"
            fixed["nets"][name]["encoded"]["paths"]=["FIXED"]
        for name,value in(
          ("baseline-snapshot.json",before),("insertion-snapshot.json",inserted),
          ("insertion-plan.json",plan),("drt-original-classes.json",classes)):
            (data/name).write_bytes(p.encode(value))
        (work/"insertion.def").write_bytes(raw);(work/"fixed-expected.def").write_bytes(fixed_raw)
        (work/"restored-expected.def").write_bytes(routed)
        generated=fixed_raw if phase=="fixed-audit"else routed
        if mutation=="geometry":generated=generated.replace(b"( 1 0 )",b"( 9 0 )",1)
        if mutation=="class":generated=generated.replace(b"+ ROUTED",b"+ FIXED",1)
        def snapshot(source,target,names):
            target.write_bytes(generated);return copy.deepcopy(fixed if phase=="fixed-audit"else restored)
        gates=[]
        def original_gate(*args):
            gates.append("original-clock-native-API-stub")
            return {"result":{"clock_or_fixed_nets":1691,"all_source_clock_and_fixed_records_preserved":True}}
        scope=actual_native_functions()
        scope.update(snapshot=snapshot,n=SimpleNamespace(original_gate=original_gate),
          preserve_owned_routes=lambda *a:None,connectivity=lambda *a:{"synthetic_native_geometry":True},
          route_tcl=lambda *a:"# synthetic I/O boundary; renderer tested independently\n",
          check_tcl=lambda *a:"# synthetic I/O boundary; renderer tested independently\n")
        args=SimpleNamespace(phase=phase,work=work,out=data,input=work/"input.odb",
          donor=work/"donor.odb",environment=work/"environment.tcl",original_tcl=work/"original.tcl")
        error=None
        try:scope["phase"](args)
        except BaseException as exc:error=exc
        needle={"fixed-audit":"exact serialized fixed overlay","restored-audit":"restored complete DEF",
          "failure-restored-audit":"failed-route restoration bytes"}[phase]
        if mutation is None:p.require(error is None,"exact native audit fixture: "+repr(error))
        else:p.require(isinstance(error,AssertionError)and needle in str(error),"strict native byte refusal: "+repr(error))
        return dict(phase=phase,mutation=mutation,error=None if error is None else repr(error),
          original_clock_api_calls=gates,actual_native_function_executed_in_synthetic_fixture=True,native_executed=False)

def collect_case(mutation):
    with tempfile.TemporaryDirectory(prefix="bulk-collect-control-")as directory:
        work=Path(directory);data=work/"out";data.mkdir();raw=b"VERSION 5.8 ;\nNETS 1 ;\n- data + USE SIGNAL\n  + ROUTED Metal1 ( 0 0 ) ( 1 0 ) ;\nEND NETS\nEND DESIGN\n"
        (work/"baseline-check-before.def").write_bytes(raw)
        after=raw if mutation is None else raw.replace(b"( 1 0 )",b"( 9 0 )")if mutation=="geometry"else raw.replace(b"+ ROUTED",b"+ FIXED")
        (work/"baseline-check-after.def").write_bytes(after)
        (work/"baseline-counts.json").write_bytes(p.encode(dict(full_count=0,design_is_routed=1)))
        text="Net: data\n  Pin:   U/A (sg13g2_inv_1)\n    Layer: Via1\n"
        text+="      Partial area ratio: 1.00\n      Required ratio: 20.00 (Gate area) \n"
        text+="      Cumulative area ratio: 1.00\n      Required ratio: 20.00 (Cumulative area) \n"
        (work/"baseline-full-antenna.rpt").write_text(text)
        category=SimpleNamespace(writeJSON=lambda path:Path(path).write_text('{"synthetic":true}\n'))
        scope=actual_native_functions()
        scope.update(n=SimpleNamespace(load=lambda path:(object(),SimpleNamespace(findMarkerCategory=lambda name:category))),
          odb=SimpleNamespace(dbDatabase=SimpleNamespace(destroy=lambda db:None)),
          drc=SimpleNamespace(measure_report=lambda *args:dict(marker_count=0,synthetic_native_DRC=True)))
        error=None
        try:value=scope["collect_checks"]("baseline",work,data)
        except BaseException as exc:error=exc;value=None
        if mutation is None:p.require(error is None and value[0]["net_count"]==0,"actual collect exact DEF")
        else:p.require(isinstance(error,AssertionError)and "read-only checker DEF"in str(error),"collect byte refusal")
        return dict(phase="collect_checks",mutation=mutation,error=None if error is None else repr(error),
          actual_native_function_executed_in_synthetic_fixture=True,native_executed=False)

def lifecycle_case(failed=None,cleanup=None,missing_terminal=False,missing_metadata=False,write_failure=False,preserve_failure=False):
    with tempfile.TemporaryDirectory(prefix="bulk-adapter-control-")as directory:
        root=Path(directory);work=root/"work";data=root/"out";work.mkdir();data.mkdir()
        report=dict(commands=[],terminal_errors=[],**p.FLAGS);events=[];records={}
        primary=RuntimeError("primary:"+str(failed));cleanup_error=RuntimeError("cleanup:"+str(cleanup))
        def runner(report,label,argv,timeout):
            events.append(label);report["commands"].append(dict(label=label,argv=argv,requested_timeout_seconds=timeout,returncode=0))
            if label=="bulk-postdrt-repair"and not missing_metadata:(work/"insertion-after-shim.odb").write_bytes(b"synthetic state")
            if label=="bulk-postdrt-fixed-import":(work/"fixed.odb").write_bytes(b"synthetic fixed state")
            if label=="bulk-postdrt-"+str(failed):raise primary
            if label=="bulk-postdrt-"+str(cleanup):raise cleanup_error
            if "-python"in argv:
                phase=os.environ["NSSOC_BULK_PHASE"]
                if not(missing_terminal and phase=="prepare"):
                    (data/(phase+"-terminal.json")).write_bytes(p.encode(dict(phase=phase,complete=True,error=None,terminal_errors=[],**p.FLAGS)))
                if phase=="failure-restore-plan":
                    (data/"class-restoration-plan.json").write_bytes(p.encode(dict(failure_cleanup=True,used_pre_route_fallback=False,**p.FLAGS)))
        def writer(name,value):
            records[name]=copy.deepcopy(value)
            if write_failure and name=="cycle-progress.json":raise OSError("progress publication")
        def preserve():
            events.append("independent-preservation")
            if preserve_failure:raise OSError("preservation primary")
            return dict(complete=True,files={},synthetic_native_io=True)
        error=None
        try:value=inner.run_bound_cycle(report,work,data,runner,writer,preserve)
        except BaseException as exc:error=exc;value=None
        p.require(events[-1]=="independent-preservation","preservation attempted after all cleanup")
        p.require("cycle-terminal.json"in records,"terminal record retained")
        if failed:
            p.require(error is primary,"actual adapter original exception identity")
            actual=[x.removeprefix("bulk-postdrt-")for x in events if x.removeprefix("bulk-postdrt-")in p.PHASES]
            p.require(actual==list(p.PHASES[:p.PHASES.index(failed)+1]),"no actual phase continuation")
        elif cleanup or missing_terminal or missing_metadata or write_failure or preserve_failure:
            p.require(error is not None,"adapter failure never accepted")
        else:
            p.require(error is None and value["complete"]is True,"actual full adapter cycle")
            p.require([x.removeprefix("bulk-postdrt-")for x in events if x.removeprefix("bulk-postdrt-")in p.PHASES]==list(p.PHASES),"all actual callbacks")
        route=[r for r in report["commands"]if r["label"]=="bulk-postdrt-route"]
        repair=[r for r in report["commands"]if r["label"]=="bulk-postdrt-repair"]
        p.require(len(route)<=1 and len(repair)<=1,"no retry repair/route")
        if route:p.require(route[0]["requested_timeout_seconds"]==14400,"original route deadline")
        if failed=="route":
            p.require("bulk-postdrt-cleanup-class-plan"in events,"failed route class restoration attempted")
            p.require("bulk-postdrt-cleanup-antenna-metadata"in events,"independent antenna metadata check")
        return dict(failed=failed,cleanup=cleanup,missing_terminal=missing_terminal,missing_metadata=missing_metadata,
          write_failure=write_failure,preserve_failure=preserve_failure,error=None if error is None else repr(error),
          events=events,commands=report["commands"],records=records,synthetic_native_io=True,native_executed=False)

def publication_case(upload_failure=False,conflict=False):
    """Actual production tar/parts publisher with synthetic byte files and cloud transport."""
    with tempfile.TemporaryDirectory(prefix="bulk-publish-control-")as directory:
        root=Path(directory);work=root/"work";out=work/"out";evidence=root/"evidence"
        out.mkdir(parents=True);evidence.mkdir()
        ctx=dict(source="a"*40,run_id=77,attempt=1,token="77-1",name="nssoc-witness-build-77-1",group=host.GROUP)
        tag="cloud-results-77-1-"+host.GROUP;proof=dict(tag=tag,release_id=88)
        (work/"owner.json").write_bytes(host.f.encode(ctx))
        (out/"bulk-postdrt-empty.stderr").write_bytes(b"")
        (out/"bulk-postdrt-primary.stdout").write_bytes(b"actual synthetic partial stream\n")
        partial=out/"work/bulk-postdrt-antenna/route-partial.odb";partial.parent.mkdir(parents=True);partial.write_bytes(b"explicit synthetic ODB placeholder")
        assets=[];uploads=[]
        info=dict(id=88,tag_name=tag,target_commitish=ctx["source"],draft=False,prerelease=True,assets=assets)
        ref=dict(ref="refs/tags/"+tag,object=dict(type="commit",sha=ctx["source"]))
        def api(path):
            return copy.deepcopy(ref if path.startswith("git/ref/")else info)
        def upload(argv,**kwargs):
            path=Path(argv[4]);uploads.append(path.name)
            if upload_failure:return SimpleNamespace(returncode=7,stdout=b"transport stdout",stderr=b"transport failure")
            pin=host.f.file_digest(path)
            assets.append(dict(id=100+len(assets),name=path.name,size=pin["bytes"],digest="sha256:"+pin["sha256"]))
            return SimpleNamespace(returncode=0,stdout=b"synthetic upload",stderr=b"")
        if conflict:assets.append(dict(id=12,name="candidate-outputs.json",size=1,digest="sha256:"+"f"*64))
        error=None
        with patch.object(host.f,"api",api),patch.object(host.subprocess,"run",upload):
            try:value=host.publish_capsule(ctx,proof,work,out,evidence)
            except BaseException as exc:error=exc;value=None
        p.require(partial.is_file()and(out/"bulk-postdrt-empty.stderr").read_bytes()==b"","all partial native bytes retained")
        index=json.loads((work/"candidate-outputs.json").read_bytes())
        p.require(index["files"]["bulk-postdrt-empty.stderr"]==p.pin(b""),"empty archived member map")
        if upload_failure or conflict:
            p.require(error is not None,"publication failure refused")
            if conflict:p.require(uploads==[],"conflicting asset never overwritten")
        else:
            p.require(error is None and value["status"]=="COMPLETE_PERMANENT_NATIVE_CAPSULE","actual production publication")
            p.require(set(uploads)=={"candidate-outputs.json","candidate-parts.json","candidate-native.tar.gz.part000"},"no direct empty upload")
            import tarfile
            with tarfile.open(work/"candidate-native.tar.gz","r:gz")as archive:
                members={m.name:archive.extractfile(m).read()for m in archive}
            p.require(members["bulk-postdrt-empty.stderr"]==b"" and members["work/bulk-postdrt-antenna/route-partial.odb"]==partial.read_bytes(),"actual full archive retains empty and partial")
        return dict(upload_failure=upload_failure,conflict=conflict,uploads=uploads,error=None if error is None else repr(error),
          synthetic_native_bytes=True,synthetic_cloud_transport=True,native_executed=False)

def acquisition_case(change=None):
    import cloud_mainchip_full_antenna_readback as original
    from types import SimpleNamespace
    class BoundaryReached(RuntimeError):pass
    values={
      "actions/runs/"+str(p.PRODUCER["run"]):json.loads((p.ROOT/p.PROOF["run"]).read_bytes()),
      "actions/runs/"+str(p.PRODUCER["run"])+"/attempts/1/jobs?per_page=100":json.loads((p.ROOT/p.PROOF["jobs"]).read_bytes()),
      "releases/"+str(p.PRODUCER["release"]):json.loads((p.ROOT/p.PROOF["release"]).read_bytes()),
      "git/ref/tags/"+p.PRODUCER["tag"]:json.loads((p.ROOT/p.PROOF["ref"]).read_bytes())}
    if change=="source":values["actions/runs/"+str(p.PRODUCER["run"])]["head_sha"]="0"*40
    if change=="release":values["releases/"+str(p.PRODUCER["release"])]["id"]=1
    if change=="asset":values["releases/"+str(p.PRODUCER["release"])]["assets"].pop()
    events=[]
    def forbidden_native_download(name,work,out):
        events.append(name);raise BoundaryReached("synthetic acquisition boundary: "+name)
    with tempfile.TemporaryDirectory(prefix="bulk-acquire-control-")as directory:
        work=Path(directory)/"work";evidence=Path(directory)/"evidence";work.mkdir();evidence.mkdir()
        error=None
        with patch.object(host.f,"api",lambda path:copy.deepcopy(values[path])),patch.object(original,"download",forbidden_native_download):
            try:host.acquire_current(work,evidence)
            except BaseException as exc:error=exc
        if change is None:
            p.require(isinstance(error,BoundaryReached)and len(events)==1,"actual producer reaches only synthetic transport")
            p.require(len(list(evidence.glob("producer-*.json")))==5,"complete actual producer evidence before acquisition")
        else:p.require(isinstance(error,AssertionError)and not events,"invalid producer blocked before native transport")
        return dict(change=change,error=repr(error),transport_calls=events,actual_producer_metadata=True,
          synthetic_transport=True,native_payload_acquired=False)

def projection_controls():
    original=host.ROOT;manifest=host.source_gate();rows=[]
    with tempfile.TemporaryDirectory(prefix="bulk-projection-control-")as directory:
        root=Path(directory)
        for name in [*manifest["files"],host.MANIFEST]:
            target=root/name;target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(host.c.secure_file(original,name).read_bytes())
        with patch.object(host,"ROOT",root):
            host.source_gate();rows.append(dict(label="actual complete projected method and transitive sources",passed=True))
            path=root/host.PRIOR_METHOD;raw=path.read_bytes();path.unlink()
            try:host.source_gate()
            except (AssertionError,FileNotFoundError)as exc:rows.append(dict(label="missing historical method refused",error=repr(exc)))
            else:raise AssertionError("missing historical method accepted")
            path.write_bytes(raw)
            path=root/"scripts/mainchip_bulk_postdrt_antenna_native.py";raw=path.read_bytes()
            path.write_bytes(raw+b"\n# deliberate hosted source mutation\n")
            try:host.source_gate()
            except AssertionError as exc:rows.append(dict(label="native source mutation refused",error=repr(exc)))
            else:raise AssertionError("changed native source accepted")
            path.write_bytes(raw)
    return rows

def supervisor_case(code):
    import base64,contextlib,io
    with tempfile.TemporaryDirectory(prefix="bulk-supervised-control-")as directory:
        root=Path(directory);out=root/"out";trace=out/"trace";trace.mkdir(parents=True)
        sup=inner.supervision.supervisor();sup.OUT=out;sup.TRACE=trace
        report=dict(commands=[],terminal_errors=[]);console=io.StringIO();error=None
        argv=[sys.executable,"-I","-B","-c","raise SystemExit("+str(code)+")"]
        with patch.object(inner,"write",lambda name,value:(out/name).write_bytes(p.encode(value))),contextlib.redirect_stdout(console):
            try:inner.supervised_run(report,"python-"+str(code),argv,1200,sup,cwd=root)
            except BaseException as exc:error=exc
            finally:sup.stop_process(sup.ACTIVE);sup.STOP.set()
        p.require(report["commands"][0]["supervision_record"]["returncode"]==code,"actual child return code")
        if code==0:p.require(error is None and not report["terminal_errors"],"real zero child qualified command")
        else:p.require(error is not None,"real nonzero child refused")
        files={}
        for path in sorted(out.rglob("*")):
            if path.is_file():
                raw=path.read_bytes();files[path.relative_to(out).as_posix()]=dict(**p.pin(raw),base64=base64.b64encode(raw).decode())
        return dict(code=code,commands=report["commands"],error=None if error is None else repr(error),
          full_console_stdout=console.getvalue(),full_files=files,actual_python_child=True,native_CAD_executed=False)

def shutdown_case(failure=None):
    report=dict(terminal_errors=[]);events=[]
    def step(name):
        events.append(name)
        if name==failure:raise OSError("actual shutdown fixture: "+name)
    sup=SimpleNamespace(ACTIVE=object(),stop_process=lambda active:step("stop"),
      STOP=SimpleNamespace(set=lambda:step("event")))
    beat=SimpleNamespace(join=lambda timeout:step("join"),is_alive=lambda:failure=="alive")
    value=inner.stop_supervision(report,sup,beat)
    p.require(events==["stop","event","join"],"all independent owned shutdown attempts")
    p.require(value["complete"]is(failure is None),"shutdown failure remains incomplete")
    return dict(failure=failure,events=events,result=value,synthetic_process_io=True)

def controls():
    manifest=host.source_gate()
    disabled=copy.deepcopy(manifest);disabled["native_execution_enabled"]=False
    try:host.authorize_native(disabled)
    except AssertionError as exc:p.require("bulk native disabled"in str(exc),"disabled authority refusal")
    else:raise AssertionError("inert native authority unexpectedly active")
    projected=projection_controls()
    prior_result=prior.controls()
    p.require(prior_result["counts"]==dict(positive=10,refusal=49,lifecycle=20,rendered_tcl=9),"inherited source control census")
    audits=[audit_case(phase,mutation)for phase in("fixed-audit","restored-audit","failure-restored-audit")for mutation in(None,"geometry","class")]
    audits.extend(collect_case(mutation)for mutation in(None,"geometry","class"))
    cycles=[lifecycle_case()]
    cycles.extend(lifecycle_case(failed=name)for name in p.PHASES)
    cycles.extend([
      lifecycle_case(cleanup="cleanup-antenna-metadata"),
      lifecycle_case(failed="route",cleanup="cleanup-class-plan"),
      lifecycle_case(failed="route",preserve_failure=True),
      lifecycle_case(missing_terminal=True),lifecycle_case(missing_metadata=True),
      lifecycle_case(write_failure=True),lifecycle_case(preserve_failure=True)])
    supervised=[supervisor_case(code)for code in(0,7)]
    shutdown=[shutdown_case(failure)for failure in(None,"stop","event","alive")]
    acquisitions=[acquisition_case(change)for change in(None,"source","release","asset")]
    publications=[publication_case(),publication_case(upload_failure=True),publication_case(conflict=True)]
    return dict(status="PASS_BULK_POSTDRT_INTEGRATION_SOURCE_CONTROLS",
      inherited=prior_result,projection_fixtures=projected,native_audit_byte_fixtures=audits,bound_cycle_fixtures=cycles,publication_fixtures=publications,acquisition_fixtures=acquisitions,supervisor_fixtures=supervised,shutdown_fixtures=shutdown,
      counts=dict(inherited=prior_result["counts"],projection=len(projected),supervisor=len(supervised),shutdown=len(shutdown),acquisition=len(acquisitions),native_audit=len(audits),bound_cycle=len(cycles),publication=len(publications)),
      native_authorized=False,native_executed=False,**p.FLAGS)

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,required=True);args=parser.parse_args()
    primary=None
    try:
        ctx=host.context(os.environ);manifest=host.source_gate()
        p.require(manifest["source_controls_authorized"]is True,"hosted source controls disabled")
        result=controls()
        result["current_context"]=dict(source=ctx["source"],run_id=ctx["run_id"],attempt=1,source_controls_only=True,native_executed=False)
    except BaseException as exc:
        primary=exc;result=dict(status="FAIL_BULK_POSTDRT_INTEGRATION_SOURCE_CONTROLS",error=repr(exc),
          traceback=traceback.format_exc(),native_authorized=False,native_executed=False,**p.FLAGS)
    errors=[]
    for name,fn in(
      ("file",lambda:(args.output.parent.mkdir(parents=True,exist_ok=True),args.output.write_bytes(p.encode(result)))),
      ("stdout",lambda:print(p.encode(result).decode(),end=""))):
        try:fn()
        except BaseException as exc:errors.append(dict(operation=name,error=repr(exc)))
    if errors:
        try:print(p.encode(dict(errors=errors,primary=None if primary is None else repr(primary))).decode(),file=sys.stderr)
        except BaseException:pass
    if primary is not None:raise primary
    if errors:raise RuntimeError("integration report preservation: "+repr(errors))
if __name__=="__main__":main()
