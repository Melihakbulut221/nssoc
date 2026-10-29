#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only restoration, unchanged four-phase preparation and frozen continuation."""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tarfile
import time
import mainchip_fixed_engine_route_prefix_contract as c
from mainchip_witness_engine_build import (
    fingerprint, execute_command, create_owned, cleanup_owned, terminal_availability)
import wait_cloud_tested_source_release as reservation
ROOT=Path(__file__).resolve().parent.parent
def write(path,value):c.atomic_record(path,value)

def owned_work(ctx,create=False):
    base=Path(os.environ["RUNNER_TEMP"])
    c.require(base.is_absolute() and not base.is_symlink(),"runner temp")
    work=base/(c.GROUP+"-"+ctx["token"])
    c.require(not work.is_symlink(),"work symlink")
    if create:
        work.mkdir(mode=0o700);write(work/"owner.json",ctx)
    c.require(c.decode((work/"owner.json").read_bytes())==ctx,"owned work identity")
    return work

def restore_engine(work,out):
    from route_cloud_newer_postcts import fetch
    expected=c.expected_engine(ROOT);read=reservation.release.api
    envelope=c.engine_envelope(read("actions/runs/"+str(c.ENGINE_RUN)),
        read("actions/runs/"+str(c.ENGINE_RUN)+"/attempts/1/jobs?per_page=100"),
        read("releases/"+str(c.ENGINE_RELEASE)),read("git/ref/tags/"+c.ENGINE_TAG),expected["release"])
    write(out/"engine-source-envelope.json",envelope)
    part=expected["parts"]["parts"][0];archive=work/part["name"]
    url="https://github.com/"+c.REPOSITORY+"/releases/download/"+c.ENGINE_TAG+"/"+part["name"]
    fetch(url,part["sha256"],archive)
    c.require(fingerprint(archive)==expected["parts"]["archive"],"engine archive identity")
    with archive.open("rb")as stream:
        inventory=c.engine_extract(stream,work/"engine",expected["files"])
    write(out/"engine-restoration.json",inventory)
    c.require(fingerprint(work/"engine/openroad")==c.ENGINE,"restored ELF")
    (work/"engine/openroad").chmod(0o500)
    shutil.copyfile(c.secure_file(ROOT,c.RUNTIME_SOURCE),work/"runtime-dependencies.json")
    shutil.copyfile(work/"runtime-dependencies.json",out/"runtime-dependencies.json")

def restore_input(work,out):
    import mainchip_signal_repair_readback as old
    from route_cloud_newer_postcts import fetch
    read=reservation.release.api
    name=f"cloud-results-{old.RUN}-1-{old.GROUP}"
    envelope=old.live_envelope(read("actions/runs/"+str(old.RUN)),
        read("actions/runs/"+str(old.RUN)+"/jobs?per_page=100"),
        read("releases/"+str(old.RELEASE)),read("git/ref/tags/"+name))
    transport=work/"input-transport";transport.mkdir()
    stem=f"{old.GROUP}-{old.RUN}-1";url="https://github.com/"+c.REPOSITORY+"/releases/download/"+name+"/"
    for suffix,h in ((".summary.json",old.SUMMARY),(".parts.json",old.PARTS)):
        fetch(url+stem+suffix,h,transport/("input"+suffix))
        c.require((transport/("input"+suffix)).read_bytes()==c.secure_file(ROOT,old.PREFIX+suffix).read_bytes(),"original input JSON")
    report=old.expected_report((transport/"input.summary.json").read_bytes())
    manifest=old.manifest((transport/"input.parts.json").read_bytes())
    for part in manifest["parts"]:fetch(url+part["name"],part["sha256"],transport/part["name"])
    expected=dict(report["outputs"],**{"result.json":old.SUMMARY})
    selected=tuple(old.SELECTED)+(c.INPUT_MEMBER,)
    c.require(len(set(selected))==len(selected) and expected[c.INPUT_MEMBER]==c.INPUT["sha256"],"explicit original ODB selection")
    inventory=old.audit_extract(manifest,transport,transport/"selected",expected,selected)
    c.require(len(inventory["all_original_files"])==94 and inventory["complete_original_inventory_verified_before_analysis"] is True,"original 94-file inventory")
    source=transport/"selected"/c.INPUT_MEMBER;c.require(fingerprint(source)==c.INPUT,"restored original ODB")
    shutil.copyfile(source,work/"input.odb")
    write(out/"input-restoration.json",dict(envelope=envelope,inventory=inventory,
        original_failed_result_preserved=True,summary_sha256=old.SUMMARY,parts_sha256=old.PARTS))


