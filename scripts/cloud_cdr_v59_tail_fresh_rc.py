#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Owned-process fresh RC on immutable saved tail geometry; no layout or electrical acceptance."""
import argparse
import ast
import contextlib
import json
import os
from pathlib import Path
import shutil
import signal
import sys
import threading
import traceback
import cdr_v59_tail_fresh_rc_admission as source
import cdr_v59_tail_fresh_rc_legacy as stages
import cdr_v59_tail_access_runtime as runtime
import migrate_outputs_to_cloud as publisher
import ensure_cloud_tested_source_release as release
from cloud_chunked_results import pack
from wait_cloud_tested_source_release import wait

ROOT=source.ROOT
OUT=source.OUT
TRANSPORT=ROOT/"hw/soc/out/cloud-cdr-v59-tail-fresh-rc-publication"
GROUP="cdr-v59-tail-fresh-rc"
APP_SHA="d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466"
SECONDS={"restore-complete-saved955-and-current184":1200,"fresh-current500-binding":1200,
 "fresh-current500-wire-RC":1200,"fresh-seven-MIM-both-native-orders":1200}
PIPELINE_SOURCE="scripts/cloud_cdr_v59_mim_stage.py"
PIPELINE_SHA="15c6d6f6399f28a211ad0ea86a385d4400ab43aab6b0109214240b6eca935372"
PIPELINE_PASS="PASS_PD500_MIM_NATIVE_DOUBLE_TOTALS_TWO_ORDERS_22_CONTROLS_EACH_AND21_COMPOSITION_CONTROLS_REQUIRES_LOADED_WAVES"
PASS="PASS_FRESH_TAIL500_BINDING_WIRE_RC_SEVEN_MIM_TWO_ORDERS_REQUIRES_ORIGINAL_ELECTRICAL_MATRIX"
DIRECT={"archive-verification.json":"restore/archive-verification.json",
 "joint-admission.json":"restore/joint-admission.json","canonical-candidate.json":"restore/canonical-candidate.json",
 "binding-result.json":"binding/result.json","binding.json":"binding/binding.json",
 "wire-RC-result.json":"wire-stage/result.json","MIM-precision-result.json":"mim/result.json",
 "precise-capture.json":"mim/precise/result.json","precise-audit.json":"mim/precise/audit-stage/result.json",
 "reversed-capture.json":"mim/precise_reversed/result.json","reversed-audit.json":"mim/precise_reversed/audit-stage/result.json",
 "composition.json":"mim/composition/composition.json","runtime-smoke.json":"runtime-smoke/result.json"}

def require(value,message):
    if not value:raise AssertionError(message)

def inventory(root):
    return stages.inventory(root)

def storage(label):
    require(label in ("initial","restore","binding","wire","MIM","publication"),"Unknown storage checkpoint")
    size=0
    if OUT.exists():
        for name in inventory(OUT):size+=source.regular(OUT,name).stat().st_size
    required=max(4*1024**3,2*size+1024**3) if label=="publication" else (16 if label=="initial" else 8)*1024**3
    free=shutil.disk_usage(ROOT).free
    require(free>=required,"Insufficient complete-evidence storage reserve")
    return {"checkpoint":label,"free_bytes":free,"required_bytes":required,"current_output_bytes":size}

@contextlib.contextmanager
def tokenless():
    old={key:os.environ.get(key)for key in ("GH_TOKEN","GITHUB_TOKEN")}
    try:
        for key in old:os.environ.pop(key,None)
        yield
    finally:
        for key,value in old.items():
            if value is None:os.environ.pop(key,None)
            else:os.environ[key]=value

def exception_record(label,error):
    return {"action":label,"type":type(error).__name__,"error":repr(error),
      "traceback":"".join(traceback.format_exception(type(error),error,error.__traceback__))}

