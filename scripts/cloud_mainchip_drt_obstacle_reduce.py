#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""GitHub-only authenticated JSON reduction. No CAD, native archive or route execution."""
import argparse,hashlib,json,os,re,resource,signal,subprocess,time,traceback,types
from pathlib import Path
import mainchip_terminal_readback as q
import mainchip_drt_obstacle_reduce as core
ROOT=Path(__file__).resolve().parents[1]
BRANCH="codex/mainchip-drt-obstacle-reduction-v1"
GROUP="mainchip-drt-obstacle-reduction"
MANIFEST="scripts/mainchip-drt-obstacle-reduce-source.json"
CONFIG="scripts/mainchip-drt-obstacle-reduce-inputs.json"
OUT=ROOT/"obstacle-reduction"
EXPECTED_CONTROLS=58
MAX_OUTPUT_BYTES=64*1024*1024
INPUT_NAMES={"native-result.json","scope.json","host-result.json","inner-result.json","progress.json","command.json"}
def source_gate(mode):
    e=os.environ
    q.require(e.get("GITHUB_ACTIONS")=="true"and e.get("RUNNER_ENVIRONMENT")=="github-hosted","GitHub hosted only")
    q.require(e.get("GITHUB_REPOSITORY")==q.REPO and e.get("GITHUB_EVENT_NAME")=="workflow_dispatch"and e.get("GITHUB_REF")=="refs/heads/"+BRANCH,"exact actual manual source branch")
    q.require(mode in("controls","analysis")and e.get("MODE")==mode and e.get("GITHUB_JOB")==("source-controls"if mode=="controls"else"analysis"),"exact job/mode")
    head=e["GITHUB_SHA"];q.require(re.fullmatch("[0-9a-f]{40}",head)is not None and e.get("APPROVED_SOURCE")==head and e.get("GITHUB_RUN_ATTEMPT")=="1","exact approved source and first attempt")
    q.require(subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==head,"actual checkout")
    raw=(ROOT/MANIFEST).read_bytes()
    q.require(raw==subprocess.check_output(["git","show",head+":"+MANIFEST],cwd=ROOT),"exact committed manifest bytes")
    m=q.decode(raw);q.require(m["schema"]=="mainchip-obstacle-reduction-source-v1"and m["native_execution_authorized"]is False and m["routing_authorized"]is False,"derived-only source scope")
    for name,p in m["files"].items():
        q.valid_name(name);q.filepin(p);path=ROOT/name
        q.require(path.is_file()and not path.is_symlink()and q.pin(path)==p,"complete protected source "+name)
    c=q.decode((ROOT/CONFIG).read_bytes())
    q.require(c["schema"]=="mainchip-obstacle-reduction-inputs-v1"and c["native_execution_authorized"]is False and c["routing_authorized"]is False,"derived-only input scope")
    q.require(type(c["analysis_authorized"])is bool and c["analysis_authorized"]is m["analysis_authorized"],"same explicit readonly analysis authority")
    return head
def actual_context():
    head=source_gate("analysis");c=q.decode((ROOT/CONFIG).read_bytes())
    q.require(c["analysis_authorized"]is True,"Actual report acquisition remains disabled")
    return dict(source=head,run=int(os.environ["GITHUB_RUN_ID"]),attempt=1),c
def write(name,value):
    q.valid_name(name);q.require("/"not in name,"flat owned output")
    p=OUT/name;raw=q.encode(value);q.require(len(raw)<=MAX_OUTPUT_BYTES,"bounded complete JSON output")
    with p.open("xb")as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
def small_asset(asset,expected,api=q.api):
    q.require(asset["state"]=="uploaded"and asset["size"]==expected["bytes"]and asset["digest"]=="sha256:"+expected["sha256"],"uploaded exact source asset")
    q.require(expected["bytes"]<=2*1024*1024,"bounded small metadata asset")
    return q.checked(api("releases/assets/"+str(asset["id"]),True),expected)
