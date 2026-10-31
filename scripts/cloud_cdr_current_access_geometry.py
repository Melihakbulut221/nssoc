#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read actual current GDS/L2N ownership on a hosted runner, preserving original rejection."""
import argparse,contextlib,copy,json,os,shutil,subprocess,tempfile,traceback,types,signal,sys,threading
from pathlib import Path
import cloud_cdr_current_eight_drain_wave_replay as q
import cdr_v59_tail_access_runtime as runtime
ROOT=Path(__file__).resolve().parents[1]
BRANCH='codex/cdr-current-access-geometry-readback'
CONFIG='scripts/cdr-current-access-geometry-inputs.json'
MANIFEST='scripts/cdr-current-access-geometry-source-pins.json'
GROUP='cdr-current-access-geometry-readback'
FLAGS=dict(accepted=False,electrical_accepted=False,timing_accepted=False,full_phy_accepted=False,physical_acceptance=False,qualified_pex=False,new_simulation=False,geometry_changed=False,causality_proven=False)
require=q.require
encode=q.encode

def context(env,case=None):
    require(env.get('GITHUB_ACTIONS')=='true'and env.get('GITHUB_EVENT_NAME')=='workflow_dispatch','hosted manual only')
    require(env.get('GITHUB_REPOSITORY')==q.REPOSITORY and env.get('GITHUB_REF')=='refs/heads/'+BRANCH,'repository/branch')
    require(env.get('GITHUB_RUN_ATTEMPT')=='1','attempt one')
    source=env.get('GITHUB_SHA','');run=env.get('GITHUB_RUN_ID','')
    require(q.re.fullmatch('[0-9a-f]{40}',source)and q.re.fullmatch('[1-9][0-9]*',run),'source/run')
    c=dict(source=source,run_id=int(run),attempt=1)
    if case is not None:
        require(case=='nominal_late','one pinned existing case')
        c.update(case=case,group=GROUP+'-'+case,token=run+'-1')
    return c

def source_guard(root=ROOT):
    c=q.decode(q.regular(root,CONFIG).read_bytes())
    require(c['schema']=='cdr-current-access-geometry-inputs-v1'and c['branch']==BRANCH and c['case']=='nominal_late','collector identity')
    require(c['source_controls_authorized']is True and type(c['readback_authorized'])is bool,'typed authority')
    require(c['all_acceptance_false']is True and c['native_simulation']is False,'collector scope')
    prior=q.source_guard(root)
    require(q.fingerprint(q.regular(root,q.CONFIG).read_bytes())['sha256']==c['qualified_case_reader']['sha256'],'qualified reader config')
    require(prior['producer']==c['original_producer'],'same original producer')
    return c

def checkout_binding(ctx,c,root=ROOT):
    require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()==ctx['source'],'exact current checkout')
    raw=q.regular(root,MANIFEST).read_bytes()
    require(raw==subprocess.check_output(['git','show',ctx['source']+':'+MANIFEST],cwd=root),'manifest changed')
    m=q.decode(raw);require(m['schema']=='cdr-current-access-geometry-source-pins-v1','manifest schema')
    for path,pin in m['files'].items():require(q.file_pin(q.regular(root,path))==pin,'source changed: '+path)
    require(m['readback_authorized']is c['readback_authorized'],'authority consistent')

    return dict(manifest=q.fingerprint(raw),files=m['files'],source=ctx['source'])

def controls_binding(raw,ctx):
    r=q.decode(raw)
    require(r['status']=='PASS_CDR_CURRENT_ACCESS_GEOMETRY_SOURCE_CONTROLS'and r['passed']is True,'source controls status')
    require(r['current_context']==dict(source=ctx['source'],run_id=ctx['run_id'],attempt=1),'same-source controls')
    require(r['actual_native_acquired']is False and r['physical_acceptance']is False,'source control scope')
    require(r['inherited_counts']==dict(groups=10,refusals=86,lifecycle=4)and r['sampler_test_methods']==6,'qualified reader controls')
    require(r['access_test_methods']==12 and r['access_tests_successful']is True,'original RC controls')
    require(r['geometry_test_methods']==7 and r['geometry_tests_successful']is True,'new geometry controls')
    require(r['native_fixtures']['status']=='PASS_CURRENT_ACCESS_GEOMETRY_NATIVE_FIXTURES'and r['native_fixtures']['counts']==dict(point=5,ownership=6,units=5,full_contract=10),'actual pinned synthetic native fixtures')
    require(r['native_fixtures']['actual_geometry_acquired']is False,'fixtures are not native input evidence')
    return q.fingerprint(raw)



