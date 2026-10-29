#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted source-only prefix checks; native/cloud collaborators are explicitly synthetic."""
import argparse
import ast
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import FunctionType
from unittest.mock import patch
import mainchip_fixed_engine_route_prefix_contract as c
import mainchip_fixed_engine_route_prefix_driver as driver
import mainchip_fixed_engine_route_prefix_native as native
import cloud_mainchip_fixed_engine_route_prefix as host
import mainchip_two_signal_repair as repair
import check_mainchip_built_engine_route_prefix as old
import check_mainchip_fixed_engine_runtime_host as old_host

ROOT=Path(__file__).resolve().parent.parent
ORIGINAL_SOURCES={'scripts/cloud_mainchip_built_engine_route_prefix.py': 'efea3589a92dc9dc1d1b7e4f3570a8d78785b0a5162efc2b4df24bc6fb3e5fba', 'scripts/mainchip_built_engine_route_prefix_inner.py': '464621a06086557cac09cea4a7f3c19112daba8e5f7f5b5e5413bfcffe27fcb6', 'scripts/mainchip_built_engine_route_prefix_driver.py': '1b2e824309c19bc547edfff6152885bc38b4ab40982000f349d3fdc34dbfe488', 'scripts/mainchip_built_engine_route_prefix_native.py': 'e7750dceb862030ffcb7e1dbd62cee22ee137861763f23884e8d9c06a9adb226', 'scripts/cloud_mainchip_fixed_engine_runtime.py': 'ef508a573843557739e1f6f81b7acddbb82f8f08d5d4ae7983568f469ed11276', 'scripts/mainchip_fixed_engine_runtime_contract.py': 'f4497294ed2b2874a00c48d277287cc6684d61eb127e5af924d51b0022989274'}
NEW_SOURCES={'scripts/cloud_mainchip_fixed_engine_route_prefix.py': 'f7b43c87dc5b90f52a96009ba390b0b6d6b96645c8d856664956fd4c169b9988', 'scripts/mainchip_fixed_engine_route_prefix_inner.py': '857b0c66dd407089495ebf23e43d9f81b20e87d332da570e210a42fc7359306d', 'scripts/mainchip_fixed_engine_route_prefix_driver.py': 'e9576ecfd5b636b3819cd0dad60334c02c87e66bd014e3179919f2669089f689', 'scripts/mainchip_fixed_engine_route_prefix_native.py': '8bbc8fb7c4f49c5a54d27f206d316e1c2c610ab358e7ca5ee13c6f26f01a119b'}
OLD_CHECKER_SHA='9ad562b540dad1653755a7476feef4b75f68630842197db34f31473dcb280f5d'
OLD_HOST_CHECKER_SHA='2fdd0a6adf698deb2ebb279985379901de96a05bd4fb371004b63c88d2adcb59'
DERIVATION_EDITS={'host': [('import mainchip_built_engine_route_prefix_contract as c', 'import mainchip_fixed_engine_route_prefix_contract as c'), ('def restore_engine(work,out):\n    from route_cloud_newer_postcts import fetch\n    expected=c.expected_engine(ROOT);read=reservation.release.api\n    envelope=c.engine_envelope(read("actions/runs/"+str(c.ENGINE_RUN)),\n        read("actions/runs/"+str(c.ENGINE_RUN)+"/jobs?per_page=100"),\n        read("releases/"+str(c.ENGINE_RELEASE)),read("git/ref/tags/"+c.ENGINE_TAG),expected["release"])\n    write(out/"engine-source-envelope.json",envelope)\n    part=expected["parts"]["parts"][0];archive=work/part["name"]\n    url="https://github.com/"+c.REPOSITORY+"/releases/download/"+c.ENGINE_TAG+"/"+part["name"]\n    fetch(url,part["sha256"],archive)\n    c.require(fingerprint(archive)==expected["parts"]["archive"],"engine archive identity")\n    with archive.open("rb")as stream:\n        inventory=c.engine_extract(stream,work/"engine",expected["files"])\n    write(out/"engine-restoration.json",inventory)\n    c.require(fingerprint(work/"engine/openroad")==c.ENGINE,"restored ELF")\n    (work/"engine/openroad").chmod(0o500)\n    shutil.copyfile(c.secure_file(ROOT,c.PREFIX+"runtime-dependencies.json"),work/"runtime-dependencies.json")\n', 'def restore_engine(work,out):\n    from route_cloud_newer_postcts import fetch\n    expected=c.expected_engine(ROOT);read=reservation.release.api\n    envelope=c.engine_envelope(read("actions/runs/"+str(c.ENGINE_RUN)),\n        read("actions/runs/"+str(c.ENGINE_RUN)+"/attempts/1/jobs?per_page=100"),\n        read("releases/"+str(c.ENGINE_RELEASE)),read("git/ref/tags/"+c.ENGINE_TAG),expected["release"])\n    write(out/"engine-source-envelope.json",envelope)\n    part=expected["parts"]["parts"][0];archive=work/part["name"]\n    url="https://github.com/"+c.REPOSITORY+"/releases/download/"+c.ENGINE_TAG+"/"+part["name"]\n    fetch(url,part["sha256"],archive)\n    c.require(fingerprint(archive)==expected["parts"]["archive"],"engine archive identity")\n    with archive.open("rb")as stream:\n        inventory=c.engine_extract(stream,work/"engine",expected["files"])\n    write(out/"engine-restoration.json",inventory)\n    c.require(fingerprint(work/"engine/openroad")==c.ENGINE,"restored ELF")\n    (work/"engine/openroad").chmod(0o500)\n    shutil.copyfile(c.secure_file(ROOT,c.RUNTIME_SOURCE),work/"runtime-dependencies.json")\n    shutil.copyfile(work/"runtime-dependencies.json",out/"runtime-dependencies.json")\n'), ('c.require(m["native_prefix_authorized"] is True,"native routing prefix not authorized")', 'c.authorize_prefix(m)'), ('schema="built-engine-route-prefix-host-v1"', 'schema="fixed-engine-route-prefix-host-v1"'), ('        c.require(all(x["returncode"]==0 and x["timed_out"] is False for x in inner["commands"]),"native command failure")', '        c.require(all(x["returncode"]==0 and x["timed_out"] is False for x in inner["commands"]),"native command failure")\n        expected=c.expected_engine(ROOT)\n        c.runtime_match(expected["runtime"],c.decode((out/"runtime-observed.json").read_bytes()))\n        c.require(fingerprint(work/"runtime-dependencies.json")==fingerprint(c.secure_file(ROOT,c.RUNTIME_SOURCE)),"runtime expectation file changed")'), ('c.require(not proof["existing_assets"],"release not empty before native probe")', 'c.validate_reservation(proof,ctx,True)'), ('        shutil.copyfile(ROOT/"docs/evidence/mainchip-built-engine-route-prefix-source-admission-20261029.json",out/"prefix-source-admission.json")\n        shutil.copyfile(ROOT/"route-prefix-controls.json",out/"route-prefix-controls.json")', '        shutil.copyfile(c.secure_file(ROOT,c.SOURCE_ADMISSION),out/"prefix-source-admission.json")\n        report["runtime_qualification"]=c.runtime_qualification(ROOT)\n        write(out/"runtime-qualification.json",report["runtime_qualification"])\n        report["current_source_controls"]=c.control_evidence(ROOT,ctx)\n        write(out/"current-source-controls.json",report["current_source_controls"])\n        for name,expected in report["current_source_controls"].items():\n            c.require(Path(name).name==name and name.endswith("-controls.json"),"source control output name")\n            shutil.copyfile(c.secure_file(ROOT,name),out/name)\n            c.require(fingerprint(out/name)==expected,"source control copy changed")'), ('c.method(source);projected=True', 'c.method(source);c.runtime_qualification(source);projected=True'), ('ROOT/"scripts/mainchip_built_engine_route_prefix_inner.py"', 'ROOT/"scripts/mainchip_fixed_engine_route_prefix_inner.py"'), ('def publish():\n    ctx=c.context(os.environ); c.method(ROOT)\n    work=owned_work(ctx); out=work/"out"; out.mkdir(exist_ok=True)\n    proof=reservation.wait(c.GROUP,os.environ)\n    write(out/"publication-availability.json",terminal_availability(out))\n    files={}\n    for p in sorted(out.rglob("*")):\n        c.require(not p.is_symlink(),"output symlink")\n        if p.is_file():files[p.relative_to(out).as_posix()]=fingerprint(p)\n    write(out/"outputs.json",dict(source=ctx["source"],files=files,physical_acceptance=False))\n    archive=work/"route-prefix-evidence.tar.gz"\n    with tarfile.open(archive,"w:gz")as tar:\n        for p in sorted(out.iterdir()):\n            c.require(not p.is_symlink(),"archive symlink")\n            tar.add(p,arcname=p.name,recursive=True)\n    archive_receipt=fingerprint(archive)\n    parts=[]\n    with archive.open("rb")as stream:\n        i=0\n        while True:\n            raw=stream.read(512*1024**2)\n            if not raw:break\n            p=work/("route-prefix-evidence.tar.gz.part%03d"%i);p.write_bytes(raw)\n            parts.append(dict(name=p.name,**fingerprint(p)));i+=1\n    write(out/"parts.json",dict(archive=archive_receipt,parts=parts))\n    tag="cloud-results-"+ctx["token"]+"-"+c.GROUP\n    uploads=[out/x for x in ("host-result.json","inner-result.json","method.json",\n        "route-prefix-controls.json","native-prefix-result.json","release-reservation.json",\n        "outputs.json","parts.json","container-initial.json","container-terminal.json",\n        "runtime-observed.json","frozen-prefix.json","frozen-prefix-inventory.json","prefix-source-admission.json","source-admission.json","routing-source-envelope.json","engine-restoration.json","input-restoration.json","engine-source-envelope.json","publication-availability.json") if (out/x).is_file()]\n    uploads.extend(work/p["name"]for p in parts)\n    planned={p.name for p in uploads}\n    c.require(len(planned)==len(uploads),"duplicate publication filename")\n    c.require({x["name"] for x in proof["existing_assets"]} <= planned,"unexpected reserved asset")\n    def upload(tag,path):\n        subprocess.run(["gh","release","upload",tag,str(path),"--repo",c.REPOSITORY],check=True,timeout=1800)\n    uploaded=[publish_asset(p,ctx,proof["release_id"],reservation.release.api,upload) for p in uploads]\n    info=reservation.release.api("releases/tags/"+tag)\n    ref=reservation.release.api("git/ref/tags/"+tag)\n    reservation.release.validate_release(info,ref,tag,ctx["source"])\n    byname={a["name"]:a for a in info["assets"]}\n    c.require(set(byname)=={x["name"]for x in uploaded},"release asset census")\n    for row in uploaded:\n        actual=byname[row["name"]]\n        c.require(actual["size"]==row["bytes"] and actual["digest"]=="sha256:"+row["sha256"],\n                  "published asset mismatch")\n    write(out/"publication.json",dict(status="PASS_PERMANENT_RELEASE_PUBLICATION",\n        release_id=info["id"],tag=tag,source=ctx["source"],assets=uploaded,\n        native_archives_stay_in_cloud=True))\n    print(json.dumps(dict(release_id=info["id"],tag=tag,assets=len(uploaded)),sort_keys=True))\n    return 0\n', 'def publish():\n    ctx=c.context(os.environ)\n    work=owned_work(ctx); out=work/"out"; out.mkdir(exist_ok=True)\n    source_error=None\n    try:c.method(ROOT)\n    except BaseException as exc:source_error=exc\n    # Preservation is separately authorized by the exact current context, owned\n    # workspace and reserved source/tag. Source failure never becomes build PASS.\n    try:\n        proof=reservation.wait(c.GROUP,os.environ);c.validate_reservation(proof,ctx,False)\n        availability=terminal_availability(out)\n        availability.update(source_integrity_validated=source_error is None,native_accepted=False,\n          source_integrity_error=None if source_error is None else c.error_record("publication-source-integrity",source_error))\n        write(out/"publication-availability.json",availability)\n        optional=("host-result.json","inner-result.json","method.json","native-prefix-result.json",\n          "release-reservation.json","container-initial.json","container-terminal.json",\n          "runtime-dependencies.json","runtime-observed.json","engine-restoration.json",\n          "input-restoration.json","engine-source-envelope.json","current-source-controls.json",\n          "runtime-qualification.json","prefix-source-admission.json","source-admission.json",\n          "routing-source-envelope.json","frozen-prefix.json","frozen-prefix-inventory.json",\n          "publication-availability.json")\n        # Current source-control names are supplied by the contract. Discover their\n        # preserved copies without re-running failed source admission during publication.\n        optional+=tuple(sorted(p.name for p in out.iterdir()\n          if p.name.endswith("-controls.json") and p.name not in optional))\n        plan=c.direct_plan(out,optional);write(out/"direct-publication-plan.json",plan)\n        files={}\n        for p in sorted(out.rglob("*")):\n            c.require(not p.is_symlink(),"output symlink")\n            if p.is_file():files[p.relative_to(out).as_posix()]=fingerprint(p)\n        write(out/"outputs.json",dict(source=ctx["source"],files=files,physical_acceptance=False))\n        archive=work/"route-prefix-evidence.tar.gz"\n        with tarfile.open(archive,"w:gz")as tar:\n            for p in sorted(out.iterdir()):\n                c.require(not p.is_symlink(),"archive symlink")\n                tar.add(p,arcname=p.name,recursive=True)\n        archive_receipt=fingerprint(archive)\n        parts=[]\n        with archive.open("rb")as stream:\n            i=0\n            while True:\n                raw=stream.read(512*1024**2)\n                if not raw:break\n                p=work/("route-prefix-evidence.tar.gz.part%03d"%i);p.write_bytes(raw)\n                parts.append(dict(name=p.name,**fingerprint(p)));i+=1\n        write(out/"parts.json",dict(archive=archive_receipt,parts=parts))\n        tag="cloud-results-"+ctx["token"]+"-"+c.GROUP\n        uploads=[out/r["name"]for r in plan["files"]if r["disposition"]=="direct"]\n        uploads.extend(out/x for x in ("outputs.json","parts.json","direct-publication-plan.json"))\n        uploads.extend(work/p["name"]for p in parts)\n        planned={p.name for p in uploads}\n        c.require(len(planned)==len(uploads),"duplicate publication filename")\n        c.require({x["name"] for x in proof["existing_assets"]} <= planned,"unexpected reserved asset")\n        def upload(tag,path):\n            subprocess.run(["gh","release","upload",tag,str(path),"--repo",c.REPOSITORY],check=True,timeout=1800)\n        uploaded=[publish_asset(p,ctx,proof["release_id"],reservation.release.api,upload) for p in uploads]\n        info=reservation.release.api("releases/tags/"+tag)\n        ref=reservation.release.api("git/ref/tags/"+tag)\n        reservation.release.validate_release(info,ref,tag,ctx["source"])\n        byname={a["name"]:a for a in info["assets"]}\n        c.require(set(byname)=={x["name"]for x in uploaded},"release asset census")\n        for row in uploaded:\n            actual=byname[row["name"]]\n            c.require(actual["size"]==row["bytes"] and actual["digest"]=="sha256:"+row["sha256"],\n                      "published asset mismatch")\n        write(out/"publication.json",dict(status="PASS_PERMANENT_RELEASE_PUBLICATION"if source_error is None else"PASS_PERMANENT_FAILURE_EVIDENCE_ONLY",\n            source_integrity_validated=source_error is None,native_accepted=False,\n            release_id=info["id"],tag=tag,source=ctx["source"],assets=uploaded,\n            native_archives_stay_in_cloud=True))\n        print(json.dumps(dict(release_id=info["id"],tag=tag,assets=len(uploaded)),sort_keys=True))\n    except BaseException as publication_error:\n        if source_error is not None:\n            record=dict(status="FAIL_SOURCE_INTEGRITY_AND_PUBLICATION",native_accepted=False,\n              source_error=c.error_record("source",source_error),publication_error=c.error_record("publication",publication_error))\n            try:write(out/"publication-failure.json",record)\n            except BaseException:\n                try:print("FIXED_PREFIX_PUBLICATION_FALLBACK "+json.dumps(record,sort_keys=True),flush=True)\n                except BaseException:pass\n            raise source_error\n        raise\n    if source_error is not None:raise source_error\n    return 0\n')], 'publisher_from_runtime': [('        optional=("host-result.json","inner-result.json","method.json","runtime-probe-controls.json",\n          "runtime-host-controls.json","api-identity-census.json","release-reservation.json",\n          "container-initial.json","container-terminal.json","runtime-dependencies.json",\n          "runtime-observed.json","engine-restoration.json","input-restoration.json",\n          "engine-source-envelope.json","current-source-controls.json","publication-availability.json")', '        optional=("host-result.json","inner-result.json","method.json","native-prefix-result.json",\n          "release-reservation.json","container-initial.json","container-terminal.json",\n          "runtime-dependencies.json","runtime-observed.json","engine-restoration.json",\n          "input-restoration.json","engine-source-envelope.json","current-source-controls.json",\n          "runtime-qualification.json","prefix-source-admission.json","source-admission.json",\n          "routing-source-envelope.json","frozen-prefix.json","frozen-prefix-inventory.json",\n          "publication-availability.json")\n        # Current source-control names are supplied by the contract. Discover their\n        # preserved copies without re-running failed source admission during publication.\n        optional+=tuple(sorted(p.name for p in out.iterdir()\n          if p.name.endswith("-controls.json") and p.name not in optional))'), ('archive=work/"runtime-probe-evidence.tar.gz"', 'archive=work/"route-prefix-evidence.tar.gz"'), ('p=work/("runtime-probe-evidence.tar.gz.part%03d"%i)', 'p=work/("route-prefix-evidence.tar.gz.part%03d"%i)'), ('FIXED_RUNTIME_PUBLICATION_FALLBACK ', 'FIXED_PREFIX_PUBLICATION_FALLBACK ')], 'inner': [('import mainchip_built_engine_route_prefix_contract as c', 'import mainchip_fixed_engine_route_prefix_contract as c'), ('from mainchip_built_engine_route_prefix_contract import MEMORY,PIDS,require', 'from mainchip_fixed_engine_route_prefix_contract import MEMORY,PIDS,require'), ('schema="built-engine-route-prefix-inner-v1"', 'schema="fixed-engine-route-prefix-inner-v1"'), ('        c.method(WORK/"source")', '        c.authorize_prefix(c.method(WORK/"source"))'), ('/work/source/scripts/mainchip_built_engine_route_prefix_driver.py', '/work/source/scripts/mainchip_fixed_engine_route_prefix_driver.py')], 'driver': [('import mainchip_built_engine_route_prefix_contract as c', 'import mainchip_fixed_engine_route_prefix_contract as c')], 'native': [('import mainchip_built_engine_route_prefix_contract as c', 'import mainchip_fixed_engine_route_prefix_contract as c')]}

