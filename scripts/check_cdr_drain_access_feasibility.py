#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted source controls; native/cloud collaborators are explicitly synthetic."""
import argparse,base64,collections,copy,json,os,tempfile,traceback,types,zlib
from pathlib import Path
from unittest.mock import patch
import cloud_cdr_drain_access_feasibility as h
import cdr_drain_access_feasibility_native as n
import check_cdr_current_rc_contacts as inherited

class Point:
    def __init__(self,x,y):self.x=x;self.y=y
class Box:
    def __init__(self,*v):self.v=v
class Polygon:
    def __init__(self,box):self.box=box
    def inside(self,p):
        a,b,c,d=self.box.v;return a<=p.x<=c and b<=p.y<=d
class Region:
    def __init__(self,value):self.box=value.box if isinstance(value,Polygon)else value
    def __and__(self,other):
        a,b,c,d=self.box.v;e,f,g,i=other.box.v
        return types.SimpleNamespace(is_empty=lambda:max(a,e)>=min(c,g)or max(b,f)>=min(d,i))
FAKE=types.SimpleNamespace(Point=Point,Box=Box,Region=Region)

def emitted(out,emit_impl=None):
    if emit_impl is None:emit_impl=h.emit
    lines=[];index=emit_impl(out,lambda line,**kw:lines.append(line));parts=collections.defaultdict(list);ends={}
    for line in lines:
        marker,raw=line.split(" ",1);obj=h.decode(raw)
        if marker=="CDR_ACCESS_OVERLAY_CHUNK":parts[obj["name"]].append(obj)
        if marker=="CDR_ACCESS_OVERLAY_END":ends[obj["name"]]=obj
    assert set(index)==set(ends)
    for name,value in index.items():
        rows=parts[name];assert [r["index"]for r in rows]==list(range(len(rows)))
        raw=zlib.decompress(b"".join(base64.b64decode(r["data"])for r in rows))
        assert raw==(out/name).read_bytes()and h.frozen.fingerprint(raw)==value
    return index

def feasibility_controls():
    positives=[];refusals=[]
    def yes(name,fn):
        value=fn();positives.append(dict(name=name,evidence=value));return value
    def no(name,fn):
        try:fn()
        except Exception as exc:refusals.append(dict(name=name,error=repr(exc)));return
        raise AssertionError("missing feasibility refusal: "+name)
    cfg=h.decode((h.ROOT/h.CONFIG).read_bytes());auth=h.decode((h.ROOT/cfg["ancestry"]).read_bytes())
    for resistor in ("R2997","R12299"):
        rows=yes("actual_five_constructor_roots_"+resistor,lambda resistor=resistor:n.constructor_rows(auth,resistor))
        assert len(rows)==5
    a=[[[0,0],[10,0],[10,100],[0,100]]];b=[[[30,10],[40,10],[40,90],[30,90]]]
    measured=yes("parallel_gap_and_run",lambda:n.parallel_edge_measurements(a,b))
    assert min(r["gap_dbu"]for r in measured)==20
    assert any(r["gap_dbu"]==20 and r["parallel_run_dbu"]==80 for r in measured)
    assert yes("no_parallel_overlap",lambda:n.parallel_edge_measurements(a,[[[30,200],[40,200],[40,300],[30,300]]]))==[]
    same=yes("coincident_zero_gap_retained",lambda:n.parallel_edge_measurements(a,a))
    assert any(r["gap_dbu"]==0 and r["parallel_run_dbu"]==100 for r in same)
    enc=yes("signed_bounding_enclosure_not_legal",lambda:n.bounding_enclosure([0,0,100,100],[-1,20,90,110]))
    assert enc["left"]==-1 and enc["top"]==-10 and enc["legal_enclosure_proved"]is False
    assert yes("integer_box",lambda:n.integer_box([0,-10,20,10]))==[0,-10,20,10]
    def original_bodies():
        import ast
        old=ast.parse((h.ROOT/"scripts/cdr_current_access_overlay_native.py").read_text())
        new=ast.parse((h.ROOT/h.NATIVE).read_text())
        names=("parse_path","properties","stable_path","point_rows","candidates","polygon_record","raw_geometry","observe","native_controls")
        before={x.name:ast.dump(x,include_attributes=False)for x in old.body if isinstance(x,ast.FunctionDef)}
        after={x.name:ast.dump(x,include_attributes=False)for x in new.body if isinstance(x,ast.FunctionDef)}
        assert all(before[k]==after[k]for k in names)
        return dict(functions=list(names),unchanged=True)
    yes("unchanged_original_native_bodies",original_bodies)
    for value in ([0,0,True,10],[0,0,1.5,10],[1,0,0,10],[0,0,1]):
        no("invalid_box_"+repr(value),lambda value=value:n.integer_box(value))
    bad=copy.deepcopy(auth);bad["source"]="0"*40
    no("wrong_ancestry_source",lambda:n.constructor_rows(bad,"R2997"))
    bad=copy.deepcopy(auth);bad["run_id"]=1
    no("wrong_ancestry_run",lambda:n.constructor_rows(bad,"R2997"))
    for name,mut in (
      ("missing_root",lambda x:x.pop(next(k for k in x if k.startswith("constructor:")))),
      ("unknown_material",lambda x:next(v for k,v in x.items()if k.startswith("constructor:"))["record"].update(material_name_hex="7878")),
      ("footprint_claim",lambda x:next(v for k,v in x.items()if k.startswith("constructor:"))["record"].update(final_footprint_proved=True)),
      ("material_multiset",lambda x:next(v for k,v in x.items()if k.startswith("constructor:"))["record"].update(material_name_hex="6d6574616c31"))):
        bad=copy.deepcopy(auth);mut(bad["selected_native_record_projections"]["R2997"]["complete_ancestry_nodes"])
        no(name,lambda bad=bad:n.constructor_rows(bad,"R2997"))
    counts=dict(positive=len(positives),refusal=len(refusals));assert counts==dict(positive=8,refusal=10),counts
    return dict(status="PASS_DRAIN_ACCESS_SOURCE_CONTROLS",counts=counts,positives=positives,refusals=refusals,native_executed=False)