def perform(ctx,reserved,controls_raw,out,c,root=ROOT,api_call=q.api,fetch=q.download):
    require(c['readback_authorized']is True,'readback disabled')
    binding=checkout_binding(ctx,c,root);controls=controls_binding(controls_raw,ctx)
    q.write_new(out/'current-source-binding.json',encode(binding));q.write_new(out/'source-controls.json',controls_raw)
    tag='cloud-results-'+ctx['token']+'-'+ctx['group']
    fresh=q.reservation(ctx,reserved,api_call('releases/tags/'+tag),api_call('git/ref/tags/'+tag))
    q.write_new(out/'reservation.json',encode(fresh))
    prior=q.source_guard(root);case=c['case'];e=prior['cases'][case]
    def live(suffix):
        run=api_call('actions/runs/'+str(prior['producer']['run_id']))
        jobs=api_call('actions/runs/'+str(prior['producer']['run_id'])+'/attempts/1/jobs?per_page=100')
        release=api_call('releases/'+str(e['release_id']));ref=api_call('git/ref/tags/'+e['tag'])
        for name,obj in (('run',run),('jobs',jobs),('release',release),('ref',ref)):q.write_new(out/('producer-'+name+suffix+'.json'),encode(obj))
        result=q.validate_current_case_live(prior,case,run,jobs,release,ref)
        q.write_new(out/('live-binding'+suffix+'.json'),encode(result));return result
    producer=live('');summary,parts,report=q.metadata(prior,case,root)
    require(all(summary['outputs'].get(k)==v for k,v in c['selected'].items()),'selected current model inventory')
    require(not any('wave.raw'in k or k.endswith('.gz')for k in c['selected']),'no waveform selection')
    for suffix,key in (('summary','summary_path'),('parts','parts_path'),('native-result','report_path'),('original-publication','publication_path')):q.write_new(out/('producer-'+suffix+'.json'),q.pinned(prior,root,e[key]))
    require(len(summary['outputs'])==c['expected_native_member_count'],'complete original input census')
    require(shutil.disk_usage(out.parent).free>=parts['bytes']+2*1024**3,'runner space')
    primary=None;temp=tempfile.TemporaryDirectory(prefix='cdr-access-rc-',dir=out.parent)
    try:
        work=Path(temp.name);archive,transport=q.acquire(prior,case,parts,work,fetch)
        q.write_new(out/'transport-proof.json',encode(transport))
        full=q.select_archive(archive,summary['outputs'],list(c['selected']),parts['source_directory'],work/'selected')
        q.write_new(out/'complete-input-census.json',encode(full));saved=work/'selected'
        require(q.regular(saved,e['report_member']).read_bytes()==q.pinned(prior,root,e['report_path']),'actual archived native report')
        require(q.file_pin(q.regular(saved,'result.json'))=={k:summary['raw_terminal'][k]for k in ('bytes','sha256')},'original raw outer result')
        require(all(full['selected'][n]['bytes']==c['selected_bytes'][n]for n in c['selected']),'actual selected sizes')
        native=run_native(saved,out/'native-inspection',c,root)
        result=q.decode(q.regular(out/'native-inspection'/'result','geometry-observation.json').read_bytes())
        require(result['status']=='PASS_CURRENT_ACCESS_GEOMETRIC_OBSERVATION_NOT_EDGE_ATTRIBUTION','complete ownership inspection')
        require(set(result['targets'])==set(c['targets']),'all four actual target nets')
        for name in c['selected']:require(q.file_pin(q.regular(saved,name))==full['selected'][name],'selected bytes changed')
        live('-after');source_guard(root);checkout_binding(ctx,c,root)
        return dict(status='PASS_AUTHENTIC_CURRENT_FOUR_NET_GEOMETRY_READBACK_ONLY',context=ctx,producer=producer,controls=controls,complete_input_members=full['full_member_count'],selected_members=len(full['selected']),native_counts=result['native_counts'],target_nets=len(result['targets']),original_electrical_status=report['status'],original_rejection_preserved=True,native_lifecycle=native,**FLAGS)

    except BaseException as error:primary=error;raise
    finally:
        try:temp.cleanup()
        except BaseException as error:
            q.preserve_error(out,'cleanup-error.json',error,primary)
            if primary is None:raise

def run(ctx,reserved,controls_raw,out,root=ROOT,api_call=q.api,fetch=q.download):
    require(not out.exists()and not out.is_symlink(),'output no overwrite');out.mkdir(parents=True);primary=None
    try:
        c=source_guard(root);result=perform(ctx,reserved,controls_raw,out,c,root,api_call,fetch)
        q.write_new(out/'readback-result.json',encode(result));return result
    except BaseException as error:
        primary=error
        failure=dict(status='FAIL_CURRENT_FOUR_NET_GEOMETRY_READBACK',context=ctx,error=repr(error),traceback=traceback.format_exc(),**FLAGS)
        try:q.write_new(out/'readback-failure.json',encode(failure))
        except BaseException as secondary:print(encode(dict(failure,save_error=repr(secondary))).decode(),flush=True)
        for name in (CONFIG,MANIFEST,'scripts/cloud_cdr_current_access_geometry.py','scripts/cdr_current_access_geometry_native.py'):
            try:q.write_new(out/('retained-source/'+name),q.regular(root,name).read_bytes())
            except BaseException as secondary:q.preserve_error(out,'retain-'+Path(name).name+'.error.json',secondary,error)
        raise
    finally:
        try:q.emit(out)
        except BaseException as error:
            q.preserve_error(out,'emission-error.json',error,primary)
            if primary is None:raise


