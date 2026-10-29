#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only full frozen restore, separately owned tails and permanent evidence."""
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
import mainchip_built_engine_route_tail_contract as c
import mainchip_built_engine_route_tail_handoff as handoff
from mainchip_witness_engine_build import (
 fingerprint, execute_command, create_owned, cleanup_owned, terminal_availability)
import wait_cloud_tested_source_release as reservation
ROOT=Path(__file__).resolve().parent.parent

def write(path,value):c.atomic_record(path,value)

def owned_work(ctx,create=False):
    base=Path(os.environ["RUNNER_TEMP"])
    c.require(base.is_absolute() and not base.is_symlink(),"runner temp")
    work=base/(c.group(ctx["mode"],ctx["stage"])+"-"+ctx["token"])
    c.require(not work.is_symlink(),"work symlink")
    if create:
        work.mkdir(mode=0o700);write(work/"owner.json",ctx)
    c.require(c.decode((work/"owner.json").read_bytes())==ctx,"owned work identity")
    return work

def restore_prefix(work,out):
    from route_cloud_newer_postcts import fetch
    inv=c.prefix_contract(ROOT);read=reservation.release.api
    proof=c.envelope(ROOT,read("actions/runs/"+str(c.PREFIX_RUN)),
        read("actions/runs/"+str(c.PREFIX_RUN)+"/jobs?per_page=100"),
        read("releases/"+str(c.PREFIX_RELEASE)),read("git/ref/tags/"+c.PREFIX_TAG))
    write(out/"prefix-envelope.json",proof)
    transport=work/"prefix-transport";transport.mkdir()
    manifest=c.saved(ROOT,"parts")
    url="https://github.com/"+c.REPOSITORY+"/releases/download/"+c.PREFIX_TAG+"/"
    for part in manifest["parts"]:
        path=transport/part["name"]
        fetch(url+part["name"],part["sha256"],path)
        c.require(fingerprint(path)=={k:part[k] for k in ("bytes","sha256")},"prefix part identity")
    archive=transport/"prefix.tar.gz"
    with archive.open("xb") as target:
        for part in manifest["parts"]:
            with (transport/part["name"]).open("rb") as source:shutil.copyfileobj(source,target,4*1024**2)
    c.require(fingerprint(archive)==manifest["archive"],"complete outer archive identity")
    expected=dict(c.saved(ROOT,"outputs")["files"])
    expected["outputs.json"]=fingerprint(c.secure_file(ROOT,c.PREFIX+".outputs.json"))
    outer=transport/"outer"
    with archive.open("rb") as stream:
        full=c.engine_extract(stream,outer,expected,tuple(expected),c.LIMITS["archive_expanded_limit"])
    frozen=c.saved(ROOT,"frozen-prefix")
    c.require(fingerprint(outer/"frozen-native-workspace.tar.gz")==frozen["archive"]
        and fingerprint(outer/"frozen-prefix-inventory.json")==frozen["inventory"],"nested frozen archive identities")
    c.require(c.decode((outer/"frozen-prefix-inventory.json").read_bytes())==inv,"complete frozen map equality")
    restored=transport/"restored"
    with (outer/"frozen-native-workspace.tar.gz").open("rb") as stream:
        nested=c.engine_extract(stream,restored,inv["files"],tuple(inv["files"]),c.LIMITS["archive_expanded_limit"])
    # Only owned, newly extracted roots are relocated. Existing out contains current provenance.
    for p in sorted(restored.iterdir()):
        if p.name=="out":
            c.require(set(x.name for x in p.iterdir())=={"work"} and not (out/"work").exists(),"frozen out projection")
            (p/"work").rename(out/"work")
        else:
            c.require(not (work/p.name).exists(),"frozen destination collision")
            p.rename(work/p.name)
    c.frozen_unchanged(work,inv)
    c.require(nested["all_files"]==inv["files"] and nested["all_regular_members_verified"] is True
        and nested["unpacked_bytes"]==c.FROZEN_BYTES,"frozen census")
    shutil.copyfile(c.secure_file(ROOT,c.PREFIX+".frozen-prefix-inventory.json"),work/"frozen-manifest.json")
    (work/"engine/openroad").chmod(0o500)
    write(out/"prefix-restoration.json",dict(outer=full,nested=nested,
        frozen_inventory=fingerprint(work/"frozen-manifest.json"),
        complete_outer_archive_verified=True,complete_746_native_projection_verified=True,
        native_archives_remain_in_cloud=True))
    return inv

