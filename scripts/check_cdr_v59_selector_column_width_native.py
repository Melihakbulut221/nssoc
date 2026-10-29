#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted actual adapter/lifecycle controls; synthetic payloads are never native geometry."""
import argparse, contextlib, copy, hashlib, io, json, os, signal, subprocess, sys, tempfile, types
from pathlib import Path
from unittest import mock
import cdr_v59_selector_column_width_native as a
import cloud_cdr_v59_selector_column_width_native as w
import check_cdr_v59_tail_loaded_restore as fixture

ENV=dict(GITHUB_ACTIONS="true",RUNNER_ENVIRONMENT="github-hosted",GITHUB_REPOSITORY="Melihakbulut221/nssoc",
         GITHUB_RUN_ATTEMPT="1",GITHUB_RUN_ID="123456",GITHUB_SHA="a"*40)

def reject(label,fn,reason):
    try:fn()
    except AssertionError as e:
        assert e.args==(reason,),(label,e)
        return dict(label=label,reason=reason)
    raise AssertionError("Accepted negative: "+label)

def auth_controls(method):
    rows=[];positive=[]
    for enabled in (False,True):
        base=copy.deepcopy(method)
        for k in a.NATIVE:base[k]=enabled
        a.validate_authorizations(base);positive.append(dict(native=enabled))
        mutations=[("split",a.NATIVE[0],not enabled,"Split geometry authorization"),
          ("boolean",a.NATIVE[0],int(enabled),"Authorization must be boolean: "+a.NATIVE[0]),
          ("source","source_controls_authorized",False,"Source controls disabled"),
          ("method","inherited_width_method_sha256","0"*64,"Tested width method identity changed"),
          ("scope","scope","PHYSICAL_PASS","Geometry scope changed")]
        mutations += [(k,k,True,"Forbidden qualification or electrical flag")for k in a.FALSE]
        for label,key,value,reason in mutations:
            bad=copy.deepcopy(base);bad[key]=value
            assert json.dumps(bad,sort_keys=True)!=json.dumps(base,sort_keys=True)
            rows.append(reject(str(enabled)+"/"+label,lambda bad=bad:a.validate_authorizations(bad),reason))
    disabled=copy.deepcopy(method)
    for k in a.NATIVE:disabled[k]=False
    with mock.patch.object(a,"methods",return_value=disabled),mock.patch.dict(os.environ,ENV):
        rows.append(reject("disabled-execution",a.authorize,"Geometry stage disabled"))
    enabled=copy.deepcopy(method)
    for k in a.NATIVE:enabled[k]=True
    with mock.patch.object(a,"methods",return_value=enabled),mock.patch.dict(os.environ,dict(ENV,GITHUB_RUN_ATTEMPT="2")):
        rows.append(reject("retry",a.authorize,"First attempt required"))
    return dict(positive=positive,refusals=rows)

