#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted single routing continuation; no repeated diode creation or antenna repair."""
import argparse,os,json,shutil,subprocess,sys
from pathlib import Path
import cloud_mainchip_bulk_postdrt_antenna as base
import mainchip_saved_diode_routing as plan
import cloud_mainchip_saved_diode_reconstruction as predecessor
from cloud_mainchip_bulk_postdrt_antenna import (
 f,c,p,tail,build,ROOT,BRANCH,GROUP,CURRENT,OUTER_SECONDS,context,control_evidence,
 reservation,acquire_current,publish_capsule,preserve_outputs,retained_workspace,emit)
MANIFEST="scripts/mainchip-saved-diode-routing-pins.json"

def source_gate():
    inherited=predecessor.source_gate()
    manifest=f.decode(c.secure_file(ROOT,MANIFEST).read_bytes())
    f.require(manifest["schema"]=="saved-diode-routing-pins-v1","routing source schema")
    f.require(manifest["native_repair_authorized"]is False and manifest["diode_reconstruction_authorized"]is False
      and manifest["scoped_routing_authorized"]is True,"only scoped routing continuation")
    required=set(inherited["files"])|{predecessor.MANIFEST,
      "scripts/mainchip_saved_diode_routing_native.py","scripts/mainchip_saved_diode_routing_inner.py",
      "scripts/cloud_mainchip_saved_diode_routing.py","scripts/check_mainchip_saved_diode_routing.py",
      "scripts/mainchip_saved_diode_routing.py","scripts/mainchip_fast_insertion_def.py","scripts/check_mainchip_fast_insertion_def.py"}
    f.require(required<=set(manifest["files"]),"complete unchanged original and continuation sources")
    for path,digest in manifest["files"].items():
        f.require(f.file_digest(c.secure_file(ROOT,path))["sha256"]==digest,"routing source pin: "+path)
    f.require(all(manifest[k]is False for k in p.FLAGS),"routing cannot authorize final acceptance")
    return manifest
def authorize_native(manifest):
    f.require(manifest["scoped_routing_authorized"]is True and manifest["native_repair_authorized"]is False
      and manifest["diode_reconstruction_authorized"]is False,"only one scoped saved-candidate routing continuation")
    return dict(scoped_routing=True,repair_antennas=False,reconstruction=False,**p.FLAGS)

def cleanup_preserved_workspace(ctx,evidence):
    """Called only after successful workflow artifact upload, never by perform()."""
    work=Path(os.environ["RUNNER_TEMP"])/(GROUP+"-"+ctx["token"])
    if not work.exists()and not work.is_symlink():return dict(absent=True)
    f.require(not work.is_symlink()and work.is_dir(),"cleanup workspace type")
    f.require(not (work/"owner.json").is_symlink()and f.decode((work/"owner.json").read_bytes())==ctx,"cleanup owner")
    try:
        report=f.decode((Path(evidence)/"result.json").read_bytes())
        complete=report.get("status")=="COMPLETE_SAVED_DIODE_ROUTING_CLOUD_EXPERIMENT" and report.get(
            "output_preservation",{}).get("complete")is True and report.get(
            "workspace_retained",{}).get("path")==str(work) and report.get("native_publication",{}).get("status")=="COMPLETE_PERMANENT_NATIVE_CAPSULE"
    except BaseException as exc:
        return dict(absent=False,retained=True,reason="Missing or unreadable terminal preservation record",error=repr(exc))
    if not complete:return dict(absent=False,retained=True,reason="Failed or incomplete preservation remains owned")
    shutil.rmtree(work);f.require(not work.exists(),"cleanup incomplete")
    return dict(absent=True,removed_owned_workspace=True)