def terminal_contract(out,report):
    state=report["container_terminal"]["State"]
    c.require(not state["Running"] and not state["OOMKilled"] and state["ExitCode"]==0 and not state["Error"],"container failure")
    inner=c.decode(c.secure_file(out,"inner-result.json").read_bytes())
    case=c.decode(c.secure_file(out,"case-result.json").read_bytes())
    stage=report["stage"]
    c.require(stage in ("route","audit") and inner["stage"]==stage
        and inner["status"]=="PASS_BUILT_ELF_ACTUAL_"+stage.upper()+"_STAGE"
        and not inner["terminal_errors"],"inner failure")
    c.require(all(x["returncode"]==0 and not x["timed_out"] for x in inner["commands"]),"inner command failure")
    expected="PASS_ROUTE_ONLY_AWAITING_ORIGINAL_AUDITS" if stage=="route" else "PASS_COMPLETE_ROUTE_TAIL_DIAGNOSTIC"
    c.require(case["status"]==expected and not case["terminal_errors"],"tail failure")
    c.require(case["source"]==report["source"] and case["mode"]==report["mode"] and case["stage"]==stage,"tail request join")
    return case

def probe():
    ctx=c.context(os.environ);m=c.method(ROOT)
    c.require(ctx["mode"] in c.MODES and ctx["stage"] in ("route","audit")
        and m["native_"+ctx["stage"]+"_authorized"],"native stage not authorized")
    c.require(subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==ctx["source"],"checkout identity")
    work=owned_work(ctx,True);out=work/"out";out.mkdir()
    report=dict(schema="built-engine-route-tail-host-v1",source=ctx["source"],mode=ctx["mode"],stage=ctx["stage"],
        status="IN_PROGRESS",physical_acceptance=False,observer_equivalence_qualified=False,
        commands=[],terminal_errors=[],creation_attempted=False)
    primary=None;identity=None;handlers={};projected=False;restored=False;started=time.monotonic()
    def command(label,argv,timeout=120):return execute_command(report,out,label,argv,timeout)
    def inspect_one(value):return c.decode(subprocess.check_output(["docker","inspect",value],timeout=30))[0]
    def interrupted(sig,frame):raise RuntimeError("owned tail interrupted by signal "+str(sig))
    try:
        for sig in (signal.SIGINT,signal.SIGTERM):handlers[sig]=signal.signal(sig,interrupted)
        proof=reservation.wait(c.group(ctx["mode"],ctx["stage"]),os.environ)
        c.require(not proof["existing_assets"],"tail release not empty")
        write(out/"release-reservation.json",proof)
        shutil.copyfile(ROOT/c.METHOD,out/"method.json")
        shutil.copyfile(ROOT/"route-tail-controls.json",out/"route-tail-controls.json")
        c.require(shutil.disk_usage(work).free>=c.LIMITS["min_free_disk_bytes"],"scratch disk budget")
        if ctx["stage"]=="route":restore_prefix(work,out)
        else:handoff.restore(work,out,ROOT,ctx,os.environ)
        restored=True
        projection=work/"tail-source"
        if ctx["stage"]=="route":
            projection.mkdir()
            for p in [*m["protected"],c.METHOD]:
                target=projection/p;target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(c.secure_file(ROOT,p),target)
        c.method(projection);projected=True
        write(work/"request.json",dict(mode=ctx["mode"],stage=ctx["stage"],source=ctx["source"],
            run_id=int(os.environ["GITHUB_RUN_ID"]),engine=c.ENGINE))
        shutil.copyfile(ROOT/"scripts/mainchip_built_engine_route_tail_inner.py",work/"inner.py")
        command("immutable-image-pull",["docker","pull",c.IMAGE],1800)
        image=c.decode(command("image-inspect",["docker","image","inspect",c.IMAGE]))[0];c.validate_image(image)
        identity=create_owned(ctx,work,report,command,c.create_argv(ctx,work,os.getuid(),os.getgid()))
        info=inspect_one(identity);c.validate_container(info,ctx,work);write(out/"container-initial.json",info)
        command("owned-container-start",["docker","start","--attach",identity],c.stage_limits(ctx["stage"])["container_seconds"])
    except BaseException as exc:
        primary=exc;report["failure"]=c.error_record("built-engine-route-tail",exc)
    finally:
        cleanup_owned(ctx,work,report,identity,report["creation_attempted"],inspect_one,command)
        c.attempt(report,"checkout-source-unchanged",lambda:c.method(ROOT))
        if projected:c.attempt(report,"projected-tail-source-unchanged",lambda:c.method(work/"tail-source"))
        if restored:c.attempt(report,"frozen-prefix-unchanged",lambda:c.frozen_unchanged(work,
            c.decode(c.secure_file(work,"frozen-manifest.json").read_bytes())))
        if restored and ctx["stage"]=="audit":
            c.attempt(report,"route-projection-unchanged",lambda:c.frozen_unchanged(work,
                c.decode(c.secure_file(work,"route-projection.json").read_bytes())))
        if report["creation_attempted"]:c.attempt(report,"actual-tail-terminal",lambda:terminal_contract(out,report))
        for sig,old in handlers.items():c.attempt(report,"restore-signal-"+str(sig),lambda sig=sig,old=old:signal.signal(sig,old))
        report["elapsed_seconds"]=time.monotonic()-started
        report["status"]=("PASS_OWNED_"+ctx["stage"].upper()+"_STAGE_DIAGNOSTIC"
            if identity is not None and primary is None and not report["terminal_errors"] else "FAIL_OWNED_ROUTE_TAIL")
        c.finish_record(out/"host-result.json",report,"FAIL_OWNED_ROUTE_TAIL",primary)
    return 0 if report["status"].startswith("PASS_") else 1