def encoded(value):
    return (json.dumps(value,sort_keys=True,indent=2)+"\n").encode()


def function(raw,name):
    nodes=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name==name]
    assert len(nodes)==1
    return ast.get_source_segment(raw,nodes[0])


def refuse(cases,name,call,reason=None,missing=False):
    try:
        call()
    except (ValueError,AssertionError,FileNotFoundError) as exc:
        if isinstance(exc,FileNotFoundError):
            assert missing,(name,repr(exc))
        else:
            assert str(exc),(name,"empty refusal reason")
            if reason is not None:assert reason in str(exc),(name,str(exc),reason)
        cases.append(dict(name=name,error=repr(exc)))
    else:
        raise AssertionError("unexpected acceptance: "+name)


def environment(run="781"):
    return dict(GITHUB_ACTIONS="true",RUNNER_ENVIRONMENT="github-hosted",RUNNER_OS="Linux",
        GITHUB_REPOSITORY=c.REPOSITORY,GITHUB_EVENT_NAME="workflow_dispatch",GITHUB_RUN_ATTEMPT="1",
        GITHUB_SHA="a"*40,GITHUB_RUN_ID=run,GITHUB_REF="refs/heads/"+c.BRANCH)


def reservation(ctx,assets=()):
    return dict(release_id=19,externally_reserved=True,creation_attempted=False,assets_overwritten=False,
        target_verified=True,tested_source=ctx["source"],tag="cloud-results-"+ctx["token"]+"-"+c.GROUP,
        existing_assets=list(assets))


