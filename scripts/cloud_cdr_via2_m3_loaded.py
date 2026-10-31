#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only actual-view acquisition and complete loaded-screen evidence lifecycle.

The native pipeline is separately source-bound; this incremental library alone
cannot execute a transient. Existing producer metadata is never rewritten.
"""
import argparse,base64,contextlib,hashlib,json,os,shutil,signal,subprocess,sys,tarfile,tempfile,threading,traceback,types,zlib
from pathlib import Path
import cdr_via2_m3_loaded_admission as a
import cdr_via2_m3_loaded_producer as producer
import cdr_v59_tail_access_runtime as runtime
import publish_cdr_via2_m3_loaded as publisher
q=a.q;ROOT=a.ROOT;require=a.require;encode=a.encode;write=q.write_new;pin=q.file_pin;decode=q.decode
FLAGS=dict(physical_accepted=False,electrical_accepted=False,qualified_pex=False,full_phy_accepted=False,original_electrical_rejection_overridden=False,layout_regenerated=False)

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

def candidate_output(path,root=ROOT):
    root=root.resolve();base=root/'hw/soc/out'
    out=(path if path.is_absolute()else root/path).resolve()
    require(out!=base and out.is_relative_to(base),'native output must be an absolute descendant of project hw/soc/out')
    return out


def authenticate_controls(ctx,out,budget,api_call=None,fetch_log=None):
    api_call=(lambda path:a.api(path,budget))if api_call is None else api_call
    fetch_log=(lambda job:a.read_source_log(job,budget))if fetch_log is None else fetch_log
    c,p=a.source_guard(ctx,budget=budget);a.authorize_native(ctx,c)
    require(not out.exists()and not out.is_symlink(),'new owned source proof');out.mkdir(parents=True)
    try:
        run=api_call('actions/runs/'+str(ctx['run_id']));write(out/'run.json',encode(run))
        jobs=api_call('actions/runs/'+str(ctx['run_id'])+'/attempts/1/jobs?per_page=100');write(out/'jobs.json',encode(jobs))
        binding=a.validate_current_run(ctx,run,jobs);source_job=[j for j in jobs['jobs']if j['name']=='source-controls'][0]
        detail=api_call('actions/jobs/'+str(source_job['id']));write(out/'source-job.json',encode(detail))
        require(all(detail[k]==source_job[k]for k in('id','run_id','run_attempt','head_sha','name','status','conclusion','steps')),'exact actual completed source job')
        log=fetch_log(source_job['id']);write(out/'source-job.log',log)
        records,proof=a.authenticate_source_log(ctx,log,c)
        for name,raw in records.items():write(out/'records'/name,raw)
        write(out/'receipt.json',encode(dict(proof,current_run_binding=binding,source_job_id=source_job['id'],all_acceptance_false=True)))
        a.source_guard(ctx,budget=budget)
        return records['loaded-controls/result.json']
    except BaseException as error:q.preserve_error(out,'failure.json',error,None);raise

def require_qualification(value,c):
    require(isinstance(value,dict)and value.get('status')=='PASS_WHOLE_MIM_PD500_LOADED_SCREEN_NOT_CLOSED_LOOP_OR_PHY_SIGNOFF','unchanged full loaded screen status')
    require(value.get('case')=='nominal_late'and value.get('transient_executed')is True and value.get('sources_unchanged')is True,'actual original nominal_late measurement')
    require(value.get('devices_passed')is True and value.get('data_passed')is True and value['vi']['passed']is True,'all original electrical measurement gates')
    require(all(value.get(name)is False for name in('accepted','cdr_accepted','full_phy_accepted','qualified_pex','closed_loop')),'one screen does not confer PHY signoff')
    return value


def bind_engine_handoff(out,ctx,plan,plan_pin,prepared_pin,process):
    """Never substitute the wrapper code for the actual engine's signed result."""
    import cdr_via2_m3_loaded_native as entry
    engine_path=q.regular(out,'engine-result.json');engine_pin=pin(engine_path);record=decode(engine_path.read_bytes())
    rc=entry.validate_engine_result(out,plan,record,process['returncode'])
    write(out/'host-engine-binding.json',encode(dict(context=ctx,engine_result=engine_pin,actual_engine_returncode=rc,wrapper_returncode=process['returncode'],wrapper_receipt=pin(q.regular(out/'supervision','transient.command.json')),plan=plan_pin,prepared_state=prepared_pin)))
    return dict(engine_pin=engine_pin,actual_engine_returncode=rc)

