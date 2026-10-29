#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only generation/reread with qualified supervision and permanent failure evidence."""
import argparse, contextlib, json, os, shutil, signal, sys, threading, traceback
from pathlib import Path
import cdr_selector_width_topology_stage as source
import cdr_v59_tail_access_runtime as runtime
import cdr_v59_tail_saved_identity as publication_helpers
import ensure_cloud_tested_source_release as release
import migrate_outputs_to_cloud as publisher
from cloud_chunked_results import pack
from wait_cloud_tested_source_release import wait

ROOT=source.ROOT
OUT=source.OUT
TRANSPORT=ROOT/"hw/soc/out/cloud-cdr-selector-width-topology-publication"
GROUP=source.GROUP
DRIVER_LOG=ROOT/"hw/soc/out/cdr-selector-width-topology-driver-logs/driver.log"
PASS="PASS_WIDTH_TOPOLOGY_REQUIRES_FRESH_RC_AND_ELECTRICAL"
BUDGETS={k:1200 for k in ("restore-complete-graph-capsule","native-synthetic-controls","actual-native-comparison-and-faults")}
FALSE=("fresh_RC_executed","simulation_executed","graph_equivalence_accepted","native_DRC_executed","native_LVS_executed",
       "physical_accepted","electrical_accepted","qualified_pex","full_phy_accepted","automatic_retry")
require=source.require

def inventory(root):
    require(root.is_dir()and not root.is_symlink(),"Invalid evidence root")
    result={}
    for p in root.rglob("*"):
        require(not p.is_symlink(),"Symlink in evidence")
        if p.is_dir():continue
        require(p.is_file(),"Nonregular evidence")
        result[p.relative_to(root).as_posix()]=source.sha(p)
    return result

def error_record(label,error):
    return dict(action=label,type=type(error).__name__,error=repr(error),
                traceback="".join(traceback.format_exception(type(error),error,error.__traceback__)))

def storage(publication=False):
    total=sum((OUT/n).stat().st_size for n in inventory(OUT))if OUT.exists()else 0
    required=max(4*1024**3,2*total+1024**3)if publication else 16*1024**3
    free=shutil.disk_usage(ROOT).free
    require(free>=required,"Insufficient complete-evidence storage")
    return dict(free_bytes=free,required_bytes=required,evidence_bytes=total)

@contextlib.contextmanager
def tokenless():
    old={k:os.environ.get(k)for k in ("GH_TOKEN","GITHUB_TOKEN")}
    try:
        for k in old:os.environ.pop(k,None)
        yield
    finally:
        for k,v in old.items():
            if v is None:os.environ.pop(k,None)
            else:os.environ[k]=v

def initial(reservation):
    r=dict(status="RUNNING_WIDTH_TOPOLOGY_COMPARISON",source_head=os.environ["GITHUB_SHA"],
      run_id=int(os.environ["GITHUB_RUN_ID"]),run_attempt=1,reservation=reservation,commands=[],
      topology_started=False,native_width_comparison_passed=False,
      terminal_finalization_complete=False,original_failure_preserved=True,
      source_graph_run=source.RUN,source_graph_head=source.HEAD,
      consumed_view=source.VIEW,complete_input_members=4103,
      candidate_gds_sha256=source.GDS_SHA)
    r.update({k:False for k in FALSE})
    return r

def output_map(result):
    result["outputs"]={n:h for n,h in inventory(OUT).items()if n!="result.json"}

def fallback(key,result):
    try:print(json.dumps({key:result},sort_keys=True,allow_nan=False),file=sys.stderr,flush=True)
    except BaseException:pass

def finish(result,supervisor,heartbeat,previous):
    errors=[]
    def attempt(label,fn):
        try:
            value=fn()
            result.setdefault("terminal_actions",[]).append(dict(action=label,completed=True))
            if value is not None:result.setdefault("terminal_evidence",{})[label]=value
        except BaseException as error:
            errors.append(error);result.setdefault("terminal_errors",[]).append(error_record(label,error))
    if supervisor is not None:
        attempt("owned_process_cleanup",lambda:supervisor.stop_process(supervisor.ACTIVE))
        attempt("stop_heartbeat",supervisor.STOP.set)
    if heartbeat is not None:
        def join():
            heartbeat.join(timeout=5);require(not heartbeat.is_alive(),"Heartbeat did not stop")
        attempt("join_heartbeat",join)
    for sig,handler in previous.items():
        def restore(sig=sig,handler=handler):signal.signal(sig,handler)
        attempt("restore_signal_"+str(int(sig)),restore)
    if supervisor is not None:attempt("terminal_resource_sample",lambda:supervisor.sample("geometry_terminal"))
    attempt("protected_source_integrity",lambda:dict(protected_files=len(source.methods()["protected_sha256"])))
    if (OUT/source.VIEW).exists():attempt("complete_saved_input_integrity",lambda:source.validate_view(OUT))
    attempt("complete_output_inventory",lambda:output_map(result))
    result["terminal_finalization_complete"]=not errors
    if errors:result.update(status="FAIL_TERMINAL",native_width_comparison_passed=False)
    try:source.atomic(OUT/"result.json",result)
    except BaseException as error:
        errors.append(error);result.setdefault("terminal_errors",[]).append(error_record("atomic_terminal_save",error))
        result.update(status="FAIL_TERMINAL_SAVE",native_width_comparison_passed=False,terminal_finalization_complete=False)
        attempt("post_save_failure_inventory",lambda:output_map(result))
        fallback("unsaved_geometry_terminal",result)
    return errors