def context_controls():
    env=environment();ctx=c.context(env)
    assert ctx["source"]==env["GITHUB_SHA"] and ctx["token"]=="781-1"
    cases=[]
    changes=(("GITHUB_ACTIONS","false"),("RUNNER_OS","Windows"),
        ("RUNNER_ENVIRONMENT","self-hosted"),("GITHUB_REPOSITORY","foreign/repo"),
        ("GITHUB_EVENT_NAME","push"),("GITHUB_RUN_ATTEMPT","2"),("GITHUB_RUN_ID","0"),
        ("GITHUB_SHA","main"),("GITHUB_REF","refs/heads/"+c.previous.BRANCH),
        ("GITHUB_REF","refs/heads/main"),("GITHUB_RUN_ATTEMPT",1))
    for i,(key,value) in enumerate(changes):
        refuse(cases,str(i)+":"+key,lambda key=key,value=value:c.context({**env,key:value}))
    assert len(cases)==11
    return dict(positive_count=1,refusal_count=11,cases=cases)


def method_controls(method,prior):
    cases=[];positive=[]
    # Establish disabled baselines explicitly even when this same checker repeats
    # immediately before a future native-authorized preparation.
    for source_flag,native_flag in ((False,False),(True,False),(True,True)):
        sample=copy.deepcopy(method)
        sample.update(source_controls_authorized=source_flag,native_prefix_authorized=native_flag,
            controller_ready=native_flag)
        assert c.validate_method(sample,prior)==sample
        if native_flag:c.authorize_prefix(sample)
        else:refuse(cases,"disabled preparation "+str(source_flag),lambda:c.authorize_prefix(sample))
        positive.append(dict(source=source_flag,native=native_flag,controller=native_flag))
    base=copy.deepcopy(method)
    base.update(source_controls_authorized=True,native_prefix_authorized=False,controller_ready=False)
    for key in ("source_controls_authorized","native_prefix_authorized","controller_ready"):
        for value in (0,1,None,"true"):
            sample=copy.deepcopy(base);sample[key]=value
            refuse(cases,"typed:"+key+":"+repr(value),lambda sample=sample:c.validate_method(sample,prior))
    for key in c.AUTH_FALSE:
        for value in (True,0,None):
            sample=copy.deepcopy(base);sample[key]=value
            refuse(cases,"scope:"+key+":"+repr(value),lambda sample=sample:c.validate_method(sample,prior))
    for native_flag,controller in ((False,True),(True,False)):
        sample=copy.deepcopy(base);sample.update(native_prefix_authorized=native_flag,controller_ready=controller)
        refuse(cases,"controller mismatch "+str(native_flag),lambda sample=sample:c.validate_method(sample,prior))
    sample=copy.deepcopy(base);sample.update(source_controls_authorized=False,native_prefix_authorized=True,controller_ready=True)
    refuse(cases,"native without source",lambda:c.validate_method(sample,prior))
    for key,value in (("schema","wrong"),("branch",c.previous.BRANCH),("group","foreign"),
                      ("prior_method_sha256","0"*64)):
        sample=copy.deepcopy(base);sample[key]=value
        refuse(cases,"identity:"+key,lambda sample=sample:c.validate_method(sample,prior))
    for key in ("engine","input"):
        sample=copy.deepcopy(base);sample[key]["sha256"]="0"*64
        refuse(cases,"native identity:"+key,lambda sample=sample:c.validate_method(sample,prior))
    sample=copy.deepcopy(base);sample["limits"]["phase_seconds"]=1199
    refuse(cases,"shortened original phase budget",lambda:c.validate_method(sample,prior))
    inherited=next(iter(prior["protected"]))
    for name,mutate in (
        ("removed inherited",lambda m:m["protected"].pop(inherited)),
        ("changed inherited",lambda m:m["protected"].update({inherited:"0"*64})),
        ("removed prior method",lambda m:m["protected"].pop(c.PRIOR)),
        ("removed new wrapper",lambda m:m["protected"].pop("scripts/cloud_mainchip_fixed_engine_route_prefix.py")),
        ("removed runtime proof",lambda m:m["protected"].pop(next(iter(c.RUNTIME_REQUIRED)))),
        ("changed runtime proof",lambda m:m["protected"].update({next(iter(c.RUNTIME_REQUIRED)):"0"*64}))):
        sample=copy.deepcopy(base);mutate(sample)
        refuse(cases,name,lambda sample=sample:c.validate_method(sample,prior))
    assert len(positive)==3 and len(c.AUTH_FALSE)==8 and len(cases)==54,(len(positive),len(cases))
    return dict(positive_count=3,refusal_count=len(cases),typed_modes=positive,cases=cases)


