#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted synthetic authority/lifecycle/publication controls, no native payloads."""
import argparse,ast,copy,hashlib,io,json,os,sys,tarfile,tempfile,threading,types,unittest
from contextlib import ExitStack,redirect_stderr
from pathlib import Path
from unittest.mock import patch
import cdr_selector_width_fresh_rc_execution as e
import cloud_cdr_selector_width_fresh_rc as d
import check_cdr_selector_width_fresh_rc_source as inherited

RECORDS=[]
def record(label,kind,**extra):
    RECORDS.append(dict(case=label,kind=kind,**extra))

def enabled(method):
    value=copy.deepcopy(method)
    for name in e.NATIVE:value[name]=True
    value["source_controls_authorized"]=value["controller_readiness"]=True
    return value

def receipt():
    tag,head=e.release.context(e.GROUP,os.environ)
    return dict(schema="width-fresh-rc-reservation-v1",source_head=head,
      run_id=int(os.environ["GITHUB_RUN_ID"]),run_attempt=1,method_sha256=e.sha(e.METHOD),
      legacy_method_sha256=e.LEGACY_SHA,empty_before_dependencies=True,creation_attempted=False,
      release=dict(id=42,tag_name=tag,target_commitish=head,draft=False,prerelease=True,assets=[]),
      ref=dict(ref="refs/tags/"+tag,object=dict(type="commit",sha=head)))

