#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Actual loaded outer lifecycle and publication; synthetic numerical/remote transport only."""
import copy,hashlib,io,json,os,shutil,signal,sys,tempfile,traceback,types
from contextlib import contextmanager,ExitStack,redirect_stdout
from pathlib import Path
from unittest.mock import patch
import cloud_cdr_v59_tail_loaded_stage as d
import check_cdr_v59_tail_loaded_result as results

a=d.a
ENV={"GITHUB_ACTIONS":"true","RUNNER_ENVIRONMENT":"github-hosted",
 "GITHUB_REPOSITORY":"Melihakbulut221/nssoc","GITHUB_RUN_ID":"101","GITHUB_RUN_ATTEMPT":"1","GITHUB_SHA":"a"*40}
ENGINE=b"EXPLICIT SYNTHETIC ENGINE FILE; NEVER EXECUTED\n"
ENGINE_EXPECTED="103134f6e3bf71771a7f9c94cc43fd5ea2f9d51490116718814aa344e9c51509"
class InjectedFailure(RuntimeError):pass

def encoded(value):
    return(json.dumps(value,indent=2,sort_keys=True)+"\n").encode()

def frame_refusal(call,reason,function):
    try:call()
    except AssertionError as error:
        assert error.args==(reason,),(reason,error.args)
        frames=[];tb=error.__traceback__
        while tb is not None:
            frames.append((tb.tb_frame.f_code.co_name,tb.tb_frame.f_code.co_filename));tb=tb.tb_next
        assert (function,d.__file__)in frames,(reason,frames)
        return {"reason":reason,"actual_frame":function}
    raise AssertionError("Accepted "+reason)

@contextmanager
def fixture(actual,method,fault):
    original_stage=a.regular(a.ROOT,d.result_gate.ORIGINAL).read_bytes()
    sampler=a.regular(a.ROOT,d.runtime.SAMPLER).read_bytes()
    with tempfile.TemporaryDirectory()as folder,ExitStack()as stack:
        root=Path(folder);c=copy.deepcopy(actual)
        payloads={name:("SYNTHETIC_CURRENT_MEMBER "+name+"\n").encode()
          for name in actual["actual_fresh_RC"]["expected_files"]}
        assert len(payloads)==3823
        c["actual_fresh_RC"]["expected_files"]={name:hashlib.sha256(value).hexdigest()for name,value in payloads.items()}
        protected={a.PIN:encoded(c),d.result_gate.ORIGINAL:original_stage,
          d.runtime.SAMPLER:sampler,"protected-fixture.py":b"ORIGINAL_PROTECTED_FIXTURE\n"}
        for name,value in protected.items():
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(value)
        m=copy.deepcopy(method)
        for name in a.AUTH:m[name]=True
        m["controller_readiness"]=True
        m["protected_sha256"]={name:hashlib.sha256(value).hexdigest()for name,value in protected.items()}
        a.write(root/a.METHOD,m)
        stack.enter_context(patch.object(a,"ROOT",root));stack.enter_context(patch.object(d,"ROOT",root))
        stack.enter_context(patch.dict(os.environ,ENV))
        stack.enter_context(patch.object(d,"ENGINE_SHA",hashlib.sha256(ENGINE).hexdigest()))
        stack.enter_context(patch.object(d.shutil,"disk_usage",return_value=types.SimpleNamespace(free=64*1024**3)))
        case,preparation=results.current_fixture(fault)
        assert a.methods()==m and a.authorize(True)==m and a.authorize(False)==m
        yield {"root":root,"contract":c,"method":m,"payloads":payloads,"case":case,"preparation":preparation,
          "protected":root/"protected-fixture.py"}

