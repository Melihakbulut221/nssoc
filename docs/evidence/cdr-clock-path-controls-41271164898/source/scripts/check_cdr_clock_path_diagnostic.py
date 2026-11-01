#!/usr/bin/env python3
import json,unittest
import numpy as np
import cdr_clock_path_diagnostic as c
class Controls(unittest.TestCase):
    def test_exact_linear_crossing_both_directions(self):
        t=np.array([0.,1.,2.]);x=np.array([-1.,0.,1.]);c.axes(t,x)
        self.assertEqual(c.crossings(t,x,0.,2.,1),[1.])
        self.assertEqual(c.crossings(t,-x,0.,2.,-1),[1.])
    def test_multiple_crossings_preserved(self):
        t=np.arange(6,dtype=float);x=np.array([-1.,1.,-1.,1.,-1.,1.])
        self.assertEqual(c.crossings(t,x,0.,5.,1),[.5,2.5,4.5])
    def test_no_crossing_and_bounded_window(self):
        t=np.arange(4,dtype=float)
        self.assertEqual(c.crossings(t,np.ones(4),0.,3.,1),[])
        self.assertEqual(c.crossings(t,t-1.,1.5,3.,1),[])
        for low,high,direction in [(-1,2,1),(0,4,1),(2,1,1),(0,2,0),(float("nan"),2,1)]:
            with self.assertRaises(ValueError):c.crossings(t,t,low,high,direction)
    def test_invalid_native_axes_rejected(self):
        for t,x in [(np.array([0.,0.]),np.ones(2)),(np.arange(2.),np.ones(3)),(np.arange(2.),np.array([0.,np.nan])),(np.array([1.,0.]),np.ones(2))]:
            with self.assertRaises(ValueError):c.axes(t,x)
    def row(self,i,clock,tail):
        return dict(native_id=i,model="npn13g2",terminals=[dict(terminal=k,native_net=v)for k,v in [("C","out"+str(i)),("B",clock),("E",tail),("S","sub")]])
    def test_pairing_uses_shared_emitter_not_device_number(self):
        rows=[self.row(1,"cp","e1"),self.row(9,"cn","e1"),self.row(2,"cn","e2"),self.row(8,"cp","e2")]
        groups=c.clock_groups(rows)
        self.assertEqual(set(groups),{"e1","e2"})
        self.assertEqual([r["native_id"]for r in groups["e1"]["cn"]],[9])
        self.assertEqual([r["native_id"]for r in groups["e2"]["cp"]],[8])
    def test_incomplete_or_duplicate_clock_identity_refused(self):
        with self.assertRaises(ValueError):c.clock_groups([self.row(1,"cp","e1")])
        with self.assertRaises(ValueError):c.clock_groups([self.row(1,"cp","e1"),self.row(1,"cn","e1")])
if __name__=="__main__":
    config=json.loads((c.d.ROOT/c.d.CONFIG).read_bytes());c.d.source_guard(config)
    r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Controls))
    result=dict(tests=r.testsRun,failures=len(r.failures),errors=len(r.errors),skips=len(r.skipped))
    print("CLOCK_PATH_CONTROLS "+json.dumps(result),flush=True)
    raise SystemExit(0 if result==dict(tests=6,failures=0,errors=0,skips=0)else 1)
