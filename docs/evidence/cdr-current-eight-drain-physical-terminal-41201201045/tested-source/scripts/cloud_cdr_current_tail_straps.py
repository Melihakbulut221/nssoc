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
    require(tail["status"]=="PASS_CURRENT_EIGHT_DRAIN_SOURCE_CONTROLS"and tail["count"]==22 and len(set(tail["passed_cases"]))==22,"current22 controls")
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


def publication_context(ctx):
    return dict(source=ctx["source"],run=ctx["run_id"],attempt=1,case=ctx["case"],group=ctx["group"],tag=ctx["tag"])


def do_work(ctx,proof,controls,bundle,evidence,report,expected,app):
    source_guard(expected);source_guard(ctx);report["controls"]=bind_controls(ctx,controls)
    require(app.is_absolute()and pin(app)["sha256"]==config()["appimage"]["sha256"],"pinned cloud AppImage")
    r.write_new(evidence/"same-source-controls.json",r.encode(controls))
    c=r.source_guard();pins=config()
    reserved=r.reservation(ctx,proof,r.api("releases/tags/"+ctx["tag"]),r.api("git/ref/tags/"+ctx["tag"]))
    r.write_new(evidence/"reservation.json",r.encode(dict(proof=proof,verified=reserved)))
    case=ctx["case"];entry=c["cases"][case]
    live={}
    for key,endpoint in(("run","actions/runs/"+str(c["producer"]["run_id"])),
      ("jobs","actions/runs/"+str(c["producer"]["run_id"])+"/attempts/1/jobs?per_page=100"),
      ("release","releases/"+str(entry["release_id"])),("ref","git/ref/tags/"+entry["tag"])):
        live[key]=r.api(endpoint);r.write_new(evidence/("producer-"+key+".json"),r.encode(live[key]))
    binding=r.validate_live(c,case,live["run"],live["jobs"],live["release"],live["ref"])
    summary,parts,original=r.metadata(c,case)
    names=plan.input_names(pins,summary["outputs"])
    r.write_new(evidence/"producer-live-binding.json",r.encode(binding))
    r.write_new(evidence/"producer-original-native-report.json",r.pinned(c,ROOT,entry["report_path"]))
    r.write_new(evidence/"selected-input-pins.json",r.encode(pins))
    r.require(shutil.disk_usage(bundle).free>=parts["bytes"]+4*1024**3,"runner disk before archive acquisition")
    transport=bundle/"transport";transport.mkdir()
    archive,received=r.acquire(c,case,parts,transport)
    r.write_new(evidence/"transport-proof.json",r.encode(received))
    saved=bundle/"native-inputs"
    census=r.select_archive(archive,summary["outputs"],names,parts["source_directory"],saved)
    r.write_new(evidence/"complete-input-census.json",r.encode(census))
    r.require(census["full_member_count"]==2797 and census["every_member_authenticated"]is True,"all original members")
    r.require(r.regular(saved,entry["report_member"]).read_bytes()==r.pinned(c,ROOT,entry["report_path"]),"received actual native report")
    r.require(r.file_pin(r.regular(saved,"result.json"))=={k:summary["raw_terminal"][k]for k in("bytes","sha256")},"received raw outer failure")
    # Full source archive remains permanently upstream. All selected native bytes
    # remain in our owned bundle for success/failure publication and fallback.
    shutil.rmtree(transport);report["input_census"]=dict(full_members=2797,selected=len(names),native_inputs_retained_in_bundle=True)
    report["actual_native_inputs_acquired"]=True
    native=bundle/"native";native.mkdir()
    write(native/"preflight.json",encode(dict(current_context=ctx,input_census=census,
      original_electrical_rejection_preserved=True,controls=report["controls"],**FLAGS)))
    physical=native_readback(pins,saved,native,expected,app)
    for name in names:require(r.file_pin(r.regular(saved,name))==census["selected"][name],"selected native input unchanged")
    source_guard(ctx);source_guard(expected)
    report.update(status="COMPLETE_CURRENT_EIGHT_DRAIN_PHYSICAL_TRIAL_ONLY",physical_report=physical,
      actual_native_inputs_acquired=True,physical_trial_completed=True,
      original_electrical_status=original["status"],original_electrical_rejection_preserved=True)
    return physical

