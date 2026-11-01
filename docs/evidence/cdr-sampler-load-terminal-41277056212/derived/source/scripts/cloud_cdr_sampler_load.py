#!/usr/bin/env python3
"""Cloud-only exploratory sampler-load simulation, with durable native evidence."""
import argparse,hashlib,json,os,shutil,signal,subprocess,tarfile,time,traceback
from pathlib import Path,PurePosixPath
import cdr_sampler_load_candidate as candidate
import cdr_via2_m3_loaded_core as core
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"cloud-sampler-load";NATIVE=OUT/"native";DERIVED=OUT/"derived"
REPO="Melihakbulut221/nssoc"
def require(ok,message):
    if not ok:raise ValueError(message)
def save(path,value):
    core.write_exclusive(path,value)
def api(path):
    p=subprocess.run(["gh","api","repos/"+REPO+"/"+path],text=True,capture_output=True,timeout=180)
    require(p.returncode==0,p.stderr[:2000]);return json.loads(p.stdout)
def source_gate():
    require(os.environ.get("GITHUB_ACTIONS")=="true" and os.environ["GITHUB_RUN_ATTEMPT"]=="1","actual hosted first attempt")
    head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    require(head==os.environ["GITHUB_SHA"],"exact checked-out source")
    pins=json.loads((ROOT/"scripts/cdr-sampler-load-host-pins.json").read_bytes())
    for name,pin in pins["files"].items():require(core.file_pin(ROOT/name)==pin,"unchanged source "+name)
    return dict(source=head,run_id=int(os.environ["GITHUB_RUN_ID"]),attempt=1)
def release_gate(ctx,wait=False,empty=True):
    tag="cloud-results-"+str(ctx["run_id"])+"-1-cdr-sampler-load"
    until=time.monotonic()+(180 if wait else 0)
    while True:
        p=subprocess.run(["gh","api","repos/"+REPO+"/releases/tags/"+tag],text=True,capture_output=True,timeout=180)
        if p.returncode==0:break
        require(wait and "HTTP 404" in p.stderr and time.monotonic()<until,"independent exact-source release reservation missing")
        time.sleep(3)
    r=json.loads(p.stdout);ref=api("git/ref/tags/"+tag)
    require(r["tag_name"]==tag and r["target_commitish"]==ctx["source"] and not r["draft"] and r["prerelease"],"exact candidate release")
    require(ref["object"]["type"]=="commit" and ref["object"]["sha"]==ctx["source"],"exact candidate tag")
    if empty:require(not r["assets"],"reserved output release must be empty")
    return r
def admit(ctx):
    run=api("actions/runs/"+str(ctx["run_id"]))
    jobs=api("actions/runs/"+str(ctx["run_id"])+"/jobs?per_page=100")
    require(run["head_sha"]==ctx["source"] and run["run_attempt"]==1 and run["event"]=="workflow_dispatch","own exact-source dispatch")
    controls=[j for j in jobs["jobs"] if j["name"]=="source-controls"]
    require(len(controls)==1 and controls[0]["head_sha"]==ctx["source"] and controls[0]["status"]=="completed" and controls[0]["conclusion"]=="success","own completed source controls")
    require(all(s["conclusion"] in ("success","skipped") for s in controls[0]["steps"]),"all source control steps")
    save(DERIVED/"admission.json",dict(context=ctx,run=run,jobs=jobs,reservation=release_gate(ctx,True),physical_acceptance=False))
def download_asset(asset,path):
    meta=api("releases/assets/"+str(asset["id"]))
    require(meta["name"]==asset["name"] and meta["size"]==asset["bytes"] and meta["digest"]=="sha256:"+asset["sha256"],"native asset identity")
    with path.open("xb") as stream:
        p=subprocess.run(["gh","api","repos/"+REPO+"/releases/assets/"+str(asset["id"]),"-H","Accept: application/octet-stream"],stdout=stream,stderr=subprocess.PIPE,timeout=900)
    require(p.returncode==0,p.stderr.decode()[:2000]);require(core.file_pin(path)=={k:asset[k] for k in ("bytes","sha256")},"complete native archive")
def restore(archive,archive_root,expected,selected,destination):
    destination.mkdir(exist_ok=False);seen={};total=0
    with tarfile.open(archive,"r:gz") as tar:
        for member in tar:
            name=member.name
            if name==archive_root and member.isdir():continue
            require(name.startswith(archive_root+"/"),"original archive root")
            name=name[len(archive_root)+1:]
            require(name and not name.startswith("/") and all(p not in ("",".","..") for p in name.split("/")) and str(PurePosixPath(name))==name,"canonical archive member")
            if member.isdir():continue
            require(member.isfile() and name in expected and name not in seen,"unique expected regular archive member")
            require(member.size>=0 and member.size<2*1024**3,"member size")
            total+=member.size;require(total<4*1024**3,"archive expansion bound")
            h=hashlib.sha256();n=0;target=None
            try:
                if name in selected:
                    path=destination/name;path.parent.mkdir(parents=True,exist_ok=True);target=path.open("xb")
                stream=tar.extractfile(member)
                while True:
                    b=stream.read(1024**2)
                    if not b:break
                    n+=len(b);h.update(b)
                    if target:target.write(b)
            finally:
                if target:target.close()
            observed=dict(bytes=n,sha256=h.hexdigest());pin=expected[name]
            require(n==member.size and observed["sha256"]==(pin if isinstance(pin,str) else pin["sha256"]),"every original member hash")
            if isinstance(pin,dict):require(observed=={k:pin[k] for k in ("bytes","sha256")},"every original member bytes")
            seen[name]=observed
    require(set(seen)==set(expected) and set(selected)<=set(seen),"complete archive census")
    return dict(full_member_count=len(seen),full_members=seen,selected={n:seen[n] for n in selected},every_member_authenticated=True)
