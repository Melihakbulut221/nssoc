#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Authenticate frozen cloud inputs, observe once, preserve every generated failure."""
import ast,base64,hashlib,json,os,re,shutil,subprocess,time,types
from pathlib import Path
import mainchip_drt_obstacle_contract as k
import mainchip_fixed_engine_route_tail_contract as c
import cloud_mainchip_fixed_engine_route_tail as tail
import cloud_mainchip_full_antenna_readback as restore
import mainchip_witness_engine_build as build
q=k.q
ROOT=Path(__file__).resolve().parents[1]
GROUP="mainchip-drt-obstacle-readback"
MANIFEST="scripts/mainchip-drt-obstacle-readback-source.json"
CONFIG="scripts/mainchip-drt-obstacle-readback-inputs.json"
INNER="scripts/mainchip_drt_obstacle_inner.py"
OUT=ROOT/"obstacle-readback"
EXPECTED_TESTS=40
def context(env,checkout):
    ctx=k.context(env,checkout)
    q.require(env.get("RUNNER_ENVIRONMENT")=="github-hosted"and env.get("RUNNER_OS")=="Linux","hosted Linux")
    q.require(env.get("GITHUB_JOB")=="observation"and env.get("MODE")=="observation"
      and env.get("APPROVED_SOURCE")==ctx["source"],"dedicated exact-source read-only job")
    return dict(ctx,run_id=ctx["run"],token=str(ctx["run"])+"-1",name="nssoc-witness-build-"+str(ctx["run"])+"-1")
def current_run(ctx,run,jobs):
    q.require((run["id"],run["head_sha"],run["head_branch"],run["event"],run["run_attempt"],run["path"],run["workflow_id"],run["status"])==
      (ctx["run"],ctx["source"],"codex/mainchip-drt-obstacle-readback","workflow_dispatch",1,".github/workflows/cloud-evidence-summary.yml",382556685,"in_progress"),"actual current observer run")
    q.require(jobs["total_count"]==len(jobs["jobs"])==3 and {j["name"]for j in jobs["jobs"]}=={"source-controls","preserve-job-log","observation"},"complete actual job set")
    for j in jobs["jobs"]:
        q.require(j["head_sha"]==ctx["source"]and j["run_id"]==ctx["run"]and j["run_attempt"]==1,"actual job identity")
        if j["name"]=="observation":q.require(j["status"]=="in_progress"and j["conclusion"]is None,"live sole observer")
        else:
            q.require(j["status"]=="completed"and j["conclusion"]=="success"and all(s["status"]=="completed"and s["conclusion"]in("success","skipped")for s in j["steps"]),"source/complete-log prerequisites")
    return next(j["id"]for j in jobs["jobs"]if j["name"]=="source-controls")
def expected_test_ids():
    result=[]
    for module in("check_mainchip_terminal_readback","check_mainchip_drt_report_analysis","check_mainchip_drt_obstacle","check_mainchip_drt_obstacle_host"):
        tree=ast.parse((ROOT/"scripts"/(module+".py")).read_text())
        classes=[n for n in tree.body if isinstance(n,ast.ClassDef)and n.name=="Controls"];q.require(len(classes)==1,"one protected Controls class")
        result += [module+".Controls."+n.name for n in classes[0].body if isinstance(n,ast.FunctionDef)and n.name.startswith("test_")]
    q.require(len(result)==len(set(result))==EXPECTED_TESTS,"complete protected test source inventory")
    return sorted(result)
