#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Synthetic full-input transport, publication, lifecycle and source-admission controls."""
import ast,base64,copy,hashlib,io,json,os,subprocess,tarfile,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
import cloud_mainchip_drt_obstacle_readback as h
q=h.q;k=h.k
class Controls(unittest.TestCase):
    def env(self):
        return dict(GITHUB_ACTIONS="true",GITHUB_REPOSITORY="Melihakbulut221/nssoc",GITHUB_EVENT_NAME="workflow_dispatch",
          GITHUB_REF="refs/heads/codex/mainchip-drt-obstacle-readback",GITHUB_SHA="a"*40,GITHUB_RUN_ID="123",GITHUB_RUN_ATTEMPT="1",
          RUNNER_ENVIRONMENT="github-hosted",RUNNER_OS="Linux",GITHUB_JOB="observation",MODE="observation",APPROVED_SOURCE="a"*40)
    def ctx(self):return h.context(self.env(),"a"*40)
    def actual(self):
        ctx=self.ctx();run=dict(id=123,head_sha=ctx["source"],head_branch="codex/mainchip-drt-obstacle-readback",event="workflow_dispatch",
          run_attempt=1,path=".github/workflows/cloud-evidence-summary.yml",workflow_id=382556685,status="in_progress")
        jobs=dict(total_count=3,jobs=[dict(id=i,head_sha=ctx["source"],run_id=123,run_attempt=1,name=n,status="in_progress"if n=="observation"else"completed",
          conclusion=None if n=="observation"else"success",steps=[dict(status="completed",conclusion="success")])for i,n in enumerate(("source-controls","preserve-job-log","observation"),1)])
        return run,jobs
    def test_actual_environment_forwarding_and_native_job_scope(self):
        ctx=self.ctx();e=self.env();saved=dict(e);args=h.hosted_argv(ctx,Path("/tmp/explicit-synthetic-work"),1001,1001,e)
        self.assertEqual(e,saved);self.assertEqual(args[:2],["docker","create"])
        self.assertIn("GITHUB_SHA="+ctx["source"],args);self.assertIn("GITHUB_REF="+e["GITHUB_REF"],args)
        self.assertNotIn("GH_TOKEN",str(args));self.assertEqual(args[-1],"/work/inner.py")
        for key,val in(("RUNNER_ENVIRONMENT","self-hosted"),("RUNNER_OS","Windows"),("GITHUB_JOB","source-controls"),
          ("MODE","controls"),("APPROVED_SOURCE","b"*40),("GITHUB_REF","refs/heads/main")):
            with self.assertRaises(ValueError):h.context({**e,key:val},"a"*40)
    def test_actual_source_prerequisites_and_complete_job_identity(self):
        ctx=self.ctx();run,jobs=self.actual();self.assertEqual(h.current_run(ctx,run,jobs),1)
        for key,val in(("id",124),("head_sha","b"*40),("head_branch","main"),("event","push"),("run_attempt",2),("status","completed")):
            with self.assertRaises(ValueError):h.current_run(ctx,{**run,key:val},jobs)
        for index,key,value in((0,"conclusion","failure"),(1,"status","in_progress"),(2,"status","completed"),(0,"head_sha","b"*40),(2,"run_id",124)):
            bad=copy.deepcopy(jobs);bad["jobs"][index][key]=value
            with self.assertRaises(ValueError):h.current_run(ctx,run,bad)
        bad=copy.deepcopy(jobs);bad["jobs"].pop()
        with self.assertRaises(ValueError):h.current_run(ctx,run,bad)
    def result(self):
        return dict(status="PASS_OBSTACLE_ADAPTER_SOURCE_CONTROLS",source="a"*40,run=123,attempt=1,tests_run=40,
          failures=0,errors=0,skipped=0,successful=True,test_ids=h.expected_test_ids(),native_acquired=False,native_tools_executed=False,**k.FLAGS)
    def log(self,r):return b"2026-10-31T19:00:00.000Z MAINCHIP_OBSTACLE_CONTROLS "+json.dumps(r,sort_keys=True).encode()+b"\n"
    def test_complete_raw_control_log_source_inventory_and_refusals(self):
        r=self.result();raw=self.log(r);self.assertEqual(h.control_log(raw,self.ctx())["result"],r)
        for key,val in(("source","b"*40),("run",124),("attempt",2),("tests_run",39),("errors",1),("skipped",1),
          ("native_acquired",True),("physical_cause_proven",True),("successful",False),("test_ids",r["test_ids"][:-1]+["unrelated.test"])):
            with self.subTest(key=key),self.assertRaises(ValueError):h.control_log(self.log({**r,key:val}),self.ctx())
        for bad in(raw+raw,b"echo "+raw,b"MAINCHIP_OBSTACLE_CONTROLS {bad}\n",b"\xff"):
            with self.assertRaises((ValueError,UnicodeError)):h.control_log(bad,self.ctx())
    def test_pinned_input_config_and_census_refusals(self):
        c=q.decode((h.ROOT/h.CONFIG).read_bytes());k.validate_config(c)
        for key,val in(("expected_report_records",595),("expected_selected_metal2_shorts",433),("native_routing_authorized",True),("native_readonly_authorized",1)):
            bad=copy.deepcopy(c);bad[key]=val
            with self.assertRaises(ValueError):k.validate_config(bad)
        for mutate in(lambda x:x["selected_members"].pop(next(iter(x["selected_members"]))),
          lambda x:x["producer"]["members"].pop(next(iter(x["producer"]["members"]))),
          lambda x:x["analysis_result"].__setitem__("source","b"*40),
          lambda x:x["selected_members"]["work/bulk-postdrt-antenna/stale-wire-cleared.odb"].__setitem__("bytes",1)):
            bad=copy.deepcopy(c);mutate(bad)
            with self.assertRaises((ValueError,KeyError)):k.validate_config(bad)
    def acquisition_fixture(self,root,corrupt=False):
        selected=["work/bulk-postdrt-antenna/stale-wire-cleared.odb","work/bulk-postdrt-antenna/fixed-routing.drc-10.rpt",
          "bulk-postdrt-antenna/insertion-plan.json","bulk-postdrt-antenna/stale-wire-mutation.json"]
        payload={n:("EXPLICIT_SYNTHETIC_INPUT "+n+"\n").encode()for n in selected}
        payload.update({"other/member"+str(i):("synthetic"+str(i)).encode()for i in range(731)})
        pin=lambda b:dict(bytes=len(b),sha256=q.sha(b));members={n:pin(b)for n,b in payload.items()}
        stream=io.BytesIO()
        with tarfile.open(fileobj=stream,mode="w:gz")as tar:
            for n,b in payload.items():info=tarfile.TarInfo(n);info.size=len(b);tar.addfile(info,io.BytesIO(b))
        archive=stream.getvalue()
        if corrupt:members["other/member1"]["sha256"]="0"*64
        index=dict(run=41211382427,source="ddc1cbddf68096c5e976bf9acda5c5fb0168c5b9",attempt=1,files=members,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
        parts=dict(archive=pin(archive),parts=[dict(name="candidate-native.tar.gz.part000",**pin(archive))])
        assets={"candidate-outputs.json":q.encode(index),"candidate-parts.json":q.encode(parts),"candidate-native.tar.gz.part000":archive}
        producer=dict(producer_run=index["run"],producer_source=index["source"],assets={n:dict(id=i,**pin(b))for i,(n,b)in enumerate(assets.items())},members=members,parts=parts)
        analysis=b'{"explicitly_synthetic_analysis":true}\n'
        config=dict(producer=producer,selected_members={n:members[n]for n in selected},analysis_result=dict(asset_id=777,pin=pin(analysis)))
        release=dict(id=1,tag_name="synthetic",target_commitish=index["source"],draft=False,prerelease=True,assets=[])
        envelope=dict(release=release,ref={"explicit":"synthetic"},run={"explicit":"synthetic"})
        def download(c,n,dest):dest.write_bytes(assets[n]);self.assertEqual(q.pin(dest),{k:c["assets"][n][k]for k in("bytes","sha256")})
        work=root/"work";work.mkdir();out=root/"out";out.mkdir()
        with patch.object(q,"producer",return_value=envelope),patch.object(h,"analysis_producer",return_value=envelope),patch.object(q,"download",side_effect=download),patch.object(q,"api",return_value=analysis):
            result=h.acquire(config,work,out)
        self.assertEqual({p.relative_to(result).as_posix()for p in result.rglob("*")if p.is_file()},set(selected)|{"hosted-analysis.json"})
        admission=q.decode((out/"selected-input-admission.json").read_bytes())
        self.assertEqual(len(admission["all_members"]),735);self.assertTrue(admission["all735_authenticated"])
    def test_full735_synthetic_transport_and_unselected_corruption(self):
        with tempfile.TemporaryDirectory()as d:self.acquisition_fixture(Path(d))
        with tempfile.TemporaryDirectory()as d:
            with self.assertRaisesRegex(AssertionError,"native member digest other/member1"):self.acquisition_fixture(Path(d),True)
    def test_preservation_independent_failure_and_unexpected_native_bytes(self):
        with tempfile.TemporaryDirectory()as d:
            root=Path(d);work=root/"work";out=work/"out";out.mkdir(parents=True);evidence=root/"evidence";evidence.mkdir()
            for n,b in(("a.json",b"{}\n"),("b.json",b"{}\n"),("unexpected.odb",b"EXPLICIT_SYNTHETIC_NATIVE_BYTES"),("native.odb.partial",b"\xff\x00"),("native.partial",b"\xfe"),("bad.json",b"\xff"),("events.jsonl.partial",b'{"partial_record":true}\n')):(out/n).write_bytes(b)
            (out/"work").mkdir();(out/"work/frozen.odb").write_bytes(b"EXPLICIT_UNCHANGED_INPUT")
            report=dict(terminal_errors=[]);real=h.shutil.copyfile
            def copyfile(src,dest):
                if Path(src).name=="a.json":raise OSError("synthetic one-file retention error")
                return real(src,dest)
            with patch.object(h.shutil,"copyfile",side_effect=copyfile):h.preserve_outputs(work,out,evidence,report)
            self.assertFalse(report["generated_output_preservation_complete"])
            self.assertEqual(set(report["generated_output_inventory"]),{"b.json","unexpected.odb","native.odb.partial","native.partial","bad.json","events.jsonl.partial"})
            self.assertFalse(report["generated_output_inventory"]["unexpected.odb"]["derived_text"])
            for name in("native.odb.partial","native.partial","bad.json"):self.assertFalse(report["generated_output_inventory"][name]["derived_text"])
            self.assertTrue(report["generated_output_inventory"]["events.jsonl.partial"]["derived_text"])
            self.assertFalse((evidence/"native/work").exists());self.assertEqual(len(report["terminal_errors"]),1)
    def test_complete_publication_catalog_and_no_retry_after_upload_failure(self):
        for fail in(False,True):
            with self.subTest(fail=fail),tempfile.TemporaryDirectory()as d:
                out=Path(d)/"evidence";out.mkdir();(out/"result.json").write_bytes(b"{}\n");(out/"empty.stderr").write_bytes(b"");(out/"unexpected.odb").write_bytes(b"SYNTHETIC");(out/"native.odb.partial").write_bytes(b"\xff");(out/"valid.jsonl.partial").write_bytes(b'{"synthetic":true}\n')
                ctx=self.ctx();proof=dict(tag="synthetic",release_id=9);published={};calls=[]
                def destination(ctx,empty,expected=None):
                    if empty:self.assertEqual(published,{})
                    if expected is not None:self.assertEqual(published,expected)
                    return"synthetic",dict(id=9)
                def upload(argv,**kw):
                    calls.append(argv);self.assertEqual(argv[:3],["gh","release","upload"]);self.assertNotIn("--clobber",argv)
                    if fail:raise subprocess.CalledProcessError(1,argv)
                    p=Path(argv[4]);self.assertNotIn(p.name,published);published[p.name]=q.pin(p)
                with patch.object(h,"destination",side_effect=destination),patch.object(h.subprocess,"run",side_effect=upload):
                    if fail:
                        with self.assertRaises(subprocess.CalledProcessError):h.publication(ctx,proof,out)
                        self.assertEqual(len(calls),1)
                    else:
                        h.publication(ctx,proof,out)
                        catalog=q.decode((out.parent/"obstacle-publication/readback-catalog.json").read_bytes())
                        self.assertEqual(set(catalog["files"]),{"result.json","empty.stderr","unexpected.odb","native.odb.partial","valid.jsonl.partial"})
                        self.assertTrue(catalog["files"]["empty.stderr"]["embedded_empty"]);self.assertFalse(catalog["files"]["unexpected.odb"]["derived_text"])
                        self.assertFalse(catalog["files"]["native.odb.partial"]["derived_text"]);self.assertTrue(catalog["files"]["valid.jsonl.partial"]["derived_text"])
                        self.assertIn("publication-receipt.json",published)
    def test_source_consumer_refusal_precedes_acquisition_and_primary_survives_cleanup(self):
        with tempfile.TemporaryDirectory()as d:
            root=Path(d);primary=ValueError("synthetic bad source controls");secondary=OSError("synthetic cleanup failure")
            with (patch.object(h,"collect_controls",side_effect=primary),patch.object(h,"acquire",side_effect=AssertionError("must not acquire")),patch.object(h,"reserved",side_effect=AssertionError("must not reserve")),
              patch.object(h.build,"cleanup_owned",side_effect=secondary),patch.object(k,"source_gate",return_value={})):
                try:h.perform(self.ctx(),root/"work",root/"out",{}, {})
                except ValueError as error:self.assertIs(error,primary)
                else:self.fail("primary refusal became pass")
            result=q.decode((root/"out/result.json").read_bytes())
            self.assertEqual(result["status"],"FAIL_READONLY_OBSTACLE_CLOUD_OBSERVATION");self.assertEqual(len(result["terminal_errors"]),1)
    def test_unchanged_inner_cgroup_limits_with_explicit_memory_observation(self):
        path=h.ROOT/"scripts/mainchip_drt_obstacle_inner.py";tree=ast.parse(path.read_text())
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=="check_usage")
        scope=dict(k=k,c=h.c);exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),"exec"),scope)
        value=dict(memory_max=str(h.c.MEMORY))
        v={"memory.max":str(h.c.MEMORY),"memory.swap.max":"0","pids.max":str(h.c.PIDS),"cpu.max":"200000 100000","memory.current":"123","memory.stat":"anon 10\nfile 20"}
        scope["check_usage"](v)
        for name,val in(("memory.max",str(h.c.MEMORY+1)),("memory.swap.max","1"),("pids.max","999"),("cpu.max","100000 100000")):
            with self.assertRaises(ValueError):scope["check_usage"]({**v,name:val})
