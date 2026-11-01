"""Exercise snapshot-only routing delta and failed native preservation; no CAD."""
import copy,json,os,tempfile,unittest
from pathlib import Path
import mainchip_full_route_snapshots as s
ROOT=Path(__file__).resolve().parents[1]
BASE=(ROOT/"scripts/mainchip-bounded-route-baseline.tcl").read_bytes()
class Controls(unittest.TestCase):
 def fixture(self,t):
  w=Path(t)/"work";d=Path(t)/"data";w.mkdir();d.mkdir();(w/"route.tcl").write_bytes(BASE)
  return w,d,["/work/engine/openroad","-no_init","-exit",str(w/"route.tcl")]
 def fake(self,w):
  def run(*args):
   for n in s.FILES:(w/n).write_bytes(b"SYNTHETIC NOT NATIVE")
   (w/"drt_iter0.odb").write_bytes(b"SYNTHETIC SNAPSHOT")
   return {"returncode":0}
  return run
 def test_only_snapshot_flag_changes(self):
  changed=s.render(BASE)
  self.assertEqual(changed.replace(s.SNAPSHOT_ENABLE,b"",1),BASE)
  self.assertIn(b'DRT_OPT_ITERS) ne "64"',changed)
  self.assertIn(b'-or_seed 42',changed)
  self.assertEqual(changed.count(b'detailed_route {*}$drt_args'),1)
 def test_altered_baseline_refused(self):
  for bad in [BASE+b"\n",BASE.replace(b'-or_seed 42',b'-or_seed 43'),BASE.replace(b'DRT_THREADS) ne "2"',b'DRT_THREADS) ne "4"')]:
   with self.assertRaises(AssertionError):s.render(bad)
 def test_success_does_not_claim_reload_or_signoff(self):
  with tempfile.TemporaryDirectory()as t:
   w,d,a=self.fixture(t);r={};s.execute_stage(r,self.fake(w),a,14400,w,d)
   v=s.validate(r["full_route_stage"])
   self.assertFalse(v["snapshot_reload_qualified"])
   self.assertFalse(v["snapshot_inventory"]["drt_iter0.odb"]["reload_verified"])
   self.assertTrue(all(v[k]is False for k in s.FLAGS))
 def test_failed_route_keeps_actual_partial_snapshot_pin(self):
  with tempfile.TemporaryDirectory()as t:
   w,d,a=self.fixture(t);r={}
   def fail(*args):
    (w/"drt_iter27.odb").write_bytes(b"REAL TEST FIXTURE ONLY")
    raise RuntimeError("synthetic elapsed limit")
   with self.assertRaises(RuntimeError):s.execute_stage(r,fail,a,14400,w,d)
   v=json.loads((d/s.REPORT).read_bytes())
   self.assertEqual(v["snapshot_inventory"]["drt_iter27.odb"]["sha256"],s.pin(b"REAL TEST FIXTURE ONLY")["sha256"])
   with self.assertRaises(AssertionError):s.validate(v)
 def test_stale_snapshot_refused(self):
  with tempfile.TemporaryDirectory()as t:
   w,d,a=self.fixture(t);(w/"drt_iter1.odb").write_bytes(b"STALE")
   with self.assertRaises(AssertionError):s.execute_stage({},self.fake(w),a,14400,w,d)
 def test_invalid_snapshot_paths_refused(self):
  for name in ["drt_iter65.odb","drt_iter-1.odb","drt_iter1.def","drt_iterx.odb"]:
   with tempfile.TemporaryDirectory()as t:
    p=Path(t);(p/name).write_bytes(b"BAD")
    with self.assertRaises(AssertionError):s.snapshot_inventory(p)
  with tempfile.TemporaryDirectory()as t:
   p=Path(t);(p/"real").write_bytes(b"KEEP");(p/"drt_iter0.odb").symlink_to(p/"real")
   with self.assertRaises(AssertionError):s.snapshot_inventory(p)
 def test_forged_actual_program_and_acceptance_refused(self):
  with tempfile.TemporaryDirectory()as t:
   w,d,a=self.fixture(t);r={};s.execute_stage(r,self.fake(w),a,14400,w,d)
   for key,val in [("snapshots_enabled",False),("snapshot_reload_qualified",True),("physical_acceptance",True),("iterations",8),("actual_program",s.pin(b"wrong"))]:
    bad=copy.deepcopy(r["full_route_stage"]);bad[key]=val
    with self.assertRaises(AssertionError):s.validate(bad)
 def test_budget_and_argv_remain_original(self):
  with tempfile.TemporaryDirectory()as t:
   w,d,a=self.fixture(t)
   with self.assertRaises(AssertionError):s.execute_stage({},self.fake(w),a,14401,w,d)
   with self.assertRaises(AssertionError):s.execute_stage({},self.fake(w),a+["extra"],14400,w,d)
if __name__=="__main__":
 assert os.environ.get("GITHUB_ACTIONS")=="true"
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Controls))
 out=ROOT/"full64-snapshot-controls";out.mkdir()
 (out/"result.json").write_text(json.dumps(dict(source=os.environ["GITHUB_SHA"],run=int(os.environ["GITHUB_RUN_ID"]),tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),native_executed=False,physical_acceptance=False),sort_keys=True,indent=2)+"\n")
 raise SystemExit(0 if result.wasSuccessful()else 1)