def producer_gate(p):
    runid=p.get("producer_run_id",p.get("run_id"));source=p.get("producer_source",p.get("source"))
    run=api("actions/runs/"+str(runid));r=api("releases/"+str(p["release_id"]));tag=api("git/ref/tags/"+p["tag"])
    require(run["status"]=="completed" and run["run_attempt"]==1 and run["head_sha"]==source,"exact terminal producer")
    require(run["conclusion"]==("success" if runid==41251732540 else "failure"),"retain original producer outcome")
    require(tag["object"]["type"]=="commit" and tag["object"]["sha"]==source,"original producer tag")
    require(r["tag_name"]==p["tag"] and r["target_commitish"]==p.get("actual_target_commitish",source),"original producer release")
    require({a["name"] for a in r["assets"]}=={a["name"] for a in p["assets"]},"complete original assets")
    for a in p["assets"]:
        live=next(x for x in r["assets"] if x["name"]==a["name"])
        require(live["id"]==a["id"] and live["size"]==a["bytes"] and live["digest"]=="sha256:"+a["sha256"],"original asset digest")
    return dict(run=run,release=r,tag=tag)
def acquire():
    p=json.loads((ROOT/"scripts/cdr-via2-m3-loaded-producer-inputs.json").read_bytes())
    save(DERIVED/"fresh-rc-producer.json",producer_gate(p))
    asset=next(a for a in p["assets"] if ".tar.gz.part" in a["name"])
    archive=NATIVE/"baseline.tar.gz";download_asset(asset,archive)
    selected={p[k]["path"] for k in ("model","composition","planes")}
    restored=NATIVE/"baseline"
    proof=restore(archive,p["archive_root"],p["complete_members"],selected,restored)
    save(DERIVED/"baseline-archive-census.json",proof)
    baseline={k:str(restored/p[k]["path"]) for k in ("model","composition","planes")}
    core.verify_current_inputs(baseline)
    cfg=json.loads((ROOT/"scripts/cdr-via2-m3-loaded-runtime-inputs.json").read_bytes())
    for name,pin in cfg["records"].items():require(core.file_pin(ROOT/name)==pin,"exact runtime metadata")
    rp=cfg["producer"];save(DERIVED/"runtime-producer.json",producer_gate(rp))
    summary=json.loads((ROOT/"docs/evidence/cdr-via2-m3-loaded-runtime-inputs/pump-summary.json").read_bytes())
    expected=dict(summary["outputs"]);expected["result.json"]=core.file_pin(ROOT/"docs/evidence/cdr-via2-m3-loaded-runtime-inputs/pump-summary.json")["sha256"]
    selected={n for n in expected if n.startswith("source/model-sources/") or n in ("source-pin.json","source/runtime/patched-ngspice","result.json")}
    require(len(expected)==120 and len(selected)==40,"complete runtime scope")
    asset=next(a for a in rp["assets"] if ".tar.gz.part" in a["name"])
    archive=NATIVE/"runtime.tar.gz";download_asset(asset,archive)
    restored=NATIVE/"runtime";proof=restore(archive,rp["archive_root"],expected,selected,restored)
    save(DERIVED/"runtime-archive-census.json",proof)
    engine=restored/"source/runtime/patched-ngspice";engine.chmod(0o755)
    runtime=dict(lib=str(restored/"source/model-sources"),engine=str(engine),source_pin=str(restored/"source-pin.json"),models_summary=str(restored/"result.json"))
    core.verify_runtime(runtime)
    return baseline,runtime
