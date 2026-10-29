#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted actual publication/pack controls with synthetic files and cloud transport."""
import argparse,contextlib,copy,hashlib,io,json,os,tarfile,tempfile,traceback
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import cdr_width_loaded_execution_admission as a
import cloud_cdr_width_loaded_stage as s
import cdr_width_loaded_publication as p
import check_cdr_width_loaded_execution as execution

STATUS="PASS_WIDTH_LOADED_FAILURE_PUBLICATION_SOURCE_CONTROLS"

def records(out):
    return {str(f.relative_to(out)):hashlib.sha256(f.read_bytes()).hexdigest()
      for f in out.rglob("*")if f.is_file()and not f.is_symlink()}

def archive_check(ctx,proof):
    stem=ctx["group"]+"-"+os.environ["GITHUB_RUN_ID"]+"-1"
    manifest=json.loads((ctx["transport"]/(stem+".parts.json")).read_bytes())
    raw=b"".join((ctx["transport"]/row["name"]).read_bytes()for row in manifest["parts"])
    a.require(hashlib.sha256(raw).hexdigest()==manifest["sha256"],"Synthetic packed archive digest differs")
    with tarfile.open(fileobj=io.BytesIO(raw),mode="r:gz")as tar:
        observed={}
        for item in tar.getmembers():
            if item.isdir():continue
            a.require(item.isfile(),"Unexpected synthetic archive member")
            name=Path(item.name).relative_to(ctx["output"].name).as_posix()
            observed[name]=hashlib.sha256(tar.extractfile(item).read()).hexdigest()
    a.require(observed==records(ctx["output"])==proof["complete_outputs"],"Full synthetic archive inventory differs")
    summary=json.loads((ctx["transport"]/(stem+".summary.json")).read_bytes())
    a.require(summary["outputs"]==observed,"Summary does not bind full actual packed files")
    return summary,manifest