def native_pipeline(original,out,preflight,c,p):
    import cdr_via2_m3_loaded_runtime as inputs
    import cdr_via2_m3_loaded_native as entry
    ctx=a.context(os.environ);require(out==a.OUT and original==a.ORIGINAL,'exact separate producer/case roots')
    def gate():
        with a.phase_budget(c['resources']['metadata_seconds'])as budget:
            a.source_guard(ctx,budget=budget);a.native_preflight(preflight,ctx,c,p)
    gate()
    with a.phase_budget(c['resources']['acquisition_seconds'])as budget:inputs.acquire(ROOT,out,ctx,c,p,budget)
    supervisor=None;heartbeat=None;previous={};primary=None;errors=[];commands=[];qualification=None
    native_entry=ROOT/'scripts/cdr_via2_m3_loaded_native.py';entry_pin=pin(native_entry)
    def execute(argv,label,allow_nonzero=False):
        argv=list(map(str,argv));gate();failure=None
        try:
            with tokenless():supervisor.supervised(argv,label,passed=False,seconds=c['resources']['engine_seconds'],cwd=ROOT)
        except BaseException as error:failure=error
        try:
            record=decode(q.regular(supervisor.TRACE,label+'.command.json').read_bytes());commands.append(record)
            require(record['argv']==argv and record['minimum_available_kib']==2097152 and record['maximum_group_rss_kib']==10485760,'exact owned wrapper and original resource gates')
            for stream in('stdout','stderr'):require(pin(q.regular(supervisor.TRACE,label+'.'+stream))==dict(bytes=record[stream+'_bytes'],sha256=record[stream+'_sha256']),'complete supervised wrapper stream')
            require(record['supervision_failure']is None and not record['process_group_cleanup']['remaining_live'],'supervision completion required')
            require(record['returncode']in(0,1)if allow_nonzero else record['returncode']==0,'explicit wrapper exit contract')
            require(pin(native_entry)==entry_pin,'actual native entry source unchanged')
            gate()
        except BaseException as error:
            if failure is None:failure=error
        if failure is not None:raise failure
        return record
    try:
        supervisor=runtime.supervisor(ROOT,out,out/'supervision',gate,runtime.SAMPLER_SHA);supervisor.TRACE.mkdir()
        for sig in(signal.SIGINT,signal.SIGTERM):previous[sig]=signal.getsignal(sig);signal.signal(sig,supervisor.interrupted)
        heartbeat=threading.Thread(target=supervisor.heartbeat,daemon=True);heartbeat.start()
        base=[sys.executable,'-B',native_entry,'--out',out]
        execute(base+['--phase','prepare'],'prepare')
        case=out/entry.CASE;plan_pin=pin(q.regular(case,'transient-command.json'));prepared_pin=pin(q.regular(case,'prepared-state.json'))
        plan,state=entry.prepared_contract(out,ctx,plan_pin,prepared_pin)
        write(out/'host-prepared-binding.json',encode(dict(context=ctx,entry=entry_pin,plan=plan_pin,prepared_state=prepared_pin,exact_plan=plan)))
        args=['--plan-bytes',plan_pin['bytes'],'--plan-sha256',plan_pin['sha256'],'--prepared-bytes',prepared_pin['bytes'],'--prepared-sha256',prepared_pin['sha256']]
        process=execute(base+['--phase','transient']+args,'transient',allow_nonzero=True)
        handoff=bind_engine_handoff(out,ctx,plan,plan_pin,prepared_pin,process);engine_pin=handoff['engine_pin']
        execute(base+['--phase','measure']+args+['--engine-bytes',engine_pin['bytes'],'--engine-sha256',engine_pin['sha256']],'measure')
        qualification=decode(q.regular(out,'measured-result.json').read_bytes());require_qualification(qualification,c)
        require(qualification==decode(q.regular(case,'measurement-result.json').read_bytes()),'complete original measurement output equality')
        gate()
    except BaseException as error:primary=error
    finally:
        actions,cleanup=finish(supervisor,heartbeat,previous);errors+=cleanup
        evidence=dict(actions=actions,errors=[repr(e)for e in errors],primary_error=None if primary is None else repr(primary),commands=commands,**FLAGS)
        try:write(out/'native-lifecycle.json',encode(evidence))
        except BaseException as error:
            errors.append(error);print('UNSAVED_LOADED_NATIVE_LIFECYCLE '+encode(dict(evidence,save_error=repr(error))).decode(),flush=True)
    if primary is not None:raise primary
    if errors:raise errors[0]
    return qualification