def control_log(raw,ctx):
    text=raw.decode("utf-8");rows=[]
    for line in text.splitlines():
        m=re.fullmatch(r"(?:\d{4}-\d\d-\d\dT[0-9:.]+Z )?MAINCHIP_OBSTACLE_CONTROLS (\{.*\})",line)
        if m:rows.append(q.decode(m[1]))
    q.require(len(rows)==1,"one complete actual controls result")
    r=rows[0]
    q.require(r["status"]=="PASS_OBSTACLE_ADAPTER_SOURCE_CONTROLS"and r["source"]==ctx["source"]and r["run"]==ctx["run"]and r["attempt"]==1,"same source/run controls")
    q.require(r["tests_run"]==EXPECTED_TESTS and r["failures"]==r["errors"]==r["skipped"]==0 and r["successful"]is True,"all required controls passed")
    q.require(type(r["test_ids"])is list and sorted(r["test_ids"])==expected_test_ids(),"complete exact protected test inventory")
    q.require(r["native_acquired"]is False and r["native_tools_executed"]is False and all(r[n]is False for n in k.FLAGS),"source controls never native acceptance")
    return dict(result=r,log_pin=dict(bytes=len(raw),sha256=q.sha(raw)))
def collect_controls(ctx,out):
    run=q.api("actions/runs/"+str(ctx["run"]));jobs=q.api("actions/runs/"+str(ctx["run"])+"/attempts/1/jobs?per_page=100")
    job=current_run(ctx,run,jobs)
    raw=subprocess.check_output(["gh","api","--allow-escape-sequences","repos/"+q.REPO+"/actions/jobs/"+str(job)+"/logs"])
    bound=control_log(raw,ctx)
    for name,value in(("current-run.json",run),("current-jobs.json",jobs),("same-source-controls.json",bound)):(out/name).write_bytes(q.encode(value))
    (out/"same-source-controls.log").write_bytes(raw)
    return bound
def destination(ctx,empty,expected=None):
    fn=types.FunctionType(q.destination.__code__,dict(q.destination.__globals__,GROUP=GROUP),q.destination.__name__,q.destination.__defaults__,q.destination.__closure__)
    return fn(ctx["source"],empty,expected)
def reserved(ctx,out):
    deadline=time.monotonic()+180
    while True:
        try:tag,info=destination(ctx,True);break
        except subprocess.CalledProcessError as exc:
            if b"HTTP 404"not in(exc.stderr or b"")or time.monotonic()>=deadline:raise
            time.sleep(2)
    proof=dict(tag=tag,release_id=info["id"],tested_source=ctx["source"],externally_reserved=True,
      creation_attempted=False,assets_overwritten=False,existing_assets=[],target_verified=True)
    (out/"reservation.json").write_bytes(q.encode(dict(proof=proof,release=info)))
    return proof
def analysis_producer(p):
    run=q.api("actions/runs/"+str(p["run"]));release=q.api("releases/"+str(p["release"]));ref=q.api("git/ref/tags/"+p["tag"])
    q.require(run["head_sha"]==p["source"]and run["run_attempt"]==1 and run["status"]=="completed"and run["conclusion"]=="success","qualified analysis run")
    q.require(q.immutable_release(release)==p["immutable_release"]and ref["object"]["type"]=="commit"and ref["object"]["sha"]==p["source"],"complete exact analysis publication")
    return dict(run=run,release=release,ref=ref)