def origin_controls():
    g=a.generator;contract=a.width_contract()
    witness_path="docs/evidence/cdr-v59-tail-original-leaf-layout-20261026.json"
    witness=(a.ROOT/witness_path).read_bytes()
    assert hashlib.sha256(witness).hexdigest()=="5519863b12a9e0c86514daa78fb958199929e5b07fe0be95e07da8b882c2aa90"
    original_metadata=json.loads(witness)
    assert g.canonical(original_metadata["origin_translation_um"])=="[-0.0,-3.97]"
    assert contract["baseline_inventory"]["parent/inputs/sampler_cd/layout/pre-v59-result-cd_shunt.json"]==hashlib.sha256(witness).hexdigest()
    graph_raw=(a.ROOT/contract["qualified_graph_path"]).read_bytes()
    assert hashlib.sha256(graph_raw).hexdigest()==contract["qualified_graph_sha256"]
    generator_name="scripts/generate_cdr_v59_selector_column_width.py"
    generator_raw=(a.ROOT/generator_name).read_bytes()
    assert hashlib.sha256(generator_raw).hexdigest()=="30ccd03dac9a3054cce09e97517aa13b1c9ff97fd057bfe3c1d4efe4ae0433de"
    original_admitted=g.admitted;original_exact=g.exact
    positive=[];refusals=[];observed=None
    with tempfile.TemporaryDirectory()as tmp:
        root=Path(tmp);out=root/"hw/soc/out/origin-fixture";view=out/a.VIEW
        contract_path=root/"scripts/width-fixture.json";method_path=root/"scripts/method-fixture.json"
        graph_path=root/contract["qualified_graph_path"]
        graph_path.parent.mkdir(parents=True);(root/generator_name).parent.mkdir(parents=True,exist_ok=True)
        payloads={n:("EXPLICIT_SYNTHETIC_MEMBER_NOT_NATIVE:"+n).encode()for n in contract["baseline_inventory"]}
        payloads[g.CHILD_META]=witness
        assert len(payloads)==605
        def prepare(metadata=None,graph=None):
            for n,raw in payloads.items():
                p=view/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
            if metadata is not None:
                (view/g.CHILD_META).write_text(json.dumps(metadata,indent=2,allow_nan=True)+"\n")
            (root/generator_name).write_bytes(generator_raw)
            graph_path.write_bytes(graph_raw if graph is None else (json.dumps(graph,indent=2)+"\n").encode())
            c=copy.deepcopy(contract);c["baseline_inventory"]=g.frozen.files(view)
            c["qualified_graph_sha256"]=a.sha(graph_path)
            a.atomic(contract_path,c)
            m=dict(geometry_generation_authorized=True,native_execution_authorized=True,
                   simulation_authorized=False,electrical_accepted=False,
                   protected_sha256={generator_name:hashlib.sha256(generator_raw).hexdigest()})
            a.atomic(method_path,m)
            return c,m
        with contextlib.ExitStack()as stack:
            for obj,name,value in ((a,"ROOT",root),(a,"METHOD",method_path),(g,"ROOT",root),
                                   (g,"METHOD",method_path),(g,"CONTRACT",contract_path)):
                stack.enter_context(mock.patch.object(obj,name,value))
            stack.enter_context(mock.patch.dict(os.environ,ENV))
            c,m=prepare()
            # Exact frozen code, real 605-file hashing, real qualified graph, and
            # actual authenticated leaf JSON reproduce the pre-native failure.
            try:original_admitted(view)
            except AssertionError as error:
                assert error.args==("Changed child origin",)
                frames=[f.tb_frame.f_code for f in traceback_nodes(error)]
                assert original_admitted.__code__ in frames and original_exact.__code__ in frames
                regression=dict(error=repr(error),actual_admitted_and_exact_frames=True,
                                authenticated_metadata_sha256=hashlib.sha256(witness).hexdigest())
            else:raise AssertionError("Frozen origin rejection did not reproduce")
            fn=a.admitted_function()
            assert fn.__code__ is original_admitted.__code__ and fn.__defaults__ is original_admitted.__defaults__
            assert fn.__closure__ is original_admitted.__closure__ and fn.__kwdefaults__ is original_admitted.__kwdefaults__
            assert set(fn.__globals__)==set(original_admitted.__globals__)
            assert all(fn.__globals__[k]is v for k,v in original_admitted.__globals__.items()if k not in ("METHOD","exact"))
            assert fn.__globals__["METHOD"]==method_path and fn.__globals__["exact"]is a.origin_exact
            assert g.admitted is original_admitted and g.exact is original_exact
            def denied(label,kind,args,extra_frame=None):
                try:fn(view)
                except BaseException as error:
                    assert type(error)is kind and error.args==args,(label,type(error),error.args)
                    frames=[f.tb_frame.f_code for f in traceback_nodes(error)]
                    assert original_admitted.__code__ in frames,label
                    if extra_frame is not None:assert extra_frame in frames,label
                    refusals.append(dict(mode=label,error=repr(error),actual_admitted_frame=True))
                else:raise AssertionError("Accepted origin/admission negative: "+label)
            for label,x in (("signed_zero",-0.0),("float_zero",0.0),("integer_zero",0)):
                meta=copy.deepcopy(original_metadata);meta["origin_translation_um"]=[x,-3.97]
                c,m=prepare(meta)
                result=fn(view)
                assert result[0]==c and result[1]==contract["declared_rectangles"]
                assert result[2]["checks"]>0 and len(result[1])==26
                positive.append(dict(mode=label,actual_admitted_code=True,complete_synthetic_members=605,
                  real_qualified_graph=True,original_proposal_unchanged=True))
                if label=="signed_zero":
                    observed=a.origin_observation(out)
                    assert observed["child_metadata_sha256"]==a.sha(view/g.CHILD_META)
                    assert g.canonical(observed["origin_translation_um"])=="[-0.0,-3.97]"
                    assert observed["generator_sha256"]==hashlib.sha256(generator_raw).hexdigest()
                    assert observed["admitted_code_unchanged"]is True
                    (view/g.CHILD_META).write_bytes((view/g.CHILD_META).read_bytes()+b" ")
                    observation_refusal=reject("observed_metadata_hash",lambda:a.origin_observation(out),"Changed child metadata")
            bad_values=[("x_shift", [.005,-3.97]),("x_negative",[-.005,-3.97]),
              ("y_shift",[0,-3.975]),("y_sign",[0,3.97]),("x_bool",[False,-3.97]),
              ("y_bool",[0,True]),("x_string",["0",-3.97]),("y_string",[0,"-3.97"]),
              ("x_nan",[float("nan"),-3.97]),("y_inf",[0,float("inf")]),
              ("x_neg_inf",[float("-inf"),-3.97]),("x_null",[None,-3.97]),
              ("short",[0]),("extra",[0,-3.97,0]),("object",{"x":0,"y":-3.97}),
              ("huge_integer",[10**400,-3.97])]
            for label,value in bad_values:
                meta=copy.deepcopy(original_metadata);meta["origin_translation_um"]=value
                prepare(meta);denied(label,AssertionError,("Changed child origin",),a.origin_exact.__code__)
            prepare()
            with mock.patch.dict(os.environ,{"GITHUB_ACTIONS":"false"}):
                denied("hosted_gate",AssertionError,("Hosted-only generation",))
            c,m=prepare();m["geometry_generation_authorized"]=m["native_execution_authorized"]=False
            a.atomic(method_path,m);denied("method_gate",AssertionError,("Disabled geometry candidate",))
            prepare();(root/generator_name).write_bytes(generator_raw+b"\n# deliberate source mutant\n")
            denied("protected_source",AssertionError,(("Changed protected source",generator_name),))
            prepare();victim=next(n for n in payloads if n!=g.CHILD_META);(view/victim).unlink()
            denied("complete_inventory",AssertionError,("Incomplete current 605-file baseline",),original_exact.__code__)
            prepare();graph_path.write_bytes(graph_raw+b" ")
            denied("graph_hash",AssertionError,())
            graph=json.loads(graph_raw);graph["geometry"]["native_device_count"]=499
            prepare(graph=graph);denied("graph_census",AssertionError,(),g.validate_graph.__code__)
            graph=json.loads(graph_raw);cluster=contract["owner_partitions"]["sd"]["M_SE"]["native_cluster"]
            matches=[r for r in graph["geometry"]["native_net_coverage"]if r["native_cluster"]==cluster]
            assert len(matches)==1;matches[0]["native_cluster"]=-1
            prepare(graph=graph)
            denied("graph_partition",AssertionError,("Changed complete native owner partition",),original_exact.__code__)
            meta=copy.deepcopy(original_metadata);del meta["origin_translation_um"]
            prepare(meta);denied("missing_metadata_field",KeyError,("origin_translation_um",))
            meta=copy.deepcopy(original_metadata);row=next(r for r in meta["routes"]if r["net"]=="M_SE")
            row["escape_lane_um"]+=.005;prepare(meta)
            denied("selected_route",AssertionError,("Changed selected source routes",),g.boxes.__code__)
            # Numeric relaxation must not escape into any other frozen comparator.
            for label,value,expected in (("other_int_float",0,0.0),("other_boolean",False,0)):
                reason="Unrelated exact comparison"
                try:a.origin_exact(value,expected,reason)
                except AssertionError as error:
                    assert error.args==(reason,)
                    assert original_exact.__code__ in [f.tb_frame.f_code for f in traceback_nodes(error)]
                    refusals.append(dict(mode=label,error=repr(error),original_exact_frame=True))
                else:raise AssertionError("General canonical comparison was relaxed")
            prepare();assert fn(view)[1]==contract["declared_rectangles"]
    assert g.admitted is original_admitted and g.exact is original_exact
    assert len(positive)==3 and len(refusals)==27
    return dict(positive=positive,refusals=refusals,old_rejection=regression,
                observation=observed,observation_refusal=observation_refusal,
                synthetic_inventory_not_actual_GDS=True,native_executed=False)