def controls(expected):
    positives=[];refusals=[];lifecycle=[]
    def yes(name,fn):value=fn();positives.append(dict(name=name,evidence=value));return value
    def no(name,fn,needle):
        try:fn()
        except Exception as exc:
            assert needle in str(exc),(name,repr(exc));refusals.append(dict(name=name,error=repr(exc)));return
        raise AssertionError("Missing refusal: "+name)
    config,old,data=yes("authentic_source_and_complete_capsule",lambda:h.source_guard(expected))
    positives[-1]["evidence"]=dict(members=len(data["full"]),selected=len(config["selected"]))
    actual=h.decode(h.frozen.regular(h.ROOT,config["incidence"]).read_bytes())
    for key in ("28","124"):
        rows=yes("actual_102_raw_points_"+key,lambda key=key:n.point_rows(actual["targets"][key]))
        assert len(rows)==102
        assert all(r["point_dbu"]==[int(v)*5 for v in r["source_record"]["tokens"][4:6]]for r in rows)
        positives[-1]["evidence"]=dict(count=102,raw_coordinates_exact=True)
    target=actual["targets"]["28"]
    for name,mut,needle in [
      ("duplicate_node",lambda x:x["nodes"].append(copy.deepcopy(x["nodes"][0])),"102 nodes"),
      ("missing_node",lambda x:x["nodes"].pop(),"102 nodes"),
      ("alias_loaded_node",lambda x:x["nodes"][0].update(loaded=x["nodes"][1]["loaded"]),"102 nodes"),
      ("raw_token_disagreement",lambda x:x["native_primitive_records"][0]["tokens"].__setitem__(4,"1"),"raw primitive tokens"),
      ("duplicate_rnode",lambda x:x["native_primitive_records"].append(copy.deepcopy(x["native_primitive_records"][0])),"unique current rnode"),
      ("missing_rnode",lambda x:x["native_primitive_records"].pop(0),"complete rnode")]:
        bad=copy.deepcopy(target);mut(bad);no(name,lambda bad=bad:n.point_rows(bad),needle)
    for value,needle in [("metal7","type zero"),("0.5","integer raw coordinates"),("nan","integer raw coordinates")]:
        bad=copy.deepcopy(target);row=bad["native_primitive_records"][0]
        row["tokens"][-1 if value=="metal7"else 4]=value
        row["raw"]=" ".join(row["tokens"])
        no("rnode_"+value,lambda bad=bad:n.point_rows(bad),needle)
    polys=[("metal",Polygon(Box(0,0,10,10))),("other-layer-via",Polygon(Box(0,0,10,10)))]
    def match(point,items):
        r=n.candidates(FAKE,point,items)
        assert r["resistor_layer_assigned"]is False and r["resistor_footprint_assigned"]is False
        return r
    zero=yes("zero_matches_retained",lambda:match([30,30],polys));assert zero["disposition"]=="NO_MATCH"
    one=yes("one_match_is_not_ownership",lambda:match([5,5],polys[:1]));assert one["disposition"]=="ONE_POINT_MATCH_NOT_OWNERSHIP"
    coincident=yes("coincident_distinct_layers_retained",lambda:match([5,5],polys));assert coincident["contains_or_boundary"]==["metal","other-layer-via"]
    edge=yes("boundary_is_explicit",lambda:match([0,5],polys));assert len(edge["contains_or_boundary"])==2
    near=yes("quantization_not_containment",lambda:match([11,5],polys));assert not near["contains_or_boundary"]and len(near["quantization_box_positive_area_overlap"])==2
    for point in ([True,0],[1.1,0],[0],[0,"0"]):
        no("invalid_point_"+repr(point),lambda point=point:n.candidates(FAKE,point,polys),"integer point")
    env=dict(GITHUB_ACTIONS="true",GITHUB_REPOSITORY=h.frozen.REPOSITORY,GITHUB_EVENT_NAME="workflow_dispatch",
      GITHUB_RUN_ATTEMPT="1",GITHUB_REF="refs/heads/"+h.BRANCH,GITHUB_SHA="a"*40,GITHUB_RUN_ID="123")
    ctx=yes("current_host_context",lambda:h.context(env))
    for key,value in [("GITHUB_ACTIONS","false"),("GITHUB_REPOSITORY","other/repo"),("GITHUB_EVENT_NAME","push"),
       ("GITHUB_RUN_ATTEMPT","2"),("GITHUB_REF","refs/heads/main"),("GITHUB_SHA","b"*39),("GITHUB_RUN_ID","0")]:
        bad=dict(env);bad[key]=value;no("context_"+key,lambda bad=bad:h.context(bad),"")
    no("wrong_manifest_hash",lambda:h.source_guard("0"*64),"source manifest hash")
    no("missing_manifest_hash",lambda:h.source_guard(""),"explicit source manifest hash")
    original_pin=h.pin
    def corrupt(path):
        value=original_pin(path)
        return dict(value,sha256="0"*64)if path.as_posix().endswith(h.NATIVE)else value
    with patch.object(h,"pin",corrupt):no("actual_source_pin_refusal",lambda:h.source_guard(expected),"source bytes")
    report=dict(status="PASS_CURRENT_ACCESS_OVERLAY_SOURCE_CONTROLS",passed=True,counts=h.COUNTS,
      current_context=dict(source=ctx["source"],run_id=ctx["run_id"],attempt=1,source_controls_only=True,native_executed=False),
      native_executed=False,physical_acceptance=False,feasibility_controls=dict(status="PASS_DRAIN_ACCESS_SOURCE_CONTROLS",counts=dict(positive=8,refusal=10),native_executed=False),original_archive_controls=dict(status="PASS_CURRENT_RC_CONTACT_SOURCE_CONTROLS",passed=True,counts=dict(positive=14,refusal=80,lifecycle=5),native_executed=False))
    yes("source_controls_binding",lambda:h.controls_binding(h.encode(report),ctx))
    for key,value in [("status","FAIL"),("passed",False),("counts",{}),("native_executed",True),("physical_acceptance",True)]:
        bad=copy.deepcopy(report);bad[key]=value;no("controls_"+key,lambda bad=bad:h.controls_binding(h.encode(bad),ctx),"")
    bad=copy.deepcopy(report);bad["current_context"]["source"]="b"*40
    no("wrong_controls_source",lambda:h.controls_binding(h.encode(bad),ctx),"same-source controls")
    for key,value in [("status","FAIL"),("counts",{}),("native_executed",True)]:
        bad=copy.deepcopy(report);bad["original_archive_controls"][key]=value
        no("inherited_controls_"+key,lambda bad=bad:h.controls_binding(h.encode(bad),ctx),"inherited archive controls")
    with tempfile.TemporaryDirectory(prefix="overlay-source-controls-")as directory:
        base=Path(directory);out=base/"streams";out.mkdir()
        for name,raw in [("empty.stderr",b""),("complete.stdout",b"all\x00bytes\xff"),("partial.json",b"{broken")]:
            (out/name).write_bytes(raw)
        yes("complete_zero_binary_malformed_emission",lambda:emitted(out))
        no("output_no_overwrite",lambda:h.run(ctx,{},b"",out,expected,base/"app"),"output no overwrite")
        # Save the real production emitter before patching h.emit; avoid recursive mocks.
        actual_emit=h.emit
        # Exercise actual run/finally publication paths, with native/cloud body explicitly synthetic.
        for mode in ("body","body_plus_emit","source_guard","terminal_save"):
            dest=base/mode;primary=RuntimeError("primary-"+mode);captured=[]
            def body(*args):
                target=args[3];(target/"empty.stderr").write_bytes(b"");(target/"native-raw.stdout").write_bytes(b"raw\x00\xff")
                if mode in ("body","body_plus_emit"):raise primary
                return {"synthetic":True}
            original_write=h.write
            def write(path,raw):
                if mode=="terminal_save"and path.name=="readback-result.json":raise primary
                return original_write(path,raw)
            def emit(path,*args):
                if mode=="body_plus_emit":raise OSError("secondary-emitter")
                captured.append(emitted(path,actual_emit))
            with patch.object(h,"perform",body),patch.object(h,"source_guard",side_effect=primary if mode=="source_guard"else None),patch.object(h,"write",write),patch.object(h,"emit",emit):
                try:h.run(ctx,{},b"",dest,expected,base/"app")
                except RuntimeError as exc:assert exc is primary
                else:raise AssertionError("primary failure lost")
            assert(dest/"empty.stderr").read_bytes()==b""and(dest/"native-raw.stdout").read_bytes()==b"raw\x00\xff"
            assert h.decode((dest/"readback-failure.json").read_bytes())["error"]["message"]==str(primary)
            expected_files={"empty.stderr","native-raw.stdout","readback-failure.json"}
            assert {p.name for p in dest.iterdir()}==expected_files
            if mode=="body_plus_emit":assert captured==[]
            else:
                assert len(captured)==1 and captured[0]=={name:h.pin(dest/name)for name in expected_files}
            lifecycle.append(dict(name=mode,actual_run_and_finally=True,primary_preserved=True,output_retained=True,
              complete_production_emission_verified=mode!="body_plus_emit",emission_injected_failure=mode=="body_plus_emit"))
        for broken in ("cleanup","stop","join"):
            events=[]
            def fail(which):
                events.append(which)
                if which==broken:raise RuntimeError(which)
            sup=types.SimpleNamespace(ACTIVE=None,stop_process=lambda p:fail("cleanup"),STOP=types.SimpleNamespace(set=lambda:fail("stop")))
            heart=types.SimpleNamespace(join=lambda **kw:fail("join"),is_alive=lambda:False)
            actions,errors=h.finish(sup,heart,{})
            assert events==["cleanup","stop","join"]and len(errors)==1 and len(actions)==3
            lifecycle.append(dict(name="finish_"+broken,all_independent_cleanup_attempted=True))
        for mode in ("success","body_and_cleanup","body_and_final_save","wrong_budget_event"):
            dest=base/("native_"+mode);dest.mkdir();app=base/("app_"+mode);app.write_bytes(b"synthetic app")
            cfg=copy.deepcopy(config);cfg["appimage"]["sha256"]=h.pin(app)["sha256"]
            primary=RuntimeError("native-body-primary");events=[]
            class Sup:
                TRACE=dest/"supervision"
                ACTIVE=None
                STOP=types.SimpleNamespace(set=lambda:events.append("stop"))
                interrupted=lambda *a:None
                heartbeat=lambda self:None
                def stop_process(self,p):
                    events.append("cleanup")
                    if mode=="body_and_cleanup":raise OSError("secondary-cleanup")
                def supervised(self,argv,label,**kw):
                    assert kw["seconds"]==1200 and kw["cwd"]==dest
                    raw=b"full synthetic stream"
                    (self.TRACE/(label+".stdout")).write_bytes(raw);(self.TRACE/(label+".stderr")).write_bytes(b"")
                    record=dict(argv=argv,minimum_available_kib=2097152,maximum_group_rss_kib=10485760,returncode=0,
                      supervision_failure=None,process_group_cleanup=dict(remaining_live=[]),
                      stdout_bytes=len(raw),stdout_sha256=h.frozen.fingerprint(raw)["sha256"],
                      stderr_bytes=0,stderr_sha256=h.frozen.fingerprint(b"")["sha256"])
                    (self.TRACE/(label+".command.json")).write_bytes(h.encode(record))
                    start=dict(event="command_start",label=label,argv=argv,timeout_seconds=1201 if mode=="wrong_budget_event"else 1200,
                      minimum_available_kib=2097152,maximum_group_rss_kib=10485760)
                    (self.TRACE/"events.jsonl").write_text(json.dumps(start)+"\n")
                    (dest/"native-api-controls.json").write_bytes(h.encode(dict(status="PASS_PINNED_PYA_SYNTHETIC_POINT_CONTROLS",positive=5,synthetic_geometry=True,real_target_geometry_qualified=False)))
                    (dest/"feasibility-native-controls.json").write_bytes(h.encode(dict(status="PASS_DRAIN_ACCESS_PINNED_PYA_SYNTHETIC_CONTROLS",positive=6,synthetic_geometry=True,real_geometry_feasible=False)))
                    (dest/"drain-access-feasibility.json").write_bytes(h.encode(dict(status="PASS_DRAIN_ACCESS_OBSERVATION_NOT_DRC_ACCEPTANCE",scope=h.FLAGS,targets={"28":{},"124":{}})))
                    (dest/"overlay.json").write_bytes(h.encode(dict(status="PASS_CURRENT_ACCESS_GEOMETRIC_OBSERVATION_NOT_EDGE_ATTRIBUTION",scope=h.FLAGS,drain_access_feasibility=h.pin(dest/"drain-access-feasibility.json"))))
                    if mode.startswith("body_"):raise primary
            original_write=h.write
            def final_write(path,raw):
                if mode=="body_and_final_save"and path.name=="native-lifecycle.json":raise OSError("secondary-save")
                return original_write(path,raw)
            fake_thread=types.SimpleNamespace(start=lambda:events.append("start"),join=lambda **kw:events.append("join"),is_alive=lambda:False)
            # Match signal.signal's real contract: it returns the replaced handler.
            # Both the original handlers and the installed supervisor handler are callable.
            signal_handlers={sig:(lambda *args:None)for sig in (h.signal.SIGINT,h.signal.SIGTERM)}
            original_handlers=dict(signal_handlers);returned_handlers=[];lifecycle_stdout=[]
            def signal_swap(sig,handler):
                replaced=signal_handlers[sig];signal_handlers[sig]=handler
                returned_handlers.append(replaced);return replaced
            with patch.object(h.runtime,"launcher",return_value=types.SimpleNamespace(probe=lambda *a:{"accepted":True})),patch.object(h.runtime,"supervisor",return_value=Sup()),patch.object(h,"source_guard",return_value=(cfg,None,None)),patch.object(h.threading,"Thread",return_value=fake_thread),patch.object(h.signal,"getsignal",side_effect=lambda sig:signal_handlers[sig]),patch.object(h.signal,"signal",side_effect=signal_swap),patch.object(h,"write",final_write),patch("builtins.print",side_effect=lambda line,**kw:lifecycle_stdout.append(line)):
                try:value=h.native_readback(cfg,base/"selected",dest,expected,app)
                except BaseException as exc:
                    if mode.startswith("body_"):assert exc is primary
                    else:assert mode=="wrong_budget_event"and "budget/resource event"in str(exc)
                else:assert mode=="success"and value==h.pin(dest/"overlay.json")
            assert "stop"in events and "join"in events and "cleanup"in events
            assert(dest/"supervision/access-overlay.stdout").read_bytes()==b"full synthetic stream"
            assert signal_handlers==original_handlers
            assert len(returned_handlers)==4 and all(callable(handler)for handler in returned_handlers)
            if mode=="body_and_final_save":
                assert not(dest/"native-lifecycle.json").exists()
                assert len(lifecycle_stdout)==1 and lifecycle_stdout[0].startswith("CDR_ACCESS_OVERLAY_UNSAVED_LIFECYCLE ")
                lifecycle_report=json.loads(lifecycle_stdout[0].split(" ",1)[1])
                assert lifecycle_report["primary_error"]==repr(primary)
            else:
                lifecycle_bytes=(dest/"native-lifecycle.json").read_bytes()
                lifecycle_report=h.decode(lifecycle_bytes)
                assert lifecycle_bytes==h.encode(lifecycle_report)
                assert lifecycle_stdout==[]
            restoration=[row for row in lifecycle_report["actions"]if row["action"].startswith("restore_signal_")]
            assert restoration==[dict(action="restore_signal_"+str(sig),completed=True,evidence=dict(signal=int(sig),restored=True))for sig in original_handlers]
            assert len(lifecycle_report["actions"])==5
            lifecycle.append(dict(name="actual_native_readback_"+mode,native_subprocess_and_cloud_explicitly_synthetic=True,complete_stream_retained=True,callable_signal_returns_exercised=True,prior_handlers_restored=True,complete_lifecycle_json_verified=True,lifecycle_fallback_verified=mode=="body_and_final_save"))
        finalizer=[]
        for name,has_primary,write_failure,stdout_failure in (
          ("primary_write",True,True,False),("primary_stdout",True,False,True),
          ("primary_dual",True,True,True),("write_only",False,True,False),("stdout_only",False,False,True)):
            path=base/("finalizer_"+name)/"report.json";lines=[]
            primary=RuntimeError("original-controls-error")if has_primary else None
            write_error=OSError("injected-final-report-write");stdout_error=BrokenPipeError("injected-final-report-stdout")
            report=dict(status="FAIL_SYNTHETIC_FINALIZER_FIXTURE",native_executed=False,error="original-controls-error")
            original_write=h.write
            def save(target,raw):
                if write_failure:raise write_error
                return original_write(target,raw)
            def writer(text,**kwargs):
                if stdout_failure:raise stdout_error
                lines.append(text)
            with patch.object(h,"write",save):
                try:finish_report(path,report,primary,writer)
                except BaseException as exc:assert exc is (primary if has_primary else write_error if write_failure else stdout_error)
                else:raise AssertionError("finalization error lost")
            if not write_failure:assert path.read_bytes()==h.encode(report)
            if not stdout_failure:assert lines==[h.encode(report).decode()]
            finalizer.append(dict(name=name,actual_finish_report=True,primary_preserved=has_primary,
              file_complete=not write_failure,stdout_complete=not stdout_failure))
        assert len(finalizer)==5
    inherited_result=inherited.controls()
    assert inherited_result["counts"]==dict(positive=14,refusal=80,lifecycle=5)
    extra=feasibility_controls()
    result=dict(feasibility_controls=extra,status="PASS_CURRENT_ACCESS_OVERLAY_SOURCE_CONTROLS",passed=True,
      counts=dict(positive=len(positives),refusal=len(refusals),lifecycle=len(lifecycle)),
      positives=positives,refusals=refusals,lifecycle=lifecycle,original_archive_controls=inherited_result,
      synthetic_geometry_collaborators=True,actual_pya_geometry_tests_deferred_to_reserved_readback=True,
      checker_finalization_cases=finalizer,checker_finalization_count=5,
      native_executed=False,physical_acceptance=False)
    assert result["counts"]==h.COUNTS,result["counts"]
    return result

