#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only existing-capture analysis and permanent reserved publication."""
import argparse, base64, hashlib, json, os, secrets, shutil, sys, traceback
from pathlib import Path
import cdr_v59_tail_headroom_admission as a
import cdr_v59_tail_headroom_rows as core
import cloud_cdr_v59_binding_rc as evidence
import ensure_cloud_tested_source_release as release
import wait_cloud_tested_source_release as waiter
import migrate_outputs_to_cloud as publisher
from cloud_chunked_results import pack, verify_parts

def group(case):
    a.need(case in a.CASES,"unknown case")
    return "cdr-v59-tail-headroom-"+case

def encode(value):
    return (json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+"\n").encode()

def write(path,value):
    path=Path(path)
    a.need(not path.is_symlink(),"linked output")
    temp=path.with_name(path.name+".tmp-"+secrets.token_hex(12))
    a.need(not temp.exists() and not temp.is_symlink(),"temporary name collision")
    with temp.open("xb")as stream:
        stream.write(encode(value));stream.flush();os.fsync(stream.fileno())
    os.replace(temp,path)

def inventory(root):
    a.need(root.is_dir()and not root.is_symlink(),"invalid evidence root")
    found={}
    for path in sorted(root.rglob("*")):
        a.need(not path.is_symlink()and(path.is_dir()or path.is_file()),"nonregular output")
        if path.is_file()and path!=root/"result.json":
            found[str(path.relative_to(root))]=dict(bytes=path.stat().st_size,sha256=a.sha(path))
    return found

def initial(case):
    return dict(status="RUNNING_SAVED_CAPTURE_READBACK",source_head=os.environ["GITHUB_SHA"],
        run_id=int(os.environ["GITHUB_RUN_ID"]),run_attempt=1,case=case,group=group(case),
        original_run=a.RUN,original_source=a.HEAD,new_simulation=False,new_extraction=False,
        geometry_changed=False,accepted=False,cdr_accepted=False,full_phy_accepted=False,
        qualified_pex=False,causality_proven=False,original_electrical_rejection=True,
        terminal_complete=False,terminal_errors=[])

def finish(root,result,primary):
    # Every finalization action runs; secondary failures never replace primary.
    result["status_before_terminal"]=result["status"]
    errors=[]
    try:
        a.methods()
    except BaseException as error:
        errors.append(dict(action="protected_sources",error=repr(error)))
    try:
        result["outputs"]=inventory(root)
    except BaseException as error:
        errors.append(dict(action="complete_output_inventory",error=repr(error)))
    result["active_primary_error"]=repr(primary)if primary else None
    result["terminal_errors"]=errors
    result["terminal_complete"]=not errors
    if errors:
        result["status"]="FAIL_READBACK_TERMINAL"
    try:
        write(root/"result.json",result)
    except BaseException as error:
        errors.append(dict(action="atomic_terminal_save",error=repr(error)))
        result["terminal_errors"]=errors
        result["terminal_complete"]=False
        result["status"]="FAIL_READBACK_TERMINAL_SAVE"
        try:
            result["outputs"]=inventory(root)
        except BaseException as refresh_error:
            errors.append(dict(action="post_save_failure_inventory",error=repr(refresh_error)))
        try:
            raw=encode(result)
            print("CDR_TAIL_HEADROOM_TERMINAL_FALLBACK "+json.dumps(dict(bytes=len(raw),
                sha256=hashlib.sha256(raw).hexdigest(),base64=base64.b64encode(raw).decode())),flush=True)
        except BaseException as fallback_error:
            errors.append(dict(action="fallback_encode_or_emit",error=repr(fallback_error)))
            # Existing body exception wins even if both preservation channels fail.
    if errors and primary is None:
        raise RuntimeError("Readback terminal preservation failed: "+repr(errors))

