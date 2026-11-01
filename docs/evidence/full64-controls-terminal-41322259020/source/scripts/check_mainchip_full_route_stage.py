"""Lifecycle controls only; synthetic outputs cannot establish routing acceptance."""
import copy,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock
import mainchip_full_route_stage as stage
ROOT=Path(__file__).resolve().parents[1]
FIXTURE=ROOT/"scripts/mainchip-bounded-route-baseline.tcl"
class Controls(unittest.TestCase):
 def setup_stage(self,temp):
  work=Path(temp)/"work";data=Path(temp)/"data";work.mkdir();data.mkdir()
  (work/"route.tcl").write_bytes(FIXTURE.read_bytes())
  return work,data,["/work/engine/openroad","-no_init","-exit",str(work/"route.tcl")]
 def runner(self,work):
  def f(report,label,argv,seconds):
   self.assertEqual((label,seconds),("bulk-postdrt-route",14400))
   self.assertEqual((work/"route.tcl").read_bytes(),FIXTURE.read_bytes())
   for name in stage.FILES:(work/name).write_bytes(b"SYNTHETIC CONTROL ONLY "+name.encode())
   return "synthetic"
  return f
 def test_original64_program_unchanged(self):
  raw=FIXTURE.read_bytes();self.assertEqual(stage.render(raw),raw)
  self.assertEqual(stage.ITERATIONS,64)
  self.assertIn(b'DRT_OPT_ITERS) ne "64"',raw)
 def test_eight_pass_or_changed_program_rejected(self):
  raw=FIXTURE.read_bytes()
  for bad in [raw.replace(stage.OLD,b"lappend drt_args -droute_end_iter 8\n"),raw+b"\n",raw.replace(b"Metal4",b"Metal3"),raw.replace(b"write_db",b"#write_db")]:
   with self.assertRaises(AssertionError):stage.render(bad)
 def test_completed_outputs_and_actual_program_verified(self):
  with tempfile.TemporaryDirectory()as temp:
   w,d,a=self.setup_stage(temp);r={}
   self.assertEqual(stage.execute_stage(r,self.runner(w),a,14400,w,d),"synthetic")
   v=json.loads((d/stage.REPORT).read_bytes());self.assertEqual(stage.validate(v),r["full_route_stage"])
   self.assertEqual(v["actual_program"],v["original_program"])
   for n in stage.FILES:self.assertEqual(v["checkpoints"][n],stage.file_pin(w/n))
 def test_failure_keeps_partial_and_rejects_success(self):
  with tempfile.TemporaryDirectory()as temp:
   w,d,a=self.setup_stage(temp);r={}
   def fail(*args):
    (w/"route-partial.odb").write_bytes(b"SYNTHETIC PARTIAL")
    raise RuntimeError("synthetic failure")
   with self.assertRaisesRegex(RuntimeError,"synthetic failure"):stage.execute_stage(r,fail,a,14400,w,d)
   v=json.loads((d/stage.REPORT).read_bytes());self.assertIn("route-partial.odb",v["checkpoints"])
   with self.assertRaises(AssertionError):stage.validate(v)
 def test_missing_outputs_rejected(self):
  with tempfile.TemporaryDirectory()as temp:
   w,d,a=self.setup_stage(temp)
   with self.assertRaises(AssertionError):stage.execute_stage({},lambda *args:None,a,14400,w,d)
   with self.assertRaises(AssertionError):stage.validate(json.loads((d/stage.REPORT).read_bytes()))
 def test_stale_or_symlink_output_before_engine(self):
  for n in stage.FILES:
   for link in [False,True]:
    with tempfile.TemporaryDirectory()as temp:
     w,d,a=self.setup_stage(temp);r=Mock()
     if link:(w/n).symlink_to(w/"absent")
     else:(w/n).write_bytes(b"STALE")
     with self.assertRaises(AssertionError):stage.execute_stage({},r,a,14400,w,d)
     r.assert_not_called()
 def test_duplicate_stage_before_engine(self):
  with tempfile.TemporaryDirectory()as temp:
   w,d,a=self.setup_stage(temp);r=Mock()
   with self.assertRaises(AssertionError):stage.execute_stage({"full_route_stage":{}},r,a,14400,w,d)
   r.assert_not_called()
 def test_wrong_command_or_budget_before_engine(self):
  with tempfile.TemporaryDirectory()as temp:
   w,d,a=self.setup_stage(temp);r=Mock()
   for command,seconds in [(a,14401),(["other"],14400)]:
    with self.assertRaises(AssertionError):stage.execute_stage({},r,command,seconds,w,d)
   r.assert_not_called()
 def test_policy_and_false_acceptance_refused(self):
  with tempfile.TemporaryDirectory()as temp:
   w,d,a=self.setup_stage(temp);r={};stage.execute_stage(r,self.runner(w),a,14400,w,d)
   for k,v in [("iterations",8),("baseline_iterations",8),("route_returned",False),("complete",False),("error","failed"),("checkpoints",{}),("physical_acceptance",True),("timing_accepted",True),("full_phy_accepted",True)]:
    bad=copy.deepcopy(r["full_route_stage"]);bad[k]=v
    with self.assertRaises(AssertionError):stage.validate(bad)
 def test_actual_program_pin_drift_refused(self):
  with tempfile.TemporaryDirectory()as temp:
   w,d,a=self.setup_stage(temp);r={};stage.execute_stage(r,self.runner(w),a,14400,w,d)
   bad=copy.deepcopy(r["full_route_stage"]);bad["actual_program"]["sha256"]="a"*64
   with self.assertRaises(AssertionError):stage.validate(bad)
 def test_input_changed_during_engine_preserved_as_failure(self):
  with tempfile.TemporaryDirectory()as temp:
   w,d,a=self.setup_stage(temp);r={}
   def change(*args):
    self.runner(w)(*args)
    (w/"route.tcl").write_bytes(b"changed")
   with self.assertRaises(AssertionError):stage.execute_stage(r,change,a,14400,w,d)
   with self.assertRaises(AssertionError):stage.validate(json.loads((d/stage.REPORT).read_bytes()))
if __name__=="__main__":
 assert os.environ.get("GITHUB_ACTIONS")=="true"
 pins=json.loads((ROOT/"scripts/mainchip-full64-pins.json").read_bytes())
 for n,p in pins.items():assert stage.file_pin(ROOT/n)==p,n
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Controls))
 out=ROOT/"full64-controls";out.mkdir(exist_ok=False)
 for n,p in pins.items():assert stage.file_pin(ROOT/n)==p,n
 record=dict(source=os.environ["GITHUB_SHA"],run=int(os.environ["GITHUB_RUN_ID"]),tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),native_executed=False,iterations=64,unchanged_baseline_Tcl=stage.file_pin(FIXTURE),**stage.FLAGS)
 (out/"result.json").write_text(json.dumps(record,sort_keys=True,indent=2)+"\n")
 raise SystemExit(0 if result.wasSuccessful()else 1)
