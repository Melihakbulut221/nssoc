#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Storage-persistence candidate; native entry is disabled pending separate admission."""
NATIVE_EXECUTION_AUTHORIZED=False
import argparse,json,os,shutil,signal,sys,threading,traceback
import cdr_width_loaded_publication as publication
from pathlib import Path
import cdr_current_eight_drain_loaded_admission as a
import cdr_current_eight_drain_loaded_result as result_gate
import cdr_v59_tail_loaded_terminal as terminal
import cdr_v59_tail_access_runtime as runtime
import cloud_cdr_v59_binding_rc as evidence
import migrate_outputs_to_cloud as publisher
import ensure_cloud_tested_source_release as release
from wait_cloud_tested_source_release import wait
from cloud_chunked_results import pack

ROOT=a.ROOT
WORKER="scripts/cloud_cdr_current_eight_drain_loaded.py"
ENGINE_SHA="103134f6e3bf71771a7f9c94cc43fd5ea2f9d51490116718814aa344e9c51509"
PREP_PASS="PASS_CURRENT_TAIL_LOADED_PREPARATION_ORIGINAL_BINDING_GATES"
CASE_PASS="PASS_CURRENT_TAIL_ORIGINAL_LOADED_CASE_NOT_PHY_ACCEPTANCE"

def context(case,prepare):
    a.require(case in a.CASES and type(prepare)is bool and(not prepare or case=="nominal_early"),"Invalid original case mode")
    suffix="preparation"if prepare else case
    return {"case":case,"prepare":prepare,"group":"cdr-current-eight-drain-loaded-"+suffix,
      "output":ROOT/("cloud-cdr-current-eight-drain-loaded-evidence-"+suffix),
      "worker":ROOT/("cloud-cdr-current-eight-drain-loaded-"+case),
      "transport":ROOT/"hw/soc/out"/("cloud-cdr-current-eight-drain-loaded-"+suffix+"-publication"),
      "label":"original-loaded-"+suffix,"seconds":1200 if prepare else 7200}

def read_json(path):
    return json.loads(path.read_bytes())

def inventory(root):
    a.require(root.is_dir()and not root.is_symlink(),"Invalid complete evidence root")
    result={}
    for path in root.rglob("*"):
        a.require(not path.is_symlink(),"Symlink in complete evidence")
        if path.is_dir():continue
        a.require(path.is_file(),"Nonregular complete evidence")
        result[str(path.relative_to(root))]=a.sha(path)
    return result

def error_record(action,error):
    return {"action":action,"type":type(error).__name__,"error":repr(error),
      "traceback":"".join(traceback.format_exception(type(error),error,error.__traceback__))}

class StorageRefusal(AssertionError):
    def __init__(self,record):
        self.record=record
        super().__init__("Insufficient full loaded evidence storage")

def storage(ctx,label):
    a.require(label in ("initial","copy","publication"),"Unknown loaded storage checkpoint")
    root=ctx["worker"]if label=="copy"else ctx["output"]
    if not root.exists():size=0
    elif label=="copy":
        # Qualification/copy records each invalid member separately; sizing must
        # not prevent preservation of the remaining regular failure evidence.
        size=sum(path.stat().st_size for path in root.rglob("*")if not path.is_symlink()and path.is_file())
    else:size=sum(a.regular(root,n).stat().st_size for n in inventory(root))
    required=16*1024**3 if label=="initial"else max(4*1024**3,2*size+1024**3)
    free=shutil.disk_usage(ROOT).free
    record={"checkpoint":label,"free_bytes":free,"required_bytes":required,
      "available_source_bytes":size,"sufficient":free>=required,
      "native_execution_authorized":False}
    root=ctx["output"]
    a.require(root.is_dir()and not root.is_symlink(),"Storage evidence root required")
    journal=root/"storage-checks"
    a.require(not journal.is_symlink(),"Storage journal symlink refused")
    journal.mkdir(exist_ok=True)
    path=journal/(label+".json")
    # Exclusive creation and fsync preserve the measured refusal before raising.
    with path.open("x",encoding="utf-8")as stream:
        stream.write(json.dumps(record,sort_keys=True,indent=2)+"\n")
        stream.flush();os.fsync(stream.fileno())
    print("CURRENT_LOADED_STORAGE_CHECK "+json.dumps(record,sort_keys=True),flush=True)
    if not record["sufficient"]:raise StorageRefusal(record)
    return record