@contextmanager
def remote(f,ctx,mutate_preparation=None,upload_error=None):
    values={};refs={};uploads={};lookups=[];downloads=[]
    for group in ["cdr-v59-tail-loaded-"+x for x in a.CASES]+["cdr-v59-tail-loaded-preparation"]:
        tag,head=d.release.context(group,ENV)
        values[tag]={"id":123+len(values),"tag_name":tag,"target_commitish":head,"draft":False,"prerelease":True,"assets":[]}
        refs[tag]={"ref":"refs/tags/"+tag,"object":{"type":"commit","sha":head}}
    native=copy.deepcopy(f["preparation"])
    if mutate_preparation:mutate_preparation(native)
    native_bytes=encoded(native)
    prepctx=d.context("nominal_early",True)
    summary=d.initial_result(prepctx,{},{"synthetic_storage":True})
    summary.update(status=d.PREP_PASS,native_case_passed=True,terminal_finalization_complete=True,
      outer_terminal_finalization_complete=True,outer_terminal_errors=[],
      native_controller_result_sha256=hashlib.sha256(native_bytes).hexdigest(),
      outputs={"native/result.json":hashlib.sha256(native_bytes).hexdigest()})
    prep_tag,_=d.release.context(prepctx["group"],ENV);prepstem=prepctx["group"]+"-101-1"
    sourcebytes={}
    for suffix,value in (("summary.json",encoded(summary)),("native-result.json",native_bytes)):
        name=prepstem+"."+suffix;url="fixture://"+name;sourcebytes[url]=value
        values[prep_tag]["assets"].append({"id":1000+len(sourcebytes),"name":name,"size":len(value),
          "digest":"sha256:"+hashlib.sha256(value).hexdigest(),"state":"uploaded","browser_download_url":url})
    # A preparation lifecycle starts before its own result assets exist.
    if ctx["prepare"]:values[prep_tag]["assets"]=[]
    def api(path,missing=False):
        lookups.append(path)
        if path.startswith("releases/tags/"):
            tag=path[len("releases/tags/"):];assert tag in values,path;return copy.deepcopy(values[tag])
        if path.startswith("git/ref/tags/"):
            tag=path[len("git/ref/tags/"):];assert tag in refs,path;return copy.deepcopy(refs[tag])
        raise AssertionError("Unexpected fixture API: "+path)
    def fetch(url,digest,target):
        value=sourcebytes[url];assert hashlib.sha256(value).hexdigest()==digest
        target.write_bytes(value);downloads.append(url)
    def upload(argv,**kwargs):
        tag=argv[3]
        assert argv[:3]==["gh","release","upload"]and argv[-2:]==["-R","Melihakbulut221/nssoc"]
        if upload_error is not None:raise upload_error
        path=Path(argv[4]);key=(tag,path.name);assert key not in uploads
        value=path.read_bytes();uploads[key]=value
        values[tag]["assets"].append({"id":2000+len(uploads),"name":path.name,"size":len(value),
          "digest":"sha256:"+hashlib.sha256(value).hexdigest(),"state":"uploaded",
          "browser_download_url":"https://example.invalid/"+path.name})
        return types.SimpleNamespace(returncode=0)
    real_wait=d.wait
    def wait(group,env):
        return real_wait(group,env,api,lambda seconds:None,lambda *args,**kwargs:None)
    with patch.object(d.release,"api",side_effect=api),patch.object(a,"fetch",side_effect=fetch),\
         patch.object(d.publisher.subprocess,"run",side_effect=upload),patch.object(d,"wait",side_effect=wait):
        yield {"values":values,"refs":refs,"uploads":uploads,"lookups":lookups,"downloads":downloads,
          "sourcebytes":sourcebytes,"prep_tag":prep_tag,"prepstem":prepstem,"api":api}

def roundtrip(ctx,remote,successful):
    result=d.read_json(ctx["output"]/"result.json")
    proof=d.read_json(ctx["transport"]/"publication.json")
    assert proof["status"]=="PASS_COMPLETE_ORIGINAL_LOADED_EVIDENCE_PUBLISHED"
    stem=ctx["group"]+"-101-1";tag,_=d.release.context(ctx["group"],ENV)
    assert remote["uploads"][(tag,stem+".summary.json")]==(ctx["output"]/"result.json").read_bytes()
    manifest=d.read_json(ctx["transport"]/(stem+".parts.json"))
    expected=d.inventory(ctx["output"]);target=ctx["output"].parent/"published-roundtrip"
    a.saved.exact_extract(manifest,ctx["transport"],target,expected)
    assert d.inventory(target)==expected
    assert len(remote["uploads"])==len(proof["assets"])
    for row in proof["direct_bindings"]:
        raw=(ctx["output"]/row["member"]).read_bytes()
        assert remote["uploads"][(tag,stem+"."+row["asset_suffix"])]==raw
        assert row["sha256"]==hashlib.sha256(raw).hexdigest()
        assert row["qualified_as_success"]is successful and row["JSON_syntax_checked"]is successful
    return {"files":len(expected),"assets":len(proof["assets"]),"all_bytes_roundtripped":True,
      "successful":successful,"direct":proof["direct_bindings"]}