def acquire(config,work,out):
    p=config["producer"];before=q.producer(p);abefore=analysis_producer(config["analysis_result"])
    for n,v in(("producer-before.json",before),("analysis-producer-before.json",abefore)):(out/n).write_bytes(q.encode(v))
    transport=work/"current-transport";transport.mkdir()
    for name in p["assets"]:q.download(p,name,transport/name)
    index=q.decode((transport/"candidate-outputs.json").read_bytes());parts=q.decode((transport/"candidate-parts.json").read_bytes())
    q.require(index["run"]==p["producer_run"]and index["source"]==p["producer_source"]and index["attempt"]==1 and index["files"]==p["members"],"exact full native index")
    q.require(all(index[n]is False for n in("physical_acceptance","timing_accepted","full_phy_accepted"))and parts==p["parts"],"original rejection and complete parts")
    archive=transport/"native.tar.gz"
    with archive.open("xb")as target:
        for part in parts["parts"]:
            q.valid_name(part["name"])
            with(transport/part["name"]).open("rb")as source:shutil.copyfileobj(source,target,1024**2)
    q.require(q.pin(archive)==parts["archive"],"full archive bytes")
    selected=work/"obstacle-inputs"
    observed=restore.restore(archive,index["files"],set(config["selected_members"]),selected)
    q.require(observed==p["members"]and len(observed)==735,"all native archive members authenticated")
    a=config["analysis_result"];raw=q.api("releases/assets/"+str(a["asset_id"]),True);q.checked(raw,a["pin"])
    (selected/"hosted-analysis.json").write_bytes(raw)
    after=q.producer(p);aafter=analysis_producer(a)
    q.require(q.immutable_release(before["release"])==q.immutable_release(after["release"])and before["ref"]==after["ref"],"unchanged original native publication")
    q.require(q.immutable_release(abefore["release"])==q.immutable_release(aafter["release"])and abefore["ref"]==aafter["ref"],"unchanged analysis publication")
    for n,v in(("producer-after.json",after),("analysis-producer-after.json",aafter),("selected-input-admission.json",dict(all_members=observed,selected=config["selected_members"],analysis=a["pin"],all735_authenticated=True,native_bytes_cloud_only=True))):(out/n).write_bytes(q.encode(v))
    for n in("candidate-outputs.json","candidate-parts.json"):(out/n).write_bytes((transport/n).read_bytes())
    return selected
def hosted_argv(ctx,work,uid,gid,env):
    argv=c.create_argv(ctx,work,uid,gid)
    names=("GITHUB_ACTIONS","GITHUB_REPOSITORY","GITHUB_EVENT_NAME","GITHUB_REF","GITHUB_SHA","GITHUB_RUN_ID","GITHUB_RUN_ATTEMPT","GITHUB_JOB","RUNNER_OS","RUNNER_ENVIRONMENT","MODE","APPROVED_SOURCE")
    q.require(context(env,ctx["source"])==ctx,"actual forwarded context")
    q.require(not any("GITHUB_"in s for s in argv),"original argv has no fabricated hosted context")
    extra=[]
    for name in names:extra+=["--env",name+"="+env[name]]
    return argv[:2]+extra+argv[2:]
def derived_text(path):
    """Only recognized text kinds with strict UTF-8; composite native names stay cloud-only."""
    suffixes=[x.lower()for x in path.suffixes]
    native={".odb",".gds",".gds2",".oas",".def",".lef",".spef",".spice",".sp",".l2n",".bin",".tar",".gz",".zip",".7z"}
    if native.intersection(suffixes):return False
    allowed=bool(suffixes)and(suffixes[-1]in(".json",".jsonl",".stdout",".stderr",".log")
      or len(suffixes)>=2 and suffixes[-2:]in([".json",".partial"],[".jsonl",".partial"]))
    if not allowed:return False
    try:
        with path.open("r",encoding="utf-8",errors="strict")as stream:
            while stream.read(1024*1024):pass
    except UnicodeError:return False
    return True
def preserve_outputs(work,out,evidence,report):
    """Preserve every generated byte independently; original out/work is frozen input."""
    inventory={};frozen=None;before=len(report["terminal_errors"])
    for path in sorted(out.rglob("*")):
        name=path.relative_to(out).as_posix()
        if name=="work"or name.startswith("work/"):continue
        def one(path=path,name=name):
            q.require(not path.is_symlink(),"native output symlink")
            if not path.is_file():q.require(path.is_dir(),"regular native output");return
            pin=q.pin(path);target=evidence/"native"/name;target.parent.mkdir(parents=True,exist_ok=True)
            q.require(not target.exists(),"exclusive generated evidence");shutil.copyfile(path,target);q.require(q.pin(target)==pin,"complete generated bytes")
            inventory[name]=dict(pin,derived_text=derived_text(path))
        c.attempt(report,"preserve-generated:"+name,one)
    def frozen_input():
        nonlocal frozen
        if(work/"frozen-manifest.json").is_file():
            frozen=q.pin(work/"frozen-manifest.json");shutil.copyfile(work/"frozen-manifest.json",evidence/"frozen-manifest.json")
    c.attempt(report,"preserve-frozen-manifest",frozen_input)
    report["generated_output_inventory"]=inventory
    report["generated_output_preservation_complete"]=len(report["terminal_errors"])==before
    report["excluded_unchanged_input"]=dict(path="out/work",frozen_manifest=frozen,reason="Authenticated frozen native input; no generated stage writes this root")
    return inventory