def freeze_route():
    ctx=c.context(os.environ);m=c.method(ROOT)
    c.require(ctx["stage"]=="route" and ctx["mode"] in c.MODES and m["native_route_authorized"],
        "route handoff not authorized")
    work=owned_work(ctx)
    return handoff.freeze(work,work/"out",ROOT)

def publish_asset(path,ctx,release_id,read,upload):
    c.require(path.is_file() and not path.is_symlink(),"publication regular file")
    expected=fingerprint(path);tag="cloud-results-"+ctx["token"]+"-"+c.group(ctx["mode"],ctx["stage"])
    def current():
        info=read("releases/tags/"+tag);ref=read("git/ref/tags/"+tag)
        reservation.release.validate_release(info,ref,tag,ctx["source"])
        c.require(info["id"]==release_id,"reserved release identity")
        return info
    info=current();same=[a for a in info["assets"] if a["name"]==path.name]
    reused=bool(same)
    if same:
        c.require(len(same)==1 and same[0]["size"]==expected["bytes"]
            and same[0]["digest"]=="sha256:"+expected["sha256"],"existing asset conflict")
    else:upload(tag,path)
    info=current();same=[a for a in info["assets"] if a["name"]==path.name]
    c.require(len(same)==1 and same[0]["size"]==expected["bytes"]
        and same[0]["digest"]=="sha256:"+expected["sha256"],"published asset mismatch")
    return dict(name=path.name,**expected,reused_identical=reused)