def binding_controls():
    rows=[]
    for fail in (False,True):
        primary=RuntimeError("actual generator adapter collaborator");seen=[]
        previous=(a.generator.METHOD,a.generator.admitted,a.generator.exact)
        def run(source,out):
            seen.append((source,out,a.generator.METHOD))
            assert a.generator.METHOD==a.METHOD
            assert a.generator.admitted is not previous[1]
            assert a.generator.admitted.__code__ is previous[1].__code__
            assert a.generator.admitted.__globals__["exact"] is a.origin_exact
            assert a.generator.exact is previous[2]
            if fail:raise primary
            return {"explicit_synthetic_generation":True}
        with tempfile.TemporaryDirectory()as tmp, mock.patch.object(a,"authorize",return_value={}),\
             mock.patch.object(a,"validate_view",return_value={}),mock.patch.object(a.generator,"run",side_effect=run):
            root=Path(tmp);caught=None
            try:r=a.generate(root)
            except BaseException as e:caught=e
            assert len(seen)==1 and seen[0][:2]==(root/a.VIEW,root/"candidate")
            assert (a.generator.METHOD,a.generator.admitted,a.generator.exact)==previous
            if fail:assert caught is primary
            else:assert caught is None and r=={"explicit_synthetic_generation":True}
        rows.append(dict(failed_body=fail,method_global_restored=True,admitted_global_restored=True,original_exact_unchanged=True))
    return rows