def save_result(result):
    try:source.write(OUT/"result.json",result)
    except BaseException as error:
        result["terminal_save_error"]=exception_record("save_result",error)
        result["fresh_RC_pipeline_complete"]=False
        if result["status"]==PASS or result["status"].startswith("RUNNING"):
            result["status"]="FAIL_TERMINAL_SAVE"
        print(json.dumps({"unsaved_terminal_fresh_RC_result":result},sort_keys=True,allow_nan=False),flush=True)
        raise

def execute(supervisor,result,argv,label,without_tokens=False):
    require(label in SECONDS,"Unknown supervised fresh RC phase")
    primary=None;errors=[];record=None
    try:
        with tokenless()if without_tokens else contextlib.nullcontext():
            supervisor.supervised(argv,label,seconds=SECONDS[label],cwd=ROOT)
    except BaseException as error:primary=error
    try:
        path=supervisor.TRACE/(label+".command.json")
        record=source.read_json(source.regular(supervisor.TRACE,path.name))
        require(record["label"]==label and record["argv"]==list(map(str,argv)),"Supervised command identity changed")
        for stream in ("stdout","stderr"):
            path=source.regular(supervisor.TRACE,label+"."+stream)
            require(path.stat().st_size==record[stream+"_bytes"] and source.sha(path)==record[stream+"_sha256"],
              "Complete supervised stream differs from command record")
        result["commands"].append(record)
        require(record["returncode"]==0 and record["supervision_failure"] is None
          and not record["process_group_cleanup"]["remaining_live"],"Supervised fresh RC phase rejected")
    except BaseException as error:
        errors.append(error);result.setdefault("command_evidence_errors",[]).append(exception_record(label,error))
    try:save_result(result)
    except BaseException as error:errors.append(error)
    if primary is not None:raise primary
    if errors:raise errors[0]
    return record

def pipeline_validator():
    path=source.regular(ROOT,PIPELINE_SOURCE)
    require(source.sha(path)==PIPELINE_SHA,"Frozen MIM pipeline validator changed")
    tree=ast.parse(path.read_text())
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=="validate_pipeline"]
    require(len(nodes)==1,"Frozen MIM pipeline validator missing")
    scope={"os":os,"PASS":PIPELINE_PASS}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),"exec"),scope)
    return scope["validate_pipeline"]

def validate_completed_pipeline():
    report=source.read_json(stages.MIM_OUT/"result.json")
    pipeline_validator()(report,0)
    require(report["outputs"]=={n:h for n,h in inventory(stages.MIM_OUT).items()if n!="result.json"},
      "Complete fresh MIM output map changed")
    for variant in ("precise","precise_reversed"):
        pair=report["variants"][variant]
        require(pair["capture"]==source.read_json(stages.MIM_OUT/variant/"result.json")
          and pair["audit"]==source.read_json(stages.MIM_OUT/variant/"audit-stage/result.json"),
          "Fresh native-order reports differ from completed pipeline")
    require(report["composition"]["contract"]==source.read_json(stages.MIM_OUT/"composition/composition.json"),
      "Fresh composition differs from completed pipeline")
    stages.verify_restored()
    return {"status":report["status"],"summary_sha256":source.sha(stages.MIM_OUT/"result.json"),
      "complete_output_files":len(report["outputs"]),"same_run_complete_binding_and_RC_handoff":True,
      "unchanged_original_pipeline_validator":PIPELINE_SHA,"both_native_orders_verified":True,
      "original_physical_failure_relabelled":False,"qualified_pex":False,"electrical_accepted":False}

