#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only exact two-diode candidate, physical checks and permanent preservation."""
import argparse,base64,hashlib,json,os,re,shutil,subprocess,sys,tarfile,tempfile,zlib
from pathlib import Path,PurePosixPath
import cloud_mainchip_final_marker_readback as f
import mainchip_fixed_engine_route_tail_contract as c
import cloud_mainchip_fixed_engine_route_tail as tail
import mainchip_witness_engine_build as build
ROOT=Path(__file__).resolve().parent.parent
BRANCH="codex/mainchip-net459-diode-prune"
GROUP="mainchip-net459-diode-prune"
MANIFEST="scripts/mainchip-net459-diode-prune-pins.json"
CURRENT_MEMBER="work/drc-observed.odb"
CURRENT=dict(bytes=213429713,sha256="47d657f41565f5c379a9152672eac824a5d296043c3726527031452ad2097677")

def context(env):
    f.require(env.get("GITHUB_ACTIONS")=="true"and env.get("RUNNER_OS")=="Linux","hosted Linux")
    f.require(env.get("GITHUB_REPOSITORY")==f.REPOSITORY and env.get("GITHUB_EVENT_NAME")=="workflow_dispatch","manual repository")
    f.require(env.get("GITHUB_REF")=="refs/heads/"+BRANCH and env.get("GITHUB_RUN_ATTEMPT")=="1","branch/attempt")
    run=env["GITHUB_RUN_ID"];source=env["GITHUB_SHA"]
    f.require(re.fullmatch(r"[1-9][0-9]*",run)and re.fullmatch(r"[0-9a-f]{40}",source),"run/source")
    return dict(source=source,run_id=int(run),attempt=1,token=run+"-1",name="nssoc-witness-build-"+run+"-1",group=GROUP)

def source_gate():
    manifest=f.decode((ROOT/MANIFEST).read_bytes())
    f.require(manifest["schema"]=="net459-diode-prune-pins-v1","manifest schema")
    for path,pin in manifest["files"].items():
        f.require(f.file_digest(c.secure_file(ROOT,path))==pin,"source pin: "+path)
    c.method(ROOT)
    return manifest

def reservation(ctx,proof,info,ref):
    tag="cloud-results-"+ctx["token"]+"-"+GROUP
    assets=f.release_binding(info,ref,tag,ctx["source"])
    f.require(proof.get("tag")==tag and proof.get("tested_source")==ctx["source"]
       and proof.get("release_id")==info["id"],"reservation identity")
    f.require(proof.get("target_verified")is True and proof.get("assets_overwritten")is False
       and proof.get("externally_reserved")is True and proof.get("creation_attempted")is False,
       "external exact source reservation")
    f.require(proof.get("existing_assets")==[]and not assets,"fresh release")
    return dict(tag=tag,source=ctx["source"],release_id=info["id"],verified_before_acquisition=True)

def select_database(archive,expected,out):
    """Verify every archive member; stream only the exact current input to disk."""
    f.validate_map(expected);f.require(expected.get(CURRENT_MEMBER)==CURRENT,"current member identity")
    f.require(not out.exists()and not out.is_symlink(),"input no overwrite")
    directories={str(p)for name in expected for p in PurePosixPath(name).parents if str(p)!="."}
    seen=set();observed={}
    with tarfile.open(archive,"r|gz")as tar:
        for member in tar:
            name=member.name;f.checked_path(name)
            f.require(name not in seen,"duplicate member");seen.add(name)
            if member.isdir():
                f.require(name in directories,"unexpected directory");continue
            f.require(member.isfile()and not member.issparse()and name in expected,"special/unexpected member")
            row=expected[name];f.require(member.size==row["bytes"],"declared size")
            stream=tar.extractfile(member);f.require(stream is not None,"missing stream")
            target=out.open("xb")if name==CURRENT_MEMBER else None
            h=hashlib.sha256();size=0
            try:
                with stream:
                    for raw in iter(lambda:stream.read(1024*1024),b""):
                        size+=len(raw);f.require(size<=row["bytes"],"member overrun");h.update(raw)
                        if target is not None:target.write(raw)
            finally:
                if target is not None:target.close()
            found=dict(bytes=size,sha256=h.hexdigest())
            f.require(found==row,"member digest: "+name);observed[name]=found
    f.require(observed==expected and f.file_digest(out)==CURRENT,"complete current archive")
    return dict(full_members=observed,current_input=CURRENT,full_archive_verified=True,
       native_bytes_remain_in_cloud=True)