def finish_report(output,report,primary=None,writer=print):
    """Try file and stdout independently; neither may replace an original error."""
    errors=[];raw=None
    try:raw=h.encode(report)
    except BaseException as exc:errors.append(exc)
    if raw is not None:
        try:
            output.parent.mkdir(parents=True,exist_ok=True);h.write(output,raw)
        except BaseException as exc:errors.append(exc)
        try:writer(raw.decode(),end="",flush=True)
        except BaseException as exc:errors.append(exc)
    else:
        try:writer("CDR_ACCESS_OVERLAY_CONTROL_ENCODING_FAILURE "+repr(dict(
          primary_error=None if primary is None else repr(primary),report=report,
          errors=[repr(e)for e in errors])),flush=True)
        except BaseException as exc:errors.append(exc)
    if primary is not None:raise primary
    if errors:raise errors[0]

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--pins-sha256",required=True);parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args();ctx=h.context(os.environ);primary=None
    current=dict(source=ctx["source"],run_id=ctx["run_id"],attempt=1,source_controls_only=True,native_executed=False)
    try:
        report=controls(args.pins_sha256);report["current_context"]=current
    except BaseException as exc:
        primary=exc
        report=dict(status="FAIL_CURRENT_ACCESS_OVERLAY_SOURCE_CONTROLS",passed=False,error=repr(exc),
          traceback=traceback.format_exc(),current_context=current,native_executed=False,physical_acceptance=False)
    finish_report(args.output,report,primary)
if __name__=="__main__":main()