def producer(config,api=q.api):
    p=config["producer"];run=api("actions/runs/"+str(p["run_id"]));release=api("releases/"+str(p["release_id"]));ref=api("git/ref/tags/"+p["tag"])
    q.require(run["id"]==p["run_id"]and run["status"]=="completed"and run["conclusion"]=="success"and run["head_sha"]==p["source"]and run["head_branch"]==p["branch"]and run["run_attempt"]==p["attempt"]==1 and run["path"]==p["workflow"],"actual completed source observer")
    q.require(q.immutable_release(release)==p["immutable_release"],"complete original publication immutable identity")
    q.require(ref["object"]["type"]=="commit"and ref["object"]["sha"]==p["source"],"original exact lightweight tag")
    jobs=api("actions/runs/"+str(p["run_id"])+"/attempts/1/jobs?per_page=100")
    q.require(jobs["total_count"]==len(jobs["jobs"])==3 and {j["name"]for j in jobs["jobs"]}=={"source-controls","preserve-job-log","observation"},"complete original jobs")
    q.require(all(j["status"]=="completed"and j["conclusion"]=="success"and j["head_sha"]==p["source"]and j["run_id"]==p["run_id"]and j["run_attempt"]==1 for j in jobs["jobs"]),"all original jobs successful")
    assets={a["name"]:a for a in release["assets"]};q.require(len(assets)==len(release["assets"])==44 and all(a["state"]=="uploaded"for a in release["assets"]),"all original assets fully uploaded")
    catalog=q.decode(small_asset(assets["readback-catalog.json"],p["catalog_pin"],api))
    receipt=q.decode(small_asset(assets["publication-receipt.json"],p["publication_receipt_pin"],api))
    q.require(catalog["source"]==receipt["source"]==p["source"]and catalog["run"]==receipt["run"]==p["run_id"],"same original source/run")
    q.require(receipt["release_id"]==p["release_id"]and receipt["tag"]==p["tag"]and receipt["receipt_self_not_in_files"]is True,"complete original receipt")
    q.require(set(assets)==set(receipt["files"])|{"publication-receipt.json"},"no partial/extra original assets")
    for name,pin in receipt["files"].items():
        q.filepin(pin);q.require(assets[name]["size"]==pin["bytes"]and assets[name]["digest"]=="sha256:"+pin["sha256"],"every original asset pin")
    q.require(len(catalog["files"])==54,"complete original 54-member catalog")
    selected=set();catalog_assets=[]
    for member,row in catalog["files"].items():
        q.valid_name(member);q.filepin({k:row[k]for k in("bytes","sha256")})
        q.require(type(row["derived_text"])is bool,"explicit source output kind")
        if row["bytes"]==0:
            q.require(row["name"]is None and row["embedded_empty"]is True and row["sha256"]==q.sha(b""),"exact embedded empty output")
        else:
            expected=q.sha(member.encode())[:16]+"-"+member.rsplit("/",1)[-1]
            q.require(row["name"]==expected and receipt["files"][expected]=={k:row[k]for k in("bytes","sha256")},"complete catalog member binding")
            catalog_assets.append(expected)
    q.require(len(catalog_assets)==len(set(catalog_assets))and set(catalog_assets)|{"readback-catalog.json"}==set(receipt["files"]),"complete unique source catalog")
    q.require(set(config["inputs"])==INPUT_NAMES,"exact selected JSON inputs")
    for name,pin in config["inputs"].items():
        row=catalog["files"][pin["member"]];asset=assets[pin["asset_name"]]
        q.require(row["derived_text"]is True and row["name"]==pin["asset_name"]and asset["id"]==pin["asset_id"],"selected exact derived asset")
        q.require({k:row[k]for k in("bytes","sha256")}=={k:pin[k]for k in("bytes","sha256")},"selected complete byte pin")
        selected.add(pin["member"])
    q.require(len(selected)==len(INPUT_NAMES),"no aliased selected members")
    return dict(run=run,jobs=jobs,release=release,ref=ref,catalog=catalog,receipt=receipt)
