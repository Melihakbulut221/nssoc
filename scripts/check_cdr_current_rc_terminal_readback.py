#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted synthetic boundary controls; never download or execute a native payload."""
import copy,hashlib,io,json,os,tarfile,unittest,zipfile
from pathlib import Path
import cloud_cdr_current_rc_terminal_readback as c
class Controls(unittest.TestCase):
    def setUp(self):
        self.cfg,self.pins=c.source_guard()
    def env(self):
        return {"GITHUB_ACTIONS":"true","RUNNER_ENVIRONMENT":"github-hosted","RUNNER_OS":"Linux",
          "GITHUB_REPOSITORY":"Melihakbulut221/nssoc","GITHUB_EVENT_NAME":"workflow_dispatch","GITHUB_RUN_ATTEMPT":"1",
          "GITHUB_REF":"refs/heads/"+c.BRANCH,"GITHUB_SHA":"a"*40,"GITHUB_RUN_ID":"123"}
    def fixture(self):
        model="mim/composition/pd500-mim-wire.spice";layout="mim/precise/source/parent/layout/result.json"
        plane=c.encoded({"status":"PASS_PD500_NATIVE160_PLANES_51_NETS_19_FAULTS",
          "anchors":[{"logical_net":"n"+str(i%51)}for i in range(160)],"inputs":{"source/layout/result.json":c.digest(b"{}\n")}})
        data={model:b"* synthetic model only\n",layout:b"{}\n","publication-driver.log":b"synthetic driver\n",
          "mim/precise/source/native-planes.json":plane,"mim/precise_reversed/source/native-planes.json":plane}
        outputs={n:c.digest(raw)for n,raw in data.items()}
        raw={"status":"SYNTHETIC_ONLY","outputs":{n:h for n,h in outputs.items()if n!="publication-driver.log"}}
        data["result.json"]=c.encoded(raw)
        summary={**raw,"outputs":outputs}
        cfg={"captures":self.cfg["captures"],"model_member":model,"model_sha256":outputs[model],"planes_sha256":c.digest(plane)}
        return cfg,summary,data
    def archive(self,data,extra=None):
        stream=io.BytesIO()
        with tarfile.open(fileobj=stream,mode="w:gz")as tar:
            root=tarfile.TarInfo("fixture/");root.type=tarfile.DIRTYPE;tar.addfile(root)
            for name,raw in data.items():
                item=tarfile.TarInfo("fixture/"+name);item.size=len(raw);tar.addfile(item,io.BytesIO(raw))
            if extra is not None:
                item,raw=extra;tar.addfile(item,io.BytesIO(raw)if raw is not None else None)
        stream.seek(0);return stream
    def inspect(self,data=None,extra=None):
        cfg,summary,normal=self.fixture()
        members,selected,dirs=c.inspect_archive(self.archive(normal if data is None else data,extra),"fixture",summary["outputs"],cfg["captures"])
        return cfg,summary,members,selected,dirs
    def test_source_and_context(self):
        self.assertEqual(len(self.pins["files"]),3);self.assertEqual(c.context(self.env())["run"],123)
    def test_context_refuses_local(self):
        e=self.env();e["GITHUB_ACTIONS"]="false"
        with self.assertRaises(AssertionError):c.context(e)
    def test_context_refuses_wrong_branch(self):
        e=self.env();e["GITHUB_REF"]="refs/heads/codex/cdr-drain-m1-loaded-electrical"
        with self.assertRaises(AssertionError):c.context(e)
    def test_context_refuses_retry(self):
        e=self.env();e["GITHUB_RUN_ATTEMPT"]="2"
        with self.assertRaises(AssertionError):c.context(e)
    def reserved(self):
        ctx=c.context(self.env());info={"id":7,"tag_name":"cloud-results-123-1-"+c.GROUP,
          "target_commitish":ctx["source"],"draft":False,"prerelease":True,"assets":[]}
        ref={"object":{"type":"commit","sha":ctx["source"]}}
        return ctx,info,ref
    def test_reserved_release_positive(self):
        ctx,info,ref=self.reserved();self.assertFalse(c.reservation(info,ref,ctx,True)["creation_attempted"])
    def test_reserved_release_rejects_existing_asset(self):
        ctx,info,ref=self.reserved();info["assets"]=[{}]
        with self.assertRaises(AssertionError):c.reservation(info,ref,ctx,True)
    def test_reserved_release_rejects_wrong_source(self):
        ctx,info,ref=self.reserved();info["target_commitish"]="b"*40
        with self.assertRaises(AssertionError):c.reservation(info,ref,ctx,True)
    def test_reserved_release_rejects_annotated_tag(self):
        ctx,info,ref=self.reserved();ref["object"]["type"]="tag"
        with self.assertRaises(AssertionError):c.reservation(info,ref,ctx,True)
    def producer(self):
        p=self.cfg["producer"]
        run={"id":p["run"],"head_sha":p["source"],"head_branch":p["branch"],"workflow_id":p["workflow_id"],
          "run_attempt":1,"event":"workflow_dispatch","status":"completed","conclusion":"success"}
        jobs={"total_count":len(self.cfg["jobs"]),"jobs":copy.deepcopy(self.cfg["jobs"])}
        release={"id":p["release_id"],"tag_name":p["tag"],"target_commitish":p["source"],
          "draft":False,"prerelease":True,"assets":copy.deepcopy(self.cfg["assets"])}
        ref={"object":{"type":"commit","sha":p["source"]}}
        return run,jobs,release,ref
    def test_producer_pinned_metadata_positive(self):
        self.assertTrue(c.producer_check(self.cfg,*self.producer()))
    def test_producer_mutations(self):
        mutations=[lambda x:x[0].__setitem__("head_sha","0"*40),lambda x:x[0].__setitem__("run_attempt",2),
          lambda x:x[1]["jobs"].pop(),lambda x:x[1]["jobs"][0].__setitem__("conclusion","failure"),
          lambda x:x[2]["assets"][0].__setitem__("digest","sha256:"+"0"*64),
          lambda x:x[2]["assets"][0].__setitem__("size",1),lambda x:x[3]["object"].__setitem__("sha","0"*40)]
        for mutation in mutations:
            rows=list(self.producer());mutation(rows)
            with self.subTest(mutation=repr(mutation)),self.assertRaises(AssertionError):c.producer_check(self.cfg,*rows)
    def test_producer_snapshot_namespace(self):
        values=dict(zip(("run","jobs","release","tag"),self.producer()))
        self.assertTrue(c.validate_snapshot(self.cfg,values))
        values["ref"]=values.pop("tag")
        with self.assertRaises(AssertionError):c.validate_snapshot(self.cfg,values)

    def test_parts_positive(self):
        c.validate_parts(self.cfg,self.cfg["parts"])
    def test_parts_refuses_substitution(self):
        for key,value in [("bytes",1),("sha256","0"*64),("source_directory","wrong")]:
            p=copy.deepcopy(self.cfg["parts"]);p[key]=value
            with self.subTest(key=key),self.assertRaises(AssertionError):c.validate_parts(self.cfg,p)
    def test_complete_archive_positive(self):
        cfg,s,m,selected,dirs=self.inspect()
        r=c.validate_readback(cfg,s,m,selected)
        self.assertEqual(r["full_members"],len(m));self.assertTrue(r["both_native_order_planes_byte_equal"])
    def test_archive_missing_member(self):
        cfg,s,data=self.fixture();data.pop(cfg["model_member"])
        with self.assertRaises(AssertionError):self.inspect(data)
    def test_archive_hash_change(self):
        cfg,s,data=self.fixture();data[cfg["model_member"]]+=b"changed"
        with self.assertRaises(AssertionError):self.inspect(data)
    def test_archive_extra_member(self):
        item=tarfile.TarInfo("fixture/unlisted");item.size=1
        with self.assertRaises(AssertionError):self.inspect(extra=(item,b"x"))
    def test_archive_duplicate_member(self):
        item=tarfile.TarInfo("fixture/result.json");item.size=2
        with self.assertRaises(AssertionError):self.inspect(extra=(item,b"{}"))
    def test_archive_bad_paths(self):
        for name in ["/fixture/escape","fixture/../escape","other/file","fixture//ambiguous","fixture/./ambiguous","fixture/back\\slash"]:
            item=tarfile.TarInfo(name);item.size=2
            with self.subTest(name=name),self.assertRaises(AssertionError):self.inspect(extra=(item,b"{}"))
    def test_archive_links_and_devices(self):
        for kind in [tarfile.SYMTYPE,tarfile.LNKTYPE,tarfile.FIFOTYPE,tarfile.CHRTYPE]:
            item=tarfile.TarInfo("fixture/unsafe");item.type=kind;item.linkname="result.json"
            with self.subTest(kind=kind),self.assertRaises(AssertionError):self.inspect(extra=(item,None))
    def test_archive_selected_json_malformed(self):
        cfg,s,data=self.fixture();data["result.json"]=b"{bad"
        with self.assertRaises(ValueError):self.inspect(data)
    def test_readback_summary_semantics_change(self):
        cfg,s,m,selected,_=self.inspect();s["status"]="changed"
        with self.assertRaises(AssertionError):c.validate_readback(cfg,s,m,selected)
    def test_readback_extra_raw_output(self):
        cfg,s,m,selected,_=self.inspect();raw=c.parse(selected["result.json"]);raw["outputs"]["extra"]="0"*64
        selected["result.json"]=c.encoded(raw);m["result.json"]={"bytes":len(selected["result.json"]),"sha256":c.digest(selected["result.json"])}
        with self.assertRaises(AssertionError):c.validate_readback(cfg,s,m,selected)
    def test_readback_requires_two_order_byte_equality(self):
        cfg,s,m,selected,_=self.inspect();selected["mim/precise_reversed/source/native-planes.json"]+=b"\n"
        with self.assertRaises(AssertionError):c.validate_readback(cfg,s,m,selected)
    def test_readback_raw_substituted_summary(self):
        cfg,s,m,selected,_=self.inspect();selected["result.json"]=c.encoded(s)
        m["result.json"]={"bytes":len(selected["result.json"]),"sha256":c.digest(selected["result.json"])}
        with self.assertRaises(AssertionError):c.validate_readback(cfg,s,m,selected)
    def test_no_nonfinite_json(self):
        with self.assertRaises(ValueError):c.parse(b'{"x":NaN}')

    def zip_fixture(self,rows):
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,"w")as z:
            for name,raw in rows:z.writestr(name,raw)
        stream.seek(0);return stream
    def test_zip_selected_json_positive(self):
        found=c.inspect_zip(self.zip_fixture([("folder/publication.json",b'{"original":true}'),("native.bin",b"synthetic")]),
          {"folder/publication.json":"original-publication.json"})
        self.assertEqual(found["folder/publication.json"],b'{"original":true}')
    def test_zip_missing_selected(self):
        with self.assertRaises(AssertionError):c.inspect_zip(self.zip_fixture([("other.json",b"{}")]),{"wanted.json":"out.json"})
    def test_zip_duplicate_selected(self):
        with self.assertRaises(AssertionError):c.inspect_zip(self.zip_fixture([("wanted.json",b"{}"),("wanted.json",b"{}")]),{"wanted.json":"out.json"})
    def test_zip_bad_paths(self):
        for name in ("../escape","/absolute","x//ambiguous"):
            with self.subTest(name=name),self.assertRaises(AssertionError):
                c.inspect_zip(self.zip_fixture([(name,b"{}"),("wanted.json",b"{}")]),{"wanted.json":"out.json"})
    def test_zip_invalid_json(self):
        with self.assertRaises(ValueError):c.inspect_zip(self.zip_fixture([("wanted.json",b"invalid")]),{"wanted.json":"out.json"})
    def test_zip_rejects_symlink(self):
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,"w")as z:
            item=zipfile.ZipInfo("wanted.json");item.create_system=3;item.external_attr=0o120777<<16;z.writestr(item,b"{}")
        stream.seek(0)
        with self.assertRaises(AssertionError):c.inspect_zip(stream,{"wanted.json":"out.json"})

def main():
    ctx=c.context()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Controls)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    record={"status":"PASS_HOSTED_READBACK_SOURCE_CONTROLS"if result.wasSuccessful()else"FAIL_HOSTED_READBACK_SOURCE_CONTROLS",
      "source":ctx,"tests":result.testsRun,"failures":len(result.failures),"errors":len(result.errors),
      "native_acquisition":False,"numerical_execution":False}
    Path("readback-source-controls.json").write_bytes(c.encoded(record))
    print(c.encoded(record).decode())
    if not result.wasSuccessful():raise SystemExit(1)
if __name__=="__main__":main()