class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.method=e.methods()
        cls.data=e.original.evidence.source_guard()
        cls.saved=e.original.evidence.validate_saved()

    def refuse(self,label,call,kind=AssertionError,contains=None):
        with self.assertRaises(kind)as caught:call()
        if contains:self.assertIn(contains,str(caught.exception))
        record(label,"refusal",error=repr(caught.exception))
        return caught.exception

    def test_real_source_guard_and_both_typed_authority_modes(self):
        legacy=e.original.methods()
        self.assertFalse(legacy["controller_readiness"])
        self.assertTrue(all(legacy[k]is False for k in e.NATIVE+e.FALSE))
        e.methods();record("actual complete new and historical source guards","positive")
        for on in (False,True):
            m=enabled(self.method)if on else copy.deepcopy(self.method)
            if not on:
                for name in e.NATIVE:m[name]=False
                m["controller_readiness"]=False
            e.validate_authorizations(m)
            for key in e.NATIVE+e.FALSE+("source_controls_authorized","controller_readiness"):
                bad=copy.deepcopy(m);bad[key]=1
                self.refuse("nonboolean "+str(on)+" "+key,lambda:e.validate_authorizations(bad))
            bad=copy.deepcopy(m);bad[e.NATIVE[0]]=not on
            self.refuse("split "+str(on),lambda:e.validate_authorizations(bad))
            bad=copy.deepcopy(m);bad["physical_accepted"]=True
            self.refuse("false acceptance "+str(on),lambda:e.validate_authorizations(bad))
        disabled=copy.deepcopy(self.method)
        for key in e.NATIVE:disabled[key]=False
        disabled["controller_readiness"]=False
        self.refuse("actual disabled hosted gate",lambda:e.context(disabled))
        real=e.sha;target=e.ROOT/e.ENTRIES["binding"]
        with patch.object(e,"sha",side_effect=lambda p:"0"*64 if Path(p)==target else real(p)):
            self.refuse("actual changed entry source",e.methods,contains="Changed execution source")
        record("both genuine typed authorization baselines","positive",modes=2)

    def test_actual_preflight_and_child_receipt_guards(self):
        value=receipt();calls=[];m=enabled(self.method)
        with tempfile.TemporaryDirectory(prefix="rc-reservation-fixture-",dir=e.ROOT)as temp:
            path=Path(temp)/"reservation.json"
            def api(name,missing=False):
                calls.append(name)
                return copy.deepcopy(value["release"]if name.startswith("releases/")else value["ref"])
            with patch.object(e,"methods",return_value=m),patch.object(e,"RESERVATION",path),              patch.object(e.release,"api",side_effect=api),patch.object(e,"wait",return_value={}):
                proof=e.preflight()
                self.assertEqual(proof["sha256"],e.sha(path));self.assertEqual(len(calls),2)
                with patch.dict(os.environ,{e.RESERVATION_ENV:e.sha(path)}):
                    self.assertEqual(e.authorize(),m)
                    self.assertEqual(e.reservation(m)["validated"]["release_id"],42)
                    self.refuse("receipt no clobber",e.preflight)
                    path.write_bytes(path.read_bytes()+b" ")
                    self.refuse("receipt hash changed",e.authorize)
                record("actual preflight and tokenless receipt validator","positive",synthetic_remote_metadata=True)
        for label,mutate in (
          ("old source",lambda r:r.__setitem__("source_head","b"*40)),
          ("old run",lambda r:r.__setitem__("run_id",int(os.environ["GITHUB_RUN_ID"])+1)),
          ("boolean run",lambda r:r.__setitem__("run_id",True)),
          ("repeated",lambda r:r.__setitem__("run_attempt",2)),
          ("other method",lambda r:r.__setitem__("method_sha256","b"*64)),
          ("historical method",lambda r:r.__setitem__("legacy_method_sha256","b"*64)),
          ("wrong release source",lambda r:r["release"].__setitem__("target_commitish","b"*40)),
          ("annotated ref",lambda r:r["ref"]["object"].__setitem__("type","tag")),
          ("preexisting assets",lambda r:r["release"]["assets"].append(
            dict(id=1,name="prior",size=0,digest="sha256:"+hashlib.sha256(b"").hexdigest()))),
          ("creation",lambda r:r.__setitem__("creation_attempted",True))):
            bad=copy.deepcopy(value);mutate(bad)
            self.refuse("reservation "+label,lambda:e.validate_reservation(bad,m))
        for key,value in (("GITHUB_RUN_ATTEMPT","2"),("GITHUB_EVENT_NAME","push"),
                          ("RUNNER_ENVIRONMENT","self-hosted"),("GITHUB_REPOSITORY","other/repo")):
            with patch.dict(os.environ,{key:value}):
                self.refuse("host context "+key,lambda:e.context(m))

    def test_exact_workers_and_scoped_entry_success_and_failure(self):
        for stage,path in e.WORKERS.items():
            raw,filename,ns=e.worker_namespace(stage)
            self.assertEqual(raw,(e.ROOT/path).read_bytes())
            self.assertEqual(ns["__file__"],str(e.ROOT/e.ENTRIES[stage]))
            self.assertEqual(ns["__name__"],"__main__")
            self.assertEqual(filename,e.ROOT/path)
        real=e.regular
        with patch.object(e,"regular",side_effect=lambda root,name:
          real(root,e.ENTRIES["binding"])if name==e.WORKERS["binding"]else real(root,name)):
            self.refuse("wrong worker bytes",lambda:e.worker_namespace("binding"))
        self.refuse("unknown entry",lambda:e.worker_namespace("invented"))
        original=e.original.authorize;workers=e.stages.WORKERS
        for fails in (False,True):
            calls=[];primary=RuntimeError("synthetic native collaborator failure")
            def gate():calls.append("gate");return enabled(self.method)
            def probe():
                self.assertIs(e.original.authorize,gate)
                self.assertEqual(e.stages.WORKERS,e.ENTRIES)
                e.original.authorize();calls.append("body")
                if fails:raise primary
            raw=b"probe()\n"
            with patch.object(e,"authorize",side_effect=gate)as actual_gate:
                # The active function object is the mock callable installed by worker_scope.
                def probe():
                    self.assertIs(e.original.authorize,actual_gate)
                    self.assertEqual(e.stages.WORKERS,e.ENTRIES)
                    e.original.authorize();calls.append("body")
                    if fails:raise primary
                with patch.object(e,"worker_namespace",return_value=(raw,e.ROOT/e.WORKERS["binding"],
                      dict(__name__="__main__",probe=probe))):
                    if fails:self.assertIs(self.refuse("entry primary",lambda:e.entry("binding"),RuntimeError),primary)
                    else:e.entry("binding")
            self.assertIs(e.original.authorize,original);self.assertIs(e.stages.WORKERS,workers)
            self.assertEqual(calls,["gate","gate","body"])
        with patch.object(e,"authorize",return_value=enabled(self.method)),          patch.object(e.stages,"WORKERS",dict(e.ENTRIES)):
            self.refuse("prepatched authority namespace",lambda:e.entry("binding"))
        record("five exact numerical sources and scoped entry restoration","positive",
          synthetic_entry_body=True,actual_numerical_main_executed=False)

    def test_actual_original_restore_under_new_scope(self):
        for mode in ("complete","transport"):
            with inherited.fixture(self.data,self.saved,mode)as(io,values):
                # Reuse exact full4103/current75 metadata and original restore clone.
                # The inherited fixture replaces archive/native byte I/O only.
                with patch.object(e.original,"authorize",e._ORIGINAL_AUTHORIZE),                  patch.object(e,"authorize",return_value=enabled(self.method)):
                    if mode=="transport":
                        self.assertIs(self.refuse("new entry transport primary",e.restore,RuntimeError),io.failure)
                    else:
                        pin=e.restore();self.assertEqual(pin["complete_graph_members"],4103)
                        self.assertEqual(pin["current_members"],75)
                        self.assertFalse((e.original.ANALYSIS/"result.json").exists())
                    self.assertIs(e.original.authorize,e._ORIGINAL_AUTHORIZE)
                    self.assertEqual(e.stages.WORKERS,e._ORIGINAL_WORKERS)
                self.assertTrue(io.clones and all(row["changed_globals"]==["authorize"]for row in io.clones))
        record("new scoped actual old restore clone","positive",synthetic_archive_IO=True,
          actual_archive_restoration_qualified=False)

    def test_original_controller_numerical_and_supervisor_boundaries(self):
        old=(e.ROOT/"scripts/cloud_cdr_v59_tail_fresh_rc.py").read_text()
        new=Path(d.__file__).read_text()
        defs=lambda text:{n.name:ast.dump(n,include_attributes=False)for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}
        a,b=defs(old),defs(new)
        for name in ("inventory","storage","tokenless","exception_record","execute","pipeline_validator",
                     "validate_completed_pipeline","finalization"):
            self.assertEqual(a[name],b[name],name)
        self.assertEqual(list(d.SECONDS.values()),[1200]*4)
        inherited.worker_derivations()
        self.assertEqual(d.pipeline_validator().__name__,"validate_pipeline")
        frozen=e.ROOT/"scripts/check_cdr_v59_tail_access_physical.py"
        scope=dict(json=json,Path=Path,tempfile=tempfile,gate=e.methods,
          c=types.SimpleNamespace(runtime=d.runtime,ROOT=e.ROOT,sha=e.sha))
        result=d.publication_helpers.load_definitions(frozen,["runtime_controls"],scope)["runtime_controls"]()
        self.assertEqual(len(result["supervisor"]["controls"]),13)
        self.assertEqual(len(result["all11_launcher_results_saved"]),11)
        self.assertFalse(result["actual_appimage_executed"]);self.assertFalse(result["native_executed"])
        record("unchanged worker/controller functions and actual qualified process controls","positive",
          native_executed=False,supervisor_cases=13,launcher_results=11)

    def test_actual_execute_timeout_stream_and_save_failures(self):
        for mode in ("timeout","changed_stream","save"):
            with tempfile.TemporaryDirectory()as temp:
                out=Path(temp);trace=out/"supervision";trace.mkdir()
                label=next(iter(d.SECONDS));argv=["synthetic","native"]
                primary=TimeoutError("original supervised timeout")
                def supervised(args,name,seconds,cwd):
                    self.assertEqual(seconds,1200)
                    for stream,raw in (("stdout",b"partial output"),("stderr",b"")):
                        (trace/(name+"."+stream)).write_bytes(raw)
                    command=dict(label=name,argv=args,returncode=1 if mode=="timeout"else 0,
                      supervision_failure="timeout"if mode=="timeout"else None,
                      process_group_cleanup=dict(remaining_live=[]))
                    for stream in ("stdout","stderr"):
                        p=trace/(name+"."+stream);command[stream+"_bytes"]=p.stat().st_size
                        command[stream+"_sha256"]=e.sha(p)
                    e.atomic(trace/(name+".command.json"),command)
                    if mode=="changed_stream":(trace/(name+".stdout")).write_bytes(b"changed")
                    if mode=="timeout":raise primary
                owned=types.SimpleNamespace(TRACE=trace,supervised=supervised)
                result=d.initial_result({},{});saved=OSError("save after command")
                with patch.object(d,"OUT",out):
                    if mode=="save":
                        with patch.object(d,"save_result",side_effect=saved):
                            self.assertIs(self.refuse("actual execute save",lambda:d.execute(owned,result,argv,label),OSError),saved)
                    elif mode=="timeout":
                        self.assertIs(self.refuse("actual execute timeout",lambda:d.execute(owned,result,argv,label),TimeoutError),primary)
                        self.assertEqual(result["commands"][0]["stderr_bytes"],0)
                    else:self.refuse("actual execute stream corruption",lambda:d.execute(owned,result,argv,label))
                self.assertTrue((trace/(label+".stdout")).exists())

    def test_actual_main_and_independent_finalization(self):
        for mode in ("complete","body","body_cleanup","stop","source","save","body_save"):
            with tempfile.TemporaryDirectory()as temp,ExitStack()as stack:
                root=Path(temp);out=root/"out";calls=[];primary=RuntimeError("body primary")
                secondary=OSError("terminal atomic replace failure");capture=io.StringIO()
                method=dict(protected_sha256={d.runtime.SAMPLER:"synthetic"})
                class Stop:
                    def set(self):
                        calls.append("stop")
                        if mode=="stop":raise RuntimeError("stop fault")
                class Owned:
                    TRACE=out/"supervision";ACTIVE=None;STOP=Stop()
                    def heartbeat(self):pass
                    def interrupted(self,*a):raise RuntimeError("unexpected signal")
                    def stop_process(self,p):
                        calls.append("cleanup")
                        if mode=="body_cleanup":raise RuntimeError("cleanup fault")
                    def sample(self,label):calls.append("sample");return {"synthetic":True}
                class Thread:
                    def __init__(self,**kw):pass
                    def start(self):calls.append("start")
                    def join(self,timeout):calls.append("join")
                    def is_alive(self):return False
                def body(result,*args):
                    (out/"partial.stdout").write_bytes(b"complete synthetic partial")
                    (out/"partial.stderr").write_bytes(b"")
                    calls.append("body")
                    if mode in ("body","body_cleanup","body_save"):raise primary
                    result.update(status=d.PASS,fresh_RC_pipeline_complete=True,binding_executed=True,extraction_executed=True)
                def method_check():
                    calls.append("source")
                    if mode=="source":raise AssertionError("source changed")
                    return method
                real_replace=os.replace;replaces=[]
                def replace(a,b):
                    if Path(b)==out/"result.json":
                        replaces.append((a,b))
                        if mode in ("save","body_save")and len(replaces)>=2:raise secondary
                    return real_replace(a,b)
                for obj,key,value in ((d,"OUT",out),(d,"TRANSPORT",root/"transport"),(d.stages,"ANALYSIS",root/"current"),
                    (d.stages,"PIN",root/"absent-pin")):
                    stack.enter_context(patch.object(obj,key,value))
                for obj,key,value in ((e,"authorize",lambda:method),(e,"reservation",lambda m:{}),
                    (e,"publication_authorize",lambda:{}),(d,"storage",lambda label:{}),
                    (e,"methods",method_check),(d.runtime,"supervisor",lambda *a:Owned()),
                    (d.threading,"Thread",Thread),(d,"run",body),(d.signal,"signal",lambda *a:lambda *b:None),
                    (e.os,"replace",replace)):
                    stack.enter_context(patch.object(obj,key,value))
                stack.enter_context(redirect_stderr(capture))
                if mode=="complete":self.assertEqual(d.main_run()["status"],d.PASS)
                elif mode in ("body","body_cleanup","body_save"):
                    self.assertIs(self.refuse("main "+mode,d.main_run,RuntimeError),primary)
                elif mode=="save":self.assertIs(self.refuse("main "+mode,d.main_run,OSError),secondary)
                else:self.refuse("main "+mode,d.main_run,Exception)
                self.assertIn("join",calls);self.assertIn("source",calls);self.assertIn("sample",calls)
                if mode in ("save","body_save"):
                    r=json.loads(capture.getvalue().splitlines()[-1])["unsaved_terminal_fresh_RC_result"]
                    self.assertFalse(r["fresh_RC_pipeline_complete"])
                    self.assertEqual(r["outputs"],{n:h for n,h in d.inventory(out).items()if n!="result.json"})
                    self.assertTrue(any(".incomplete."in n for n in r["outputs"]))
                else:
                    r=e.read_json(out/"result.json")
                    self.assertEqual(r["outputs"],{n:h for n,h in d.inventory(out).items()if n!="result.json"})
                json.dumps(r,allow_nan=False)
        record("seven actual outer main lifecycle paths","positive",native_body_is_synthetic=True)

    def test_save_fallback_encode_emit_and_inventory_cannot_mask_primary(self):
        for mode in ("encode","emit","inventory"):
            with tempfile.TemporaryDirectory()as temp,ExitStack()as stack:
                out=Path(temp);r=d.initial_result({},{});primary=OSError("primary atomic replace")
                stack.enter_context(patch.object(d,"OUT",out))
                stack.enter_context(patch.object(e.os,"replace",side_effect=primary))
                if mode=="encode":r["non_json"]=object()
                if mode=="emit":stack.enter_context(patch("builtins.print",side_effect=OSError("emit")))
                if mode=="inventory":stack.enter_context(patch.object(d,"output_map",side_effect=RuntimeError("inventory")))
                # For encode, atomic JSON encoding itself is the precise primary.
                if mode=="encode":
                    self.refuse("terminal encode remains primary",lambda:d.save_result(r),TypeError)
                else:self.assertIs(self.refuse("terminal "+mode,lambda:d.save_result(r),OSError),primary)

    def test_failed_envelopes_and_scope_refusals(self):
        for raw in (None,b"",b"{partial",b"[]"):
            with tempfile.TemporaryDirectory()as temp,patch.object(d,"OUT",Path(temp)):
                if raw is not None:(d.OUT/"result.json").write_bytes(raw)
                (d.OUT/"empty.stderr").write_bytes(b"")
                r=d.publication_result({})
                self.assertFalse(r["fresh_RC_pipeline_complete"])
                if raw is not None:self.assertEqual((d.OUT/"result.json").read_bytes(),raw)
                for key in d.FALSE:
                    bad=copy.deepcopy(r);bad[key]=True
                    self.refuse("publication scope "+key+repr(raw),lambda:d.validate_publication(bad))
                bad=copy.deepcopy(r);bad["status"]=d.PASS
                self.refuse("forged PASS "+repr(raw),lambda:d.validate_publication(bad))
                (d.OUT/"unlisted").write_bytes(b"changed")
                self.refuse("complete output drift "+repr(raw),lambda:d.validate_publication(r))

    def test_real_pack_publication_empty_failure_and_no_clobber(self):
        for mode in ("complete","upload","upload_save_emit"):
            with tempfile.TemporaryDirectory()as temp,ExitStack()as stack:
                root=Path(temp);out=root/"out";out.mkdir();transport=root/"transport"
                external=root/"driver.log";external.write_bytes(b"")
                (out/"binding").mkdir();(out/"binding/result.json").write_bytes(b"")
                (out/"binding/binding.json").write_bytes(b"{partial original")
                raw=b"{malformed terminal";(out/"result.json").write_bytes(raw)
                uploaded=[];primary=RuntimeError("upload original");old_hook=d.publisher.release
                def uploader(path,tag):
                    self.assertGreater(path.stat().st_size,0)
                    uploaded.append(path.name)
                    if mode!="complete":raise primary
                    return dict(name=path.name,bytes=path.stat().st_size,sha256=e.sha(path))
                for obj,key,value in ((d,"OUT",out),(d,"TRANSPORT",transport),(d,"DRIVER_LOG",external),
                    (d,"storage",lambda *a:{}),(e,"publication_authorize",lambda:{}),
                    (d.publisher,"publish",uploader)):
                    stack.enter_context(patch.object(obj,key,value))
                stack.enter_context(patch.object(e,"methods",side_effect=AssertionError("source proof changed")))
                real_atomic=e.atomic;count=[]
                def atomic(path,value):
                    if Path(path)==transport/"publication.json":
                        count.append(path)
                        if mode=="upload_save_emit"and len(count)>1:raise OSError("publication save")
                    return real_atomic(path,value)
                stack.enter_context(patch.object(e,"atomic",side_effect=atomic))
                if mode=="upload_save_emit":stack.enter_context(patch("builtins.print",side_effect=OSError("fallback emit")))
                r=d.publication_result({})
                if mode=="complete":self.assertEqual(d.publish(r)["status"],"PASS_COMPLETE_FRESH_WIDTH_RC_EVIDENCE_PUBLICATION_ONLY")
                else:self.assertIs(self.refuse("publication "+mode,lambda:d.publish(r),RuntimeError),primary)
                self.assertIs(d.publisher.release,old_hook)
                self.refuse("publication no-clobber "+mode,lambda:d.publish(r))
                self.assertEqual((out/"result.json").read_bytes(),raw)
                manifest=e.read_json(next(transport.glob("*.parts.json")))
                joined=b"".join((transport/row["name"]).read_bytes()for row in manifest["parts"])
                with tarfile.open(fileobj=io.BytesIO(joined),mode="r:gz")as archive:
                    for member,data in (("result.json",raw),("binding/result.json",b""),
                        ("binding/binding.json",b"{partial original"),("publication-driver.log",b"")):
                        self.assertEqual(archive.extractfile("out/"+member).read(),data)
                plan=e.read_json(next(transport.glob("*.direct-publication-plan.json")))
                rows={row["suffix"]:row for row in plan["files"]}
                for suffix in ("binding-result.json","driver.log"):
                    self.assertEqual(rows[suffix]["disposition"],"archive_only_empty")
                    self.assertEqual(rows[suffix]["sha256"],hashlib.sha256(b"").hexdigest())
                    self.assertEqual(rows[suffix]["bytes"],0)
                    self.assertFalse(any(n.endswith("."+suffix)for n in uploaded))
                self.assertFalse(r["fresh_RC_pipeline_complete"])
                self.assertEqual(r["status"],"FAIL_PROTECTED_SOURCE_AT_PUBLICATION")
        record("real pack and publication with explicit synthetic uploader","positive",native_payloads=False)

