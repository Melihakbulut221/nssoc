#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""GitHub-hosted, owned native engine build with permanent failure evidence."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tarfile
import time
import traceback
import mainchip_witness_engine_build_contract as c
import mainchip_two_signal_internal_witness as observer
import wait_cloud_tested_source_release as reservation

ROOT = Path(__file__).resolve().parent.parent

def write(path, data):
    c.atomic_record(path, data)

def fingerprint(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for raw in iter(lambda: f.read(1024*1024), b""):
            h.update(raw)
    return dict(bytes=path.stat().st_size, sha256=h.hexdigest())

def owned_work(ctx, create=False):
    base = Path(os.environ["RUNNER_TEMP"])
    c.require(base.is_absolute() and not base.is_symlink(), "runner temp root")
    p = base / (c.GROUP+"-"+ctx["token"])
    c.require(not p.is_symlink(), "owned work symlink")
    if create:
        p.mkdir(mode=0o700)
        write(p/"owner.json", ctx)
    c.require(c.decode((p/"owner.json").read_bytes()) == ctx, "owned work identity")
    return p

def snapshot(source):
    rows = {}
    repos = [source] + [source/p for p in c.GITLINKS]
    for repo in repos:
        paths = subprocess.check_output(["git", "-C", str(repo), "ls-files", "-z"]).split(b"\0")
        for raw in paths:
            if not raw: continue
            rel = raw.decode()
            p = repo/rel
            if p.is_dir() and p.relative_to(source).as_posix() in c.GITLINKS:
                continue
            c.require(p.is_file() or p.is_symlink(), "tracked source disappeared")
            value = dict(symlink=os.readlink(p)) if p.is_symlink() else fingerprint(p)
            rows[p.relative_to(source).as_posix()] = value
        head = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
        relative = repo.relative_to(source).as_posix()
        c.require(head == (c.UPSTREAM if relative == "." else c.GITLINKS[relative][1]), "source HEAD drift")
    return rows


def execute_command(report, out, label, argv, timeout=120, runner=subprocess.run):
    item = dict(label=label, argv=argv, returncode=None, elapsed_seconds=None)
    report["commands"].append(item); begin = time.monotonic()
    primary = None; progress_error = None; answer = None
    try:
        with (out/(label+".stdout")).open("wb") as so, (out/(label+".stderr")).open("wb") as se:
            result = runner(argv, stdout=so, stderr=se, timeout=timeout)
            item["returncode"] = result.returncode
            c.require(result.returncode == 0, label+" failed")
        answer = (out/(label+".stdout")).read_bytes()
    except BaseException as exc:
        primary = exc; item["error"] = c.error_record(label, exc)
    finally:
        item["elapsed_seconds"] = time.monotonic()-begin
        try:
            write(out/"host-progress.json", report)
        except BaseException as exc:
            progress_error = exc
            report["terminal_errors"].append(c.error_record("host-progress", exc))
    if primary is not None: raise primary
    if progress_error is not None: raise progress_error
    return answer

def create_owned(ctx, work, report, invoke, argv):
    names = invoke("names-before-owned-create",
                   ["docker","container","ls","-a","--format","{{.Names}}"], 120).decode()
    c.require(ctx["name"] not in names.splitlines(), "owned name already exists")
    # The intent is durable before the daemon call, never before the name refusal.
    c.atomic_record(work/"out"/"create-attempt.json",
                    dict(context=ctx, argv=argv, creation_attempted=True))
    report["creation_attempted"] = True
    identity = invoke("owned-container-create", argv, 120).decode().strip()
    c.require(__import__("re").fullmatch("[0-9a-f]{64}", identity) is not None,
              "created container identity")
    return identity

def cleanup_owned(ctx, work, report, identity, creation_attempted, inspect_one, invoke):
    if not creation_attempted:
        report["owned_cleanup_skipped"] = "No creation attempt by this process"
        return
    state = {}
    def owned(info):
        c.require(info["Name"] == "/"+ctx["name"]
                  and info["Config"]["Labels"].get("nssoc.build.source") == ctx["source"]
                  and info["Config"]["Labels"].get("nssoc.build.token") == ctx["token"]
                  and __import__("re").fullmatch("[0-9a-f]{64}", info["Id"]) is not None,
                  "cleanup ownership")
        c.require(identity is None or info["Id"] == identity, "cleanup container identity")
        return info
    def recover():
        info = owned(inspect_one(identity or ctx["name"]))
        state["id"] = info["Id"]; state["info"] = info
        report["owned_container_recovery"] = dict(id=info["Id"], name=info["Name"],
            recovered_after_create_client_error=identity is None)
    c.attempt(report, "recover-owned-container", recover)
    if "id" not in state: return
    def capture():
        info = owned(inspect_one(state["id"])); state["info"] = info
        report["container_terminal"] = info
        c.atomic_record(work/"out"/"container-terminal.json", info)
    def stop():
        info = owned(inspect_one(state["id"]))
        if info["State"]["Running"]:
            invoke("owned-stop", ["docker","stop","--time","15",state["id"]], 45)
    c.attempt(report, "owned-stop", stop)
    c.attempt(report, "post-stop-inspect", capture)
    # An unsuccessful stop or inspect cannot skip the independently owned kill path.
    def kill():
        info = owned(inspect_one(state["id"]))
        if info["State"]["Running"]:
            invoke("owned-kill", ["docker","kill",state["id"]], 45)
    c.attempt(report, "owned-kill-if-running", kill)
    c.attempt(report, "terminal-inspect", capture)
    def stopped():
        c.validate_container(owned(inspect_one(state["id"])), ctx, work, True)
    c.attempt(report, "stopped-container-contract", stopped)
    def remove():
        info = owned(inspect_one(state["id"]))
        c.require(info["State"]["Running"] is False and info["State"]["Pid"] == 0,
                  "remove live container")
        invoke("owned-container-remove", ["docker","rm",state["id"]], 60)
    c.attempt(report, "owned-container-removal", remove)
    def absent():
        names = invoke("owned-removal-census",
            ["docker","container","ls","-a","--format","{{.Names}}"], 60).decode()
        c.require(ctx["name"] not in names.splitlines(), "owned container remains")
    c.attempt(report, "owned-removal-confirmation", absent)


def build():
    ctx = c.context(os.environ); m = c.method(ROOT)
    c.require(m["source_controls_authorized"] is True and m["engine_build_authorized"] is True, "build not authorized")
    work = owned_work(ctx, True); out = work/"out"; out.mkdir()
    report = dict(schema="mainchip-witness-engine-host-v1", source=ctx["source"],
        status="IN_PROGRESS", commands=[], terminal_errors=[], creation_attempted=False,
        physical_acceptance=False, observer_equivalence_qualified=False, native_routing_executed=False)
    started=time.monotonic(); container_id=None; before=None; primary=None; handlers={}
    def command(label, argv, timeout=120):
        return execute_command(report, out, label, argv, timeout)
    def inspect_one(identity):
        return c.decode(subprocess.check_output(["docker","inspect",identity],timeout=30))[0]
    def interrupted(signum, frame):
        raise RuntimeError("owned engine build interrupted by signal "+str(signum))
    def terminal_source():
        after=snapshot(work/"source"); write(out/"source-after.json",after)
        c.require(after == before, "compiled tracked source changed")
        header=work/"source/src/drt/src/MainchipInternalWitness.h"
        c.require(fingerprint(header)["sha256"] == m["protected"][observer.HEADER], "observer header changed")
        c.method(ROOT)
    def terminal_engine():
        info=report["container_terminal"]
        inner=c.decode((out/"inner-result.json").read_bytes())
        c.validate_terminal(info,inner)
        c.require(fingerprint(out/"openroad") == inner["binary"], "binary receipt mismatch")
    try:
        for sig in (signal.SIGTERM, signal.SIGINT):
            handlers[sig]=signal.signal(sig,interrupted)
        proof=reservation.wait(c.GROUP,os.environ)
        c.require(not proof["existing_assets"],"release is not empty before build")
        write(out/"release-reservation.json",proof)
        shutil.copyfile(ROOT/c.METHOD,out/"method.json")
        for filename in ("engine-build-controls.json","internal-witness-controls.json"):
            c.require((ROOT/filename).is_file(),"source controls evidence missing")
            shutil.copyfile(ROOT/filename,out/filename)
        c.require(shutil.disk_usage(work).free >= m["limits"]["min_free_disk_bytes"],"free disk budget")
        command("docker-version",["docker","version"],60)
        names=command("existing-container-names",["docker","container","ls","-a","--format","{{.Names}}"]).decode()
        c.require(ctx["name"] not in names.splitlines(),"owned name already exists")
        command("immutable-image-pull",["docker","pull",c.IMAGE],1800)
        image=c.decode(command("image-inspect",["docker","image","inspect",c.IMAGE]))[0]
        c.validate_image(image)
        source=work/"source"; source.mkdir()
        def fetch_repo(path,url,revision,label):
            path.mkdir(parents=True,exist_ok=True)
            command(label+"-init",["git","init",str(path)])
            command(label+"-remote",["git","-C",str(path),"remote","add","origin",url])
            command(label+"-fetch",["git","-C",str(path),"fetch","--depth=1","origin",revision],1200)
            command(label+"-checkout",["git","-C",str(path),"checkout","--detach","FETCH_HEAD"],300)
            head=command(label+"-head",["git","-C",str(path),"rev-parse","HEAD"]).decode().strip()
            c.require(head==revision,"upstream fetch identity")
        fetch_repo(source,"https://github.com/The-OpenROAD-Project/OpenROAD.git",c.UPSTREAM,"openroad")
        links=command("source-gitlinks",["git","-C",str(source),"ls-tree","-r","HEAD"]).decode().splitlines()
        got={}
        for line in links:
            if line.startswith("160000 "):
                meta,path=line.split("\t",1); got[path]=meta.split()[2]
        c.require(got=={p:v[1]for p,v in c.GITLINKS.items()},"gitlink identities")
        for i,(path,(url,revision)) in enumerate(c.GITLINKS.items()):
            fetch_repo(source/path,url,revision,"dependency-"+str(i))
            nested=command("dependency-"+str(i)+"-gitlinks",["git","-C",str(source/path),"ls-tree","-r","HEAD"]).decode()
            c.require(not any(line.startswith("160000 ")for line in nested.splitlines()),"unbound nested gitlink")
        for relative,expected in m["upstream_primary"].items():
            c.require(fingerprint(source/relative)["sha256"]==expected,"upstream primary identity: "+relative)
        original=(source/"src/drt/src/TritonRoute.cpp").read_bytes()
        modified=observer.derive(original)
        c.require(c.digest(modified)==m["derived_router_sha256"],"derived router identity")
        (source/"src/drt/src/TritonRoute.cpp").write_bytes(modified)
        shutil.copyfile(ROOT/observer.HEADER,source/"src/drt/src/MainchipInternalWitness.h")
        before=snapshot(source); write(out/"source-before.json",before)
        for local,destination in (("scripts/mainchip_witness_engine_build_inner.py","inner.py"),
                                   ("scripts/mainchip_witness_engine_build_contract.py","mainchip_witness_engine_build_contract.py")):
            shutil.copyfile(ROOT/local,work/destination)
        create=c.create_argv(ctx,work,os.getuid(),os.getgid())
        container_id=create_owned(ctx,work,report,command,create)
        info=inspect_one(container_id); c.validate_container(info,ctx,work); write(out/"container-initial.json",info)
        command("owned-container-start",["docker","start","--attach",container_id],11040)
    except BaseException as exc:
        primary=exc
        report["failure"]=c.error_record("build",exc)
    finally:
        cleanup_owned(ctx,work,report,container_id,report["creation_attempted"],inspect_one,command)
        if before is not None:
            c.attempt(report,"tracked-source-identity",terminal_source)
        if report["creation_attempted"]:
            c.attempt(report,"engine-terminal-contract",terminal_engine)
        for sig, previous in handlers.items():
            def restore(sig=sig, previous=previous):
                signal.signal(sig, previous)
            c.attempt(report,"restore-signal-"+str(sig),restore)
        report["elapsed_seconds"]=time.monotonic()-started
        report["status"]=("PASS_COMPILED_ENGINE_INTERFACE_ONLY"
            if container_id is not None and not report["terminal_errors"] and primary is None
            else "FAIL_ENGINE_BUILD")
        c.finish_record(out/"host-result.json",report,"FAIL_ENGINE_BUILD",primary)
    print(json.dumps(report,sort_keys=True))
    return 0 if report["status"].startswith("PASS_") else 1


def terminal_availability(out):
    states={}
    for name in ("host-result.json","inner-result.json"):
        path=out/name
        c.require(not path.is_symlink(),"terminal record symlink")
        item=dict(present=path.is_file())
        if item["present"]:
            item.update(fingerprint(path))
            try:
                value=c.decode(path.read_bytes())
                item["parsed_object"]=isinstance(value,dict)
                item["status"]=value.get("status") if isinstance(value,dict) else None
            except BaseException as exc:
                item["parse_error"]=c.error_record("read-"+name,exc)
        states[name]=item
    return dict(source_records=states,physical_acceptance=False,
                observer_equivalence_qualified=False,
                missing_or_malformed_records_do_not_block_preservation=True)

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
    archive=work/"engine-evidence.tar.gz"
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
            p=work/("engine-evidence.tar.gz.part%03d"%i);p.write_bytes(raw)
            parts.append(dict(name=p.name,**fingerprint(p)));i+=1
    write(out/"parts.json",dict(archive=archive_receipt,parts=parts))
    tag="cloud-results-"+ctx["token"]+"-"+c.GROUP
    uploads=[out/x for x in ("host-result.json","inner-result.json","method.json",
        "engine-build-controls.json","internal-witness-controls.json","release-reservation.json",
        "outputs.json","parts.json","container-initial.json","container-terminal.json",
        "runtime-dependencies.json","build-configuration.json","publication-availability.json") if (out/x).is_file()]
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
    p=argparse.ArgumentParser();p.add_argument("mode",choices=("build","publish"));a=p.parse_args()
    sys.exit(build()if a.mode=="build"else publish())