def derivation(root):
    raws={p:c.secure_file(root,p).read_bytes() for p in ORIGINAL_SOURCES}
    current={p:c.secure_file(root,p).read_bytes() for p in NEW_SOURCES}
    assert {p:c.digest(b)for p,b in raws.items()}==ORIGINAL_SOURCES
    assert {p:c.digest(b)for p,b in current.items()}==NEW_SOURCES
    assert c.digest(c.secure_file(root,"scripts/check_mainchip_built_engine_route_prefix.py").read_bytes())==OLD_CHECKER_SHA
    assert c.digest(c.secure_file(root,"scripts/check_mainchip_fixed_engine_runtime_host.py").read_bytes())==OLD_HOST_CHECKER_SHA
    rows=[]
    for role in ("host","inner","driver","native"):
        before_path=("scripts/cloud_mainchip_built_engine_route_prefix.py" if role=="host"
            else "scripts/mainchip_built_engine_route_prefix_"+role+".py")
        after_path=("scripts/cloud_mainchip_fixed_engine_route_prefix.py" if role=="host"
            else "scripts/mainchip_fixed_engine_route_prefix_"+role+".py")
        original=raws[before_path].decode();value=original
        for before,after in DERIVATION_EDITS[role]:
            assert value.count(before)==1,(role,before[:80]);value=value.replace(before,after,1)
        assert value.encode()==current[after_path],("complete declared derivation",role)
        for before,after in reversed(DERIVATION_EDITS[role]):
            assert value.count(after)==1;value=value.replace(after,before,1)
        assert value==original,("exact reversal",role)
        rows.append(dict(role=role,edits=len(DERIVATION_EDITS[role]),reversed_byte_exact=True))
    old_contract=c.secure_file(root,"scripts/mainchip_built_engine_route_prefix_contract.py").read_text()
    new_contract=c.secure_file(root,"scripts/mainchip_fixed_engine_route_prefix_contract.py").read_text()
    original_command=function(old_contract,"command")
    expected=original_command.replace("mainchip_built_engine_route_prefix_native.py","mainchip_fixed_engine_route_prefix_native.py")
    assert expected!=original_command and function(new_contract,"command")==expected
    assert function(new_contract,"prefix_complete")==function(old_contract,"prefix_complete")
    assert c.PHASES==old.c.PHASES and c.PASS_STATUSES==old.c.PASS_STATUSES and c.LIMITS==old.c.LIMITS
    return dict(wrappers=rows,original_command_only_native_path_changed=True,
        original_prefix_complete_byte_exact=True,all_original_limits_preserved=True,native_executed=False)