def publish():
    ctx=c.context(os.environ);c.method(ROOT);work=owned_work(ctx);out=work/"out"
    proof=reservation.wait(c.group(ctx["mode"],ctx["stage"]),os.environ)
    write(out/"publication-availability.json",terminal_availability(out))
    files={}
    for p in sorted(out.rglob("*")):
        c.require(not p.is_symlink() and (p.is_file() or p.is_dir()),"output special entry")
        if p.is_file():files[p.relative_to(out).as_posix()]=fingerprint(p)
    write(out/"outputs.json",dict(source=ctx["source"],mode=ctx["mode"],stage=ctx["stage"],files=files,physical_acceptance=False))
    total=sum(row['bytes'] for row in files.values())
    c.require(shutil.disk_usage(work).free>=2*total+2*1024**3,'complete publication disk budget')
    archive=work/"route-tail-evidence.tar.gz"
    with tarfile.open(archive,"w:gz") as tar:
        for p in sorted(out.iterdir()):tar.add(p,arcname=p.name,recursive=True)
    parts=[]
    with archive.open("rb") as stream:
        i=0
        while True:
            raw=stream.read(512*1024**2)
            if not raw:break
            p=work/("route-tail-evidence.tar.gz.part%03d"%i);p.write_bytes(raw)
            parts.append(dict(name=p.name,**fingerprint(p)));i+=1
    write(out/"parts.json",dict(archive=fingerprint(archive),parts=parts))
    direct=("host-result.json","inner-result.json","case-result.json","observer-diagnosis.json",
        "writer-raw.json","method.json","route-tail-controls.json","release-reservation.json",
        "outputs.json","parts.json","container-initial.json","container-terminal.json",
        "runtime-observed.json","prefix-envelope.json","prefix-restoration.json","publication-availability.json",
        "route-handoff.json","route-handoff-inventory.json","route-source-envelope.json","route-restoration.json",
        "route-host-result.json","route-inner-result.json","route-case-result.json","route-route-handoff.json",
        "route-route-handoff-inventory.json","route-outputs.json","route-parts.json","route-method.json")
    uploads=[out/p for p in direct if (out/p).is_file()]+[work/p["name"] for p in parts]
    for directory in (out/"supervision",out/"witness"):
        if directory.is_dir():
            uploads.extend(p for p in sorted(directory.iterdir()) if p.is_file()
                and p.suffix in (".json",".jsonl",".stdout",".stderr"))
    uploads.extend(out/p for p in ("owned-container-start.stdout","owned-container-start.stderr") if (out/p).is_file())
    planned={p.name for p in uploads}
    c.require(len(planned)==len(uploads)
        and {x["name"] for x in proof["existing_assets"]}<=planned,"publication census")
    def upload(tag,path):
        subprocess.run(["gh","release","upload",tag,str(path),"--repo",c.REPOSITORY],check=True,timeout=1800)
    rows=[publish_asset(p,ctx,proof["release_id"],reservation.release.api,upload) for p in uploads]
    live=reservation.release.api("releases/"+str(proof["release_id"]))
    c.require({a["name"]:(a["size"],a["digest"]) for a in live["assets"]}==
        {r["name"]:(r["bytes"],"sha256:"+r["sha256"]) for r in rows},"full published census")
    write(out/"publication.json",dict(status="PASS_PERMANENT_DIAGNOSTIC_PUBLICATION",
        source=ctx["source"],mode=ctx["mode"],stage=ctx["stage"],release_id=proof["release_id"],assets=rows,physical_acceptance=False))
    return 0

