#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Supervised, reserved-only cloud readback of immutable saved native identities."""
import argparse
import contextlib
import json
import os
from pathlib import Path
import shutil
import signal
import sys
import threading
import traceback
import cdr_v59_tail_saved_identity as source
import cdr_v59_tail_access_runtime as runtime
import migrate_outputs_to_cloud as publisher
import ensure_cloud_tested_source_release as release
from cloud_chunked_results import pack
from wait_cloud_tested_source_release import wait

ROOT=source.ROOT
OUT=ROOT/"hw/soc/out/cloud-cdr-v59-tail-saved-identity"
TRANSPORT=ROOT/"hw/soc/out/cloud-cdr-v59-tail-saved-identity-publication"
APP_SHA="d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466"
SECONDS={"restore-complete-saved931-capsule":1200,"read-only-saved-native-identities":1200}
DIRECT=("archive-verification.json","original-identity.json","current-identity.json",
 "raw-hierarchy-diagnostic.json","raw-hierarchy-proof.json","original-comparator-rejection.json","identity-comparison.json","acquired-witness-controls.json")
EXPORTS={side+"-"+name+".json":path for side,files in source.SIDES.items()
 for name,path in files.items() if name in ("inventory","pins")}
PASS="PASS_SAVED_IDENTITY_READBACK_ORIGINAL_PHYSICAL_FAILURE_RETAINED"

def storage(stage):
    assert stage in ("initial","restore","identity","publication")
    size=0
    if OUT.exists():
        assert OUT.is_dir() and not OUT.is_symlink()
        for p in OUT.rglob("*"):
            assert not p.is_symlink() and (p.is_dir() or p.is_file())
            if p.is_file():size+=p.stat().st_size
    needed=max(4*1024**3,2*size+1024**3) if stage=="publication" else 8*1024**3
    free=shutil.disk_usage(ROOT).free
    assert free>=needed,("Insufficient evidence reserve",stage,free,needed)
    return {"stage":stage,"free_bytes":free,"required_bytes":needed,"current_evidence_bytes":size}

@contextlib.contextmanager
def tokenless():
    prior={k:os.environ.get(k) for k in ("GH_TOKEN","GITHUB_TOKEN")}
    try:
        for k in prior:os.environ.pop(k,None)
        yield
    finally:
        for k,v in prior.items():
            if v is None:os.environ.pop(k,None)
            else:os.environ[k]=v

def execute(supervisor,result,argv,label,without_tokens=False):
    assert label in SECONDS
    try:
        with tokenless() if without_tokens else contextlib.nullcontext():
            supervisor.supervised(argv,label,seconds=SECONDS[label],cwd=ROOT)
    finally:
        path=supervisor.TRACE/(label+".command.json")
        if path.exists():
            record=source.read_json(path)
            for stream in ("stdout","stderr"):
                p=supervisor.TRACE/(label+"."+stream)
                assert p.is_file() and not p.is_symlink()
                assert p.stat().st_size==record[stream+"_bytes"] and source.sha(p)==record[stream+"_sha256"]
            result["commands"].append(record);source.write(OUT/"result.json",result)
    assert record["returncode"]==0 and record["supervision_failure"] is None
    assert not record["process_group_cleanup"]["remaining_live"]
    return record

def collect_direct(result):
    # Failed/interrupted evidence is raw data, including truncated JSON writes.
    # Only a claimed successful acquisition must provide every parseable report.
    success=result["status"]==PASS
    files=[];bindings=[]
    def add(name,path,kind,expected=None):
        assert path.is_file() and not path.is_symlink()
        relative=path.relative_to(OUT).as_posix();digest=source.sha(path)
        assert result["outputs"].get(relative)==digest,"Direct evidence differs from terminal inventory"
        if success:
            try:source.read_json(path)
            except (ValueError,UnicodeError) as error:
                raise AssertionError("Malformed direct JSON cannot qualify successful readback: "+name) from error
            if expected is not None:assert digest==expected,"Successful saved-input export changed"
        files.append((name,path))
        bindings.append({"asset_suffix":name,"output_member":relative,"bytes":path.stat().st_size,
          "sha256":digest,"kind":kind,"json_syntax_checked_for_success":success,
          "qualified_as_success":success,"expected_saved_input_sha256":expected,
          "matches_original_saved_input":None if expected is None else digest==expected})
    for name in DIRECT:
        path=OUT/name
        assert not path.is_symlink()
        if success:assert path.exists(),"Missing successful direct report: "+name
        if path.exists():add(name,path,"acquisition_output")
    for name,member in EXPORTS.items():
        path=OUT/"restored"/member
        assert not path.is_symlink()
        if success:assert path.exists(),"Missing successful saved-input export: "+name
        if path.exists():add(name,path,"saved_input_export",source.expected_files()[member])
    return files,bindings

