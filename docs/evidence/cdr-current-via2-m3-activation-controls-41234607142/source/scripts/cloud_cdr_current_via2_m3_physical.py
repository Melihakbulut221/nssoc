#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only explicit current Via2/M3 generation and unchanged physical checker adapter."""
import argparse,base64,contextlib,hashlib,json,os,shutil,signal,subprocess,sys,tarfile,tempfile,threading,traceback,types,zlib
from pathlib import Path
import cdr_current_via2_m3_physical_admission as a
import cdr_v59_tail_access_runtime as runtime
import cloud_chunked_results as packer
from run_cloud_tx_layout_repair import fetch as runtime_fetch
import publish_cdr_current_via2_m3_physical as publisher
q=a.q;ROOT=a.ROOT;require=a.require;encode=a.encode;write=q.write_new;pin=q.file_pin;decode=q.decode
frozen=types.SimpleNamespace(regular=q.regular)
FLAGS=a.FLAGS
NATIVE='scripts/cdr_current_via2_m3_physical_native.py'
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

def derive_physical(out,root=ROOT):
    import cloud_cdr500_resistor_v59_physical as physical
    name="hw/soc/flow/check_pcie_cdr_sampler_active_input_v57_parent.py"
    original=frozen.regular(root,name).read_text()
    text,changes=physical.physical_source(original,"cd_shunt")
    require(len(changes)==4,"four immutable qualified physical substitutions")
    methods=out/"methods";methods.mkdir()
    write(methods/"check_physical.py",text.encode())
    value=dict(original=name,original_sha256=hashlib.sha256(original.encode()).hexdigest(),
      generated=pin(methods/"check_physical.py"),changes=changes,all_numerical_and560_13_gates_unchanged=True)
    write(out/"physical-derivation.json",encode(value));return methods/"check_physical.py"

def validate_physical(out):
    import cloud_cdr_v59_tail_access_physical as physical
    report=decode(frozen.regular(out,"physical/result.json").read_bytes())
    physical.validate_physical(report)
    expected=("drc","lvs","lvs_flat","v59_old_length","gain_gate_disconnected","gain_tail_width",
      "missing_gain_hbt","old_sampler_input_width","old_retime_width","wrong_follower_polarity",
      "old_data_header_length","wrong_finger_count","missing_hbt","q_open","rail_short","offgrid")
    require(set(report["steps"])==set(expected),"all original physical phases")
    for mode in ("lvs","lvs_flat"):
        require(report["steps"][mode]["native_primitive_census"]==dict(npn13g2=124,sg13_lv_nmos=50,rppd=98,cap_cmim=7,ptap1=221),"original500 primitive composition")
    require(all(pin(Path(n))["sha256"]==h for n,h in report["inputs"].items()),"actual physical input hashes")
    require(report["inputs"][str(out/"layout"/"nssoc_cdr_pd500_resistor_v59.gds")]==pin(out/"layout"/"nssoc_cdr_pd500_resistor_v59.gds")["sha256"],"new candidate GDS binding")
    require(report["serial_phy_complete"]is report["main_chip_integrated"]is report["qualified_pex"]is False,"no downstream acceptance")
    return dict(status=report["status"],report=pin(out/"physical/result.json"),full_DRC_categories=560,markers=0,
      deep_and_flat_devices=500,fault_controls=13,fresh_RC_executed=False,electrical_acceptance=False)

def emit_derived(out,writer=print):
    # Complete native bytes remain in the release/artifact, never in local-bound logs.
    records=publisher.inventory(out);writer('VIA2_M3_ADAPTER_INDEX '+json.dumps(records,sort_keys=True),flush=True)
    selected={}
    for name,record in records.items():
        allowed=not name.startswith('inputs/')and(name.endswith(('.json','.jsonl','.log','.stdout','.stderr')))
        if allowed:
            raw=q.regular(out,name).read_bytes()
            try:raw.decode('utf-8',errors='strict')
            except UnicodeError:allowed=False
        if not allowed:
            writer('VIA2_M3_ADAPTER_EXTERNAL '+json.dumps(dict(name=name,transport='complete reserved release and artifact only',**record),sort_keys=True),flush=True);continue
        selected[name]=record;packed=zlib.compress(raw,6)
        chunks=[packed[i:i+24576]for i in range(0,len(packed),24576)]or[b'']
        for i,chunk in enumerate(chunks):writer('VIA2_M3_ADAPTER_CHUNK '+json.dumps(dict(name=name,index=i,data=base64.b64encode(chunk).decode()),sort_keys=True),flush=True)
        writer('VIA2_M3_ADAPTER_END '+json.dumps(dict(name=name,chunks=len(chunks),**record),sort_keys=True),flush=True)
    return dict(complete_inventory=records,emitted_derived=selected,native_payload_emitted=False)

