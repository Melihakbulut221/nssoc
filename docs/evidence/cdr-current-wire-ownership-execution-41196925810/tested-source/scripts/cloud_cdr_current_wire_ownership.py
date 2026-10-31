#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read-only current CDR ownership diagnosis on hosted runners, preserving all input/output bytes."""
import argparse,hashlib,json,os,shutil,subprocess,sys,traceback
from pathlib import Path
import cloud_cdr_drain_m1_wave_replay as r
import publish_cdr_drain_wave_replay as publisher
import analyze_cdr_current_wire_ownership as analysis
ROOT=Path(__file__).resolve().parents[1]
MANIFEST="scripts/cdr-current-wire-ownership-execution-pins.json"
INPUTS="scripts/cdr-current-wire-ownership-inputs.json"
GROUP="cdr-current-wire-ownership-nominal_early"
HOST_CONTROLS=29
FLAGS=dict(analysis.FLAGS,actual_capture_replayed=False,new_simulation=False,native_CAD_executed=False)

def context(env):
    value=r.context(env,"nominal_early");value["group"]=GROUP
    value["tag"]="cloud-results-"+value["token"]+"-"+GROUP
    return value
def publication_context(ctx):
    return dict(source=ctx["source"],run=ctx["run_id"],attempt=1,case=ctx["case"],group=ctx["group"],tag=ctx["tag"])

def source_guard(ctx,root=ROOT):
    r.source_guard(root);publisher.source_guard(publication_context(ctx),root)
    r.require(subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip()==ctx["source"],"exact ownership checkout")
    raw=r.regular(root,MANIFEST).read_bytes()
    r.require(raw==subprocess.check_output(["git","show",ctx["source"]+":"+MANIFEST],cwd=root),"execution manifest unchanged")
    manifest=r.decode(raw)
    r.require(manifest["schema"]=="cdr-current-wire-ownership-execution-pins-v1","execution manifest schema")
    r.require(manifest["source_controls_authorized"]is True,"source controls authorization")
    for name,pin in manifest["files"].items():r.require(r.file_pin(r.regular(root,name))==pin,"ownership source changed: "+name)
    r.require(all(manifest[k]is False for k in analysis.FLAGS),"all final/causal flags remain false")
    return manifest

def authorize(manifest):
    r.require(manifest["native_acquisition_authorized"]is True and manifest["native_analysis_authorized"]is True,"read-only actual analysis enabled")
    r.require(manifest["native_simulation_authorized"]is False and manifest["geometry_changes_authorized"]is False,"no simulation or geometry authority")
    return dict(read_only_current_model_analysis=True,**FLAGS)

def bind_controls(ctx,records):
    r.require(set(records)=={"controls","publication","ownership","execution"},"all same-source control groups")
    r.controls_binding(r.encode(records["controls"]),ctx)
    pub=records["publication"]
    r.require(pub["status"]=="PASS_COMPLETE_REPLAY_PUBLICATION_CONTROLS"and pub["passed"]is True
      and pub["counts"]==dict(positive=7,refusals=33,lifecycle=4),"original publication controls")
    r.require(pub["current_context"]["source"]==ctx["source"]and pub["current_context"]["run"]==ctx["run_id"]
      and pub["current_context"]["attempt"]==1 and pub["synthetic_inputs_only"]is True,"same-source publication controls")
    for group,status,count in(("ownership","PASS_CURRENT_CDR_WIRE_OWNERSHIP_SOURCE_CONTROLS",33),
      ("execution","PASS_CURRENT_CDR_OWNERSHIP_EXECUTION_SOURCE_CONTROLS",HOST_CONTROLS)):
        value=records[group]
        r.require(value["status"]==status and value["count"]==count and len(set(value["passed_cases"]))==count,"complete "+group+" controls")
        r.require(value["source"]==ctx["source"]and value["run_id"]==ctx["run_id"]and value["attempt"]==1,"same-source "+group)
        r.require(value["synthetic_inputs_only"]is True and value["actual_native_inputs_acquired"]is False
          and value["actual_model_analyzed"]is False,"synthetic-only "+group)
        r.require(all(value[k]is False for k in analysis.FLAGS),"no "+group+" acceptance")
    r.require(all(pub[k]is False for k in("actual_native_capture_acquired","actual_release_mutated","physical_acceptance","timing_accepted","full_phy_accepted")),"publication control scope")
    return {name:r.fingerprint(r.encode(value))for name,value in records.items()}

