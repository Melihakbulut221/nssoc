#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only complete-capsule readback. No geometry or electrical acceptance."""
import argparse,contextlib,hashlib,json,os,re,shutil,signal,subprocess,sys,tempfile,threading,traceback
from pathlib import Path
import cloud_cdr_current_rc_contacts as frozen
import cloud_cdr_drain_m1_width_trial as prior
import types
import cdr_v59_tail_access_runtime as runtime
ROOT=Path(__file__).resolve().parents[1]
BRANCH="codex/cdr-drain-m1-fresh-graph"
GROUP="cdr-drain-m1-fresh-graph"
CONFIG="scripts/cdr-drain-m1-fresh-graph-inputs.json"
PINS="scripts/cdr-drain-m1-fresh-graph-pins.json"
NATIVE="scripts/cdr_drain_m1_fresh_graph_native.py"
FLAGS=dict(geometry_changed=False,simulation_executed=False,electrical_acceptance=False,
 physical_acceptance=False,full_phy_accepted=False,fresh_RC_executed=False)
COUNTS=dict(positive=5,refusal=12,lifecycle=5)
require=frozen.require
encode=frozen.encode
decode=frozen.decode
pin=frozen.file_pin
write=frozen.write_new

def source_guard(expected,root=ROOT):
    raw=frozen.regular(root,PINS).read_bytes()
    require(re.fullmatch("[0-9a-f]{64}",expected or "")and hashlib.sha256(raw).hexdigest()==expected,"source manifest hash")
    manifest=decode(raw);require(manifest["schema"]=="drain-m1-fresh-graph-pins-v1","source manifest schema")
    for name,digest in manifest["protected_sha256"].items():
        require(pin(frozen.regular(root,name))["sha256"]==digest,"source bytes: "+name)
    baseline,old,data=prior.source_guard("d5d040630ca41d4e8f2815a090a468a96a46a655b9b3c7158013a10692921c2d",root)
    config=decode(frozen.regular(root,CONFIG).read_bytes())
    require(config["schema"]=="drain-m1-fresh-graph-inputs-v1"and config["branch"]==BRANCH and config["group"]==GROUP,"graph source identity")
    require(config["scope"]==FLAGS and config["source_controls_authorized"]is True and config["native_graph_authorized"]is True
      and config["native_physical_trial_authorized"]is False and config["fresh_rc_authorized"]is False,"typed graph-only authority")
    require(config["producer"]==old["producer"]and config["original_full_count"]==len(data["full"])==6647,"complete original RC inputs")
    require(all(data["full"].get(n)==digest for n,digest in config["selected"].items()),"exact current parent/reference source")
    require(config["runtime"]==baseline["runtime"]and config["appimage"]==baseline["appimage"],"original runtime")
    physical=config["physical"]
    proof=decode(frozen.regular(root,physical["proof_prefix"]+"diagnosis.json").read_bytes())
    require(pin(frozen.regular(root,physical["proof_prefix"]+"receipt.json"))["sha256"]==physical["receipt_sha256"],"actual physical receipt")
    require(proof["source"]==physical["producer"]["head_sha"]and proof["run_id"]==physical["producer"]["id"]
      and proof["candidate"]["gds"]==physical["gds"]and proof["candidate"]["flat_lvs"]==physical["lvs"],"actual candidate binding")
    require(proof["physical"]["categories"]==560 and proof["physical"]["markers"]==0 and proof["physical"]["deep_LVS"]==proof["physical"]["flat_LVS"]==500
      and proof["physical"]["original_faults_rejected"]==13,"actual full physical qualification")
    inventory=decode(frozen.regular(root,physical["proof_prefix"]+"readback/hw/soc/out/cloud-cdr-drain-m1-trial/permanent-output-inventory.json").read_bytes())
    full={n:v["sha256"]for n,v in inventory["complete_available_derived_files"].items()}
    full["hw/soc/out/cloud-cdr-drain-m1-trial/permanent-output-inventory.json"]=pin(frozen.regular(root,physical["proof_prefix"]+"readback/hw/soc/out/cloud-cdr-drain-m1-trial/permanent-output-inventory.json"))["sha256"]
    require(full==physical["full"]and len(full)==154,"complete actual physical archive map")
    require(set(physical["selected"])<=set(full),"selected physical map")
    prior.validate_rectangles(config["rectangles"])
    return config,old,data


def context(env):
    require(env.get("GITHUB_ACTIONS")=="true"and env.get("GITHUB_REPOSITORY")==frozen.REPOSITORY,"GitHub hosted repository only")
    require(env.get("GITHUB_EVENT_NAME")=="workflow_dispatch"and env.get("GITHUB_RUN_ATTEMPT")=="1","manual first attempt only")
    require(env.get("GITHUB_REF")=="refs/heads/"+BRANCH,"overlay branch")
    require(re.fullmatch("[0-9a-f]{40}",env.get("GITHUB_SHA",""))is not None,"current source")
    require(re.fullmatch("[1-9][0-9]*",env.get("GITHUB_RUN_ID",""))is not None,"current run")
    return dict(source=env["GITHUB_SHA"],run_id=int(env["GITHUB_RUN_ID"]),attempt=1,group=GROUP,token=env["GITHUB_RUN_ID"]+"-1")