def restore_controls(observation):
    actual=a.loaded.descriptor();a.loaded.snapshots()
    original={n:a.regular(a.ROOT,s["path"]).read_bytes()for n,s in actual["actual_fresh_RC"]["snapshots"].items()}
    results=[]
    for mode in ("preparation_return","unselected_hash"):
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp);c,s,repo,responses,payloads,unselected,planes=fixture.fixture(root,actual,original,mode)
            out=root/"out";out.mkdir();calls=[];gates=[]
            wc=copy.deepcopy(a.width_contract())
            wc["baseline_inventory"]={n[len("canonical-current-view/"):]:h for n,h in c["actual_fresh_RC"]["expected_files"].items()
                                      if n.startswith("canonical-current-view/")}
            assert len(wc["baseline_inventory"])==605
            def api(path):calls.append(path);return copy.deepcopy(responses[path])
            def fetch(url,digest,path):
                raw=payloads[url];assert hashlib.sha256(raw).hexdigest()==digest;path.write_bytes(raw)
            def gate():gates.append(True);return {}
            with mock.patch.object(a,"authorize",side_effect=gate),mock.patch.object(a,"width_contract",return_value=wc),\
                 mock.patch.object(a,"origin_observation",return_value=observation),\
                 mock.patch.object(a.loaded,"ROOT",repo),mock.patch.object(a.loaded,"descriptor",return_value=c),\
                 mock.patch.object(a.loaded,"snapshots",return_value=s),mock.patch.object(a.loaded,"fetch",side_effect=fetch),\
                 mock.patch.object(a.loaded.release,"api",side_effect=api),\
                 mock.patch.object(a.loaded,"authorize",side_effect=AssertionError("Old authorization must not be called")):
                caught=None
                try:r=a.restore(out)
                except BaseException as e:caught=e
            assert len(gates)==2 and len(calls)==4
            if mode=="unselected_hash":
                assert type(caught)is AssertionError and caught.args==(unselected,)
                assert any(f.tb_frame.f_code.co_name=="exact_extract"for f in traceback_nodes(caught))
            else:
                assert caught is None,repr(caught)
                assert r["view"]["full_capsule_members"]==3823 and r["view"]["view"]["files"]==605
                assert r["inherited_restore_code_unchanged"]is True and r["historical_authorization_borrowed"]is False
                assert a.read(out/"restore.json")==r and r["origin_admission"]==observation
            results.append(dict(mode=mode,full3823_synthetic_archive=True,view605=True,
                                actual_restore_and_extract=True,historical_gate_called=False,
                                synthetic_origin_observation_collaborator=True))
    return results

def traceback_nodes(error):
    tb=error.__traceback__
    while tb is not None:
        yield tb;tb=tb.tb_next

