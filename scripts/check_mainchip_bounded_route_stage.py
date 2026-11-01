"""Cloud-only source/lifecycle controls; synthetic DB bytes are never native evidence."""
import copy
import hashlib
import json
import os
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock
import mainchip_bounded_route_stage as stage
import mainchip_bounded_route_stage_inner as inner
import cloud_mainchip_bounded_route_stage as host
import check_mainchip_targeted_counterpart_host as old_tests

ROOT = host.ROOT
FIXTURE = ROOT / "scripts/mainchip-bounded-route-baseline.tcl"

class Controls(unittest.TestCase):
    def setup_stage(self, temp):
        work = Path(temp) / "work"
        data = Path(temp) / "data"
        work.mkdir(); data.mkdir()
        (work / "route.tcl").write_bytes(FIXTURE.read_bytes())
        argv = ["/work/engine/openroad", "-no_init", "-exit", str(work / "route.tcl")]
        return work, data, argv
    def fake_router(self, work):
        def run(report, label, argv, seconds):
            self.assertEqual(label, "bulk-postdrt-route")
            self.assertEqual(seconds, 14400)
            self.assertIn(stage.NEW, (work / "route.tcl").read_bytes())
            for name in stage.FILES:
                (work / name).write_bytes(b"SYNTHETIC CONTROL ONLY " + name.encode())
            return "synthetic-return"
        return run
    def test_01_exact_actual_tcl_only_changes_explicit_bound(self):
        raw = FIXTURE.read_bytes()
        result = stage.render(raw)
        self.assertEqual(result.replace(stage.NEW, stage.OLD), raw)
        self.assertIn(b'DRT_OPT_ITERS) ne "64"', result)
        for command in (b"write_def", b"write_db", b"catch {detailed_route", b"set_thread_count"):
            self.assertEqual(result.count(command), raw.count(command))
    def test_02_changed_source_or_second_application_rejected(self):
        raw = FIXTURE.read_bytes()
        for bad in (raw+b"\n", raw.replace(b"Metal4", b"Metal3"), raw.replace(b"read_db", b"#read_db"),
                    stage.render(raw), raw.replace(b"write_db", b"#write_db")):
            with self.assertRaises(AssertionError): stage.render(bad)
    def test_03_returned_route_pins_all_actual_outputs(self):
        with tempfile.TemporaryDirectory() as temp:
            work, data, argv = self.setup_stage(temp); report={}
            self.assertEqual(stage.execute_stage(report, self.fake_router(work), argv, 14400, work, data),
                             "synthetic-return")
            actual = json.loads((data/stage.REPORT).read_bytes())
            self.assertEqual(stage.validate(actual), report["bounded_route_stage"])
            for name in stage.FILES:
                self.assertEqual(actual["checkpoints"][name], stage.pin((work/name).read_bytes()))
    def test_04_failed_route_preserves_partial_without_success(self):
        with tempfile.TemporaryDirectory() as temp:
            work, data, argv = self.setup_stage(temp); report={}
            def fail(*args):
                (work/"route-partial.odb").write_bytes(b"synthetic partial")
                raise RuntimeError("synthetic route failure")
            with self.assertRaisesRegex(RuntimeError, "synthetic route failure"):
                stage.execute_stage(report, fail, argv, 14400, work, data)
            actual=json.loads((data/stage.REPORT).read_bytes())
            self.assertIn("route-partial.odb",actual["checkpoints"])
            with self.assertRaises(AssertionError):stage.validate(actual)
    def test_05_missing_outputs_cannot_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            work, data, argv=self.setup_stage(temp)
            with self.assertRaises(AssertionError):
                stage.execute_stage({},lambda *args:None,argv,14400,work,data)
            with self.assertRaises(AssertionError):stage.validate(json.loads((data/stage.REPORT).read_bytes()))
    def test_06_stale_output_duplicate_stage_and_symlink_rejected(self):
        for name in stage.FILES:
            with tempfile.TemporaryDirectory() as temp:
                work,data,argv=self.setup_stage(temp)
                (work/name).write_bytes(b"stale")
                with self.assertRaises(AssertionError):
                    stage.execute_stage({},mock.Mock(side_effect=AssertionError("too late")),argv,14400,work,data)
        with tempfile.TemporaryDirectory() as temp:
            work,data,argv=self.setup_stage(temp)
            with self.assertRaises(AssertionError):
                stage.execute_stage(dict(bounded_route_stage={}),lambda *args:None,argv,14400,work,data)
            (work/stage.FILES[0]).symlink_to(work/"absent")
            with self.assertRaises(AssertionError):
                stage.execute_stage({},lambda *args:None,argv,14400,work,data)
    def test_07_command_and_budget_fail_before_call(self):
        with tempfile.TemporaryDirectory() as temp:
            work,data,argv=self.setup_stage(temp)
            runner=mock.Mock()
            for command,seconds in ((argv,14401),(["other"],14400)):
                with self.assertRaises(AssertionError):stage.execute_stage({},runner,command,seconds,work,data)
            runner.assert_not_called()
    def test_08_false_completion_or_changed_policy_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            work,data,argv=self.setup_stage(temp);report={}
            stage.execute_stage(report,self.fake_router(work),argv,14400,work,data)
            good=report["bounded_route_stage"]
            for key,value in (("iterations",64),("baseline_iterations",8),("complete",False),
                              ("route_returned",False),("error","failed"),("physical_acceptance",True),
                              ("timing_accepted",True),("full_phy_accepted",True),("checkpoints",{})):
                bad=copy.deepcopy(good);bad[key]=value
                with self.assertRaises(AssertionError):stage.validate(bad)
    def test_09_compiled_inner_preserves_clear_before_route_and_preserver(self):
        with tempfile.TemporaryDirectory() as temp:
            work,data,argv=self.setup_stage(temp);report={};calls=[];preserver=object()
            def base(report, runner, passed):
                self.assertIs(passed,preserver)
                return runner(report,"bulk-postdrt-route",argv,14400)
            def runner(report,label,command,seconds):
                calls.append(label)
                if label=="bulk-postdrt-stale-wire-clear":
                    (data/"stale-wire-clear-terminal.json").write_text(json.dumps(
                        dict(phase="stale-wire-clear",complete=True,error=None,terminal_errors=[],**inner.prior.p.FLAGS)))
                    return
                return self.fake_router(work)(report,label,command,seconds)
            with mock.patch.object(inner.prior.original,"WORK",work),mock.patch.object(inner.prior,"DATA",data), \
                 mock.patch.object(inner.prior.original,"run_route_cycle",base):
                self.assertEqual(inner.run_route_cycle(report,runner,preserver),"synthetic-return")
            self.assertEqual(calls,["bulk-postdrt-stale-wire-clear","bulk-postdrt-route"])
            stage.validate(report["bounded_route_stage"])
            self.assertTrue(report["stale_wire_clear"]["complete"])
    def test_10_exact_manifest_and_compiled_host_namespace(self):
        manifest=host.source_gate()
        self.assertTrue(manifest["native_execution_authorized"])
        old=host.prior.perform.__globals__.copy()
        captured={}
        def capture(original,**updates):
            captured.update(updates)
            return lambda *args: "captured"
        with tempfile.TemporaryDirectory() as temp, \
             mock.patch.object(host,"control_evidence",return_value={}), \
             mock.patch.object(host.inherited,"host_perform",capture):
            self.assertEqual(host.perform({}, {}, Path(temp)), "captured")
        self.assertEqual(captured["MANIFEST"],host.MANIFEST)
        self.assertIs(captured["source_gate"],host.source_gate)
        self.assertEqual(host.prior.perform.__globals__,old)
        adapter=host.inherited.clone(host.inherited.host_perform,INNER=host.INNER)
        compiled=adapter(host.prior.original.perform,source_gate=host.source_gate,MANIFEST=host.MANIFEST)
        def constants(code):
            for value in code.co_consts:
                if isinstance(value,types.CodeType):yield from constants(value)
                else:yield value
        self.assertEqual(list(constants(compiled.__code__)),
                         [host.INNER if v==host.inherited.OLD_INNER else v
                          for v in constants(host.prior.original.perform.__code__)])
    def test_11_original_result_refusals_remain_active(self):
        config,plan,scope,native,mutation=old_tests.fixture()
        with mock.patch.object(host,"authenticate_stage",return_value={"synthetic":True}):
            self.assertTrue(host.accept_result(native,mutation,config,plan,scope,
                                              host.prior.original.plan.accept_native_result)["saved_diode_routing_complete"])
            for change in ("route","PG","original-command"):
                bad=copy.deepcopy(native)
                if change=="route":bad["saved_diode_routing_result"]["current_route_calls"]=2
                if change=="PG":bad["saved_diode_routing_result"]["direct_diode_pg_contact_passed"]=False
                if change=="original-command":bad["commands"][0]["returncode"]=7
                with self.assertRaises(AssertionError):
                    host.accept_result(bad,mutation,config,plan,scope,host.prior.original.plan.accept_native_result)
    def test_12_checkpoint_readback_rejects_changed_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp);(out/"work").mkdir()
            work=out/"work/bulk-postdrt-antenna";work.mkdir()
            data=out/"bulk-postdrt-antenna";data.mkdir()
            (work/"route.tcl").write_bytes(FIXTURE.read_bytes());report={}
            argv=["/work/engine/openroad","-no_init","-exit",str(work/"route.tcl")]
            stage.execute_stage(report,self.fake_router(work),argv,14400,work,data)
            host.authenticate_stage(report,out)
            for name in stage.FILES:
                path=work/name;old=path.read_bytes();path.write_bytes(old+b"changed")
                with self.assertRaises(AssertionError):host.authenticate_stage(report,out)
                path.write_bytes(old)

if __name__=="__main__":
    assert os.environ.get("GITHUB_ACTIONS")=="true"
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Controls))
    out=ROOT/"bounded-route-controls";out.mkdir(exist_ok=False)
    value=dict(source=os.environ["GITHUB_SHA"],run=int(os.environ["GITHUB_RUN_ID"]),tests=result.testsRun,
               failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),
               native_executed=False,workflow=stage.pin((ROOT/host.WORKFLOW).read_bytes()))
    (out/"result.json").write_text(json.dumps(value,sort_keys=True,indent=2)+"\n")
    print(json.dumps(value,sort_keys=True))
    raise SystemExit(0 if result.wasSuccessful() else 1)