def controls_binding(raw,ctx):
    report=decode(raw)
    require(report["status"]=="PASS_DRAIN_M1_FRESH_GRAPH_SOURCE_CONTROLS"and report["passed"]is True,"source controls status")
    require(report["current_context"]==dict(source=ctx["source"],run_id=ctx["run_id"],attempt=1,source_controls_only=True,native_executed=False),"same-source controls")
    require(report["native_executed"]is False and report["physical_acceptance"]is False,"source-only scope")
    require(report["counts"]==COUNTS,"complete current source controls")
    require(report["inherited"]["counts"]==dict(positive=5,refusal=10,lifecycle=4),"inherited lifecycle controls")
    return frozen.fingerprint(raw)

def preflight(ctx,reserved,controls_raw,expected,root=ROOT,api_call=frozen.api):
    config,old,data=source_guard(expected,root)
    controls=controls_binding(controls_raw,ctx)
    tag="cloud-results-"+ctx["token"]+"-"+GROUP
    receipt=frozen.reservation(ctx,reserved,api_call("releases/tags/"+tag),api_call("git/ref/tags/"+tag))
    run=api_call("actions/runs/"+str(old["producer"]["id"]))
    jobs=api_call("actions/runs/"+str(old["producer"]["id"])+"/attempts/1/jobs?per_page=100")
    release=api_call("releases/"+str(old["release_id"]));ref=api_call("git/ref/tags/"+old["tag"])
    live=frozen.validate_live(old,run,jobs,release,ref)
    p=config["physical"]
    physical_live=frozen.validate_live(p,api_call("actions/runs/"+str(p["producer"]["id"])),
      api_call("actions/runs/"+str(p["producer"]["id"])+"/attempts/1/jobs?per_page=100"),
      api_call("releases/"+str(p["release_id"])),api_call("git/ref/tags/"+p["tag"]))
    return config,old,data,dict(current_context=ctx,reservation=receipt,current_source_controls=controls,
      source_manifest_sha256=expected,physical_producer=physical_live,producer=live,producer_run=run,producer_jobs=jobs,producer_release=release,producer_ref=ref)

@contextlib.contextmanager
def tokenless():
    saved={k:os.environ.get(k)for k in ("GH_TOKEN","GITHUB_TOKEN")}
    try:
        for k in saved:os.environ.pop(k,None)
        yield
    finally:
        for k,v in saved.items():
            if v is None:os.environ.pop(k,None)
            else:os.environ[k]=v

def finish(supervisor,heartbeat,previous):
    errors=[];actions=[]
    def attempt(label,fn):
        try:actions.append(dict(action=label,completed=True,evidence=fn()))
        except BaseException as exc:
            errors.append(exc);actions.append(dict(action=label,completed=False,error=repr(exc)))
    if supervisor is not None:
        attempt("owned_process_cleanup",lambda:supervisor.stop_process(supervisor.ACTIVE))
        attempt("stop_heartbeat",supervisor.STOP.set)
    if heartbeat is not None:
        def join():
            heartbeat.join(timeout=5);require(not heartbeat.is_alive(),"heartbeat survived")
        attempt("join_heartbeat",join)
    for sig,handler in previous.items():
        def restore_signal(sig=sig,handler=handler):
            # signal.signal returns the replaced handler, which may be callable.
            # Record completed restoration without serializing that live object.
            signal.signal(sig,handler)
            return dict(signal=int(sig),restored=True)
        attempt("restore_signal_"+str(sig),restore_signal)
    return actions,errors

def runtime_restore(out,expected,root=ROOT):
    source_guard(expected,root);ctx=context(os.environ)
    require(decode(frozen.regular(out,"preflight.json").read_bytes())["current_context"]==ctx,"child authenticated current preflight")
    import cloud_cdr_v59_tail_access_physical as physical
    gate=lambda:source_guard(expected,root)
    namespace=dict(physical.runtime_worker.__globals__)
    namespace.update(authorize=gate,methods=gate,OUT=out)
    fn=types.FunctionType(physical.runtime_worker.__code__,namespace,physical.runtime_worker.__name__)
    require(fn.__code__ is physical.runtime_worker.__code__,"unchanged frozen runtime body")
    fn()
    manifest=decode(frozen.regular(out,"runtime-source-manifest.json").read_bytes())
    require(all(pin(frozen.regular(root,n))["sha256"]==v["sha256"]for n,v in manifest["files"].items()),"full frozen runtime source")
    gate()