def records():
    rows={phase:dict(status=status,accepted=False,timing_accepted=False,full_phy_accepted=False)
          for phase,status in c.PASS_STATUSES.items()}
    rows["ownership"]["original_gate"]=dict(result=dict(clock_or_fixed_nets=1691,
        all_source_clock_and_fixed_records_preserved=True))
    rows["fixed-audit"]["router_census"]=dict(two_routed_nonfixed_guided_names=list(repair.TARGETS))
    return rows


def actual_driver_controls():
    rows=records();cases=[];events=[]
    def read(phase):
        events.append("read:"+phase)
        return copy.deepcopy(rows[phase])
    result=driver.execute_prefix(lambda p,a:events.append("execute:"+p),read,lambda:events.append("actionable"))
    assert result==rows and events==["execute:ownership","read:ownership","actionable",
        "execute:prepare-fixed","read:prepare-fixed","execute:paired-all-nontarget-fixed-import",
        "execute:fixed-audit","read:fixed-audit"]
    cases.append(dict(case="complete",events=list(events)))
    expected_script="/work/source/scripts/mainchip_fixed_engine_route_prefix_native.py"
    for phase in c.PHASES:
        command=c.command(phase,"/work/engine/openroad")
        assert command==(["/work/engine/openroad","-no_init","-exit","/work/out/work/fixed.tcl"]
          if phase=="paired-all-nontarget-fixed-import" else
          ["/work/engine/openroad","-no_init","-exit","-python",expected_script])
    for failed in c.PHASES:
        events=[];sentinel=RuntimeError("phase sentinel "+failed);caught=None
        def execute(phase,argv):
            events.append("execute:"+phase)
            if phase==failed:raise sentinel
        try:driver.execute_prefix(execute,read,lambda:events.append("actionable"))
        except RuntimeError as exc:caught=exc
        assert caught is sentinel
        assert [x[8:]for x in events if x.startswith("execute:")]==list(c.PHASES[:c.PHASES.index(failed)+1])
        cases.append(dict(case="failure:"+failed,events=list(events),exact_primary_preserved=True))
    events=[];denial=ValueError("ownership denied");caught=None
    def denied():
        events.append("actionable-denied");raise denial
    try:driver.execute_prefix(lambda p,a:events.append("execute:"+p),read,denied)
    except ValueError as exc:caught=exc
    assert caught is denial and events==["execute:ownership","read:ownership","actionable-denied"]
    cases.append(dict(case="ownership-denied",events=list(events),exact_primary_preserved=True))
    # Reuse the unchanged meaningful fixture code against the ACTUAL new driver.
    # Its original broken-main regression remains pinned to its exact historical body.
    namespace={**old.__dict__,"c":c,"driver":driver,"ROOT":ROOT}
    lifecycle=FunctionType(old.lifecycle_controls.__code__,namespace)(rows)
    assert len(cases)==6 and len(lifecycle)==8
    path_source=function(c.secure_file(ROOT,"scripts/check_mainchip_built_engine_route_prefix.py").read_text(),"path_controls")
    before="import mainchip_built_engine_route_prefix_native as adapter"
    after="import mainchip_fixed_engine_route_prefix_native as adapter"
    assert path_source.count(before)==1
    path_source=path_source.replace(before,after,1)
    exec(compile(path_source,"<actual-fixed-prefix-path-controls>","exec"),namespace)
    paths=namespace["path_controls"]()
    assert paths["positive_paths"]==3 and paths["refused_paths"]==13
    assert paths["actual_native_executed"] is False
    return dict(sequencing_count=6,sequencing_cases=cases,lifecycle_count=8,lifecycle_cases=lifecycle,
        path_controls=paths,actual_new_driver_main_executed=True,
        synthetic_native_thread_signal_and_ownership=True,native_executed=False)