def worker_files(f,ctx,mode):
    root=ctx["worker"];root.mkdir()
    for name,value in f["payloads"].items():
        path=root/"current-mim-bundle"/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(value)
    engine=root/"source/source/runtime/patched-ngspice";engine.parent.mkdir(parents=True);engine.write_bytes(ENGINE)
    (root/".hidden").write_bytes(b"FULL_HIDDEN_EVIDENCE");(root/"empty").write_bytes(b"")
    (root/"complete-native-wave.raw").write_bytes(b"EXPLICIT SYNTHETIC WHOLE WAVE BYTES\0\xff\n")
    report=copy.deepcopy(f["preparation"]if ctx["prepare"]else f["case"])
    if mode=="engine_changed":engine.write_bytes(ENGINE+b"CHANGED")
    report["outputs"]={n:h for n,h in d.inventory(root).items()if n!="result.json"}
    a.write(root/"result.json",report)
    if mode in ("body_failure","body_cleanup","partial_JSON"):
        (root/"result.json").write_bytes(b'{"interrupted":')
        (root/"partial.bin").write_bytes(b"AVAILABLE_PARTIAL\0")
    if mode=="malformed_native":(root/"result.json").write_bytes(b'{"malformed":')
    if mode=="source_corruption":f["protected"].write_bytes(b"CHANGED_PROTECTED_SOURCE")
    if mode=="copy_symlink":(root/"refused-link").symlink_to(root/"empty")
    return report