def acquire_current(work,evidence):
    read=f.api
    inputs=dict(run=read("actions/runs/"+str(f.PRODUCER_RUN)),
      jobs=read("actions/runs/"+str(f.PRODUCER_RUN)+"/attempts/1/jobs?per_page=100"),
      release=read("releases/"+str(f.PRODUCER_RELEASE)),ref=read("git/ref/tags/"+f.PRODUCER_TAG))
    binding=f.validate_live(**inputs)
    for name,value in inputs.items():f.write_new(evidence/("producer-"+name+".json"),f.encode(value))
    transport=work/"current-transport";transport.mkdir()
    for name in ("outputs.json","parts.json"):f.download(f.ASSETS[name],transport/name)
    files,parts=f.metadata((transport/"outputs.json").read_bytes(),(transport/"parts.json").read_bytes())
    f.require(files[CURRENT_MEMBER]==CURRENT,"current input map")
    paths=[]
    for row in parts["parts"]:
        path=transport/row["name"];f.download(f.ASSETS[row["name"]],path);paths.append(path)
    archive=transport/"current.tar.gz";f.combine_parts(paths,parts,archive)
    proof=select_database(archive,files,work/"current-input.odb")
    f.write_new(evidence/"current-input-restoration.json",f.encode(dict(proof,producer=binding)))
    for name in ("outputs.json","parts.json"):
        f.write_new(evidence/("producer-"+name),(transport/name).read_bytes())
    shutil.rmtree(transport)

def derived_path(path):
    return path.suffix in (".json",".jsonl",".stdout",".stderr",".lef",".rpt") or bool(
        re.fullmatch(r".+\.json\.[A-Za-z0-9_-]+\.tmp",path.name))

def preserve_outputs(out,evidence,report):
    """Copy each derived output independently; retain the complete owned tree."""
    result=dict(copied={},excluded_roots=[],complete=False,owned_outputs_retained=True,
                retained_output_path=str(out),artifact_required=True)
    report["output_preservation"]=result;before=len(report["terminal_errors"])
    def visit(directory):
        entries=c.attempt(report,"enumerate:"+str(directory.relative_to(out)),
                          lambda:sorted(directory.iterdir()))
        if entries is None:return
        for path in entries:
            relative=path.relative_to(out)
            def one():
                f.require(not path.is_symlink(),"evidence symlink")
                if path.is_dir():
                    if len(relative.parts)==1 and relative.parts[0]in ("work","witness","supervision"):
                        result["excluded_roots"].append(relative.as_posix());return
                    visit(path);return
                f.require(path.is_file()and derived_path(path),"unexpected output")
                pin=f.file_digest(path)
                if pin["bytes"]>2*1024**2:
                    published=report.get("native_publication",{}).get("files",{})
                    f.require(published.get(relative.as_posix())==pin,"large output not permanently preserved")
                    result.setdefault("complete_large_outputs_in_native_capsule",{})[relative.as_posix()]=pin
                    return
                dest=evidence/"native"/relative
                dest.parent.mkdir(parents=True,exist_ok=True)
                f.write_new(dest,path.read_bytes())
                f.require(f.file_digest(dest)==pin,"preserved output bytes")
                result["copied"][relative.as_posix()]=pin
            c.attempt(report,"preserve:"+relative.as_posix(),one)
    visit(out)
    result["complete"]=len(report["terminal_errors"])==before
    return result

def retained_workspace(ctx,work,out,report):
    f.require(not work.is_symlink()and not out.is_symlink()and out.is_dir(),"owned retained output")
    f.require(f.decode((work/"owner.json").read_bytes())==ctx,"retained output owner")
    report["workspace_retained"]=dict(path=str(work),output_path=str(out),
        reason="Retained until complete workflow artifact upload succeeds",cleanup_after_artifact=True)

def cleanup_preserved_workspace(ctx,evidence):
    """Called only after successful workflow artifact upload, never by perform()."""
    work=Path(os.environ["RUNNER_TEMP"])/(GROUP+"-"+ctx["token"])
    if not work.exists()and not work.is_symlink():return dict(absent=True)
    f.require(not work.is_symlink()and work.is_dir(),"cleanup workspace type")
    f.require(not (work/"owner.json").is_symlink()and f.decode((work/"owner.json").read_bytes())==ctx,"cleanup owner")
    try:
        report=f.decode((Path(evidence)/"result.json").read_bytes())
        complete=report.get("status")=="COMPLETE_NET459_DIODE_PRUNE_CLOUD_EXPERIMENT" and report.get(
            "output_preservation",{}).get("complete")is True and report.get(
            "workspace_retained",{}).get("path")==str(work) and report.get("native_publication",{}).get("status")=="COMPLETE_PERMANENT_NATIVE_CAPSULE"
    except BaseException as exc:
        return dict(absent=False,retained=True,reason="Missing or unreadable terminal preservation record",error=repr(exc))
    if not complete:return dict(absent=False,retained=True,reason="Failed or incomplete preservation remains owned")
    shutil.rmtree(work);f.require(not work.exists(),"cleanup incomplete")
    return dict(absent=True,removed_owned_workspace=True)

