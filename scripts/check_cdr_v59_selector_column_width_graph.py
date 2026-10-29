#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted-only admission, provenance, no-acceptance and terminal controls."""
import ast, copy, hashlib, json, os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import cdr_v59_selector_column_width_graph as s
import cloud_cdr_v59_selector_column_width_graph as d
import check_cdr_v59_tail_access_topology as original_controls

class Controls(unittest.TestCase):
    def test_authorizations_and_source(self):
        m=s.methods()
        self.assertGreaterEqual(len(m["protected_sha256"]),1020)
        for key in s.FALSE:
            bad=copy.deepcopy(m);bad[key]=True
            with self.assertRaises(AssertionError):s.validate_authorizations(bad)
        for key in s.NATIVE+s.FALSE+("source_controls_authorized",):
            bad=copy.deepcopy(m);bad[key]=1
            with self.assertRaises(AssertionError):s.validate_authorizations(bad)
        bad=copy.deepcopy(m);bad[s.NATIVE[0]]=not bad[s.NATIVE[1]]
        with self.assertRaises(AssertionError):s.validate_authorizations(bad)
        bad=copy.deepcopy(m)
        for k in s.NATIVE:bad[k]=False
        s.validate_authorizations(bad)
        with self.assertRaises(AssertionError):s.execution_context(bad)
        with patch.dict(os.environ,{"GITHUB_RUN_ATTEMPT":"2"}):
            with self.assertRaises(AssertionError):s.execution_context(m)

    def test_live_producer_exact_full_release(self):
        objects=[s.read(s.ROOT/(s.PREFIX+k+".json"))for k in ("run","jobs","release","tag")]
        s.validate_live(*objects)
        cases=[(0,"head_sha","0"*40),(0,"conclusion","failure"),(0,"run_attempt",2),
          (0,"path","wrong.yml"),(1,"total_count",1),(2,"id",1),(2,"draft",True)]
        for index,key,value in cases:
            changed=copy.deepcopy(objects);changed[index][key]=value
            with self.assertRaises((AssertionError,ValueError)):s.validate_live(*changed)
        for change in ("missing","digest","job"):
            changed=copy.deepcopy(objects)
            if change=="missing":changed[2]["assets"].pop()
            elif change=="digest":changed[2]["assets"][0]["digest"]="sha256:"+"0"*64
            else:changed[1]["jobs"][0]["conclusion"]="failure"
            with self.assertRaises(AssertionError):s.validate_live(*changed)

    def test_full_inventory_admission(self):
        e=s.expected_files()
        self.assertEqual(len(e),3992)
        self.assertEqual(e["layout/"+s.TOP+".gds"],s.GDS_SHA)
        self.assertEqual(e["result.json"],s.SUMMARY_SHA)
        self.assertEqual(e["physical/lvs_flat/result.lvsdb"],"46f7b57763441747cacf5740887fdadd0bfbc75c40549effd86afb7a60dba276")
        self.assertEqual(len([n for n in e if n.startswith("saved-input/"+s.previous.inherited.VIEW+"/")]),605)

    def test_exact_reversible_derivation(self):
        texts,proof=s.derived_texts()
        self.assertEqual(len(texts),3)
        for name,text in texts.items():
            ast.parse(text)
            restored=text
            for c in reversed(proof[name]["changes"]):
                self.assertEqual(restored.count(c["after"]),c["count"])
                restored=restored.replace(c["after"],c["before"])
            self.assertEqual(restored,(s.ROOT/proof[name]["source"]).read_text())
        self.assertIn("len(faults)==19",texts["width_planes.py"])
        self.assertIn("len(rows)==len(expected)==160",texts["width_planes.py"])
        self.assertIn("assert len(used)==16",texts["check_width_parent_geometry.py"])

    def test_metadata_projection_and_source_preservation(self):
        with tempfile.TemporaryDirectory()as temp:
            out=Path(temp);base=s.baseline(out)/"parent";phy=out/s.VIEW
            (base/"inputs/sampler_cd/layout").mkdir(parents=True)
            (base/"layout").mkdir();(phy/"layout").mkdir()
            (phy/"physical/lvs_flat").mkdir(parents=True)
            original=dict(source_plan={"source":"original"},placements={str(i):{}for i in range(16)},
              primitive_census={"fixture":500},ports={str(i):"box"for i in range(25)},historical="keep original")
            s.atomic(base/"layout/result.json",original);s.atomic(base/"children.json",{"children":{}})
            (base/"inputs/sampler_cd/layout/leaf.gds").write_bytes(b"source")
            s.atomic(phy/"layout/result.json",dict(ports=original["ports"]))
            (phy/"layout"/(s.TOP+".gds")).write_bytes(b"new physical")
            (phy/"layout"/(s.TOP+".lef")).write_bytes(b"lef")
            (phy/"physical/lvs_flat/result.lvsdb").write_bytes(b"new lvs")
            before={p:p.read_bytes()for p in phy.rglob("*")if p.is_file()}
            with patch.object(s,"validate_view",return_value={}),patch.object(s,"GDS_SHA",s.sha(phy/"layout"/(s.TOP+".gds"))):
                meta=s.prepare_view(out)
            self.assertEqual(before,{p:p.read_bytes()for p in before})
            self.assertEqual(meta["source_plan"],original["source_plan"])
            self.assertEqual(meta["placements"],original["placements"])
            self.assertFalse(meta["physical_accepted"])
            self.assertEqual((out/"candidate/parent/physical/lvs_flat/result.lvsdb").read_bytes(),b"new lvs")
            s.check_derived(out)
            target=out/"candidate/methods/width_planes.py"
            target.write_text(target.read_text()+"\n# modified\n")
            with self.assertRaises(AssertionError):s.check_derived(out)

    def test_report_bindings_reject_stale_and_escaped_inputs(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp);view=root/"candidate";view.mkdir()
            p=view/"actual.json";p.write_bytes(b"actual")
            valid={"inputs":{str(p):{"bytes":6,"sha256":s.sha(p)}}}
            s.report_inputs(valid,view)
            for key,value in (("bytes",5),("sha256","0"*64)):
                bad=copy.deepcopy(valid);bad["inputs"][str(p)][key]=value
                with self.assertRaises(AssertionError):s.report_inputs(bad,view)
            outer=root/"outside";outer.write_bytes(b"actual")
            with self.assertRaises(AssertionError):s.report_inputs({"inputs":{str(outer):s.sha(outer)}},view)
            link=view/"link";link.symlink_to(p)
            with self.assertRaises(AssertionError):s.report_inputs({"inputs":{str(link):s.sha(p)}},view)
            with self.assertRaises(AssertionError):s.report_inputs({"inputs":{}},view)

    def test_legacy_verdict_cannot_award_width_equivalence(self):
        with tempfile.TemporaryDirectory()as temp:
            out=Path(temp);old=s.baseline(out)/"wire";new=out/"candidate/wire"
            names=("native05/result.json","device-locations01.json","anchors08.json")
            fixtures=("graph.json","locations.json","anchors.json")
            for dest in (old,new):
                for name,fixture in zip(names,fixtures):
                    target=dest/name;target.parent.mkdir(parents=True,exist_ok=True)
                    target.write_bytes((s.ROOT/original_controls.FIXTURE/fixture).read_bytes())
            first=s.legacy_topology_diagnostic(out)
            self.assertEqual(first["status"],"LEGACY_COMPARATOR_REJECTED")
            self.assertFalse(first["graph_equivalence_accepted"])
            self.assertFalse(first["legacy_material_policy_applicable"])
            self.assertEqual(first,s.legacy_topology_diagnostic(out))
            with patch.object(s.topology,"compare",return_value={"illustrative_return":True}):
                returned=s.legacy_topology_diagnostic(out)
            self.assertEqual(returned["status"],"LEGACY_COMPARATOR_RETURNED")
            self.assertFalse(returned["graph_equivalence_accepted"])

    def test_driver_command_identity_and_failed_record_retained(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp);trace=root/"trace";trace.mkdir()
            class Supervisor:
                TRACE=trace
                def supervised(self,argv,label,seconds,cwd):
                    record=dict(label=label,argv=list(map(str,argv)),returncode=9,
                      supervision_failure=None,process_group_cleanup=dict(remaining_live=[]))
                    for stream in ("stdout","stderr"):
                        p=trace/(label+"."+stream);p.write_bytes(b"complete failure stream")
                        record[stream+"_bytes"]=p.stat().st_size;record[stream+"_sha256"]=s.sha(p)
                    s.atomic(trace/(label+".command.json"),record)
                    raise RuntimeError("original supervised failure")
            r={"commands":[]};label=list(d.BUDGETS)[0]
            with patch.object(d,"OUT",root):
                with self.assertRaisesRegex(RuntimeError,"original supervised failure"):
                    d.execute(Supervisor(),r,["fixture"],label)
            self.assertEqual(r["commands"][0]["returncode"],9)
            self.assertTrue(r["command_errors"])

    def test_terminal_cleanup_continues_after_failure(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp);calls=[]
            class Stop:
                def set(self):calls.append("stop")
            class Supervisor:
                ACTIVE=None;STOP=Stop()
                def stop_process(self,p):calls.append("cleanup");raise RuntimeError("cleanup failed")
                def sample(self,p):calls.append("sample")
            class Heartbeat:
                def join(self,timeout):calls.append("join")
                def is_alive(self):return False
            result={"status":"FAIL_ORIGINAL","native_graph_readback_passed":False,
              "error":{"type":"ValueError","error":"original failure"}}
            with patch.object(d,"OUT",root),patch.object(s,"methods",return_value={"protected_sha256":{}}):
                errors=d.finish(result,Supervisor(),Heartbeat(),{})
            self.assertTrue(errors)
            self.assertEqual(calls,["cleanup","stop","join","sample"])
            self.assertEqual(result["error"]["error"],"original failure")
            self.assertFalse(result["native_graph_readback_passed"])
            self.assertFalse(result["terminal_finalization_complete"])
            self.assertTrue((root/"result.json").is_file())

if __name__=="__main__":
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Controls)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps(dict(status="PASS_GRAPH_SOURCE_CONTROLS_ONLY"if result.wasSuccessful()else"FAIL_GRAPH_SOURCE_CONTROLS",
      tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),
      native_execution=False,graph_equivalence_accepted=False,physical_accepted=False,electrical_accepted=False),sort_keys=True),flush=True)
    raise SystemExit(0 if result.wasSuccessful()else 1)