def runtime_restore(out,preflight,selected):
    ctx=a.context(os.environ);c=a.source_guard(ctx);a.native_preflight(preflight,ctx,c,selected)
    spec=decode(q.regular(ROOT,'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_bytes())
    packed=out/'frozen-runtime.tar.gz';require(not packed.exists(),'runtime archive no overwrite')
    runtime_fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed)
    require(pin(packed)==dict(bytes=spec['receipt']['bytes'],sha256=spec['receipt']['sha256']),'pinned original frozen runtime')
    with tarfile.open(packed)as tar:tar.extractall(ROOT,filter='data')
    manifest=decode(q.regular(ROOT,'manifest.json').read_bytes())
    require(all(pin(q.regular(ROOT,n))['sha256']==v['sha256']for n,v in manifest['files'].items()),'complete original frozen runtime files')
    a.source_guard(ctx);a.native_preflight(preflight,ctx,c,selected)
    write(out/'runtime-source-manifest.json',encode(manifest));packed.unlink()


def native_pipeline(selected,out,preflight,c):
    ctx=a.context(os.environ);a.authorize_native(ctx,c);gate=lambda:a.source_guard(ctx)
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
        execute([sys.executable,ROOT/'scripts/cloud_cdr_current_via2_m3_physical.py','--runtime','--output',out,'--preflight',preflight,'--selected',selected],'frozen-runtime',1200)
        with tokenless():smoke=launcher.probe(app,c['appimage']['sha256'],out/'runtime-smoke')
        require(smoke['accepted']is True,'pinned immutable runtime smoke')
        execute([app,'python',ROOT/NATIVE,'--selected',selected,'--output',out/'layout','--preflight',preflight],'exact16-via2-m3-generation',1800)
        generation=decode(q.regular(out/'layout','generation.json').read_bytes())
        require(generation['status']=='GENERATED_DECLARED_VIA2_M3_CANDIDATE_REQUIRES_FRESH_DRC_LVS_RC_WAVES'and generation['proof']['structural_reversal_exact']is True and len(generation['proof']['added_records'])==16,'complete exact declared reversible generation')
        checker=derive_physical(out,ROOT)
        execute([sys.executable,checker,'--layout',out/'layout','--out',out/'physical','--app',app],'full560-DRC-deep-flat-LVS13',7200)
        physical=validate_physical(out);write(out/'physical-qualification.json',encode(physical))
        gate();a.native_preflight(preflight,ctx,c,selected);require(pin(app)['sha256']==c['appimage']['sha256'],'runtime unchanged')
    except BaseException as error:primary=error
    finally:
        actions,cleanup=finish(supervisor,heartbeat,previous);errors+=cleanup
        evidence=dict(actions=actions,errors=[repr(e)for e in errors],primary_error=None if primary is None else repr(primary),commands=commands,**FLAGS)
        try:write(out/'native-lifecycle.json',encode(evidence))
        except BaseException as error:
            errors.append(error);print('UNSAVED_VIA2_M3_NATIVE_LIFECYCLE '+encode(dict(evidence,save_error=repr(error))).decode(),flush=True)
    if primary is not None:raise primary
    if errors:raise errors[0]
    return physical



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
        return records['cdr-via2-m3-adapter-controls/result.json']
    except BaseException as error:
        q.preserve_error(out,'failure.json',error,None);raise

def perform(ctx,c,reserved,controls_raw,out,api_call=q.api,fetch=q.download,pipeline=native_pipeline):
    a.authorize_native(ctx,c);a.source_guard(ctx)
    actual_controls=authenticate_controls(ctx,out/'source-controls-evidence',api_call=api_call)
    require(actual_controls==controls_raw,'independently repeated complete actual source proof')
    controls=a.bind_controls(controls_raw,ctx)
    write(out/'same-source-controls.json',controls_raw)
    write(out/'context.json',encode(ctx));write(out/'reservation-original.json',encode(reserved))
    current_run=api_call('actions/runs/'+str(ctx['run_id']));current_jobs=api_call('actions/runs/'+str(ctx['run_id'])+'/attempts/1/jobs?per_page=100')
    write(out/'current-run.json',encode(current_run));write(out/'current-jobs.json',encode(current_jobs))
    current_binding=a.validate_current_run(ctx,current_run,current_jobs)
    tag='cloud-results-'+ctx['token']+'-'+ctx['group']
    info=api_call('releases/tags/'+tag);ref=api_call('git/ref/tags/'+tag)
    write(out/'result-release-empty.json',encode(info));write(out/'result-tag.json',encode(ref))
    reservation=q.reservation(ctx,reserved,info,ref)
    prior=q.source_guard();entry=prior['cases'][c['case']]
    def live(suffix):
        values=[]
        for name,path in(('run','actions/runs/'+str(prior['producer']['run_id'])),('jobs','actions/runs/'+str(prior['producer']['run_id'])+'/attempts/1/jobs?per_page=100'),('release','releases/'+str(entry['release_id'])),('ref','git/ref/tags/'+entry['tag'])):
            value=api_call(path);values.append(value);write(out/('producer-'+name+suffix+'.json'),encode(value))
        proof=q.validate_current_case_live(prior,c['case'],*values);write(out/('producer-binding'+suffix+'.json'),encode(proof));return proof
    producer=live('');summary,parts,original=q.metadata(prior,c['case'])
    require(len(summary['outputs'])==2991 and all(summary['outputs'].get(n)==h for n,h in c['selected'].items()),'current exact2991 inventory and20selected')
    for name,key in(('summary','summary_path'),('parts','parts_path'),('native-result','report_path'),('original-publication','publication_path')):write(out/('producer-'+name+'.json'),q.pinned(prior,ROOT,entry[key]))
    require(shutil.disk_usage(out.parent).free>=parts['bytes']+4*1024**3,'full original archive plus candidate evidence storage')
    # Original 1.13GB archive remains permanently in its authentic producer release.
    # Every selected input and generated failure/output stays in this new cloud bundle.
    primary=None;temp=tempfile.TemporaryDirectory(prefix='via2-m3-original-',dir=out.parent)
    try:
        archive,received=q.acquire(prior,c['case'],parts,Path(temp.name),fetch);write(out/'transport-proof.json',encode(received))
        selected=out/'inputs';full=q.select_archive(archive,summary['outputs'],list(c['selected']),parts['source_directory'],selected)
        write(out/'complete-input-census.json',encode(full))
        require(full['full_member_count']==2991 and full['every_member_authenticated']is True and len(full['selected'])==20,'entire original archive authentication')
        require(full['selected']=={n:dict(bytes=c['selected_bytes'][n],sha256=h)for n,h in c['selected'].items()},'exact20 actual byte pins')
        require(q.regular(selected,entry['report_member']).read_bytes()==q.pinned(prior,ROOT,entry['report_path']),'original native report bytes')
        require(pin(q.regular(selected,'result.json'))=={k:summary['raw_terminal'][k]for k in('bytes','sha256')},'original raw outer result bytes')
        preflight=dict(context=ctx,generation_authorized=True,physical_verification_authorized=True,controls=controls,current_run_binding=current_binding,
          producer_binding=producer,reservation_binding=reservation,all2991_authenticated=True,selected=full['selected'],selected_root=str(selected.resolve()),original_rejection_preserved=True,**FLAGS)
        write(out/'preflight.json',encode(preflight));physical=pipeline(selected,out/'native',out/'preflight.json',c)
        for n,pin_before in full['selected'].items():require(pin(q.regular(selected,n))==pin_before,'all20 originals unchanged')
        live('-after');a.source_guard(ctx)
        return dict(status='PASS_CURRENT_VIA2_M3_GENERATION_AND_ORIGINAL_FULL_PHYSICAL_ONLY',context=ctx,selected_members=20,complete_input_members=2991,physical=physical,
          original_electrical_status=original['status'],original_rejection_preserved=True,new_RC_executed=False,**FLAGS)
    except BaseException as error:primary=error;raise
    finally:
        try:temp.cleanup()
        except BaseException as error:
            q.preserve_error(out,'original-archive-cleanup-error.json',error,primary)
            if primary is None:raise


def run(ctx,c,reserved,controls_raw,out,body=perform,emitter=emit_derived):
    require(not out.exists()and not out.is_symlink(),'owned output no overwrite');out.mkdir(parents=True)
    primary=None;result=None
    try:
        result=body(ctx,c,reserved,controls_raw,out);write(out/'result.json',encode(result))
    except BaseException as error:
        primary=error;failure=dict(status='FAIL_CURRENT_VIA2_M3_GENERATION_OR_PHYSICAL',context=ctx,error=repr(error),traceback=traceback.format_exc(),**FLAGS)
        try:write(out/'failure.json',encode(failure))
        except BaseException as second:print('UNSAVED_VIA2_M3_FAILURE '+encode(dict(failure,save_error=repr(second))).decode(),flush=True)
    try:emitter(out)
    except BaseException as error:
        q.preserve_error(out,'derived-emission-error.json',error,primary)
        if primary is None:primary=error
    if primary is not None:raise primary
    return result

def main():
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True);g.add_argument('--candidate',action='store_true');g.add_argument('--runtime',action='store_true');g.add_argument('--authenticate-controls',action='store_true')
    p.add_argument('--output',type=Path,required=True);p.add_argument('--preflight',type=Path);p.add_argument('--selected',type=Path);p.add_argument('--reservation',type=Path);p.add_argument('--controls-proof',type=Path);args=p.parse_args()
    ctx=a.context(os.environ);c=a.source_guard(ctx);a.authorize_native(ctx,c)
    if args.authenticate_controls:
        authenticate_controls(ctx,args.output);return
    if args.runtime:
        require(args.preflight is not None and args.selected is not None,'runtime preflight required');runtime_restore(args.output,args.preflight,args.selected);return
    require(args.reservation is not None and args.controls_proof is not None,'independent reservation and actual control proof required')
    run(ctx,c,decode(q.regular(args.reservation.parent,args.reservation.name).read_bytes()),q.regular(args.controls_proof.parent,args.controls_proof.name).read_bytes(),args.output)
if __name__=='__main__':main()