def original_controls():
    capture=io.StringIO()
    with contextlib.redirect_stdout(capture):old.main()
    result=json.loads(capture.getvalue())
    assert result["status"]=="PASS_SHARED_PREFIX_SOURCE_CONTROLS"
    assert (result["positive_count"],result["refusal_count"],len(result["sequencing_cases"]),result["lifecycle_count"])==(4,23,6,8)
    assert all(result[k]is False for k in ("native_prefix_executed","native_routing_executed","physical_acceptance"))
    return result


def copied_projection(root,base,method):
    target=base/"projected";target.mkdir()
    for name in [*method["protected"],c.METHOD]:
        dst=target/name;dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(c.secure_file(root,name),dst)
    assert c.method(target)==method
    # Recursive required producer methods and runtime receipt must exist in the
    # copied protected tree, without falling back to the original checkout.
    proof=c.runtime_qualification(target)
    assert c.RUNTIME_RUN==40858216637 and c.RUNTIME_SOURCE_SHA=="1812666a357bb8aca75bcfc5e1c523106ad7b08e"
    assert len(c.RUNTIME_REQUIRED)==48
    assert {key:proof[key]for key in ("run","source","release_id","receipt_sha256",
        "runtime_qualified","proof_files","runtime_dependency_files","all_net_count","all_instance_count")}==dict(
        run=40858216637,source="1812666a357bb8aca75bcfc5e1c523106ad7b08e",release_id=427727176,
        receipt_sha256="d7a4bccbf2437eaa836955c77cb1013e0ea2e701c01c922e13217ddc701dd10a",
        runtime_qualified=True,proof_files=48,runtime_dependency_files=104,
        all_net_count=143820,all_instance_count=153130)
    assert proof["engine"]==c.ENGINE and proof["input"]==c.INPUT
    assert all(proof[k]is False for k in ("native_routing_executed","physical_acceptance","observer_equivalence_qualified"))
    cases=[]
    for name in sorted(c.RUNTIME_REQUIRED):
        path=target/name;raw=path.read_bytes()
        try:
            path.write_bytes(raw+b"\n")
            refuse(cases,"runtime-proof:"+name,lambda:c.runtime_qualification(target),"runtime proof bytes: "+name)
        finally:path.write_bytes(raw)
    receipt_name=c.RUNTIME_PREFIX+"receipt.json";path=target/receipt_name;raw=path.read_bytes()
    for mode in ("missing","symlink"):
        try:
            path.unlink()
            if mode=="symlink":path.symlink_to(target/c.PRIOR)
            refuse(cases,"runtime-receipt:"+mode,lambda:c.runtime_qualification(target),
                "path symlink" if mode=="symlink" else "missing regular file",missing=True)
        finally:
            if path.is_symlink():path.unlink()
            path.write_bytes(raw)
    assert len(cases)==50
    source_cases=[]
    for name,mode in (("scripts/cloud_mainchip_fixed_engine_route_prefix.py","tampered"),
                      ("scripts/cloud_mainchip_fixed_engine_route_prefix.py","missing"),
                      (c.PRIOR,"tampered"),(c.PRIOR,"missing"),
                      ("scripts/mainchip_fixed_engine_route_prefix_driver.py","symlink")):
        path=target/name;raw=path.read_bytes()
        try:
            if mode=="tampered":path.write_bytes(raw+b"\n")
            else:
                path.unlink()
                if mode=="symlink":path.symlink_to(target/c.PRIOR)
            refuse(source_cases,"projection:"+name+":"+mode,lambda:c.method(target),missing=True)
        finally:
            if path.is_symlink():path.unlink()
            path.write_bytes(raw)
    assert len(source_cases)==5
    assert c.method(target)==method and c.runtime_qualification(target)==proof
    return target,dict(positive_count=1,proof_file_count=48,refusal_count=50,cases=cases,
        source_refusal_count=5,source_cases=source_cases,
        copied_protected_source_only=True,recursive_prior_methods_and_full_receipt_validated=True,
        runtime_proof=proof,actual_native_archive_acquired=False)


