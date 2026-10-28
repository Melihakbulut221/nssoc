#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Built ELF/read-only native database qualification, not routing or timing acceptance."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tarfile
import mainchip_witness_engine_build_contract as core
from mainchip_witness_engine_build_contract import (
    require, secure_file, digest, decode, atomic_record, attempt, finish_record,
    error_record, IMAGE, IMAGE_ID, MEMORY, CPUS, PIDS, create_argv,
    validate_image, validate_container)
METHOD = "scripts/mainchip-built-engine-runtime-probe-methods.json"
GROUP = "mainchip-built-engine-runtime-probe"
BRANCH = "codex/mainchip-built-engine-runtime-probe"
REPOSITORY = core.REPOSITORY
PREFIX = "docs/evidence/mainchip-internal-witness-engine-native-build-terminal-20261028."
ENGINE_RUN = 40756287268
ENGINE_SOURCE = "3f389a05b6d2630eb6f0db80df2c191be8fd9e91"
ENGINE_RELEASE = 427111201
ENGINE_TAG = "cloud-results-40756287268-1-mainchip-internal-witness-engine-build"
ENGINE = dict(bytes=108939848, sha256="1e79e2f0e77eb1a9153ec2c4040a0420e66d77777843a211da2cfd9b59b0238a")
INPUT = dict(bytes=213740873, sha256="444f75328e4065ae1fd1fdf1b872980931fcbae8ec8a62182a833e48230bf9b1")
INPUT_MEMBER = "work/drc-observed.odb"
LIMITS = dict(memory_bytes=MEMORY, nano_cpus=CPUS, pids=PIDS,
              probe_seconds=1200, inner_seconds=1800, container_seconds=1980,
              min_free_disk_bytes=12*1024**3, archive_unpacked_bytes=1024**3)

def context(env):
    require(env.get("GITHUB_ACTIONS") == "true" and env.get("RUNNER_OS") == "Linux", "hosted Linux only")
    require(env.get("GITHUB_REPOSITORY") == REPOSITORY, "repository identity")
    require(env.get("GITHUB_RUN_ATTEMPT") == "1", "no retry")
    require(re.fullmatch("[1-9][0-9]*", env.get("GITHUB_RUN_ID","")) is not None, "run identity")
    require(re.fullmatch("[0-9a-f]{40}", env.get("GITHUB_SHA","")) is not None, "source identity")
    require(env.get("GITHUB_REF") == "refs/heads/"+BRANCH, "runtime probe branch")
    token=env["GITHUB_RUN_ID"]+"-1"
    # The inherited ownership label/name is a container isolation identity only.
    # This stage performs no engine build and makes no compilation claim.
    return dict(name="nssoc-witness-build-"+token, source=env["GITHUB_SHA"], token=token)

def method(root):
    m=decode(secure_file(root,METHOD).read_bytes())
    require(m["schema"]=="mainchip-built-engine-runtime-probe-v1", "method schema")
    require(m["limits"]==LIMITS and m["image"]==IMAGE and m["image_id"]==IMAGE_ID, "runtime limits/image")
    require(m["engine"]==ENGINE and m["input"]==INPUT, "immutable native inputs")
    require(type(m["native_probe_authorized"]) is bool, "authorization type")
    for k in ("native_routing_authorized","rc_sta_execution_authorized","physical_acceptance","observer_equivalence_qualified"):
        require(m[k] is False, "read-only scope")
    require(m["qualified_routing_engine"] is None, "routing is not qualified by a probe")
    prior=core.method(root)
    require(all(m["protected"].get(p)==h for p,h in prior["protected"].items()),"inherited protection removed")
    require(m["inherited_protected_count"]==len(prior["protected"]),"inherited map count")
    for p,h in m["protected"].items():
        require(re.fullmatch("[0-9a-f]{64}",h) is not None and digest(secure_file(root,p).read_bytes())==h,"protected source: "+p)
    return m