def run(case,m,root):
    a.cloud_guard(m);waiter.wait(group(case),os.environ)
    a.need(not root.exists()and not root.is_symlink(),"evidence destination exists")
    root.mkdir(parents=True)
    result=initial(case);primary=None
    write(root/"initial.json",result)
    work=a.ROOT/("cloud-"+group(case)+"-input")
    try:
        a.need(shutil.disk_usage(root).free>=12*1024**3,"insufficient cloud scratch")
        saved,report,restore=a.restore(case,work,m)
        write(root/"restore-proof.json",restore)
        t,d,contract,replayed=a.validate_native(saved,report)
        write(root/"original-measurements-replayed.json",replayed)
        diagnosis=core.diagnostic(t,d,report,contract)
        write(root/"diagnosis.json",diagnosis)
        frames=core.write_frames(root/"native-frames.bin",t,d,diagnosis,report,contract)
        write(root/"frames.json",frames)
        for path,record in restore["selected"].items():
            a.need(a.sha(saved/path)==record["sha256"],"source changed during readback")
        result.update(status="PASS_CURRENT_PVT_SAVED_ROW_READBACK_NOT_ACCEPTANCE",
            original_status=report["status"],original_data_passed=report["data_passed"],
            original_devices_passed=report["devices_passed"],original_VI_only_passed=report["vi"]["passed"],
            all_original_measurements_reproduced=True,
            original_wave_sha256=report["raw_capture"]["raw_sha256"],
            native_rows=report["raw_capture"]["header_rows"],frames=frames,
            diagnosis_sha256=a.sha(root/"diagnosis.json"))
        del t,d
        # Only disposable cloud copies are removed after a complete verified read.
        shutil.rmtree(work)
    except BaseException as error:
        primary=error
        result.update(status="FAIL_CURRENT_PVT_SAVED_ROW_READBACK",error=repr(error),
                      traceback=traceback.format_exc())
        raise
    finally:
        finish(root,result,primary)
    return result

def publication_result(root,case):
    path=a.regular(root,"result.json")
    r=a.read_json(path)
    a.need(r["source_head"]==os.environ["GITHUB_SHA"]
        and r["run_id"]==int(os.environ["GITHUB_RUN_ID"])and r["run_attempt"]==1,"publication identity")
    a.need(r["case"]==case and r["group"]==group(case)
        and r["original_run"]==a.RUN and r["original_source"]==a.HEAD,"publication producer")
    for flag in ("new_simulation","new_extraction","geometry_changed","accepted","cdr_accepted",
                 "full_phy_accepted","qualified_pex","causality_proven"):
        a.need(r[flag]is False,"publication scope widened")
    a.need(r["status"]in("PASS_CURRENT_PVT_SAVED_ROW_READBACK_NOT_ACCEPTANCE",
        "FAIL_CURRENT_PVT_SAVED_ROW_READBACK","FAIL_READBACK_TERMINAL","FAIL_READBACK_TERMINAL_SAVE",
        "FAIL_BEFORE_READBACK_TERMINAL"),"nonterminal publication")
    a.need(r["original_electrical_rejection"]is True,"original rejection lost")
    a.need(r["outputs"]==inventory(root),"output evidence changed or missing")
    if r["status"].startswith("PASS_"):
        a.need(r["terminal_complete"]is True and r["terminal_errors"]==[]
            and r["all_original_measurements_reproduced"]is True,"incomplete success")
        a.need(r["original_data_passed"]is False and r["original_devices_passed"]is False
            and r["original_VI_only_passed"]is(case=="cold_late"),"original verdict changed")
        required={"initial.json","restore-proof.json","original-measurements-replayed.json",
                  "diagnosis.json","native-frames.bin","frames.json"}
        a.need(required<=set(r["outputs"]),"complete success outputs missing")
        a.need(r["diagnosis_sha256"]==r["outputs"]["diagnosis.json"]["sha256"],"diagnosis join")
        diagnosis=a.read_json(a.regular(root,"diagnosis.json"))
        frames=a.read_json(a.regular(root,"frames.json"))
        replay=a.read_json(a.regular(root,"original-measurements-replayed.json"))
        restore=a.read_json(a.regular(root,"restore-proof.json"))
        a.need(frames==r["frames"] and frames["complete"] is True,"frame proof join")
        a.need(frames["sha256"]==r["outputs"]["native-frames.bin"]["sha256"]
            and frames["bytes"]==r["outputs"]["native-frames.bin"]["bytes"],"frame bytes join")
        a.need(frames["columns"]==["native_row","time",*diagnosis["selected_vectors"]]
            and frames["frame_rows"]==diagnosis["frame_rows"]
            and type(frames["rows"]) is int and frames["rows"]==len(frames["frame_rows"])>0
            and frames["dtype"]=="<f8"
            and frames["bytes"]==frames["rows"]*len(frames["columns"])*8,"frame schema join")
        a.need(frames["diagnosis_sha256"]==core.digest(core.canonical(diagnosis)),
            "canonical diagnosis join")
        a.need(diagnosis["original_capture"]["raw_sha256"]==r["original_wave_sha256"]
            and restore["selected"]["native/native/wave.raw"]["sha256"]==r["original_wave_sha256"],
            "original capture join")
        a.need(restore["all_original_outputs_verified"] is True
            and restore["all_member_hashes_verified"]==3934,"complete original inventory join")
        a.need(replay["readback_only"] is True and replay["all_numerical_gates_unchanged"] is True
            and replay["original_status"]==r["original_status"],"original measurement replay join")
        a.need(all(frames[k] is False and diagnosis[k] is False for k in
            ("electrical_accepted","cdr_accepted","full_phy_accepted")),"diagnostic acceptance widened")
    return r