def lifecycle_controls(method):
    modes=("clean","body","process_stop","heartbeat_stop","join","source","inventory",
           "save","body_cleanup","body_save","save_encode","save_emit")
    rows=[]
    for mode in modes:
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp);out=root/"out";transport=root/"transport";events=[];state={"body":False}
            body_error=RuntimeError("body-primary");stop_error=RuntimeError("owned-stop")
            beat_error=RuntimeError("heartbeat-stop");join_error=RuntimeError("heartbeat-join")
            save_error=OSError("atomic-replace");source_error=RuntimeError("terminal-source")
            inv_error=RuntimeError("terminal-inventory")
            class Stop:
                def set(self):
                    events.append("stop")
                    if mode in ("heartbeat_stop","body_cleanup"):raise beat_error
            class Owned:
                ACTIVE=None;STOP=Stop();TRACE=out/"supervision"
                def interrupted(self,*args):raise RuntimeError("signal")
                def heartbeat(self):pass
                def stop_process(self,active):
                    events.append("process")
                    if mode in ("process_stop","body_cleanup"):raise stop_error
                    return dict(remaining_live=[])
                def sample(self,label):events.append("sample");return dict(label=label)
            owned=Owned()
            class Beat:
                def __init__(self,**kwargs):pass
                def start(self):events.append("start")
                def join(self,timeout):
                    events.append("join")
                    if mode=="join":raise join_error
                def is_alive(self):return False
            def body(result,supervisor,m):
                assert supervisor is owned
                state["body"]=True;events.append("body")
                (out/"partial.txt").write_text("ACTUAL_SYNTHETIC_PARTIAL")
                if mode in ("body","body_cleanup","body_save"):raise body_error
                result.update(status=w.PASS,generation_started=True,generation_and_serialized_reread_complete=True)
            def methods():
                events.append("source")
                if state["body"]and mode=="source":raise source_error
                return method
            real_inventory=w.inventory;real_replace=a.os.replace;real_dumps=json.dumps
            def inv(path):
                events.append("inventory")
                if state["body"]and mode=="inventory":raise inv_error
                return real_inventory(path)
            def replace(src,dst):
                if state["body"]and mode in ("save","body_save","save_encode","save_emit")and Path(dst).name=="result.json":
                    assert Path(src).is_file()
                    raise save_error
                return real_replace(src,dst)
            stream=io.StringIO();handlers={sig:signal.getsignal(sig)for sig in (signal.SIGINT,signal.SIGTERM)}
            with contextlib.ExitStack()as stack:
                for obj,name,value in ((w,"ROOT",root),(w,"OUT",out),(w,"TRANSPORT",transport)):
                    stack.enter_context(mock.patch.object(obj,name,value))
                stack.enter_context(mock.patch.dict(os.environ,ENV))
                stack.enter_context(mock.patch.object(a,"authorize",return_value=method))
                stack.enter_context(mock.patch.object(a,"methods",side_effect=methods))
                stack.enter_context(mock.patch.object(w,"storage",return_value={}))
                stack.enter_context(mock.patch.object(w.runtime,"supervisor",return_value=owned))
                stack.enter_context(mock.patch.object(w.threading,"Thread",Beat))
                stack.enter_context(mock.patch.object(w,"run",side_effect=body))
                stack.enter_context(mock.patch.object(w,"inventory",side_effect=inv))
                stack.enter_context(mock.patch.object(a.os,"replace",side_effect=replace))
                stack.enter_context(contextlib.redirect_stderr(stream))
                if mode=="save_encode":
                    stack.enter_context(mock.patch.object(w.json,"dumps",side_effect=ValueError("fallback-encode")))
                if mode=="save_emit":
                    stack.enter_context(mock.patch("builtins.print",side_effect=OSError("fallback-emit")))
                caught=None
                try:returned=w.main_run({})
                except BaseException as e:caught=e
            assert state["body"]and all(x in events for x in ("process","stop","join","sample","source","inventory")),(mode,events)
            assert all(signal.getsignal(sig)==handler for sig,handler in handlers.items()),mode
            if mode=="clean":
                assert caught is None and returned["status"]==w.PASS
                saved=a.read(out/"result.json")
                assert saved["terminal_finalization_complete"]is True
            elif mode.startswith("body"):assert caught is body_error,(mode,caught)
            else:
                expected={"process_stop":stop_error,"heartbeat_stop":beat_error,"join":join_error,
                          "source":source_error,"inventory":inv_error}.get(mode,save_error)
                assert caught is expected,(mode,caught)
            if mode in ("save","body_save"):
                fallback=json.loads(stream.getvalue())["unsaved_geometry_terminal"]
                assert fallback["outputs"]=={n:h for n,h in real_inventory(out).items()if n!="result.json"}
                assert any(n.endswith(".incomplete")for n in fallback["outputs"])
                assert fallback["generation_and_serialized_reread_complete"]is False
                assert any(f.tb_frame.f_code.co_name=="atomic"for f in traceback_nodes(save_error))
            elif mode not in ("save_encode","save_emit"):
                saved=a.read(out/"result.json")
                assert (saved["status"]==w.PASS)==(mode=="clean")
                if mode!="inventory":
                    assert saved["outputs"]=={n:h for n,h in real_inventory(out).items()if n!="result.json"}
            rows.append(dict(mode=mode,body_reached=True,all_cleanup_attempted=True,real_signal_restore=True,
                             original_exception_identity=True,synthetic_owned_process=True))
    return rows

def command_controls():
    rows=[]
    for mode in ("clean","argv","stream","returncode","cleanup","body_and_missing"):
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp);out=root/"out";out.mkdir();trace=out/"trace";trace.mkdir()
            label="generate26-and-serialized-reread";argv=["synthetic-engine","python","generate"];primary=RuntimeError("supervised-primary")
            def supervised(args,label,seconds,cwd):
                assert seconds==1800 and args==argv
                if mode=="body_and_missing":raise primary
                raw=b"SYNTHETIC COMPLETE STREAM"
                record=dict(label=label,argv=list(args),returncode=0,supervision_failure=None,process_group_cleanup={"remaining_live":[]})
                for stream in ("stdout","stderr"):
                    (trace/(label+"."+stream)).write_bytes(raw)
                    record[stream+"_bytes"]=len(raw);record[stream+"_sha256"]=hashlib.sha256(raw).hexdigest()
                if mode=="argv":record["argv"]=["other"]
                if mode=="stream":record["stdout_sha256"]="0"*64
                if mode=="returncode":record["returncode"]=7
                if mode=="cleanup":record["process_group_cleanup"]["remaining_live"]=[123]
                a.atomic(trace/(label+".command.json"),record)
            owned=types.SimpleNamespace(TRACE=trace,supervised=supervised)
            result={"commands":[]}
            with mock.patch.object(w,"ROOT",root),mock.patch.object(w,"OUT",out):
                caught=None
                try:w.execute(owned,result,argv,label,True)
                except BaseException as e:caught=e
            if mode=="clean":assert caught is None and len(result["commands"])==1
            elif mode=="body_and_missing":assert caught is primary
            else:assert type(caught)is AssertionError,(mode,caught)
            assert a.read(out/"result.json")==result
            rows.append(dict(mode=mode,actual_execute=True))
    return rows

