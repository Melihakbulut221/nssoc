#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted transport/lifecycle fixtures plus unchanged complete geometry controls."""
import contextlib,copy,io,json,os,shutil,subprocess,tempfile,time,types,unittest
from pathlib import Path
from unittest import mock
import check_mainchip_drt_obstacle_reduce as base
import cloud_mainchip_drt_obstacle_reduce as h
q=h.q

def inputs_fixture():
    report,scope=base.fixture()
    return {
      "native-result.json":report,"scope.json":scope,
      "host-result.json":dict(status="COMPLETE_READONLY_OBSTACLE_CLOUD_OBSERVATION",primary_error=None,terminal_errors=[],generated_output_preservation_complete=True),
      "inner-result.json":dict(status="COMPLETE_READONLY_OBSTACLE_ENGINE",terminal_errors=[]),
      "command.json":dict(returncode=0,supervision_failure=None,stderr_bytes=0,stderr_sha256=q.sha(b""),
        argv=["/work/engine/openroad","-no_init","-exit","-python","/work/tail-source/scripts/mainchip_drt_obstacle_native.py"],
        minimum_available_kib=2097152,maximum_group_rss_kib=10485760,
        process_group_cleanup=dict(remaining_live=[],remaining_nonrunning=[])),
      "progress.json":dict(stage="native-endpoint-census",observed_endpoint_names=scope["endpoint_names"],
        required_endpoint_names=scope["endpoint_names"],**{k:False for k in h.core.SOURCE_FLAGS})}

def producer_fixture():
    source="a"*40;run=701;release_id=702;tag="synthetic-source-tag"
    values=inputs_fixture();catalog=dict(source=source,run=run,files={});payload={};assets=[];selected={}
    def add_asset(name,raw):
        identity=800+len(assets);pin=dict(bytes=len(raw),sha256=q.sha(raw))
        assets.append(dict(id=identity,name=name,size=len(raw),digest="sha256:"+pin["sha256"],state="uploaded",download_count=0))
        payload[identity]=raw;return identity,pin
    for ordinal,name in enumerate(sorted(h.INPUT_NAMES)):
        member="synthetic/inputs/"+name;raw=q.encode(values[name]);asset_name=q.sha(member.encode())[:16]+"-"+name
        identity,pin=add_asset(asset_name,raw);catalog["files"][member]=dict(pin,name=asset_name,derived_text=True)
        selected[name]=dict(pin,member=member,asset_name=asset_name,asset_id=identity)
    for ordinal in range(36):
        member="synthetic/extra/record-"+str(ordinal)+".json";asset_name=q.sha(member.encode())[:16]+"-"+member.rsplit("/",1)[-1]
        _,pin=add_asset(asset_name,q.encode(dict(synthetic_extra=ordinal)))
        catalog["files"][member]=dict(pin,name=asset_name,derived_text=True)
    for ordinal in range(12):
        catalog["files"]["synthetic/empty/"+str(ordinal)+".log"]=dict(bytes=0,sha256=q.sha(b""),name=None,derived_text=True,embedded_empty=True)
    _,catalog_pin=add_asset("readback-catalog.json",q.encode(catalog))
    receipt=dict(source=source,run=run,release_id=release_id,tag=tag,receipt_self_not_in_files=True,
      files={a["name"]:dict(bytes=a["size"],sha256=a["digest"][7:])for a in assets})
    _,receipt_pin=add_asset("publication-receipt.json",q.encode(receipt))
    release=dict(id=release_id,tag_name=tag,target_commitish=source,draft=False,prerelease=True,assets=assets)
    config=dict(producer=dict(run_id=run,source=source,release_id=release_id,tag=tag,branch="synthetic-fixture",attempt=1,
      workflow=".github/workflows/cloud-evidence-summary.yml",immutable_release=q.immutable_release(release),
      catalog_pin=catalog_pin,publication_receipt_pin=receipt_pin),inputs=selected)
    jobs=dict(total_count=3,jobs=[dict(id=900+i,name=name,status="completed",conclusion="success",head_sha=source,run_id=run,run_attempt=1)
      for i,name in enumerate(("source-controls","preserve-job-log","observation"))])
    responses={
      "actions/runs/"+str(run):dict(id=run,status="completed",conclusion="success",head_sha=source,
        head_branch="synthetic-fixture",run_attempt=1,path=config["producer"]["workflow"]),
      "releases/"+str(release_id):release,
      "git/ref/tags/"+tag:dict(object=dict(type="commit",sha=source)),
      "actions/runs/"+str(run)+"/attempts/1/jobs?per_page=100":jobs}
    def api(path,raw=False):
        if path.startswith("releases/assets/"):
            if raw is not True:raise AssertionError("metadata acquisition mode")
            return payload[int(path.rsplit("/",1)[-1])]
        if raw:raise AssertionError("unexpected raw metadata")
        return copy.deepcopy(responses[path])
    return config,values,responses,payload,api