def native_readback(config,selected,out,expected,app,root=ROOT,physical=None):
    require(out.is_relative_to(root/"hw/soc/out"),"candidate output under owned native output")
    require(pin(app)["sha256"]==config["appimage"]["sha256"],"pinned AppImage")
    gate=lambda:source_guard(expected,root)
    launcher=runtime.launcher(root,gate,"501d4846603abd42b9efeaf515a5ad45f136d58997e37b16329003623b9f33ac")
    supervisor=None;heartbeat=None;previous={};primary=None;errors=[];actions=[];commands=[]
    def execute(argv,label,seconds):
        failure=None
        try:
            with tokenless():supervisor.supervised(list(map(str,argv)),label,seconds=seconds,cwd=root)
        except BaseException as exc:failure=exc
        try:
            record=decode(frozen.regular(supervisor.TRACE,label+".command.json").read_bytes())
            require(record["argv"]==list(map(str,argv))and record["minimum_available_kib"]==2097152 and record["maximum_group_rss_kib"]==10485760,"exact command/resources")
            for stream in ("stdout","stderr"):
                require(pin(frozen.regular(supervisor.TRACE,label+"."+stream))==dict(bytes=record[stream+"_bytes"],sha256=record[stream+"_sha256"]),"full command stream")
            events=[decode(line)for line in frozen.regular(supervisor.TRACE,"events.jsonl").read_bytes().splitlines()if line.strip()]
            starts=[e for e in events if e.get("event")=="command_start"and e.get("label")==label]
            require(len(starts)==1 and starts[0]["timeout_seconds"]==seconds,"original phase deadline")
            commands.append(record)
            require(record["returncode"]==0 and record["supervision_failure"]is None and not record["process_group_cleanup"]["remaining_live"],"native phase failed")
        except BaseException as exc:
            if failure is None:failure=exc
        if failure is not None:raise failure
    try:
        supervisor=runtime.supervisor(root,out,out/"supervision",gate,runtime.SAMPLER_SHA);supervisor.TRACE.mkdir()
        for sig in (signal.SIGINT,signal.SIGTERM):
            previous[sig]=signal.getsignal(sig);signal.signal(sig,supervisor.interrupted)
        heartbeat=threading.Thread(target=supervisor.heartbeat,daemon=True);heartbeat.start()
        execute([sys.executable,root/"scripts/cloud_cdr_drain_m1_fresh_graph.py","--runtime","--output",out,"--pins-sha256",expected],"frozen-runtime",1200)
        with tokenless():smoke=launcher.probe(app,config["appimage"]["sha256"],out/"runtime-smoke")
        require(smoke["accepted"]is True,"pinned runtime smoke")
        require(physical is not None,"authenticated physical selection")
        common=[app,"python",root/NATIVE,"--selected",selected,"--physical",physical,"--output",out,"--pins-sha256",expected]
        for mode in ("prepare","planes","recover"):
            execute(common+["--mode",mode],"fresh-"+mode,1200)
        for name in ("probe01.py","locate01.py","anchors01.py","dedup01.py"):
            execute([app,"python",out/"candidate/wire"/name],"fresh-"+name.removesuffix(".py"),1200)
        execute(common+["--mode","verify"],"fresh-complete-identity-and-material",1200)
        report=decode(frozen.regular(out,"graph-qualification.json").read_bytes())
        require(report["status"]=="PASS_FRESH_TWO_M1_GRAPH_IDENTITIES_FULL_PARTITION_UNIONS_REQUIRES_RC","fresh graph result")
        gate();require(pin(app)["sha256"]==config["appimage"]["sha256"],"AppImage changed")
    except BaseException as exc:primary=exc
    finally:
        actions,cleanup=finish(supervisor,heartbeat,previous);errors+=cleanup
        evidence=dict(actions=actions,errors=[repr(e)for e in errors],primary_error=None if primary is None else repr(primary),commands=commands)
        try:write(out/"native-lifecycle.json",encode(evidence))
        except BaseException as exc:
            errors.append(exc)
            try:print("CDR_DRAIN_M1_UNSAVED_LIFECYCLE "+json.dumps(evidence,sort_keys=True),flush=True)
            except BaseException:pass
    if primary is not None:raise primary
    if errors:raise errors[0]
    return pin(out/"graph-qualification.json")