def terminal_body(action,integrity,writer,report):
    """Preserve primary failure and independent integrity/terminal evidence."""
    primary=None
    try:action()
    except BaseException as exc:
        primary=exc;report["error"]=repr(exc);report["traceback"]=traceback.format_exc()
    finally:
        try:integrity()
        except BaseException as exc:report["terminal_errors"].append(dict(action="source-integrity",error=repr(exc)))
        if primary is not None or report["terminal_errors"]:report["status"]="FAIL_CURRENT_EIGHT_DRAIN_PHYSICAL_TRIAL"
        try:writer(report)
        except BaseException as exc:
            report["terminal_errors"].append(dict(action="terminal-record",error=repr(exc)));report["status"]="FAIL_CURRENT_EIGHT_DRAIN_PHYSICAL_TRIAL"
            print("CDR_TAIL_STRAPS_UNSAVED_TERMINAL "+json.dumps(report,sort_keys=True),flush=True)
            if primary is None:primary=exc
    if primary is not None:raise primary
    r.require(not report["terminal_errors"],"tail straps terminal errors")
    return report


def prepare_publication(ctx,bundle,destination):
    """Use qualified complete packing, with physical-trial-specific non-acceptance metadata."""
    import cloud_chunked_results as pack
    publisher.source_guard(publication_context(ctx))
    paths,index=publisher.prepare(publication_context(ctx),bundle,destination,pack.pack)
    path=paths[0];before=r.decode(path.read_bytes())
    r.require(before["schema"]=="complete-cdr-wave-replay-output-index-v1"
      and before["files"]==index["files"]and before["context"]==publication_context(ctx),"qualified complete index")
    after=dict(before);after["schema"]="complete-current-eight-drain-physical-output-index-v1"
    del after["original_capture_replayed_is_not_electrical_acceptance"]
    after.update(actual_capture_replayed=False,physical_trial_is_not_electrical_or_full_PHY_acceptance=True)
    path.write_bytes(r.encode(after))
    r.require(r.decode(path.read_bytes())==after,"owned corrected output index")
    return paths,index


def final_integrity(ctx,bundle,evidence):
    outcomes={};errors=[]
    def inputs():
        path=evidence/"complete-input-census.json"
        if not path.exists():return dict(applicable=False,complete_census_available=False,partial_inputs_retained=True)
        census=r.decode(r.regular(evidence,path.name).read_bytes())
        r.require(census["every_member_authenticated"]is True and census["full_member_count"]==2797 and len(census["selected"])==42,"terminal full input census")
        for name,pin in census["selected"].items():r.require(r.file_pin(r.regular(bundle/"native-inputs",name))==pin,"terminal selected input unchanged: "+name)
        return dict(applicable=True,complete_census_available=True,selected=len(census["selected"]),unchanged=True)
    for name,fn in(("source",lambda:source_guard(ctx)),("selected-inputs",inputs)):
        try:
            value=fn();outcomes[name]=dict(complete=True,result=dict(verified=True)if name=="source"else value)
        except BaseException as exc:
            outcomes[name]=dict(complete=False,error=repr(exc));errors.append(outcomes[name])
    r.write_new(evidence/"terminal-integrity.json",r.encode(outcomes))
    r.require(not errors,"independent terminal integrity errors: "+repr(errors))
    return outcomes


def preserve_derived(bundle,evidence):
    """Complete native text records are readable; GDS/LVS databases stay in the capsule."""
    native=bundle/"native";records={}
    if not native.exists():return records
    allowed={".json",".jsonl",".stdout",".stderr",".log",".txt",".tcl",".py",".rpt"}
    for path in sorted(native.rglob("*")):
        require(not path.is_symlink(),"native derived output symlink")
        if path.is_dir():continue
        require(path.is_file(),"native output regular file")
        if path.suffix not in allowed:continue
        name=path.relative_to(native).as_posix();raw=path.read_bytes()
        write(evidence/"native-records"/name,raw);records[name]=r.fingerprint(raw)
    write(evidence/"complete-native-text-index.json",encode(records))
    return records