def acquire_failed(work,evidence):
    import types
    import cloud_mainchip_full_antenna_readback as reader
    prefix="docs/evidence/mainchip-bulk-namespace-real-repair-terminal-41172959321/capsule-metadata/"
    outputs=f.decode(c.secure_file(ROOT,prefix+"candidate-outputs.json").read_bytes())
    parts=f.decode(c.secure_file(ROOT,prefix+"candidate-parts.json").read_bytes())
    run=f.api("actions/runs/41172959321")
    jobs=f.api("actions/runs/41172959321/attempts/1/jobs?per_page=100")
    release=f.api("releases/429743993")
    tag="cloud-results-41172959321-1-mainchip-bulk-postdrt-antenna"
    ref=f.api("git/ref/tags/"+tag)
    expected="4c672914056e61ed6af094d1d46a116f5c07620e"
    f.require(run["head_sha"]==expected and run["status"]=="completed"and run["conclusion"]=="failure"
      and run["run_attempt"]==1 and run["workflow_id"]==401215446,"failed producer")
    outcomes={"source-controls":"success","preserve-job-log":"success","trial":"failure","preserve-antenna-job-logs":"success"}
    f.require(len(jobs["jobs"])==4 and {j["name"]:j["conclusion"]for j in jobs["jobs"]}==outcomes,"complete failed producer jobs")
    f.require(all(j["head_sha"]==expected and j["run_id"]==41172959321 and j["status"]=="completed"for j in jobs["jobs"]),"producer jobs identity")
    f.require(release["id"]==429743993 and release["tag_name"]==tag and release["target_commitish"]==expected
      and release["draft"]is False and release["prerelease"]is True and ref["object"]["type"]=="commit"
      and ref["object"]["sha"]==expected,"failed producer capsule identity")
    p.exact(outputs["input"],CURRENT,"original accepted source")
    f.require(outputs["source"]==expected and outputs["run"]==41172959321 and outputs["attempt"]==1
      and len(outputs["files"])==65,"full failed output census")
    p.exact(parts["archive"],dict(bytes=304831102,sha256="01b48941ab1b6b351ab2a0e6cb18dc6c3f2e5ede34d2d98227eacf12c036d87a"),"failed archive")
    assets={a["name"]:dict(id=a["id"],bytes=a["size"],sha256=a["digest"].removeprefix("sha256:"))for a in release["assets"]}
    f.require(len(assets)==len(release["assets"])==3 and set(assets)==
      {"candidate-outputs.json","candidate-parts.json","candidate-native.tar.gz.part000"},"exact failed assets")
    for row in parts["parts"]:
        p.exact({k:assets[row["name"]][k]for k in("bytes","sha256")},{k:row[k]for k in("bytes","sha256")},"producer asset pin")
    for name,value in(("failed-producer-run.json",run),("failed-producer-jobs.json",jobs),
      ("failed-producer-release.json",release),("failed-producer-ref.json",ref)):
        f.write_new(evidence/name,f.encode(value))
    transport=work/"failed-transport";transport.mkdir()
    original=reader.download
    download=types.FunctionType(original.__code__,dict(original.__globals__,ASSETS=assets),
      original.__name__,original.__defaults__,original.__closure__)
    acquisition=evidence/"failed-acquisition";acquisition.mkdir()
    paths={name:download(name,transport,acquisition)for name in assets}
    p.exact(f.decode(paths["candidate-outputs.json"].read_bytes()),outputs,"full failed received metadata")
    p.exact(f.decode(paths["candidate-parts.json"].read_bytes()),parts,"full failed received parts")
    p.exact(f.file_digest(paths["candidate-native.tar.gz.part000"]),parts["archive"],"full failed archive bytes")
    selected=plan.DONOR_SELECTED
    f.require(selected<=set(outputs["files"]),"complete saved reconstruction inputs")
    observed=reader.restore(paths["candidate-native.tar.gz.part000"],outputs["files"],selected,work/"failed-repair-inputs")
    f.write_new(evidence/"failed-input-restoration.json",f.encode(dict(full_members=observed,selected=sorted(selected),
      full_archive_verified=True,producer_run=41172959321,producer_source=expected,
      native_bytes_remain_in_cloud=True,read_only_acquisition=True,production_candidate=False)))
    shutil.rmtree(transport)