def run_engine(plan):
    path=Path(plan["stdout"]);require(not path.exists(),"exclusive engine log")
    require(core.file_pin(plan["argv"][0])==plan["engine"],"frozen engine executable")
    env={k:v for k,v in os.environ.items() if k not in plan["remove_environment_keys"]};env.update(plan["environment"])
    require(not any(k in env for k in ("GH_TOKEN","GITHUB_TOKEN","LD_PRELOAD","PYTHONPATH","PYTHONHOME")),"tokenless engine")
    began=time.monotonic();child=None;observations=[]
    record=dict(command=plan,engine_started=False,physical_acceptance=False)
    try:
        with path.open("xb") as log:
            child=subprocess.Popen(plan["argv"],cwd=plan["cwd"],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            record.update(engine_started=True,pid=child.pid)
            last=0
            while child.poll() is None:
                elapsed=time.monotonic()-began
                require(elapsed<1200,"original 1200 second engine budget")
                require(path.stat().st_size<=16*1024**2,"original engine log bound")
                if elapsed-last>=30:
                    print(json.dumps(dict(phase="transient",elapsed_seconds=elapsed,pid=child.pid,log_bytes=path.stat().st_size)),flush=True);last=elapsed
                time.sleep(.5)
            record.update(returncode=child.returncode,elapsed_seconds=time.monotonic()-began)
        return child.returncode
    except BaseException as error:
        record.update(error=repr(error),traceback=traceback.format_exc());raise
    finally:
        if child is not None and child.poll() is None:
            try:os.killpg(child.pid,signal.SIGTERM);child.wait(timeout=5)
            except (ProcessLookupError,subprocess.TimeoutExpired):
                if child.poll() is None:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=5)
        if child is not None:record["observed_returncode"]=child.returncode
        if path.is_file():record["native_log"]=core.file_pin(path)
        save(DERIVED/"engine-result.json",record)
def simulate():
    ctx=source_gate();OUT.mkdir(exist_ok=False);NATIVE.mkdir();DERIVED.mkdir()
    save(DERIVED/"context.json",ctx);admit(ctx)
    require(shutil.disk_usage(OUT).free>=8*1024**3,"8 GiB native workspace reserve")
    baseline,runtime=acquire();paths,delta=candidate.materialize(baseline,NATIVE/"candidate")
    save(DERIVED/"candidate-delta.json",delta)
    v=candidate.variant(baseline,paths);case=NATIVE/"case-nominal_late"
    prepared=v["prepare_case"](case,paths,runtime,ctx)
    require(prepared["report"]["binding_controls"]["rejected"] and len(prepared["report"]["binding_controls"]["rejected"])==13,"all original actual binding controls")
    source_gate()
    rc=run_engine(prepared["plan"])
    try:
        report=v["measure_case"](case,ctx,rc,core.file_pin(case/"prepared-state.json"))
    finally:
        path=case/"measurement-result.json"
        if path.is_file():shutil.copyfile(path,DERIVED/"measurement-result.json")
        source_gate()
    save(DERIVED/"result.json",dict(status="COMPLETE_EXPLORATORY_SAMPLER_LOAD_SCREEN",context=ctx,measurement=report,layout_regenerated=False,wire_rc_recomputed=False,physical_acceptance=False,full_phy_accepted=False,final_timing_complete=False))
def publish():
    ctx=source_gate();require(OUT.is_dir(),"existing candidate attempt")
    pub=OUT/"publication";pub.mkdir(exist_ok=False)
    r=release_gate(ctx,empty=True)
    save(DERIVED/"publication-reservation.json",r)
    source=DERIVED/"source";source.mkdir()
    pins=json.loads((ROOT/"scripts/cdr-sampler-load-host-pins.json").read_bytes())
    for name in [*pins["files"],"scripts/cdr-sampler-load-host-pins.json"]:
        target=source/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
    census={str(p.relative_to(OUT)):core.file_pin(p) for p in OUT.rglob("*") if p.is_file() and pub not in p.parents}
    save(pub/"complete-output-index.json",dict(context=ctx,files=census,physical_acceptance=False,full_phy_accepted=False))
    archive=pub/"native.tar.gz"
    with tarfile.open(archive,"w:gz",compresslevel=1) as tar:
        for name in sorted(census):tar.add(OUT/name,arcname="cloud-sampler-load/"+name,recursive=False)
    parts=[]
    with archive.open("rb") as stream:
        i=0
        while True:
            b=stream.read(256*1024**2)
            if not b:break
            path=pub/("native.tar.gz.part"+format(i,"04d"));path.write_bytes(b)
            parts.append(dict(name=path.name,index=i,**core.file_pin(path)));i+=1
    save(pub/"parts.json",dict(context=ctx,archive=core.file_pin(archive),source_directory="cloud-sampler-load",parts=parts))
    archive.unlink()
    for path in sorted(pub.iterdir()):
        if not path.is_file():continue
        p=subprocess.run(["gh","release","upload",r["tag_name"],str(path),"--repo",REPO],capture_output=True,text=True,timeout=900)
        require(p.returncode==0,p.stderr[:2000])
    observed=release_gate(ctx,empty=False)
    expected={p.name:core.file_pin(p) for p in pub.iterdir() if p.is_file()}
    require(set(expected)=={a["name"] for a in observed["assets"]},"complete published asset set")
    for a in observed["assets"]:require(a["size"]==expected[a["name"]]["bytes"] and a["digest"]=="sha256:"+expected[a["name"]]["sha256"],"published native bytes")
    save(DERIVED/"publication-result.json",dict(status="COMPLETE_NATIVE_PUBLICATION",release=observed["id"],tag=observed["tag_name"],assets=expected,physical_acceptance=False))
if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--publish",action="store_true");args=parser.parse_args()
    try:
        if args.publish:publish()
        else:simulate()
    except BaseException:
        DERIVED.mkdir(parents=True,exist_ok=True)
        name="publication-failure.txt" if args.publish else "failure.txt"
        (DERIVED/name).write_text(traceback.format_exc());raise
