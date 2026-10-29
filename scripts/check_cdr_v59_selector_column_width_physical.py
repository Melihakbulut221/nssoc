#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted controls for fresh candidate binding, original physical gates and cleanup."""
import copy, hashlib, json, os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import cdr_v59_selector_column_width_physical as s
import cloud_cdr_v59_selector_column_width_physical as d

class Controls(unittest.TestCase):
    def test_source_and_disabled_refusals(self):
        m=s.methods()
        self.assertGreaterEqual(len(m["protected_sha256"]),1002)
        for key in s.FALSE:
            bad=copy.deepcopy(m);bad[key]=True
            with self.assertRaises(AssertionError):s.validate_authorizations(bad)
        for key in s.NATIVE+s.FALSE+("source_controls_authorized",):
            bad=copy.deepcopy(m);bad[key]=1
            with self.assertRaises(AssertionError):s.validate_authorizations(bad)
        bad=copy.deepcopy(m);bad["native_execution_authorized"]=False
        with self.assertRaises(AssertionError):s.validate_authorizations(bad)
        bad=copy.deepcopy(m)
        for k in s.NATIVE:bad[k]=False
        s.validate_authorizations(bad)
        with self.assertRaises(AssertionError):s.execution_context(bad)
        with patch.dict(os.environ,{"GITHUB_RUN_ATTEMPT":"2"}):
            with self.assertRaises(AssertionError):s.execution_context(m)

    def test_live_producer_and_refusals(self):
        p=s.PREFIX
        objects=[s.read(s.ROOT/(p+key+".json"))for key in ("run","jobs","release","tag")]
        s.validate_live(*objects)
        mutations=[(0,"head_sha","0"*40),(0,"conclusion","failure"),(0,"run_attempt",2),
                   (0,"path","wrong.yml"),(1,"total_count",1),(2,"id",1),(2,"draft",True)]
        for index,key,value in mutations:
            changed=copy.deepcopy(objects);changed[index][key]=value
            with self.assertRaises((AssertionError,ValueError)):s.validate_live(*changed)
        changed=copy.deepcopy(objects);changed[1]["jobs"][0]["conclusion"]="failure"
        with self.assertRaises(AssertionError):s.validate_live(*changed)
        changed=copy.deepcopy(objects);changed[2]["assets"][0]["digest"]="sha256:"+"0"*64
        with self.assertRaises(AssertionError):s.validate_live(*changed)

    def test_complete_saved_inventory(self):
        e=s.expected_files()
        self.assertEqual(e["candidate/"+s.TOP+".gds"],s.GDS_SHA)
        self.assertEqual(e["result.json"],s.SUMMARY_SHA)
        self.assertEqual(len([n for n in e if n.startswith(s.inherited.VIEW+"/")]),605)
        self.assertGreater(len(e),3823)

    def test_physical_derivation_and_unchanged_gates(self):
        original=(s.ROOT/"hw/soc/flow/check_pcie_cdr_sampler_active_input_v57_parent.py").read_text()
        text,changes=s.physical.frozen.physical_source(original,"cd_shunt")
        self.assertEqual(len(changes),4)
        self.assertIn('if result["status"] != expected or result["category_count"] != 560:',text)
        self.assertIn('if len(result["circuits"]) != 1 or any(',text)
        self.assertIn('result["circuits"][0][key] != 500',text)
        self.assertIn('"no_simplify=true"',text)
        self.assertIn('"top_lvl_pins=true"',text)
        self.assertIn('"v59_old_length",',text)
        self.assertIn('assert dict(census)==EXPECTED_CENSUS',text)

    def test_layout_view_preserves_inputs_and_binds_new_gds(self):
        with tempfile.TemporaryDirectory()as temp:
            out=Path(temp);saved=out/s.VIEW;base=saved/s.inherited.VIEW/"parent/layout"
            base.mkdir(parents=True);(saved/"candidate").mkdir()
            ports={str(i):"(0,0;1,1)"for i in range(25)}
            s.atomic(base/"result.json",{"ports":ports,"old_metadata":"retained"})
            for n,value in [(s.TOP+".lef",b"LEF"),("schematic.cir",b"SCHEMATIC")]:
                (base/n).write_bytes(value)
            (saved/"candidate"/(s.TOP+".gds")).write_bytes(b"candidate")
            s.atomic(saved/"candidate/result.json",{"prior":"retained"})
            before={p:p.read_bytes()for p in saved.rglob("*")if p.is_file()}
            digest=s.sha(saved/"candidate"/(s.TOP+".gds"))
            with patch.object(s,"validate_view",return_value={}),patch.object(s,"GDS_SHA",digest):
                result=s.prepare_layout(out)
            self.assertEqual(result["ports"],ports)
            self.assertEqual(result["outputs"][s.TOP+".gds"],digest)
            self.assertEqual({p:p.read_bytes()for p in before},before)
            self.assertEqual((out/"layout/schematic.cir").read_bytes(),b"SCHEMATIC")
            self.assertEqual(len(result["inputs"]),5)
            self.assertFalse(result["physical_accepted"])
            derived=s.read(out/"derived-methods.json")
            self.assertEqual(len(derived["exact_reversible_changes"]),4)

    def physical_fixture(self,out,digest):
        (out/"layout").mkdir();(out/"physical").mkdir();(out/"methods").mkdir()
        (out/"layout"/(s.TOP+".gds")).write_bytes(b"fixture")
        (out/"methods/check_physical.py").write_text("fixture")
        s.atomic(out/"derived-methods.json",{"generated_sha256":s.sha(out/"methods/check_physical.py")})
        s.atomic(out/"runtime-source-manifest.json",{"files":{}})
        s.atomic(out/"layout/result.json",{"generated_candidate_sha256":digest})
        audit=dict(status="PASS within comparison scope",circuit_status_counts={"Match":1},
          extraction_diagnostics=[],circuits=[dict(layout_devices_recursive=500,schematic_devices_recursive=500)])
        steps={n:dict(status="REJECTED_EXPECTED_FAULT")for n in s.PHASES}
        steps["drc"]=dict(status="PASS",measurement=dict(status="PASS",category_count=560,markers=0))
        for n in ("lvs","lvs_flat"):
            steps[n]=dict(status="PASS",audit=copy.deepcopy(audit),
              native_primitive_census=dict(npn13g2=124,sg13_lv_nmos=50,rppd=98,cap_cmim=7,ptap1=221))
        return dict(status="PASS_NATIVE_PDK_CDR_PD500_DRC_LVS_AND_FAULT_CONTROLS",steps=steps,
          inputs={str(out/"layout"/(s.TOP+".gds")):digest},serial_phy_complete=False,
          main_chip_integrated=False,qualified_pex=False)

    def test_actual_candidate_validator_rejects_physical_faults(self):
        with tempfile.TemporaryDirectory()as temp:
            out=Path(temp);digest=hashlib.sha256(b"fixture").hexdigest()
            baseline=self.physical_fixture(out,digest)
            def run(record):
                s.atomic(out/"physical/result.json",record)
                return s.validate_candidate(out)
            with patch.object(s,"GDS_SHA",digest),patch.object(s,"validate_view",return_value={}),patch.object(s,"methods",return_value={}):
                positive=run(baseline)
                self.assertEqual(positive["expected_faults_rejected"],13)
                cases=[]
                for key,val in (("category_count",559),("markers",1),("status","FAIL")):
                    r=copy.deepcopy(baseline);r["steps"]["drc"]["measurement"][key]=val;cases.append(r)
                for mode in ("lvs","lvs_flat"):
                    r=copy.deepcopy(baseline);r["steps"][mode]["audit"]["circuits"][0]["layout_devices_recursive"]=499;cases.append(r)
                    r=copy.deepcopy(baseline);r["steps"][mode]["audit"]["extraction_diagnostics"]=["warning"];cases.append(r)
                    r=copy.deepcopy(baseline);r["steps"][mode]["native_primitive_census"]["rppd"]=97;cases.append(r)
                r=copy.deepcopy(baseline);r["steps"]["renamed_fault"]=r["steps"].pop("q_open");cases.append(r)
                r=copy.deepcopy(baseline);r["steps"]["offgrid"]["status"]="PASS";cases.append(r)
                for key in ("serial_phy_complete","main_chip_integrated","qualified_pex"):
                    r=copy.deepcopy(baseline);r[key]=True;cases.append(r)
                r=copy.deepcopy(baseline);r["inputs"][str(out/"layout"/(s.TOP+".gds"))]="0"*64;cases.append(r)
                for r in cases:
                    with self.assertRaises(AssertionError):run(r)
                (out/"layout"/(s.TOP+".gds")).write_bytes(b"changed")
                with self.assertRaises(AssertionError):run(baseline)
                self.assertEqual(len(cases),15)

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
            result={"status":"FAIL_ORIGINAL","native_physical_qualification_passed":False,
              "error":{"type":"ValueError","error":"original failure"}}
            with patch.object(d,"OUT",root),patch.object(s,"methods",return_value={"protected_sha256":{}}):
                errors=d.finish(result,Supervisor(),Heartbeat(),{})
            self.assertTrue(errors)
            self.assertEqual(calls,["cleanup","stop","join","sample"])
            self.assertEqual(result["error"]["error"],"original failure")
            self.assertFalse(result["native_physical_qualification_passed"])
            self.assertFalse(result["terminal_finalization_complete"])
            self.assertTrue((root/"result.json").is_file())

if __name__=="__main__":
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Controls)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps(dict(status="PASS_SOURCE_CONTROLS_ONLY"if result.wasSuccessful()else"FAIL_SOURCE_CONTROLS",
      tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),
      native_execution=False,physical_accepted=False,electrical_accepted=False),sort_keys=True),flush=True)
    raise SystemExit(0 if result.wasSuccessful()else 1)