def run(result,supervisor,method):
    result["storage"].append(storage("restore"))
    execute(supervisor,result,[sys.executable,__file__,"--restore-worker"],"restore-complete-saved955-and-current184")
    pin=source.read_json(stages.PIN)
    result["saved_geometry_admission"]={"sha256":source.sha(stages.PIN),"status":pin["status"],
      "original_physical_run_status":pin["original_physical_run_status"]}
    stages.verify_saved_inputs(pin)
    app=Path(os.environ["CLOUD_APPIMAGE"])
    require(app.is_file()and not app.is_symlink()and source.sha(app)==APP_SHA,"Qualified AppImage changed")
    launcher=runtime.launcher(ROOT,source.methods,method["protected_sha256"][runtime.PROBE])
    with tokenless():result["runtime_smoke"]=launcher.probe(app,APP_SHA,OUT/"runtime-smoke")
    save_result(result)
    require(result["runtime_smoke"]["accepted"] is True,"Qualified native launcher smoke rejected")
    result["storage"].append(storage("binding"));result["binding_executed"]=True
    execute(supervisor,result,[sys.executable,stages.derived("binding")],"fresh-current500-binding",True)
    binding=stages.stage_pin("binding")
    result["binding_result_sha256"]=binding["summary_sha256"]
    result["storage"].append(storage("wire"));result["extraction_executed"]=True
    execute(supervisor,result,[sys.executable,stages.derived("rc")],"fresh-current500-wire-RC",True)
    rc=stages.stage_pin("rc");result["wire_RC_result_sha256"]=rc["summary_sha256"]
    result["storage"].append(storage("MIM"))
    execute(supervisor,result,[sys.executable,stages.derived("precision")],"fresh-seven-MIM-both-native-orders",True)
    result["completed_pipeline"]=validate_completed_pipeline()
    require(source.sha(app)==APP_SHA,"Qualified AppImage changed during extraction")
    source.methods();stages.verify_saved_inputs(pin)
    result.update(status=PASS,fresh_RC_pipeline_complete=True)

def finalization(result,supervisor,heartbeat,previous):
    errors=[]
    def attempt(label,fn):
        try:
            value=fn();result.setdefault("terminal_actions",[]).append({"action":label,"completed":True})
            if value is not None:result.setdefault("terminal_evidence",{})[label]=value
        except BaseException as error:
            errors.append(error);result.setdefault("terminal_errors",[]).append(exception_record(label,error))
    if supervisor is not None:
        attempt("owned_process_cleanup",lambda:supervisor.stop_process(supervisor.ACTIVE))
        attempt("stop_heartbeat",supervisor.STOP.set)
    if heartbeat is not None:
        def join():
            heartbeat.join(timeout=5)
            require(not heartbeat.is_alive(),"Heartbeat did not stop")
        attempt("join_heartbeat",join)
    for sig,handler in previous.items():
        attempt("restore_signal_"+str(int(sig)),lambda sig=sig,handler=handler:signal.signal(sig,handler))
    if supervisor is not None:attempt("terminal_resource_sample",lambda:supervisor.sample("fresh_RC_terminal"))
    def source_integrity():
        method=source.methods()
        return {"method_sha256":source.sha(source.METHOD),"protected_files":len(method["protected_sha256"])}
    attempt("protected_source_integrity",source_integrity)
    if stages.PIN.exists():
        attempt("saved_input_integrity",lambda:stages.verify_saved_inputs(source.read_json(stages.PIN)))
    # Copy actual available current bytes even if integrity failed; never rewrite original metadata.
    if stages.ANALYSIS.exists():
        def copy_current():
            table=inventory(stages.ANALYSIS)
            proof=stages.copy_table(stages.ANALYSIS,OUT/"canonical-current-view",table)
            return {"files":len(table),"all_actual_bytes_preserved":True,"verification":proof,
              "original_metadata_preserved":True,"integrity_acceptance":False}
        attempt("canonical_current_evidence_copy",copy_current)
    def output_map():
        result["outputs"]={n:h for n,h in inventory(OUT).items()if n!="result.json"}
    attempt("complete_output_inventory",output_map)
    if errors:
        result["fresh_RC_pipeline_complete"]=False
        if result["status"]==PASS or result["status"].startswith("RUNNING"):result["status"]="FAIL_TERMINAL_FINALIZATION"
    result["terminal_finalization_complete"]=not errors
    try:save_result(result)
    except BaseException as error:errors.append(error)
    return errors

