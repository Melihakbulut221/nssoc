#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only complete-capsule readback. No geometry or electrical acceptance."""
import argparse,contextlib,hashlib,json,os,re,shutil,signal,subprocess,sys,tempfile,threading,traceback
from pathlib import Path
import cloud_cdr_current_rc_contacts as frozen
import cdr_v59_tail_access_runtime as runtime
ROOT=Path(__file__).resolve().parents[1]
BRANCH="codex/cdr-current-access-overlay"
GROUP="cdr-current-access-overlay"
CONFIG="scripts/cdr-current-access-overlay-inputs.json"
PINS="scripts/cdr-current-access-overlay-pins.json"
NATIVE="scripts/cdr_current_access_overlay_native.py"
FLAGS=dict(geometry_changed=False,simulation_executed=False,electrical_acceptance=False,
 physical_acceptance=False,full_phy_accepted=False,resistor_footprint_assignment=False)
COUNTS=dict(positive=11,refusal=33,lifecycle=11)
require=frozen.require
encode=frozen.encode
decode=frozen.decode
pin=frozen.file_pin
write=frozen.write_new

def source_guard(expected,root=ROOT):
    require(re.fullmatch("[0-9a-f]{64}",expected or "")is not None,"explicit source manifest hash")
    raw=frozen.regular(root,PINS).read_bytes()
    require(hashlib.sha256(raw).hexdigest()==expected,"source manifest hash")
    manifest=decode(raw)
    require(manifest["schema"]=="current-access-overlay-source-pins-v1","source manifest schema")
    for name,value in manifest["files"].items():
        require(pin(frozen.regular(root,name))==value,"source bytes: "+name)
    require({CONFIG,NATIVE,"scripts/cloud_cdr_current_access_overlay.py","scripts/check_cdr_current_access_overlay.py"}<=set(manifest["files"]),"required source pins")
    config=decode(frozen.regular(root,CONFIG).read_bytes())
    require(config["schema"]=="current-access-overlay-inputs-v1"and config["branch"]==BRANCH and config["group"]==GROUP,"overlay source identity")
    require(config["scope"]==FLAGS,"overlay scope")
    require(config["runtime"]==dict(seconds=1200,min_available_kib=2097152,max_group_rss_kib=10485760),"original runtime limits")
    old=frozen.source_guard(root);data=frozen.metadata(old,root)
    require(config["producer"]==old["producer"]and config["original_full_count"]==len(data["full"])==6647,"original complete capsule")
    require(set(config["selected"])==set(config["paths"].values())and
      all(data["full"].get(n)==h for n,h in config["selected"].items()),"exact selected full paths")
    require(config["targets"]=={"28":{"native_name":"$131","component":17},"124":{"native_name":"$680","component":61}},"exact target identities")
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
    require(report.get("status")=="PASS_CURRENT_ACCESS_OVERLAY_SOURCE_CONTROLS"and report.get("passed")is True,"source controls status")
    require(report.get("counts")==COUNTS,"source controls counts")
    require(report.get("current_context")==dict(source=ctx["source"],run_id=ctx["run_id"],attempt=1,source_controls_only=True,native_executed=False),"same-source controls")
    require(report.get("native_executed")is False and report.get("physical_acceptance")is False,"source controls scope")
    old=report.get("original_archive_controls",{})
    require(old.get("status")=="PASS_CURRENT_RC_CONTACT_SOURCE_CONTROLS"and old.get("passed")is True and old.get("counts")==dict(positive=14,refusal=80,lifecycle=5)and old.get("native_executed")is False,"inherited archive controls")
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
    return config,old,data,dict(current_context=ctx,reservation=receipt,current_source_controls=controls,
      source_manifest_sha256=expected,producer=live,producer_run=run,producer_jobs=jobs,producer_release=release,producer_ref=ref)

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
    for sig,handler in previous.items():attempt("restore_signal_"+str(sig),lambda sig=sig,handler=handler:signal.signal(sig,handler))
    return actions,errors

