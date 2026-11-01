#!/usr/bin/env python3
import json,unittest
import numpy as np
import cdr_sampler_candidate_wave as d
class Events(unittest.TestCase):
    def setUp(self):
        self.t=np.arange(6.)*1e-9;self.c=np.full(6,.8);self.b=np.full(6,.8);self.e=np.zeros(6);self.i=np.full(6,.002)
    def run_events(self):return d.violation_events(self.t,self.c,self.b,self.e,self.i,2)
    def test_no_false_positive(self):self.assertEqual(self.run_events(),[])
    def test_minimum_active_only(self):
        self.c[0]=.1;self.assertEqual(self.run_events(),[])
        self.c[3]=.3;r=self.run_events();self.assertEqual(len(r),1);self.assertEqual(r[0]["worst_row"],3)
        self.assertFalse(r[0]["before_active_interval"]);self.assertEqual(r[0]["metric"],"minimum_active_vce_v")
    def test_startup_maximum_is_not_filtered(self):
        self.c[0]=1.7;r=self.run_events();self.assertEqual(len(r),1);self.assertTrue(r[0]["before_active_interval"])
        self.assertEqual(r[0]["metric"],"maximum_alltime_abs_vce_v");self.assertEqual(r[0]["worst_row"],0)
    def test_negative_voltage_absolute_limit(self):
        self.c[1]=-1.7;r=self.run_events();self.assertEqual(r[0]["value"],1.7);self.assertEqual(r[0]["worst_row"],1)
    def test_vbe_and_per_emitter_current(self):
        self.b[4]=-1.01;self.i[5]=-.0062;r=self.run_events()
        self.assertEqual([e["metric"]for e in r],["maximum_alltime_abs_vbe_v","maximum_alltime_abs_ic_per_emitter_a"])
        self.assertAlmostEqual(r[1]["value"],.0031);self.assertEqual(r[1]["worst_row"],5)
    def test_all_intervals_preserved(self):
        self.c[[2,3,5]]=.3;r=self.run_events()[0]
        self.assertEqual([(x["first_row"],x["last_row"],x["samples"])for x in r["all_violating_intervals"]],[(2,3,2),(5,5,1)])
    def test_inclusive_limits(self):
        self.c[2]=.4;self.c[3]=1.6;self.b[4]=1.;self.i[5]=.006;self.assertEqual(self.run_events(),[])
    def test_invalid_axes_refused(self):
        for which in ("time","shape","nan","nx","active"):
            t,c,b,e,i=[x.copy()for x in(self.t,self.c,self.b,self.e,self.i)];nx=2
            if which=="time":t[3]=t[2]
            if which=="shape":c=c[:-1]
            if which=="nan":c[1]=np.nan
            if which=="nx":nx=0
            if which=="active":t=t/100
            with self.subTest(which=which),self.assertRaises(ValueError):d.violation_events(t,c,b,e,i,nx)
    def test_wrong_case_identity_refused(self):
        report=dict(case="nominal_late",corner="nominal",returncode=0,diagnostics=[],sources_unchanged=True,current_context=dict(attempt=1,run_id=41260582673,source="cde6353e164d32feee5a3e56cc54b32a3001f736"))
        with self.assertRaisesRegex(ValueError,"actual case identity"):d.diagnose(report,self.t,{})
if __name__=="__main__":
    config=json.loads((d.ROOT/d.CONFIG).read_bytes());d.source_guard(config)
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Events))
    report=dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped))
    print("CANDIDATE_EVENTS_CONTROLS "+json.dumps(report),flush=True)
    raise SystemExit(0 if report==dict(tests=9,failures=0,errors=0,skips=0)else 1)