def collect_direct(result):
    successful=result["status"]==PASS
    files=[];bindings=[]
    for name,member in DIRECT.items():
        path=OUT/member
        require(not path.is_symlink(),"Direct evidence is a symlink")
        if successful:require(path.exists(),"Missing successful direct evidence: "+member)
        if not path.exists():continue
        path=source.regular(OUT,member);digest=source.sha(path)
        require(result["outputs"].get(member)==digest,"Direct evidence differs from terminal output map")
        if successful:
            try:source.read_json(path)
            except (ValueError,UnicodeError)as error:
                raise AssertionError("Malformed direct JSON cannot qualify fresh RC success: "+member)from error
        files.append((name,path))
        bindings.append({"asset_suffix":name,"output_member":member,"bytes":path.stat().st_size,
          "sha256":digest,"qualified_as_success":successful,"JSON_syntax_checked":successful})
    return files,bindings

def validate_publication(result):
    require(result["source_head"]==os.environ["GITHUB_SHA"],"Publication source changed")
    require(type(result["run_id"])is int and result["run_id"]==int(os.environ["GITHUB_RUN_ID"]),
      "Publication run changed")
    require(type(result["run_attempt"])is int and result["run_attempt"]==1,"Publication attempt changed")
    require(result["original_physical_run"]==40369539200 and result["typed_saved_readback_run"]==40542841034
      and result["original_physical_status"]=="FAIL_ADDITIVE_TAIL_WIRE_PHYSICAL"
      and result["original_failure_preserved"]is True,"Original physical failure identity changed")
    for key in ("automatic_retry","physical_geometry_regenerated","simulation_executed","physical_accepted",
      "electrical_accepted","qualified_pex","full_phy_accepted"):
        require(result[key]is False,"Publication engineering scope changed")
    for key in ("binding_executed","extraction_executed","fresh_RC_pipeline_complete"):
        require(type(result[key])is bool,"Publication execution flag is not boolean")
    if result["status"]==PASS:
        require(result["fresh_RC_pipeline_complete"]is True and result["terminal_finalization_complete"]is True
          and result["binding_executed"]is True and result["extraction_executed"]is True
          and not result.get("terminal_errors"),"Incomplete fresh RC success")
    else:
        require(result["status"].startswith(("FAIL_","RUNNING_"))and result["fresh_RC_pipeline_complete"]is False,
          "Failed result incorrectly qualifies fresh RC")
    require(result["outputs"]=={n:h for n,h in inventory(OUT).items()if n!="result.json"},
      "Publication complete output map changed")

def publish(result):
    require(os.environ.get("GITHUB_RUN_ATTEMPT")=="1","Publication requires first attempt")
    require(OUT.is_dir()and not OUT.is_symlink()and not TRANSPORT.exists()and not TRANSPORT.is_symlink(),
      "Invalid publication roots")
    storage("publication")
    report=source.regular(OUT,"result.json");require(source.read_json(report)==result,"Terminal report changed")
    validate_publication(result);direct,bindings=collect_direct(result)
    TRANSPORT.mkdir()
    stem=GROUP+"-"+os.environ["GITHUB_RUN_ID"]+"-1"
    summary=TRANSPORT/(stem+".summary.json");shutil.copyfile(report,summary)
    require(source.sha(summary)==source.sha(report),"Published summary bytes changed")
    packed=pack(OUT,stem,TRANSPORT,512*1024**2)
    helper=source.frozen.publication_helpers()
    files=helper.publication_files(TRANSPORT,summary,TRANSPORT/(stem+".parts.json"),packed)
    for name,path in direct:
        target=TRANSPORT/(stem+"."+name);shutil.copyfile(path,target)
        require(source.sha(target)==source.sha(path),"Direct JSON copy changed")
        files.append(target)
    require(len({p.name for p in files})==len(files),"Duplicate publication names")
    proof={"status":"RUNNING_PUBLICATION","assets":[],"direct_asset_bindings":bindings,
      "failed_direct_outputs_preserved_as_raw_bytes":result["status"]!=PASS,
      "original_failure_preserved":True}
    source.write(TRANSPORT/"publication.json",proof)
    tag,_=release.context(GROUP,os.environ)
    previous=publisher.release;publisher.release=helper.only_reserved(GROUP,os.environ,release.api)
    try:
        for path in files:
            before=source.sha(path);proof["assets"].append(publisher.publish(path,tag))
            require(source.sha(path)==before,"Publication asset bytes changed")
            source.write(TRANSPORT/"publication.json",proof)
        proof["status"]="PASS_COMPLETE_FRESH_RC_EVIDENCE_PUBLISHED"
    except BaseException as error:proof.update(status="FAIL_PUBLICATION",error=repr(error));raise
    finally:
        publisher.release=previous;source.write(TRANSPORT/"publication.json",proof)
    return proof