def expected_engine(root):
    def read(suffix): return decode(secure_file(root,PREFIX+suffix).read_bytes())
    outputs=read("outputs.json"); parts=read("parts.json"); host=read("host-result.json"); inner=read("inner-result.json")
    require(outputs["source"]==ENGINE_SOURCE and outputs["physical_acceptance"] is False, "build source/scope")
    require(len(outputs["files"])==94 and outputs["files"]["openroad"]==ENGINE,"engine output inventory")
    require(host["source"]==ENGINE_SOURCE and host["status"]=="PASS_COMPILED_ENGINE_INTERFACE_ONLY" and not host["terminal_errors"],"host build result")
    require(inner["status"]=="PASS_COMPLETE_OPENROAD_BUILD_AND_INTERFACE_SMOKE_ONLY" and not inner["terminal_errors"] and inner["binary"]==ENGINE,"inner build result")
    for result in (host,inner):
        require(all(x["returncode"]==0 for x in result["commands"]),"build command failure")
        require(result["physical_acceptance"] is False and result["observer_equivalence_qualified"] is False,"build scope changed")
    require(len(parts["parts"])==1 and parts["parts"][0]["name"]=="engine-evidence.tar.gz.part000","engine parts")
    require({k:parts["parts"][0][k] for k in ("bytes","sha256")}==parts["archive"],"engine archive binding")
    files=dict(outputs["files"])
    b=secure_file(root,PREFIX+"outputs.json").read_bytes()
    files["outputs.json"]=dict(bytes=len(b),sha256=digest(b))
    require(len(files)==95,"complete engine archive inventory")
    runtime=read("runtime-dependencies.json")
    require(len(runtime)==104,"runtime library count")
    return dict(files=files,parts=parts,runtime=runtime,release=read("release.json"))

def engine_envelope(run,jobs,release,tag,expected_release):
    import ensure_cloud_tested_source_release as r
    require((run["id"],run["run_attempt"],run["head_sha"],run["status"],run["conclusion"])==
            (ENGINE_RUN,1,ENGINE_SOURCE,"completed","success"),"original build run")
    require(run["event"]=="workflow_dispatch" and run["path"]==".github/workflows/mainchip-internal-witness-engine-build.yml"
            and run["head_branch"]=="codex/mainchip-internal-witness-engine-build","original build workflow")
    require({x["id"]:(x["name"],x["status"],x["conclusion"]) for x in jobs["jobs"]}==
            {123055977574:("source-controls","completed","success"),123057210407:("engine-build","completed","success")}
            and len(jobs["jobs"])==2,"original build jobs")
    r.validate_release(release,tag,ENGINE_TAG,ENGINE_SOURCE)
    require(release["id"]==expected_release["id"]==ENGINE_RELEASE,"engine release")
    def identities(value):
        rows=value["assets"]
        require(len({x["id"]for x in rows})==len(rows) and len({x["name"]for x in rows})==len(rows),"duplicate release asset")
        return {x["id"]:(x["name"],x["size"],x["digest"])for x in rows}
    require(identities(release)==identities(expected_release),"engine release asset census")
    return dict(run=ENGINE_RUN,source=ENGINE_SOURCE,release=ENGINE_RELEASE,tag=ENGINE_TAG)

def canonical(name):
    p=PurePosixPath(name)
    require(isinstance(name,str) and name and "\\" not in name and "\0" not in name
            and not p.is_absolute() and p.as_posix()==name and all(x not in (".","..","")for x in p.parts),"archive path")
    return p

def engine_extract(stream,destination,expected,selected=("openroad",),limit=1024**3):
    destination=Path(destination)
    require(not destination.exists() and not destination.is_symlink(),"fresh extraction destination")
    require(set(selected)<=set(expected) and bool(expected),"selected engine files")
    directories=set()
    for name,row in expected.items():
        p=canonical(name);directories.update(str(x)for x in p.parents if str(x)!=".")
        require(type(row["bytes"]) is int and 0<=row["bytes"]<=limit and re.fullmatch("[0-9a-f]{64}",row["sha256"]) is not None,"archive member receipt")
    destination.mkdir();seen=set();found={};total=0
    with tarfile.open(fileobj=stream,mode="r|gz")as archive:
        for member in archive:
            require(member.isfile() or member.isdir(),"nonregular archive member")
            name=member.name.rstrip("/")if member.isdir()else member.name
            canonical(name);require(name not in seen,"duplicate archive member");seen.add(name)
            if member.isdir():
                require(name in directories,"unrecorded archive directory");continue
            require(name in expected and member.size==expected[name]["bytes"],"archive member identity/size")
            total+=member.size;require(total<=limit,"archive expanded size")
            h=hashlib.sha256();size=0;out=None
            try:
                if name in selected:
                    target=destination/name;target.parent.mkdir(parents=True,exist_ok=True);out=target.open("xb")
                with archive.extractfile(member)as content:
                    for raw in iter(lambda:content.read(4*1024**2),b""):
                        h.update(raw);size+=len(raw)
                        if out is not None:out.write(raw)
            finally:
                if out is not None:out.close()
            row=dict(bytes=size,sha256=h.hexdigest())
            require(row==expected[name],"changed archive member");found[name]=row
    require(set(found)==set(expected),"missing archive member")
    return dict(all_files=found,all_regular_members_verified=True,selected=list(selected),unpacked_bytes=total)

def runtime_match(expected,actual):
    require(len(expected)==104 and actual==expected,"runtime dependency identities")
    return dict(count=len(actual),exact_paths_sizes_hashes=True)
