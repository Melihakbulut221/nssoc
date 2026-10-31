#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only canonical-view projection of authentic physical/reference archives."""
import argparse,base64,contextlib,hashlib,json,os,shutil,signal,subprocess,sys,tarfile,tempfile,threading,traceback,types,zlib
from pathlib import Path
import cdr_via2_m3_canonical_view_admission as a
import cdr_v59_tail_access_runtime as runtime
import cloud_chunked_results as packer
from run_cloud_tx_layout_repair import fetch as runtime_fetch
import publish_cdr_via2_m3_canonical_view as publisher
q=a.q;ROOT=a.ROOT;require=a.require;encode=a.encode;write=q.write_new;pin=q.file_pin;decode=q.decode
frozen=types.SimpleNamespace(regular=q.regular)
FLAGS=a.FLAGS
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

def runtime_restore(out,preflight,reference,physical):
    ctx=a.context(os.environ);c=a.source_guard(ctx);a.native_preflight(preflight,ctx,c,reference,physical)
    spec=decode(q.regular(ROOT,'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_bytes())
    packed=out/'frozen-runtime.tar.gz';require(not packed.exists(),'runtime archive no overwrite')
    runtime_fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed)
    require(pin(packed)==dict(bytes=spec['receipt']['bytes'],sha256=spec['receipt']['sha256']),'pinned original frozen runtime')
    with tarfile.open(packed)as tar:tar.extractall(ROOT,filter='data')
    manifest=decode(q.regular(ROOT,'manifest.json').read_bytes())
    require(all(pin(q.regular(ROOT,n))['sha256']==v['sha256']for n,v in manifest['files'].items()),'complete original frozen runtime files')
    a.source_guard(ctx);a.native_preflight(preflight,ctx,c,reference,physical)
    write(out/'runtime-source-manifest.json',encode(manifest));packed.unlink()

def native_pipeline(reference,physical,out,preflight,c):
    ctx=a.context(os.environ);a.authorize_native(ctx,c);gate=lambda:a.source_guard(ctx)
    a.native_preflight(preflight,ctx,c,reference,physical)
    out=candidate_output(out)
    require(not out.exists()and not out.is_symlink(),'new native output');out.mkdir()
    policy=decode(q.regular(ROOT,'current-cdr-runtime-policy.json').read_bytes());app=Path(policy['appimage'])
    require(policy['source']==ctx['source']and policy['run_id']==ctx['run_id']and policy['attempt']==1,'current scoped runtime policy')
    require(app.is_absolute()and pin(app)['sha256']==c['appimage']['sha256']==policy['appimage_sha256'],'exact immutable AppImage')
    require(policy['loaded']is True and policy['global_policy_changed']is False and policy['restriction_before']==policy['restriction_after'],'scoped unchanged namespace restriction')
    require(policy['profile']=='/etc/apparmor.d/nssoc-cdr-runtime-'+ctx['token']and hashlib.sha256(policy['profile_text'].encode()).hexdigest()==policy['profile_sha256'],'exact run-owned runtime profile')
    write(out/'runtime-policy.json',encode(policy))
    launcher=runtime.launcher(ROOT,gate,'501d4846603abd42b9efeaf515a5ad45f136d58997e37b16329003623b9f33ac')
    supervisor=None;heartbeat=None;previous={};primary=None;errors=[];actions=[];commands=[]
    def execute(argv,label,seconds):
        argv=list(map(str,argv));failure=None
        try:
            with tokenless():supervisor.supervised(argv,label,seconds=seconds,cwd=ROOT)
        except BaseException as error:failure=error
        try:
            record=decode(q.regular(supervisor.TRACE,label+'.command.json').read_bytes());commands.append(record)
            require(record['argv']==argv and record['minimum_available_kib']==2097152 and record['maximum_group_rss_kib']==10485760,'exact original command and resource limits')
            for stream in('stdout','stderr'):require(pin(q.regular(supervisor.TRACE,label+'.'+stream))==dict(bytes=record[stream+'_bytes'],sha256=record[stream+'_sha256']),'complete command stream')
            events=[decode(b)for b in q.regular(supervisor.TRACE,'events.jsonl').read_bytes().splitlines()if b.strip()]
            starts=[e for e in events if e.get('event')=='command_start'and e.get('label')==label]
            require(len(starts)==1 and starts[0]['timeout_seconds']==seconds,'unchanged phase timeout')
            require(record['returncode']==0 and record['supervision_failure']is None and not record['process_group_cleanup']['remaining_live'],'actual native phase failed')
        except BaseException as error:
            if failure is None:failure=error
        if failure is not None:raise failure
    try:
        supervisor=runtime.supervisor(ROOT,out,out/'supervision',gate,runtime.SAMPLER_SHA);supervisor.TRACE.mkdir()
        for sig in(signal.SIGINT,signal.SIGTERM):previous[sig]=signal.getsignal(sig);signal.signal(sig,supervisor.interrupted)
        heartbeat=threading.Thread(target=supervisor.heartbeat,daemon=True);heartbeat.start()
        execute([sys.executable,ROOT/'scripts/cloud_cdr_via2_m3_canonical_view.py','--runtime','--output',out,'--preflight',preflight,'--reference',reference,'--physical',physical],'frozen-runtime',1200)
        with tokenless():smoke=launcher.probe(app,c['appimage']['sha256'],out/'runtime-smoke')
        require(smoke['accepted']is True,'pinned immutable runtime smoke')
        native_entry=ROOT/'scripts/cdr_via2_m3_canonical_view_native.py'
        def native(mode):
            execute([app,'python',native_entry,'--mode',mode,'--reference',reference,'--physical',physical,'--output',out,'--preflight',preflight],'canonical-'+mode,1200)
        native('prepare');view=out/'view/candidate'
        native('planes');native('recover')
        for worker in('probe01.py','locate01.py','anchors01.py','dedup01.py'):
            a.source_guard(ctx);a.native_preflight(preflight,ctx,c,reference,physical)
            execute([app,'python',view/'wire'/worker],'fresh-'+worker.removesuffix('.py'),1200)
        native('verify')
        qualification=decode(q.regular(out,'view/canonical-view-qualification.json').read_bytes())
        require(qualification['status']==c['core']['qualification_status'],'complete fresh canonical-view qualification')
        gate();a.native_preflight(preflight,ctx,c,reference,physical);require(pin(app)['sha256']==c['appimage']['sha256'],'runtime unchanged')
    except BaseException as error:primary=error
    finally:
        actions,cleanup=finish(supervisor,heartbeat,previous);errors+=cleanup
        evidence=dict(actions=actions,errors=[repr(e)for e in errors],primary_error=None if primary is None else repr(primary),commands=commands,**FLAGS)
        try:write(out/'native-lifecycle.json',encode(evidence))
        except BaseException as error:
            errors.append(error);print('UNSAVED_VIA2_M3_NATIVE_LIFECYCLE '+encode(dict(evidence,save_error=repr(error))).decode(),flush=True)
    if primary is not None:raise primary
    if errors:raise errors[0]
    return qualification

def authenticate_controls(ctx,out,api_call=q.api,fetch_log=a.read_source_log):
    c=a.source_guard(ctx);a.authorize_native(ctx,c)
    require(not out.exists()and not out.is_symlink(),'new owned source proof');out.mkdir(parents=True)
    try:
        run=api_call('actions/runs/'+str(ctx['run_id']));write(out/'run.json',encode(run))
        jobs=api_call('actions/runs/'+str(ctx['run_id'])+'/attempts/1/jobs?per_page=100');write(out/'jobs.json',encode(jobs))
        binding=a.validate_current_run(ctx,run,jobs);source_job=[j for j in jobs['jobs']if j['name']=='source-controls'][0]
        detail=api_call('actions/jobs/'+str(source_job['id']));write(out/'source-job.json',encode(detail))
        require(all(detail[k]==source_job[k]for k in('id','run_id','run_attempt','head_sha','name','status','conclusion','steps')),'exact actual completed source job')
        log=fetch_log(source_job['id']);write(out/'source-job.log',log)
        records,proof=a.authenticate_source_log(ctx,log)
        for name,raw in records.items():
            path=out/'records'/name;path.parent.mkdir(parents=True,exist_ok=True);write(path,raw)
        write(out/'receipt.json',encode(dict(proof,current_run_binding=binding,source_job_id=source_job['id'],all_acceptance_false=True)))
        a.source_guard(ctx)
        return records['canonical-view-controls/result.json']
    except BaseException as error:
        q.preserve_error(out,'failure.json',error,None);raise

def perform(ctx,c,reserved,controls_raw,out,api_call=q.api,fetch=q.download,pipeline=native_pipeline):
    a.authorize_native(ctx,c);a.source_guard(ctx)
    actual=authenticate_controls(ctx,out/'source-controls-evidence',api_call=api_call)
    require(actual==controls_raw,'independently repeated actual source proof')
    controls=a.bind_controls(controls_raw,ctx);write(out/'same-source-controls.json',controls_raw)
    write(out/'context.json',encode(ctx));write(out/'reservation-original.json',encode(reserved))
    current_run=api_call('actions/runs/'+str(ctx['run_id']));current_jobs=api_call('actions/runs/'+str(ctx['run_id'])+'/attempts/1/jobs?per_page=100')
    write(out/'current-run.json',encode(current_run));write(out/'current-jobs.json',encode(current_jobs))
    current_binding=a.validate_current_run(ctx,current_run,current_jobs)
    tag='cloud-results-'+ctx['token']+'-'+ctx['group'];info=api_call('releases/tags/'+tag);ref=api_call('git/ref/tags/'+tag)
    write(out/'result-release-empty.json',encode(info));write(out/'result-tag.json',encode(ref))
    reservation=q.reservation(ctx,reserved,info,ref)
    bindings={};maps={};parts={}
    def live(key,suffix):
        p=c['producers'][key];values=[]
        for name,path in(('run','actions/runs/'+str(p['run_id'])),('jobs','actions/runs/'+str(p['run_id'])+'/attempts/1/jobs?per_page=100'),('release','releases/'+str(p['release_id'])),('ref','git/ref/tags/'+p['tag'])):
            value=api_call(path);values.append(value);write(out/(key+'-producer-'+name+suffix+'.json'),encode(value))
        proof=a.validate_producer(c,key,*values);write(out/(key+'-producer-binding'+suffix+'.json'),encode(proof));return proof
    for key in('reference','physical'):
        bindings[key]=live(key,'');maps[key],parts[key]=a.metadata(c,key)
    needed=sum(p['bytes']for p in parts.values())+3*sum(v['bytes']for i in maps.values()for v in i['files'].values())+4*1024**3
    require(shutil.disk_usage(out.parent).free>=needed,'both complete immutable native archives plus view and evidence storage')
    (out/'inputs').mkdir();roots={key:out/'inputs'/key for key in parts};restored={};full={}
    primary=None;temp=tempfile.TemporaryDirectory(prefix='canonical-view-native-',dir=out.parent)
    try:
        for key in('reference','physical'):
            p=c['producers'][key];part=parts[key]['parts'][0];asset=next(x for x in p['assets']if x['name']==part['name'])
            archive=Path(temp.name)/(key+'-'+part['name']);fetch(asset,archive)
            require(pin(archive)==dict(bytes=parts[key]['bytes'],sha256=parts[key]['sha256']),'part and combined exact native archive bytes')
            write(out/(key+'-transport-proof.json'),encode(dict(asset=asset,combined=pin(archive),acquired_only_on_runner=True)))
            full[key]=q.select_archive(archive,{n:v['sha256']for n,v in maps[key]['files'].items()},list(maps[key]['files']),parts[key]['source_directory'],roots[key])
            write(out/(key+'-complete-input-census.json'),encode(full[key]));restored[key]=a.validate_restored(c,key,roots[key],full[key])
        preflight=dict(context=ctx,view_execution_authorized=True,generation_authorized=False,source_controls=controls,current_run_binding=current_binding,producer_bindings=bindings,reservation_binding=reservation,restore_roots={k:str(p)for k,p in roots.items()},restore_proofs=restored,original_absolute_results_rewritten=False,fresh_RC_executed=False,**FLAGS)
        write(out/'preflight.json',encode(preflight))
        qualification=pipeline(roots['reference'],roots['physical'],out/'native',out/'preflight.json',c)
        for key in roots:a.validate_restored(c,key,roots[key],full[key]);live(key,'-after')
        a.source_guard(ctx)
        return dict(status='PASS_CURRENT_VIA2_M3_FRESH_CANONICAL_VIEW_ONLY_REQUIRES_FRESH_RC_AND_WAVES',context=ctx,complete_reference_members=330,complete_physical_members=172,original_proofs_retained=True,qualification=qualification,**FLAGS)
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
    records=publisher.inventory(out);writer('VIA2_M3_VIEW_INDEX '+json.dumps(records,sort_keys=True),flush=True)
    selected={}
    for name,record in records.items():
        allowed=derived_text_name(name)
        if allowed:
            raw=q.regular(out,name).read_bytes()
            try:raw.decode('utf-8',errors='strict')
            except UnicodeError:allowed=False
        if not allowed:
            writer('VIA2_M3_VIEW_EXTERNAL '+json.dumps(dict(name=name,transport='complete reserved release and artifact only',**record),sort_keys=True),flush=True);continue
        selected[name]=record;packed=zlib.compress(raw,6)
        chunks=[packed[i:i+24576]for i in range(0,len(packed),24576)]or[b'']
        for i,chunk in enumerate(chunks):writer('VIA2_M3_VIEW_CHUNK '+json.dumps(dict(name=name,index=i,data=base64.b64encode(chunk).decode()),sort_keys=True),flush=True)
        writer('VIA2_M3_VIEW_END '+json.dumps(dict(name=name,chunks=len(chunks),**record),sort_keys=True),flush=True)
    return dict(complete_inventory=records,emitted_derived=selected,native_payload_emitted=False)

def run(ctx,c,reserved,controls_raw,out,body=perform,emitter=emit_derived):
    require(not out.exists()and not out.is_symlink(),'owned output no overwrite');out.mkdir(parents=True)
    primary=None;result=None
    try:
        result=body(ctx,c,reserved,controls_raw,out);write(out/'result.json',encode(result))
    except BaseException as error:
        primary=error;failure=dict(status='FAIL_CURRENT_VIA2_M3_CANONICAL_VIEW',context=ctx,error=repr(error),traceback=traceback.format_exc(),**FLAGS)
        try:write(out/'failure.json',encode(failure))
        except BaseException as second:print('UNSAVED_VIA2_M3_FAILURE '+encode(dict(failure,save_error=repr(second))).decode(),flush=True)
    try:emitter(out)
    except BaseException as error:
        q.preserve_error(out,'derived-emission-error.json',error,primary)
        if primary is None:primary=error
    if primary is not None:raise primary
    return result

def main():
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True);g.add_argument('--view',action='store_true');g.add_argument('--runtime',action='store_true');g.add_argument('--authenticate-controls',action='store_true')
    p.add_argument('--output',type=Path,required=True);p.add_argument('--preflight',type=Path);p.add_argument('--reference',type=Path);p.add_argument('--physical',type=Path);p.add_argument('--reservation',type=Path);p.add_argument('--controls-proof',type=Path);args=p.parse_args()
    ctx=a.context(os.environ);c=a.source_guard(ctx);a.authorize_native(ctx,c)
    if args.authenticate_controls:authenticate_controls(ctx,args.output);return
    if args.runtime:
        require(args.preflight is not None and args.reference is not None and args.physical is not None,'runtime preflight and two roots required');runtime_restore(args.output,args.preflight,args.reference,args.physical);return
    require(args.reservation is not None and args.controls_proof is not None,'independent reservation and actual controls required')
    run(ctx,c,decode(q.regular(args.reservation.parent,args.reservation.name).read_bytes()),q.regular(args.controls_proof.parent,args.controls_proof.name).read_bytes(),candidate_output(args.output))
if __name__=='__main__':main()