def main():
    if "--runtime"in sys.argv:
        args=argparse.ArgumentParser();args.add_argument("--runtime",action="store_true")
        args.add_argument("--output",type=Path,required=True);args.add_argument("--pins-sha256",required=True)
        a=args.parse_args();runtime_restore(a.output,a.pins_sha256);return
    args=argparse.ArgumentParser()
    args.add_argument("--bundle",type=Path,required=True);args.add_argument("--publication",type=Path,required=True)
    args.add_argument("--reservation",type=Path,required=True);args.add_argument("--controls",type=Path,required=True)
    args.add_argument("--pins-sha256",required=True);args.add_argument("--appimage",type=Path,required=True)
    a=args.parse_args();ctx=context(os.environ)
    require(a.bundle.is_absolute()and a.bundle==ROOT/"hw/soc/out"/(GROUP+"-"+ctx["token"]),"exact owned cloud output")
    source_guard(ctx);source_guard(a.pins_sha256)
    r.require(not a.bundle.exists()and not a.bundle.is_symlink(),"new owned bundle")
    a.bundle.mkdir(parents=True);evidence=a.bundle/"evidence";evidence.mkdir()
    r.write_new(a.bundle/"owner.json",r.encode(ctx))
    report=dict(status="IN_PROGRESS",context=ctx,terminal_errors=[],physical_trial_completed=False,actual_native_inputs_acquired=False,**FLAGS)
    primary=None;proof=None
    try:
        proof=r.decode(a.reservation.read_bytes());controls=r.decode(a.controls.read_bytes())
        terminal_body(lambda:do_work(ctx,proof,controls,a.bundle,evidence,report,a.pins_sha256,a.appimage),
          lambda:final_integrity(ctx,a.bundle,evidence),lambda value:r.write_new(evidence/"result.json",r.encode(value)),report)
    except BaseException as exc:
        primary=exc
        if not(evidence/"result.json").exists():
            report.update(status="FAIL_CURRENT_EIGHT_DRAIN_PHYSICAL_TRIAL",error=repr(exc),traceback=traceback.format_exc())
            try:r.write_new(evidence/"result.json",r.encode(report))
            except BaseException as secondary:print("CDR_TAIL_STRAPS_TERMINAL_ERROR "+repr(secondary),flush=True)
    finally:
        try:preserve_derived(a.bundle,evidence)
        except BaseException as exc:
            print("CDR_TAIL_STRAPS_DERIVED_PRESERVATION_FAILURE "+repr(exc),flush=True)
            if primary is None:primary=exc
        try:
            r.require(proof is not None,"publication reservation loaded")
            source_guard(ctx)
            paths,index=prepare_publication(ctx,a.bundle,a.publication)
            receipt=publisher.publish(publication_context(ctx),proof,paths,a.publication)
            r.require(publisher.inventory(a.bundle)==index["files"],"published bundle unchanged")
            source_guard(ctx)
            print("CDR_TAIL_STRAPS_PUBLICATION "+json.dumps(dict(receipt=receipt,archive=index["archive"],
              complete_files=len(index["files"]),**FLAGS),sort_keys=True),flush=True)
        except BaseException as exc:
            print("CDR_TAIL_STRAPS_PUBLICATION_FAILURE "+json.dumps(dict(error=repr(exc),traceback=traceback.format_exc(),**FLAGS),sort_keys=True),flush=True)
            if primary is None:primary=exc
        try:r.emit(evidence)
        except BaseException as exc:
            print("CDR_TAIL_STRAPS_EMISSION_FAILURE "+repr(exc),flush=True)
            if primary is None:primary=exc
    if primary is not None:raise primary
if __name__=="__main__":main()
