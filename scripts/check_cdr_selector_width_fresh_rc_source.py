#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted-only current75 admission/adapter controls; no native payload acquisition.

Real source validators, metadata, restore function code, copies and stage APIs.
Archive fetch/extraction/native payload hashes and sizes are explicit test doubles.
These controls do not qualify archive restoration, native geometry or numerical RC.
"""
import argparse
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import traceback
import types
import unittest
from contextlib import ExitStack,contextmanager
from unittest.mock import patch
import cdr_selector_width_fresh_rc_admission as s
import cdr_selector_width_fresh_rc_legacy as a

ROOT=Path(__file__).resolve().parents[1]
REVIEW="docs/evidence/cdr-selector-width-fresh-rc-disabled-source-20261029.json"
EXPECTED_CHANGED=("validate_summary","verify_saved_inputs","restore_for_binding",
 "assert_current_candidate_ready","restore_for_rc")
REPORTS=[]


def require(value,message):
    if not value:raise AssertionError(message)


def record(label,**fields):
    REPORTS.append(dict(case=label,**fields))


def reject(label,action,reason,kind=AssertionError):
    try:action()
    except kind as error:
        require(error.args==(reason,),(label,"wrong refusal",error.args,reason))
        record(label,refused=True,reason=reason)
        return error
    raise AssertionError((label,"accepted invalid input"))


def put(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if isinstance(value,bytes):path.write_bytes(value)
    else:s.write(path,value)


def worker_derivations(overrides=None):
    overrides=overrides or {};audit=json.loads((ROOT/REVIEW).read_bytes());rows=[]
    before=b"cdr_v59_tail_fresh_rc_legacy";after=b"cdr_selector_width_fresh_rc_legacy"
    for row in audit["worker_derivations"]:
        old=(ROOT/row["source"]).read_bytes()
        new=overrides.get(row["target"],(ROOT/row["target"]).read_bytes())
        require(hashlib.sha256(old).hexdigest()==row["source_sha256"],"Frozen worker changed")
        require(old.count(before)==row["replacements"] and before not in new,
          "Wrong worker import count")
        require(old.replace(before,after)==new and new.replace(after,before)==old,
          "Exact numerical worker derivation changed")
        ot=ast.parse(old);nt=ast.parse(new)
        od={x.name:x for x in ot.body if isinstance(x,(ast.FunctionDef,ast.ClassDef))}
        nd={x.name:x for x in nt.body if isinstance(x,(ast.FunctionDef,ast.ClassDef))}
        require(set(od)==set(nd)and all(ast.dump(od[n],include_attributes=False)==
          ast.dump(nd[n],include_attributes=False)for n in od),"Numerical function AST changed")
        rows.append(dict(path=row["target"],sha256=hashlib.sha256(new).hexdigest(),
          full_byte_reverse=True,unchanged_function_count=len(od)))
    old=(ROOT/"scripts/cdr_v59_tail_fresh_rc_legacy.py").read_text()
    new=Path(a.__file__).read_text()
    defs=lambda text:{x.name:x for x in ast.parse(text).body if isinstance(x,ast.FunctionDef)}
    od,nd=defs(old),defs(new)
    changed=tuple(n for n in nd if ast.dump(od[n],include_attributes=False)!=
      ast.dump(nd[n],include_attributes=False))
    require(changed==EXPECTED_CHANGED and len(nd)-len(changed)==18,
      "Unapproved inherited adapter function change")
    return rows


class SyntheticNativeIO:
    """Tiny explicit payloads. Authentic hashes are a synthetic I/O seam only."""
    def __init__(self,base,data,saved,mode):
        self.base=base;self.data=data;self.saved=saved;self.mode=mode
        self.full=saved["complete_graph_files"];self.current=saved["current_files"]
        self.payloads={};self.hashes={};self.calls=[];self.clones=[]
        self.failure=RuntimeError("injected primary archive transport failure")
        self.real_sha=s.sha;self.real_regular=s.graph_restore.regular
        self.method=s.methods();self.g=s.evidence.graph
        for name,h in self.full.items():
            raw=("EXPLICIT SYNTHETIC NATIVE PAYLOAD "+name+"\n").encode()
            self.payloads[name]=raw;self.hashes[raw]=h
        for name,path in self.g.REPORT_PATHS.items():
            raw=(ROOT/(self.g.PREFIX+name+".json")).read_bytes()
            require(hashlib.sha256(raw).hexdigest()==self.full[path],"Authentic report fixture hash changed")
            self.payloads[path]=raw
        for name in ("probe01.py","locate01.py","anchors01.py","dedup01.py"):
            raw=(ROOT/("docs/evidence/cdr-v59-tail-exact-wire-methods-20261026/"+name)).read_bytes()
            require(hashlib.sha256(raw).hexdigest()==self.current["wire/"+name],
              "Actual copied original wire method changed")
            self.payloads["candidate/wire/"+name]=raw
        self.parts={row["name"]:row for row in data["graph"]["parts"]["parts"]}
        for name,row in self.parts.items():
            raw=("SYNTHETIC ARCHIVE PART NOT A NATIVE ARCHIVE "+name+"\n").encode()
            self.hashes[raw]=row["sha256"]

    def sha(self,path):
        p=Path(path)
        if p.is_relative_to(self.base)or p.is_relative_to(s.ANALYSIS):
            raw=p.read_bytes()
            if raw in self.hashes:return self.hashes[raw]
        return self.real_sha(p)

    def fetch(self,url,digest,path):
        path=Path(path);self.calls.append(dict(action="fetch",url=url,sha256=digest,name=path.name))
        stem=self.data["graph"]["parts"]["stem"]+"."
        if path.name in ("summary.json","parts.json"):
            raw=(ROOT/(self.g.PREFIX+path.name)).read_bytes()
            require(url.endswith(stem+path.name)and hashlib.sha256(raw).hexdigest()==digest,
              "Wrong actual report transport request")
        else:
            require(path.name in self.parts and digest==self.parts[path.name]["sha256"],
              "Wrong exact archive-part transport request")
            raw=("SYNTHETIC ARCHIVE PART NOT A NATIVE ARCHIVE "+path.name+"\n").encode()
            if self.mode=="transport":
                path.write_bytes(raw+b"partial transport")
                raise self.failure
        path.write_bytes(raw)

    def regular(self,root,name):
        p=self.real_regular(root,name)
        if p.name not in self.parts:return p
        size=self.parts[p.name]["bytes"]
        class ExplicitSyntheticSize:
            def __fspath__(self):return str(p)
            def stat(self):return types.SimpleNamespace(st_size=size)
            def unlink(self):p.unlink()
        return ExplicitSyntheticSize()

    def extract(self,manifest,transport,destination,expected):
        require(manifest==self.data["graph"]["parts"]and expected==self.full,
          "Actual restore requested wrong complete4103 transport")
        require(not destination.exists(),"Synthetic extraction destination exists")
        self.calls.append(dict(action="synthetic_exact_extract",members=len(expected)))
        for name,raw in self.payloads.items():put(destination/name,raw)
        if self.mode=="missing":(destination/"candidate/wire/device-locations01.json").unlink()
        elif self.mode=="root_result":put(destination/"candidate/result.json",b"not an admitted member")
        return dict(regular_members=4103,synthetic_payload_IO=True,
          actual_archive_or_native_geometry_verified=False)

    def view(self,root):
        # The native restored-file parser is an explicit boundary. Actual metadata
        # validators run outside it; every real fixture file and direct report is checked.
        root=Path(root);table=self.g.tree(root)
        require({n:r["sha256"]for n,r in table.items()}==self.full,
          "Synthetic complete4103 file inventory changed")
        for name,path in self.g.REPORT_PATHS.items():
            require((root/path).read_bytes()==(ROOT/(self.g.PREFIX+name+".json")).read_bytes(),
              "Authentic direct report fixture changed")
        require(not(root/"candidate/result.json").exists(),"Synthetic current root result invented")
        return dict(synthetic_payload_IO=True,complete_member_count=4103,
          all_fixture_files_and_original_report_bytes_checked=True,
          native_restored_report_parser_executed=False,actual_native_restoration_qualified=False)

    def api(self,endpoint):
        top=self.data["topology"];graph=self.data["graph"]
        rows={
          "actions/runs/"+str(s.evidence.RUN):top["run.json"],
          "actions/runs/"+str(s.evidence.RUN)+"/attempts/1/jobs?per_page=100":top["jobs.json"],
          "releases/"+str(s.evidence.RELEASE):top["release.json"],
          "git/ref/tags/"+s.evidence.TAG:top["tag.json"],
          "actions/runs/"+str(self.g.RUN):graph["run"],
          "actions/runs/"+str(self.g.RUN)+"/attempts/1/jobs?per_page=100":graph["jobs"],
          "releases/"+str(self.g.RELEASE):graph["release"],
          "releases/tags/"+self.g.TAG:graph["release"],
          "git/ref/tags/"+self.g.TAG:graph["tag"]}
        require(endpoint in rows,"Unexpected cloud API request")
        self.calls.append(dict(action="saved_metadata_api",endpoint=endpoint))
        return copy.deepcopy(rows[endpoint])

    def function(self,code,namespace,name,defaults,closure):
        original=s.graph_restore.restore
        require(code is original.__code__ and defaults is original.__defaults__
          and closure is original.__closure__ and name==original.__name__,"Restore code identity changed")
        changed={key for key in set(namespace)|set(original.__globals__)
          if namespace.get(key)is not original.__globals__.get(key)}
        require(changed=={"authorize"}and namespace["authorize"]is s.authorize,
          "Restore clone changed a non-authority global")
        self.clones.append(dict(code_identity=True,changed_globals=sorted(changed)))
        return types.FunctionType(code,namespace,name,defaults,closure)


@contextmanager
def fixture(data,saved,mode="complete"):
    # This exact original producer path must remain unchanged in report bytes.
    canonical=Path(saved["canonical_analysis_path"])
    require(s.ANALYSIS==canonical and not canonical.exists()and not canonical.is_symlink(),
      "Source fixture canonical path already occupied")
    with tempfile.TemporaryDirectory(prefix="width-rc-source-fixture-")as temp,ExitStack()as stack:
        base=Path(temp).resolve();out=base/"out";io=SyntheticNativeIO(base,data,saved,mode)
        values={"OUT":out,"RESTORE":out/"restore","CAPSULE":out/"restore/graph-input",
          "PIN":out/"restore/joint-admission.json","ANALYSIS":canonical,
          "BINDING":out/"binding","RC_STAGE":out/"wire-stage","MIM_OUT":out/"mim",
          "HANDOFF":out/"mim/inputs/fresh-stage-manifest.json"}
        stack.enter_context(patch.object(s,"OUT",out))
        for name,value in values.items():stack.enter_context(patch.object(a,name,value))
        stack.enter_context(patch.object(s,"methods",return_value=io.method))
        stack.enter_context(patch.object(s.evidence,"source_guard",return_value=data))
        stack.enter_context(patch.object(s.graph_restore.evidence,"source_guard",return_value=data["graph"]))
        stack.enter_context(patch.object(s.evidence.graph,"validate_restored",side_effect=io.view))
        stack.enter_context(patch.object(s.release,"api",side_effect=io.api))
        stack.enter_context(patch.object(s.graph_restore,"fetch",side_effect=io.fetch))
        stack.enter_context(patch.object(s.graph_restore.extraction,"exact_extract",side_effect=io.extract))
        stack.enter_context(patch.object(s.graph_restore,"regular",side_effect=io.regular))
        for module in (s,a,s.graph_restore,s.evidence.graph):
            stack.enter_context(patch.object(module,"sha",side_effect=io.sha))
        stack.enter_context(patch.object(s,"types",types.SimpleNamespace(FunctionType=io.function)))
        stack.enter_context(patch.object(s,"authorize",side_effect=lambda:io.calls.append(dict(action="synthetic_authority_boundary"))))
        try:yield io,values
        finally:
            # The path was absent on entry and only this sequential fixture creates it.
            if canonical.exists():shutil.rmtree(canonical)


def install_stage_reports(io):
    """Explicit synthetic numerical outputs exercise actual unchanged stage validators."""
    for root in (a.BINDING,a.RC_STAGE):root.mkdir(parents=True,exist_ok=True)
    put(a.BINDING/"empty",b"");put(a.BINDING/".hidden",b"retain complete binding")
    put(a.RC_STAGE/"empty",b"")
    put(a.ANALYSIS/"wire/fresh-rc.spice",b"* SYNTHETIC, NO RC EXTRACTION\nR1 a b 1\nC1 a b 2e-15\n")
    devices=[dict(native_id=i,native_model="rppd",model="rppd",native_parameters={},parameters={})for i in range(1,501)]
    for ident in a.numerical.TARGETS:
        devices[ident-1].update(native_parameters=dict(w="4",l="5",ps="0",b="0",m="1"),parameters=dict(w="4u",l="5u"))
    bound=dict(devices=devices,census=a.numerical.CENSUS,native_ports=["p"+str(i)for i in range(25)],
      node_map={str(i):str(i)for i in range(114)})
    put(a.BINDING/"binding.json",bound)
    pin=s.read_json(a.PIN);integrity=a.verify_saved_inputs(pin)
    common=dict(source_head=os.environ["GITHUB_SHA"],sources_unchanged=True,qualified_pex=False,
      full_phy_accepted=False,closed_loop=False,saved_capsule_integrity=integrity)
    binding=dict(common,status=a.PASS["binding"],binding=bound,controls=[dict(rejected=True)for _ in range(14)],
      target_length_controls=dict(actual_fresh_binding=True,rejected=list(range(6))),
      native_contact_comparisons=[dict(explicitly_synthetic=True)for _ in range(221)],
      contact_model_controls=dict(rejected_geometry=list(range(3)),rejected_compact_models=list(range(3))),
      native_simulation_passed=False,wire_rc_included=False)
    rc=dict(common,status=a.PASS["rc"],geometry=s.read_json(a.ANALYSIS/"wire/native05/result.json"),
      anchors=s.read_json(a.ANALYSIS/"wire/anchors08.json"),
      capture=dict(returncode=0,status="NATIVE_COMPLETE_AWAITING_RC_AUDIT"),
      audit=dict(status="PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY",original_devices=500,geometry_probes=978,
        physical_wire_components=113,actual_exported_resistors=1,actual_exported_capacitors=1),
      controls=dict(status="PASS_REAL_NATIVE_BASELINE_AND13_RAW_CORRUPTION_CONTROLS",cases=[dict(rejected=True)for _ in range(13)]),
      new_current_view_outputs=a.new_current_outputs(pin),terminal_output_inventory_complete=True,terminal_output_errors=[])
    for root,report in ((a.BINDING,binding),(a.RC_STAGE,rc)):
        report["outputs"]=a.inventory(root);put(root/"result.json",report)
    return binding,rc


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.method=s.methods();cls.data=s.evidence.source_guard();cls.saved=s.evidence.validate_saved()
        require(len(cls.saved["complete_graph_files"])==4103 and len(cls.saved["current_files"])==75,
          "Incomplete authentic current graph metadata")

    def test_authorizations_and_real_source_integrity(self):
        self.assertFalse(self.method["controller_readiness"])
        self.assertTrue(all(self.method[n]is False for n in s.NATIVE_FLAGS+s.FALSE))
        for enabled in (False,True):
            m=copy.deepcopy(self.method)
            for key in s.NATIVE_FLAGS:m[key]=enabled
            m["source_controls_authorized"]=m["controller_readiness"]=enabled
            s.validate_authorizations(m)
            bad=copy.deepcopy(m);bad[s.NATIVE_FLAGS[0]]=not enabled
            reject("split_native_"+str(enabled),lambda:s.validate_authorizations(bad),"Split fresh width RC authorization")
        for key in s.NATIVE_FLAGS+s.FALSE+("source_controls_authorized","controller_readiness"):
            m=copy.deepcopy(self.method);m[key]=1
            reject("typed_"+key,lambda:s.validate_authorizations(m),"Nonboolean fresh width RC authorization")
        reject("disabled_actual_authorize",s.authorize,"Fresh width RC is disabled")
        target=ROOT/"scripts/cdr_selector_width_fresh_rc_admission.py";real=s.sha
        with patch.object(s,"sha",side_effect=lambda p:"0"*64 if Path(p)==target else real(p)):
            reject("real_source_digest",s.methods,"Changed fresh width RC source: scripts/cdr_selector_width_fresh_rc_admission.py")
        record("actual_source_guard",positive=True,protected=len(self.method["protected_sha256"]))

    def test_exact_numerical_derivations(self):
        rows=worker_derivations();self.assertEqual(len(rows),5)
        mutations={
          "binding":(b"len(ports)==len(set(ports))==25",b"len(ports)==len(set(ports))==24"),
          "wire_rc":(b"original_devices=500",b"original_devices=499"),
          "mim_capture":(b"L.dbu==.001",b"L.dbu==.002"),
          "mim_audit":(b"len(r['wire_controls']['cases'])==13",b"len(r['wire_controls']['cases'])==12"),
          "mim_precision":(b"for variant in ('precise','precise_reversed'):",b"for variant in ('precise',):")}
        for row in rows:
            path=row["path"];original=(ROOT/path).read_bytes()
            stage=Path(path).stem.removeprefix("cloud_cdr_selector_width_fresh_")
            before,after=mutations[stage]
            require(original.count(before)==1,"Numerical mutation is not a unique real predicate")
            reject("numerical_mutation_"+stage,
              lambda:worker_derivations({path:original.replace(before,after)}),
              "Exact numerical worker derivation changed")
        record("five_exact_workers_and_eighteen_unchanged_adapter_functions",positive=True,workers=rows)

    def test_complete_restore_and_absolute_projection(self):
        with fixture(self.data,self.saved)as(io,paths):
            pin=s.restore()
            self.assertEqual(io.clones,[dict(code_identity=True,changed_globals=["authorize"])])
            self.assertEqual(sum(c["action"]=="synthetic_authority_boundary"for c in io.calls),2)
            self.assertEqual(sum(c["action"]=="fetch"for c in io.calls),4)
            self.assertEqual(a.inventory(a.ANALYSIS),self.saved["current_files"])
            self.assertFalse((a.ANALYSIS/"result.json").exists())
            self.assertEqual(a.ANALYSIS,Path(self.saved["canonical_analysis_path"]))
            self.assertEqual(s.read_json(a.PIN),pin)
            for original,h in s.read_json(a.ANALYSIS/"wire/anchors08.json")["inputs"].items():
                self.assertEqual(io.sha(Path(original)),h)
            self.assertEqual(s.qualify_saved(a.CAPSULE,s.contract()),pin)
            self.assertEqual({p.name for p in(a.RESTORE/"input-transport").iterdir()},
              {"summary.json","parts.json"})
            record("actual_clone_full4103_current75_projection",positive=True,original_absolute_path_preserved=True,
              absent_current_root_result=True,synthetic_native_IO=True,clones=io.clones)

    def test_primary_transport_failure_and_partial_bytes(self):
        with fixture(self.data,self.saved,"transport")as(io,paths):
            try:s.restore()
            except RuntimeError as error:self.assertIs(error,io.failure)
            else:self.fail("Accepted transport failure")
            self.assertEqual(len(io.clones),1)
            transport=a.RESTORE/"input-transport"
            self.assertTrue((transport/"summary.json").is_file()and(transport/"parts.json").is_file())
            partial=transport/next(iter(io.parts))
            self.assertTrue(partial.read_bytes().endswith(b"partial transport"))
            self.assertFalse(a.ANALYSIS.exists());self.assertFalse(a.PIN.exists())
            record("actual_clone_primary_transport_failure",refused=True,exact_exception_identity=True,
              partial_synthetic_transport_preserved=True)

    def test_source_refusal_precedes_any_transport(self):
        real=s.sha;target=ROOT/"scripts/cdr_selector_width_fresh_rc_admission.py";calls=[]
        with patch.object(s,"sha",side_effect=lambda p:"0"*64 if Path(p)==target else real(p)),\
          patch.object(s.release,"api",side_effect=lambda *args:calls.append(args)):
            reject("source_refusal_before_transport",s.restore,
              "Changed fresh width RC source: scripts/cdr_selector_width_fresh_rc_admission.py")
        self.assertEqual(calls,[])

    def test_complete_inventory_and_projection_refusals(self):
        for mode in ("missing","root_result"):
            with fixture(self.data,self.saved,mode)as(io,paths):
                reject("restore_"+mode,s.restore,"Synthetic complete4103 file inventory changed")
                self.assertFalse(a.ANALYSIS.exists());self.assertFalse(a.PIN.exists())
                self.assertEqual(len(io.clones),1)
        with fixture(self.data,self.saved)as(io,paths):
            a.ANALYSIS.mkdir(parents=True);put(a.ANALYSIS/"owned-test-marker",b"preexisting")
            reject("occupied_canonical_projection",s.restore,"Canonical analysis path occupied")
            self.assertEqual((a.ANALYSIS/"owned-test-marker").read_bytes(),b"preexisting")
            self.assertTrue(a.PIN.exists())

    def test_actual_binding_and_RC_adapters(self):
        with fixture(self.data,self.saved)as(io,paths):
            pin=s.restore();a.BINDING.mkdir();a.RC_STAGE.mkdir()
            selected=list(s.evidence.BINDING_FILES)
            prior,proof=a.restore_for_binding(pin,selected,a.BINDING)
            self.assertEqual(a.inventory(a.BINDING/"inputs"),self.saved["current_binding_files"])
            self.assertEqual(prior["outputs"],self.saved["current_files"])
            self.assertFalse(proof["current_root_result_fabricated"])
            graph,rcproof=a.restore_for_rc(pin,a.RC_STAGE)
            self.assertEqual(graph["strict_wire_graph"],self.data["graph"]["graph"])
            self.assertEqual(graph["anchors"],self.data["graph"]["anchors"])
            self.assertEqual(rcproof["current_candidate_files"],75)
            reject("binding_wrong_order",lambda:a.restore_for_binding(pin,list(reversed(selected)),a.BINDING),
              "Fresh width binding selection changed")
            reject("binding_wrong_destination",lambda:a.restore_for_binding(pin,selected,a.OUT/"wrong"),
              "Wrong fresh width binding output")
            reject("rc_wrong_destination",lambda:a.restore_for_rc(pin,a.OUT/"wrong"),"Wrong fresh width wire RC stage")
            extra=a.ANALYSIS/"result.json";put(extra,b"not admitted")
            reject("rc_invented_root_result",lambda:a.restore_for_rc(pin,a.RC_STAGE),"Complete numerical inventory changed")
            extra.unlink()
            target=a.ANALYSIS/"wire/device-locations01.json";raw=target.read_bytes();target.write_bytes(raw+b"changed")
            reject("binding_changed_current_input",lambda:a.verify_saved_inputs(pin),
              "Numerical input digest changed: wire/device-locations01.json")
            target.write_bytes(raw)
            a.assert_current_candidate_ready()
            record("actual_six_binding_and_RC_adapters",positive=True,complete_current=75,anchor_paths=9,synthetic_native_IO=True)

    def test_actual_stage_handoff_and_both_order_projection(self):
        with fixture(self.data,self.saved)as(io,paths):
            pin=s.restore();a.BINDING.mkdir();a.RC_STAGE.mkdir()
            a.restore_for_binding(pin,list(s.evidence.BINDING_FILES),a.BINDING)
            binding,rc=install_stage_reports(io)
            self.assertEqual(a.stage_report("binding"),binding);self.assertEqual(a.stage_report("rc"),rc)
            a.MIM_OUT.mkdir();h=a.restore_inputs()
            self.assertEqual(len(h["complete_current_view_files"]),76)
            self.assertEqual(h["binding"]["run"],int(os.environ["GITHUB_RUN_ID"]))
            self.assertFalse(h["historical763_1136_1127_counts_reused"])
            for order in ("precise","precise_reversed"):
                out=a.MIM_OUT/order;out.mkdir()
                prior,proof,bound,bproof,projection=a.project_for_capture(out)
                self.assertEqual(prior,rc);self.assertEqual(bound,binding);self.assertEqual(projection,binding["binding"])
                self.assertEqual(proof["summary_sha256"],h["rc"]["summary_sha256"])
                self.assertEqual(a.inventory(out/"source"),h["complete_current_view_files"])
                self.assertEqual((out/"model-binding/empty").read_bytes(),b"")
                self.assertEqual((out/"model-binding/.hidden").read_bytes(),b"retain complete binding")
                a.verify_projection(out)
            bad=copy.deepcopy(h);bad["run"]+=1;put(a.HANDOFF,bad)
            reject("handoff_wrong_run",a.verify_restored,"Fresh handoff source/run mismatch");put(a.HANDOFF,h)
            bad=copy.deepcopy(h);bad["source_head"]="0"*40;put(a.HANDOFF,bad)
            reject("handoff_wrong_source",a.verify_restored,"Fresh handoff source/run mismatch");put(a.HANDOFF,h)
            bad=copy.deepcopy(h);bad["historical763_1136_1127_counts_reused"]=True;put(a.HANDOFF,bad)
            reject("handoff_borrowed_identity",a.verify_restored,"Historical bundle relabelled");put(a.HANDOFF,h)
            reject("repeat_handoff",a.restore_inputs,"Fresh MIM handoff already exists or root missing")
            reject("wrong_native_order",lambda:a.project_for_capture(a.MIM_OUT/"unknown"),"Wrong fresh native order")
            out=a.MIM_OUT/"precise";target=out/"source/wire/fresh-rc.spice";raw=target.read_bytes();target.write_bytes(raw+b"changed")
            reject("projected_RC_changed",lambda:a.verify_projection(out),"Numerical input digest changed: wire/fresh-rc.spice")
            target.write_bytes(raw)
            target=out/"model-binding/empty";target.unlink();target.symlink_to(out/"model-binding/.hidden")
            reject("projected_symlink",lambda:a.verify_projection(out),"Nonregular evidence member")
            target.unlink();target.write_bytes(b"")
            bad=copy.deepcopy(rc);bad["audit"]["actual_exported_resistors"]=True;put(a.RC_STAGE/"result.json",bad)
            reject("typed_RC_count",lambda:a.stage_report("rc"),"Fresh actual R/C counts invalid")
            put(a.RC_STAGE/"result.json",rc)
            bad=copy.deepcopy(binding);bad["controls"][0]["rejected"]=False;put(a.BINDING/"result.json",bad)
            reject("binding_fault_control_missing",lambda:a.stage_report("binding"),"Fresh14 binding faults changed")
            put(a.BINDING/"result.json",binding)
            a.verify_restored()
            record("actual_current76_full_stage_and_both_order_handoff",positive=True,
              synthetic_numerical_reports_not_RC_qualification=True,orders=2)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",required=True);args=parser.parse_args()
    require(os.environ.get("GITHUB_ACTIONS")=="true"and os.environ.get("RUNNER_ENVIRONMENT")=="github-hosted"
      and os.environ.get("GITHUB_REPOSITORY")=="Melihakbulut221/nssoc"
      and os.environ.get("GITHUB_EVENT_NAME")=="workflow_dispatch"
      and os.environ.get("GITHUB_RUN_ATTEMPT")=="1","First hosted repository source controls only")
    result=dict(status="RUNNING",source_head=os.environ["GITHUB_SHA"],run_id=int(os.environ["GITHUB_RUN_ID"]),
      run_attempt=1,native_execution=False,native_payload_acquired=False,archive_downloaded=False,
      real_archive_restoration_qualified=False,numerical_RC_executed=False,controller_readiness=False,
      physical_accepted=False,electrical_accepted=False,qualified_pex=False,full_phy_accepted=False)
    output=Path(args.output);require(not output.exists()and not output.is_symlink(),"Control output already exists")
    s.write(output,result)
    try:
        test=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Controls))
        result.update(tests=test.testsRun,failures=len(test.failures),errors=len(test.errors),records=REPORTS,
          method_sha256=s.sha(s.METHOD),positive_records=sum(r.get("positive")is True for r in REPORTS),
          refusal_records=sum(r.get("refused")is True for r in REPORTS))
        require(test.wasSuccessful(),"Fresh width RC source controls failed")
        require(test.testsRun==8,"Incomplete source test suite")
        result["status"]="PASS_FRESH_WIDTH_RC_ADMISSION_ADAPTER_SOURCE_CONTROLS_ONLY"
    except BaseException as error:
        result.update(status="FAIL_FRESH_WIDTH_RC_SOURCE_CONTROLS",error=repr(error),traceback=traceback.format_exc(),records=REPORTS)
        raise
    finally:s.write(output,result)

if __name__=="__main__":main()