def initial_result(reservation,initial):
    return {"status":"RUNNING_FRESH_TAIL_RC","run_id":int(os.environ["GITHUB_RUN_ID"]),"run_attempt":1,
      "source_head":os.environ["GITHUB_SHA"],"reservation":reservation,"commands":[],"storage":[initial],
      "original_physical_run":40369539200,"typed_saved_readback_run":40542841034,
      "original_physical_status":"FAIL_ADDITIVE_TAIL_WIRE_PHYSICAL","original_failure_preserved":True,
      "automatic_retry":False,"binding_executed":False,"extraction_executed":False,
      "physical_geometry_regenerated":False,"simulation_executed":False,"physical_accepted":False,
      "electrical_accepted":False,"qualified_pex":False,"full_phy_accepted":False,
      "fresh_RC_pipeline_complete":False,"terminal_finalization_complete":False}

def main():
    parser=argparse.ArgumentParser()
    group=parser.add_mutually_exclusive_group()
    group.add_argument("--restore-worker",action="store_true")
    group.add_argument("--preflight",action="store_true")
    group.add_argument("--publish-only",action="store_true")
    args=parser.parse_args();method=source.authorize()
    if args.restore_worker:source.restore(stages.RESTORE);return
    reservation=wait(GROUP,os.environ)
    if args.preflight:print(json.dumps(reservation,sort_keys=True));return
    if args.publish_only:
        require(OUT.is_dir()and not OUT.is_symlink(),"No existing fresh RC evidence")
        if (OUT/"result.json").is_file():result=source.read_json(OUT/"result.json")
        else:
            result=initial_result(reservation,{})
            result.update(status="FAIL_BEFORE_TERMINAL_REPORT",outputs={n:h for n,h in inventory(OUT).items()if n!="result.json"})
            save_result(result)
        publish(result);return
    initial=storage("initial")
    require(not OUT.exists()and not OUT.is_symlink()and not TRANSPORT.exists()and not TRANSPORT.is_symlink()
      and not stages.ANALYSIS.exists()and not stages.ANALYSIS.is_symlink(),"Fresh RC destination already exists")
    OUT.mkdir(parents=True)
    result=initial_result(reservation,initial);primary=None;supervisor=None;heartbeat=None;previous={}
    try:
        save_result(result)
        supervisor=runtime.supervisor(ROOT,OUT,OUT/"supervision",source.methods,method["protected_sha256"][runtime.SAMPLER])
        supervisor.TRACE.mkdir()
        for sig in (signal.SIGINT,signal.SIGTERM):previous[sig]=signal.signal(sig,supervisor.interrupted)
        candidate=threading.Thread(target=supervisor.heartbeat,daemon=True);candidate.start();heartbeat=candidate
        run(result,supervisor,method)
    except BaseException as error:
        primary=error
        result.update(status="FAIL_FRESH_TAIL_RC",error=repr(error),traceback=traceback.format_exc(),
          fresh_RC_pipeline_complete=False)
    terminal=finalization(result,supervisor,heartbeat,previous)
    publication_error=None
    try:publish(result)
    except BaseException as error:publication_error=error
    if primary is not None:raise primary
    if terminal:raise terminal[0]
    if publication_error is not None:raise publication_error
    require(result["status"]==PASS and result["fresh_RC_pipeline_complete"]is True,"Fresh RC did not complete")

if __name__=="__main__":main()