def same_source_controls(ctx,api=q.api):
    jobs=api("actions/runs/"+str(ctx["run"])+"/attempts/1/jobs?per_page=100")
    q.require(jobs["total_count"]==len(jobs["jobs"])==3 and {j["name"]for j in jobs["jobs"]}=={"source-controls","preserve-job-log","analysis"},"exact current three-job workflow")
    for j in jobs["jobs"]:
        q.require(j["head_sha"]==ctx["source"]and j["run_id"]==ctx["run"]and j["run_attempt"]==1,"current job source/attempt")
        if j["name"]!="analysis":q.require(j["status"]=="completed"and j["conclusion"]=="success","both successful current prerequisites")
        else:q.require(j["status"]=="in_progress","actual active analysis job")
    job=next(j for j in jobs["jobs"]if j["name"]=="source-controls")
    cmd=["gh","api","--allow-escape-sequences","repos/"+q.REPO+"/actions/jobs/"+str(job["id"])+"/logs"]
    raw=subprocess.check_output(cmd,stderr=subprocess.PIPE,timeout=60);raw.decode("utf-8-sig",errors="strict")
    records=[]
    for line in raw.decode("utf-8-sig").splitlines():
        m=re.fullmatch(r"\ufeff?\d{4}-\d\d-\d\dT[0-9:.]+Z MAINCHIP_OBSTACLE_REDUCTION_CONTROLS (\{.*\})",line)
        if m:records.append(q.decode(m[1]))
    q.require(len(records)==1,"single actual complete control record");r=records[0]
    q.require(r["source"]==ctx["source"]and r["status"]=="PASS_SOURCE_ONLY_OBSTACLE_REDUCTION_CONTROLS"and r["tests_run"]==EXPECTED_CONTROLS and r["successful"]is True and r["failures"]==r["errors"]==r["skipped"]==0,"all exact current controls")
    q.require(r["native_acquired"]is r["native_executed"]is r["actual_report_acquired"]is False,"source fixture never claims native/input acquisition")
    (OUT/"same-source-controls.log").write_bytes(raw);write("same-source-jobs.json",jobs);write("same-source-controls.json",r)
    return r
def download(name,pin,inputs):
    q.require(name in INPUT_NAMES,"exact input basename");path=inputs/name
    q.require(not path.exists(),"exclusive input download")
    stderr=OUT/(name+".download.stderr.log");started=time.monotonic()
    cmd=["gh","api","--allow-escape-sequences","repos/"+q.REPO+"/releases/assets/"+str(pin["asset_id"]),"-H","Accept: application/octet-stream"]
    record=dict(argv=cmd,expected={k:pin[k]for k in("bytes","sha256")},input=name)
    primary=None
    try:
        def file_bound():resource.setrlimit(resource.RLIMIT_FSIZE,(max(pin["bytes"]+1,1024*1024),max(pin["bytes"]+1,1024*1024)))
        with path.open("xb")as output,stderr.open("xb")as errors:
            done=subprocess.run(cmd,stdout=output,stderr=errors,timeout=300,check=False,preexec_fn=file_bound)
        record["returncode"]=done.returncode;q.require(done.returncode==0,"exact derived asset download failed")
        q.require(q.pin(path)==record["expected"],"complete downloaded input size/SHA256")
    except BaseException as error:primary=error;record["error"]=repr(error)
    finally:
        record["elapsed_seconds"]=time.monotonic()-started
        try:
            if path.exists():record["received"]=q.pin(path)
            if stderr.exists():record["stderr"]=q.pin(stderr)
        except BaseException as error:
            record["terminal_pin_error"]=repr(error)
            if primary is None:primary=error
        try:write(name+".download.json",record)
        except BaseException as error:
            print("UNSAVED_DOWNLOAD_RECORD "+json.dumps(dict(record,save_error=repr(error))),flush=True)
            if primary is None:primary=error
    if primary is not None:raise primary
    return path