def selected_inputs(input_pins,c,case,expected):
    r.require(input_pins["schema"]=="current-cdr-wire-ownership-inputs-v1"and input_pins["selected_member_count"]==34,"current34 input pins")
    members=input_pins["members"]
    r.require(len(members)==34 and all(expected[name]==pin["sha256"]for name,pin in members.items()),"actual source member hash join")
    authority=input_pins["precise_geometry_authority"]
    r.require(authority["explicit_source_prefix"]==analysis.PRECISE_PREFIX and authority["canonical_anchor_not_substitutable"]is True,"actual precise geometry authority")
    r.require(authority["anchors"]==analysis.PRECISE_PREFIX+"wire/anchors08.json","actual precise anchors")
    model="native/current-mim-bundle/mim/composition/pd500-mim-wire.spice"
    r.require(members[model]["sha256"]==analysis.MODEL_SHA,"actual final composed model pin")
    r.require(c["cases"]["nominal_early"]["selected"][model]==c["cases"]["constant_one"]["selected"][model]==analysis.MODEL_SHA,"same passive model in both rejected cases")
    names=set(members)|{c["cases"][case]["report_member"],"result.json"}
    r.require(names<=set(expected)and len(names)==36,"all selected inputs and actual reports")
    return names

def record_analysis(saved,pins,report,c,evidence,writer=r.write_new):
    """Retain every completed numerical pair before later endpoint or aggregate checks."""
    def read(name):return r.regular(saved,name).read_bytes()
    for name,pin in pins["members"].items():r.require(r.file_pin(r.regular(saved,name))==pin,"restored actual input "+name)
    root="native/current-mim-bundle/"
    contract=r.decode(read(root+"mim/composition/composition.json"))
    model=read(root+"mim/composition/pd500-mim-wire.spice").decode()
    planes=r.decode(read(root+"canonical-current-view/native-planes.json"))
    numeric=r.load_numeric(c)
    r.validate_binding(numeric,report,contract,planes,model)
    prefix=analysis.PRECISE_PREFIX
    anchors=r.decode(read(prefix+"wire/anchors08.json"))
    solver=analysis.load_solver();writer(evidence/"solver-controls.json",r.encode(solver.controls()))
    import numpy,scipy
    writer(evidence/"numerical-runtime.json",r.encode(dict(python=sys.version,numpy=numpy.__version__,scipy=scipy.__version__,openblas_threads=os.environ.get("OPENBLAS_NUM_THREADS"),omp_threads=os.environ.get("OMP_NUM_THREADS"))))
    pairs=[]
    def measured(edges,start,stop):
        value=solver.solve(edges,start,stop)
        index=len(pairs);record=dict(index=index,from_node=start,to_node=stop,wire_only_solution=value,**FLAGS)
        writer(evidence/("wire-solve-%02d.json"%index),r.encode(record));pairs.append(index)
        return value
    result=analysis.analyze(model,read(prefix+"wire/rc03/wires.spice").decode(),contract,anchors,
      read(prefix+"wire/rc03/pump_wires.res.ext").decode(),read(prefix+"wire/rc03/pump_wires.ext").decode(),
      read(prefix+"wire/rc03/pump_wires.mag").decode(),measured)
    r.require(len(pairs)==len(result["evaluations"])==34,"all actual requested solves")
    writer(evidence/"current-wire-ownership-analysis.json",r.encode(result))
    return result