def validate_publication(result):
    assert result["source_head"]==os.environ["GITHUB_SHA"],"Publication source changed"
    assert type(result["run_id"]) is int and result["run_id"]==int(os.environ["GITHUB_RUN_ID"]),"Publication run changed"
    assert result["run_attempt"]==1,"Publication attempt changed"
    assert result["original_run"]==source.RUN and result["original_status"]=="FAIL_ADDITIVE_TAIL_WIRE_PHYSICAL"
    assert result["original_failure_preserved"] is True,"Original failure lost"
    for name in ("automatic_retry","geometry_generated","extraction_executed","simulation_executed",
      "physical_accepted","electrical_accepted","qualified_pex","full_phy_accepted"):
        assert result[name] is False,"Publication scope changed"
    if result["status"]==PASS:assert result["read_only_identity_verified"] is True
    else:
        assert result["status"].startswith(("FAIL_","RUNNING_")) and result["read_only_identity_verified"] is False
    actual={p.relative_to(OUT).as_posix():source.sha(p) for p in OUT.rglob("*")
      if p.is_file() and p!=OUT/"result.json"}
    assert result["outputs"]==actual,"Publication complete output map changed"

def publish(result):
    assert os.environ.get("GITHUB_RUN_ATTEMPT")=="1"
    assert OUT.is_dir() and not OUT.is_symlink() and not TRANSPORT.exists()
    storage("publication")
    report=OUT/"result.json";assert report.is_file() and not report.is_symlink()
    assert source.read_json(report)==result
    validate_publication(result)
    direct,direct_bindings=collect_direct(result)
    TRANSPORT.mkdir()
    stem=source.GROUP+"-"+os.environ["GITHUB_RUN_ID"]+"-1"
    summary=TRANSPORT/(stem+".summary.json")
    shutil.copyfile(report,summary);assert source.sha(summary)==source.sha(report)
    packed=pack(OUT,stem,TRANSPORT,512*1024**2)
    helper=source.publication_helpers()
    files=helper.publication_files(TRANSPORT,summary,TRANSPORT/(stem+".parts.json"),packed)
    for name,path in direct:
        dest=TRANSPORT/(stem+"."+name)
        shutil.copyfile(path,dest);assert source.sha(dest)==source.sha(path)
        files.append(dest)
    assert len({p.name for p in files})==len(files)
    proof={"status":"RUNNING_PUBLICATION","original_run_failure_preserved":True,"assets":[],
      "direct_asset_bindings":direct_bindings,"failed_direct_outputs_preserved_as_raw_bytes":result["status"]!=PASS}
    source.write(TRANSPORT/"publication.json",proof)
    tag,_=release.context(source.GROUP,os.environ)
    previous=publisher.release;publisher.release=helper.only_reserved(source.GROUP,os.environ,release.api)
    try:
        for path in files:
            proof["assets"].append(publisher.publish(path,tag));source.write(TRANSPORT/"publication.json",proof)
        proof["status"]="PASS_FULL_SAVED_READBACK_EVIDENCE_PUBLISHED"
    except BaseException as error:
        proof.update(status="FAIL_PUBLICATION",error=repr(error));raise
    finally:
        publisher.release=previous;source.write(TRANSPORT/"publication.json",proof)
    return proof