def perform(ctx,reserved,controls_raw,out,expected,app,root=ROOT,api_call=frozen.api,fetch=frozen.download):
    config,old,data,proof=preflight(ctx,reserved,controls_raw,expected,root,api_call)
    write(out/"preflight.json",encode(proof));write(out/"source-controls.json",controls_raw)
    require(shutil.disk_usage(out.parent).free>=data["parts"]["bytes"]+3*1024**3,"runner storage before acquisition")
    tmp=tempfile.TemporaryDirectory(prefix="cdr-access-overlay-",dir=out.parent);primary=None
    try:
        work=Path(tmp.name);archive,transport=frozen.acquire(old,data["parts"],work,fetch)
        write(out/"transport-proof.json",encode(transport))
        census=frozen.select_archive(archive,data["full"],list(config["selected"]),data["parts"]["source_directory"],work/"selected")
        write(out/"complete-input-census.json",encode(census))
        source_guard(expected,root)
        p=config["physical"];asset=p["assets"]["cdr-drain-m1-width-trial-evidence.tar.gz"]
        physical_archive=work/"physical.tar.gz";fetch(asset,physical_archive)
        physical_census=frozen.select_archive(physical_archive,p["full"],p["selected"],p["source_directory"],work/"physical")
        write(out/"complete-physical-census.json",encode(physical_census))
        observed=native_readback(config,work/"selected",out,expected,app,root,physical=work/"physical")
        require(all(pin(frozen.regular(work/"physical",name))==physical_census["selected"][name]for name in p["selected"]),"restored physical source mutation")
        require(all(pin(frozen.regular(work/"selected",name))==census["selected"][name]for name in config["selected"]),"restored source mutation")
        return dict(status="PASS_FRESH_TWO_M1_GRAPH_AND_TERMINAL_BINDING_REQUIRES_RC",current_context=ctx,
          complete_input_members=census["full_member_count"],selected=census["selected"],overlay=observed,
          source_manifest_sha256=expected,scope=FLAGS)
    except BaseException as exc:primary=exc;raise
    finally:
        try:tmp.cleanup()
        except BaseException as exc:
            try:write(out/"cleanup-error.json",encode(dict(error=repr(exc),primary_error=None if primary is None else repr(primary))))
            except BaseException:pass
            if primary is None:raise

def emit(out,writer=print):
    files={}
    for path in sorted(out.rglob("*")):
        require(not path.is_symlink(),"output symlink")
        if path.is_dir():continue
        require(path.is_file(),"nonregular output");files[path.relative_to(out).as_posix()]=pin(path)
    writer("CDR_DRAIN_M1_COMPLETE_INVENTORY "+json.dumps(files,sort_keys=True),flush=True)
    return files

def run(ctx,reserved,controls_raw,out,expected,app,root=ROOT,api_call=frozen.api,fetch=frozen.download):
    require(not out.exists()and not out.is_symlink(),"output no overwrite")
    out.mkdir(parents=True);primary=None
    try:
        result=perform(ctx,reserved,controls_raw,out,expected,app,root,api_call,fetch)
        source_guard(expected,root);write(out/"readback-result.json",encode(result));return result
    except BaseException as exc:
        primary=exc
        failure=dict(status="FAIL_DRAIN_M1_FRESH_GRAPH",current_context=ctx,
          error=dict(type=type(exc).__name__,message=str(exc)),traceback=traceback.format_exc(),scope=FLAGS)
        try:write(out/"readback-failure.json",encode(failure))
        except BaseException:
            try:print("CDR_ACCESS_OVERLAY_FAILURE "+json.dumps(failure,sort_keys=True),flush=True)
            except BaseException:pass
        raise
    finally:
        try:emit(out)
        except BaseException:
            if primary is None:raise

def main():
    if "--runtime" in sys.argv:
        parser=argparse.ArgumentParser();parser.add_argument("--runtime",action="store_true")
        parser.add_argument("--output",required=True,type=Path);parser.add_argument("--pins-sha256",required=True)
        args=parser.parse_args();runtime_restore(args.output,args.pins_sha256);return
    parser=argparse.ArgumentParser()
    modes=parser.add_mutually_exclusive_group(required=True);modes.add_argument("--preflight",action="store_true");modes.add_argument("--readback",action="store_true")
    parser.add_argument("--output",required=True,type=Path);parser.add_argument("--reservation",required=True,type=Path)
    parser.add_argument("--controls-proof",required=True,type=Path);parser.add_argument("--pins-sha256",required=True)
    parser.add_argument("--appimage",type=Path)
    args=parser.parse_args();ctx=context(os.environ)
    require(subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==ctx["source"],"checkout identity")
    reserved=decode(frozen.regular(args.reservation.parent,args.reservation.name).read_bytes())
    controls=frozen.regular(args.controls_proof.parent,args.controls_proof.name).read_bytes()
    if args.preflight:
        proof=preflight(ctx,reserved,controls,args.pins_sha256)[3]
        write(args.output,encode(proof));print(json.dumps(proof,sort_keys=True))
    else:
        require(args.appimage is not None and args.appimage.is_absolute(),"absolute pinned AppImage required")
        run(ctx,reserved,controls,args.output.resolve(),args.pins_sha256,args.appimage)
if __name__=="__main__":main()