def preflight(ctx):
    a.authorize(ctx["prepare"]);c=a.descriptor();p=c["proposed_execution"]
    groups=["cdr-current-eight-drain-loaded-"+name for name in a.CASES]+["cdr-current-eight-drain-loaded-preparation"]
    a.require(set(groups)==set(p["groups"])and len(groups)==11 and p["reserve_all_eleven_before_any_native_dependencies"]is True
      and p["create_preparation_reservation_last"]is True,"Complete matrix reservation policy changed")
    a.require(p["preparation_seconds"]==1200 and p["each_loaded_case_seconds"]==7200
      and p["max_parallel"]==2 and p["fail_fast"]is False and p["automatic_retry"]is False,
      "Original matrix execution policy changed")
    reservations={group:wait(group,os.environ)for group in groups}
    return {"groups":reservations,"all_eleven_reserved_before_dependencies":True}

def fetch_preparation(ctx):
    group="cdr-current-eight-drain-loaded-preparation";tag,head=release.context(group,os.environ)
    info=release.api("releases/tags/"+tag);ref=release.api("git/ref/tags/"+tag)
    reservation=release.validate_release(info,ref,tag,head)
    stem=group+"-"+os.environ["GITHUB_RUN_ID"]+"-1"
    destination=ctx["output"]/"preparation-proof";destination.mkdir()
    fetched={}
    for suffix in ("summary.json","native-result.json"):
        rows=[x for x in info["assets"]if x["name"]==stem+"."+suffix]
        a.require(len(rows)==1,"Same-run preparation direct proof missing")
        asset=rows[0];digest=asset["digest"].removeprefix("sha256:")
        a.require(asset["state"]=="uploaded"and type(asset["size"])is int and 0<asset["size"]<=64*1024**2
          and len(digest)==64,"Invalid preparation proof asset")
        path=destination/suffix;a.fetch(asset["browser_download_url"],digest,path)
        a.require(path.stat().st_size==asset["size"]and a.sha(path)==digest,"Preparation proof asset changed")
        fetched[suffix]={"path":path,"sha256":digest,"asset":{k:asset[k]for k in ("id","name","size","digest")}}
    summary=read_json(fetched["summary.json"]["path"]);native=read_json(fetched["native-result.json"]["path"])
    a.require(summary["status"]==PREP_PASS and summary["source_head"]==head
      and summary["run_id"]==int(os.environ["GITHUB_RUN_ID"])and summary["run_attempt"]==1
      and summary["case"]=="nominal_early"and summary["preparation_only"]is True
      and summary["group"]==group,"Same-run preparation identity changed")
    a.require(summary["native_case_passed"]is True and summary["terminal_finalization_complete"]is True
      and summary["outer_terminal_finalization_complete"]is True and not summary["outer_terminal_errors"],
      "Same-run preparation did not qualify")
    a.require(summary["outputs"]["native/result.json"]==fetched["native-result.json"]["sha256"]
      and summary["native_controller_result_sha256"]==fetched["native-result.json"]["sha256"],
      "Preparation native bytes differ from full summary")
    a.require(all(summary[k]is False for k in ("accepted","qualified_pex","full_phy_accepted","cdr_accepted",
      "physical_accepted","geometry_regenerated","native_extraction_executed","automatic_retry")),
      "Preparation acceptance scope changed")
    result_gate.validate(native,"nominal_early",True,0)
    return native,{"reservation":reservation,"source_head":head,"run_id":int(os.environ["GITHUB_RUN_ID"]),
      "files":{name:{"member":"preparation-proof/"+name,"sha256":row["sha256"],"asset":row["asset"]}for name,row in fetched.items()},
      "complete_original_preparation_predicates_passed":True,"vectors":native["vector_census"]}

