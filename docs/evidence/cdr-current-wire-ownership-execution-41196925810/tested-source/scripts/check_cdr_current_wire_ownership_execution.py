#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted adapter controls: real prior records and explicitly synthetic boundary fixtures."""
import copy,json,os,tempfile
from pathlib import Path
from unittest import mock
import cloud_cdr_current_wire_ownership as h
r=h.r
PROOF="docs/evidence/cdr-current-wire-ownership-controls-41195513564/source-records/"

def main():
    r.require(os.environ.get("GITHUB_ACTIONS")=="true","cloud controls only")
    actual_ctx=h.context(os.environ);h.source_guard(actual_ctx)
    rows=[]
    def record(name):
        assert name not in rows;rows.append(name)
        print(json.dumps(dict(completed_execution_control=name,index=len(rows),synthetic_inputs_only=True)),flush=True)
    def ok(name,fn):fn();record(name)
    def no(name,fn):
        try:fn()
        except(AssertionError,ValueError,KeyError,RuntimeError):record(name)
        else:raise AssertionError("accepted invalid execution fixture: "+name)
    def eq(a,b):assert a==b,(a,b)
    ok("owned manual context and distinct publication group",lambda:eq(actual_ctx["group"],"cdr-current-wire-ownership-nominal_early"))
    no("other branch refused",lambda:h.context(dict(os.environ,GITHUB_REF="refs/heads/main")))
    no("rerun attempt refused",lambda:h.context(dict(os.environ,GITHUB_RUN_ATTEMPT="2")))
    manifest=h.source_guard(actual_ctx)
    ok("only read-only actual analysis authorized",lambda:h.authorize(manifest))
    for name,edit in(
      ("disabled analysis refused",dict(native_analysis_authorized=False)),
      ("new simulator authority refused",dict(native_simulation_authorized=True)),
      ("geometry authority refused",dict(geometry_changes_authorized=True))):
        no(name,lambda edit=edit:h.authorize(dict(manifest,**edit)))
    # Authentic prior source records; only the new execution-control proof is synthetic.
    records={key:r.decode((h.ROOT/PROOF/file).read_bytes())for key,file in(
      ("controls","controls.json"),("publication","publication-controls.json"),("ownership","ownership-controls.json"))}
    old=records["ownership"];ctx=dict(actual_ctx,source=old["source"],run_id=old["run_id"])
    records["execution"]=dict(status="PASS_CURRENT_CDR_OWNERSHIP_EXECUTION_SOURCE_CONTROLS",
      count=h.HOST_CONTROLS,passed_cases=["synthetic"+str(i)for i in range(h.HOST_CONTROLS)],
      source=ctx["source"],run_id=ctx["run_id"],attempt=1,synthetic_inputs_only=True,
      actual_native_inputs_acquired=False,actual_model_analyzed=False,**h.analysis.FLAGS)
    ok("authentic prior groups with synthetic adapter proof accepted for exact source",lambda:h.bind_controls(ctx,records))
    missing=dict(records);del missing["execution"]
    no("missing control group refused",lambda:h.bind_controls(ctx,missing))
    mutations=[
      ("mismatched ownership source refused","ownership",dict(source="0"*40)),
      ("actual publication mutation claim refused","publication",dict(actual_release_mutated=True)),
      ("incomplete execution controls refused","execution",dict(count=h.HOST_CONTROLS-1)),
      ("false electrical acceptance refused","ownership",dict(electrical_accepted=True)),
      ("non-synthetic execution controls refused","execution",dict(synthetic_inputs_only=False))]
    for name,key,edit in mutations:
        changed=copy.deepcopy(records);changed[key].update(edit)
        no(name,lambda changed=changed:h.bind_controls(ctx,changed))
    c=r.source_guard();summary,parts,original=r.metadata(c,"nominal_early")
    pins=r.decode((h.ROOT/h.INPUTS).read_bytes());expected=summary["outputs"]
    ok("all actual34precise inputs plus2reports selected",lambda:eq(len(h.selected_inputs(pins,c,"nominal_early",expected)),36))
    wrong=copy.deepcopy(pins);wrong["precise_geometry_authority"]["anchors"]="native/current-mim-bundle/canonical-current-view/wire/anchors08.json"
    no("canonical anchor substitution refused",lambda:h.selected_inputs(wrong,c,"nominal_early",expected))
    wrong2=copy.deepcopy(pins);wrong2["members"]["native/current-mim-bundle/mim/composition/pd500-mim-wire.spice"]["sha256"]="0"*64
    no("changed final model pin refused",lambda:h.selected_inputs(wrong2,c,"nominal_early",expected))
    wrong3=dict(expected);wrong3.pop(next(iter(pins["members"])))
    no("missing actual archive member refused",lambda:h.selected_inputs(pins,c,"nominal_early",wrong3))
    wrong4=copy.deepcopy(c);wrong4["cases"]["constant_one"]["selected"]["native/current-mim-bundle/mim/composition/pd500-mim-wire.spice"]="0"*64
    no("different constant-one passive model refused",lambda:h.selected_inputs(pins,wrong4,"nominal_early",expected))
    def lifecycle(action_fail=False,integrity_fail=False,writer_fail=False):
        seen=[];primary=ValueError("actual-primary-fixture")
        report=dict(status="COMPLETE_CURRENT_CDR_WIRE_OWNERSHIP_DIAGNOSIS_ONLY",terminal_errors=[],**h.FLAGS)
        def action():
            seen.append("action")
            if action_fail:raise primary
        def integrity():
            seen.append("integrity")
            if integrity_fail:raise RuntimeError("integrity-fixture")
        def writer(value):
            seen.append("writer")
            if writer_fail:raise RuntimeError("writer-fixture")
        error=None
        try:h.terminal_body(action,integrity,writer,report)
        except BaseException as exc:error=exc
        eq(seen,["action","integrity","writer"])
        if action_fail:assert error is primary
        elif integrity_fail or writer_fail:assert error is not None
        else:assert error is None
        if action_fail or integrity_fail or writer_fail:assert report["status"]=="FAIL_CURRENT_CDR_WIRE_OWNERSHIP"
    ok("successful independent terminal evidence",lambda:lifecycle())
    ok("primary analysis failure preserved",lambda:lifecycle(action_fail=True))
    ok("integrity failure rejects otherwise successful analysis",lambda:lifecycle(integrity_fail=True))
    ok("terminal record failure rejects otherwise successful analysis",lambda:lifecycle(writer_fail=True))
    ok("primary retained across integrity failure",lambda:lifecycle(action_fail=True,integrity_fail=True))
    ok("primary retained across both finalization failures",lambda:lifecycle(action_fail=True,integrity_fail=True,writer_fail=True))
    def integrity_fixture(mutate=False,source_fail=False):
        with tempfile.TemporaryDirectory()as directory:
            bundle=Path(directory)/"bundle";saved=bundle/"native-inputs";evidence=bundle/"evidence"
            saved.mkdir(parents=True);evidence.mkdir();selected={}
            for i in range(36):
                name="fixture%02d.ext"%i;p=saved/name;p.write_text("SYNTHETIC INPUT "+str(i))
                selected[name]=r.file_pin(p)
            r.write_new(evidence/"complete-input-census.json",r.encode(dict(full_member_count=2797,every_member_authenticated=True,selected=selected)))
            if mutate:(saved/"fixture00.ext").write_text("MUTATED SYNTHETIC INPUT")
            with mock.patch.object(h,"source_guard",side_effect=RuntimeError("source-fixture")if source_fail else None,return_value={}):
                error=None
                try:h.final_integrity(actual_ctx,bundle,evidence)
                except AssertionError as exc:error=exc
            terminal=r.decode((evidence/"terminal-integrity.json").read_bytes())
            assert terminal["selected-inputs"]["complete"]is(not mutate)
            assert terminal["source"]["complete"]is(not source_fail)
            assert(error is not None)==(mutate or source_fail)
    ok("all selected input bytes rechecked at terminal",lambda:integrity_fixture())
    ok("changed selected input rejects terminal",lambda:integrity_fixture(mutate=True))
    ok("source failure does not suppress selected input verification",lambda:integrity_fixture(source_fail=True))
    def publication_fixture():
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);bundle=root/"bundle";bundle.mkdir()
            (bundle/"evidence.json").write_text('{"synthetic_only":true}\n')
            (bundle/"empty.stderr").write_bytes(b"")
            (bundle/"fixture.ext").write_text("SYNTHETIC NATIVE BOUNDARY; NOT A REAL MODEL")
            paths,index=h.prepare_publication(actual_ctx,bundle,root/"publication")
            receipt=r.decode(paths[0].read_bytes())
            eq(receipt["schema"],"complete-current-cdr-wire-ownership-output-index-v1")
            assert receipt["actual_capture_replayed"]is False and "original_capture_replayed_is_not_electrical_acceptance"not in receipt
            eq(receipt["files"],h.publisher.inventory(bundle));assert receipt["files"]["empty.stderr"]["bytes"]==0
            assert len(paths)>=3 and index["complete_empty_streams_preserved"]is True
    ok("actual qualified packing with ownership metadata and empty files",publication_fixture)
    assert len(rows)==29 and len(set(rows))==29
    report=dict(status="PASS_CURRENT_CDR_OWNERSHIP_EXECUTION_SOURCE_CONTROLS",count=29,passed_cases=rows,
      source=actual_ctx["source"],run_id=actual_ctx["run_id"],attempt=1,synthetic_inputs_only=True,
      actual_native_inputs_acquired=False,actual_model_analyzed=False,**h.analysis.FLAGS)
    r.write_new(Path(os.environ.get("CDR_OWNERSHIP_CONTROLS_OUTPUT","cdr-drain-wave-source-controls/execution-controls.json")),r.encode(report))
    print(json.dumps(report,sort_keys=True))
if __name__=="__main__":main()
