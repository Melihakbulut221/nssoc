#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only actual-view acquisition and complete fresh-RC evidence lifecycle.

The native pipeline is separately source-bound; this incremental library alone
cannot execute extraction. Existing producer metadata is never rewritten.
"""
import argparse,base64,contextlib,hashlib,json,os,shutil,signal,subprocess,sys,tarfile,tempfile,threading,traceback,types,zlib
from pathlib import Path
import cdr_via2_m3_fresh_rc_admission as a
import cdr_via2_m3_fresh_rc_producer as producer
import cdr_v59_tail_access_runtime as runtime
from run_cloud_tx_layout_repair import fetch as runtime_fetch
import publish_cdr_via2_m3_fresh_rc as publisher
q=a.q;ROOT=a.ROOT;require=a.require;encode=a.encode;write=q.write_new;pin=q.file_pin;decode=q.decode
FLAGS=dict(physical_accepted=False,electrical_accepted=False,qualified_pex=False,full_phy_accepted=False,original_electrical_rejection_overridden=False,simulation_executed=False,layout_regenerated=False)

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

def authenticate_controls(ctx,out,api_call=q.api,fetch_log=a.read_source_log):
    c,p=a.source_guard(ctx);a.authorize_native(ctx,c)
    require(not out.exists()and not out.is_symlink(),'new owned source proof');out.mkdir(parents=True)
    try:
        run=api_call('actions/runs/'+str(ctx['run_id']));write(out/'run.json',encode(run))
        jobs=api_call('actions/runs/'+str(ctx['run_id'])+'/attempts/1/jobs?per_page=100');write(out/'jobs.json',encode(jobs))
        binding=a.validate_current_run(ctx,run,jobs);source_job=[j for j in jobs['jobs']if j['name']=='source-controls'][0]
        detail=api_call('actions/jobs/'+str(source_job['id']));write(out/'source-job.json',encode(detail))
        require(all(detail[k]==source_job[k]for k in('id','run_id','run_attempt','head_sha','name','status','conclusion','steps')),'exact actual completed source job')
        log=fetch_log(source_job['id']);write(out/'source-job.log',log)
        records,proof=a.authenticate_source_log(ctx,log,c)
        for name,raw in records.items():
            path=out/'records'/name;path.parent.mkdir(parents=True,exist_ok=True);write(path,raw)
        write(out/'receipt.json',encode(dict(proof,current_run_binding=binding,source_job_id=source_job['id'],all_acceptance_false=True)))
        a.source_guard(ctx)
        return records['fresh-rc-controls/result.json']
    except BaseException as error:
        q.preserve_error(out,'failure.json',error,None);raise

def perform(ctx,c,reserved,controls_raw,out,api_call=q.api,fetch=q.download,pipeline=None):
    a.authorize_native(ctx,c);actual_c,p=a.source_guard(ctx);require(c==actual_c,'current immutable configuration')
    require(pipeline is not None,'separately qualified fresh RC pipeline required')
    actual=authenticate_controls(ctx,out/'source-controls-evidence',api_call=api_call)
    require(actual==controls_raw,'independently repeated actual source proof')
    controls=a.bind_controls(controls_raw,ctx,c);write(out/'same-source-controls.json',controls_raw)
    write(out/'context.json',encode(ctx));write(out/'reservation-original.json',encode(reserved))
    current_run=api_call('actions/runs/'+str(ctx['run_id']));current_jobs=api_call('actions/runs/'+str(ctx['run_id'])+'/attempts/1/jobs?per_page=100')
    write(out/'current-run.json',encode(current_run));write(out/'current-jobs.json',encode(current_jobs))
    current_binding=a.validate_current_run(ctx,current_run,current_jobs)
    tag='cloud-results-'+ctx['token']+'-'+ctx['group'];info=api_call('releases/tags/'+tag);ref=api_call('git/ref/tags/'+tag)
    write(out/'result-release-empty.json',encode(info));write(out/'result-tag.json',encode(ref))
    reservation=q.reservation(ctx,reserved,info,ref)
    original=producer.metadata(ROOT,p)
    def live(suffix):
        values=[]
        for name,path in(('run','actions/runs/'+str(p['run_id'])),('jobs','actions/runs/'+str(p['run_id'])+'/attempts/1/jobs?per_page=100'),('release','releases/'+str(p['release_id'])),('ref','git/ref/tags/'+p['tag'])):
            value=api_call(path);values.append(value);write(out/('view-producer-'+name+suffix+'.json'),encode(value))
        proof=producer.validate_live(p,original,*values);write(out/('view-producer-binding'+suffix+'.json'),encode(proof));return proof
    binding=live('');parts=original['parts'];index=original['index'];restore=a.ORIGINAL
    require(out==a.OUT and not restore.exists()and not restore.is_symlink(),'new original absolute producer restore and exact fresh output')
    needed=parts['bytes']+8*sum(v['bytes']for v in index['files'].values())+16*1024**3
    require(shutil.disk_usage(out.parent).free>=needed,'entire immutable input plus fresh RC complete-evidence storage')
    write(out/'initial-storage.json',encode(dict(free_bytes=shutil.disk_usage(out.parent).free,required_bytes=needed)))
    primary=None;temp=tempfile.TemporaryDirectory(prefix='fresh-rc-native-',dir=out.parent)
    try:
        part=parts['parts'][0];asset=next(x for x in p['assets']if x['name']==part['name'])
        archive=Path(temp.name)/part['name'];fetch(asset,archive)
        require(pin(archive)==dict(bytes=parts['bytes'],sha256=parts['sha256']),'part and combined exact native archive bytes')
        write(out/'view-transport-proof.json',encode(dict(asset=asset,combined=pin(archive),acquired_only_on_runner=True)))
        full=q.select_archive(archive,{n:v['sha256']for n,v in index['files'].items()},list(index['files']),parts['source_directory'],restore)
        write(out/'view-complete-input-census.json',encode(full));restored=producer.validate_restored(restore,p,full,original)
        preflight=dict(context=ctx,fresh_rc_execution_authorized=True,generation_authorized=False,electrical_simulation_authorized=False,source_controls=controls,current_run_binding=current_binding,producer_binding=binding,reservation_binding=reservation,restore_root=str(restore),current_view_root=producer.CURRENT_ROOT,restore_proof=restored,original_absolute_results_rewritten=False,historical_producer_context_substituted=False,**FLAGS)
        write(out/'preflight.json',encode(preflight));a.native_preflight(out/'preflight.json',ctx,c,p)
        qualification=pipeline(Path(producer.CURRENT_ROOT),out,out/'preflight.json',c,p)
        producer.validate_restored(restore,p,full,original);live('-after');a.source_guard(ctx)
        return dict(status='PASS_CURRENT_VIA2_M3_FRESH_RC_REQUIRES_UNCHANGED_ELECTRICAL_WAVES',context=ctx,complete_view_producer_members=665,current_view_files=78,original_absolute_proofs_retained=True,qualification=qualification,**FLAGS)
    except BaseException as error:primary=error;raise
    finally:
        try:temp.cleanup()
        except BaseException as error:
            q.preserve_error(out,'native-archive-cleanup-error.json',error,primary)
            if primary is None:raise

def derived_text_name(name):
    """A text suffix never turns a native/compressed payload name into derived evidence."""
    p=Path(name)
    native={'.odb','.gds','.gds2','.gdsii','.oas','.oasis','.def','.lef','.spef','.spice','.sp','.cir','.l2n','.lvsdb','.lyrdb','.ext','.raw','.wave','.vcd','.fst','.bin','.tar','.gz','.zip','.7z'}
    suffixes={suffix.lower()for part in p.parts for suffix in Path(part).suffixes}
    return not name.startswith('inputs/')and all(not part.startswith('.')for part in p.parts)and not(native&suffixes)and p.suffix.lower()in{'.json','.jsonl','.log','.stdout','.stderr'}

def emit_derived(out,writer=print):
    # Complete native bytes remain in the release/artifact, never in local-bound logs.
    records=publisher.inventory(out);writer('VIA2_M3_RC_INDEX '+json.dumps(records,sort_keys=True),flush=True)
    selected={}
    for name,record in records.items():
        allowed=derived_text_name(name)
        if allowed:
            raw=q.regular(out,name).read_bytes()
            try:raw.decode('utf-8',errors='strict')
            except UnicodeError:allowed=False
        if not allowed:
            writer('VIA2_M3_RC_EXTERNAL '+json.dumps(dict(name=name,transport='complete reserved release and artifact only',**record),sort_keys=True),flush=True);continue
        selected[name]=record;packed=zlib.compress(raw,6)
        chunks=[packed[i:i+24576]for i in range(0,len(packed),24576)]or[b'']
        for i,chunk in enumerate(chunks):writer('VIA2_M3_RC_CHUNK '+json.dumps(dict(name=name,index=i,data=base64.b64encode(chunk).decode()),sort_keys=True),flush=True)
        writer('VIA2_M3_RC_END '+json.dumps(dict(name=name,chunks=len(chunks),**record),sort_keys=True),flush=True)
    return dict(complete_inventory=records,emitted_derived=selected,native_payload_emitted=False)

def run(ctx,c,reserved,controls_raw,out,body=perform,emitter=emit_derived):
    require(not out.exists()and not out.is_symlink(),'owned output no overwrite');out.mkdir(parents=True)
    primary=None;result=None
    try:
        result=body(ctx,c,reserved,controls_raw,out);write(out/'result.json',encode(result))
    except BaseException as error:
        primary=error;failure=dict(status='FAIL_CURRENT_VIA2_M3_FRESH_RC',context=ctx,error=repr(error),traceback=traceback.format_exc(),**FLAGS)
        try:write(out/'failure.json',encode(failure))
        except BaseException as second:print('UNSAVED_VIA2_M3_FAILURE '+encode(dict(failure,save_error=repr(second))).decode(),flush=True)
    try:emitter(out)
    except BaseException as error:
        q.preserve_error(out,'derived-emission-error.json',error,primary)
        if primary is None:primary=error
    if primary is not None:raise primary
    return result

if __name__=='__main__':
    raise SystemExit('Incomplete source-only host library; native entry requires separately reviewed integrated adapter')