def main():
    import importlib,sys
    q.require(os.environ.get("GITHUB_ACTIONS")=="true","hosted source controls only")
    k.source_gate();k.validate_config(q.decode((h.ROOT/h.CONFIG).read_bytes()))
    head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=h.ROOT,text=True).strip();ctx=k.context(os.environ,head)
    modules=[importlib.import_module(n)for n in("check_mainchip_terminal_readback","check_mainchip_drt_report_analysis","check_mainchip_drt_obstacle","check_mainchip_drt_obstacle_host")]
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(m)for m in modules)
    def ids(s):
        for item in s:
            if isinstance(item,unittest.TestSuite):yield from ids(item)
            else:yield item.id()
    planned=sorted(ids(suite));q.require(planned==h.expected_test_ids(),"exact intended control suite")
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    report=dict(status="PASS_OBSTACLE_ADAPTER_SOURCE_CONTROLS"if result.wasSuccessful()and not result.skipped else"FAIL_OBSTACLE_ADAPTER_SOURCE_CONTROLS",
      source=head,run=ctx["run"],attempt=1,tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),
      skipped=len(result.skipped),successful=result.wasSuccessful()and not result.skipped,test_ids=planned,native_acquired=False,native_tools_executed=False,**k.FLAGS)
    print("MAINCHIP_OBSTACLE_CONTROLS "+json.dumps(report,sort_keys=True),flush=True)
    return 0 if report["successful"]and report["tests_run"]==h.EXPECTED_TESTS else 1
if __name__=="__main__":raise SystemExit(main())