def execute(supervisor,result,argv,label,without_tokens=False):
    primary=None;errors=[];record=None
    try:
        with tokenless()if without_tokens else contextlib.nullcontext():
            supervisor.supervised(argv,label,seconds=BUDGETS[label],cwd=ROOT)
    except BaseException as error:primary=error
    try:
        record=source.read(source.regular(supervisor.TRACE,label+".command.json"))
        require(record["label"]==label and record["argv"]==list(map(str,argv)),"Command identity changed")
        for stream in ("stdout","stderr"):
            p=source.regular(supervisor.TRACE,label+"."+stream)
            require(p.stat().st_size==record[stream+"_bytes"]and source.sha(p)==record[stream+"_sha256"],
                    "Complete command stream changed")
        result["commands"].append(record)
        require(record["returncode"]==0 and record["supervision_failure"]is None
          and not record["process_group_cleanup"]["remaining_live"],"Supervised geometry phase failed")
    except BaseException as error:
        errors.append(error);result.setdefault("command_errors",[]).append(error_record(label,error))
    try:source.atomic(OUT/"result.json",result)
    except BaseException as error:errors.append(error)
    if primary is not None:raise primary
    if errors:raise errors[0]
    return record

def run(result,supervisor,method):
    worker=ROOT/"scripts/cdr_selector_width_topology_stage.py"
    execute(supervisor,result,[sys.executable,str(worker),"restore"],"restore-complete-graph-capsule")
    result["restore"]=source.read(OUT/"restore.json");source.validate_view(OUT)
    app=Path(os.environ["CLOUD_APPIMAGE"])
    require(app.is_file()and not app.is_symlink()and source.sha(app)==source.APP_SHA,"Qualified AppImage changed")
    launcher=runtime.launcher(ROOT,source.methods,method["protected_sha256"][runtime.PROBE])
    with tokenless():result["runtime_smoke"]=launcher.probe(app,source.APP_SHA,OUT/"runtime-smoke")
    require(result["runtime_smoke"]["accepted"]is True,"Qualified runtime smoke failed")
    result["topology_started"]=True;source.atomic(OUT/"result.json",result)
    checker=ROOT/"scripts/check_cdr_selector_width_topology.py"
    execute(supervisor,result,[str(app),"python",str(checker),"--native-synthetic",
      "--output",str(OUT/"native-synthetic.json")],"native-synthetic-controls",True)
    execute(supervisor,result,[str(app),"python",str(checker),"--native",
      "--old-root",str(OUT/source.VIEW/source.OLD),"--new-root",str(OUT/source.VIEW/source.FRESH),
      "--expected",str(OUT/"expected-roots.json"),"--output",str(OUT/"native-controls.json")],
      "actual-native-comparison-and-faults",True)
    result["candidate"]=source.validate_candidate(OUT)
    require(source.sha(app)==source.APP_SHA,"AppImage changed during comparison")
    source.methods()
    result.update(status=PASS,native_width_comparison_passed=True)

def main_run(reservation):
    method=source.authorize();storage()
    require(not OUT.exists()and not OUT.is_symlink()and not TRANSPORT.exists()and not TRANSPORT.is_symlink(),
            "Destination already exists")
    OUT.mkdir(parents=True);result=initial(reservation)
    supervisor=None;heartbeat=None;previous={};primary=None
    try:
        source.atomic(OUT/"result.json",result)
        supervisor=runtime.supervisor(ROOT,OUT,OUT/"supervision",source.methods,
                                      method["protected_sha256"][runtime.SAMPLER])
        supervisor.TRACE.mkdir()
        for sig in (signal.SIGINT,signal.SIGTERM):previous[sig]=signal.signal(sig,supervisor.interrupted)
        candidate=threading.Thread(target=supervisor.heartbeat,daemon=True)
        candidate.start();heartbeat=candidate
        run(result,supervisor,method)
    except BaseException as error:
        primary=error;result.update(status="FAIL_WIDTH_TOPOLOGY_COMPARISON",native_width_comparison_passed=False,
                                   error=error_record("body",error))
    terminal=finish(result,supervisor,heartbeat,previous)
    if primary is not None:raise primary
    if terminal:raise terminal[0]
    require(result["status"]==PASS,"Physical qualification did not complete")
    return result