def decode_file(path):
    with path.open("r",encoding="utf-8",errors="strict")as stream:
        return json.load(stream,object_pairs_hook=q.unique,parse_constant=lambda x:(_ for _ in()).throw(ValueError("nonfinite JSON")))
def validate_selected_inputs(values,config):
    host=values["host-result.json"];inner=values["inner-result.json"];command=values["command.json"];progress=values["progress.json"]
    q.require(host["status"]=="COMPLETE_READONLY_OBSTACLE_CLOUD_OBSERVATION"and host["primary_error"]is None and host["terminal_errors"]==[]and host["generated_output_preservation_complete"]is True,"complete original host")
    q.require(inner["status"]=="COMPLETE_READONLY_OBSTACLE_ENGINE"and inner["terminal_errors"]==[],"complete original engine")
    q.require(command["returncode"]==0 and command["supervision_failure"]is None and command["stderr_bytes"]==0 and command["stderr_sha256"]==q.sha(b""),"original successful command and empty stderr")
    q.require(command["argv"]==["/work/engine/openroad","-no_init","-exit","-python","/work/tail-source/scripts/mainchip_drt_obstacle_native.py"],"exact original observed command")
    q.require(command["minimum_available_kib"]==2097152 and command["maximum_group_rss_kib"]==10485760,"unchanged original resource guards")
    q.require(command["process_group_cleanup"]["remaining_live"]==[]and command["process_group_cleanup"]["remaining_nonrunning"]==[],"original process cleanup")
    q.require(progress["stage"]=="native-endpoint-census"and progress["observed_endpoint_names"]==progress["required_endpoint_names"]==values["scope.json"]["endpoint_names"],"complete original progress endpoint census")
    core.false_scope(progress)
def destination(ctx,empty,expected=None):
    f=types.FunctionType(q.destination.__code__,dict(q.destination.__globals__,GROUP=GROUP),q.destination.__name__,q.destination.__defaults__,q.destination.__closure__)
    tag,release=f(ctx["source"],empty,expected)
    q.require(release["id"]!=430206503,"original observation release is never a destination")
    return tag,release
def publication(ctx):
    destination(ctx,True);catalog={};expected={}
    allowed={"same-source-controls.log","same-source-jobs.json","same-source-controls.json","reservation.json",
      "producer-before.json","producer-after.json","witnesses.jsonl","endpoints.json","markers.json","other_markers.json","result.json"}
    allowed|={name+suffix for name in INPUT_NAMES for suffix in(".download.stderr.log",".download.json")}
    for path in sorted(OUT.iterdir()):
        q.require(path.is_file()and not path.is_symlink()and path.name in allowed,"known flat derived output only")
        # Unknown/binary partial bytes remain in the always-retained cloud artifact.
        with path.open("r",encoding="utf-8",errors="strict")as stream:
            while stream.read(1024*1024):pass
        p=q.pin(path);catalog[path.name]=dict(p,embedded_empty=p["bytes"]==0)
        if p["bytes"]:expected[path.name]=p
    write("readback-catalog.json",dict(source=ctx["source"],run=ctx["run"],files=catalog,all_large_inputs_retained_at_original_release=True,**core.FLAGS))
    expected["readback-catalog.json"]=q.pin(OUT/"readback-catalog.json")
    tag,_=destination(ctx,True)
    for name in expected:subprocess.run(["gh","release","upload",tag,str(OUT/name),"--repo",q.REPO],check=True,timeout=180)
    _,release=destination(ctx,False,expected)
    write("publication-receipt.json",dict(source=ctx["source"],run=ctx["run"],release_id=release["id"],tag=tag,files=dict(expected),receipt_self_not_in_files=True,**core.FLAGS))
    subprocess.run(["gh","release","upload",tag,str(OUT/"publication-receipt.json"),"--repo",q.REPO],check=True,timeout=180)
    expected["publication-receipt.json"]=q.pin(OUT/"publication-receipt.json")
    destination(ctx,False,expected)
