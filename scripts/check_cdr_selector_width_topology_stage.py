#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted-only admission, terminal preservation and exact source controls."""
import copy,io,json,os,tarfile,tempfile,threading,unittest
from contextlib import ExitStack
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

    def test_main_run_preserves_body_failure_when_terminal_cleanup_also_fails(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp);out=root/"out";transport=root/"publication"
            class Supervisor:
                TRACE=out/"supervision";ACTIVE=None
                STOP=threading.Event()
                def heartbeat(self):self.STOP.wait(20)
                def interrupted(self,*args):raise RuntimeError("unexpected signal")
                def stop_process(self,p):raise RuntimeError("cleanup-extra")
                def sample(self,label):return {"fixture":True}
            method={"protected_sha256":{d.runtime.SAMPLER:"fixture"}}
            with patch.object(d,"OUT",out),patch.object(d,"TRANSPORT",transport),\
              patch.object(d,"storage",return_value={}),patch.object(s,"authorize",return_value=method),\
              patch.object(s,"methods",return_value=method),\
              patch.object(d.runtime,"supervisor",return_value=Supervisor()),\
              patch.object(d,"run",side_effect=RuntimeError("body-original")):
                with self.assertRaisesRegex(RuntimeError,"body-original"):
                    d.main_run({"fixture":True})
            report=s.read(out/"result.json")
            self.assertEqual(report["status"],"FAIL_TERMINAL")
            self.assertIn("body-original",report["error"]["error"])
            self.assertTrue(any("cleanup-extra"in e["error"]for e in report["terminal_errors"]))
            self.assertFalse(report["native_width_comparison_passed"])
            self.assertTrue(Supervisor.STOP.is_set())

    def test_actual_pack_and_publish_preserve_integrity_failure_and_empty_files(self):
        # Actual production publish() and pack(); only remote uploader/reservation
        # and resource availability are fixtures. All work executes on the host.
        for fail_upload in (False,True):
            with tempfile.TemporaryDirectory()as temp:
                root=Path(temp);out=root/"out";out.mkdir();transport=root/"publication"
                external=root/"driver.log";external.write_bytes(b"")
                (out/"native-controls.json").write_bytes(b"")
                (out/"native-synthetic.json").write_bytes(b"{partial original")
                raw=b"{malformed original terminal";(out/"result.json").write_bytes(raw)
                captured=[];old_hook=d.publisher.release
                def uploader(path,tag):
                    self.assertGreater(path.stat().st_size,0)
                    captured.append((path.name,path.read_bytes(),tag))
                    if fail_upload:raise RuntimeError("upload-original")
                    return {"name":path.name,"bytes":path.stat().st_size,"sha256":s.sha(path)}
                with ExitStack()as stack:
                    for obj,name,value in ((d,"OUT",out),(d,"TRANSPORT",transport),(d,"DRIVER_LOG",external)):
                        stack.enter_context(patch.object(obj,name,value))
                    stack.enter_context(patch.object(d,"storage",return_value={}))
                    stack.enter_context(patch.object(s,"publication_authorize",return_value={}))
                    stack.enter_context(patch.object(s,"methods",side_effect=AssertionError("protected proof changed")))
                    stack.enter_context(patch.object(s.evidence,"source_guard",side_effect=AssertionError("protected proof changed")))
                    stack.enter_context(patch.object(d.publisher,"publish",side_effect=uploader))
                    # Keep actual helper factory and publication_files()/pack().
                    # Only the reservation's eventual network call is never used
                    # because this test uploader records data without networking.
                    result=d.publication_result({"fixture":True})
                    if fail_upload:
                        with self.assertRaisesRegex(RuntimeError,"upload-original"):d.publish(result)
                    else:
                        self.assertEqual(d.publish(result)["status"],
                          "PASS_COMPLETE_WIDTH_TOPOLOGY_EVIDENCE_PUBLICATION_ONLY")
                    self.assertIs(d.publisher.release,old_hook)
                    with self.assertRaisesRegex(AssertionError,"Publication already attempted"):
                        d.publish(result)
                self.assertEqual((out/"result.json").read_bytes(),raw)
                self.assertEqual((out/"native-controls.json").read_bytes(),b"")
                self.assertEqual(external.read_bytes(),b"")
                self.assertTrue(captured)
                self.assertEqual(result["status"],"FAIL_PROTECTED_SOURCE_AT_PUBLICATION")
                self.assertIn("protected proof changed",result["publication_source_error"]["error"])
                manifests=list(transport.glob("*.parts.json"));self.assertEqual(len(manifests),1)
                manifest=s.read(manifests[0])
                joined=b"".join((transport/r["name"]).read_bytes()for r in manifest["parts"])
                with tarfile.open(fileobj=io.BytesIO(joined),mode="r:gz")as archive:
                    self.assertEqual(archive.extractfile("out/result.json").read(),raw)
                    self.assertEqual(archive.extractfile("out/native-controls.json").read(),b"")
                    self.assertEqual(archive.extractfile("out/publication-driver.log").read(),b"")
                    self.assertEqual(archive.extractfile("out/native-synthetic.json").read(),b"{partial original")
                plan=s.read(next(transport.glob("*.direct-publication-plan.json")))
                rows={r["suffix"]:r for r in plan["files"]}
                for suffix in ("native-controls.json","driver.log"):
                    row=rows[suffix]
                    self.assertEqual(row["bytes"],0);self.assertEqual(row["disposition"],"archive_only_empty")
                    self.assertEqual(row["sha256"],"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
                    self.assertFalse(any(n.endswith("."+suffix)for n,_,_ in captured))
                    self.assertEqual(result["outputs"][row["member"]],row["sha256"])
                self.assertEqual(rows["native-synthetic.json"]["disposition"],"direct_and_archive")
                final=s.read(transport/"publication.json")
                self.assertEqual(final["status"],"FAIL_PUBLICATION"if fail_upload else
                  "PASS_COMPLETE_WIDTH_TOPOLOGY_EVIDENCE_PUBLICATION_ONLY")
                if fail_upload:self.assertIn("upload-original",final["error"]["error"])
                else:
                    self.assertTrue(any(n.endswith(".native-synthetic.json")for n,_,_ in captured))
                    self.assertTrue(any(n.endswith(".direct-publication-plan.json")for n,_,_ in captured))

if __name__=="__main__":
    assert os.environ.get("GITHUB_ACTIONS")=="true" and os.environ.get("RUNNER_ENVIRONMENT")=="github-hosted"
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Controls)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps(dict(status="PASS_WIDTH_STAGE_SOURCE_CONTROLS_ONLY"if result.wasSuccessful()else"FAIL_WIDTH_STAGE_SOURCE_CONTROLS",
      tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),
      native_execution=False,graph_equivalence_accepted=False,physical_accepted=False,electrical_accepted=False),sort_keys=True),flush=True)
    raise SystemExit(0 if result.wasSuccessful()else 1)
