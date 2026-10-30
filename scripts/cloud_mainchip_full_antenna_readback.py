#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted, read-only whole-capsule antenna diagnosis. No CAD or model execution."""
import argparse,base64,hashlib,json,os,re,subprocess,tarfile,time,traceback,zlib
from pathlib import Path,PurePosixPath
import mainchip_full_antenna_report as report
ROOT=Path(__file__).resolve().parents[1]
REPO="Melihakbulut221/nssoc";BRANCH="codex/mainchip-net459-diode-prune"
GROUP="mainchip-full-antenna-readback"
MANIFEST="scripts/mainchip-full-antenna-readback-pins.json"
PRODUCER=40976029940
SOURCE="1a3b654cabaa4decc6201ad6efdac86dff80c5af"
RELEASE=428511278
TAG="cloud-results-40976029940-1-mainchip-net459-diode-prune"
ASSETS={
 "candidate-outputs.json":dict(id=690336463,bytes=9995,sha256="e124cdf0c9e93350803d5a0a62c46355b07f18be300eabf346e4745706ee6ae9"),
 "candidate-parts.json":dict(id=690336558,bytes=316,sha256="89ddce47439d028ee432fc80cfeb827f5dafa068127a893ec22ca83dc320d800"),
 "candidate-native.tar.gz.part000":dict(id=690336646,bytes=404651112,sha256="105c240da970283e3537da700c5a324ac1c8bdb30cd1307d8fb84c0eaa0a6902")}
SELECT={
 "work/net459-diode-prune/baseline-full-antenna.rpt",
 "work/net459-diode-prune/candidate-full-antenna.rpt",
 "work/net459-diode-prune/baseline-ant-counts.json",
 "work/net459-diode-prune/candidate-ant-counts.json",
 "net459-diode-prune/result.json","prune-baseline-ant.stdout","prune-candidate-check.stdout"}
def pin(path):
    h=hashlib.sha256();size=0
    with Path(path).open("rb")as f:
        for b in iter(lambda:f.read(1024**2),b""):h.update(b);size+=len(b)
    return dict(bytes=size,sha256=h.hexdigest())
def require(v,message):
    if not v:raise AssertionError(message)
def safe_name(name):
    require(isinstance(name,str)and name and "\\"not in name and "\x00"not in name,"archive path")
    p=PurePosixPath(name);require(not p.is_absolute()and all(x not in("","..",".")for x in name.split("/"))and str(p)==name,"canonical relative path")
    return p
def validate_map(files):
    require(isinstance(files,dict)and files,"nonempty census")
    for name,r in files.items():
        safe_name(name);require(set(r)=={"bytes","sha256"}and type(r["bytes"])is int and r["bytes"]>=0 and re.fullmatch("[0-9a-f]{64}",r["sha256"]),"file pin")
def context(env):
    require(env.get("GITHUB_ACTIONS")=="true"and env.get("RUNNER_OS")=="Linux","hosted Linux")
    require(env.get("GITHUB_REPOSITORY")==REPO and env.get("GITHUB_EVENT_NAME")=="workflow_dispatch","repository/event")
    require(env.get("GITHUB_REF")=="refs/heads/"+BRANCH and env.get("GITHUB_RUN_ATTEMPT")=="1","branch/attempt")
    source=env["GITHUB_SHA"];run=env["GITHUB_RUN_ID"]
    require(re.fullmatch("[0-9a-f]{40}",source)and re.fullmatch("[1-9][0-9]*",run),"context identifiers")
    require(subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()==source,"exact checkout")
    return dict(source=source,run=int(run),attempt=1,tag="cloud-results-"+run+"-1-"+GROUP)
def source_guard():
    p=ROOT/MANIFEST;require(p.is_file()and not p.is_symlink(),"manifest")
    m=json.loads(p.read_bytes());require(m["schema"]=="mainchip-full-antenna-readback-pins-v1","manifest schema")
    validate_map(m["files"])
    for name,row in m["files"].items():
        f=ROOT/name;require(f.is_file()and not f.is_symlink()and pin(f)==row,"source pin "+name)
    require(pin(ROOT/report.PRIMARY)["sha256"]==report.PRIMARY_SHA,"pinned native reporter source")
    return m