def finish(ctx,result,reserved,primary,publish=publication):
    try:write("result.json",result)
    except BaseException as error:
        print("UNSAVED_REDUCTION_RESULT "+json.dumps(dict(result,save_error=repr(error))),flush=True)
        if primary is None:primary=error
    if reserved:
        try:publish(ctx)
        except BaseException as error:
            print("REDUCTION_PUBLICATION_FAILURE "+repr(error),flush=True)
            if primary is None:primary=error
    return primary
def limit(signum,frame):raise TimeoutError("Bounded 900-second derived report acquisition/reduction deadline")
def run():
    ctx,c=actual_context();q.require(not OUT.exists(),"exclusive result directory");OUT.mkdir()
    work=Path(os.environ["RUNNER_TEMP"])/(GROUP+"-"+str(ctx["run"])+"-1")
    q.require(not work.exists()and not work.is_symlink(),"exclusive cloud input directory")
    work.mkdir();inputs=work/"inputs";inputs.mkdir()
    result=dict(status="RUNNING",source=ctx["source"],run=ctx["run"],input_pins=c["inputs"],**core.FLAGS)
    primary=None;reserved=False;previous_handler=signal.getsignal(signal.SIGALRM)
    try:
        same_source_controls(ctx)
        deadline=time.monotonic()+180
        while True:
            try:tag,reservation=destination(ctx,True);break
            except subprocess.CalledProcessError as error:
                if b"HTTP 404"not in(error.stderr or b"")or time.monotonic()>=deadline:raise
                time.sleep(2)
        reserved=True;write("reservation.json",reservation)
        resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,8*1024**3))
        signal.signal(signal.SIGALRM,limit);signal.alarm(900)
        before=producer(c);write("producer-before.json",before)
        paths={name:download(name,pin,inputs)for name,pin in c["inputs"].items()}
        values={name:decode_file(path)for name,path in paths.items()}
        validate_selected_inputs(values,c)
        emitted=0;output_bytes=0
        with(OUT/"witnesses.jsonl").open("xb")as stream:
            def emit(row):
                nonlocal emitted,output_bytes
                raw=(json.dumps(row,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
                output_bytes+=len(raw);q.require(output_bytes<=MAX_OUTPUT_BYTES,"complete compact witness stream size bound")
                stream.write(raw);emitted+=1
            reduced=core.reduce_report(values["native-result.json"],values["scope.json"],emit)
            stream.flush();os.fsync(stream.fileno())
        q.require(emitted==reduced["summary"]["complete_witness_records"],"complete actual emitted witness stream")
        for name in("endpoints","markers","other_markers"):write(name+".json",reduced[name])
        for name,path in paths.items():q.require(q.pin(path)=={k:c["inputs"][name][k]for k in("bytes","sha256")},"input bytes unchanged after reduction")
        after=producer(c);write("producer-after.json",after)
        q.require(q.immutable_release(before["release"])==q.immutable_release(after["release"]),"original source publication unchanged")
        source_gate("analysis")
        result.update(reduced["summary"],source=ctx["source"],run=ctx["run"],complete_input_sha256_verified=True,original_large_result_retained_in_cloud=True)
    except BaseException as error:
        primary=error;result.update(status="FAIL_READONLY_OBSTACLE_REDUCTION",error=repr(error),traceback=traceback.format_exc())
    finally:
        signal.alarm(0);signal.signal(signal.SIGALRM,previous_handler)
        primary=finish(ctx,result,reserved,primary)
    if primary is not None:raise primary
    # Authenticated input bytes remain available in the original immutable release;
    # the runner work directory is only an acquisition copy, never a new result.
    for path in inputs.iterdir():path.unlink()
    inputs.rmdir();work.rmdir()
    print(json.dumps({k:result[k]for k in("status","source","run","selected_markers","endpoints","complete_witness_records")}),flush=True)
def main():
    p=argparse.ArgumentParser();p.add_argument("--controls",action="store_true");args=p.parse_args()
    if args.controls:print(source_gate("controls"))
    else:run()
if __name__=="__main__":main()