def storage_check(out,needed):
    storage=dict(free_bytes=shutil.disk_usage(out.parent).free,required_bytes=needed)
    write(out/'initial-storage.json',encode(storage))
    require(storage['free_bytes']>=storage['required_bytes'],'full immutable producer and native waveform evidence storage')
    return storage

def perform(ctx,c,reserved,controls_raw,out,pipeline=native_pipeline):
    temp=None;primary=None
    try:
        with a.phase_budget(c['resources']['acquisition_seconds'])as budget:
            a.authorize_native(ctx,c);actual_c,p=a.source_guard(ctx,budget=budget);require(c==actual_c,'current immutable configuration')
            actual=authenticate_controls(ctx,out/'source-controls-evidence',budget)
            require(actual==controls_raw,'independently repeated actual source proof')
            controls=a.bind_controls(controls_raw,ctx,c);write(out/'same-source-controls.json',controls_raw)
            write(out/'context.json',encode(ctx));write(out/'reservation-original.json',encode(reserved))
            current_run=a.api('actions/runs/'+str(ctx['run_id']),budget);current_jobs=a.api('actions/runs/'+str(ctx['run_id'])+'/attempts/1/jobs?per_page=100',budget)
            write(out/'current-run.json',encode(current_run));write(out/'current-jobs.json',encode(current_jobs));current_binding=a.validate_current_run(ctx,current_run,current_jobs)
            tag='cloud-results-'+ctx['token']+'-'+ctx['group'];info=a.api('releases/tags/'+tag,budget);ref=a.api('git/ref/tags/'+tag,budget)
            write(out/'result-release-empty.json',encode(info));write(out/'result-tag.json',encode(ref));reservation=q.reservation(ctx,reserved,info,ref)
            original=producer.metadata(ROOT,p)
            def live(suffix,budget):
                values=[]
                for name,path in(('run','actions/runs/'+str(p['producer_run_id'])),('jobs','actions/runs/'+str(p['producer_run_id'])+'/attempts/1/jobs?per_page=100'),('release','releases/'+str(p['release_id'])),('ref','git/ref/tags/'+p['tag'])):
                    value=a.api(path,budget);values.append(value);write(out/('rc-producer-'+name+suffix+'.json'),encode(value))
                proof=producer.validate_live(p,original,*values);write(out/('rc-producer-binding'+suffix+'.json'),encode(proof));return proof
            binding=live('',budget);parts=original['parts'];index=original['index'];restore=a.ORIGINAL
            require(out==a.OUT and not restore.exists()and not restore.is_symlink(),'new exact original absolute producer restore')
            storage_check(out,parts['bytes']+4*sum(v['bytes']for v in index['files'].values())+8*1024**3)
            temp=Path(tempfile.mkdtemp(prefix='loaded-native-',dir=out))
            part=parts['parts'][0];asset=next(x for x in p['assets']if x['name']==part['name']);archive=temp/part['name'];a.download(asset,archive,budget)
            require(pin(archive)==dict(bytes=parts['bytes'],sha256=parts['sha256']),'part and combined exact native archive bytes')
            write(out/'rc-transport-proof.json',encode(dict(asset=asset,combined=pin(archive),acquired_only_on_runner=True)))
            full=q.select_archive(archive,{n:v['sha256']for n,v in index['files'].items()},list(index['files']),parts['source_directory'],restore)
            write(out/'rc-complete-input-census.json',encode(full));restored=producer.validate_restored(restore,p,full,original)
            preflight=dict(context=ctx,loaded_execution_authorized=True,generation_authorized=False,fresh_rc_execution_authorized=False,source_controls=controls,current_run_binding=current_binding,producer_binding=binding,reservation_binding=reservation,restore_root=str(restore),restore_proof=restored,original_absolute_results_rewritten=False,historical_producer_context_substituted=False,**FLAGS)
            write(out/'preflight.json',encode(preflight));a.native_preflight(out/'preflight.json',ctx,c,p);budget.timeout(1)
        qualification=pipeline(restore,out,out/'preflight.json',c,p);require_qualification(qualification,c)
        with a.phase_budget(c['resources']['metadata_seconds'])as budget:
            producer.validate_restored(restore,p,full,original);live('-after',budget);a.source_guard(ctx,budget=budget)
        return dict(status='PASS_CURRENT_VIA2_M3_NOMINAL_LATE_LOADED_SCREEN_REQUIRES_FULL_MATRIX_AND_PHY_SIGNOFF',context=ctx,complete_rc_producer_members=3091,original_absolute_proofs_retained=True,qualification=qualification,simulation_executed=True,**FLAGS)
    except BaseException as error:primary=error;raise
    finally:
        if temp is not None:
            if primary is None:
                try:shutil.rmtree(temp)
                except BaseException as error:q.preserve_error(out,'native-archive-cleanup-error.json',error,primary);raise
            else:
                try:write(out/'failed-acquisition-retained.json',encode(dict(path=str(temp),native_bytes_remain_cloud_only=True,primary_error=repr(primary))))
                except BaseException as error:print('UNSAVED_FAILED_ACQUISITION '+repr(error),flush=True)