def main():
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);args=p.parse_args()
    assert os.environ.get("GITHUB_ACTIONS")=="true"and os.environ.get("RUNNER_ENVIRONMENT")=="github-hosted"
    assert os.environ.get("GITHUB_EVENT_NAME")=="workflow_dispatch"and os.environ.get("GITHUB_RUN_ATTEMPT")=="1"
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Controls)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    report=dict(status="PASS_FRESH_WIDTH_RC_EXECUTION_SOURCE_CONTROLS_ONLY"if result.wasSuccessful()else
      "FAIL_FRESH_WIDTH_RC_EXECUTION_SOURCE_CONTROLS",tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),
      records=RECORDS,positive_records=sum(r["kind"]=="positive"for r in RECORDS),
      refusal_records=sum(r["kind"]=="refusal"for r in RECORDS),
      source_head=os.environ["GITHUB_SHA"],run_id=int(os.environ["GITHUB_RUN_ID"]),run_attempt=1,
      method_sha256=e.sha(e.METHOD),historical_method_sha256=e.LEGACY_SHA,
      native_execution=False,native_payload_acquired=False,native_archive_restoration_qualified=False,
      fresh_RC_passed=False,qualified_pex=False,electrical_accepted=False,full_phy_accepted=False,
      boundaries="Actual authority/restore/main/finalization/pack/publication code; native payload I/O, native body and remote uploader explicitly synthetic.")
    e.atomic(args.output,report)
    print(json.dumps(report,sort_keys=True),flush=True)
    raise SystemExit(0 if result.wasSuccessful()else 1)

if __name__=="__main__":main()