def execute(ctx,result,supervisor):
    argv=[sys.executable,str(ROOT/WORKER),"--case",ctx["case"]]
    if ctx["prepare"]:argv.append("--prepare-only")
    a.require(ctx["seconds"]==(1200 if ctx["prepare"]else 7200),"Unknown original loaded worker budget")
    primary=None;record=None
    try:supervisor.supervised(argv,ctx["label"],seconds=ctx["seconds"],cwd=ROOT)
    except BaseException as error:primary=error
    try:
        path=a.regular(supervisor.TRACE,ctx["label"]+".command.json")
        record=read_json(path)
        a.require(record["label"]==ctx["label"]and record["argv"]==argv,"Loaded command identity changed")
        result["command"]=record
        for stream in ("stdout","stderr"):
            path=a.regular(supervisor.TRACE,ctx["label"]+"."+stream)
            a.require(path.stat().st_size==record[stream+"_bytes"]and a.sha(path)==record[stream+"_sha256"],
              "Loaded complete command stream changed")
        a.require(record["returncode"]==0 and record["supervision_failure"]is None
          and not record["process_group_cleanup"]["remaining_live"],"Original loaded worker failed")
    except BaseException as error:
        result["command_evidence_error"]=error_record("command_evidence",error)
        if primary is None:primary=error
    if primary is not None:raise primary
    return record

def copy_worker(ctx,result):
    source=ctx["worker"];destination=ctx["output"]/"native"
    a.require(source.is_dir()and not source.is_symlink(),"Native worker evidence is missing or invalid")
    a.require(not destination.exists()and not destination.is_symlink(),"Native evidence destination exists")
    result["storage"].append(storage(ctx,"copy"))
    destination.mkdir();copied={};errors=[];records=[]
    for path in sorted(source.rglob("*")):
        name=str(path.relative_to(source));target=destination/name
        try:
            a.require(not path.is_symlink(),"Symlink in native worker evidence")
            if path.is_dir():target.mkdir(parents=True,exist_ok=True);continue
            a.require(path.is_file(),"Nonregular native worker evidence")
            before=a.sha(path);size=path.stat().st_size
            target.parent.mkdir(parents=True,exist_ok=True)
            with path.open("rb")as src,target.open("xb")as dst:shutil.copyfileobj(src,dst,4*1024**2)
            a.require(a.sha(target)==a.sha(path)==before and target.stat().st_size==size,"Native evidence changed during preservation")
            copied[name]=before
        except BaseException as error:
            errors.append(error);row=error_record("copy:"+name,error)
            if path.is_symlink():row["refused_symlink_target"]=os.readlink(path)
            records.append(row)
    result["native_evidence_preservation"]={"original_directory":str(source),"retained_directory":"native",
      "copied_files":copied,"errors":records,"complete":not errors,"original_metadata_rewritten":False}
    if errors:raise errors[0]
    a.require(copied==inventory(source)==inventory(destination),"Complete native evidence copy differs")

def qualify_native(ctx,result,prepared):
    root=ctx["output"]/"native";path=a.regular(root,"result.json")
    result["native_controller_result_sha256"]=a.sha(path)
    native=read_json(path);result["native_status"]=native.get("status")
    a.require(not result.get("body_error")and not result.get("command_evidence_error"),"Loaded owned command did not complete cleanly")
    a.require(native["outputs"]=={n:h for n,h in inventory(root).items()if n!="result.json"},
      "Complete native worker output map changed")
    a.verify_exact_files(root/"current-mim-bundle",a.expected_files())
    a.require(a.sha(a.regular(root,"source/source/runtime/patched-ngspice"))==
      ENGINE_SHA,"Original loaded engine changed")
    result["native_validation"]=result_gate.validate(native,ctx["case"],ctx["prepare"],result["command"]["returncode"],prepared)
    result["native_case_passed"]=True
    return native