def publication_controls(observation):
    rows=[]
    for mode in ("synthetic_success","origin_join","missing","malformed","nonobject","false_success","source_failure","upload","upload_save","save_encode","save_emit"):
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp);out=root/"out";out.mkdir();transport=root/"transport"
            (out/"partial.raw").write_bytes(b"EXACT PARTIAL BYTES")
            driver_log=root/"driver.log";driver_log.write_bytes(b"EXACT DRIVER STDOUT STDERR AND FALLBACK ENVELOPE")
            if mode=="malformed":(out/"result.json").write_bytes(b'{"truncated":')
            if mode=="nonobject":(out/"result.json").write_text("[]")
            if mode=="false_success":a.atomic(out/"result.json",{"status":w.PASS})
            synthetic_candidate={"explicit_synthetic_native_validation":True}
            if mode in ("synthetic_success","origin_join"):
                with mock.patch.dict(os.environ,ENV):r=w.initial({})
                r.update(status=w.PASS,generation_started=True,
                  generation_and_serialized_reread_complete=True,terminal_finalization_complete=True,
                  candidate=synthetic_candidate,commands=[dict(label=label,returncode=0,supervision_failure=None,
                  process_group_cleanup={"remaining_live":[]})for label in w.BUDGETS])
                smoke=dict(accepted=True,**{k:a.APP_SHA for k in ("expected_appimage_sha256","appimage_before_sha256","appimage_after_sha256")})
                a.atomic(out/"runtime-smoke/result.json",smoke);r["runtime_smoke"]=smoke
                a.atomic(out/"restore.json",{"explicit_synthetic_restore":True,"origin_admission":observation})
                r["restore"]=a.read(out/"restore.json")
                if mode=="origin_join":
                    changed=copy.deepcopy(r["restore"])
                    changed["origin_admission"]["origin_translation_um"][0]=.005
                    a.atomic(out/"restore.json",changed)
                a.atomic(out/"candidate/result.json",{"explicit_synthetic_generator":True})
                r["outputs"]={n:h for n,h in w.inventory(out).items()if n!="result.json"}
                a.atomic(out/"result.json",r)
            raw=(out/"result.json").read_bytes()if(out/"result.json").exists()else None
            uploads=[];primary=RuntimeError("upload-primary");save=OSError("publication-save")
            real_atomic=a.atomic;real_release=w.publisher.release
            tag="cloud-results-123456-1-"+w.GROUP
            info={"id":987,"tag_name":tag,"target_commitish":ENV["GITHUB_SHA"],"draft":False,"prerelease":True,"assets":[]}
            ref={"ref":"refs/tags/"+tag,"object":{"type":"commit","sha":ENV["GITHUB_SHA"]}}
            def api(path,missing=False):
                if path=="releases/tags/"+tag:return copy.deepcopy(info)
                if path=="git/ref/tags/"+tag:return ref
                raise AssertionError(path)
            def upload(argv,**kwargs):
                assert argv[:3]==["gh","release","upload"]and argv[3]==tag and "--clobber"not in argv
                p=Path(argv[4]);uploads.append(p.name)
                if mode in ("upload","upload_save"):raise primary
                info["assets"].append(dict(id=900+len(uploads),name=p.name,size=p.stat().st_size,
                  digest="sha256:"+a.sha(p),browser_download_url="https://example.invalid/"+p.name))
                return types.SimpleNamespace(returncode=0)
            def atomic(path,value):
                if Path(path).name=="publication.json"and ((mode=="upload_save"and uploads)or mode in ("save_encode","save_emit")):raise save
                return real_atomic(path,value)
            with contextlib.ExitStack()as stack:
                for obj,name,val in ((w,"ROOT",root),(w,"OUT",out),(w,"TRANSPORT",transport),(w,"DRIVER_LOG",driver_log)):
                    stack.enter_context(mock.patch.object(obj,name,val))
                stack.enter_context(mock.patch.dict(os.environ,ENV))
                stack.enter_context(mock.patch.object(a,"publication_authorize",return_value={}))
                stack.enter_context(mock.patch.object(w,"storage",return_value={}))
                stack.enter_context(mock.patch.object(a,"methods",side_effect=RuntimeError("source-integrity")if mode=="source_failure"else None,return_value={}))
                stack.enter_context(mock.patch.object(a,"validate_candidate",return_value=synthetic_candidate))
                stack.enter_context(mock.patch.object(w.release,"api",side_effect=api))
                stack.enter_context(mock.patch.object(w.publisher.subprocess,"run",side_effect=upload))
                stack.enter_context(mock.patch.object(a,"atomic",side_effect=atomic))
                stack.enter_context(contextlib.redirect_stderr(io.StringIO()))
                if mode=="save_encode":
                    original_dumps=json.dumps
                    def encoding(value,*args,**kwargs):
                        if type(value)is dict and "unsaved_geometry_publication"in value:raise ValueError("fallback-encode")
                        return original_dumps(value,*args,**kwargs)
                    stack.enter_context(mock.patch.object(w.json,"dumps",side_effect=encoding))
                if mode=="save_emit":stack.enter_context(mock.patch("builtins.print",side_effect=OSError("fallback-emit")))
                result=w.publication_result({})
                assert result["generation_and_serialized_reread_complete"]is (mode=="synthetic_success")
                if mode=="origin_join":
                    assert result["status"]=="FAIL_MISSING_OR_INVALID_TERMINAL_REPORT"
                    assert "Restore result changed" in str(result["terminal_report_error"])
                caught=None
                try:proof=w.publish(result)
                except BaseException as e:caught=e
            assert w.publisher.release is real_release
            assert ((out/"result.json").read_bytes()if(out/"result.json").exists()else None)==raw
            if mode in ("upload","upload_save"):assert caught is primary,(mode,caught)
            elif mode in ("save_encode","save_emit"):assert caught is save,(mode,caught)
            else:
                assert caught is None,(mode,caught)
                assert proof["status"]=="PASS_COMPLETE_GEOMETRY_EVIDENCE_PUBLICATION_ONLY"
                expected_assets=7 if mode in ("synthetic_success","origin_join")else 4
                assert len(info["assets"])==expected_assets and len(uploads)==expected_assets
                if mode=="source_failure":assert result["status"]=="FAIL_PROTECTED_SOURCE_AT_PUBLICATION"
                summary=next(transport.glob("*.summary.json"))
                assert a.read(summary)==result
                if mode in ("synthetic_success","origin_join"):
                    published_restore=next(transport.glob("*.restore.json"))
                    assert published_restore.read_bytes()==(out/"restore.json").read_bytes()
                    assert any(x["name"]==published_restore.name and x["digest"]=="sha256:"+a.sha(published_restore)for x in info["assets"])
                    if mode=="synthetic_success":
                        assert a.read(summary)["restore"]["origin_admission"]==observation
                        assert a.read(published_restore)["origin_admission"]==observation
                assert proof["driver_log"]["sha256"]==a.sha(driver_log)
                assert next(transport.glob("*.driver.log")).read_bytes()==driver_log.read_bytes()
            rows.append(dict(mode=mode,actual_pack_and_reserved_publisher=True,raw_terminal_preserved=True,
                             synthetic_cloud_transport=True,no_acceptance=True))
    return rows