def native_readback(config,selected,out,expected,app,root=ROOT):
    require(pin(app)["sha256"]==config["appimage"]["sha256"],"pinned AppImage")
    gate=lambda:source_guard(expected,root)
    launcher=runtime.launcher(root,gate,"501d4846603abd42b9efeaf515a5ad45f136d58997e37b16329003623b9f33ac")
    supervisor=None;heartbeat=None;previous={};primary=None;actions=[];errors=[]
    try:
        with tokenless():
            smoke=launcher.probe(app,config["appimage"]["sha256"],out/"runtime-smoke")
        require(smoke["accepted"]is True,"pinned runtime smoke")
        supervisor=runtime.supervisor(root,out,out/"supervision",gate,runtime.SAMPLER_SHA)
        supervisor.TRACE.mkdir()
        for sig in (signal.SIGINT,signal.SIGTERM):
            previous[sig]=signal.getsignal(sig);signal.signal(sig,supervisor.interrupted)
        heartbeat=threading.Thread(target=supervisor.heartbeat,daemon=True);heartbeat.start()
        argv=[str(app),"python",str(root/NATIVE),"--selected",str(selected),"--output",str(out/"overlay.json"),"--pins-sha256",expected]
        try:
            with tokenless():supervisor.supervised(argv,"access-overlay",seconds=1200,cwd=out)
        except BaseException as exc:primary=exc
        try:
            record=decode(frozen.regular(supervisor.TRACE,"access-overlay.command.json").read_bytes())
            require(record["argv"]==argv and record["minimum_available_kib"]==2097152 and record["maximum_group_rss_kib"]==10485760,"native command identity")
            for stream in ("stdout","stderr"):
                require(pin(frozen.regular(supervisor.TRACE,"access-overlay."+stream))==dict(bytes=record[stream+"_bytes"],sha256=record[stream+"_sha256"]),"full command stream")
            events=[decode(line)for line in frozen.regular(supervisor.TRACE,"events.jsonl").read_bytes().splitlines()if line.strip()]
            starts=[e for e in events if e.get("event")=="command_start"and e.get("label")=="access-overlay"]
            require(len(starts)==1 and starts[0]["argv"]==argv and starts[0]["timeout_seconds"]==1200 and starts[0]["minimum_available_kib"]==2097152 and starts[0]["maximum_group_rss_kib"]==10485760,"original command budget/resource event")
            require(record["returncode"]==0 and record["supervision_failure"]is None and not record["process_group_cleanup"]["remaining_live"],"native command failed")
            api_controls=decode(frozen.regular(out,"native-api-controls.json").read_bytes())
            require(api_controls==dict(status="PASS_PINNED_PYA_SYNTHETIC_POINT_CONTROLS",positive=5,synthetic_geometry=True,real_target_geometry_qualified=False),"actual pinned API controls")
            result=decode(frozen.regular(out,"overlay.json").read_bytes())
            require(result["status"]=="PASS_CURRENT_ACCESS_GEOMETRIC_OBSERVATION_NOT_EDGE_ATTRIBUTION"and result["scope"]==FLAGS,"native observation scope")
            require(pin(app)["sha256"]==config["appimage"]["sha256"],"runtime source mutation")
            gate()
        except BaseException as exc:
            if primary is None:primary=exc
            errors.append(exc)
    except BaseException as exc:
        if primary is None:primary=exc
    finally:
        actions,cleanup_errors=finish(supervisor,heartbeat,previous);errors+=cleanup_errors
        try:write(out/"native-lifecycle.json",encode(dict(actions=actions,errors=[repr(e)for e in errors],primary_error=None if primary is None else repr(primary))))
        except BaseException as exc:
            errors.append(exc)
            try:print("CDR_ACCESS_OVERLAY_UNSAVED_LIFECYCLE "+json.dumps(dict(actions=actions,errors=[repr(e)for e in errors],primary_error=None if primary is None else repr(primary)),sort_keys=True),flush=True)
            except BaseException:pass
    if primary is not None:raise primary
    if errors:raise errors[0]
    return pin(out/"overlay.json")

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
        observed=native_readback(config,work/"selected",out,expected,app,root)
        require(all(pin(frozen.regular(work/"selected",name))==census["selected"][name]for name in config["selected"]),"restored source mutation")
        return dict(status="PASS_CURRENT_ACCESS_OVERLAY_READBACK_NOT_ACCEPTANCE",current_context=ctx,
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
    # Qualified streaming implementation, new marker namespace only.
    def translated(line,**kwargs):writer(line.replace("CDR_RC_CONTACT_","CDR_ACCESS_OVERLAY_",1),**kwargs)
    return frozen.emit(out,translated)

def run(ctx,reserved,controls_raw,out,expected,app,root=ROOT,api_call=frozen.api,fetch=frozen.download):
    require(not out.exists()and not out.is_symlink(),"output no overwrite")
    out.mkdir(parents=True);primary=None
    try:
        result=perform(ctx,reserved,controls_raw,out,expected,app,root,api_call,fetch)
        source_guard(expected,root);write(out/"readback-result.json",encode(result));return result
    except BaseException as exc:
        primary=exc
        failure=dict(status="FAIL_CURRENT_ACCESS_OVERLAY_READBACK",current_context=ctx,
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