def finalize(ctx,result,supervisor,heartbeat,previous,prepared):
    errors=[]
    def attempt(label,call):
        try:call();result["outer_terminal_actions"].append({"action":label,"completed":True})
        except BaseException as error:
            errors.append(error);result["outer_terminal_errors"].append(error_record(label,error))
            result["outer_terminal_actions"].append({"action":label,"completed":False})
    if supervisor is not None:
        def cleanup():result["owned_cleanup"]=supervisor.stop_process(supervisor.ACTIVE)
        attempt("owned_process_cleanup",cleanup)
        attempt("stop_heartbeat",supervisor.STOP.set)
    if heartbeat is not None:
        def join():
            heartbeat.join(timeout=5)
            a.require(not heartbeat.is_alive(),"Loaded heartbeat did not stop")
        attempt("join_heartbeat",join)
    for sig,handler in previous.items():
        def restore(sig=sig,handler=handler):signal.signal(sig,handler)
        attempt("restore_signal_"+str(int(sig)),restore)
    if supervisor is not None:
        def sample():result["terminal_resource_sample"]=supervisor.sample("loaded_terminal")
        attempt("terminal_resource_sample",sample)
    attempt("preserve_complete_native_evidence",lambda:copy_worker(ctx,result))
    attempt("original_native_case_qualification",lambda:qualify_native(ctx,result,prepared))
    result["outer_terminal_finalization_complete"]=not errors
    if result.get("body_error")or errors:result["status"]="FAIL_OR_REJECTED_CURRENT_TAIL_LOADED_CASE"
    elif result["native_case_passed"]:result["status"]=PREP_PASS if ctx["prepare"]else CASE_PASS
    def save():a.write(ctx["output"]/"result.json",result)
    try:terminal.finalize(ctx["output"],result,save,a)
    except BaseException as error:errors.append(error)
    return errors

def initial_result(ctx,reservations,initial):
    return {"status":"RUNNING_CURRENT_TAIL_LOADED_CASE","source_head":os.environ["GITHUB_SHA"],
      "run_id":int(os.environ["GITHUB_RUN_ID"]),"run_attempt":1,"case":ctx["case"],"preparation_only":ctx["prepare"],
      "group":ctx["group"],"reservations":reservations,"storage":[initial],
      "native_case_passed":False,"accepted":False,"qualified_pex":False,"full_phy_accepted":False,
      "cdr_accepted":False,"physical_accepted":False,"geometry_regenerated":False,
      "native_extraction_executed":False,"automatic_retry":False,
      "original_eight_electrical_rejections_and_two_fault_detections_preserved":True,
      "fresh_RC_run":a.RUN,"original_physical_run":40369539200,
      "original_physical_status":"FAIL_ADDITIVE_TAIL_WIRE_PHYSICAL",
      "original_physical_historical_only":True,
      "current_width_run":a.PHYSICAL_RUN,"current_width_source":a.PHYSICAL_SOURCE,
      "current_graph_run":a.GRAPH_RUN,"current_graph_source":a.GRAPH_SOURCE,
      "outer_terminal_actions":[],"outer_terminal_errors":[],"outer_terminal_finalization_complete":False}