def isolated_controls(method):
    rows=[];sources=dict(method["protected_sha256"]);sources[str(a.METHOD.relative_to(a.ROOT))]=a.sha(a.METHOD)
    with tempfile.TemporaryDirectory()as tmp:
        root=Path(tmp)
        for name,h in sources.items():
            raw=a.regular(a.ROOT,name).read_bytes();assert hashlib.sha256(raw).hexdigest()==h
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
        command=[sys.executable,"-I","-B","-c",
          "import sys;sys.path.insert(0,sys.argv[1]);import cdr_v59_selector_column_width_native as a;import cloud_cdr_v59_selector_column_width_native as w;a.methods();print('ISOLATED_PROTECTED_IMPORT_PASS')",
          str(root/"scripts")]
        for mode in ("pristine","missing_new_host","changed_restore","missing_waiter"):
            target={"missing_new_host":"scripts/cloud_cdr_v59_selector_column_width_native.py",
                    "changed_restore":"scripts/cdr_v59_tail_loaded_admission.py",
                    "missing_waiter":"scripts/wait_cloud_tested_source_release.py"}.get(mode)
            original=(root/target).read_bytes()if target else None
            if target:
                if mode=="changed_restore":(root/target).write_bytes(original+b"\n# changed source\n")
                else:(root/target).unlink()
            p=subprocess.run(command,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=180)
            if mode=="pristine":assert p.returncode==0 and p.stdout.strip()==b"ISOLATED_PROTECTED_IMPORT_PASS",p.stderr
            else:assert p.returncode!=0 and (b"ModuleNotFoundError"in p.stderr or b"Protected source changed"in p.stderr),p.stderr
            rows.append(dict(mode=mode,returncode=p.returncode,stdout=p.stdout.decode(),stderr=p.stderr.decode()))
            if target:(root/target).write_bytes(original)
    return dict(rows=rows,explicit_protected_files=len(sources),actual_isolated_subprocess=True)