def do_work(ctx,proof,controls,bundle,evidence,report):
    authorize(source_guard(ctx));report["controls"]=bind_controls(ctx,controls)
    r.write_new(evidence/"same-source-controls.json",r.encode(controls))
    c=r.source_guard();pins=r.decode(r.regular(ROOT,INPUTS).read_bytes())
    reserved=r.reservation(ctx,proof,r.api("releases/tags/"+ctx["tag"]),r.api("git/ref/tags/"+ctx["tag"]))
    r.write_new(evidence/"reservation.json",r.encode(dict(proof=proof,verified=reserved)))
    case=ctx["case"];entry=c["cases"][case]
    live={}
    for key,endpoint in(("run","actions/runs/"+str(c["producer"]["run_id"])),
      ("jobs","actions/runs/"+str(c["producer"]["run_id"])+"/attempts/1/jobs?per_page=100"),
      ("release","releases/"+str(entry["release_id"])),("ref","git/ref/tags/"+entry["tag"])):
        live[key]=r.api(endpoint);r.write_new(evidence/("producer-"+key+".json"),r.encode(live[key]))
    binding=r.validate_live(c,case,live["run"],live["jobs"],live["release"],live["ref"])
    summary,parts,original=r.metadata(c,case)
    names=selected_inputs(pins,c,case,summary["outputs"])
    r.write_new(evidence/"producer-live-binding.json",r.encode(binding))
    r.write_new(evidence/"producer-original-native-report.json",r.pinned(c,ROOT,entry["report_path"]))
    r.write_new(evidence/"selected-input-pins.json",r.encode(pins))
    r.require(shutil.disk_usage(bundle).free>=parts["bytes"]+4*1024**3,"runner disk before archive acquisition")
    transport=bundle/"transport";transport.mkdir()
    archive,received=r.acquire(c,case,parts,transport)
    r.write_new(evidence/"transport-proof.json",r.encode(received))
    saved=bundle/"native-inputs"
    census=r.select_archive(archive,summary["outputs"],names,parts["source_directory"],saved)
    r.write_new(evidence/"complete-input-census.json",r.encode(census))
    r.require(census["full_member_count"]==2797 and census["every_member_authenticated"]is True,"all original members")
    r.require(r.regular(saved,entry["report_member"]).read_bytes()==r.pinned(c,ROOT,entry["report_path"]),"received actual native report")
    r.require(r.file_pin(r.regular(saved,"result.json"))=={k:summary["raw_terminal"][k]for k in("bytes","sha256")},"received raw outer failure")
    # Full source archive remains permanently upstream. All selected native bytes
    # remain in our owned bundle for success/failure publication and fallback.
    shutil.rmtree(transport);report["input_census"]=dict(full_members=2797,selected=len(names),native_inputs_retained_in_bundle=True)
    result=record_analysis(saved,pins,original,c,evidence)
    for name in names:r.require(r.file_pin(r.regular(saved,name))==census["selected"][name],"actual selected input unchanged")
    source_guard(ctx)
    report.update(status="COMPLETE_CURRENT_CDR_WIRE_OWNERSHIP_DIAGNOSIS_ONLY",analysis_status=result["status"],
      completed_pairs=len(result["evaluations"]),original_electrical_status=original["status"],
      original_electrical_rejection_preserved=True,actual_model_analyzed=True,actual_native_inputs_acquired=True)
    return result

def terminal_body(action,integrity,writer,report):
    """Preserve primary failure and independent integrity/terminal evidence."""
    primary=None
    try:action()
    except BaseException as exc:
        primary=exc;report["error"]=repr(exc);report["traceback"]=traceback.format_exc()
    finally:
        try:integrity()
        except BaseException as exc:report["terminal_errors"].append(dict(action="source-integrity",error=repr(exc)))
        if primary is not None or report["terminal_errors"]:report["status"]="FAIL_CURRENT_CDR_WIRE_OWNERSHIP"
        try:writer(report)
        except BaseException as exc:
            report["terminal_errors"].append(dict(action="terminal-record",error=repr(exc)));report["status"]="FAIL_CURRENT_CDR_WIRE_OWNERSHIP"
            print("CDR_OWNERSHIP_UNSAVED_TERMINAL "+json.dumps(report,sort_keys=True),flush=True)
            if primary is None:primary=exc
    if primary is not None:raise primary
    r.require(not report["terminal_errors"],"ownership terminal errors")
    return report

def prepare_publication(ctx,bundle,destination):
    """Use qualified complete packing, with ownership-specific non-acceptance metadata."""
    import cloud_chunked_results as pack
    publisher.source_guard(publication_context(ctx))
    paths,index=publisher.prepare(publication_context(ctx),bundle,destination,pack.pack)
    path=paths[0];before=r.decode(path.read_bytes())
    r.require(before["schema"]=="complete-cdr-wave-replay-output-index-v1"
      and before["files"]==index["files"]and before["context"]==publication_context(ctx),"qualified complete index")
    after=dict(before);after["schema"]="complete-current-cdr-wire-ownership-output-index-v1"
    del after["original_capture_replayed_is_not_electrical_acceptance"]
    after.update(actual_capture_replayed=False,read_only_wire_diagnosis_is_not_electrical_acceptance=True)
    path.write_bytes(r.encode(after))
    r.require(r.decode(path.read_bytes())==after,"owned corrected output index")
    return paths,index

