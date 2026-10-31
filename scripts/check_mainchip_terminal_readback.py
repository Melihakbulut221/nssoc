#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import copy,io,json,os,tarfile,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import mainchip_terminal_readback as m
class Controls(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.archive=self.root/"fixture.tar.gz"
        self.raw={"reports/failure.json":b'{"status":"REJECTED","physical_acceptance":false}\n',"logs/route.stdout":b"complete native error log\n","logs/route.stderr":b"","native/design.odb":b"synthetic excluded design"}
        self.index={n:dict(bytes=len(b),sha256=m.sha(b))for n,b in self.raw.items()}
        self.selected=["reports/failure.json","logs/route.stdout","logs/route.stderr"]
    def tearDown(self):self.temp.cleanup()
    def pack(self,rows=None):
        with tarfile.open(self.archive,"w:gz")as t:
            for n,b,kind in rows or [(n,b,tarfile.REGTYPE)for n,b in self.raw.items()]:
                i=tarfile.TarInfo(n);i.size=len(b);i.type=kind
                if kind in(tarfile.SYMTYPE,tarfile.LNKTYPE):i.linkname="reports/failure.json";i.size=0
                t.addfile(i,io.BytesIO(b)if i.isfile()else None)
    def scan(self,index=None,selected=None):
        return m.scan(self.archive,self.index if index is None else index,self.selected if selected is None else selected,self.root/"reports-out")
    def test_complete_rejected_reports_without_native_export(self):
        self.pack();r=self.scan()
        self.assertEqual(len(r["all_members"]),4);self.assertEqual(set(r["reports"]),set(self.selected))
        self.assertFalse((self.root/"reports-out/native/design.odb").exists())
        self.assertEqual((self.root/"reports-out/logs/route.stderr").read_bytes(),b"")
        self.assertFalse(json.loads((self.root/"reports-out/reports/failure.json").read_bytes())["physical_acceptance"])
    def test_unselected_native_corruption_is_rejected(self):
        self.pack();d=copy.deepcopy(self.index);d["native/design.odb"]["sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"native member hash"):self.scan(d)
    def test_duplicate_missing_and_extra_members_are_rejected(self):
        base=[(n,b,tarfile.REGTYPE)for n,b in self.raw.items()]
        for rows in(base+[base[0]],base[:-1],base+[("extra.txt",b"x",tarfile.REGTYPE)]):
            with tempfile.TemporaryDirectory()as td:
                self.pack(rows)
                with self.assertRaises(ValueError):m.scan(self.archive,self.index,self.selected,Path(td)/"out")
    def test_symlink_hardlink_and_special_file_refused(self):
        for kind in(tarfile.SYMTYPE,tarfile.LNKTYPE,tarfile.FIFOTYPE):
            with self.subTest(kind=kind):
                self.pack([("reports/failure.json",b"",kind)])
                with tempfile.TemporaryDirectory()as td:
                    with self.assertRaisesRegex(ValueError,"regular"):m.scan(self.archive,self.index,self.selected,Path(td)/"out")
    def test_traversal_noncanonical_and_native_selection_refused(self):
        for n in("../x","/x","a/../x","a//x","./x","a\\x","a\nx"):
            with self.subTest(n=n):
                with self.assertRaises(ValueError):m.valid_name(n)
        self.pack()
        with self.assertRaisesRegex(ValueError,"whitelist"):self.scan(selected=["native/design.odb"])
    def test_size_invalid_json_and_duplicate_json_refused(self):
        self.pack();d=copy.deepcopy(self.index);d["reports/failure.json"]["bytes"]+=1
        with self.assertRaisesRegex(ValueError,"size"):self.scan(d)
        for raw in(b'{"x":NaN}',b'{"x":1,"x":2}',b'{"broken":'):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):m.decode(raw)
    def test_destination_exact_empty_source_and_complete_publication(self):
        head="a"*40;tag="cloud-results-17-1-"+m.GROUP
        release=dict(id=19,tag_name=tag,target_commitish=head,draft=False,prerelease=True,assets=[])
        ref=dict(object=dict(type="commit",sha=head))
        def api(path):return copy.deepcopy(release if path.startswith("releases/")else ref)
        with patch.dict(os.environ,{"GITHUB_RUN_ID":"17","GITHUB_RUN_ATTEMPT":"1"}),patch.object(m,"api",side_effect=api):
            self.assertEqual(m.destination(head,True)[0],tag)
            for key,value in(("id",429993235),("draft",True),("prerelease",False),("target_commitish","main"),("assets",[dict(name="existing")])):
                old=release[key];release[key]=value
                with self.subTest(key=key):
                    with self.assertRaises(ValueError):m.destination(head,True)
                release[key]=old
            ref["object"]["sha"]="b"*40
            with self.assertRaises(ValueError):m.destination(head,True)
            ref["object"]["sha"]=head
            release["assets"]=[dict(name="out.json",size=2,digest="sha256:"+"1"*64)]
            m.destination(head,False,{"out.json":dict(bytes=2,sha256="1"*64)})
            with self.assertRaises(ValueError):m.destination(head,False,{})
    def test_mutable_download_counters_do_not_weaken_published_content_identity(self):
        r=dict(id=19,tag_name="tag",target_commitish="a"*40,draft=False,prerelease=True,
          assets=[dict(id=7,name="part",size=17,digest="sha256:"+"1"*64,download_count=0)])
        changed=copy.deepcopy(r);changed["assets"][0]["download_count"]=5
        self.assertEqual(m.immutable_release(r),m.immutable_release(changed))
        for key,value in(("id",8),("name","other"),("size",18),("digest","sha256:"+"2"*64)):
            bad=copy.deepcopy(changed);bad["assets"][0][key]=value
            self.assertNotEqual(m.immutable_release(r),m.immutable_release(bad))
        changed["target_commitish"]="b"*40
        self.assertNotEqual(m.immutable_release(r),m.immutable_release(changed))
    def test_nonhosted_refusal_precedes_network(self):
        with patch.dict(os.environ,{"GITHUB_ACTIONS":"false"}),patch.object(m,"api",side_effect=AssertionError("network")):
            with self.assertRaisesRegex(ValueError,"hosted only"):m.source_gate()

    def test_only_two_exact_drt_reports_can_be_selected(self):
        reports={n:("violation type: Short\nsrcs: net_a net_b\nbbox = ( 1.000, 2.000 ) - ( 3.000, 4.000 ) on Layer met2\n"+n+"\n").encode()for n in m.DRT_REPORTS}
        self.raw.update(reports);self.index={n:dict(bytes=len(b),sha256=m.sha(b))for n,b in self.raw.items()}
        self.pack();result=self.scan(selected=list(m.DRT_REPORTS))
        self.assertEqual(set(result["all_members"]),set(self.raw))
        self.assertEqual(set(result["reports"]),set(m.DRT_REPORTS))
        for n,b in reports.items():self.assertEqual((self.root/"reports-out"/n).read_bytes(),b)
        self.assertFalse((self.root/"reports-out/native/design.odb").exists())
        self.assertFalse((self.root/"reports-out/reports/failure.json").exists())
    def test_arbitrary_rpt_path_and_case_are_rejected(self):
        for n in("native/design.rpt","work/bulk-postdrt-antenna/fixed-routing.drc-15.rpt","work/bulk-postdrt-antenna/fixed-routing.drc-5.RPT"):
            with self.subTest(n=n),tempfile.TemporaryDirectory()as td:
                raw=b"not an authorized DRT report\n";index={n:dict(bytes=len(raw),sha256=m.sha(raw))}
                self.pack([(n,raw,tarfile.REGTYPE)])
                with self.assertRaisesRegex(ValueError,"whitelist"):m.scan(self.archive,index,[n],Path(td)/"out")
    def test_exact_drt_report_still_requires_digest_and_utf8(self):
        n=m.DRT_REPORTS[0]
        for raw,bad_hash in((b"valid text\n",True),(b"\xff\x00",False)):
            with self.subTest(raw=raw),tempfile.TemporaryDirectory()as td:
                self.pack([(n,raw,tarfile.REGTYPE)])
                index={n:dict(bytes=len(raw),sha256=("0"*64 if bad_hash else m.sha(raw)))}
                with self.assertRaises((ValueError,UnicodeError)):m.scan(self.archive,index,[n],Path(td)/"out")

if __name__=="__main__":
    if os.environ.get("GITHUB_ACTIONS")!="true":raise RuntimeError("Run controls on GitHub only")
    unittest.main(verbosity=2)
