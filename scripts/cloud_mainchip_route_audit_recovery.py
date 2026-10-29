#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""New owned audit execution using an unchanged frozen historical native program."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
from types import FunctionType,SimpleNamespace
import mainchip_route_audit_recovery_contract as a
import mainchip_route_audit_recovery_restore as recovery
import mainchip_route_recovery_evidence as evidence
import mainchip_built_engine_route_tail_contract as c
import cloud_mainchip_built_engine_route_tail as old
from mainchip_witness_engine_build import fingerprint,terminal_availability
import wait_cloud_tested_source_release as reservation
ROOT=Path(__file__).resolve().parents[1]


def owned_work(ctx,create=False):
    a.validate_context(ctx)
    base=Path(os.environ["RUNNER_TEMP"])
    c.require(base.is_absolute()and not base.is_symlink(),"runner temp")
    work=base/(a.group(ctx["mode"])+"-"+ctx["token"])
    c.require(not work.is_symlink(),"recovery work symlink")
    if create:
        work.mkdir(mode=0o700);c.atomic_record(work/"owner.json",ctx)
    c.require(a.canonical(c.decode((work/"owner.json").read_bytes()))==a.canonical(ctx),"recovery owned work identity")
    return work


def terminal_contract(out,report,ctx,saved):
    a.validate_context(ctx)
    c.require(report["source"]==ctx["source"]and report["mode"]==ctx["mode"]and report["stage"]=="audit",
      "new audit host identity")
    # A temporary comparison view tells the unchanged validator what its frozen
    # native request actually says. Neither old native JSON nor host JSON changes.
    row=old.terminal_contract(out,dict(report,source=evidence.SOURCE))
    c.require(a.canonical({k:row[k]for k in ("source","mode","stage","run_id","engine")})==
      a.canonical(saved["old_audit_context"]),"frozen native request result binding")
    lineage=row["route_lineage"]
    c.require(lineage["original_route_job_conclusion"]=="failure"
      and lineage["original_run_conclusion"]=="failure"
      and lineage["original_audit_jobs_conclusion"]=="skipped"
      and lineage["original_audits_succeeded"]is False
      and lineage["future_audits_are_new_execution"]is True
      and a.canonical(lineage["new_host_context"])==a.canonical(ctx),"new audit/historical route lineage")
    c.require([x["label"]for x in row["commands"]]==list(c.PHASES[1:])
      and all(x["requested_timeout_seconds"]==1200 and x["returncode"]==0
        and x["supervision_failure"]is None for x in row["commands"]),"five unchanged audit commands")
    c.require(row["route_command"]==evidence.source_guard()["cases"][ctx["mode"]]["case-result.json"]["commands"][0],
      "original route command rewritten")
    c.require(all(row[k]is False for k in a.REQUIRE_FALSE),"new audit cannot accept design")
    return row