def fixture(mode,body=None,cleanup=None):
    original_root=a.ROOT
    required=set(a.NEW_REQUIRED)|{"scripts/cdr_width_loaded_publication.py",
      "scripts/check_cdr_width_loaded_publication.py",
      "docs/evidence/cdr-width-loaded-publication-repair-source-review-20261029.json"}
    source={name:a.regular(original_root,name).read_bytes()for name in required}
    cloud_error=OSError("synthetic cloud upload primary")
    body_error=RuntimeError("synthetic native child primary")
    cleanup_error=RuntimeError("synthetic owned cleanup primary")
    with tempfile.TemporaryDirectory()as temp,contextlib.ExitStack()as stack:
        root=Path(temp);e=execution.env()
        stack.enter_context(patch.dict(os.environ,e,clear=True))
        stack.enter_context(patch.object(a,"ROOT",root));stack.enter_context(patch.object(s,"ROOT",root))
        for name,raw in source.items():
            path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        sentinel=root/"scripts/synthetic-protected.py";sentinel.write_bytes(b"# pristine synthetic source\n")
        protected={**{n:hashlib.sha256(b).hexdigest()for n,b in source.items()},
          "scripts/synthetic-protected.py":a.sha(sentinel)}
        method={"source_controls_authorized":True,"workflow_dispatch_authorized":True,
          "controller_readiness":True,"preparation_authorized":True,"simulation_authorized":True,
          "protected_sha256":protected}
        method_path=root/a.METHOD;method_path.write_text(json.dumps(method))
        def methods():
            m=p.strict_json(method_path.read_bytes())
            for name,h in m["protected_sha256"].items():
                a.require(a.sha(a.regular(root,name))==h,"synthetic exact source corruption: "+name)
            return m
        stack.enter_context(patch.object(a,"methods",methods))
        # This test's method/authorization data is synthetic, while production
        # context, source-byte comparison, reservation, pack, publisher and
        # terminal behavior are actual. The execution checker covers authority.
        stack.enter_context(patch.object(a,"authorize",lambda prepare:methods()))
        stack.enter_context(patch.object(s,"storage",lambda ctx,label:
          {"checkpoint":label,"free_bytes":64*1024**3,"required_bytes":16*1024**3}))
        ctx=s.context("nominal_early",True)
        tag,head=s.release.context(ctx["group"],os.environ)
        info={"id":101,"tag_name":tag,"target_commitish":head,"draft":False,"prerelease":True,"assets":[]}
        ref={"ref":"refs/tags/"+tag,"object":{"type":"commit","sha":head}}
        if mode=="wrong_reservation":info["target_commitish"]="b"*40
        requests=[];uploads=[]
        def api(name,missing=False):
            requests.append(name)
            if name=="releases/tags/"+tag:return copy.deepcopy(info)
            if name=="git/ref/tags/"+tag:return copy.deepcopy(ref)
            raise AssertionError("Unexpected cloud API: "+name)
        stack.enter_context(patch.object(s.release,"api",api))
        def upload(argv,*args,**kwargs):
            a.require(argv[:3]==["gh","release","upload"]and argv[3]==tag and argv[-2:]==["-R","Melihakbulut221/nssoc"],
              "Unexpected cloud transport command")
            path=Path(argv[4]);a.require(path.stat().st_size>0,"Attempted zero-byte direct upload")
            if mode in ("upload_failure","body_cleanup_upload","cleanup_upload","upload_and_receipt_failure"):
                raise cloud_error
            a.require(not any(x["name"]==path.name for x in info["assets"]),"Attempted asset overwrite")
            raw=path.read_bytes();uploads.append(path.name)
            info["assets"].append({"id":1000+len(uploads),"name":path.name,"size":len(raw),
              "digest":"sha256:"+hashlib.sha256(raw).hexdigest(),"state":"uploaded",
              "browser_download_url":"https://example.invalid/synthetic/"+path.name})
            return SimpleNamespace(returncode=0)
        stack.enter_context(patch.object(s.publisher.subprocess,"run",upload))
        old_hook=s.publisher.release
        if mode=="no_clobber":
            info["assets"].append({"id":999,"name":ctx["group"]+"-"+e["GITHUB_RUN_ID"]+"-1.summary.json",
              "size":1,"digest":"sha256:"+"0"*64,"browser_download_url":"https://example.invalid/prior"})
        if body is None:
            ctx["output"].mkdir()
            native=ctx["output"]/"native";native.mkdir()
            (native/"synthetic.wave").write_bytes(bytes(range(256))*8)
            (native/"empty.stderr").write_bytes(b"")
            if mode!="missing_native":
                (native/"result.json").write_bytes(b""if mode=="empty_native"else b"{broken"if mode=="malformed_native"else b'{"synthetic_native_data":true}\n')
            r=s.initial_result(ctx,{},{"fixture":"explicit synthetic"})
            r.update(status=s.PREP_PASS,native_case_passed=True,terminal_finalization_complete=True,
              outer_terminal_finalization_complete=True,outer_terminal_errors=[],terminal_errors=[],
              native_evidence_preservation={"complete":True})
            r["outputs"]=s.inventory(ctx["output"])
            if mode!="missing_outer":
                (ctx["output"]/"result.json").write_bytes(b""if mode=="empty_outer"else b"{broken"if mode=="malformed_outer"else
                  (json.dumps(r,sort_keys=True)+"\n").encode())
            if mode=="valid_failure":
                r.update(status="FAIL_SYNTHETIC_ORIGINAL_CASE",native_case_passed=False)
                (ctx["output"]/"result.json").write_text(json.dumps(r))
            if mode=="source_corrupt":sentinel.write_bytes(b"# changed synthetic protected source\n")
            if mode=="malformed_method":method_path.write_bytes(b"{bad method")
            if mode=="in_memory_mismatch":r["status"]="FAIL_DIFFERENT_IN_MEMORY"
            before={n:(ctx["output"]/n).read_bytes()for n in records(ctx["output"])}
            primary=None;proof=None
            if mode=="upload_and_receipt_failure":
                real_write=a.write
                def failed_receipt(path,value):
                    if path==ctx["transport"]/"publication.json"and value["status"]=="FAIL_LOADED_PUBLICATION":
                        raise OSError("synthetic final publication save failure")
                    return real_write(path,value)
                stack.enter_context(patch.object(a,"write",failed_receipt))
                stack.enter_context(patch("builtins.print",side_effect=OSError("synthetic fallback emission failure")))
            try:proof=s.publish(ctx,r if mode=="in_memory_mismatch"else None)
            except BaseException as error:primary=error
            a.require(s.publisher.release is old_hook,"Publisher reservation hook leaked")
            if mode=="wrong_reservation":
                a.require(isinstance(primary,AssertionError)and not uploads and not ctx["transport"].exists(),
                  "Wrong exact-source reservation reached archive/upload")
                return {"name":mode,"refusal_before_pack":True}
            if mode in ("upload_failure","upload_and_receipt_failure"):
                a.require(primary is cloud_error,"Upload primary was replaced")
                if mode=="upload_and_receipt_failure":
                    # Last durable receipt is the actual pre-upload RUNNING state;
                    # no fabricated final save is asserted when both channels fail.
                    proof=json.loads((ctx["transport"]/"publication.json").read_bytes())
                    a.require(proof["status"]=="RUNNING_LOADED_PUBLICATION","Invented final failed receipt")
                else:
                    proof=json.loads((ctx["transport"]/"publication.json").read_bytes())
                    a.require(proof["status"]=="FAIL_LOADED_PUBLICATION","Upload failure receipt missing")
            elif mode=="no_clobber":
                a.require(isinstance(primary,RuntimeError)and "never overwrite"in str(primary)and not uploads,
                  "Existing conflicting asset was overwritten")
                proof=json.loads((ctx["transport"]/"publication.json").read_bytes())
            else:a.require(primary is None,"Actual publication failed: "+repr(primary))
            summary,manifest=archive_check(ctx,proof)
            a.require(all((ctx["output"]/n).read_bytes()==b for n,b in before.items()),"Original raw files were rewritten")
            for n,h in proof["complete_outputs"].items():
                a.require(a.sha(ctx["output"]/n)==h,"Complete available evidence changed")
            unqualified=mode not in ("positive","upload_failure","no_clobber","upload_and_receipt_failure")
            if unqualified:a.require(summary["publication_qualified_as_success"]is False
              and summary["native_case_passed"]is False,"Failed/malformed evidence became success")
            plan=json.loads((ctx["output"]/p.PLAN).read_bytes())
            if mode=="empty_native":
                row=next(x for x in plan["files"]if x["member"]=="native/result.json")
                a.require(row["disposition"]=="archive_only_empty"and row["bytes"]==0
                  and not any(x.endswith(".native-result.json")for x in uploads),"Empty terminal direct asset uploaded")
            if mode=="source_corrupt":
                check=summary["publication_source_check"]
                row=next(x for x in check["observations"]if x["path"]=="scripts/synthetic-protected.py")
                a.require(check["qualified"]is False and check["error"]
                  and (ctx["output"]/row["member"]).read_bytes()==sentinel.read_bytes()
                  and row["expected_sha256"]!=row["actual_sha256"],"Changed source bytes/error lost")
            return {"name":mode,"full_archive_members":len(proof["complete_outputs"]),
              "actual_publisher_and_pack":True,"publication_qualified_as_success":summary["publication_qualified_as_success"],
              "native_data_synthetic":True,"raw_bytes_unchanged":True}
        # Exercise ACTUAL run_case -> execute -> finalize -> copy -> terminal ->
        # publish with only child/thread/signal/storage/cloud boundaries doubled.
        calls=[]
        class Stop:
            def set(self):calls.append("stop_heartbeat")
        class Supervisor:
            ACTIVE=None;STOP=Stop();TRACE=ctx["output"]/"supervision"
            def heartbeat(self):pass
            def interrupted(self,*args):pass
            def stop_process(self,active):
                calls.append("cleanup")
                if cleanup:raise cleanup_error
                return {"remaining_live":[]}
            def sample(self,label):calls.append("sample");return {"synthetic":True}
            def supervised(self,argv,label,seconds,cwd):
                a.require(seconds==1200 and cwd==root,"Original child budget/path changed")
                ctx["worker"].mkdir()
                (ctx["worker"]/"result.json").write_bytes(b"")
                (ctx["worker"]/"synthetic.wave").write_bytes(bytes(range(256)))
                stdout=b"synthetic child output\n";stderr=b""
                (self.TRACE/(label+".stdout")).write_bytes(stdout)
                (self.TRACE/(label+".stderr")).write_bytes(stderr)
                record={"label":label,"argv":argv,"returncode":1 if body else 0,
                  "supervision_failure":None,"process_group_cleanup":{"remaining_live":[]},
                  "stdout_bytes":len(stdout),"stdout_sha256":hashlib.sha256(stdout).hexdigest(),
                  "stderr_bytes":0,"stderr_sha256":hashlib.sha256(stderr).hexdigest()}
                (self.TRACE/(label+".command.json")).write_text(json.dumps(record))
                if body:raise body_error
        class Heartbeat:
            def __init__(self,*args,**kwargs):pass
            def start(self):calls.append("start")
            def join(self,timeout):calls.append("join")
            def is_alive(self):return False
        supervisor=Supervisor()
        stack.enter_context(patch.object(s.runtime,"supervisor",lambda *args:supervisor))
        stack.enter_context(patch.object(s.threading,"Thread",Heartbeat))
        stack.enter_context(patch.object(s.signal,"signal",lambda *args:None))
        method["protected_sha256"][s.runtime.SAMPLER]="0"*64
        # Needed by run_case before the explicit synthetic supervisor factory;
        # never read or claim a native sampler payload in this fixture.
        def lifecycle_authorize(prepare):return method
        stack.enter_context(patch.object(a,"authorize",lifecycle_authorize))
        try:s.run_case(ctx,{})
        except BaseException as error:
            a.require(error is (body_error if body else cleanup_error),"Original body/cleanup primary replaced")
        else:raise AssertionError("Lifecycle failure accepted")
        a.require("cleanup"in calls and "stop_heartbeat"in calls and "join"in calls and "sample"in calls,
          "Independent terminal actions skipped")
        proof=json.loads((ctx["transport"]/"publication.json").read_bytes())
        a.require(proof["status"]=="FAIL_LOADED_PUBLICATION","Actual publication failure receipt missing")
        summary,_=archive_check(ctx,proof)
        raw=json.loads((ctx["output"]/"result.json").read_bytes())
        a.require(any(x["action"]=="owned_process_cleanup"and not x["completed"]for x in raw["outer_terminal_actions"]),
          "Cleanup failure lost from original finalizer")
        a.require(summary["publication_qualified_as_success"]is False,"Lifecycle failure became success")
        a.require(s.publisher.release is old_hook,"Lifecycle publisher hook leaked")
        return {"name":mode,"actual_run_execute_finalize_publish":True,"primary":"body"if body else"cleanup",
          "raw_empty_native_and_waveform_preserved":True,"native_data_synthetic":True}