def comparison_body(ctx,work,out):
    from route_cloud_newer_postcts import fetch
    reservation.wait(c.group("compare","compare"),os.environ)
    read=reservation.release.api;cases={};bindings={}
    run=read('actions/runs/'+os.environ['GITHUB_RUN_ID'])
    jobs=read('actions/runs/'+os.environ['GITHUB_RUN_ID']+'/jobs?per_page=100')
    c.require(run['id']==int(os.environ['GITHUB_RUN_ID']) and run['head_sha']==ctx['source']
        and run['run_attempt']==1,'same workflow audit run')
    for mode in c.MODES:
        candidates=[j for j in jobs['jobs'] if j['name']=='audit-only ('+mode+')']
        c.require(len(candidates)==1 and candidates[0]['status']=='completed'
            and candidates[0]['conclusion']=='success','complete audit job required')
        tag="cloud-results-"+ctx["token"]+"-"+c.group(mode,"audit")
        release=read("releases/tags/"+tag);ref=read("git/ref/tags/"+tag)
        reservation.release.validate_release(release,ref,tag,ctx["source"])
        assets={a["name"]:a for a in release["assets"]}
        c.require(len(assets)==len(release["assets"]),"duplicate case asset")
        directory=work/mode;directory.mkdir()
        records={}
        for name in ("host-result.json","inner-result.json","case-result.json","outputs.json","method.json"):
            a=assets[name];c.require(a["digest"].startswith("sha256:") and a["size"]<32*1024**2,"case direct JSON bound")
            p=directory/name;fetch(a["browser_download_url"],a["digest"][7:],p)
            c.require(fingerprint(p)==dict(bytes=a["size"],sha256=a["digest"][7:]),"case asset identity")
            records[name]=c.decode(p.read_bytes())
        c.require((directory/"method.json").read_bytes()==c.secure_file(ROOT,c.METHOD).read_bytes(),"case method equality")
        host=records["host-result.json"];case=terminal_contract(directory,host)
        c.require(host["status"]=="PASS_OWNED_AUDIT_STAGE_DIAGNOSTIC" and host["stage"]=="audit"
            and not host["terminal_errors"],"case host terminal")
        output=records["outputs.json"]
        for name in ("host-result.json","inner-result.json","case-result.json","method.json"):
            c.require(output["files"][name]==fingerprint(directory/name),"direct output join")
        c.require(case["mode"]==mode and case["source"]==ctx["source"]
            and case["run_id"]==int(os.environ["GITHUB_RUN_ID"]),"case current source/run/mode")
        cases[mode]=case
        write(out/("case-"+mode+".json"),case)
        bindings[mode]=dict(release_id=release["id"],tag=tag,audit_job=candidates[0],
            direct_files={name:fingerprint(directory/name) for name in records})
    result=c.compare_cases(cases["off"],cases["on"]);result["authenticated_cases"]=bindings
    return result

def comparison():
    ctx=c.context(os.environ);m=c.method(ROOT)
    c.require(ctx["mode"]=="compare" and m["native_tail_authorized"],"comparison not authorized")
    work=owned_work(ctx,True);out=work/"out";out.mkdir()
    result=dict(status="FAIL_OBSERVER_OFF_ON_OUTPUT_EQUIVALENCE",source=ctx["source"],
        terminal_errors=[],physical_acceptance=False,observed_equivalence=False)
    primary=None
    try:result.update(comparison_body(ctx,work,out))
    except BaseException as exc:
        primary=exc;result["failure"]=c.error_record("comparison",exc)
    finally:
        c.attempt(result,"comparison-source-terminal",lambda:c.method(ROOT))
        # The record is durable before either publication or rethrow.
        try:c.finish_record(out/"comparison.json",result,"FAIL_OBSERVER_OFF_ON_OUTPUT_EQUIVALENCE",primary)
        except BaseException as exc:
            if primary is None:primary=exc
        try:
            proof=reservation.wait(c.group("compare","compare"),os.environ)
            def upload(tag,path):
                subprocess.run(["gh","release","upload",tag,str(path),"--repo",c.REPOSITORY],check=True,timeout=1800)
            for path in sorted(out.glob("*.json")):
                publish_asset(path,ctx,proof["release_id"],reservation.release.api,upload)
        except BaseException as exc:
            if primary is None:primary=exc
            else:
                try:print("COMPARISON_PUBLICATION_FAILURE "+repr(exc),flush=True)
                except BaseException:pass
    if primary is not None:raise primary
    return 0 if result["observed_equivalence"] and not result["terminal_errors"] else 1

if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("action",choices=("probe","handoff","publish","compare"))
    action=parser.parse_args().action
    if action=="handoff":
        print(json.dumps(freeze_route(),sort_keys=True))
    else:sys.exit({"probe":probe,"publish":publish,"compare":comparison}[action]())