def derived_text_name(name):
    """A text suffix never turns a native/compressed payload name into derived evidence."""
    p=Path(name)
    native={'.odb','.gds','.gds2','.gdsii','.oas','.oasis','.def','.lef','.spef','.spice','.sp','.cir','.l2n','.lvsdb','.lyrdb','.ext','.raw','.wave','.vcd','.fst','.bin','.tar','.gz','.zip','.7z'}
    suffixes={suffix.lower()for part in p.parts for suffix in Path(part).suffixes}
    return not name.startswith('inputs/')and all(not part.startswith('.')for part in p.parts)and not(native&suffixes)and p.suffix.lower()in{'.json','.jsonl','.log','.stdout','.stderr'}

def emit_derived(out,writer=print):
    # Complete native bytes remain in the release/artifact, never in local-bound logs.
    records=publisher.inventory(out);writer('VIA2_M3_LOADED_INDEX '+json.dumps(records,sort_keys=True),flush=True)
    selected={}
    for name,record in records.items():
        allowed=derived_text_name(name)
        if allowed:
            raw=q.regular(out,name).read_bytes()
            try:raw.decode('utf-8',errors='strict')
            except UnicodeError:allowed=False
        if not allowed:
            writer('VIA2_M3_LOADED_EXTERNAL '+json.dumps(dict(name=name,transport='complete reserved release and artifact only',**record),sort_keys=True),flush=True);continue
        selected[name]=record;packed=zlib.compress(raw,6)
        chunks=[packed[i:i+24576]for i in range(0,len(packed),24576)]or[b'']
        for i,chunk in enumerate(chunks):writer('VIA2_M3_LOADED_CHUNK '+json.dumps(dict(name=name,index=i,data=base64.b64encode(chunk).decode()),sort_keys=True),flush=True)
        writer('VIA2_M3_LOADED_END '+json.dumps(dict(name=name,chunks=len(chunks),**record),sort_keys=True),flush=True)
    return dict(complete_inventory=records,emitted_derived=selected,native_payload_emitted=False)

def run(ctx,c,reserved,controls_raw,out,body=perform,emitter=emit_derived):
    require(not out.exists()and not out.is_symlink(),'owned output no overwrite');out.mkdir(parents=True)
    primary=None;result=None
    try:
        result=body(ctx,c,reserved,controls_raw,out);write(out/'result.json',encode(result))
    except BaseException as error:
        primary=error;failure=dict(status='FAIL_CURRENT_VIA2_M3_LOADED',context=ctx,error=repr(error),traceback=traceback.format_exc(),**FLAGS)
        try:write(out/'failure.json',encode(failure))
        except BaseException as second:print('UNSAVED_VIA2_M3_FAILURE '+encode(dict(failure,save_error=repr(second))).decode(),flush=True)
    try:emitter(out)
    except BaseException as error:
        q.preserve_error(out,'derived-emission-error.json',error,primary)
        if primary is None:primary=error
    if primary is not None:raise primary
    return result


def main():
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True);group.add_argument('--loaded',action='store_true');group.add_argument('--authenticate-controls',action='store_true')
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--reservation',type=Path);parser.add_argument('--controls-proof',type=Path);args=parser.parse_args()
    with a.phase_budget(180)as budget:
        ctx=a.context(os.environ);c,p=a.source_guard(ctx,budget=budget);a.authorize_native(ctx,c)
        if args.authenticate_controls:authenticate_controls(ctx,args.output,budget);return
    require(args.reservation is not None and args.controls_proof is not None,'independent reservation and actual same-source controls required')
    out=candidate_output(args.output);require(out==a.OUT,'exact new current loaded destination')
    run(ctx,c,decode(q.regular(args.reservation.parent,args.reservation.name).read_bytes()),q.regular(args.controls_proof.parent,args.controls_proof.name).read_bytes(),out)
if __name__=='__main__':main()