def restore_routes(work,out):
    import cloud_mainchip_fixed_clock_signal_repair as original
    oldout,oldtransport=original.OUT,original.TRANSPORT
    try:
        original.OUT=out;original.TRANSPORT=work/"routing-inputs"
        original.restore_worker()
        proof=original.restored_inputs()
    finally:
        original.OUT,original.TRANSPORT=oldout,oldtransport
    read=reservation.release.api
    tag="cloud-results-39910632183-1-mainchip-route12-global"
    live_tag=read("git/ref/tags/"+tag);release=read("releases/421512828")
    c.require(live_tag["object"]["type"]=="commit" and live_tag["object"]["sha"]==
        "5e573fdfb54aa62321ce76f930f9b5a837445416","historical global tag changed")
    c.require(release["id"]==421512828 and release["tag_name"]==tag
        and {a["id"]for a in release["assets"]}=={668190800,668190900,668191002},"historical global release")
    c.require(proof["clock_proof"]["inventory"]["complete_original_inventory_verified_before_analysis"] is True
              and len(proof["clock_proof"]["inventory"]["all_original_files"])==107,"complete clock donor archive")
    write(out/"routing-source-envelope.json",dict(clock_run=40223193329,clock_release=423594261,
        global_run=39910632183,global_report_source="639b5b8aee64347620420c1f7f60001255a754b5",
        global_actual_tag=live_tag,global_release=release,
        legacy_global_tag_differs_from_original_run_source=True,
        historical_summary_parts_full_member_and_run_binding_preserved=True,
        historical_tag_retargeted=False,original_three_marker_input_still_unaccepted=True))

def freeze_native(work,out):
    # This is the complete native continuation projection. Original transport archives
    # retain their separate authenticated releases; daemon ownership and terminal logs
    # are not native inputs and are preserved in the outer evidence capsule.
    roots=("source","routing-inputs/clock/selected","routing-inputs/global",
           "input-transport/selected","engine/openroad","input.odb","runtime-dependencies.json","out/work")
    files={}
    for relative in roots:
        p=work/relative
        c.require(p.exists() and not p.is_symlink(),"native projection missing")
        members=sorted(p.rglob("*")) if p.is_dir() else [p]
        for f in members:
            c.require(not f.is_symlink() and (f.is_file() or f.is_dir()),"native projection special entry")
            if f.is_file():
                key=f.relative_to(work).as_posix();c.require(key not in files,"duplicate native projection member")
                files[key]=fingerprint(f)
    c.require(files["engine/openroad"]==c.ENGINE and files["input.odb"]==c.INPUT,"frozen native identities")
    c.require("out/work/fixed.odb" in files and "out/work/repair.tcl" in files,"prepared workspace absent")
    manifest=dict(schema="mainchip-prepared-native-workspace-v1",canonical_root="/work",
        roots=list(roots),files=files,original_engine=c.ENGINE,original_input=c.INPUT,
        source_inventory_method=fingerprint(work/"source"/c.METHOD),
        native_routing_executed=False,observer_equivalence_qualified=False,physical_acceptance=False)
    write(out/"frozen-prefix-inventory.json",manifest)
    total=sum(x["bytes"]for x in files.values())
    c.require(shutil.disk_usage(work).free>=total+2*1024**3,"native freeze disk budget")
    archive=out/"frozen-native-workspace.tar.gz"
    with tarfile.open(archive,"w:gz")as tar:
        for name in sorted(files):tar.add(work/name,arcname=name,recursive=False)
    c.require(all(fingerprint(work/name)==row for name,row in files.items()),"native workspace changed while freezing")
    proof=dict(status="PASS_FROZEN_PREPARED_NATIVE_WORKSPACE_NOT_ROUTING_ACCEPTANCE",
        archive=fingerprint(archive),inventory=fingerprint(out/"frozen-prefix-inventory.json"),
        files=len(files),unpacked_bytes=total,native_routing_executed=False,
        native_artifacts_stay_in_cloud=True,physical_acceptance=False)
    write(out/"frozen-prefix.json",proof)
    return proof