pin=q.file_pin
decode=q.decode
def native_rows(text):
    return [dict(line=i,raw=line,tokens=__import__('shlex').split(line))for i,line in enumerate(text.splitlines(),1)if line.strip()]
frozen=types.SimpleNamespace(regular=q.regular,native_rows=native_rows)

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

def run_native(selected,out,c,root=ROOT,controls_only=False):
    ctx=context(os.environ);gate=lambda:checkout_binding(ctx,c,root)
    require(controls_only or c['readback_authorized']is True,'native readback disabled')
    out.mkdir(parents=True,exist_ok=False)
    policy=q.decode(q.regular(root,'current-cdr-runtime-policy.json').read_bytes())
    require(policy['source']==ctx['source']and policy['run_id']==ctx['run_id']and policy['attempt']==1,'same-source tool runtime policy')
    app=Path(policy['appimage'])
    require(app.is_absolute()and q.file_pin(app)['sha256']==c['appimage']['sha256']==policy['appimage_sha256'],'exact pinned AppImage')
    require(policy['loaded']is True and policy['global_policy_changed']is False and policy['restriction_before']==policy['restriction_after'],'scoped unchanged namespace policy')
    q.write_new(out/'runtime-policy.json',q.regular(root,'current-cdr-runtime-policy.json').read_bytes())
    launcher=runtime.launcher(root,gate,'501d4846603abd42b9efeaf515a5ad45f136d58997e37b16329003623b9f33ac')
    supervisor=None;heartbeat=None;previous={};primary=None;errors=[];actions=[];commands=[]
    try:
        with tokenless():smoke=launcher.probe(app,c['appimage']['sha256'],out/'runtime-smoke')
        require(smoke['accepted']is True,'pinned runtime import')
        supervisor=runtime.supervisor(root,out,out/'supervision',gate,runtime.SAMPLER_SHA);supervisor.TRACE.mkdir()
        for sig in(signal.SIGINT,signal.SIGTERM):
            previous[sig]=signal.getsignal(sig);signal.signal(sig,supervisor.interrupted)
        heartbeat=threading.Thread(target=supervisor.heartbeat,daemon=True);heartbeat.start()
        argv=[str(app),'python',str(root/'scripts/cdr_current_access_geometry_native.py'),'--output',str(out/'result')]
        if controls_only:argv+=['--controls']
        else:argv+=['--selected',str(selected)]
        label='synthetic-geometry-fixtures'if controls_only else'readonly-current-geometry'
        failure=None
        try:
            with tokenless():supervisor.supervised(argv,label,seconds=1800,cwd=root)
        except BaseException as error:failure=error
        try:
            record=q.decode(q.regular(supervisor.TRACE,label+'.command.json').read_bytes());commands.append(record)
            require(record['argv']==argv and record['minimum_available_kib']==2097152 and record['maximum_group_rss_kib']==10485760,'exact command and resources')
            for stream in('stdout','stderr'):
                require(q.file_pin(q.regular(supervisor.TRACE,label+'.'+stream))==dict(bytes=record[stream+'_bytes'],sha256=record[stream+'_sha256']),'full command stream')
            require(record['returncode']==0 and record['supervision_failure']is None and not record['process_group_cleanup']['remaining_live'],'native command failed')
        except BaseException as error:
            if failure is None:failure=error
        if failure is not None:raise failure
        gate();require(q.file_pin(app)['sha256']==c['appimage']['sha256'],'tool runtime changed')
    except BaseException as error:primary=error
    finally:
        actions,cleanup=finish(supervisor,heartbeat,previous);errors+=cleanup
        evidence=dict(actions=actions,errors=[repr(e)for e in errors],primary_error=None if primary is None else repr(primary),commands=commands,controls_only=controls_only,**FLAGS)
        try:q.write_new(out/'native-lifecycle.json',encode(evidence))
        except BaseException as error:
            errors.append(error);print('UNSAVED_GEOMETRY_LIFECYCLE '+encode(evidence).decode(),flush=True)
    if primary is not None:raise primary
    if errors:raise errors[0]
    return evidence

def main():
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True);g.add_argument('--readback',action='store_true');g.add_argument('--native-controls',action='store_true');p.add_argument('--case',choices=['nominal_late']);p.add_argument('--output',type=Path,required=True);p.add_argument('--reservation',type=Path);p.add_argument('--controls-proof',type=Path);a=p.parse_args()
    if a.native_controls:
        c=source_guard();checkout_binding(context(os.environ),c);run_native(None,a.output,c,controls_only=True);return
    require(a.case=='nominal_late'and a.reservation is not None and a.controls_proof is not None,'all readback arguments')
    ctx=context(os.environ,a.case);run(ctx,q.decode(q.regular(a.reservation.parent,a.reservation.name).read_bytes()),q.regular(a.controls_proof.parent,a.controls_proof.name).read_bytes(),a.output)
if __name__=='__main__':main()