def final_integrity(ctx,bundle,evidence):
    outcomes={};errors=[]
    def inputs():
        path=evidence/"complete-input-census.json"
        if not path.exists():return dict(applicable=False,complete_census_available=False,partial_inputs_retained=True)
        census=r.decode(r.regular(evidence,path.name).read_bytes())
        r.require(census["every_member_authenticated"]is True and census["full_member_count"]==2797 and len(census["selected"])==36,"terminal full input census")
        for name,pin in census["selected"].items():r.require(r.file_pin(r.regular(bundle/"native-inputs",name))==pin,"terminal selected input unchanged: "+name)
        return dict(applicable=True,complete_census_available=True,selected=len(census["selected"]),unchanged=True)
    for name,fn in(("source",lambda:source_guard(ctx)),("selected-inputs",inputs)):
        try:
            value=fn();outcomes[name]=dict(complete=True,result=dict(verified=True)if name=="source"else value)
        except BaseException as exc:
            outcomes[name]=dict(complete=False,error=repr(exc));errors.append(outcomes[name])
    r.write_new(evidence/"terminal-integrity.json",r.encode(outcomes))
    r.require(not errors,"independent terminal integrity errors: "+repr(errors))
    return outcomes

def main():
    args=argparse.ArgumentParser()
    args.add_argument("--bundle",type=Path,required=True);args.add_argument("--publication",type=Path,required=True)
    args.add_argument("--reservation",type=Path,required=True);args.add_argument("--controls",type=Path,required=True)
    a=args.parse_args();ctx=context(os.environ)
    r.require(not a.bundle.exists()and not a.bundle.is_symlink(),"new owned bundle")
    a.bundle.mkdir();evidence=a.bundle/"evidence";evidence.mkdir()
    r.write_new(a.bundle/"owner.json",r.encode(ctx))
    report=dict(status="IN_PROGRESS",context=ctx,terminal_errors=[],actual_model_analyzed=False,actual_native_inputs_acquired=False,**FLAGS)
    primary=None;proof=None
    try:
        proof=r.decode(a.reservation.read_bytes());controls=r.decode(a.controls.read_bytes())
        terminal_body(lambda:do_work(ctx,proof,controls,a.bundle,evidence,report),
          lambda:final_integrity(ctx,a.bundle,evidence),lambda value:r.write_new(evidence/"result.json",r.encode(value)),report)
    except BaseException as exc:
        primary=exc
        if not(evidence/"result.json").exists():
            report.update(status="FAIL_CURRENT_CDR_WIRE_OWNERSHIP",error=repr(exc),traceback=traceback.format_exc())
            try:r.write_new(evidence/"result.json",r.encode(report))
            except BaseException as secondary:print("CDR_OWNERSHIP_TERMINAL_ERROR "+repr(secondary),flush=True)
    finally:
        try:
            r.require(proof is not None,"publication reservation loaded")
            source_guard(ctx)
            paths,index=prepare_publication(ctx,a.bundle,a.publication)
            receipt=publisher.publish(publication_context(ctx),proof,paths,a.publication)
            r.require(publisher.inventory(a.bundle)==index["files"],"published bundle unchanged")
            source_guard(ctx)
            print("CDR_OWNERSHIP_PUBLICATION "+json.dumps(dict(receipt=receipt,archive=index["archive"],
              complete_files=len(index["files"]),**FLAGS),sort_keys=True),flush=True)
        except BaseException as exc:
            print("CDR_OWNERSHIP_PUBLICATION_FAILURE "+json.dumps(dict(error=repr(exc),traceback=traceback.format_exc(),**FLAGS),sort_keys=True),flush=True)
            if primary is None:primary=exc
        try:r.emit(evidence)
        except BaseException as exc:
            print("CDR_OWNERSHIP_EMISSION_FAILURE "+repr(exc),flush=True)
            if primary is None:primary=exc
    if primary is not None:raise primary
if __name__=="__main__":main()