def emit(evidence):
    rows={}
    for path in sorted(evidence.rglob("*")):
        f.require(not path.is_symlink()and(path.is_dir()or path.is_file()),"evidence path")
        if path.is_file():
            f.require(derived_path(path),"derived evidence only")
            rows[path.relative_to(evidence).as_posix()]=f.file_digest(path)
    print("NET459_DIODE_PRUNE_INDEX "+json.dumps(rows,sort_keys=True),flush=True)
    for name,pin in rows.items():
        raw=(evidence/name).read_bytes();packed=zlib.compress(raw,9)
        pieces=[packed[i:i+12000]for i in range(0,len(packed),12000)]or[b""]
        for index,piece in enumerate(pieces):
            print("NET459_DIODE_PRUNE_CHUNK "+json.dumps(dict(name=name,index=index,
              chunks=len(pieces),**pin,encoding="zlib-base64",base64=base64.b64encode(piece).decode()),
              sort_keys=True),flush=True)


def publish_capsule(ctx,proof,work,out,evidence):
    """Permanent cloud-only native candidate/partial-failure preservation."""
    f.require(f.decode((work/"owner.json").read_bytes())==ctx,"capsule owner")
    files={}
    for path in sorted(out.rglob("*")):
        f.require(not path.is_symlink(),"capsule symlink")
        if not path.is_file():continue
        relative=path.relative_to(out).as_posix()
        if relative.startswith(("work/net459-diode-prune/","net459-diode-prune/","prune-")):
            files[relative]=f.file_digest(path)
    index=work/"candidate-outputs.json"
    f.write_new(index,f.encode(dict(source=ctx["source"],run=ctx["run_id"],attempt=1,
      input=CURRENT,files=files,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)))
    archive=work/"candidate-native.tar.gz"
    with tarfile.open(archive,"w:gz")as tar:
        for name,pin in files.items():
            path=out/name;f.require(f.file_digest(path)==pin,"capsule input drift")
            tar.add(path,arcname=name,recursive=False)
    parts=[]
    with archive.open("rb")as source:
        counter=0
        while True:
            path=work/("candidate-native.tar.gz.part%03d"%counter)
            first=source.read(4*1024**2)
            if not first:break
            with path.open("xb")as dest:
                dest.write(first);size=len(first)
                while size<512*1024**2:
                    raw=source.read(min(4*1024**2,512*1024**2-size))
                    if not raw:break
                    dest.write(raw);size+=len(raw)
            parts.append(dict(name=path.name,**f.file_digest(path)));counter+=1
    parts_path=work/"candidate-parts.json"
    f.write_new(parts_path,f.encode(dict(archive=f.file_digest(archive),parts=parts)))
    tag=proof["tag"]
    def current():
        info=f.api("releases/tags/"+tag);ref=f.api("git/ref/tags/"+tag)
        f.release_binding(info,ref,tag,ctx["source"])
        f.require(info["id"]==proof["release_id"],"capsule release")
        return info
    uploads=[index,parts_path,*[work/r["name"]for r in parts]]
    planned={x.name for x in uploads};f.require(len(planned)==len(uploads),"capsule asset names")
    f.require({a["name"]for a in current()["assets"]}<=planned,"unexpected asset")
    published=[]
    for path in uploads:
        expected=f.file_digest(path);info=current();same=[a for a in info["assets"]if a["name"]==path.name]
        upload_error=None
        if not same:
            try:
                process=subprocess.run(["gh","release","upload",tag,str(path),"--repo",f.REPOSITORY],timeout=1800,capture_output=True)
                f.write_new(evidence/("publication-"+path.name+".stdout"),process.stdout)
                f.write_new(evidence/("publication-"+path.name+".stderr"),process.stderr)
                if process.returncode:upload_error="returncode "+str(process.returncode)
            except BaseException as exc:
                upload_error=repr(exc)
                for suffix in("stdout","stderr"):
                    target=evidence/("publication-"+path.name+"."+suffix)
                    if not target.exists():f.write_new(target,getattr(exc,suffix,None)or b"")
        # Reconcile once; no blind overwrite or repeated mutation after uncertainty.
        info=current();same=[a for a in info["assets"]if a["name"]==path.name]
        f.require(len(same)==1 and same[0]["size"]==expected["bytes"]
          and same[0].get("digest")=="sha256:"+expected["sha256"],"capsule publication mismatch: "+path.name+" "+str(upload_error))
        published.append(dict(name=path.name,id=same[0]["id"],**expected,reconciled_upload_error=upload_error))
    f.require({a["name"]for a in current()["assets"]}==planned,"capsule exact asset census")
    for name,pin in files.items():f.require(f.file_digest(out/name)==pin,"archived output changed")
    result=dict(status="COMPLETE_PERMANENT_NATIVE_CAPSULE",source=ctx["source"],tag=tag,
      release_id=proof["release_id"],files=files,assets=published,
      archive=f.file_digest(archive),partial_failure_preserved=True,native_bytes_remain_in_cloud=True)
    f.write_new(evidence/"native-capsule-publication.json",f.encode(result))
    return result