def acquire_reconstruction(work,evidence):
    import types
    import cloud_mainchip_full_antenna_readback as reader
    prefix="docs/evidence/mainchip-diode-reconstruction-terminal-41190910993/capsule-metadata/"
    outputs=f.decode(c.secure_file(ROOT,prefix+"candidate-outputs.json").read_bytes())
    parts=f.decode(c.secure_file(ROOT,prefix+"candidate-parts.json").read_bytes())
    run=f.api("actions/runs/41190910993")
    jobs=f.api("actions/runs/41190910993/attempts/1/jobs?per_page=100")
    release=f.api("releases/429853533")
    tag="cloud-results-41190910993-1-mainchip-bulk-postdrt-antenna"
    ref=f.api("git/ref/tags/"+tag)
    expected="be2f83b2f03190f9f5c6439d63a086dfdf06f3a9"
    f.require(run["head_sha"]==expected and run["status"]=="completed"and run["conclusion"]=="failure"
      and run["run_attempt"]==1 and run["workflow_id"]==401215446,"saved reconstruction producer")
    outcomes={"source-controls":"success","preserve-job-log":"success","diode-reconstruction":"failure","preserve-antenna-job-logs":"success"}
    f.require(len(jobs["jobs"])==4 and {j["name"]:j["conclusion"]for j in jobs["jobs"]}==outcomes,"complete saved reconstruction producer jobs")
    f.require(all(j["head_sha"]==expected and j["run_id"]==41190910993 and j["status"]=="completed"for j in jobs["jobs"]),"producer jobs identity")
    f.require(release["id"]==429853533 and release["tag_name"]==tag and release["target_commitish"]==expected
      and release["draft"]is False and release["prerelease"]is True and ref["object"]["type"]=="commit"
      and ref["object"]["sha"]==expected,"saved reconstruction producer capsule identity")
    p.exact(outputs["input"],CURRENT,"original accepted source")
    f.require(outputs["source"]==expected and outputs["run"]==41190910993 and outputs["attempt"]==1
      and len(outputs["files"])==47,"full reconstruction output census")
    p.exact(parts["archive"],plan.ARCHIVE,"reconstruction archive")
    assets={a["name"]:dict(id=a["id"],bytes=a["size"],sha256=a["digest"].removeprefix("sha256:"))for a in release["assets"]}
    f.require(len(assets)==len(release["assets"])==3 and set(assets)==
      {"candidate-outputs.json","candidate-parts.json","candidate-native.tar.gz.part000"},"exact failed assets")
    for row in parts["parts"]:
        p.exact({k:assets[row["name"]][k]for k in("bytes","sha256")},{k:row[k]for k in("bytes","sha256")},"producer asset pin")
    for name,value in(("reconstruction-producer-run.json",run),("reconstruction-producer-jobs.json",jobs),
      ("reconstruction-producer-release.json",release),("reconstruction-producer-ref.json",ref)):
        f.write_new(evidence/name,f.encode(value))
    transport=work/"reconstruction-transport";transport.mkdir()
    original=reader.download
    download=types.FunctionType(original.__code__,dict(original.__globals__,ASSETS=assets),
      original.__name__,original.__defaults__,original.__closure__)
    acquisition=evidence/"reconstruction-acquisition";acquisition.mkdir()
    paths={name:download(name,transport,acquisition)for name in assets}
    p.exact(f.decode(paths["candidate-outputs.json"].read_bytes()),outputs,"full reconstruction received metadata")
    p.exact(f.decode(paths["candidate-parts.json"].read_bytes()),parts,"full reconstruction received parts")
    p.exact(f.file_digest(paths["candidate-native.tar.gz.part000"]),parts["archive"],"full reconstruction archive bytes")
    selected=plan.RECONSTRUCTION_SELECTED
    f.require(selected<=set(outputs["files"]),"complete saved reconstruction inputs")
    observed=reader.restore(paths["candidate-native.tar.gz.part000"],outputs["files"],selected,work/"reconstruction-inputs")
    f.write_new(evidence/"reconstruction-input-restoration.json",f.encode(dict(full_members=observed,selected=sorted(selected),
      full_archive_verified=True,producer_run=41190910993,producer_source=expected,
      native_bytes_remain_in_cloud=True,read_only_acquisition=True,production_candidate=False)))
    shutil.rmtree(transport)

