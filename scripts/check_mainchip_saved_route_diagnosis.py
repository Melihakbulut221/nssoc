#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import copy,io,json,tarfile,tempfile,unittest
from pathlib import Path
import cloud_mainchip_saved_route_diagnosis as d
class DiagnosisTests(unittest.TestCase):
    def fixture(self):
        plan=dict(attachments={"D":"n"},added_instances=["D"],mutable_nets=["n"],protected_nets=["clk"],original_instances_preserved=1)
        snapshot=dict(instances={"U":{},"D":{"pins":{"A":{"net":"n"}}}},nets={
          "n":{"wire":{"opcode_count":4},"encoded":{"metadata":"ROUTED","paths":["ROUTED"]},
          "identity":{"sigtype":"SIGNAL","terminals":[["D","A"],["U","Y"]]}},"clk":{}})
        return snapshot,plan
    def test_exact_incidence_and_census(self):
        s,p=self.fixture();before=copy.deepcopy((s,p));r=d.classify(s,p)
        self.assertEqual(r["added_diodes"],1);self.assertEqual(r["mutable_metadata_counts"],{"ROUTED":1})
        self.assertEqual((s,p),before)
    def test_missing_added_owner(self):
        s,p=self.fixture();p["added_instances"]=[]
        with self.assertRaises(AssertionError):d.classify(s,p)
    def test_unowned_mutable(self):
        s,p=self.fixture();p["mutable_nets"].append("other")
        with self.assertRaises(AssertionError):d.classify(s,p)
    def test_protected_owner(self):
        s,p=self.fixture();p["protected_nets"].append("n")
        with self.assertRaises(AssertionError):d.classify(s,p)
    def test_wrong_native_pin(self):
        s,p=self.fixture();s["instances"]["D"]["pins"]["A"]["net"]="other"
        with self.assertRaises(AssertionError):d.classify(s,p)
    def test_missing_native_incidence(self):
        s,p=self.fixture();s["nets"]["n"]["identity"]["terminals"]=[["U","Y"]]
        with self.assertRaises(AssertionError):d.classify(s,p)
    def archive(self,path,name,raw=b"data",kind=None):
        with tarfile.open(path,"w:gz")as f:
            item=tarfile.TarInfo(name);item.size=len(raw)
            if kind is not None:item.type=kind;item.size=0;item.linkname="outside"
            f.addfile(item,io.BytesIO(raw)if item.isfile()else None)
    def test_complete_archive_and_unselected_tamper(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);a=root/"a.tar.gz";raw=b"data"
            self.archive(a,"a.json",raw)
            pins={"a.json":{"bytes":4,"sha256":d.hashlib.sha256(raw).hexdigest()}}
            self.assertEqual(d.archive_reader.restore(a,pins,set(),root/"good"),pins)
            pins["a.json"]["sha256"]="0"*64
            with self.assertRaises((AssertionError,ValueError)):
                d.archive_reader.restore(a,pins,set(),root/"bad")
    def test_symlink_refused(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);a=root/"a.tar.gz";self.archive(a,"a.json",kind=tarfile.SYMTYPE)
            with self.assertRaises((AssertionError,ValueError)):
                d.archive_reader.restore(a,{"a.json":{"bytes":0,"sha256":d.hashlib.sha256(b"").hexdigest()}},{"a.json"},root/"out")
    def test_complete_census_required(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);a=root/"a.tar.gz";self.archive(a,"a.json")
            pins={n:{"bytes":4,"sha256":d.hashlib.sha256(b"data").hexdigest()}for n in("a.json","missing.json")}
            with self.assertRaises((AssertionError,ValueError)):d.archive_reader.restore(a,pins,set(),root/"out")
if __name__=="__main__":unittest.main(verbosity=2)