def publish(root,case,m):
    a.cloud_guard(m);waiter.wait(group(case),os.environ)
    a.need(not root.is_symlink(),"linked evidence root")
    root.mkdir(parents=True,exist_ok=True)
    if not (root/"result.json").exists():
        r=initial(case)
        r.update(status="FAIL_BEFORE_READBACK_TERMINAL",outputs=inventory(root),
            terminal_errors=[dict(action="terminal_result",error="Result absent; retained original partial outputs")])
        write(root/"result.json",r)
    before=publication_result(root,case)
    transport=a.ROOT/"hw/soc/out"/(group(case)+"-publication")
    transport.mkdir(parents=True,exist_ok=False)
    stem=group(case)+"-"+os.environ["GITHUB_RUN_ID"]+"-1"
    summary=transport/(stem+".summary.json")
    shutil.copyfile(root/"result.json",summary)
    a.need(a.sha(summary)==a.sha(root/"result.json"),"summary copy changed")
    a.need(shutil.disk_usage(transport).free>=sum(p.stat().st_size for p in root.rglob("*")if p.is_file())+1024**3,
        "insufficient cloud publication storage")
    manifest=pack(root,stem,transport,512*1024**2);verify_parts(manifest,transport)
    files=evidence.publication_files(transport,summary,transport/(stem+".parts.json"),manifest)
    if (root/"diagnosis.json").is_file():
        direct=transport/(stem+".diagnosis.json");shutil.copyfile(root/"diagnosis.json",direct)
        a.need(a.sha(direct)==a.sha(root/"diagnosis.json"),"direct diagnosis changed")
        files.append(direct)
    a.need(publication_result(root,case)==before,"evidence changed while packing")
    tag,head=release.context(group(case),os.environ)
    lookup=evidence.only_reserved(group(case),os.environ,release.api)
    reserved=lookup(tag)
    previous=publisher.release
    def same_reserved(requested):
        r=lookup(requested)
        a.need(r["id"]==reserved["id"],"reserved release replaced")
        return r
    publisher.release=same_reserved
    proof=dict(status="RUNNING_PUBLICATION",release_id=reserved["id"],tag=tag,
        source_head=head,case=case,assets=[],accepted=False)
    primary=None
    try:
        for path in files:
            before_hash=a.sha(path);same_reserved(tag)
            item=publisher.publish(path,tag)
            a.need(a.sha(path)==before_hash,"upload source changed")
            proof["assets"].append(item)
        hosted=same_reserved(tag)
        expected={p.name:(p.stat().st_size,a.sha(p))for p in files}
        actual={x["name"]:(x["size"],x.get("digest","")[7:])for x in hosted["assets"]}
        a.need(len(actual)==len(hosted["assets"])and actual==expected,"complete publication census differs")
        proof.update(status="PASS_COMPLETE_RESERVED_READBACK_PUBLICATION_NOT_ACCEPTANCE",
                     original_status=before["status"],complete_asset_census_verified=True)
    except BaseException as error:
        primary=error;proof.update(status="FAIL_READBACK_PUBLICATION",error=repr(error));raise
    finally:
        publisher.release=previous
        try:
            write(transport/"publication.json",proof)
        except BaseException as error:
            proof["status_before_terminal"]=proof["status"]
            proof["status"]="FAIL_READBACK_PUBLICATION_TERMINAL_SAVE"
            proof["terminal_errors"]=[dict(action="atomic_publication_save",error=repr(error))]
            try:
                print("CDR_TAIL_HEADROOM_PUBLICATION_FALLBACK "+json.dumps(dict(
                    primary_error=repr(primary)if primary else None,save_error=repr(error),proof=proof)),flush=True)
            except BaseException as fallback_error:
                proof["terminal_errors"].append(dict(action="fallback_encode_or_emit",error=repr(fallback_error)))
                # The active upload exception wins; otherwise the atomic save error wins.
            if primary is None:raise
    return proof

def main():
    p=argparse.ArgumentParser();p.add_argument("--case",required=True,choices=a.CASES)
    mode=p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--readback",action="store_true");mode.add_argument("--publish",action="store_true")
    args=p.parse_args();m=a.methods()
    root=a.ROOT/("cloud-"+group(args.case))
    result=publish(root,args.case,m)if args.publish else run(args.case,m,root)
    print(json.dumps(result,sort_keys=True),flush=True)
if __name__=="__main__":
    main()
