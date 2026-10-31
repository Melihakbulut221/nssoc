"""Hosted source/refusal tests only; all native records here are synthetic."""
import ast,copy,json,os,sys,unittest
from pathlib import Path
from unittest import mock
import mainchip_stale_wire_admission as a
import check_mainchip_stale_wire_admission_inherited as context
from mainchip_stale_wire_admission import p

def fixture():
    labels=["bulk-postdrt-version","bulk-postdrt-ldd"]+[
      "bulk-postdrt-route-continuation-"+x if x in a.original.PREPARATION else "bulk-postdrt-"+x
      for x in a.original.PHASES]
    labels.insert(labels.index(a.ROUTE),a.CLEAR)
    commands=[dict(label=label,returncode=0,argv=a.ARGV if label==a.CLEAR else ["synthetic"],
      requested_timeout_seconds=14400 if label==a.ROUTE else 1200)for label in labels]
    result=dict(status="COMPLETE_SAVED_DIODE_ROUTING_QUALIFICATION",bounded_cycle_qualified=True,
      current_repair_antennas_calls=0,current_reconstruction_calls=0,current_route_calls=1,
      direct_diode_pg_contact_passed=True,candidate=dict(bytes=7,sha256="a"*64),**p.FLAGS)
    return dict(status="COMPLETE_SAVED_DIODE_ROUTING_ENGINE",terminal_errors=[],native_complete=True,
      route_cycle=dict(complete=True,terminal_errors=[],phases={x:"complete"for x in a.original.PHASES}),
      commands=commands,saved_diode_routing_result=result,
      stale_wire_clear=dict(phase="stale-wire-clear",complete=True,error=None,terminal_errors=[],**p.FLAGS),**p.FLAGS)