def lifecycle_controls(actual,method,fault):
    rows=[]
    modes=("preparation","case","body_failure","partial_JSON","malformed_native","source_corruption",
      "cleanup_failure","body_cleanup","final_sample","stop_failure","save_failure","copy_symlink",
      "publication_failure","prepared_vectors","engine_changed","command_read")
    for mode in modes:
        with fixture(actual,method,fault)as f,ExitStack()as stack:
            prepare=mode=="preparation";ctx=d.context("nominal_early"if prepare else"clock_stopped",prepare)
            errors={key:InjectedFailure(key.upper())for key in ("body","cleanup","sample","stop","save","publication","command")}
            events=[];original_release=d.publisher.release
            class Stop:
                def set(self):
                    events.append("stop")
                    if mode=="stop_failure":raise errors["stop"]
            class Thread:
                def __init__(self,target,daemon):assert daemon is True;self.target=target
                def start(self):events.append("thread_start")
                def join(self,timeout):assert timeout==5;events.append("join")
                def is_alive(self):return False
            class Owned:
                ACTIVE=None
                def __init__(self):self.TRACE=ctx["output"]/"supervision";self.STOP=Stop()
                def interrupted(self,*args):raise InjectedFailure("SIGNAL")
                def heartbeat(self):raise AssertionError("Synthetic heartbeat must not be executed")
                def stop_process(self,process):
                    events.append("cleanup")
                    if mode in ("cleanup_failure","body_cleanup"):raise errors["cleanup"]
                    return {"remaining_live":[],"explicit_synthetic_owned_transport":True}
                def sample(self,label):
                    assert label=="loaded_terminal";events.append("sample")
                    if mode=="final_sample":raise errors["sample"]
                    return {"explicit_synthetic_resource_sample":True}
                def supervised(self,argv,label,seconds,cwd):
                    assert argv==[sys.executable,str(f["root"]/d.WORKER),"--case",ctx["case"]]+(["--prepare-only"]if prepare else[])
                    assert label==ctx["label"]and seconds==(1200 if prepare else 7200)and cwd==f["root"]
                    events.append("worker");worker_files(f,ctx,mode)
                    code=7 if mode in ("body_failure","body_cleanup","partial_JSON")else 0
                    record={"label":label,"argv":argv,"returncode":code,"supervision_failure":None,
                      "process_group_cleanup":{"remaining_live":[]},"explicit_synthetic_numerical_transport":True}
                    for stream,value in (("stdout",b"WHOLE_SYNTHETIC_STDOUT\n"),("stderr",b"")):
                        path=self.TRACE/(label+"."+stream);path.write_bytes(value)
                        record[stream+"_bytes"]=len(value);record[stream+"_sha256"]=a.sha(path)
                    a.write(self.TRACE/(label+".command.json"),record)
                    if code:raise errors["body"]
            owned=Owned()
            supervisor=stack.enter_context(patch.object(d.runtime,"supervisor",return_value=owned))
            stack.enter_context(patch.object(d.threading,"Thread",Thread))
            argv=["loaded","--case",ctx["case"]]+(["--prepare-only"]if prepare else[])
            stack.enter_context(patch.object(sys,"argv",argv))
            real_replace=Path.replace;real_read=d.read_json
            def replace(path,target):
                if mode=="save_failure"and Path(target)==ctx["output"]/"result.json"and"sample"in events:
                    assert path.name=="result.json.tmp"and path.is_file();raise errors["save"]
                return real_replace(path,target)
            def read(path):
                if mode=="command_read"and Path(path).name==ctx["label"]+".command.json":
                    assert Path(path).is_file();raise errors["command"]
                return real_read(path)
            stack.enter_context(patch.object(Path,"replace",replace));stack.enter_context(patch.object(d,"read_json",side_effect=read))
            mutation=(lambda r:r["vectors"].__setitem__(0,r["vectors"][0]+"_changed"))if mode=="prepared_vectors"else None
            signals={sig:signal.getsignal(sig)for sig in (signal.SIGINT,signal.SIGTERM)}
            output=io.StringIO();caught=None
            with remote(f,ctx,mutation,errors["publication"]if mode=="publication_failure"else None)as transport,redirect_stdout(output):
                try:d.main()
                except BaseException as error:caught=error
                if mode=="save_failure":
                    emitted=[json.loads(line)["unsaved_terminal_loaded_result"]for line in output.getvalue().splitlines()
                      if line.startswith('{"unsaved_terminal_loaded_result":')]
                    assert len(emitted)==1;result=emitted[0]
                    assert result["status"]=="FAIL_TAIL_LOADED_TERMINAL_SAVE"and caught is errors["save"]
                    assert len(result["retained_atomic_fragments"])==1
                    retained=result["retained_atomic_fragments"][0]
                    assert a.sha(ctx["output"]/retained["retained"])==retained["sha256"]
                    assert result["outputs"][retained["retained"]]==retained["sha256"]
                    assert real_read(ctx["output"]/"result.json")["status"].startswith("RUNNING_")
                else:result=real_read(ctx["output"]/"result.json")
                supervisor.assert_called_once_with(f["root"],ctx["output"],ctx["output"]/"supervision",
                  a.methods,f["method"]["protected_sha256"][d.runtime.SAMPLER])
                assert events.count("worker")==events.count("cleanup")==events.count("stop")==events.count("join")==events.count("sample")==1
                assert {sig:signal.getsignal(sig)for sig in signals}==signals
                assert d.publisher.release is original_release
                assert result["outputs"]=={n:h for n,h in d.inventory(ctx["output"]).items()if n!="result.json"}
                assert (ctx["output"]/"native/.hidden").read_bytes()==b"FULL_HIDDEN_EVIDENCE"
                assert (ctx["output"]/"native/empty").read_bytes()==b""
                assert (ctx["output"]/"native/complete-native-wave.raw").read_bytes()==b"EXPLICIT SYNTHETIC WHOLE WAVE BYTES\0\xff\n"
                if mode in ("preparation","case"):
                    assert caught is None and result["status"]==(d.PREP_PASS if prepare else d.CASE_PASS)
                elif mode in ("body_failure","body_cleanup","partial_JSON"):assert caught is errors["body"]
                elif mode=="cleanup_failure":assert caught is errors["cleanup"]
                elif mode=="final_sample":assert caught is errors["sample"]
                elif mode=="stop_failure":
                    assert caught is errors["stop"]and events.index("join")>events.index("stop")
                elif mode=="publication_failure":assert caught is errors["publication"]
                elif mode=="command_read":assert caught is errors["command"]
                elif mode=="source_corruption":
                    assert type(caught)is AssertionError and caught.args==("Protected source or evidence changed: protected-fixture.py",)
                elif mode=="copy_symlink":
                    assert type(caught)is AssertionError and caught.args==("Symlink in native worker evidence",)
                    assert result["native_evidence_preservation"]["complete"]is False
                    assert result["native_evidence_preservation"]["errors"][0]["refused_symlink_target"]==str(ctx["worker"]/"empty")
                elif mode=="prepared_vectors":
                    assert type(caught)is AssertionError and caught.args==("Original acquired preparation vector census changed",)
                elif mode=="engine_changed":
                    assert type(caught)is AssertionError and caught.args==("Original loaded engine changed",)
                elif mode=="malformed_native":assert type(caught)is json.JSONDecodeError
                if mode not in ("preparation","case","publication_failure"):
                    assert result["status"].startswith("FAIL_")
                if mode=="body_cleanup":
                    assert any(x["error"]==repr(errors["cleanup"])for x in result["outer_terminal_errors"])
                assert len(result["outer_terminal_actions"])==8
                if mode in ("source_corruption","save_failure"):
                    assert not ctx["transport"].exists()
                    published={"publication_refused_after_source_or_saved_report_failure":True}
                elif mode=="publication_failure":
                    assert real_read(ctx["transport"]/"publication.json")["status"]=="FAIL_LOADED_PUBLICATION"
                    published={"publication_failure_preserved":True}
                else:published=roundtrip(ctx,transport,mode in ("preparation","case"))
                rows.append({"case":mode,"status":result["status"],"full_existing_output_map":True,
                  "actual_main_run_execute_finalization":True,"real_signals_restored":True,"all_eight_outer_actions":True,
                  "available_native_files":len(result["native_evidence_preservation"]["copied_files"]),
                  "publication":published,"explicit_synthetic_numerical_runtime":True})
    assert len(rows)==16
    return {"positive":2,"refusals":14,"cases":rows}

