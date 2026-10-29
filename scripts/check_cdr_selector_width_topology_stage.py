#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted-only admission, terminal preservation and exact source controls."""
import copy,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import cdr_selector_width_topology_stage as s
import cloud_cdr_selector_width_topology as d
import check_cdr_selector_width_topology as width

class Controls(unittest.TestCase):
    def test_protected_source_and_typed_authorizations(self):
        m=s.methods()
        self.assertGreater(len(m["protected_sha256"]),1039)
        for key in s.FALSE:
            bad=copy.deepcopy(m);bad[key]=True
            with self.assertRaises(AssertionError):s.validate_authorizations(bad)
        for key in s.NATIVE+s.FALSE+("source_controls_authorized",):
            bad=copy.deepcopy(m);bad[key]=1
            with self.assertRaises(AssertionError):s.validate_authorizations(bad)
        for value in (False,True):
            valid=copy.deepcopy(m)
            for key in s.NATIVE:valid[key]=value
            s.validate_authorizations(valid)
        bad=copy.deepcopy(m);bad[s.NATIVE[0]]=not bad[s.NATIVE[1]]
        with self.assertRaises(AssertionError):s.validate_authorizations(bad)

    def test_cloud_context_refuses_disabled_and_repeated_attempt(self):
        m=s.methods();disabled=copy.deepcopy(m)
        for key in s.NATIVE:disabled[key]=False
        with self.assertRaises(AssertionError):s.execution_context(disabled)
        enabled=copy.deepcopy(m)
        for key in s.NATIVE:enabled[key]=True
        s.execution_context(enabled)
        for key,value in (("GITHUB_RUN_ATTEMPT","2"),("RUNNER_ENVIRONMENT","self-hosted"),
          ("GITHUB_REPOSITORY","other/repo"),("GITHUB_ACTIONS","false")):
            with patch.dict(os.environ,{key:value}):
                with self.assertRaises(AssertionError):s.execution_context(enabled)

    def test_complete_producer_and_refusals(self):
        original=[s.read(s.ROOT/(s.PREFIX+k+".json"))for k in ("run","jobs","release","tag")]
        s.evidence.validate_live(*original)
        for index,key,value in ((0,"head_sha","0"*40),(0,"conclusion","failure"),(0,"run_attempt",2),
          (0,"path","wrong.yml"),(1,"total_count",1),(2,"id",1),(2,"draft",True)):
            bad=copy.deepcopy(original);bad[index][key]=value
            with self.assertRaises((AssertionError,ValueError)):s.evidence.validate_live(*bad)
        for fault in ("missing_asset","digest","job","tag"):
            bad=copy.deepcopy(original)
            if fault=="missing_asset":bad[2]["assets"].pop()
            elif fault=="digest":bad[2]["assets"][0]["digest"]="sha256:"+"0"*64
            elif fault=="job":bad[1]["jobs"][0]["conclusion"]="failure"
            else:bad[3]["object"]["sha"]="0"*40
            with self.assertRaises((AssertionError,ValueError)):s.evidence.validate_live(*bad)

    def test_full_authenticated_inventory_and_root_projection(self):
        e=s.expected_files();roots=s.expected_roots()
        self.assertEqual(len(e),4103);self.assertEqual(len(roots["old"]),605)
        self.assertEqual(len(roots["fresh"]),75);self.assertEqual(e["result.json"],s.SUMMARY_SHA)
        for side,prefix in (("old",s.OLD+"/"),("fresh",s.FRESH+"/")):
            self.assertEqual(roots[side],{n[len(prefix):]:h for n,h in e.items()if n.startswith(prefix)})
        self.assertEqual(roots["fresh"]["parent/layout/"+s.TOP+".gds"],s.GDS_SHA)
        self.assertEqual(roots["fresh"]["wire/native05/wires.l2n"],
          "4d0dd5ed072b2bd195ac779725100284aeabde99cad53597c2d4a6b2bca0be38")

    def test_actual_pya_free_coordinate_controls(self):
        result=width.source_controls()
        self.assertEqual((result["positive_cases"],result["rejected_cases"]),(3,12))
        self.assertFalse(result["pya_imported"]);self.assertFalse(result["native_geometry_executed"])

    def test_original_supervision_failure_and_complete_streams_preserved(self):
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
            result={"commands":[]};label=list(d.BUDGETS)[0]
            with patch.object(d,"OUT",root):
                with self.assertRaisesRegex(RuntimeError,"original supervised failure"):
                    d.execute(Supervisor(),result,["fixture"],label)
            self.assertEqual(result["commands"][0]["returncode"],9)
            self.assertTrue(result["command_errors"])

    def test_successful_command_cannot_hide_stream_tamper(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp);trace=root/"trace";trace.mkdir()
            class Supervisor:
                TRACE=trace
                def supervised(self,argv,label,seconds,cwd):
                    record=dict(label=label,argv=list(map(str,argv)),returncode=0,
                      supervision_failure=None,process_group_cleanup=dict(remaining_live=[]))
                    for stream in ("stdout","stderr"):
                        p=trace/(label+"."+stream);p.write_bytes(b"original")
                        record[stream+"_bytes"]=p.stat().st_size;record[stream+"_sha256"]=s.sha(p)
                    s.atomic(trace/(label+".command.json"),record)
                    (trace/(label+".stdout")).write_bytes(b"modified")
            result={"commands":[]};label=list(d.BUDGETS)[0]
            with patch.object(d,"OUT",root):
                with self.assertRaisesRegex(AssertionError,"Complete command stream changed"):
                    d.execute(Supervisor(),result,["fixture"],label)
            self.assertEqual(result["commands"],[]);self.assertTrue(result["command_errors"])

    def test_terminal_cleanup_continues_after_original_failure(self):
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
            result={"status":"FAIL_ORIGINAL","native_width_comparison_passed":False,
              "error":{"type":"ValueError","error":"original failure"}}
            with patch.object(d,"OUT",root),patch.object(s,"methods",return_value={"protected_sha256":{}}):
                errors=d.finish(result,Supervisor(),Heartbeat(),{})
            self.assertTrue(errors);self.assertEqual(calls,["cleanup","stop","join","sample"])
            self.assertEqual(result["error"]["error"],"original failure")
            self.assertFalse(result["native_width_comparison_passed"])
            self.assertFalse(result["terminal_finalization_complete"])
            self.assertTrue((root/"result.json").is_file())

    def test_missing_or_malformed_terminal_cannot_become_success(self):
        for raw in (None,b"{malformed original terminal"):
            with tempfile.TemporaryDirectory()as temp:
                root=Path(temp);path=root/"result.json"
                (root/"failure.stderr").write_bytes(b"actual failure")
                if raw is not None:path.write_bytes(raw)
                with patch.object(d,"OUT",root):
                    result=d.publication_result({"fixture":True})
                self.assertEqual(result["status"],"FAIL_MISSING_OR_INVALID_TERMINAL_REPORT")
                self.assertFalse(result["native_width_comparison_passed"])
                self.assertFalse(result["terminal_finalization_complete"])
                self.assertEqual(result["outputs"],{"failure.stderr":s.sha(root/"failure.stderr")})
                if raw is None:self.assertFalse(path.exists())
                else:self.assertEqual(path.read_bytes(),raw)

    def test_running_report_preserves_original_bytes_and_failed_scope(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp);result=d.initial({"fixture":True})
            s.atomic(root/"result.json",result);raw=(root/"result.json").read_bytes()
            with patch.object(d,"OUT",root):
                failed=d.publication_result({"fixture":True})
            self.assertEqual(failed["status"],"FAIL_INCOMPLETE_WIDTH_TOPOLOGY_EVIDENCE")
            self.assertFalse(failed["native_width_comparison_passed"])
            self.assertEqual((root/"result.json").read_bytes(),raw)

    def test_publication_refuses_false_success_and_inventory_drift(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp);result=d.initial({"fixture":True})
            result.update(status="FAIL_FIXTURE",outputs={})
            with patch.object(d,"OUT",root):
                d.validate_publication(result)
                for key in d.FALSE:
                    bad=copy.deepcopy(result);bad[key]=True
                    with self.assertRaises(AssertionError):d.validate_publication(bad)
                bad=copy.deepcopy(result);bad["status"]=d.PASS
                with self.assertRaises(AssertionError):d.validate_publication(bad)
                (root/"extra.txt").write_text("unlisted")
                with self.assertRaisesRegex(AssertionError,"Publication inventory changed"):
                    d.validate_publication(result)

if __name__=="__main__":
    assert os.environ.get("GITHUB_ACTIONS")=="true" and os.environ.get("RUNNER_ENVIRONMENT")=="github-hosted"
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Controls)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps(dict(status="PASS_WIDTH_STAGE_SOURCE_CONTROLS_ONLY"if result.wasSuccessful()else"FAIL_WIDTH_STAGE_SOURCE_CONTROLS",
      tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),
      native_execution=False,graph_equivalence_accepted=False,physical_accepted=False,electrical_accepted=False),sort_keys=True),flush=True)
    raise SystemExit(0 if result.wasSuccessful()else 1)
