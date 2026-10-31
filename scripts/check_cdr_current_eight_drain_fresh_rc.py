#!/usr/bin/env python3
"""Hosted source tests: unchanged numerical workers and current graph admission."""
import argparse,ast,copy,json,os,sys,traceback,unittest
from pathlib import Path
from unittest.mock import patch
import cdr_current_eight_drain_fresh_rc_admission as s
import check_cdr_drain_m1_fresh_rc as inherited

class CurrentControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.method=s.methods()
        cls.config=s.read_json(s.CONFIG)
        cls.contract=s.contract()
    def bad_config(self,mutate):
        value=copy.deepcopy(self.config);mutate(value);reader=s.read_json
        with patch.object(s,"read_json",side_effect=lambda p:value if Path(p)==s.CONFIG else reader(p)):
            with self.assertRaises(AssertionError):s.contract()
    def test_actual_current_input(self):
        c=self.contract
        self.assertEqual(len(c["transport"]["expected_sha256"]),330)
        self.assertEqual(c["canonical_candidate"]["members"],75)
        self.assertEqual(s.GRAPH_RUN,41206809668)
        self.assertEqual(str(s.ANALYSIS),"/home/runner/work/nssoc/nssoc/hw/soc/out/cdr-current-eight-drain-graph-41206809668-1/native/candidate")
    def test_exact_worker_rebinding(self):
        for suffix in ("binding","wire_rc","mim_capture","mim_audit","mim_precision"):
            old=s.ROOT/("scripts/cloud_cdr_drain_m1_fresh_"+suffix+".py")
            new=s.ROOT/("scripts/cloud_cdr_current_eight_drain_fresh_"+suffix+".py")
            self.assertEqual(new.read_bytes().replace(b"cdr_current_eight_drain_fresh_rc_legacy",b"cdr_drain_m1_fresh_rc_legacy"),old.read_bytes())
    def test_complete_reversible_derivation(self):
        proof=s.read_json(s.ROOT/"scripts/cdr-current-eight-drain-fresh-rc-derivation.json")
        for new,row in proof["files"].items():
            original=s.regular(s.ROOT,row["original"])
            self.assertEqual(s.sha(original),row["original_sha256"])
            text=original.read_text()
            for change in row["replacements"]:
                self.assertEqual(text.count(change["before"]),change["count"])
                text=text.replace(change["before"],change["after"])
            self.assertEqual(text,(s.ROOT/new).read_text())
    def test_controller_numerical_gates_unchanged(self):
        import cloud_cdr_current_eight_drain_fresh_rc as host
        import cloud_cdr_drain_m1_fresh_rc as old
        self.assertEqual(host.PIPELINE_SHA,old.PIPELINE_SHA)
        self.assertEqual(host.APP_SHA,old.APP_SHA)
        self.assertEqual(list(host.SECONDS.values()),[1200]*4)
        def funcs(path):
            raw=Path(path).read_text()
            return {n.name:ast.get_source_segment(raw,n)for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef)}
        before=funcs(old.__file__);after=funcs(host.__file__)
        for name in ("execute","pipeline_validator","validate_completed_pipeline","finalization","main_run","publish"):
            self.assertEqual(before[name],after[name],name)
        self.assertEqual(s.BINDING_FILES,inherited.e.BINDING_FILES)
    def test_old_graph_refused(self):
        for key,value in (("run",41003747027),("source","0"*40),("attempt",2),("workflow",1),("branch","other")):
            with self.subTest(key=key):self.bad_config(lambda c:c["graph_producer"].update({key:value}))
    def test_incomplete_capsule_refused(self):
        self.bad_config(lambda c:c["full_capsule_files"].pop(next(iter(c["full_capsule_files"]))))
    def test_extra_capsule_member_refused(self):
        self.bad_config(lambda c:c["full_capsule_files"].update(extra=dict(bytes=0,sha256="0"*64)))
    def test_full_map_hash_refused(self):
        self.bad_config(lambda c:c["full_capsule_files"][next(iter(c["full_capsule_files"]))].update(sha256="0"*64))
    def test_wrong_physical_bytes_refused(self):
        for key in ("candidate_gds","candidate_lvs"):
            with self.subTest(key=key):self.bad_config(lambda c:c["graph_qualification"][key].update(sha256="0"*64))
    def test_identity_or_geometry_claim_refused(self):
        for key in ("devices","terminals","ports","anchors","native_nets"):
            with self.subTest(key=key):self.bad_config(lambda c:c["graph_qualification"]["actual_native_identity"].update({key:1}))
        self.bad_config(lambda c:c["graph_qualification"]["material"].update(sha256="0"*64))
        self.bad_config(lambda c:c["graph_qualification"].update(fresh_RC_executed=True))
    def test_current_view_census_and_binding_refused(self):
        self.bad_config(lambda c:c["graph_qualification"]["current_files"].pop(next(iter(c["graph_qualification"]["current_files"]))))
        self.bad_config(lambda c:c.update(current_view_prefix="old/"))
    def live_fixture(self):
        q=self.config;prefix=s.ROOT/q["graph_proof"]["prefix"]
        return [copy.deepcopy(self.contract),s.read_json(prefix/"run.json"),s.read_json(prefix/"jobs.json"),
                s.read_json(prefix/"release.json"),dict(object=dict(type="commit",sha=s.GRAPH_HEAD))]
    def test_actual_live_metadata(self):
        self.assertTrue(s.live(*self.live_fixture())["successful_fresh_graph_only"])
    def test_failed_or_wrong_graph_job_refused(self):
        for mode in ("missing","running","source","run"):
            args=self.live_fixture()
            if mode=="missing":args[2]["jobs"].pop()
            else:args[2]["jobs"][0].update({"running":{"status":"in_progress"},"source":{"head_sha":"0"*40},"run":{"run_id":1}}[mode])
            with self.subTest(mode=mode),self.assertRaises(AssertionError):s.live(*args)
    def test_changed_live_asset_refused(self):
        for field,value in (("digest","sha256:"+"0"*64),("id",1),("size",0),("state","new")):
            args=self.live_fixture();args[3]["assets"][0][field]=value
            with self.subTest(field=field),self.assertRaises(AssertionError):s.live(*args)
    def test_changed_numerical_source_refused(self):
        actual=s.sha;victim=s.ROOT/s.ENTRIES["binding"]
        with patch.object(s,"sha",side_effect=lambda p:"0"*64 if Path(p)==victim else actual(p)):
            with self.assertRaises(AssertionError):s.methods()
    def test_authority_types_and_scope(self):
        for field in s.NATIVE+s.FALSE+("source_controls_authorized","controller_readiness"):
            m=copy.deepcopy(self.method);m[field]=1
            with self.subTest(field=field),self.assertRaises(AssertionError):s.validate_authorizations(m)
        for field in s.FALSE:
            m=copy.deepcopy(self.method);m[field]=True
            with self.subTest(field=field),self.assertRaises(AssertionError):s.validate_authorizations(m)
        m=copy.deepcopy(self.method);m[s.NATIVE[0]]=False
        with self.assertRaises(AssertionError):s.validate_authorizations(m)
        with patch.dict(os.environ,{"GITHUB_REF":"refs/heads/"+inherited.e.BRANCH}):
            with self.assertRaises(AssertionError):s.context(self.method)

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,required=True);args=parser.parse_args()
    assert os.environ["GITHUB_ACTIONS"]=="true"and os.environ["GITHUB_EVENT_NAME"]=="workflow_dispatch"
    assert os.environ["GITHUB_RUN_ATTEMPT"]=="1"and os.environ["GITHUB_REF"]=="refs/heads/"+s.BRANCH
    context=dict(source=os.environ["GITHUB_SHA"],run_id=int(os.environ["GITHUB_RUN_ID"]),attempt=1,source_controls_only=True,native_executed=False)
    report=dict(status="FAIL_CURRENT_EIGHT_DRAIN_FRESH_RC_SOURCE_CONTROLS",passed=False,current_context=context,
                native_executed=False,electrical_acceptance=False)
    error=None
    try:
        original_reservation_controls=inherited.reservation_controls
        def old_reservation_fixture(method):
            # Only the historical synthetic reservation fixture sees its old branch.
            # Its API, wait, receipt and controls are already mocked by the original test.
            assert os.environ["GITHUB_REF"]=="refs/heads/"+s.BRANCH
            with patch.dict(os.environ,{"GITHUB_REF":"refs/heads/"+inherited.e.BRANCH}):
                return original_reservation_controls(method)
        with patch.object(inherited,"reservation_controls",side_effect=old_reservation_fixture):
            prior=inherited.controls()
        assert os.environ["GITHUB_REF"]=="refs/heads/"+s.BRANCH
        assert prior["passed"]is True and (prior["positive"],prior["refusal"])==(8,110)
        report.update(inherited=dict(positive=8,refusal=110),inherited_report=prior)
        suite=unittest.defaultTestLoader.loadTestsFromTestCase(CurrentControls)
        assert suite.countTestCases()==16
        result=unittest.TextTestRunner(verbosity=2).run(suite)
        report.update(new_tests=result.testsRun,errors=[dict(test=str(t),traceback=v)for t,v in result.errors],
                      failures=[dict(test=str(t),traceback=v)for t,v in result.failures],skipped=result.skipped)
        assert result.wasSuccessful()and result.testsRun==16 and not result.skipped
        report.update(status="PASS_CURRENT_EIGHT_DRAIN_FRESH_RC_SOURCE_CONTROLS",passed=True)
    except BaseException as exc:
        error=exc;report["exception"]=traceback.format_exc()
        report["inherited_partial_records"]=copy.deepcopy(inherited.RECORDS)
    finally:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    if error is not None:raise error
if __name__=="__main__":main()