def probe():
    ctx=c.context(os.environ);m=c.method(ROOT)
    c.authorize_prefix(m)
    c.require(subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==ctx["source"],"checkout identity")
    work=owned_work(ctx,True);out=work/"out";out.mkdir()
    report=dict(schema="fixed-engine-route-prefix-host-v1",source=ctx["source"],status="IN_PROGRESS",
                physical_acceptance=False,observer_equivalence_qualified=False,native_routing_executed=False,
                commands=[],terminal_errors=[],creation_attempted=False)
    primary=None;identity=None;handlers={};started=time.monotonic();projected=False
    def command(label,argv,timeout=120):return execute_command(report,out,label,argv,timeout)
    def inspect_one(value):return c.decode(subprocess.check_output(["docker","inspect",value],timeout=30))[0]
    def interrupted(sig,frame):raise RuntimeError("owned native probe interrupted by signal "+str(sig))
    def terminal_native():
        info=report["container_terminal"];state=info["State"]
        c.require(not state["Running"] and not state["OOMKilled"] and state["ExitCode"]==0 and not state["Error"],"native container failure")
        inner=c.decode((out/"inner-result.json").read_bytes())
        c.require(inner["status"]=="PASS_BUILT_ELF_ACTUAL_SHARED_PREFIX" and not inner["terminal_errors"],"native runtime failure")
        c.require(all(x["returncode"]==0 and x["timed_out"] is False for x in inner["commands"]),"native command failure")
        expected=c.expected_engine(ROOT)
        c.runtime_match(expected["runtime"],c.decode((out/"runtime-observed.json").read_bytes()))
        c.require(fingerprint(work/"runtime-dependencies.json")==fingerprint(c.secure_file(ROOT,c.RUNTIME_SOURCE)),"runtime expectation file changed")
    try:
        for sig in (signal.SIGINT,signal.SIGTERM):handlers[sig]=signal.signal(sig,interrupted)
        proof=reservation.wait(c.GROUP,os.environ)
        c.validate_reservation(proof,ctx,True)
        write(out/"release-reservation.json",proof)
        shutil.copyfile(ROOT/c.METHOD,out/"method.json")
        shutil.copyfile(c.secure_file(ROOT,c.SOURCE_ADMISSION),out/"prefix-source-admission.json")
        report["runtime_qualification"]=c.runtime_qualification(ROOT)
        write(out/"runtime-qualification.json",report["runtime_qualification"])
        report["current_source_controls"]=c.control_evidence(ROOT,ctx)
        write(out/"current-source-controls.json",report["current_source_controls"])
        for name,expected in report["current_source_controls"].items():
            c.require(Path(name).name==name and name.endswith("-controls.json"),"source control output name")
            shutil.copyfile(c.secure_file(ROOT,name),out/name)
            c.require(fingerprint(out/name)==expected,"source control copy changed")
        c.require(shutil.disk_usage(work).free>=c.LIMITS["min_free_disk_bytes"],"scratch disk budget")
        # Reservation precedes every archive/dependency retrieval and every native action.
        restore_engine(work,out);restore_input(work,out);restore_routes(work,out)
        source=work/"source";source.mkdir()
        for p in [*m["protected"],c.METHOD]:
            destination=source/p;destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(c.secure_file(ROOT,p),destination)
        c.method(source);c.runtime_qualification(source);projected=True
        shutil.copyfile(ROOT/"scripts/mainchip_fixed_engine_route_prefix_inner.py",work/"inner.py")
        command("immutable-image-pull",["docker","pull",c.IMAGE],1800)
        image=c.decode(command("image-inspect",["docker","image","inspect",c.IMAGE]))[0]
        c.validate_image(image)
        identity=create_owned(ctx,work,report,command,c.create_argv(ctx,work,os.getuid(),os.getgid()))
        info=inspect_one(identity);c.validate_container(info,ctx,work);write(out/"container-initial.json",info)
        command("owned-container-start",["docker","start","--attach",identity],c.LIMITS["container_seconds"])
        # Require the actual native terminal contract before creating a reusable prefix.
        native=c.decode((out/"native-prefix-result.json").read_bytes())
        c.require(native["status"]=="PASS_ACTUAL_BUILT_ENGINE_SHARED_PREFIX" and not native["terminal_errors"],"incomplete prefix cannot be frozen")
        report["frozen_native_workspace"]=freeze_native(work,out)
    except BaseException as exc:
        primary=exc;report["failure"]=c.error_record("built-engine-route-prefix",exc)
    finally:
        cleanup_owned(ctx,work,report,identity,report["creation_attempted"],inspect_one,command)
        c.attempt(report,"checkout-source-unchanged",lambda:c.method(ROOT))
        if projected:c.attempt(report,"projected-source-unchanged",lambda:c.method(work/"source"))
        if report["creation_attempted"]:c.attempt(report,"native-terminal-contract",terminal_native)
        for sig,old in handlers.items():c.attempt(report,"restore-signal-"+str(sig),lambda sig=sig,old=old:signal.signal(sig,old))
        report["elapsed_seconds"]=time.monotonic()-started
        report["status"]=("PASS_ACTUAL_ROUTING_PREFIX_READY_NO_ROUTING"
            if identity is not None and primary is None and not report["terminal_errors"]else "FAIL_ACTUAL_ROUTING_PREFIX")
        c.finish_record(out/"host-result.json",report,"FAIL_ACTUAL_ROUTING_PREFIX",primary)
    return 0 if report["status"].startswith("PASS_")else 1