class HostControls(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="synthetic-obstacle-reduction-")
        self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.out=self.root/"out";self.out.mkdir()
        self.patch=mock.patch.object(h,"OUT",self.out);self.patch.start();self.addCleanup(self.patch.stop)
        self.ctx=dict(source="b"*40,run=703,attempt=1)
    def test_complete_producer_all_44_assets_54_members(self):
        c,v,res,payload,api=producer_fixture();before=q.encode(c);actual=h.producer(c,api)
        self.assertEqual(len(actual["release"]["assets"]),44);self.assertEqual(len(actual["catalog"]["files"]),54)
        self.assertEqual(set(c["inputs"]),h.INPUT_NAMES);self.assertEqual(q.encode(c),before)
    def test_producer_run_job_tag_identity_refusals(self):
        for label,change in(
          ("run",lambda c,r:r["actions/runs/701"].update(head_sha="f"*40)),
          ("branch",lambda c,r:r["actions/runs/701"].update(head_branch="changed")),
          ("attempt",lambda c,r:r["actions/runs/701"].update(run_attempt=2)),
          ("job",lambda c,r:r["actions/runs/701/attempts/1/jobs?per_page=100"]["jobs"][0].update(conclusion="failure")),
          ("tag",lambda c,r:r["git/ref/tags/synthetic-source-tag"]["object"].update(type="tag"))):
            with self.subTest(label=label):
                c,v,r,p,api=producer_fixture();change(c,r)
                with self.assertRaises(ValueError):h.producer(c,api)
    def test_complete_assets_and_selected_kind_refusals(self):
        for label,change in(
          ("missing",lambda c,r:r["releases/702"]["assets"].pop()),
          ("digest",lambda c,r:r["releases/702"]["assets"][0].update(digest="sha256:"+"0"*64)),
          ("uploading",lambda c,r:r["releases/702"]["assets"][0].update(state="new")),
          ("target",lambda c,r:r["releases/702"].update(target_commitish="f"*40)),
          ("selected-id",lambda c,r:c["inputs"]["scope.json"].update(asset_id=99999)),
          ("selected-sha",lambda c,r:c["inputs"]["scope.json"].update(sha256="f"*64))):
            with self.subTest(label=label):
                c,v,r,p,api=producer_fixture();change(c,r)
                with self.assertRaises((ValueError,KeyError)):h.producer(c,api)
    def test_mutable_download_count_does_not_change_identity(self):
        c,v,r,p,api=producer_fixture();r["releases/702"]["assets"][0]["download_count"]=999
        self.assertEqual(h.producer(c,api)["release"]["assets"][0]["download_count"],999)
    def test_selected_native_command_and_all_progress_refusals(self):
        values=inputs_fixture();h.validate_selected_inputs(values,{})
        cases=[
          lambda v:v["host-result.json"].update(primary_error="failed"),
          lambda v:v["inner-result.json"].update(terminal_errors=["failed"]),
          lambda v:v["command.json"].update(returncode=-11),
          lambda v:v["command.json"].update(supervision_failure="timeout"),
          lambda v:v["command.json"].update(stderr_bytes=1),
          lambda v:v["command.json"]["argv"].append("-changed"),
          lambda v:v["command.json"].update(maximum_group_rss_kib=99999999),
          lambda v:v["command.json"]["process_group_cleanup"]["remaining_live"].append(1),
          lambda v:v["progress.json"].update(observed_endpoint_names=[]),
          lambda v:v["progress.json"].update(physical_acceptance=True)]
        for change in cases:
            with self.subTest(change=str(change)):
                v=copy.deepcopy(values);change(v)
                with self.assertRaises(ValueError):h.validate_selected_inputs(v,{})
    def test_strict_json_duplicate_nonfinite_and_encoding(self):
        for i,raw in enumerate((b'{"x":1,"x":2}',b'{"x":NaN}',b'{"x":"\xff"}')):
            p=self.root/("bad"+str(i)+".json");p.write_bytes(raw)
            with self.assertRaises((ValueError,UnicodeError)):h.decode_file(p)
        p=self.root/"good.json";p.write_bytes(b'{"x":[1,true,null]}')
        self.assertEqual(h.decode_file(p),dict(x=[1,True,None]))
    def fake_download(self,raw,returncode=0,error=None):
        def execute(argv,stdout,stderr,timeout,check,preexec_fn):
            self.assertEqual(argv[:3],["gh","api","--allow-escape-sequences"])
            self.assertEqual(argv[-2:],["-H","Accept: application/octet-stream"])
            self.assertEqual(timeout,300);self.assertIs(check,False)
            with mock.patch.object(h.resource,"setrlimit")as bound:preexec_fn()
            self.last_bound=bound.call_args.args
            stdout.write(raw);stderr.write(b"synthetic retained diagnostic\n"if returncode or error else b"")
            if error is not None:raise error
            return types.SimpleNamespace(returncode=returncode)
        return execute
    def test_download_exact_stream_sha_and_bounded_child(self):
        inputs=self.root/"inputs";inputs.mkdir();raw=b'{"fixture":"exact"}\n';pin=dict(bytes=len(raw),sha256=q.sha(raw),asset_id=99)
        with mock.patch.object(h.subprocess,"run",side_effect=self.fake_download(raw)):
            p=h.download("scope.json",pin,inputs)
        self.assertEqual(p.read_bytes(),raw)
        self.assertEqual(self.last_bound,(h.resource.RLIMIT_FSIZE,(1024*1024,1024*1024)))
        record=q.decode((self.out/"scope.json.download.json").read_bytes())
        self.assertEqual(record["received"],{k:pin[k]for k in("bytes","sha256")});self.assertEqual(record["returncode"],0)
    def test_download_mismatch_retains_complete_partial_and_record(self):
        inputs=self.root/"inputs";inputs.mkdir();raw=b'{"extra":"bytes"}\n';pin=dict(bytes=1,sha256=q.sha(b"x"),asset_id=99)
        with mock.patch.object(h.subprocess,"run",side_effect=self.fake_download(raw)):
            with self.assertRaisesRegex(ValueError,"size/SHA256"):h.download("scope.json",pin,inputs)
        self.assertEqual((inputs/"scope.json").read_bytes(),raw)
        self.assertIn("error",q.decode((self.out/"scope.json.download.json").read_bytes()))
    def test_download_failure_and_timeout_primary_survive_save_failure(self):
        inputs=self.root/"inputs";inputs.mkdir();primary=subprocess.TimeoutExpired(["synthetic"],300)
        with mock.patch.object(h.subprocess,"run",side_effect=self.fake_download(b"partial",error=primary)),mock.patch.object(h,"write",side_effect=OSError("save")),contextlib.redirect_stdout(io.StringIO())as captured:
            with self.assertRaises(subprocess.TimeoutExpired)as raised:h.download("scope.json",dict(bytes=99,sha256="a"*64,asset_id=99),inputs)
        self.assertIs(raised.exception,primary);self.assertEqual((inputs/"scope.json").read_bytes(),b"partial")
        self.assertIn("UNSAVED_DOWNLOAD_RECORD",captured.getvalue());self.assertTrue((self.out/"scope.json.download.stderr.log").read_bytes())
    def test_download_nonzero_cannot_pass_with_exact_payload(self):
        inputs=self.root/"inputs";inputs.mkdir();raw=b"{}";pin=dict(bytes=2,sha256=q.sha(raw),asset_id=99)
        with mock.patch.object(h.subprocess,"run",side_effect=self.fake_download(raw,returncode=7)):
            with self.assertRaisesRegex(ValueError,"download failed"):h.download("scope.json",pin,inputs)
        self.assertEqual(q.decode((self.out/"scope.json.download.json").read_bytes())["returncode"],7)
    def test_same_source_controls_full_log_and_exact_count(self):
        jobs=dict(total_count=3,jobs=[dict(id=100+i,name=n,head_sha=self.ctx["source"],run_id=self.ctx["run"],run_attempt=1,
          status="in_progress"if n=="analysis"else"completed",conclusion=None if n=="analysis"else"success")
          for i,n in enumerate(("source-controls","preserve-job-log","analysis"))])
        record=dict(source=self.ctx["source"],status="PASS_SOURCE_ONLY_OBSTACLE_REDUCTION_CONTROLS",tests_run=h.EXPECTED_CONTROLS,
          successful=True,failures=0,errors=0,skipped=0,native_acquired=False,native_executed=False,actual_report_acquired=False)
        raw=("2026-10-31T00:00:00.000Z arbitrary retained log\n2026-10-31T00:00:01.000Z MAINCHIP_OBSTACLE_REDUCTION_CONTROLS "+json.dumps(record)+"\n").encode()
        with mock.patch.object(h.subprocess,"check_output",return_value=raw):
            self.assertEqual(h.same_source_controls(self.ctx,lambda p:copy.deepcopy(jobs)),record)
        self.assertEqual((self.out/"same-source-controls.log").read_bytes(),raw)
        for bad in(raw+raw,raw.replace(str(h.EXPECTED_CONTROLS).encode(),b"1"),raw.replace(b'"skipped": 0',b'"skipped": 1')):
            with mock.patch.object(h.subprocess,"check_output",return_value=bad):
                with self.assertRaises(ValueError):h.same_source_controls(self.ctx,lambda p:copy.deepcopy(jobs))
    def test_publication_exact_files_receipt_last_and_empty_embedded(self):
        h.write("result.json",dict(status="SYNTHETIC",**h.core.FLAGS))
        (self.out/"scope.json.download.stderr.log").write_bytes(b"");uploaded=[];states=[]
        def dest(ctx,empty,expected=None):
            states.append((empty,copy.deepcopy(expected)))
            if expected is not None:
                self.assertEqual(set(expected),set(uploaded))
                for name,pin in expected.items():self.assertEqual(pin,q.pin(self.out/name))
            return"synthetic-publication",dict(id=999)
        def upload(argv,check,timeout):
            self.assertEqual(argv[:3],["gh","release","upload"]);self.assertTrue(check)
            uploaded.append(Path(argv[4]).name);return types.SimpleNamespace(returncode=0)
        with mock.patch.object(h,"destination",side_effect=dest),mock.patch.object(h.subprocess,"run",side_effect=upload):h.publication(self.ctx)
        self.assertEqual(uploaded,["result.json","readback-catalog.json","publication-receipt.json"])
        catalog=q.decode((self.out/"readback-catalog.json").read_bytes())
        self.assertTrue(catalog["files"]["scope.json.download.stderr.log"]["embedded_empty"])
        self.assertEqual(len(states[-1][1]),3)
    def test_publication_unknown_native_composite_and_binary_stay_cloud_only(self):
        for name,raw in(("native.gds.json",b"{}"),("unknown.json",b"{}"),(".hidden.json",b"{}"),("result.json",b"\xff")):
            with self.subTest(name=name):
                p=self.out/name;p.write_bytes(raw)
                with mock.patch.object(h,"destination",return_value=("synthetic",dict(id=999))),mock.patch.object(h.subprocess,"run")as upload:
                    with self.assertRaises((ValueError,UnicodeError)):h.publication(self.ctx)
                    upload.assert_not_called()
                self.assertEqual(p.read_bytes(),raw);p.unlink()
    def test_finish_save_before_publication_and_primary_identity(self):
        primary=ValueError("original");save=OSError("save");pub=RuntimeError("publication");events=[]
        def writer(*args):events.append("save");raise save
        def publisher(*args):events.append("publish");raise pub
        with mock.patch.object(h,"write",side_effect=writer),contextlib.redirect_stdout(io.StringIO())as captured:
            self.assertIs(h.finish(self.ctx,dict(status="failed"),True,primary,publisher),primary)
        self.assertEqual(events,["save","publish"]);self.assertIn("UNSAVED_REDUCTION_RESULT",captured.getvalue());self.assertIn("REDUCTION_PUBLICATION_FAILURE",captured.getvalue())
    def test_finish_first_save_error_and_publication_error_not_lost(self):
        save=OSError("save");pub=RuntimeError("publication")
        with mock.patch.object(h,"write",side_effect=save),contextlib.redirect_stdout(io.StringIO()):
            self.assertIs(h.finish(self.ctx,{},True,None,lambda c:(_ for _ in()).throw(pub)),save)
        with mock.patch.object(h,"write"),contextlib.redirect_stdout(io.StringIO()):
            self.assertIs(h.finish(self.ctx,{},True,None,lambda c:(_ for _ in()).throw(pub)),pub)
    def test_finish_success_and_unreserved_failure(self):
        events=[]
        with mock.patch.object(h,"write",side_effect=lambda *a:events.append("save")):
            self.assertIsNone(h.finish(self.ctx,{},True,None,lambda c:events.append("publish")))
            self.assertIsNone(h.finish(self.ctx,{},False,None,lambda c:self.fail("unreserved publication")))
        self.assertEqual(events,["save","publish","save"])
    def test_destination_uses_same_code_without_original_namespace_mutation(self):
        before=q.destination.__globals__["GROUP"];observed={}
        def api(path,raw=False):
            observed.setdefault("paths",[]).append(path)
            tag="cloud-results-"+os.environ["GITHUB_RUN_ID"]+"-"+os.environ["GITHUB_RUN_ATTEMPT"]+"-"+h.GROUP
            if path.startswith("git/ref/"):return dict(object=dict(type="commit",sha=self.ctx["source"]))
            return dict(id=999,tag_name=tag,target_commitish=self.ctx["source"],draft=False,prerelease=True,assets=[])
        with mock.patch.dict(q.destination.__globals__,{"api":api}):
            tag,release=h.destination(self.ctx,True)
        self.assertTrue(tag.endswith(h.GROUP));self.assertEqual(release["id"],999)
        self.assertEqual(q.destination.__globals__["GROUP"],before)
    def test_full_host_synthetic_pipeline_preserves_every_core_record(self):
        c,values,responses,payload,api=producer_fixture();self.out.rmdir()
        ctx=dict(source="b"*40,run=time.time_ns(),attempt=1)
        work=Path(os.environ["RUNNER_TEMP"])/(h.GROUP+"-"+str(ctx["run"])+"-1")
        self.addCleanup(lambda:shutil.rmtree(work,ignore_errors=True))
        original_producer=h.producer;published=[]
        def execute(argv,stdout,stderr,timeout,check,preexec_fn):
            asset_id=int(argv[3].rsplit("/",1)[-1]);stdout.write(payload[asset_id]);return types.SimpleNamespace(returncode=0)
        with contextlib.ExitStack()as stack:
            stack.enter_context(mock.patch.object(h,"actual_context",return_value=(ctx,c)))
            stack.enter_context(mock.patch.object(h,"same_source_controls",return_value={"synthetic":True}))
            stack.enter_context(mock.patch.object(h,"destination",return_value=("synthetic",dict(id=999))))
            stack.enter_context(mock.patch.object(h,"producer",side_effect=lambda config:original_producer(config,api)))
            stack.enter_context(mock.patch.object(h.subprocess,"run",side_effect=execute))
            stack.enter_context(mock.patch.object(h,"source_gate",return_value=ctx["source"]))
            bound=stack.enter_context(mock.patch.object(h.resource,"setrlimit"))
            alarm=stack.enter_context(mock.patch.object(h.signal,"alarm"))
            stack.enter_context(mock.patch.object(h.signal,"signal"))
            original_finish=h.finish
            stack.enter_context(mock.patch.object(h,"finish",side_effect=lambda cx,r,res,p:original_finish(cx,r,res,p,lambda cx:published.append(cx))))
            with contextlib.redirect_stdout(io.StringIO()):h.run()
        result=q.decode((self.out/"result.json").read_bytes())
        self.assertEqual(result["status"],"COMPLETE_AUTHENTICATED_PREROUTE_OBSTACLE_REDUCTION")
        self.assertEqual((result["selected_markers"],result["endpoints"]),(434,373))
        expected=[(mi,wi,w["record_id"])for mi,m in enumerate(values["native-result.json"]["markers"])for wi,w in enumerate(m["endpoint_witnesses"])]
        rows=[q.decode(line)for line in(self.out/"witnesses.jsonl").read_bytes().splitlines()]
        self.assertEqual([(w["source_marker_index"],w["source_witness_index"],w["record_id"])for w in rows],expected)
        self.assertEqual(published,[ctx]);self.assertFalse(work.exists())
        bound.assert_called_once_with(h.resource.RLIMIT_AS,(8*1024**3,8*1024**3))
        self.assertIn(mock.call(900),alarm.call_args_list);self.assertIn(mock.call(0),alarm.call_args_list)
    def test_actual_authority_still_refused_without_environment_spoofing(self):
        before=dict(os.environ)
        with self.assertRaises(ValueError):h.actual_context()
        self.assertEqual(dict(os.environ),before)
    def test_exclusive_output_and_complete_output_size_guard(self):
        h.write("result.json",dict(value=1))
        with self.assertRaises(FileExistsError):h.write("result.json",dict(value=2))
        with mock.patch.object(h,"MAX_OUTPUT_BYTES",2):
            with self.assertRaises(ValueError):h.write("markers.json",dict(complete=True))
        self.assertFalse((self.out/"markers.json").exists())
    def test_small_asset_bound_and_exact_digest(self):
        raw=b"{}";asset=dict(id=999,state="uploaded",size=2,digest="sha256:"+q.sha(raw));pin=dict(bytes=2,sha256=q.sha(raw))
        self.assertEqual(h.small_asset(asset,pin,lambda p,raw: b"{}"),b"{}")
        with self.assertRaises(ValueError):h.small_asset(dict(asset,digest="sha256:"+"f"*64),pin,lambda *a:self.fail("bad asset downloaded"))
        huge=dict(bytes=2*1024*1024+1,sha256="a"*64)
        with self.assertRaises(ValueError):h.small_asset(dict(asset,size=huge["bytes"],digest="sha256:"+huge["sha256"]),huge,lambda *a:self.fail("oversized metadata downloaded"))

def main():
    head=h.source_gate("controls");stream=io.StringIO()
    suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(base.FullReductionControls),
                             unittest.defaultTestLoader.loadTestsFromTestCase(HostControls)])
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite);raw=stream.getvalue();print(raw,end="")
    record=dict(status="PASS_SOURCE_ONLY_OBSTACLE_REDUCTION_CONTROLS"if result.wasSuccessful()else"FAIL_SOURCE_CONTROLS",
      source=head,tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),
      successful=result.wasSuccessful(),native_acquired=False,native_executed=False,actual_report_acquired=False,
      full_synthetic_census=dict(markers=434,endpoints=373,original_records=596),log_sha256=q.sha(raw.encode()))
    print("MAINCHIP_OBSTACLE_REDUCTION_CONTROLS "+json.dumps(record,sort_keys=True),flush=True)
    q.require(result.testsRun==h.EXPECTED_CONTROLS and result.wasSuccessful()and not result.skipped,"all exact host/core controls passed without skips")
if __name__=="__main__":main()
