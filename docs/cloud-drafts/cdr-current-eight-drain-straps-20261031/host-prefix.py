#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only current eight-drain physical candidate with complete failure preservation."""
import argparse,hashlib,json,os,shutil,signal,subprocess,sys,threading,traceback,types
from pathlib import Path
import cloud_cdr_drain_m1_wave_replay as r
import cloud_cdr_current_wire_ownership as qualified
import publish_cdr_drain_wave_replay as publisher
import cloud_cdr_drain_m1_width_trial as original
import cdr_v59_tail_access_runtime as runtime
import cdr_current_tail_straps as plan
ROOT=Path(__file__).resolve().parents[1]
MANIFEST="scripts/cdr-current-tail-straps-pins.json"
CONFIG="scripts/cdr-current-tail-straps-inputs.json"
NATIVE="scripts/cdr_current_tail_straps_native.py"
GROUP="cdr-current-eight-drain-straps"
FLAGS=plan.FLAGS
require=plan.require
frozen=original.frozen
decode=r.decode
encode=r.encode
write=r.write_new
pin=r.file_pin
finish=original.finish
tokenless=original.tokenless
derive_physical=original.derive_physical
validate_physical=original.validate_physical
def context(env):
    ctx=r.context(env,"nominal_early");ctx["group"]=GROUP;ctx["tag"]="cloud-results-"+ctx["token"]+"-"+GROUP
    return ctx
def config():return r.decode((ROOT/CONFIG).read_bytes())
def source_guard(expected=None,root=ROOT):
    ctx=context(os.environ)
    if isinstance(expected,dict):require(ctx==expected,"current source context")
    qualified.source_guard(ctx)
    require(subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip()==ctx["source"],"exact current checkout")
    raw=r.regular(root,MANIFEST).read_bytes()
    require(raw==subprocess.check_output(["git","show",ctx["source"]+":"+MANIFEST],cwd=root),"unchanged current manifest")
    if isinstance(expected,str):require(hashlib.sha256(raw).hexdigest()==expected,"explicit current manifest")
    m=decode(raw)
    require(m["schema"]=="cdr-current-eight-drain-straps-pins-v1","current candidate manifest schema")
    require(m["source_controls_authorized"]is True and m["candidate_generation_authorized"]is True and m["physical_verification_authorized"]is True,"bounded candidate and physical authority")
    require(m["fresh_rc_authorized"]is False and m["electrical_simulation_authorized"]is False,"no unstated downstream authority")
    require(all(m[k]is False for k in FLAGS),"no final acceptance authorization")
    for path,digest in m["files"].items():require(r.file_pin(r.regular(root,path))["sha256"]==digest,"current source changed: "+path)
    return m
def bind_controls(ctx,records):
    require(set(records)=={"controls","publication","ownership","execution","tail"},"all current source control groups")
    checked=qualified.bind_controls(ctx,{k:v for k,v in records.items()if k!="tail"})
    tail=records["tail"]
    require(tail["status"]=="PASS_CURRENT_EIGHT_DRAIN_SOURCE_CONTROLS"and tail["count"]==20 and len(set(tail["passed_cases"]))==20,"current20 controls")
    require(tail["source"]==ctx["source"]and tail["run_id"]==ctx["run_id"]and tail["attempt"]==1,"fresh current control identity")
    require(tail["native_executed"]is False and all(tail[k]is False for k in FLAGS),"source controls cannot qualify physical candidate")
    checked["tail"]=dict(bytes=len(encode(tail)),sha256=hashlib.sha256(encode(tail)).hexdigest())
    return checked
def runtime_restore(out,expected,root=ROOT):
    source_guard(expected,root);ctx=context(os.environ)
    require(decode(frozen.regular(out,"preflight.json").read_bytes())["current_context"]==ctx,"authenticated runtime preflight")
    import cloud_cdr_v59_tail_access_physical as physical
    gate=lambda:source_guard(expected,root)
    namespace=dict(physical.runtime_worker.__globals__);namespace.update(authorize=gate,methods=gate,OUT=out)
    fn=types.FunctionType(physical.runtime_worker.__code__,namespace,physical.runtime_worker.__name__)
    require(fn.__code__ is physical.runtime_worker.__code__,"unchanged frozen runtime body")
    fn()
    manifest=decode(frozen.regular(out,"runtime-source-manifest.json").read_bytes())
    require(all(pin(frozen.regular(root,n))["sha256"]==v["sha256"]for n,v in manifest["files"].items()),"complete frozen runtime source")
    gate()

def native_readback(config,selected,out,expected,app,root=ROOT):
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
        execute([sys.executable,root/"scripts/cloud_cdr_current_tail_straps.py","--runtime","--output",out,"--pins-sha256",expected],"frozen-runtime",1200)
        with tokenless():smoke=launcher.probe(app,config["appimage"]["sha256"],out/"runtime-smoke")
        require(smoke["accepted"]is True,"pinned runtime smoke")
        execute([app,"python",root/NATIVE,"--selected",selected,"--output",out/"layout","--pins-sha256",expected],"eight-current-drain-straps",1800)
        generation=decode(frozen.regular(out,"layout/generation.json").read_bytes())
        require(generation["status"]=="PASS_EXACT_CURRENT_EIGHT_DRAIN_STRAP_GENERATION_ONLY"and generation["declared_additions_only"]is True,"generation exactness")
        physical=derive_physical(out,root)
        execute([sys.executable,physical,"--layout",out/"layout","--out",out/"physical","--app",app],"full560-DRC-deep-flat-LVS13",7200)
        qualified=validate_physical(out)
        write(out/"physical-qualification.json",encode(qualified))
        gate();require(pin(app)["sha256"]==config["appimage"]["sha256"],"AppImage changed")
    except BaseException as exc:primary=exc
    finally:
        actions,cleanup=finish(supervisor,heartbeat,previous);errors+=cleanup
        evidence=dict(actions=actions,errors=[repr(e)for e in errors],primary_error=None if primary is None else repr(primary),commands=commands)
        try:write(out/"native-lifecycle.json",encode(evidence))
        except BaseException as exc:
            errors.append(exc)
            try:print("CDR_CURRENT_TAIL_STRAPS_UNSAVED_LIFECYCLE "+json.dumps(evidence,sort_keys=True),flush=True)
            except BaseException:pass
    if primary is not None:raise primary
    if errors:raise errors[0]
    return pin(out/"physical-qualification.json")

