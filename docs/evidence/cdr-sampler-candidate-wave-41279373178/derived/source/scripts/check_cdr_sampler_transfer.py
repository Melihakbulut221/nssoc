#!/usr/bin/env python3
import json,unittest
import numpy as np
import cdr_sampler_transfer as d
class Transfer(unittest.TestCase):
    def test_interpolated_crossings_and_hysteresis(self):
        t=np.arange(7,dtype=float);x=np.array([-1.,-.5,.5,1.,.2,-.2,-1.])
        r=d.transitions(t,x,.4)
        self.assertEqual([e["direction"]for e in r],[1,-1])
        self.assertEqual([e["time_s"]for e in r],[1.5,4.5])
        self.assertEqual([e["confirmed_at_s"]for e in r],[2.,6.])
    def test_subthreshold_chatter_does_not_create_transitions(self):
        t=np.arange(6,dtype=float);x=np.array([-1.,.1,-.1,.1,-.1,1.])
        r=d.transitions(t,x,.4);self.assertEqual(len(r),1);self.assertEqual(r[0]["bracket_rows"],[4,5])
    def test_delayed_and_missing_events(self):
        s=[dict(time_s=0.,direction=1),dict(time_s=10.,direction=-1)]
        t=[dict(time_s=2.,direction=1)]
        r=d.match_events(s,t,5.);self.assertEqual(r["summary"]["matched"],1);self.assertEqual(r["summary"]["missing"],1)
        self.assertEqual(r["events"][0]["delay_s"],2.)
    def test_no_match_crosses_next_source_transition(self):
        s=[dict(time_s=0.,direction=1),dict(time_s=3.,direction=-1)]
        t=[dict(time_s=4.,direction=1)]
        r=d.match_events(s,t,10.);self.assertEqual(r["events"][0]["status"],"missing_in_current_input_state")
        self.assertEqual(r["events"][0]["following_same_direction"]["event"],t[0])
    def test_ambiguity_and_preceding_event_retained(self):
        s=[dict(time_s=0.,direction=1)]
        t=[dict(time_s=-1.,direction=1),dict(time_s=1.,direction=1),dict(time_s=2.,direction=1)]
        r=d.match_events(s,t,3.);self.assertEqual(r["events"][0]["status"],"ambiguous")
        self.assertEqual(r["events"][0]["preceding_same_direction"]["event"],t[0])
    def test_invalid_capture_and_order_refused(self):
        for t,x,h in [(np.array([0.,0.]),np.array([-1.,1.]),.1),
                      (np.array([0.,1.]),np.array([-1.,np.nan]),.1),
                      (np.array([0.,1.]),np.array([-1.,1.]),0.)]:
            with self.assertRaises(ValueError):d.transitions(t,x,h)
        with self.assertRaises(ValueError):d.match_events([dict(time_s=1.,direction=1),dict(time_s=0.,direction=-1)],[],1.)
    def test_topology_requires_parallel_cap_and_real_ground(self):
        def r(ident,model,names,clusters,nets):
            return dict(native_id=ident,model=model,terminals=[dict(terminal=n,native_cluster=c,native_net=k)for n,c,k in zip(names,clusters,nets)])
        rows=[r(1,"rppd",["rppd_1","rppd_2"],[88,139],["a","b"]),
              r(2,"rppd",["rppd_1","rppd_2"],[139,23],["b","avss"]),
              r(3,"cap_cmim",["mim_top","mim_btm"],[88,139],["a","b"])]
        self.assertEqual(d.passive_branch(rows,88,139)["series"]["native_id"],1)
        with self.assertRaises(ValueError):d.passive_branch(rows[:-1],88,139)
        rows[1]["terminals"][1]["native_net"]="wrong"
        with self.assertRaises(ValueError):d.passive_branch(rows,88,139)
if __name__=="__main__":
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Transfer))
    report=dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped))
    print("TRANSFER_CONTROLS "+json.dumps(report),flush=True)
    raise SystemExit(0 if report==dict(tests=7,failures=0,errors=0,skips=0)else 1)