def perform(ctx,proof,evidence):
    authorize_native(source_gate())
    controls=control_evidence(ctx)
    audit=f.decode(c.secure_file(ROOT,"bulk-postdrt-integration-controls/audit-controls.json").read_bytes())
    f.require(audit["status"]=="PASS_SAVED_DIODE_ROUTING_SOURCE_CONTROLS"and audit["count"]==140
      and len(set(audit["passed_cases"]))==140 and audit["source"]==ctx["source"]and audit["run_id"]==ctx["run_id"]
      and audit["attempt"]==1 and audit["native_executed"]is False,"same-source saved audit controls")
    f.write_new(evidence/"saved-audit-source-controls.json",f.encode(audit))
    f.write_new(evidence/"same-source-controls.json",f.encode(controls))
    f.require(subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==ctx["source"],"checkout")
    reserved=reservation(ctx,proof,f.api("releases/"+str(proof["release_id"])),
        f.api("git/ref/tags/"+proof["tag"]))
    f.write_new(evidence/"reservation.json",f.encode(dict(proof=proof,validated=reserved)))
    work=Path(os.environ["RUNNER_TEMP"])/(GROUP+"-"+ctx["token"])
    f.require(not work.exists()and not work.is_symlink(),"owned work collision")
    work.mkdir(mode=0o700);(work/"owner.json").write_bytes(f.encode(ctx))
    out=work/"out";out.mkdir()
    report=dict(status="IN_PROGRESS",source=ctx["source"],run_id=ctx["run_id"],
      physical_acceptance=False,timing_accepted=False,full_phy_accepted=False,
      commands=[],terminal_errors=[],creation_attempted=False)
    identity=None;primary=None;restored=False;projected=False
    def command(label,argv,timeout=120):return build.execute_command(report,out,label,argv,timeout)
    def inspect(value):return f.decode(subprocess.check_output(["docker","inspect",value],timeout=30))[0]
    try:
        f.require(shutil.disk_usage(work).free>=24*1024**3,"cloud disk budget")
        acquire_current(work,evidence)
        acquire_failed(work,evidence)
        acquire_reconstruction(work,evidence)
        # Historical prefix is used solely for the exact built ELF, runtime and
        # immutable source helpers. Native diagnosis receives the CURRENT ODB.
        tail.restore_prefix(work,out);restored=True
        projection=work/"tail-source";projection.mkdir()
        method=c.method(ROOT)
        for path in [*method["protected"],c.METHOD]:
            target=projection/path;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(c.secure_file(ROOT,path),target)
        manifest=source_gate()
        for path in manifest["files"]:
            target=projection/path;target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists():f.require(f.file_digest(target)["sha256"]==manifest["files"][path],"projection conflict")
            else:shutil.copyfile(c.secure_file(ROOT,path),target)
        shutil.copyfile(ROOT/MANIFEST,projection/MANIFEST)
        p.source_guard(projection)
        c.method(projection);projected=True
        shutil.copyfile(ROOT/"scripts/mainchip_saved_diode_routing_inner.py",work/"inner.py")
        f.require(f.file_digest(work/"inner.py")["sha256"]==manifest["files"]["scripts/mainchip_saved_diode_routing_inner.py"],"copied inner identity")
        command("immutable-image-pull",["docker","pull",c.IMAGE],1800)
        c.validate_image(f.decode(command("image-inspect",["docker","image","inspect",c.IMAGE]))[0])
        identity=build.create_owned(ctx,work,report,command,c.create_argv(ctx,work,os.getuid(),os.getgid()))
        c.validate_container(inspect(identity),ctx,work)
        command("bulk-postdrt-owned-container",["docker","start","--attach",identity],OUTER_SECONDS)
        result=f.decode((out/"bulk-postdrt-inner-result.json").read_bytes())
        report.update(plan.accept_native_result(result))
    except BaseException as exc:primary=exc;report["error"]=c.error_record("bulk-postdrt-antenna",exc)
    finally:
        c.attempt(report,"owned-container-cleanup",lambda:build.cleanup_owned(
            ctx,work,report,identity,report["creation_attempted"],inspect,command))
        c.attempt(report,"current-input-unchanged",lambda:f.require(f.file_digest(work/"current-input.odb")==CURRENT,"current input changed"))
        c.attempt(report,"source-unchanged",source_gate)
        if restored:c.attempt(report,"frozen-prefix-unchanged",lambda:c.frozen_unchanged(work,f.decode((work/"frozen-manifest.json").read_bytes())))
        if projected:c.attempt(report,"projected-original-source-unchanged",lambda:c.method(work/"tail-source"))
        if projected:
            c.attempt(report,"copied-inner-unchanged",lambda:f.require(f.file_digest(work/"inner.py")["sha256"]==manifest["files"]["scripts/mainchip_saved_diode_routing_inner.py"],"copied inner changed"))
            for path,pin in manifest["files"].items():
                c.attempt(report,"projected-source:"+path,lambda path=path,pin=pin:f.require(
                    f.file_digest(work/"tail-source"/path)["sha256"]==pin,"current source changed"))
        if identity is not None:
            state=report.get("container_terminal",{}).get("State",{})
            c.attempt(report,"container-terminal",lambda:f.require(not state.get("Running",True)
              and state.get("ExitCode")==0 and state.get("OOMKilled")is False and not state.get("Error"),"container failed"))
        c.attempt(report,"permanent-candidate-capsule",lambda:report.update(native_publication=publish_capsule(ctx,proof,work,out,evidence)))
        c.attempt(report,"preserve-derived-outputs",lambda:preserve_outputs(out,evidence,report))
        c.attempt(report,"retain-owned-output-for-artifact",lambda:retained_workspace(ctx,work,out,report))
        report["status"]="COMPLETE_SAVED_DIODE_ROUTING_CLOUD_EXPERIMENT"if primary is None and not report["terminal_errors"]and report.get("saved_diode_routing_complete")else"FAIL_SAVED_DIODE_ROUTING_CLOUD_EXPERIMENT"
        c.finish_record(evidence/"result.json",report,"FAIL_SAVED_DIODE_ROUTING_CLOUD_EXPERIMENT",primary)
    if primary is not None:raise primary
    f.require(not report["terminal_errors"],"readback terminal errors")
    return report

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--reservation",type=Path,required=True)
    args=parser.parse_args();ctx=context(os.environ)
    f.require(not args.output.exists()and not args.output.is_symlink(),"new evidence directory")
    args.output.mkdir(parents=True);primary=None
    try:return perform(ctx,f.decode(args.reservation.read_bytes()),args.output)
    except BaseException as exc:
        primary=exc
        failure=dict(status="FAIL_BULK_POSTDRT",terminal_errors=[],
          error=c.error_record("primary",exc),context=ctx,physical_acceptance=False,
          timing_accepted=False,full_phy_accepted=False)
        c.finish_record(args.output/"failure.json",failure,"FAIL_BULK_POSTDRT",primary)
        raise
    finally:
        try:emit(args.output)
        except BaseException:
            if primary is None:raise
if __name__=="__main__":main()