def controls():
    names=("positive","valid_failure","source_corrupt","malformed_method","missing_outer","empty_outer",
      "malformed_outer","missing_native","empty_native","malformed_native","in_memory_mismatch",
      "upload_failure","no_clobber","wrong_reservation","upload_and_receipt_failure")
    cases=[fixture(name)for name in names]
    cases.append(fixture("body_cleanup_upload",body=True,cleanup=True))
    cases.append(fixture("cleanup_upload",body=False,cleanup=True))
    return {"status":STATUS,"publication_cases":15,"actual_lifecycle_cases":2,"cases":cases,
      "actual_pack_and_publisher":True,"archive_payloads":"created solely from explicit synthetic fixture bytes",
      "real_native_archive_restored":False,"native_worker_executed":False,"simulator_executed":False,
      "electrical_accepted":False,"physical_accepted":False,"full_phy_accepted":False,
      "source_controls_only":True}

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,required=True);args=parser.parse_args()
    report={"status":"FAIL_WIDTH_LOADED_FAILURE_PUBLICATION_SOURCE_CONTROLS","source_controls_only":True,
      "native_worker_executed":False,"electrical_accepted":False,"physical_accepted":False,"full_phy_accepted":False}
    primary=None
    try:
        ctx=a.context();method=a.methods()
        a.require(method["source_controls_authorized"]is True,"Publication controls source authority disabled")
        report=controls()
        report["current_context"]={**ctx,"source_controls_only":True,"native_executed":False}
    except BaseException as error:primary=error;report.update(error=repr(error),traceback=traceback.format_exc())
    finally:
        raw=(json.dumps(report,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
        try:args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_bytes(raw)
        except BaseException as error:
            if primary is None:primary=error
        try:print(raw.decode(),end="",flush=True)
        except BaseException as error:
            if primary is None:primary=error
    if primary is not None:raise primary

if __name__=="__main__":main()