def execution_policy_controls(actual,method,fault):
    with fixture(actual,method,fault)as f:
        launched=[];positive=[];refused=[]
        class Owned:
            def __init__(self,trace):self.TRACE=trace;trace.mkdir()
            def supervised(self,argv,label,seconds,cwd):
                launched.append({"argv":argv,"label":label,"seconds":seconds})
                row={"argv":argv,"label":label,"returncode":0,"supervision_failure":None,
                  "process_group_cleanup":{"remaining_live":[]}}
                for stream in ("stdout","stderr"):
                    path=self.TRACE/(label+"."+stream);path.write_bytes(b"")
                    row[stream+"_bytes"]=0;row[stream+"_sha256"]=a.sha(path)
                a.write(self.TRACE/(label+".command.json"),row)
        modes=[("nominal_early",True)]+[(case,False)for case in a.CASES]
        for case,prepare in modes:
            ctx=d.context(case,prepare);owned=Owned(f["root"]/("trace-"+ctx["group"]))
            r={};d.execute(ctx,r,owned)
            assert r["command"]["argv"][-1]==("--prepare-only"if prepare else case)
            positive.append({"case":case,"prepare":prepare,"seconds":ctx["seconds"]})
            changed=dict(ctx,seconds=ctx["seconds"]+1);before=len(launched)
            refused.append(frame_refusal(lambda:d.execute(changed,{},owned),
              "Unknown original loaded worker budget","execute"))
            assert len(launched)==before
        for case,prepare in (("new-case",False),("nominal_late",True),("nominal_early",1),("nominal_early","false")):
            refused.append(frame_refusal(lambda:d.context(case,prepare),"Invalid original case mode","context"))
        ctx=d.context("nominal_early",True)
        with remote(f,ctx)as transport:
            result=d.preflight(ctx)
            groups=["cdr-v59-tail-loaded-"+x for x in a.CASES]+["cdr-v59-tail-loaded-preparation"]
            assert list(result["groups"])==groups and len(result["groups"])==11
            release_reads=[path for path in transport["lookups"]if path.startswith("releases/tags/")]
            assert release_reads==["releases/tags/cloud-results-101-1-"+group for group in groups]
            original_contract=copy.deepcopy(f["contract"]);original_method=copy.deepcopy(f["method"])
            for name,change,reason in (
              ("preparation_seconds",lambda p:p.__setitem__("preparation_seconds",1199),"Original matrix execution policy changed"),
              ("case_seconds",lambda p:p.__setitem__("each_loaded_case_seconds",7201),"Original matrix execution policy changed"),
              ("parallelism",lambda p:p.__setitem__("max_parallel",3),"Original matrix execution policy changed"),
              ("group_missing",lambda p:p["groups"].pop(),"Complete matrix reservation policy changed")):
                c=copy.deepcopy(original_contract);change(c["proposed_execution"])
                a.write(f["root"]/a.PIN,c);m=copy.deepcopy(original_method)
                m["protected_sha256"][a.PIN]=a.sha(f["root"]/a.PIN);a.write(f["root"]/a.METHOD,m)
                before=len(transport["lookups"])
                refused.append({"name":name,**frame_refusal(lambda:d.preflight(ctx),reason,"preflight")})
                assert len(transport["lookups"])==before
            a.write(f["root"]/a.PIN,original_contract);a.write(f["root"]/a.METHOD,original_method)
        assert len(positive)==11 and len(refused)==19
        return {"positive_modes":positive,"all_eleven_reserved_preparation_last":True,"refused":refused,
          "actual_execute_command_records":True,"native_worker_executed":False}

