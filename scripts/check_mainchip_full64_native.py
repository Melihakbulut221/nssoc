"""Real frozen preservation primitives over synthetic filesystem fixtures; no CAD."""
import copy,json,os,sys,tempfile,unittest
from unittest import mock
from pathlib import Path
import mainchip_full64_output_preservation as fix
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"original/scripts"))
import cloud_mainchip_bulk_postdrt_antenna as base
import mainchip_full64_route_inner as inner
class Controls(unittest.TestCase):
 def fixture(self,temp):
  out=Path(temp)/"out";ev=Path(temp)/"evidence";out.mkdir();ev.mkdir()
  report=dict(terminal_errors=[],native_publication=dict(files={}))
  return out,ev,report
 def put(self,out,report,name,raw,published=False):
  p=out/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
  if published:report["native_publication"]["files"][name]=base.f.file_digest(p)
  return p
 def test_three_original_failures_reproduced_and_preserved(self):
  with tempfile.TemporaryDirectory()as t:
   out,ev,r=self.fixture(t)
   for n in fix.EXACT_DEF:self.put(out,r,n,b"SYNTHETIC DEF",True)
   self.put(out,r,"host-progress.json",json.dumps({"synthetic":"x"*(3*1024**2)}).encode())
   original=copy.deepcopy(r);original_ev=Path(t)/"old";original_ev.mkdir()
   base.preserve_outputs(out,original_ev,original)
   self.assertEqual(len(original["terminal_errors"]),3)
   actual=fix.preserve_outputs(base,out,ev,r)
   self.assertTrue(actual["complete"]);self.assertFalse(r["terminal_errors"])
   self.assertEqual(set(actual["complete_large_outputs_in_native_capsule"]),fix.EXACT_DEF)
   self.assertEqual((ev/"native/host-progress.json").read_bytes(),(out/"host-progress.json").read_bytes())
 def test_only_published_exact_route_programs_allowed(self):
  with tempfile.TemporaryDirectory()as t:
   out,ev,r=self.fixture(t)
   for n in fix.EXACT_TCL:self.put(out,r,n,b"SYNTHETIC TCL",True)
   self.assertTrue(fix.preserve_outputs(base,out,ev,r)["complete"])
   self.assertEqual(set(r["output_preservation"]["copied"]),fix.EXACT_TCL)
 def test_run41699812301_route47_programs_preserved(self):
  names=("bulk-postdrt-antenna/narrow47-route-actual.tcl","bulk-postdrt-antenna/narrow47-route-original.tcl")
  with tempfile.TemporaryDirectory()as t:
   out,ev,r=self.fixture(t)
   for n in names:self.put(out,r,n,b"SYNTHETIC ROUTE47 TCL",True)
   self.assertTrue(fix.preserve_outputs(base,out,ev,r)["complete"]);self.assertFalse(r["terminal_errors"])
   self.assertEqual(set(r["output_preservation"]["copied"]),set(names))
  with tempfile.TemporaryDirectory()as t:
   out,ev,r=self.fixture(t)
   for n in names:self.put(out,r,n,b"UNPUBLISHED ROUTE47 TCL")
   self.assertFalse(fix.preserve_outputs(base,out,ev,r)["complete"]);self.assertEqual(len(r["terminal_errors"]),2)
  with tempfile.TemporaryDirectory()as t:
   out,ev,r=self.fixture(t);self.put(out,r,"bulk-postdrt-antenna/narrow47-route-other.tcl",b"UNEXPECTED",True)
   self.assertFalse(fix.preserve_outputs(base,out,ev,r)["complete"])
 def test_changed_capsule_pin_refused(self):
  for n in list(fix.EXACT_DEF)+list(fix.EXACT_TCL):
   with tempfile.TemporaryDirectory()as t:
    out,ev,r=self.fixture(t);p=self.put(out,r,n,b"ORIGINAL",True);p.write_bytes(b"CHANGED")
    self.assertFalse(fix.preserve_outputs(base,out,ev,r)["complete"])
 def test_unexpected_files_and_symlinks_refused(self):
  for n in ("bulk-postdrt-antenna/other.def","bulk-postdrt-antenna/other.tcl","other.bin"):
   with tempfile.TemporaryDirectory()as t:
    out,ev,r=self.fixture(t);self.put(out,r,n,b"UNEXPECTED",True)
    self.assertFalse(fix.preserve_outputs(base,out,ev,r)["complete"])
  with tempfile.TemporaryDirectory()as t:
   out,ev,r=self.fixture(t);(out/"host-progress.json").symlink_to(out/"absent")
   self.assertFalse(fix.preserve_outputs(base,out,ev,r)["complete"])
 def test_unpublished_large_output_refused(self):
  with tempfile.TemporaryDirectory()as t:
   out,ev,r=self.fixture(t);self.put(out,r,"unpublished.json",b" "*(3*1024**2))
   self.assertFalse(fix.preserve_outputs(base,out,ev,r)["complete"])
 def test_oversized_or_invalid_host_report_refused(self):
  for content in (b"x"*(fix.MAX_HOST+1),b"invalid-json",b"[]"):
   with tempfile.TemporaryDirectory()as t:
    out,ev,r=self.fixture(t);self.put(out,r,"host-progress.json",content)
    self.assertFalse(fix.preserve_outputs(base,out,ev,r)["complete"])
 def test_preexisting_output_not_overwritten(self):
  with tempfile.TemporaryDirectory()as t:
   out,ev,r=self.fixture(t);self.put(out,r,"small.json",b"{}")
   dest=ev/"native/small.json";dest.parent.mkdir();dest.write_bytes(b"KEEP")
   self.assertFalse(fix.preserve_outputs(base,out,ev,r)["complete"]);self.assertEqual(dest.read_bytes(),b"KEEP")
 def test_original_small_and_native_large_behavior_retained(self):
  with tempfile.TemporaryDirectory()as t:
   out,ev,r=self.fixture(t);self.put(out,r,"small.json",b"{}")
   self.put(out,r,"large.json",b" "*(3*1024**2),True)
   orig=copy.deepcopy(r);oe=Path(t)/"old";oe.mkdir()
   old=base.preserve_outputs(out,oe,orig);new=fix.preserve_outputs(base,out,ev,r)
   for k in ("copied","complete_large_outputs_in_native_capsule","complete"):self.assertEqual(old[k],new[k])

 def test_native_preparation_dispatch_and_terminal_refusal(self):
  with tempfile.TemporaryDirectory()as t:
   data=Path(t);calls=[]
   def runner(report,label,argv,seconds):
    calls.append((label,argv,seconds))
    name=label.removeprefix("bulk-postdrt-")
    (data/(name+"-terminal.json")).write_text(json.dumps(dict(phase=name,complete=True,error=None,terminal_errors=[],**inner.p.FLAGS)))
   with mock.patch.object(inner,"DATA",data):
    for label in inner.PHASES[:5]+("clear",):self.assertTrue(inner.execute(label,{},runner)["complete"])
    self.assertEqual(calls[-1][1], [inner.ENGINE,"-no_init","-exit","-python",inner.TARGET])
    def fail(report,label,argv,seconds):
     name=label.removeprefix("bulk-postdrt-")
     (data/(name+"-terminal.json")).write_text(json.dumps(dict(phase=name,complete=False,error="synthetic",terminal_errors=[],**inner.p.FLAGS)))
    with self.assertRaises(AssertionError):inner.execute("clear",{},fail)
 def test_original_fixed_phase_executor_used(self):
  with tempfile.TemporaryDirectory()as t:
   data=Path(t);calls=[];original=inner.base.execute_phase
   def runner(report,label,argv,seconds):
    calls.append(label)
    if label=="bulk-postdrt-fixed-audit":
     (data/"fixed-audit-terminal.json").write_text(json.dumps(dict(phase="fixed-audit",complete=True,error=None,terminal_errors=[],**inner.p.FLAGS)))
   def adapted(*args,**kwargs):return original(*args,work=data,data=data,**kwargs)
   with mock.patch.object(inner.base,"execute_phase",adapted):
    self.assertTrue(inner.execute("fixed-import",{},runner)["complete"])
    self.assertTrue(inner.execute("fixed-audit",{},runner)["complete"])
   self.assertEqual(calls,["bulk-postdrt-fixed-import","bulk-postdrt-fixed-audit"])
 def test_actual_route_dispatch_preserves_full64_contract(self):
  with tempfile.TemporaryDirectory()as t:
   w=Path(t)/"work";d=Path(t)/"data";w.mkdir();d.mkdir()
   (w/"route.tcl").write_bytes((ROOT/"scripts/mainchip-bounded-route-baseline.tcl").read_bytes())
   calls=[]
   def runner(report,label,argv,seconds):
    calls.append((label,argv,seconds))
    for n in inner.stage.FILES:(w/n).write_bytes(b"SYNTHETIC ONLY")
    return {"returncode":0}
   with mock.patch.object(inner,"WORK",w),mock.patch.object(inner,"DATA",d):
    r={};self.assertTrue(inner.execute("route",r,runner)["complete"])
    self.assertEqual(calls,[("bulk-postdrt-route",[inner.ENGINE,"-no_init","-exit",str(w/"route.tcl")],14400)])
    self.assertEqual(inner.stage.validate(r["full_route_stage"])["iterations"],64)
 def test_phase_order_and_unknown_phase_refused(self):
  self.assertEqual(inner.PHASES,("bootstrap","guide-overlay","guide-reload-audit","power-contact-audit","make-overlay","fixed-import","fixed-audit","clear","route"))
  with self.assertRaises(AssertionError):inner.execute("unexpected",{},mock.Mock())

if __name__=="__main__":
 assert os.environ.get("GITHUB_ACTIONS")=="true"
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Controls))
 out=ROOT/"full64-native-controls";out.mkdir(exist_ok=False)
 v=dict(source=os.environ["GITHUB_SHA"],run=int(os.environ["GITHUB_RUN_ID"]),tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),native_executed=False)
 (out/"preservation-controls.json").write_text(json.dumps(v,sort_keys=True,indent=2)+"\n")
 raise SystemExit(0 if result.wasSuccessful()else 1)
