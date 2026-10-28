#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""GitHub-hosted, owned native engine build with permanent failure evidence."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
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
    path.write_text(json.dumps(data, sort_keys=True, indent=2)+"\n")

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

def build():
    ctx = c.context(os.environ); m = c.method(ROOT)
    c.require(m["source_controls_authorized"] is True and m["engine_build_authorized"] is True, "build not authorized")
    work = owned_work(ctx, True); out = work/"out"; out.mkdir()
    report = dict(schema="mainchip-witness-engine-host-v1", source=ctx["source"],
        status="IN_PROGRESS", commands=[], terminal_errors=[], physical_acceptance=False,
        observer_equivalence_qualified=False, native_routing_executed=False)
    started = time.monotonic(); container_id = None; before = None
    def command(label, argv, timeout=120):
        item = dict(label=label, argv=argv, returncode=None, elapsed_seconds=None)
        report["commands"].append(item); begin = time.monotonic()
        try:
            with (out/(label+".stdout")).open("wb") as so, (out/(label+".stderr")).open("wb") as se:
                r = subprocess.run(argv, stdout=so, stderr=se, timeout=timeout)
                item["returncode"] = r.returncode
                c.require(r.returncode == 0, label+" failed")
            return (out/(label+".stdout")).read_bytes()
        finally:
            item["elapsed_seconds"] = time.monotonic()-begin
            write(out/"host-progress.json", report)
    def inspect():
        return c.decode(subprocess.check_output(["docker", "inspect", container_id], timeout=30))[0]
    def terminal(name, operation):
        try:
            operation()
        except Exception as exc:
            report["terminal_errors"].append(dict(action=name,error=repr(exc),traceback=traceback.format_exc()))
    def stop_and_inspect():
        info = inspect()
        c.require(info["Id"] == container_id and info["Name"] == "/"+ctx["name"]
                  and info["Config"]["Labels"].get("nssoc.build.source") == ctx["source"]
                  and info["Config"]["Labels"].get("nssoc.build.token") == ctx["token"], "cleanup ownership")
        if info["State"]["Running"]:
            command("owned-stop", ["docker","stop","--time","15",container_id], 45)
        info = inspect(); write(out/"container-terminal.json", info)
        c.validate_container(info, ctx, work, True)
    def terminal_source():
        after = snapshot(work/"source"); write(out/"source-after.json",after)
        c.require(after == before, "compiled tracked source changed")
        header = work/"source/src/drt/src/MainchipInternalWitness.h"
        c.require(fingerprint(header)["sha256"] == m["protected"][observer.HEADER], "observer header changed")
    def terminal_engine():
        info=c.decode((out/"container-terminal.json").read_bytes())
        inner=c.decode((out/"inner-result.json").read_bytes())
        c.validate_terminal(info,inner)
        c.require(fingerprint(out/"openroad") == inner["binary"], "binary receipt mismatch")
    def remove_owned():
        info=inspect()
        c.require(info["Id"] == container_id and info["Config"]["Labels"].get("nssoc.build.source")==ctx["source"]
                  and info["Config"]["Labels"].get("nssoc.build.token")==ctx["token"]
                  and info["State"]["Running"] is False, "remove ownership")
        command("owned-container-remove",["docker","rm",container_id],60)
        names=subprocess.check_output(["docker","container","ls","-a","--format","{{.Names}}"],text=True)
        c.require(ctx["name"] not in names.splitlines(),"owned container remains")
    try:
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
                                   ("scripts/mainchip_witness_engine_build_contract.py","build_contract.py")):
            shutil.copyfile(ROOT/local,work/destination)
        create=c.create_argv(ctx,work,os.getuid(),os.getgid())
        container_id=command("owned-container-create",create).decode().strip()
        info=inspect(); c.validate_container(info,ctx,work); write(out/"container-initial.json",info)
        command("owned-container-start",["docker","start","--attach",container_id],11040)
    except Exception as exc:
        report["failure"]=dict(error=repr(exc),traceback=traceback.format_exc())
    finally:
        if container_id is not None:
            terminal("stop-and-inspect",stop_and_inspect)
        if before is not None:
            terminal("tracked-source-identity",terminal_source)
        if container_id is not None:
            terminal("engine-terminal-contract",terminal_engine)
            terminal("owned-container-removal",remove_owned)
        report["elapsed_seconds"]=time.monotonic()-started
        report["status"]=("PASS_COMPILED_ENGINE_INTERFACE_ONLY"
                          if container_id is not None and not report["terminal_errors"] and "failure" not in report
                          else "FAIL_ENGINE_BUILD")
        write(out/"host-result.json",report)
    print(json.dumps(report,sort_keys=True))
    return 0 if report["status"].startswith("PASS_") else 1

def publish():
    ctx=c.context(os.environ); c.method(ROOT)
    work=owned_work(ctx); out=work/"out"
    proof=reservation.wait(c.GROUP,os.environ)
    c.require(not proof["existing_assets"],"refuse duplicate release publication")
    files={}
    for p in sorted(out.rglob("*")):
        c.require(not p.is_symlink(),"output symlink")
        if p.is_file():files[p.relative_to(out).as_posix()]=fingerprint(p)
    c.require("host-result.json" in files,"terminal host result missing")
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
        "runtime-dependencies.json") if (out/x).is_file()]
    uploads.extend(work/p["name"]for p in parts)
    uploaded=[]
    for p in uploads:
        subprocess.run(["gh","release","upload",tag,str(p),"--repo",c.REPOSITORY],check=True,timeout=1800)
        uploaded.append(dict(name=p.name,**fingerprint(p)))
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