def preparation_controls(actual,method,fault):
    cases=[]
    modes=("complete","missing_asset","wrong_source","wrong_run","wrong_status","native_hash","acceptance","size","digest")
    for mode in modes:
        with fixture(actual,method,fault)as f:
            ctx=d.context("clock_stopped",False);ctx["output"].mkdir()
            with remote(f,ctx)as transport:
                value=transport["values"][transport["prep_tag"]]
                if mode=="missing_asset":value["assets"].pop()
                elif mode=="size":value["assets"][0]["size"]+=1
                elif mode=="digest":value["assets"][0]["digest"]="sha256:"+"0"*64
                elif mode!="complete":
                    asset=value["assets"][0];url=asset["browser_download_url"]
                    summary=json.loads(transport["sourcebytes"][url])
                    if mode=="wrong_source":summary["source_head"]="b"*40
                    if mode=="wrong_run":summary["run_id"]=102
                    if mode=="wrong_status":summary["status"]="RUNNING_CURRENT_TAIL_LOADED_CASE"
                    if mode=="native_hash":summary["native_controller_result_sha256"]="0"*64
                    if mode=="acceptance":summary["accepted"]=True
                    raw=encoded(summary);transport["sourcebytes"][url]=raw
                    asset.update(size=len(raw),digest="sha256:"+hashlib.sha256(raw).hexdigest())
                if mode=="complete":
                    native,proof=d.fetch_preparation(ctx)
                    assert native==f["preparation"]and proof["run_id"]==101 and proof["source_head"]==ENV["GITHUB_SHA"]
                    assert proof["complete_original_preparation_predicates_passed"]is True
                    for name,row in proof["files"].items():
                        assert a.sha(ctx["output"]/row["member"])==row["sha256"]
                    detail={"full_native_bytes_and_original_predicates":True}
                elif mode=="digest":
                    # Transport fixture validates requested SHA against the real response bytes.
                    try:d.fetch_preparation(ctx)
                    except AssertionError as error:
                        assert error.args==()
                        tb=error.__traceback__;frames=[]
                        while tb is not None:frames.append(tb.tb_frame.f_code.co_name);tb=tb.tb_next
                        assert "fetch"in frames and"fetch_preparation"in frames
                    else:raise AssertionError("Accepted changed transport digest")
                    detail={"exact_transport_digest_refusal":True}
                else:
                    reason={"missing_asset":"Same-run preparation direct proof missing",
                      "size":"Preparation proof asset changed","wrong_source":"Same-run preparation identity changed",
                      "wrong_run":"Same-run preparation identity changed","wrong_status":"Same-run preparation identity changed",
                      "native_hash":"Preparation native bytes differ from full summary",
                      "acceptance":"Preparation acceptance scope changed"}[mode]
                    detail=frame_refusal(lambda:d.fetch_preparation(ctx),reason,"fetch_preparation")
                cases.append({"case":mode,**detail})
    assert len(cases)==9
    return {"positive":1,"refusals":8,"cases":cases}