def candidate_controls():
    c=a.width_contract();rows=[]
    for mode in ("clean","input","output","addition","ownership","cluster","clearance","material","qualification","inventory"):
        with tempfile.TemporaryDirectory()as tmp:
            out=Path(tmp);p=out/"candidate";p.mkdir()
            (p/(a.generator.TOP+".gds")).write_bytes(b"EXPLICIT_SYNTHETIC_GDS_BYTES_NOT_NATIVE_GEOMETRY")
            ownership=[dict(placement=tag,device=row["device"],net=row["net"],layer=row["layer"],
              native_cluster=c["owner_partitions"][tag][row["net"]]["native_cluster"],
              old_component_area_dbu2=10,added_area_dbu2=2,clearance_dbu=c["clearance_dbu"][str(row["layer"])])
              for tag in c["placements"]for row in c["declared_rectangles"]]
            r=dict(status="GENERATED_UNQUALIFIED_ADDITIVE_COLUMN_WIDTH",
              input_gds_sha256=c["baseline_inventory"][a.generator.GDS],
              candidate_gds_sha256=a.sha(p/(a.generator.TOP+".gds")),proposal=c["declared_rectangles"],
              added_raw_records=[["EXPLICIT_SYNTHETIC_RECORD",i]for i in range(26)],
              actual_original_native_ownership_and_clearance=ownership,
              all_original_material_raw_text_properties_hierarchy_preserved=True,
              original_500_devices_1446_terminals_978_anchors_reference_only=True,
              outputs=a.generator.frozen.files(p))
            for k in ("native_DRC_executed","native_LVS_executed","fresh_RC_executed","simulation_executed",
                      "physical_accepted","electrical_accepted","full_phy_accepted"):r[k]=False
            reasons={"input":"Wrong source GDS","output":"Candidate GDS changed","addition":"Exact26 additions changed",
              "ownership":"Complete52 ownership checks missing","cluster":"Native ownership identity changed",
              "clearance":"Native clearance evidence changed","material":"Original material lost",
              "qualification":"Unexpected candidate qualification: native_LVS_executed","inventory":"Complete candidate inventory changed"}
            if mode=="input":r["input_gds_sha256"]="0"*64
            if mode=="output":r["candidate_gds_sha256"]="0"*64
            if mode=="addition":r["added_raw_records"].pop()
            if mode=="ownership":r["actual_original_native_ownership_and_clearance"].pop()
            if mode=="cluster":r["actual_original_native_ownership_and_clearance"][0]["native_cluster"]=-1
            if mode=="clearance":r["actual_original_native_ownership_and_clearance"][0]["added_area_dbu2"]=0
            if mode=="material":r["all_original_material_raw_text_properties_hierarchy_preserved"]=False
            if mode=="qualification":r["native_LVS_executed"]=True
            if mode=="inventory":r["outputs"][a.generator.TOP+".gds"]="0"*64
            a.atomic(p/"result.json",r)
            with mock.patch.object(a,"validate_view",return_value={}):
                if mode=="clean":
                    proof=a.validate_candidate(out);assert proof["generation_and_serialized_reread_complete"]is True
                else:reject(mode,lambda:a.validate_candidate(out),reasons[mode])
            rows.append(dict(mode=mode,actual_candidate_validator=True,explicit_synthetic_report_and_GDS_bytes=True))
    return rows

def controls():
    method=a.methods();origin=origin_controls()
    return dict(status="PASS_GEOMETRY_WRAPPER_SOURCE_CONTROLS_ONLY",
      authorization=auth_controls(method),origin=origin,adapter=binding_controls(),restore=restore_controls(origin["observation"]),candidate=candidate_controls(),
      lifecycle=lifecycle_controls(method),commands=command_controls(),publication=publication_controls(origin["observation"]),
      isolated=isolated_controls(method),native_archive_acquired=False,native_geometry_executed=False,
      physical_accepted=False,electrical_accepted=False)

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,required=True);args=parser.parse_args()
    try:result=controls()
    except BaseException as error:
        result=dict(status="FAIL_GEOMETRY_WRAPPER_CONTROLS",error=repr(error))
        try:a.atomic(args.output,result)
        except BaseException:w.fallback("unsaved_geometry_wrapper_controls",result)
        raise
    a.atomic(args.output,result)
    print(json.dumps(result,sort_keys=True,allow_nan=False))

if __name__=="__main__":main()