def validate_publication(result):
    require(result["source_head"]==os.environ["GITHUB_SHA"]and type(result["run_id"])is int
        and result["run_id"]==int(os.environ["GITHUB_RUN_ID"])and type(result["run_attempt"])is int
        and result["run_attempt"]==1,"Publication identity changed")
    require(all(result[k]is False for k in FALSE),"Unexpected physical/electrical claim")
    require(result["original_failure_preserved"]is True and result["source_graph_run"]==source.RUN
        and result["source_graph_head"]==source.HEAD and result["candidate_gds_sha256"]==source.GDS_SHA
        and result["complete_input_members"]==4103
        and result["consumed_view"]==source.VIEW,"Saved source scope changed")
    require(result["outputs"]=={n:h for n,h in inventory(OUT).items()if n!="result.json"},"Publication inventory changed")
    if result["status"]==PASS:
        require(result["topology_started"]is True and result["native_width_comparison_passed"]is True
            and result["terminal_finalization_complete"]is True and not result.get("terminal_errors"),"Incomplete generation success")
        require(result["candidate"]==source.validate_candidate(OUT),"Candidate result binding changed")
        require(len(result["commands"])==len(BUDGETS) and all(c["returncode"]==0 and c["supervision_failure"]is None
            and not c["process_group_cleanup"]["remaining_live"]for c in result["commands"]),"Failed owned command")
        smoke=source.read(source.regular(OUT,"runtime-smoke/result.json"))
        require(result["runtime_smoke"]==smoke and smoke["accepted"]is True,"Missing or changed runtime smoke")
        require(all(smoke[k]==source.APP_SHA for k in ("expected_appimage_sha256","appimage_before_sha256","appimage_after_sha256")),
                "Runtime AppImage identity changed")
        require([c["label"]for c in result["commands"]]==list(BUDGETS),"Owned stage order changed")
        require(result["restore"]==source.read(OUT/"restore.json"),"Restore result changed")
    else:
        require(result["status"].startswith("FAIL_")and result["native_width_comparison_passed"]is False,
                "Failed result implies generation success")

def publication_result(reservation):
    OUT.mkdir(parents=True,exist_ok=True)
    require(not OUT.is_symlink(),"Symlink output root")
    path=OUT/"result.json";result=None
    try:
        result=source.read(path)
        require(type(result)is dict,"Nonobject terminal result")
        if result.get("status")!=PASS:
            result.update(status="FAIL_INCOMPLETE_WIDTH_TOPOLOGY_EVIDENCE",native_width_comparison_passed=False)
            output_map(result)
        validate_publication(result)
    except BaseException as error:
        # Keep the original malformed/stale report byte-for-byte in the archive.
        # The independent publication summary cannot turn it into acceptance.
        result=initial(reservation)
        result.update(status="FAIL_MISSING_OR_INVALID_TERMINAL_REPORT",
          terminal_report_error=error_record("terminal_report_validation",error),
          terminal_report_present=path.exists(),original_terminal_bytes_unmodified=True)
        output_map(result);validate_publication(result)
    return result

