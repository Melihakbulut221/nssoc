#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only restoration and bounded actual built-engine native database probe."""
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
import mainchip_built_engine_runtime_contract as c
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
        read("actions/runs/"+str(c.ENGINE_RUN)+"/jobs?per_page=100"),
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
    shutil.copyfile(c.secure_file(ROOT,c.PREFIX+"runtime-dependencies.json"),work/"runtime-dependencies.json")

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

def probe():
    ctx=c.context(os.environ);m=c.method(ROOT)
    c.require(m["native_probe_authorized"] is True,"native runtime probe not authorized")
    c.require(subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==ctx["source"],"checkout identity")
    work=owned_work(ctx,True);out=work/"out";out.mkdir()
    report=dict(schema="built-engine-runtime-host-v1",source=ctx["source"],status="IN_PROGRESS",
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
        c.require(inner["status"]=="PASS_BUILT_ELF_RUNTIME_AND_ACTUAL_CHIP_READ_ONLY_CENSUS" and not inner["terminal_errors"],"native runtime failure")
        c.require(all(x["returncode"]==0 and x["timed_out"] is False for x in inner["commands"]),"native command failure")
    try:
        for sig in (signal.SIGINT,signal.SIGTERM):handlers[sig]=signal.signal(sig,interrupted)
        proof=reservation.wait(c.GROUP,os.environ)
        c.require(not proof["existing_assets"],"release not empty before native probe")
        write(out/"release-reservation.json",proof)
        shutil.copyfile(ROOT/c.METHOD,out/"method.json")
        shutil.copyfile(ROOT/"runtime-probe-controls.json",out/"runtime-probe-controls.json")
        c.require(shutil.disk_usage(work).free>=c.LIMITS["min_free_disk_bytes"],"scratch disk budget")
        # Reservation precedes every archive/dependency retrieval and every native action.
        restore_engine(work,out);restore_input(work,out)
        source=work/"source";source.mkdir()
        for p in [*m["protected"],c.METHOD]:
            destination=source/p;destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(c.secure_file(ROOT,p),destination)
        c.method(source);projected=True
        shutil.copyfile(ROOT/"scripts/mainchip_built_engine_runtime_inner.py",work/"inner.py")
        command("immutable-image-pull",["docker","pull",c.IMAGE],1800)
        image=c.decode(command("image-inspect",["docker","image","inspect",c.IMAGE]))[0]
        c.validate_image(image)
        identity=create_owned(ctx,work,report,command,c.create_argv(ctx,work,os.getuid(),os.getgid()))
        info=inspect_one(identity);c.validate_container(info,ctx,work);write(out/"container-initial.json",info)
        command("owned-container-start",["docker","start","--attach",identity],c.LIMITS["container_seconds"])
    except BaseException as exc:
        primary=exc;report["failure"]=c.error_record("built-engine-runtime-probe",exc)
    finally:
        cleanup_owned(ctx,work,report,identity,report["creation_attempted"],inspect_one,command)
        c.attempt(report,"checkout-source-unchanged",lambda:c.method(ROOT))
        if projected:c.attempt(report,"projected-source-unchanged",lambda:c.method(work/"source"))
        if report["creation_attempted"]:c.attempt(report,"native-terminal-contract",terminal_native)
        for sig,old in handlers.items():c.attempt(report,"restore-signal-"+str(sig),lambda sig=sig,old=old:signal.signal(sig,old))
        report["elapsed_seconds"]=time.monotonic()-started
        report["status"]=("PASS_BUILT_ENGINE_READ_ONLY_NATIVE_PROBE"
            if identity is not None and primary is None and not report["terminal_errors"]else "FAIL_BUILT_ENGINE_RUNTIME_PROBE")
        c.finish_record(out/"host-result.json",report,"FAIL_BUILT_ENGINE_RUNTIME_PROBE",primary)
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
    ctx=c.context(os.environ); c.method(ROOT)
    work=owned_work(ctx); out=work/"out"; out.mkdir(exist_ok=True)
    proof=reservation.wait(c.GROUP,os.environ)
    write(out/"publication-availability.json",terminal_availability(out))
    files={}
    for p in sorted(out.rglob("*")):
        c.require(not p.is_symlink(),"output symlink")
        if p.is_file():files[p.relative_to(out).as_posix()]=fingerprint(p)
    write(out/"outputs.json",dict(source=ctx["source"],files=files,physical_acceptance=False))
    archive=work/"runtime-probe-evidence.tar.gz"
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
            p=work/("runtime-probe-evidence.tar.gz.part%03d"%i);p.write_bytes(raw)
            parts.append(dict(name=p.name,**fingerprint(p)));i+=1
    write(out/"parts.json",dict(archive=archive_receipt,parts=parts))
    tag="cloud-results-"+ctx["token"]+"-"+c.GROUP
    uploads=[out/x for x in ("host-result.json","inner-result.json","method.json",
        "runtime-probe-controls.json","api-identity-census.json","release-reservation.json",
        "outputs.json","parts.json","container-initial.json","container-terminal.json",
        "runtime-observed.json","engine-restoration.json","input-restoration.json","engine-source-envelope.json","publication-availability.json") if (out/x).is_file()]
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
    write(out/"publication.json",dict(status="PASS_PERMANENT_RELEASE_PUBLICATION",
        release_id=info["id"],tag=tag,source=ctx["source"],assets=uploaded,
        native_archives_stay_in_cloud=True))
    print(json.dumps(dict(release_id=info["id"],tag=tag,assets=len(uploaded)),sort_keys=True))
    return 0

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("mode",choices=("probe","publish"));a=p.parse_args()
    sys.exit(probe()if a.mode=="probe"else publish())