def publication(ctx,proof,out):
    """Publish all generated bytes; catalog distinguishes derived text from unexpected native bytes."""
    pub=out.parent/"obstacle-publication";pub.mkdir(exist_ok=False);expected={};catalog={}
    for path in sorted(out.rglob("*")):
        q.require(not path.is_symlink(),"publication symlink")
        if not path.is_file():q.require(path.is_dir(),"publication type");continue
        derived=derived_text(path)
        name=path.relative_to(out).as_posix();pin=q.pin(path);asset=q.sha(name.encode())[:16]+"-"+path.name
        q.require(asset not in expected,"unique complete output asset")
        if pin["bytes"]==0:catalog[name]=dict(name=None,embedded_empty=True,derived_text=derived,**pin);continue
        target=pub/asset;shutil.copyfile(path,target);q.require(q.pin(target)==pin,"publication copy")
        expected[asset]=pin;catalog[name]=dict(name=asset,derived_text=derived,**pin)
    (pub/"readback-catalog.json").write_bytes(q.encode(dict(source=ctx["source"],run=ctx["run"],files=catalog,**k.FLAGS)))
    expected["readback-catalog.json"]=q.pin(pub/"readback-catalog.json")
    tag,res=destination(ctx,True);q.require(res["id"]==proof["release_id"]and tag==proof["tag"],"reserved destination unchanged")
    for name in expected:subprocess.run(["gh","release","upload",tag,str(pub/name),"--repo",q.REPO],check=True,timeout=1800)
    _,after=destination(ctx,False,expected)
    receipt=dict(source=ctx["source"],run=ctx["run"],tag=tag,release_id=after["id"],files=dict(expected),receipt_self_not_in_files=True,**k.FLAGS)
    rp=out/"publication-receipt.json";rp.write_bytes(q.encode(receipt))
    subprocess.run(["gh","release","upload",tag,str(rp),"--repo",q.REPO],check=True,timeout=1800)
    expected[rp.name]=q.pin(rp);destination(ctx,False,expected)
    return receipt