def perform(ctx,proof,evidence):
    source_gate()
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
            if target.exists():f.require(f.file_digest(target)==manifest["files"][path],"projection conflict")
            else:shutil.copyfile(c.secure_file(ROOT,path),target)
        shutil.copyfile(ROOT/MANIFEST,projection/MANIFEST)
        c.method(projection);projected=True
        shutil.copyfile(ROOT/"scripts/mainchip_net459_diode_prune_inner.py",work/"inner.py")
        command("immutable-image-pull",["docker","pull",c.IMAGE],1800)
        c.validate_image(f.decode(command("image-inspect",["docker","image","inspect",c.IMAGE]))[0])
        identity=build.create_owned(ctx,work,report,command,c.create_argv(ctx,work,os.getuid(),os.getgid()))
        c.validate_container(inspect(identity),ctx,work)
        command("southern-owned-container",["docker","start","--attach",identity],14400)
        result=f.decode((out/"prune-inner-result.json").read_bytes())
        f.require(result["status"]=="COMPLETE_NET459_DIODE_PRUNE_ENGINE"and not result["terminal_errors"],"inner terminal")
        report["native_readback_complete"]=True
        report["candidate_checks_passed"]=result["candidate_checks_passed"]
    except BaseException as exc:primary=exc;report["error"]=c.error_record("southern-neighborhood",exc)
    finally:
        c.attempt(report,"owned-container-cleanup",lambda:build.cleanup_owned(
            ctx,work,report,identity,report["creation_attempted"],inspect,command))
        c.attempt(report,"current-input-unchanged",lambda:f.require(f.file_digest(work/"current-input.odb")==CURRENT,"current input changed"))
        c.attempt(report,"source-unchanged",source_gate)
        if restored:c.attempt(report,"frozen-prefix-unchanged",lambda:c.frozen_unchanged(work,f.decode((work/"frozen-manifest.json").read_bytes())))
        if projected:c.attempt(report,"projected-original-source-unchanged",lambda:c.method(work/"tail-source"))
        if projected:
            for path,pin in manifest["files"].items():
                c.attempt(report,"projected-source:"+path,lambda path=path,pin=pin:f.require(
                    f.file_digest(work/"tail-source"/path)==pin,"current source changed"))
        if identity is not None:
            state=report.get("container_terminal",{}).get("State",{})
            c.attempt(report,"container-terminal",lambda:f.require(not state.get("Running",True)
              and state.get("ExitCode")==0 and state.get("OOMKilled")is False and not state.get("Error"),"container failed"))
        c.attempt(report,"permanent-candidate-capsule",lambda:report.update(native_publication=publish_capsule(ctx,proof,work,out,evidence)))
        c.attempt(report,"preserve-derived-outputs",lambda:preserve_outputs(out,evidence,report))
        c.attempt(report,"retain-owned-output-for-artifact",lambda:retained_workspace(ctx,work,out,report))
        report["status"]="COMPLETE_NET459_DIODE_PRUNE_CLOUD_EXPERIMENT"if primary is None and not report["terminal_errors"]and report.get("native_readback_complete")else"FAIL_NET459_DIODE_PRUNE_CLOUD_EXPERIMENT"
        c.finish_record(evidence/"result.json",report,"FAIL_NET459_DIODE_PRUNE_CLOUD_EXPERIMENT",primary)
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
        failure=dict(status="FAIL_NET459_DIODE_PRUNE",terminal_errors=[],
          error=c.error_record("primary",exc),context=ctx,physical_acceptance=False,
          timing_accepted=False,full_phy_accepted=False)
        c.finish_record(args.output/"failure.json",failure,"FAIL_NET459_DIODE_PRUNE",primary)
        raise
    finally:
        try:emit(args.output)
        except BaseException:
            if primary is None:raise
if __name__=="__main__":main()