class Controls(unittest.TestCase):
    def test_source_gate(self):
        self.assertFalse(a.source_gate()["current_native_result_accepted"])
    def test_complete_real_environment_unchanged(self):
        before=dict(os.environ)
        actual=context.source_context(os.environ)
        self.assertEqual(actual["source"],os.environ["GITHUB_SHA"])
        self.assertEqual(os.environ["GITHUB_REF"],"refs/heads/"+context.BRANCH)
        with self.assertRaises(AssertionError):context.original_host.context(os.environ)
        historical=dict(os.environ,GITHUB_REF="refs/heads/codex/mainchip-net459-diode-prune")
        with self.assertRaises(AssertionError):context.source_context(historical)
        self.assertEqual(dict(os.environ),before)
    def test_only_inherited_context_global_changes(self):
        self.assertIs(context.source_context.__code__,context.original_host.context.__code__)
        self.assertIs(context.source_main.__code__,context.original_controls.main.__code__)
        self.assertIs(context.source_main.__globals__["controls"],context.original_controls.controls)
        for key,value in vars(context.original_host).items():
            if key!="context":self.assertIs(getattr(context.source_host,key),value,key)
    def test_original_rejects_added_phase_new_gate_preserves_record(self):
        inner=fixture();before=copy.deepcopy(inner)
        with self.assertRaises(AssertionError):a.original.accept_native_result(inner)
        self.assertTrue(a.validate_native_result(inner)["saved_diode_routing_complete"])
        self.assertEqual(inner,before)
    def test_whole_validator_ast_only_one_statement(self):
        raw=(a.ROOT/a.PLAN).read_bytes()
        old=next(n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef)and n.name=="accept_native_result")
        derived=a.validator_tree(raw).body[0]
        inserts=[i for i,n in enumerate(derived.body)if isinstance(n,ast.Expr)and isinstance(n.value,ast.Call)
          and isinstance(n.value.func,ast.Attribute)and n.value.func.attr=="insert"]
        self.assertEqual(len(inserts),1);derived.body.pop(inserts[0])
        self.assertEqual(ast.dump(old),ast.dump(derived))
        with self.assertRaises(AssertionError):a.validator_tree(raw+b"\n")
    def test_clear_missing_duplicate_order_name_extra_refused(self):
        for mode in ("missing","duplicate","order","name","extra"):
            inner=fixture();rows=inner["commands"];i=next(i for i,r in enumerate(rows)if r["label"]==a.CLEAR)
            if mode=="missing":rows.pop(i)
            elif mode=="duplicate":rows.insert(i,copy.deepcopy(rows[i]))
            elif mode=="order":rows[i],rows[i+1]=rows[i+1],rows[i]
            elif mode=="name":rows[i]["label"]="other-clear"
            else:rows.append(dict(label="extra",returncode=0))
            with self.subTest(mode=mode),self.assertRaises(AssertionError):a.validate_native_result(inner)
    def test_clear_and_route_invocation_refused(self):
        for label,key,value in ((a.CLEAR,"argv",["other"]), (a.CLEAR,"requested_timeout_seconds",1201),
          (a.CLEAR,"requested_timeout_seconds",True),(a.ROUTE,"requested_timeout_seconds",14401)):
            inner=fixture();row=next(r for r in inner["commands"]if r["label"]==label);row[key]=value
            with self.subTest(label=label,key=key,value=value),self.assertRaises(AssertionError):a.validate_native_result(inner)
    def test_clear_terminal_failure_refused(self):
        for key,value in (("phase","other"),("complete",False),("complete",1),("error","failure"),("terminal_errors",["error"])):
            inner=fixture();inner["stale_wire_clear"][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(AssertionError):a.validate_native_result(inner)
    def test_any_command_failure_refused(self):
        for i in range(17):
            inner=fixture();inner["commands"][i]["returncode"]=7
            with self.subTest(command=i),self.assertRaises(AssertionError):a.validate_native_result(inner)
    def test_all_original_phases_required(self):
        for phase in a.original.PHASES:
            inner=fixture();inner["route_cycle"]["phases"][phase]="failed"
            with self.subTest(phase=phase),self.assertRaises(AssertionError):a.validate_native_result(inner)
    def test_original_command_missing_or_reordered_refused(self):
        for mode in ("missing","reordered","second_route"):
            inner=fixture()
            if mode=="missing":inner["commands"].pop(0)
            elif mode=="reordered":inner["commands"][0],inner["commands"][1]=inner["commands"][1],inner["commands"][0]
            else:inner["commands"].append(copy.deepcopy(next(r for r in inner["commands"]if r["label"]==a.ROUTE)))
            with self.subTest(mode=mode),self.assertRaises(AssertionError):a.validate_native_result(inner)
    def test_original_physical_verdict_refusals(self):
        for key,value in (("status","FAIL"),("bounded_cycle_qualified",False),("current_repair_antennas_calls",1),
           ("current_reconstruction_calls",1),("current_route_calls",2),("direct_diode_pg_contact_passed",False)):
            inner=fixture();inner["saved_diode_routing_result"][key]=value
            with self.subTest(key=key),self.assertRaises(AssertionError):a.validate_native_result(inner)
    def test_original_candidate_pin_refusals(self):
        for key,value in (("bytes",0),("bytes",True),("sha256","A"*64),("sha256","0")):
            inner=fixture();inner["saved_diode_routing_result"]["candidate"][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(AssertionError):a.validate_native_result(inner)
    def test_original_engine_or_cleanup_failure_refused(self):
        for key,value in (("status","FAIL"),("terminal_errors",["failed"]),("native_complete",False)):
            inner=fixture();inner[key]=value
            with self.subTest(key=key),self.assertRaises(AssertionError):a.validate_native_result(inner)
        for key,value in (("complete",False),("terminal_errors",["error"])):
            inner=fixture();inner["route_cycle"][key]=value
            with self.subTest(key=key),self.assertRaises(AssertionError):a.validate_native_result(inner)
    def test_all_acceptance_flags_refused(self):
        for where in ("inner","saved_diode_routing_result","stale_wire_clear"):
            for key in p.FLAGS:
                for value in (True,0,1):
                    inner=fixture();target=inner if where=="inner"else inner[where];target[key]=value
                    with self.subTest(where=where,key=key,value=value),self.assertRaises(AssertionError):a.validate_native_result(inner)

if __name__=="__main__":
    assert os.environ["GITHUB_ACTIONS"]=="true"
    assert os.environ["GITHUB_REF"]=="refs/heads/"+context.BRANCH
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Controls)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    report=dict(status="PASS" if result.wasSuccessful()else "FAIL",
      source=os.environ["GITHUB_SHA"],run_id=int(os.environ["GITHUB_RUN_ID"]),attempt=1,
      tests=result.testsRun,failures=[dict(test=str(x),traceback=y)for x,y in result.failures],
      errors=[dict(test=str(x),traceback=y)for x,y in result.errors],skipped=result.skipped,
      native_acquisition=False,native_executed=False,physical_acceptance=False,
      timing_accepted=False,full_phy_accepted=False)
    Path("bulk-postdrt-integration-controls/stale-wire-admission-controls.json").write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    sys.exit(0 if result.wasSuccessful()and result.testsRun==15 and not result.skipped else 1)