def perform(ctx,work,out,config,manifest):
    out.mkdir();report=dict(status="IN_PROGRESS",source=ctx["source"],run=ctx["run"],commands=[],terminal_errors=[],creation_attempted=False,**k.FLAGS)
    primary=None;identity=None;proof=None;restored=False;projected=False;selected=None
    def command(label,argv,timeout=120):return build.execute_command(report,out,label,argv,timeout)
    def inspect(value):return q.decode(subprocess.check_output(["docker","inspect",value],timeout=30))[0]
    try:
        collect_controls(ctx,out);proof=reserved(ctx,out)
        q.require(shutil.disk_usage(work.parent).free>=24*1024**3,"cloud frozen-input disk budget")
        work.mkdir(mode=0o700);(work/"owner.json").write_bytes(q.encode(ctx));nativeout=work/"out";nativeout.mkdir()
        selected=acquire(config,work,out)
        tail.restore_prefix(work,nativeout);restored=True
        projection=work/"tail-source";projection.mkdir()
        names=set(manifest["inherited_files"])|set(manifest["files"])|{MANIFEST}
        for name in sorted(names):
            target=projection/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
        k.source_gate(projection);c.method(projection);projected=True
        shutil.copyfile(ROOT/INNER,work/"inner.py");q.require(q.pin(work/"inner.py")==manifest["files"][INNER],"exact inner bytes")
        (work/"obstacle-request.json").write_bytes(q.encode(dict(source=ctx["source"],context=k.context(os.environ,ctx["source"]),read_only=True)))
        command("immutable-image-pull",["docker","pull",c.IMAGE],1800)
        c.validate_image(q.decode(command("image-inspect",["docker","image","inspect",c.IMAGE]))[0])
        argv=hosted_argv(ctx,work,os.getuid(),os.getgid(),os.environ)
        identity=build.create_owned(ctx,work,report,command,argv);initial=inspect(identity);c.validate_container(initial,ctx,work)
        (out/"container-initial.json").write_bytes(q.encode(initial))
        command("obstacle-owned-container",["docker","start","--attach",identity],1500)
        result=q.decode((nativeout/"obstacle-inner-result.json").read_bytes())
        q.require(result["status"]=="COMPLETE_READONLY_OBSTACLE_ENGINE"and result["terminal_errors"]==[],"native inner terminal")
        report["native_complete"]=True
    except BaseException as exc:primary=exc;report["error"]=c.error_record("obstacle-readback",exc)
    finally:
        c.attempt(report,"owned-container-cleanup",lambda:build.cleanup_owned(ctx,work,report,identity,report["creation_attempted"],inspect,command))
        c.attempt(report,"source-unchanged",k.source_gate)
        if selected is not None:
            for name,pin in config["selected_members"].items():c.attempt(report,"input-unchanged:"+name,lambda name=name,pin=pin:q.require(q.pin(selected/name)==pin,"selected input changed"))
            c.attempt(report,"analysis-unchanged",lambda:q.require(q.pin(selected/"hosted-analysis.json")==config["analysis_result"]["pin"],"analysis input changed"))
        if restored:c.attempt(report,"frozen-input-unchanged",lambda:c.frozen_unchanged(work,q.decode((work/"frozen-manifest.json").read_bytes())))
        if projected:
            c.attempt(report,"projected-source-unchanged",lambda:k.source_gate(work/"tail-source"))
            c.attempt(report,"copied-inner-unchanged",lambda:q.require(q.pin(work/"inner.py")==manifest["files"][INNER],"copied inner changed"))
        if identity is not None:
            state=report.get("container_terminal",{}).get("State",{})
            c.attempt(report,"successful-container-terminal",lambda:q.require(not state.get("Running",True)and state.get("ExitCode")==0 and state.get("OOMKilled")is False and not state.get("Error"),"container terminal failure"))
        if(work/"out").is_dir():c.attempt(report,"complete-generated-output-retention",lambda:preserve_outputs(work,work/"out",out,report))
        report["status"]="COMPLETE_READONLY_OBSTACLE_CLOUD_OBSERVATION"if primary is None and not report["terminal_errors"]and report.get("native_complete")else"FAIL_READONLY_OBSTACLE_CLOUD_OBSERVATION"
        c.finish_record(out/"result.json",report,"FAIL_READONLY_OBSTACLE_CLOUD_OBSERVATION",primary)
        if proof is not None:
            try:publication(ctx,proof,out)
            except BaseException as exc:
                (out/"publication-failure.json").write_bytes(q.encode(dict(error=repr(exc),**k.FLAGS)))
                if primary is None:primary=exc
    if primary is not None:raise primary
    q.require(not report["terminal_errors"],"read-only terminal failures")
    return report
def main():
    manifest=k.native_authorization()
    head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip();ctx=context(os.environ,head)
    config=k.validate_config(q.decode((ROOT/CONFIG).read_bytes()))
    q.require(config["native_readonly_authorized"]is True and manifest["native_readonly_authorized"]is True,"both explicit native authorities")
    work=Path(os.environ["RUNNER_TEMP"])/(GROUP+"-"+ctx["token"])
    q.require(not work.exists()and not work.is_symlink()and not OUT.exists()and not OUT.is_symlink(),"fresh owned workspace and outputs")
    return perform(ctx,work,OUT,config,manifest)
if __name__=="__main__":main()
