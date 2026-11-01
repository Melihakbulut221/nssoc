#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import copy,hashlib,io,json,pathlib,tarfile,tempfile,unittest
import numpy as np
import cdr_via2_m3_wave_diagnostic as d

class Controls(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name)
        self.config=json.loads((d.ROOT/d.CONFIG).read_bytes())
    def tearDown(self):self.tmp.cleanup()
    def raw(self,flags="real",last_extra=b"",bad_time=False,nonfinite=False,alias="i(@q.a[ic])"):
        matrix=np.column_stack((np.linspace(0.,1.,11),np.full(11,.2),np.full(11,.001)))
        if bad_time:matrix[5,0]=matrix[4,0]
        if nonfinite:matrix[4,1]=float("nan")
        header=("Plotname: Transient Analysis\nFlags: "+flags+"\nNo. Variables: 3\nNo. Points: 11\nVariables:\n0 time time\n1 v(x) voltage\n2 "+alias+" current\nBinary:\n").encode()
        path=self.root/("wave-"+str(len(list(self.root.iterdir()))));path.write_bytes(header+matrix.astype("<f8").tobytes()+last_extra)
        return path
    def read(self,path):
        reader=d.reader(d.ROOT/self.config["reader_path"],self.config["source_files"][self.config["reader_path"]])
        return reader(path,["v(x)","@q.a[ic]"],1.,.1)
    def test_frozen_reader_complete_alias_and_digest(self):
        path=self.raw();t,values,capture=self.read(path)
        self.assertEqual(capture["header_rows"],11);self.assertEqual(capture["columns"],3)
        self.assertEqual(capture["logical_vector_order"],["time","v(x)","@q.a[ic]"])
        self.assertEqual(capture["raw_sha256"],hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertTrue(np.all(values["v(x)"]==.2));self.assertTrue(np.all(values["@q.a[ic]"]==.001))
    def test_frozen_reader_refusals(self):
        for options in(dict(flags="complex"),dict(last_extra=b"x"),dict(bad_time=True),dict(nonfinite=True),dict(alias="i(@q.other[ic])")):
            with self.subTest(options=options),self.assertRaises(AssertionError):self.read(self.raw(**options))
    def test_original_reader_pin(self):
        pin=dict(self.config["source_files"][self.config["reader_path"]]);pin["sha256"]="0"*64
        with self.assertRaises(ValueError):d.reader(d.ROOT/self.config["reader_path"],pin)
    def test_known_headroom_event_and_active_mask(self):
        t=np.arange(6.);vc=np.array([.1,.9,.8,.3,.4,.6]);vb=np.full(6,.8);ve=np.zeros(6);ic=np.full(6,.002)
        values,index,intervals=d.hbt_metrics(t,vc,vb,ve,ic,2,start=2.)
        self.assertEqual(values["minimum_active_vce_v"],.3);self.assertEqual(values["maximum_alltime_abs_vce_v"],.9)
        self.assertEqual(values["maximum_alltime_abs_ic_per_emitter_a"],.001)
        self.assertEqual(index,3);self.assertEqual(len(intervals),1);self.assertEqual(intervals[0]["first_row"],3);self.assertEqual(intervals[0]["last_row"],3)
        with self.assertRaises(ValueError):d.hbt_metrics(t,vc,vb,ve,ic,2,start=9.)
    def test_sample_sign_margin_and_complete_delays(self):
        t=np.arange(301)/100.;n=np.zeros(len(t))
        for level,wrong,under in((.2,0,0),(.05,0,6),(-.2,6,6)):
            metrics,rows=d.sample_metrics(t,np.full(len(t),level),n,[1,1],[0.,1.],(.3,.6,.9),1.,.01,.3)
            self.assertEqual(metrics["wrong_sign_samples"],wrong);self.assertEqual(metrics["below_100mv_samples"],under)
            self.assertEqual(len(rows),under);self.assertEqual(len(metrics["clock_to_valid_by_bit_s"]),2);self.assertEqual(metrics["passed"],level==.2)
        with self.assertRaises(ValueError):d.sample_metrics(t,n,n,[1],[3.],(.3,.6,.9),1.,.01,.3)
    def archive(self,entries):
        path=self.root/("archive-"+str(len(list(self.root.iterdir())))+".tar.gz")
        with tarfile.open(path,"w:gz")as tar:
            for name,raw,kind in entries:
                info=tarfile.TarInfo("cloud-cdr-via2-m3-loaded/"+name)
                if kind=="link":info.type=tarfile.SYMTYPE;info.linkname="/outside";tar.addfile(info)
                else:info.size=len(raw);tar.addfile(info,io.BytesIO(raw))
        return path
    def test_archive_all_members_and_selected_only(self):
        inventory={"case/wave.raw":dict(bytes=4,sha256=d.sha(b"1234")),"empty.log":dict(bytes=0,sha256=d.sha(b""))}
        path=self.archive([("case/wave.raw",b"1234","file"),("empty.log",b"","file")])
        out=self.root/"selected"
        result=d.restore(path,inventory,{"case/wave.raw"},out)
        self.assertEqual(result["verified_members"],2);self.assertEqual(len(list(out.iterdir())),1)
        self.assertEqual(pathlib.Path(result["selected"]["case/wave.raw"]["path"]).read_bytes(),b"1234")
    def test_archive_corruption_ownership_and_missing_refusals(self):
        inventory={"wave.raw":dict(bytes=4,sha256=d.sha(b"1234"))}
        variants=[
            [("wave.raw",b"5678","file")],
            [("wave.raw",b"1234","file"),("wave.raw",b"1234","file")],
            [("wave.raw",b"1234","file"),("extra",b"x","file")],
            [("../wave.raw",b"1234","file")],
            [("wave.raw",b"","link")],
            [],
        ]
        for i,entries in enumerate(variants):
            with self.subTest(i=i),self.assertRaises(ValueError):d.restore(self.archive(entries),inventory,{"wave.raw"},self.root/("refused-"+str(i)))
if __name__=="__main__":
    c=json.loads((d.ROOT/d.CONFIG).read_bytes());d.source_guard(c)
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Controls))
    report=dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped))
    print("WAVE_DIAG_CONTROLS "+json.dumps(report),flush=True)
    raise SystemExit(0 if report==dict(tests=7,failures=0,errors=0,skips=0)else 1)
