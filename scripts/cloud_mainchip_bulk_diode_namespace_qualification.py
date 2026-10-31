#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted actual native name roundtrip; no real antenna repair or routing."""
import argparse,os,json,shutil,subprocess,sys
from pathlib import Path
import cloud_mainchip_bulk_postdrt_antenna as base
from cloud_mainchip_bulk_postdrt_antenna import (
 f,c,p,tail,build,ROOT,BRANCH,GROUP,CURRENT,OUTER_SECONDS,context,control_evidence,
 reservation,acquire_current,publish_capsule,preserve_outputs,retained_workspace,emit)
MANIFEST="scripts/mainchip-bulk-diode-namespace-qualification-pins.json"

def source_gate():
    inherited=base.source_gate()
    f.require(inherited["native_execution_enabled"]is False,"genuine bulk repair remains disabled")
    manifest=f.decode(c.secure_file(ROOT,MANIFEST).read_bytes())
    f.require(manifest["schema"]=="bulk-diode-namespace-qualification-pins-v1","qualification schema")
    f.require(manifest["native_repair_authorized"]is False and manifest["routing_authorized"]is False
      and type(manifest["native_namespace_qualification_enabled"])is bool,"qualification authority")
    required=set(inherited["files"])|{
      base.MANIFEST,"scripts/mainchip_bulk_diode_namespace_qualification.py",
      "scripts/mainchip_bulk_diode_namespace_qualification_inner.py",
      "scripts/cloud_mainchip_bulk_diode_namespace_qualification.py"}
    f.require(required<=set(manifest["files"]),"complete unchanged original and qualification sources")
    for path,digest in manifest["files"].items():
        f.require(f.file_digest(c.secure_file(ROOT,path))["sha256"]==digest,"qualification source pin: "+path)
    f.require(all(manifest[k]is False for k in p.FLAGS),"qualification cannot authorize final acceptance")
    return manifest

def authorize_native(manifest):
    f.require(manifest["native_namespace_qualification_enabled"]is True
      and manifest["native_repair_authorized"]is False and manifest["routing_authorized"]is False,
      "only disposable native namespace qualification")
    return dict(native_namespace_only=True,genuine_repair=False,routing=False,**p.FLAGS)

def cleanup_preserved_workspace(ctx,evidence):
    """Called only after successful workflow artifact upload, never by perform()."""
    work=Path(os.environ["RUNNER_TEMP"])/(GROUP+"-"+ctx["token"])
    if not work.exists()and not work.is_symlink():return dict(absent=True)
    f.require(not work.is_symlink()and work.is_dir(),"cleanup workspace type")
    f.require(not (work/"owner.json").is_symlink()and f.decode((work/"owner.json").read_bytes())==ctx,"cleanup owner")
    try:
        report=f.decode((Path(evidence)/"result.json").read_bytes())
        complete=report.get("status")=="COMPLETE_BULK_DIODE_NAMESPACE_CLOUD_EXPERIMENT" and report.get(
            "output_preservation",{}).get("complete")is True and report.get(
            "workspace_retained",{}).get("path")==str(work) and report.get("native_publication",{}).get("status")=="COMPLETE_PERMANENT_NATIVE_CAPSULE"
    except BaseException as exc:
        return dict(absent=False,retained=True,reason="Missing or unreadable terminal preservation record",error=repr(exc))
    if not complete:return dict(absent=False,retained=True,reason="Failed or incomplete preservation remains owned")
    shutil.rmtree(work);f.require(not work.exists(),"cleanup incomplete")
    return dict(absent=True,removed_owned_workspace=True)

def perform(ctx,proof,evidence):
    authorize_native(source_gate())
    controls=control_evidence(ctx)
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
        shutil.copyfile(ROOT/"scripts/mainchip_bulk_diode_namespace_qualification_inner.py",work/"inner.py")
        f.require(f.file_digest(work/"inner.py")["sha256"]==manifest["files"]["scripts/mainchip_bulk_diode_namespace_qualification_inner.py"],"copied inner identity")
        command("immutable-image-pull",["docker","pull",c.IMAGE],1800)
        c.validate_image(f.decode(command("image-inspect",["docker","image","inspect",c.IMAGE]))[0])
        identity=build.create_owned(ctx,work,report,command,c.create_argv(ctx,work,os.getuid(),os.getgid()))
        c.validate_container(inspect(identity),ctx,work)
        command("bulk-postdrt-owned-container",["docker","start","--attach",identity],OUTER_SECONDS)
        result=f.decode((out/"bulk-postdrt-inner-result.json").read_bytes())
        f.require(result["status"]=="COMPLETE_BULK_DIODE_NAMESPACE_ENGINE"and not result["terminal_errors"],"inner terminal")
        report["native_namespace_checks_complete"]=True
        f.require(result["native_rename_API_qualified"]is True
          and result["current_chip_name_roundtrip_qualified"]is True
          and result["actual_physical_repair_calls"]==result["actual_route_calls"]==0
          and result["bounded_cycle_qualified"]is False,"qualification-only actual native result")
        report["native_rename_API_qualified"]=True
        report["current_chip_name_roundtrip_qualified"]=True
        report["actual_physical_repair_calls"]=report["actual_route_calls"]=0
        report["bounded_cycle_qualified"]=False
    except BaseException as exc:primary=exc;report["error"]=c.error_record("bulk-postdrt-antenna",exc)
    finally:
        c.attempt(report,"owned-container-cleanup",lambda:build.cleanup_owned(
            ctx,work,report,identity,report["creation_attempted"],inspect,command))
        c.attempt(report,"current-input-unchanged",lambda:f.require(f.file_digest(work/"current-input.odb")==CURRENT,"current input changed"))
        c.attempt(report,"source-unchanged",source_gate)
        if restored:c.attempt(report,"frozen-prefix-unchanged",lambda:c.frozen_unchanged(work,f.decode((work/"frozen-manifest.json").read_bytes())))
        if projected:c.attempt(report,"projected-original-source-unchanged",lambda:c.method(work/"tail-source"))
        if projected:
            c.attempt(report,"copied-inner-unchanged",lambda:f.require(f.file_digest(work/"inner.py")["sha256"]==manifest["files"]["scripts/mainchip_bulk_diode_namespace_qualification_inner.py"],"copied inner changed"))
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
        report["status"]="COMPLETE_BULK_DIODE_NAMESPACE_CLOUD_EXPERIMENT"if primary is None and not report["terminal_errors"]and report.get("native_namespace_checks_complete")else"FAIL_BULK_DIODE_NAMESPACE_CLOUD_EXPERIMENT"
        c.finish_record(evidence/"result.json",report,"FAIL_BULK_DIODE_NAMESPACE_CLOUD_EXPERIMENT",primary)
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