def validate_publication(ctx,result):
    a.require(result["source_head"]==os.environ["GITHUB_SHA"]
      and type(result["run_id"])is int and result["run_id"]==int(os.environ["GITHUB_RUN_ID"])
      and type(result["run_attempt"])is int and result["run_attempt"]==1,"Loaded publication run/source changed")
    a.require(result["case"]==ctx["case"]and result["preparation_only"]is ctx["prepare"]
      and result["group"]==ctx["group"],"Loaded publication case changed")
    a.require(result["fresh_RC_run"]==a.RUN and result["original_physical_run"]==40369539200
      and result["original_physical_status"]=="FAIL_ADDITIVE_TAIL_WIRE_PHYSICAL"
      and result["original_physical_historical_only"]is True
      and (result["current_width_run"],result["current_width_source"])==(a.PHYSICAL_RUN,a.PHYSICAL_SOURCE)
      and (result["current_graph_run"],result["current_graph_source"])==(a.GRAPH_RUN,a.GRAPH_SOURCE)
      and result["original_eight_electrical_rejections_and_two_fault_detections_preserved"]is True,
      "Loaded publication prior evidence changed")
    a.require(all(result[k]is False for k in ("accepted","qualified_pex","full_phy_accepted","cdr_accepted",
      "physical_accepted","geometry_regenerated","native_extraction_executed","automatic_retry")),
      "Loaded publication acceptance scope changed")
    successful=result["status"]in (PREP_PASS,CASE_PASS)
    if successful:
        a.require(result["status"]==(PREP_PASS if ctx["prepare"]else CASE_PASS)
          and result["native_case_passed"]is True and result["terminal_finalization_complete"]is True
          and result["outer_terminal_finalization_complete"]is True and not result["outer_terminal_errors"]
          and not result["terminal_errors"]and result["native_evidence_preservation"]["complete"]is True,
          "Incomplete loaded case cannot publish as successful")
    else:a.require(result["status"].startswith(("FAIL_","RUNNING_")),"Unrecognized failed loaded status")
    a.require(result["outputs"]=={n:h for n,h in inventory(ctx["output"]).items()if n!="result.json"},
      "Loaded publication complete output inventory differs")
    return successful

def publish(ctx,result=None):
    return publication.publish(sys.modules[__name__],ctx,result)

def run_case(ctx,reservations):
    method=a.authorize(ctx["prepare"])
    a.require(all(not p.exists()and not p.is_symlink()for p in (ctx["output"],ctx["worker"],ctx["transport"])),
      "Loaded destinations already exist")
    ctx["output"].mkdir(parents=True)
    result=initial_result(ctx,reservations,None);result["storage"]=[];primary=None;supervisor=None;heartbeat=None;previous={};prepared=None
    try:
        a.write(ctx["output"]/"result.json",result)
        result["storage"].append(storage(ctx,"initial"))
        a.write(ctx["output"]/"result.json",result)
        if not ctx["prepare"]:
            prepared,proof=fetch_preparation(ctx);result["same_run_preparation"]=proof
        supervisor=runtime.supervisor(ROOT,ctx["output"],ctx["output"]/"supervision",a.methods,
          method["protected_sha256"][runtime.SAMPLER])
        supervisor.TRACE.mkdir()
        for sig in (signal.SIGINT,signal.SIGTERM):previous[sig]=signal.signal(sig,supervisor.interrupted)
        candidate=threading.Thread(target=supervisor.heartbeat,daemon=True);candidate.start();heartbeat=candidate
        execute(ctx,result,supervisor)
    except BaseException as error:
        if isinstance(error,StorageRefusal):result["storage"].append(error.record)
        primary=error;result.update(status="FAIL_OR_REJECTED_CURRENT_TAIL_LOADED_CASE",
          body_error=error_record("loaded_worker",error))
    terminal_errors=finalize(ctx,result,supervisor,heartbeat,previous,prepared)
    publication_error=None
    try:publish(ctx,result)
    except BaseException as error:publication_error=error
    if primary is not None:raise primary
    if terminal_errors:raise terminal_errors[0]
    if publication_error is not None:raise publication_error
    a.require(result["status"]==(PREP_PASS if ctx["prepare"]else CASE_PASS),"Original loaded case did not qualify")
    return result

def main():
    raise SystemExit("Native execution disabled: this candidate requires separate exact-case admission and review.")

if __name__=="__main__":main()