def publish(result):
    source.publication_authorize();storage(True)
    try:source.methods()
    except BaseException as error:
        result.update(status="FAIL_PROTECTED_SOURCE_AT_PUBLICATION",native_width_comparison_passed=False,
                      publication_source_error=error_record("protected_source",error))
        output_map(result)
    validate_publication(result)
    require(not TRANSPORT.exists()and not TRANSPORT.is_symlink(),"Publication already attempted")
    TRANSPORT.mkdir(parents=True)
    stem=GROUP+"-"+os.environ["GITHUB_RUN_ID"]+"-1"
    direct=[];plan=[]
    def optional(suffix,member):
        path=OUT/member
        require(not path.is_symlink(),"Direct evidence symlink")
        if not path.exists():
            plan.append(dict(suffix=suffix,member=member,disposition="absent_not_fabricated"))
            return
        require(path.is_file(),"Nonregular direct evidence")
        size=path.stat().st_size;h=source.sha(path)
        record=dict(suffix=suffix,member=member,bytes=size,sha256=h,
          disposition="direct_and_archive"if size else"archive_only_empty")
        plan.append(record)
        if size:
            target=TRANSPORT/(stem+"."+suffix);shutil.copyfile(path,target)
            require(source.sha(target)==h and target.stat().st_size==size,"Direct bytes changed")
            direct.append(target)
    for suffix,member in (("native-synthetic.json","native-synthetic.json"),
                          ("native-controls.json","native-controls.json"),
                          ("expected-roots.json","expected-roots.json"),
                          ("restore.json","restore.json"),("runtime.json","runtime-smoke/result.json")):
        optional(suffix,member)
    driver_log={"present":False,"missing_not_fabricated":True}
    require(not DRIVER_LOG.is_symlink(),"Driver log symlink")
    if DRIVER_LOG.exists():
        require(DRIVER_LOG.is_file(),"Nonregular driver log")
        archived=OUT/"publication-driver.log"
        require(not archived.exists()and not archived.is_symlink(),"Driver archival copy already exists")
        shutil.copyfile(DRIVER_LOG,archived)
        require(source.sha(archived)==source.sha(DRIVER_LOG),"Driver archival bytes changed")
        driver_log=dict(present=True,bytes=archived.stat().st_size,sha256=source.sha(archived),
          member="publication-driver.log",raw_driver_log_in_complete_archive=True)
        optional("driver.log","publication-driver.log")
    else:
        plan.append(dict(suffix="driver.log",member="publication-driver.log",disposition="absent_not_fabricated"))
    # Keep the original terminal result byte-for-byte. The independent publication
    # summary includes the copied external log and the final complete output map.
    output_map(result);validate_publication(result)
    summary=TRANSPORT/(stem+".summary.json");source.atomic(summary,result)
    packed=pack(OUT,stem,TRANSPORT,512*1024**2)
    helper=publication_helpers.publication_helpers()
    files=helper.publication_files(TRANSPORT,summary,TRANSPORT/(stem+".parts.json"),packed)+direct
    publication_plan=TRANSPORT/(stem+".direct-publication-plan.json")
    source.atomic(publication_plan,dict(schema="complete-archive-direct-publication-v1",files=plan,
      zero_byte_files_preserved_in_archive=True,empty_bytes_replaced=False,
      summary_sha256=source.sha(summary),parts_sha256=source.sha(TRANSPORT/(stem+".parts.json"))))
    files.append(publication_plan)
    require(len({p.name for p in files})==len(files),"Duplicate publication assets")
    require(all(p.is_file()and not p.is_symlink()and p.stat().st_size>0 for p in files),
      "Empty direct upload refused")
    proof=dict(status="RUNNING_PUBLICATION",assets=[],source_head=os.environ["GITHUB_SHA"],
               run_id=int(os.environ["GITHUB_RUN_ID"]),engineering_accepted=False,driver_log=driver_log,
               direct_publication_plan_sha256=source.sha(publication_plan))
    tag,_=release.context(GROUP,os.environ)
    previous=publisher.release;primary=None
    publisher.release=helper.only_reserved(GROUP,os.environ,release.api)
    try:
        source.atomic(TRANSPORT/"publication.json",proof)
        for path in files:
            before=source.sha(path);proof["assets"].append(publisher.publish(path,tag))
            require(source.sha(path)==before,"Published bytes changed")
            source.atomic(TRANSPORT/"publication.json",proof)
        proof["status"]="PASS_COMPLETE_WIDTH_TOPOLOGY_EVIDENCE_PUBLICATION_ONLY"
    except BaseException as error:
        primary=error;proof.update(status="FAIL_PUBLICATION",error=error_record("publication",error))
    finally:
        publisher.release=previous
        try:source.atomic(TRANSPORT/"publication.json",proof)
        except BaseException as error:
            proof["terminal_save_error"]=error_record("publication_save",error)
            fallback("unsaved_geometry_publication",proof)
            if primary is None:primary=error
    if primary is not None:raise primary
    return proof

def main():
    p=argparse.ArgumentParser();p.add_argument("--preflight",action="store_true")
    p.add_argument("--publish-only",action="store_true");args=p.parse_args()
    if args.publish_only:
        source.publication_authorize();reservation=wait(GROUP,os.environ)
        publish(publication_result(reservation));return
    source.authorize();reservation=wait(GROUP,os.environ)
    if args.preflight:print(json.dumps(reservation,sort_keys=True));return
    main_run(reservation)

if __name__=="__main__":main()