def publication_seed(ctx,status):
    ctx["output"].mkdir()
    native=ctx["output"]/"native";native.mkdir()
    (native/"result.json").write_bytes(b'{"synthetic_result": true}\n')
    (native/".hidden").write_bytes(b"HIDDEN");(native/"empty").write_bytes(b"")
    r=d.initial_result(ctx,{},{"synthetic_storage":True})
    r.update(status=status,native_case_passed=True,terminal_finalization_complete=True,
      outer_terminal_finalization_complete=True,terminal_errors=[],outer_terminal_errors=[],
      native_evidence_preservation={"complete":True},outputs={})
    r["outputs"]={n:h for n,h in d.inventory(ctx["output"]).items()if n!="result.json"}
    a.write(ctx["output"]/"result.json",r)
    return r

def publication_controls(actual,method,fault):
    positives=[];refused=[]
    for mode in ("success","failed_partial","running","oversized"):
        with fixture(actual,method,fault)as f:
            ctx=d.context("clock_stopped",False)
            r=publication_seed(ctx,d.CASE_PASS if mode=="success"else"RUNNING_CURRENT_TAIL_LOADED_CASE"if mode=="running"else"FAIL_CASE")
            if mode=="failed_partial":(ctx["output"]/"native/result.json").write_bytes(b'{"exact_partial":')
            if mode=="oversized":r["complete_large_evidence"]="Q"*(4*1024**2+17)
            r["outputs"]={n:h for n,h in d.inventory(ctx["output"]).items()if n!="result.json"}
            a.write(ctx["output"]/"result.json",r)
            original_release=d.publisher.release
            with remote(f,ctx)as transport:
                d.publish(ctx,r);detail=roundtrip(ctx,transport,mode=="success")
                assert d.publisher.release is original_release
                if mode=="oversized":assert(ctx["transport"]/(ctx["group"]+"-101-1.summary.json")).stat().st_size>4*1024**2
                positives.append({"case":mode,**detail})
    mutations=(
      ("source",lambda r:r.__setitem__("source_head","b"*40),"Loaded publication run/source changed"),
      ("run",lambda r:r.__setitem__("run_id",102),"Loaded publication run/source changed"),
      ("boolean_run",lambda r:r.__setitem__("run_id",True),"Loaded publication run/source changed"),
      ("attempt",lambda r:r.__setitem__("run_attempt",2),"Loaded publication run/source changed"),
      ("boolean_attempt",lambda r:r.__setitem__("run_attempt",True),"Loaded publication run/source changed"),
      ("case",lambda r:r.__setitem__("case","vi_bias_off"),"Loaded publication case changed"),
      ("mode",lambda r:r.__setitem__("preparation_only",True),"Loaded publication case changed"),
      ("prior_failure",lambda r:r.__setitem__("original_physical_status","PASS"),"Loaded publication prior evidence changed"),
      ("old_electrical_lost",lambda r:r.__setitem__("original_eight_electrical_rejections_and_two_fault_detections_preserved",False),"Loaded publication prior evidence changed"),
      ("acceptance",lambda r:r.__setitem__("accepted",True),"Loaded publication acceptance scope changed"),
      ("integer_false",lambda r:r.__setitem__("qualified_pex",0),"Loaded publication acceptance scope changed"),
      ("success_without_native",lambda r:r.__setitem__("native_case_passed",False),"Incomplete loaded case cannot publish as successful"),
      ("outer_incomplete",lambda r:r.__setitem__("outer_terminal_finalization_complete",False),"Incomplete loaded case cannot publish as successful"),
      ("terminal_error",lambda r:r["terminal_errors"].append({"error":"injected"}),"Incomplete loaded case cannot publish as successful"),
      ("copy_incomplete",lambda r:r["native_evidence_preservation"].__setitem__("complete",False),"Incomplete loaded case cannot publish as successful"),
      ("status",lambda r:r.__setitem__("status","PASS_UNKNOWN"),"Unrecognized failed loaded status"),
      ("inventory",lambda r:r["outputs"].pop(next(iter(r["outputs"]))),"Loaded publication complete output inventory differs"))
    for name,mutate,reason in mutations:
        with fixture(actual,method,fault)as f:
            ctx=d.context("clock_stopped",False);r=publication_seed(ctx,d.CASE_PASS)
            before=encoded(r);mutate(r);assert encoded(r)!=before;a.write(ctx["output"]/"result.json",r)
            original_release=d.publisher.release
            with remote(f,ctx)as transport:
                detail=frame_refusal(lambda:d.publish(ctx,r),reason,"validate_publication")
                assert not transport["uploads"]and d.publisher.release is original_release
                refused.append({"case":name,**detail})
    for mode in ("successful_malformed","successful_missing","direct_symlink","saved_report_changed"):
        with fixture(actual,method,fault)as f:
            ctx=d.context("clock_stopped",False);r=publication_seed(ctx,d.CASE_PASS)
            path=ctx["output"]/"native/result.json"
            if mode=="successful_malformed":path.write_bytes(b'{"bad":')
            if mode=="successful_missing":path.unlink()
            if mode=="direct_symlink":
                path.unlink();path.symlink_to(ctx["output"]/"native/empty")
            if mode!="direct_symlink":
                r["outputs"]={n:h for n,h in d.inventory(ctx["output"]).items()if n!="result.json"}
                a.write(ctx["output"]/"result.json",r)
            if mode=="saved_report_changed":r["synthetic_changed_after_save"]=True
            original_release=d.publisher.release
            with remote(f,ctx)as transport:
                if mode=="successful_malformed":
                    try:d.publish(ctx,r)
                    except json.JSONDecodeError as error:
                        assert "read_json"in[frame.name for frame in traceback.extract_tb(error.__traceback__)]
                    else:raise AssertionError("Accepted successful malformed report")
                    detail={"actual_JSONDecodeError":True}
                else:
                    reason,function={"successful_missing":("Successful native direct report missing","publish"),
                      "direct_symlink":("Symlink in complete evidence","inventory"),
                      "saved_report_changed":("Loaded terminal report differs from publication","publish")}[mode]
                    detail=frame_refusal(lambda:d.publish(ctx,r),reason,function)
                assert not transport["uploads"]and d.publisher.release is original_release
                refused.append({"case":mode,**detail})
    assert len(positives)==4 and len(refused)==21
    return {"positive":positives,"refused":refused,"actual_pack_extract_reserved_publisher":True,
      "synthetic_remote_transport":True}

def controls():
    method=a.methods();assert method["source_controls_authorized"]is True
    assert d.ENGINE_SHA==ENGINE_EXPECTED
    actual=a.descriptor();historical,fault=results.historical_controls()
    return {"status":"PASS_LOADED_OUTER_SOURCE_CONTROLS",
      "lifecycle":lifecycle_controls(actual,method,fault),
      "execution_policy":execution_policy_controls(actual,method,fault),
      "preparation":preparation_controls(actual,method,fault),
      "publication":publication_controls(actual,method,fault),
      "historical_eight_rejections_two_faults_preserved":historical["eight_rejections_and_two_fault_detections_retained"],
      "original_numerical_worker_executed":False,"simulator_executed":False,
      "actual_current_native_archive_accessed":False,
      "fixture_runtime_engine_identity_explicitly_synthetic":True}

def main():
    try:result=controls()
    except BaseException as error:
        result={"status":"FAIL_LOADED_OUTER_SOURCE_CONTROLS","error":repr(error),"traceback":traceback.format_exc()}
        print(json.dumps(result,indent=2,sort_keys=True));raise
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=="__main__":main()