def publish_asset(path, ctx, release_id, read, upload):
    c.require(path.is_file() and not path.is_symlink(),"publication regular file")
    expected=fingerprint(path);tag="cloud-results-"+ctx["token"]+"-"+c.GROUP
    def current():
        info=read("releases/tags/"+tag);ref=read("git/ref/tags/"+tag)
        reservation.release.validate_release(info,ref,tag,ctx["source"])
        c.require(info["id"]==release_id,"reserved release identity")
        return info
    info=current();same=[a for a in info["assets"] if a["name"]==path.name]
    reused=bool(same)
    if same:
        c.require(len(same)==1 and same[0]["size"]==expected["bytes"]
                  and same[0]["digest"]=="sha256:"+expected["sha256"],
                  "existing asset conflict")
    else:
        upload(tag,path)
    # Each mutation is preceded by the exact reserved source/tag/ID check.
    info=current();same=[a for a in info["assets"] if a["name"]==path.name]
    c.require(len(same)==1 and same[0]["size"]==expected["bytes"]
              and same[0]["digest"]=="sha256:"+expected["sha256"],
              "published asset mismatch")
    return dict(name=path.name,**expected,reused_identical=reused)


def publish():
    ctx=c.context(os.environ)
    work=owned_work(ctx); out=work/"out"; out.mkdir(exist_ok=True)
    source_error=None
    try:c.method(ROOT)
    except BaseException as exc:source_error=exc
    # Preservation is separately authorized by the exact current context, owned
    # workspace and reserved source/tag. Source failure never becomes build PASS.
    try:
        proof=reservation.wait(c.GROUP,os.environ);c.validate_reservation(proof,ctx,False)
        availability=terminal_availability(out)
        availability.update(source_integrity_validated=source_error is None,native_accepted=False,
          source_integrity_error=None if source_error is None else c.error_record("publication-source-integrity",source_error))
        write(out/"publication-availability.json",availability)
        optional=("host-result.json","inner-result.json","method.json","native-prefix-result.json",
          "release-reservation.json","container-initial.json","container-terminal.json",
          "runtime-dependencies.json","runtime-observed.json","engine-restoration.json",
          "input-restoration.json","engine-source-envelope.json","current-source-controls.json",
          "runtime-qualification.json","prefix-source-admission.json","source-admission.json",
          "routing-source-envelope.json","frozen-prefix.json","frozen-prefix-inventory.json",
          "publication-availability.json")
        # Current source-control names are supplied by the contract. Discover their
        # preserved copies without re-running failed source admission during publication.
        optional+=tuple(sorted(p.name for p in out.iterdir()
          if p.name.endswith("-controls.json") and p.name not in optional))
        plan=c.direct_plan(out,optional);write(out/"direct-publication-plan.json",plan)
        files={}
        for p in sorted(out.rglob("*")):
            c.require(not p.is_symlink(),"output symlink")
            if p.is_file():files[p.relative_to(out).as_posix()]=fingerprint(p)
        write(out/"outputs.json",dict(source=ctx["source"],files=files,physical_acceptance=False))
        archive=work/"route-prefix-evidence.tar.gz"
        with tarfile.open(archive,"w:gz")as tar:
            for p in sorted(out.iterdir()):
                c.require(not p.is_symlink(),"archive symlink")
                tar.add(p,arcname=p.name,recursive=True)
        archive_receipt=fingerprint(archive)
        parts=[]
        with archive.open("rb")as stream:
            i=0
            while True:
                raw=stream.read(512*1024**2)
                if not raw:break
                p=work/("route-prefix-evidence.tar.gz.part%03d"%i);p.write_bytes(raw)
                parts.append(dict(name=p.name,**fingerprint(p)));i+=1
        write(out/"parts.json",dict(archive=archive_receipt,parts=parts))
        tag="cloud-results-"+ctx["token"]+"-"+c.GROUP
        uploads=[out/r["name"]for r in plan["files"]if r["disposition"]=="direct"]
        uploads.extend(out/x for x in ("outputs.json","parts.json","direct-publication-plan.json"))
        uploads.extend(work/p["name"]for p in parts)
        planned={p.name for p in uploads}
        c.require(len(planned)==len(uploads),"duplicate publication filename")
        c.require({x["name"] for x in proof["existing_assets"]} <= planned,"unexpected reserved asset")
        def upload(tag,path):
            subprocess.run(["gh","release","upload",tag,str(path),"--repo",c.REPOSITORY],check=True,timeout=1800)
        uploaded=[publish_asset(p,ctx,proof["release_id"],reservation.release.api,upload) for p in uploads]
        info=reservation.release.api("releases/tags/"+tag)
        ref=reservation.release.api("git/ref/tags/"+tag)
        reservation.release.validate_release(info,ref,tag,ctx["source"])
        byname={a["name"]:a for a in info["assets"]}
        c.require(set(byname)=={x["name"]for x in uploaded},"release asset census")
        for row in uploaded:
            actual=byname[row["name"]]
            c.require(actual["size"]==row["bytes"] and actual["digest"]=="sha256:"+row["sha256"],
                      "published asset mismatch")
        write(out/"publication.json",dict(status="PASS_PERMANENT_RELEASE_PUBLICATION"if source_error is None else"PASS_PERMANENT_FAILURE_EVIDENCE_ONLY",
            source_integrity_validated=source_error is None,native_accepted=False,
            release_id=info["id"],tag=tag,source=ctx["source"],assets=uploaded,
            native_archives_stay_in_cloud=True))
        print(json.dumps(dict(release_id=info["id"],tag=tag,assets=len(uploaded)),sort_keys=True))
    except BaseException as publication_error:
        if source_error is not None:
            record=dict(status="FAIL_SOURCE_INTEGRITY_AND_PUBLICATION",native_accepted=False,
              source_error=c.error_record("source",source_error),publication_error=c.error_record("publication",publication_error))
            try:write(out/"publication-failure.json",record)
            except BaseException:
                try:print("FIXED_PREFIX_PUBLICATION_FALLBACK "+json.dumps(record,sort_keys=True),flush=True)
                except BaseException:pass
            raise source_error
        raise
    if source_error is not None:raise source_error
    return 0

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("mode",choices=("probe","publish"));a=p.parse_args()
    sys.exit(probe()if a.mode=="probe"else publish())