def cloned_probe(ctx,saved):
    """Keep the qualified probe/cleanup body; adapt only identity and restore seams."""
    a.validate_context(ctx)
    def method_view(root):
        if Path(root).resolve()==ROOT:a.source_guard()
        return c.method(root)
    def write(path,value):
        path=Path(path)
        if path.name=="request.json":
            work=owned_work(ctx)
            c.require(path==work/"request.json"and a.canonical(value)==a.canonical(dict(
              mode=ctx["mode"],stage="audit",source=ctx["source"],run_id=ctx["run_id"],engine=c.ENGINE)),
              "unexpected current request at frozen execution boundary")
            c.atomic_record(work/"out/current-host-request.json",dict(new_host_context=ctx,
              host_request=value,frozen_native_request=saved["old_audit_context"],
              newly_executed_audits=True,original_skipped_audits_succeeded=False))
            c.atomic_record(path,saved["old_audit_context"])
            shutil.copyfile(path,work/"out/frozen-native-request.json")
        else:
            c.atomic_record(path,value)
            if path.name=="release-reservation.json":
                shutil.copyfile(ROOT/a.METHOD,path.parent/"recovery-method.json")
                shutil.copyfile(ROOT/a.CONTROLS,path.parent/a.CONTROLS)
    def finish(path,report,failure_status,primary=None):
        report.update(new_host_context=ctx,frozen_native_context=saved["old_audit_context"],
          audit_execution_is_new=True,original_run_conclusion="failure",original_route_job_conclusion="failure",
          original_audit_jobs_conclusion="skipped",original_audits_succeeded=False,
          rerouting_performed=False,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
        return c.finish_record(path,report,failure_status,primary)
    proxy=SimpleNamespace(**vars(c))
    proxy.context=lambda env:a.context(env)
    proxy.group=a.group;proxy.method=method_view;proxy.finish_record=finish
    namespace=dict(old.probe.__globals__)
    namespace.update(ROOT=ROOT,c=proxy,owned_work=owned_work,write=write,
      handoff=SimpleNamespace(restore=recovery.restore),
      terminal_contract=lambda out,report:terminal_contract(out,report,ctx,saved))
    call=FunctionType(old.probe.__code__,namespace,old.probe.__name__,old.probe.__defaults__,old.probe.__closure__)
    c.require(call.__code__ is old.probe.__code__,"changed owned audit lifecycle body")
    return call


def probe():
    ctx=a.context(os.environ);a.authorize(ctx)
    saved=evidence.expected_case(ctx["mode"])
    # No route codepath is reachable: context() can only construct stage audit.
    return cloned_probe(ctx,saved)()


def regular_outputs(out):
    out=Path(out)
    c.require(out.is_dir()and not any(p.is_symlink()for p in (out,*out.parents)),"owned output root")
    files={}
    for path in sorted(Path(out).rglob("*")):
        c.require(not path.is_symlink()and(path.is_file()or path.is_dir()),"recovery output special entry")
        if path.is_file():files[path.relative_to(out).as_posix()]=fingerprint(path)
    return files


def publication_plan(out,ctx):
    out=Path(out);a.validate_context(ctx)
    direct=("host-result.json","inner-result.json","case-result.json","observer-diagnosis.json",
      "writer-raw.json","method.json","recovery-method.json",a.CONTROLS,"route-tail-controls.json",
      "release-reservation.json","container-initial.json","container-terminal.json","runtime-observed.json",
      "publication-availability.json","current-host-request.json","frozen-native-request.json",
      "recovery-host-context.json","recovery-admission.json","recovery-restoration.json",
      "route-source-envelope.json","route-restoration.json","route-host-result.json","route-inner-result.json",
      "route-case-result.json","route-route-handoff.json","route-route-handoff-inventory.json",
      "route-outputs.json","route-parts.json","route-method.json",
      "owned-container-start.stdout","owned-container-start.stderr")
    paths=[out/name for name in direct]
    for folder in (out/"supervision",out/"witness"):
        if folder.is_dir():paths.extend(p for p in sorted(folder.iterdir())if p.suffix in (".json",".jsonl",".stdout",".stderr"))
    rows=[];names=set()
    for path in paths:
        c.require(not path.is_symlink(),"direct publication symlink")
        relative=path.relative_to(out).as_posix()
        if not path.exists():
            rows.append(dict(path=relative,present=False,publication="absent"));continue
        c.require(path.is_file(),"nonregular direct publication")
        receipt=fingerprint(path)
        c.require(path.name not in names,"direct publication name collision");names.add(path.name)
        rows.append(dict(path=relative,name=path.name,present=True,**receipt,
          archive_member=relative,publication="direct"if receipt["bytes"]>0 else"archive_only_empty"))
    return dict(schema="audit-recovery-direct-publication-plan-v1",new_host_context=ctx,files=rows,
      empty_streams_retained_in_full_archive=True,original_records_unchanged=True,physical_acceptance=False)


def pack(work,out,ctx):
    work,out=Path(work),Path(out);a.validate_context(ctx)
    c.require(out==work/"out"and out.is_dir()and not any(p.is_symlink()for p in (out,*out.parents)),"owned publication root")
    c.atomic_record(out/"publication-availability.json",terminal_availability(out))
    plan=publication_plan(out,ctx);c.atomic_record(out/"direct-publication-plan.json",plan)
    # Do not edit/parse native result bodies to make failure publication succeed.
    files=regular_outputs(out)
    c.require(not any(name in files for name in ("outputs.json","parts.json","publication.json")),
      "publication already prepared")
    c.atomic_record(out/"outputs.json",dict(source=ctx["source"],run_id=ctx["run_id"],mode=ctx["mode"],stage="audit",
      original_source=evidence.SOURCE,original_run=evidence.RUN,files=files,
      newly_executed_audit_evidence=True,original_jobs_remain_failed=True,physical_acceptance=False))
    total=sum(row["bytes"]for row in files.values())
    c.require(shutil.disk_usage(work).free>=2*total+2*1024**3,"recovery publication disk budget")
    archive=work/"audit-recovery-evidence.tar.gz"
    with tarfile.open(archive,"x:gz")as tar:
        for path in sorted(out.iterdir()):tar.add(path,arcname=path.name,recursive=True)
    parts=[]
    with archive.open("rb")as stream:
        i=0
        while True:
            raw=stream.read(512*1024**2)
            if not raw:break
            path=work/("audit-recovery-evidence.tar.gz.part%03d"%i)
            with path.open("xb")as target:target.write(raw)
            parts.append(dict(name=path.name,**fingerprint(path)));i+=1
    c.atomic_record(out/"parts.json",dict(archive=fingerprint(archive),parts=parts))
    uploads=[out/row["path"]for row in plan["files"]if row["publication"]=="direct"]
    uploads+=[out/"direct-publication-plan.json",out/"outputs.json",out/"parts.json"]
    uploads+=[work/row["name"]for row in parts]
    c.require(len({p.name for p in uploads})==len(uploads)
      and all(fingerprint(p)["bytes"]>0 for p in uploads),"only nonempty unique direct uploads")
    return plan,uploads


def publish_asset(path,ctx,release_id,read,upload):
    c.require(path.is_file()and not path.is_symlink(),"publication regular file")
    expected=fingerprint(path);c.require(expected["bytes"]>0,"empty direct upload forbidden")
    tag="cloud-results-"+ctx["token"]+"-"+a.group(ctx["mode"])
    def current():
        info=read("releases/tags/"+tag);ref=read("git/ref/tags/"+tag)
        reservation.release.validate_release(info,ref,tag,ctx["source"])
        c.require(info["id"]==release_id,"new recovery release identity")
        return info
    info=current();same=[r for r in info["assets"]if r["name"]==path.name];reused=bool(same)
    if same:
        c.require(len(same)==1 and same[0]["size"]==expected["bytes"]
          and same[0]["digest"]=="sha256:"+expected["sha256"],"recovery asset conflict")
    else:upload(tag,path)
    info=current();same=[r for r in info["assets"]if r["name"]==path.name]
    c.require(len(same)==1 and same[0]["size"]==expected["bytes"]
      and same[0]["digest"]=="sha256:"+expected["sha256"],"recovery published asset mismatch")
    return dict(name=path.name,**expected,reused_identical=reused)


def publish():
    ctx=a.context(os.environ);work=owned_work(ctx);out=work/"out"
    report=dict(status="FAIL_RECOVERY_PUBLICATION",new_host_context=ctx,assets=[],terminal_errors=[],physical_acceptance=False)
    primary=None
    try:
        # Source failure is recorded, never used to suppress available failure evidence.
        c.attempt(report,"current-recovery-source",a.source_guard)
        proof=reservation.wait(a.group(ctx["mode"]),os.environ)
        plan,uploads=pack(work,out,ctx)
        c.require({r["name"]for r in proof["existing_assets"]}<={p.name for p in uploads},"new release asset census")
        def upload(tag,path):
            subprocess.run(["gh","release","upload",tag,str(path),"--repo",c.REPOSITORY],check=True,timeout=1800)
        for path in uploads:
            report["assets"].append(publish_asset(path,ctx,proof["release_id"],reservation.release.api,upload))
        live=reservation.release.api("releases/"+str(proof["release_id"]))
        c.require({x["name"]:(x["size"],x["digest"])for x in live["assets"]}==
          {x["name"]:(x["bytes"],"sha256:"+x["sha256"])for x in report["assets"]},"full new publication census")
        report.update(status="PASS_PERMANENT_AUDIT_EVIDENCE_NOT_ACCEPTANCE",release_id=proof["release_id"],
          empty_direct_uploads=0,plan=fingerprint(out/"direct-publication-plan.json"))
    except BaseException as exc:
        primary=exc;report["failure"]=c.error_record("recovery-publication",exc)
    finally:c.finish_record(out/"publication.json",report,"FAIL_RECOVERY_PUBLICATION",primary)
    return 0 if report["status"].startswith("PASS_")else 1


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("action",choices=("probe","publish"))
    sys.exit({"probe":probe,"publish":publish}[parser.parse_args().action]())