def api(path):
    for attempt in range(4):
        r=subprocess.run(["gh","api","repos/"+REPO+"/"+path],capture_output=True)
        if r.returncode==0:return json.loads(r.stdout)
        error=r.stderr.decode(errors="replace")
        transient=any(x in error for x in("TLS handshake timeout","connection reset","unexpected EOF","HTTP 502","HTTP 503","HTTP 504","i/o timeout"))
        if not transient or attempt==3:raise RuntimeError("GET "+path+": "+error)
        time.sleep(attempt+1)
def release_binding(info,ref,source,tag,rid):
    require(info["id"]==rid and info["tag_name"]==tag and info["target_commitish"]==source,"release identity")
    require(info["draft"]is False and info["prerelease"]is True,"public prerelease")
    require(ref["ref"]=="refs/tags/"+tag and ref["object"]["type"]=="commit"and ref["object"]["sha"]==source,"release ref")
    assets=info["assets"];require(len({a["id"]for a in assets})==len(assets)and len({a["name"]for a in assets})==len(assets),"unique assets")
    return {a["name"]:a for a in assets}
def reservation(ctx,out):
    for attempt in range(120):
        r=subprocess.run(["gh","api","repos/"+REPO+"/releases/tags/"+ctx["tag"]],capture_output=True)
        if r.returncode==0:break
        require(b"HTTP 404"in r.stderr,"reservation lookup failed");time.sleep(2)
    else:raise RuntimeError("independent exact-source release missing")
    info=json.loads(r.stdout);ref=api("git/ref/tags/"+ctx["tag"])
    assets=release_binding(info,ref,ctx["source"],ctx["tag"],info["id"]);require(not assets,"fresh independent reservation")
    record=dict(context=ctx,release_id=info["id"],empty=True,externally_reserved=True,creation_attempted=False,verified_before_acquisition=True)
    report.save(out/"reservation.json",record);return record
def producer(out):
    run=api("actions/runs/"+str(PRODUCER));jobs=api("actions/runs/"+str(PRODUCER)+"/attempts/1/jobs?per_page=100")
    require(run["head_sha"]==SOURCE and run["run_attempt"]==1 and run["status"]=="completed"and run["conclusion"]=="success","producer run")
    require({j["name"]for j in jobs["jobs"]}=={"source-controls","preserve-job-log","candidate"},"producer jobs")
    require(all(j["head_sha"]==SOURCE and j["conclusion"]=="success"for j in jobs["jobs"]),"producer terminal jobs")
    info=api("releases/"+str(RELEASE));ref=api("git/ref/tags/"+TAG)
    assets=release_binding(info,ref,SOURCE,TAG,RELEASE)
    require(set(assets)==set(ASSETS),"producer exact asset census")
    for name,row in ASSETS.items():
        a=assets[name];require(a["id"]==row["id"]and a["size"]==row["bytes"]and a.get("digest")=="sha256:"+row["sha256"],"producer asset "+name)
    for name,data in (("producer-run.json",run),("producer-jobs.json",jobs),("producer-release.json",info),("producer-ref.json",ref)):report.save(out/name,data)
def download(name,work,out):
    row=ASSETS[name];path=work/name;require(not path.exists(),"download no overwrite")
    with path.open("xb")as f:
        r=subprocess.run(["gh","api","repos/"+REPO+"/releases/assets/"+str(row["id"]),"-H","Accept: application/octet-stream"],stdout=f,stderr=subprocess.PIPE,timeout=900)
    (out/("download-"+name+".stderr")).write_bytes(r.stderr)
    require(r.returncode==0,"asset download "+name)
    require(pin(path)=={k:row[k]for k in("bytes","sha256")},"asset hash "+name)
    return path