def publication_controls(fixture,base,method):
    # Fail immediately if a recursive producer method was omitted from the new
    # method map. Do not mock method admission in the production publish path.
    assert c.method(fixture)==method
    raw=c.secure_file(ROOT,"scripts/check_mainchip_fixed_engine_runtime_host.py").read_text()
    fn=function(raw,"publication_controls")
    before="runtime-probe-evidence.tar.gz";after="route-prefix-evidence.tar.gz"
    assert fn.count(before)==1
    namespace={**old_host.__dict__,"c":c,"h":host,"ROOT":ROOT,
        "environment":environment,"reservation":reservation}
    exec(compile(fn.replace(before,after,1),"<actual-fixed-prefix-publication-controls>","exec"),namespace)
    result=namespace["publication_controls"](fixture,base)
    assert result["status"]=="PASS_ACTUAL_FAILURE_AND_EMPTY_PUBLICATION_CONTROLS" and result["count"]==7
    assert c.method(fixture)==method
    result.update(actual_new_prefix_publish_and_pack=True,original_seven_fixture_bodies_preserved_except_archive_name=True)
    return result


def controls():
    ctx=c.context(os.environ);method=c.method(ROOT)
    c.require(method["source_controls_authorized"]is True,"prefix source controls disabled")
    c.require(subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==ctx["source"],
        "current prefix source checkout")
    prior=c.decode(c.secure_file(ROOT,c.PRIOR).read_bytes())
    source=derivation(ROOT)
    context=context_controls();authority=method_controls(method,prior)
    legacy=original_controls()
    actual=actual_driver_controls()
    with tempfile.TemporaryDirectory(prefix="fixed-prefix-source-controls-")as temporary:
        base=Path(temporary)
        fixture,proof=copied_projection(ROOT,base,method)
        publication=publication_controls(fixture,base,method)
    assert c.method(ROOT)==method
    return dict(status="PASS_FIXED_ENGINE_ROUTE_PREFIX_SOURCE_CONTROLS",
        current_context=dict(source=ctx["source"],run_id=int(ctx["token"].split("-")[0]),attempt=1,
            source_controls_only=True,native_executed=False),
        context_controls=context,authority_controls=authority,derivation=source,
        original_prefix_controls=legacy,actual_driver_controls=actual,
        runtime_proof_controls=proof,publication_controls=publication,
        native_executed=False,native_prefix_executed=False,native_routing_executed=False,
        actual_runtime_probe_executed=False,prefix_qualified=False,observer_equivalence_qualified=False,
        physical_acceptance=False)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path);args=parser.parse_args()
    report=controls();raw=encoded(report)
    if args.output:args.output.write_bytes(raw)
    else:print(raw.decode(),end="")
    return 0


if __name__=="__main__":raise SystemExit(main())