def run(result,supervisor,m):
    result["storage"].append(storage("restore"))
    execute(supervisor,result,[sys.executable,__file__,"--restore-worker"],"restore-complete-saved931-capsule")
    result["archive_verification_sha256"]=source.sha(OUT/"archive-verification.json")
    app=Path(os.environ["CLOUD_APPIMAGE"]).resolve()
    assert app.is_file() and not app.is_symlink() and source.sha(app)==APP_SHA
    launcher=runtime.launcher(ROOT,source.methods,m["protected_sha256"][runtime.PROBE])
    with tokenless():result["runtime_smoke"]=launcher.probe(app,APP_SHA,OUT/"runtime-smoke")
    source.write(OUT/"result.json",result)
    assert result["runtime_smoke"]["accepted"] is True
    result["storage"].append(storage("identity"))
    execute(supervisor,result,[app,"python",ROOT/"scripts/cdr_v59_tail_saved_identity_native.py",
      "--root",OUT/"restored","--out",OUT],"read-only-saved-native-identities",True)
    assert source.sha(app)==APP_SHA
    witness=source.read_json(OUT/"identity-comparison.json")
    assert witness["status"]=="PASS_READ_ONLY_SAVED_NATIVE_IDENTITIES_NO_TOPOLOGY_GATE_CHANGE"
    assert witness["physical_accepted"] is witness["electrical_accepted"] is witness["qualified_pex"] is False
    assert witness["topology_comparator_modified"] is False
    controls=source.read_json(OUT/"acquired-witness-controls.json")
    assert controls["status"]=="PASS_COMPLETE_ACQUIRED_WITNESS_MUTATION_CONTROLS"
    assert controls["positive_copies"]==len(controls["refusals"])==12
    assert controls["saved_native_inputs_mutated"] is False
    source.verify_inputs(OUT/"restored",source.expected_files());source.methods()
    result.update(status=PASS,read_only_identity_verified=True,identity_comparison_sha256=source.sha(OUT/"identity-comparison.json"))

def main():
    p=argparse.ArgumentParser();p.add_argument("--restore-worker",action="store_true");p.add_argument("--preflight",action="store_true")
    args=p.parse_args();m=source.authorize();assert not(args.restore_worker and args.preflight)
    if args.restore_worker:source.restore(OUT);return
    reservation=wait(source.GROUP,os.environ)
    if args.preflight:print(json.dumps(reservation));return
    initial=storage("initial")
    assert not OUT.exists() and not TRANSPORT.exists()
    OUT.mkdir(parents=True)
    supervisor=runtime.supervisor(ROOT,OUT,OUT/"supervision",source.methods,m["protected_sha256"][runtime.SAMPLER])
    supervisor.TRACE.mkdir()
    result={"status":"RUNNING_SAVED_IDENTITY_READBACK","run_id":int(os.environ["GITHUB_RUN_ID"]),
      "run_attempt":1,"source_head":os.environ["GITHUB_SHA"],"reservation":reservation,"commands":[],
      "storage":[initial],"original_run":source.RUN,"original_status":"FAIL_ADDITIVE_TAIL_WIRE_PHYSICAL",
      "original_failure_preserved":True,"read_only_identity_verified":False,"automatic_retry":False,
      "geometry_generated":False,"extraction_executed":False,"simulation_executed":False,
      "physical_accepted":False,"electrical_accepted":False,"qualified_pex":False,"full_phy_accepted":False}
    source.write(OUT/"result.json",result)
    previous={sig:signal.signal(sig,supervisor.interrupted) for sig in (signal.SIGINT,signal.SIGTERM)}
    heartbeat=threading.Thread(target=supervisor.heartbeat,daemon=True);heartbeat.start()
    try:run(result,supervisor,m)
    except BaseException as error:
        result.update(status="FAIL_SAVED_IDENTITY_READBACK",error=repr(error),traceback=traceback.format_exc(),read_only_identity_verified=False)
    finally:
        try:result["terminal_cleanup"]=supervisor.stop_process(supervisor.ACTIVE)
        except BaseException as error:
            result.update(status="FAIL_TERMINAL_CLEANUP",cleanup_error=repr(error),read_only_identity_verified=False)
        supervisor.STOP.set();heartbeat.join(timeout=5)
        for sig,handler in previous.items():signal.signal(sig,handler)
        if (OUT/"archive-verification.json").exists():
            try:result["saved_inputs_unchanged"]=source.verify_inputs(OUT/"restored",source.expected_files())
            except BaseException as error:
                result.update(status="FAIL_SAVED_INPUT_INTEGRITY",integrity_error=repr(error),read_only_identity_verified=False)
        result["outputs"]={str(p.relative_to(OUT)):source.sha(p) for p in OUT.rglob("*") if p.is_file() and p!=OUT/"result.json"}
        source.write(OUT/"result.json",result)
    publish(result)
    assert result["read_only_identity_verified"] is True,result["status"]

if __name__=="__main__":main()