def restore(archive,files,selected,root):
    validate_map(files);require(selected<=set(files),"selected native members")
    require(not root.exists()and not root.is_symlink(),"fresh extraction root");root.mkdir()
    observed={};seen=set();directories={str(p)for n in files for p in PurePosixPath(n).parents if str(p)!="."}
    with tarfile.open(archive,"r|gz")as tar:
        for member in tar:
            name=member.name;safe_name(name);require(name not in seen,"duplicate archive member");seen.add(name)
            if member.isdir():require(name in directories,"unexpected directory");continue
            require(member.isfile()and not member.issparse()and name in files,"special/unexpected member")
            row=files[name];require(member.size==row["bytes"],"declared native size")
            stream=tar.extractfile(member);require(stream is not None,"member stream")
            target=None
            if name in selected:
                target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target=target.open("xb")
            h=hashlib.sha256();size=0
            try:
                with stream:
                    for b in iter(lambda:stream.read(1024**2),b""):
                        size+=len(b);require(size<=row["bytes"],"member overrun");h.update(b)
                        if target is not None:target.write(b)
            finally:
                if target is not None:target.close()
            found=dict(bytes=size,sha256=h.hexdigest());require(found==row,"native member digest "+name);observed[name]=found
    require(observed==files,"complete archive census")
    require(all(pin(root/n)==files[n]for n in selected),"selected input hashes")
    return observed
def native_counts(root,label):
    base=root/"work/net459-diode-prune"
    counts=json.loads((base/(label+"-ant-counts.json")).read_bytes())
    require(counts==dict(full_count=609,net459_count=0,net459_violation=0),"native antenna counts")
    logfile=root/("prune-baseline-ant.stdout"if label=="baseline"else"prune-candidate-check.stdout")
    text=logfile.read_text()
    nets=[int(x)for x in re.findall(r"\[INFO ANT-0002\] Found ([0-9]+) net violations\.",text)]
    pins=[int(x)for x in re.findall(r"\[INFO ANT-0001\] Found ([0-9]+) pin violations\.",text)]
    require(len(nets)==len(pins)==2 and nets==[0,609]and pins[0]==0,"complete native antenna log calls")
    return dict(net_count=nets[-1],pin_count=pins[-1],calls=2)
def measure(root,out):
    actual=json.loads((root/"net459-diode-prune/result.json").read_bytes())
    require(actual["candidate_rejected"]is True and actual["measurement"]["marker_count"]==0,"original candidate outcome")
    parsed={}
    for label in("baseline","candidate"):
        count=native_counts(root,label)
        path=root/("work/net459-diode-prune/"+label+"-full-antenna.rpt")
        with path.open("r",encoding="ascii",newline="")as f:r=report.parse(f,count["net_count"])
        require(r[0]["violating_pins"]==count["pin_count"],"native pin counter reconciliation")
        r[0].update(native_log_counts=count,full_report=pin(path))
        for suffix,value in zip(("summary","net-census","violations"),r):report.save(out/(label+"-"+suffix+".json"),value)
        parsed[label]=r
    comparison=report.compare(parsed["baseline"],parsed["candidate"]);report.save(out/"comparison.json",comparison)
    return dict(status="COMPLETE_FULL609_ANTENNA_DIAGNOSIS_NOT_REPAIR",before=parsed["baseline"][0],after=parsed["candidate"][0],
      identical_violation_semantics=comparison["identical_violation_semantics"],
      changed_report_nets=len(comparison["changed_net_census"]),unchanged_current_native_input=True,
      physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
def publish(ctx,reserved,out):
    def live():
        d=api("releases/tags/"+ctx["tag"]);r=api("git/ref/tags/"+ctx["tag"])
        return release_binding(d,r,ctx["source"],ctx["tag"],reserved["release_id"])
    files={p.name:pin(p)for p in sorted(out.iterdir())if p.is_file()and not p.is_symlink()}
    require(len(files)==len(list(out.iterdir())),"regular flat output only")
    require(all(Path(n).suffix in(".json",".stdout",".stderr")for n in files),"derived output suffix")
    report.save(out/"publication-plan.json",dict(context=ctx,files=files,native_acquisition_local=False,all_outputs_derived=True))
    files["publication-plan.json"]=pin(out/"publication-plan.json")
    require(set(live())<=set(files),"unexpected publication asset")
    rows=[]
    for name,row in files.items():
        seen=live();error=None;stdout=b"";stderr=b""
        if name not in seen:
            try:
                p=subprocess.run(["gh","release","upload",ctx["tag"],str(out/name),"--repo",REPO],capture_output=True,timeout=900)
                stdout=p.stdout;stderr=p.stderr
                if p.returncode:error=p.stderr.decode(errors="replace")
            except BaseException as exc:
                error=repr(exc);stdout=getattr(exc,"stdout",None)or b"";stderr=getattr(exc,"stderr",None)or b""
        # Never blindly retry a mutating upload; reconcile its actual bytes once.
        seen=live();require(name in seen and seen[name]["size"]==row["bytes"]and seen[name].get("digest")=="sha256:"+row["sha256"],"permanent publication "+name+" "+str(error))
        require(pin(out/name)==row,"published output changed")
        rows.append(dict(name=name,id=seen[name]["id"],**row,reconciled_error=error,upload_stdout_base64=base64.b64encode(stdout).decode(),upload_stderr_base64=base64.b64encode(stderr).decode()))
    require(set(live())==set(files),"complete published census")
    return dict(status="COMPLETE_PERMANENT_DERIVED_PUBLICATION",context=ctx,release_id=reserved["release_id"],assets=rows)
def emit(out):
    index={p.name:pin(p)for p in sorted(out.iterdir())if p.is_file()}
    print("FULL_ANTENNA_INDEX "+json.dumps(index,sort_keys=True),flush=True)
    for name,row in index.items():
        if row["bytes"]>2*1024**2:continue
        packed=zlib.compress((out/name).read_bytes(),9)
        pieces=[packed[i:i+12000]for i in range(0,len(packed),12000)]or[b""]
        for i,b in enumerate(pieces):
            print("FULL_ANTENNA_CHUNK "+json.dumps(dict(name=name,index=i,chunks=len(pieces),**row,encoding="zlib-base64",base64=base64.b64encode(b).decode()),sort_keys=True),flush=True)
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--output",type=Path,required=True);a=ap.parse_args()
    ctx=context(os.environ);source_guard()
    require(not a.output.exists()and not a.output.is_symlink(),"fresh evidence");a.output.mkdir()
    work=Path(os.environ["RUNNER_TEMP"])/(GROUP+"-"+str(ctx["run"])+"-1")
    require(not work.exists()and not work.is_symlink(),"fresh owned workspace");work.mkdir()
    report.save(work/"owner.json",ctx)
    reserved=None;error=None
    try:
        reserved=reservation(ctx,a.output);producer(a.output)
        metadata=download("candidate-outputs.json",work,a.output);parts=download("candidate-parts.json",work,a.output)
        m=json.loads(metadata.read_bytes());ps=json.loads(parts.read_bytes())
        require(m["source"]==SOURCE and m["run"]==PRODUCER and m["attempt"]==1,"producer output identity")
        ar={k:ASSETS["candidate-native.tar.gz.part000"][k]for k in("bytes","sha256")}
        require(ps==dict(archive=ar,parts=[dict(name="candidate-native.tar.gz.part000",**ar)]),"exact single-part archive")
        archive=download("candidate-native.tar.gz.part000",work,a.output)
        observed=restore(archive,m["files"],SELECT,work/"selected")
        report.save(a.output/"full-native-census.json",observed)
        report.save(a.output/"input-binding.json",dict(source=SOURCE,producer=PRODUCER,release=RELEASE,archive=ar,full_members=len(observed),selected=sorted(SELECT),all_members_authenticated=True))
        for p in(metadata,parts):(a.output/p.name).write_bytes(p.read_bytes())
        result=measure(work/"selected",a.output)
        require(all(pin(work/"selected"/n)==observed[n]for n in SELECT),"selected input mutation")
        result.update(context=ctx,producer=PRODUCER,source_reporter_sha256=report.PRIMARY_SHA)
        report.save(a.output/"result.json",result)
    except BaseException as exc:
        error=exc;report.save(a.output/"failure.json",dict(error=repr(exc),traceback=traceback.format_exc(),context=ctx,physical_acceptance=False))
    finally:
        if reserved is not None:
            try:report.save(a.output/"publication.json",publish(ctx,reserved,a.output))
            except BaseException as exc:
                report.save(a.output/"publication-failure.json",dict(error=repr(exc),traceback=traceback.format_exc()))
                if error is None:error=exc
        emit(a.output)
    if error is not None:raise error
if __name__=="__main__":main()
