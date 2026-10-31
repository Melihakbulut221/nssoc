#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Synthetic controls of separate current admission, full publication and failure retention."""
import ast,copy,json,os,tempfile,types,traceback,zlib,base64
from pathlib import Path
from unittest.mock import patch
import cdr_current_via2_m3_physical_admission as a
import cloud_cdr_current_via2_m3_physical as host
import check_cdr_current_via2_m3_access_candidate as original_controls
import check_cdr_current_via2_m3_physical_publication as publication_controls
ROOT=a.ROOT

def env(mode='candidate',job='candidate'):
    return dict(GITHUB_ACTIONS='true',RUNNER_ENVIRONMENT='github-hosted',RUNNER_OS='Linux',GITHUB_EVENT_NAME='workflow_dispatch',
      GITHUB_REPOSITORY=a.q.REPOSITORY,GITHUB_REF='refs/heads/'+a.BRANCH,GITHUB_WORKFLOW_REF=a.q.REPOSITORY+'/'+a.WORKFLOW+'@refs/heads/'+a.BRANCH,
      GITHUB_RUN_ATTEMPT='1',GITHUB_SHA='a'*40,GITHUB_RUN_ID='12345',APPROVED_SOURCE='a'*40,REQUESTED_MODE=mode,GITHUB_JOB=job)

def fixture_current(ctx):
    run=dict(id=ctx['run_id'],head_sha=ctx['source'],head_branch=a.BRANCH,run_attempt=1,event='workflow_dispatch',workflow_id=382556685,path=a.WORKFLOW,status='in_progress')
    jobs=[]
    for i,name in enumerate(('source-controls','preserve-job-log','candidate')):
        jobs.append(dict(id=i+10,run_id=ctx['run_id'],run_attempt=1,head_sha=ctx['source'],name=name,
          status='in_progress'if name=='candidate'else'completed',conclusion=None if name=='candidate'else'success',steps=[dict(conclusion='success')]))
    return run,dict(total_count=3,jobs=jobs)

def admission_controls(c,plan,geometry,prior):
    rows=[]
    def refused(name,call):
        try:call()
        except(AssertionError,ValueError,KeyError,TypeError):rows.append(name);return
        raise AssertionError('accepted negative admission: '+name)
    e=env();ctx=a.context(e);a.validate_config(c,plan,geometry,prior)
    for key,value in [('GITHUB_ACTIONS','false'),('RUNNER_ENVIRONMENT','self-hosted'),('RUNNER_OS','Windows'),('GITHUB_EVENT_NAME','push'),
      ('GITHUB_REPOSITORY','other/repo'),('GITHUB_REF','refs/heads/main'),('GITHUB_WORKFLOW_REF','other'),('GITHUB_RUN_ATTEMPT','2'),
      ('GITHUB_SHA','b'*40),('GITHUB_RUN_ID','0'),('APPROVED_SOURCE','b'*40),('REQUESTED_MODE','readback'),('GITHUB_JOB','prepare')]:
        bad={**e,key:value};refused('context_'+key,lambda:a.context(bad))
    enabled=copy.deepcopy(c);enabled.update(generation_authorized=True,physical_verification_authorized=True);a.authorize_native(ctx,enabled)
    disabled=copy.deepcopy(c);disabled.update(generation_authorized=False,physical_verification_authorized=False)
    refused('disabled_authority',lambda:a.authorize_native(ctx,disabled))
    refused('controls_job_cannot_generate',lambda:a.authorize_native(a.context(env('controls','source-controls')),enabled))
    for field,value in [('generation_authorized',1),('physical_verification_authorized',not c['generation_authorized']),('fresh_rc_authorized',True),
      ('electrical_simulation_authorized',True),('expected_native_member_count',2797),('workflow_id',1),('case','nominal_early'),
      ('candidate_source','b'*40),('candidate_control_run',1),('branch','main'),('native_payloads_cloud_only',False)]:
        bad=copy.deepcopy(c);bad[field]=value;refused('method_'+field,lambda:a.validate_config(bad,plan,geometry,prior))
    for label,change in [('missing_member',lambda x:x['selected'].pop(next(iter(x['selected'])))),
      ('changed_existing17',lambda x:x['selected'].__setitem__(next(iter(geometry['selected'])),'f'*64)),
      ('wrong_support',lambda x:x['support_members'].__setitem__('lef',x['support_members']['schematic'])),
      ('zero_size',lambda x:x['selected_bytes'].__setitem__(next(iter(x['selected'])),0)),
      ('weakened_physical',lambda x:x['full_physical'].__setitem__('categories',559))]:
        bad=copy.deepcopy(c);change(bad);refused(label,lambda:a.validate_config(bad,plan,geometry,prior))
    run,jobs=fixture_current(ctx);a.validate_current_run(ctx,run,jobs)
    for field,value in [('id',1),('head_sha','b'*40),('head_branch','main'),('run_attempt',2),('event','push'),('workflow_id',1),('path','wrong'),('status','completed')]:
        bad={**run,field:value};refused('actual_run_'+field,lambda:a.validate_current_run(ctx,bad,jobs))
    for label,change in [('missing_job',lambda x:x['jobs'].pop()),('old_job_source',lambda x:x['jobs'][0].__setitem__('head_sha','b'*40)),
      ('failed_controls',lambda x:x['jobs'][0].__setitem__('conclusion','failure')),('failed_log',lambda x:x['jobs'][1].__setitem__('conclusion','failure')),
      ('completed_candidate',lambda x:x['jobs'][2].__setitem__('status','completed')),('failed_step',lambda x:x['jobs'][0]['steps'][0].__setitem__('conclusion','failure'))]:
        bad=copy.deepcopy(jobs);change(bad);refused(label,lambda:a.validate_current_run(ctx,run,bad))
    tag='cloud-results-'+ctx['token']+'-'+ctx['group']
    proof=dict(tag=tag,tested_source=ctx['source'],release_id=900,target_verified=True,assets_overwritten=False,externally_reserved=True,creation_attempted=False,existing_assets=[])
    info=dict(id=900,tag_name=tag,target_commitish=ctx['source'],draft=False,prerelease=True,assets=[])
    ref=dict(ref='refs/tags/'+tag,object=dict(type='commit',sha=ctx['source']))
    a.q.reservation(ctx,proof,info,ref)
    for field,value in [('externally_reserved',False),('creation_attempted',True),('tested_source','b'*40),('existing_assets',[{}])]:
        bad={**proof,field:value};refused('reservation_'+field,lambda:a.q.reservation(ctx,bad,info,ref))
    bad=copy.deepcopy(info);bad['draft']=True;refused('draft_result',lambda:a.q.reservation(ctx,proof,bad,ref))
    # Authenticate real recorded producer JSON, while acquiring no native archive.
    prefix='docs/evidence/cdr-current-access-geometry-terminal-41230358164/readback/'
    producer=[a.q.decode(a.q.regular(ROOT,prefix+'producer-'+n+'.json').read_bytes())for n in('run','jobs','release','ref')]
    a.q.validate_current_case_live(prior,'nominal_late',*producer)
    changed=copy.deepcopy(producer);changed[0]['head_sha']='b'*40;refused('old_producer_source',lambda:a.q.validate_current_case_live(prior,'nominal_late',*changed))
    changed=copy.deepcopy(producer);changed[2]['assets'].pop();refused('incomplete_original_publication',lambda:a.q.validate_current_case_live(prior,'nominal_late',*changed))
    changed=copy.deepcopy(producer);changed[3]['object']['sha']='b'*40;refused('wrong_original_tag',lambda:a.q.validate_current_case_live(prior,'nominal_late',*changed))
    a.require(len(rows)>=40,'meaningful admission refusal census')
    return dict(refusals=rows,actual_producer_metadata_revalidated=True,producer_native_acquired=False)

def native_preflight_controls(c,prior):
    ctx=a.context(env());changed=copy.deepcopy(c);changed.update(generation_authorized=True,physical_verification_authorized=True)
    prefix='docs/evidence/cdr-current-access-geometry-terminal-41230358164/readback/'
    producer=[a.q.decode(a.q.regular(ROOT,prefix+'producer-'+n+'.json').read_bytes())for n in('run','jobs','release','ref')]
    rows=[]
    with tempfile.TemporaryDirectory()as temp:
        root=Path(temp);selected=root/'inputs';selected.mkdir();pins={}
        for name in changed['selected']:
            p=selected/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(('EXPLICIT_SYNTHETIC_INPUT '+name+'\n').encode());pins[name]=a.q.file_pin(p)
        changed['selected']={n:p['sha256']for n,p in pins.items()};changed['selected_bytes']={n:p['bytes']for n,p in pins.items()}
        controls=dict(status='PASS_CURRENT_VIA2_M3_PHYSICAL_ADAPTER_SOURCE_CONTROLS',passed=True,context=dict(source=ctx['source'],run_id=ctx['run_id'],attempt=1),
          original_geometry_controls=dict(cases=30,positive=9,refusals=21),native_payload_acquired=False,actual_candidate_generated=False,
          admission_refusals=40,native_preflight_refusals=7,lifecycle_cases=4,publication_cases=7,publication_refusals=33)
        raw=a.encode(controls);(root/'same-source-controls.json').write_bytes(raw)
        run,jobs=fixture_current(ctx);current=a.validate_current_run(ctx,run,jobs)
        def write(name,value):(root/name).write_bytes(a.encode(value))
        write('current-run.json',run);write('current-jobs.json',jobs)
        for name,value in zip(('run','jobs','release','ref'),producer):write('producer-'+name+'.json',value)
        producer_binding=a.q.validate_current_case_live(prior,'nominal_late',*producer)
        tag='cloud-results-'+ctx['token']+'-'+ctx['group'];reserved=dict(tag=tag,tested_source=ctx['source'],release_id=900,target_verified=True,assets_overwritten=False,externally_reserved=True,creation_attempted=False,existing_assets=[])
        info=dict(id=900,tag_name=tag,target_commitish=ctx['source'],draft=False,prerelease=True,assets=[]);ref=dict(ref='refs/tags/'+tag,object=dict(type='commit',sha=ctx['source']))
        write('reservation-original.json',reserved);write('result-release-empty.json',info);write('result-tag.json',ref)
        p=dict(context=ctx,generation_authorized=True,physical_verification_authorized=True,all2991_authenticated=True,selected=pins,selected_root=str(selected.resolve()),
          controls=a.bind_controls(raw,ctx),current_run_binding=current,producer_binding=producer_binding,reservation_binding=a.q.reservation(ctx,reserved,info,ref))
        write('preflight.json',p);a.native_preflight(root/'preflight.json',ctx,changed,selected)
        def reject(name,change,restore):
            change()
            try:a.native_preflight(root/'preflight.json',ctx,changed,selected)
            except(AssertionError,KeyError,ValueError,TypeError):rows.append(name)
            else:raise AssertionError('Accepted false integrated native preflight '+name)
            finally:restore()
        bad=copy.deepcopy(p);bad['context']['source']='b'*40
        reject('wrong_preflight_source',lambda:write('preflight.json',bad),lambda:write('preflight.json',p))
        bad=copy.deepcopy(p);bad['all2991_authenticated']=False
        reject('incomplete_archive',lambda:write('preflight.json',bad),lambda:write('preflight.json',p))
        bad=copy.deepcopy(p);bad['selected_root']=str(root/'other')
        reject('other_selected_root',lambda:write('preflight.json',bad),lambda:write('preflight.json',p))
        first=next(iter(pins));path=selected/first;original=path.read_bytes()
        reject('changed_selected_native_bytes',lambda:path.write_bytes(b'changed'),lambda:path.write_bytes(original))
        bad={**run,'head_sha':'b'*40}
        reject('changed_actual_current_run',lambda:write('current-run.json',bad),lambda:write('current-run.json',run))
        bad={**producer[0],'head_sha':'b'*40}
        reject('changed_original_producer',lambda:write('producer-run.json',bad),lambda:write('producer-run.json',producer[0]))
        bad={**reserved,'externally_reserved':False}
        reject('not_independently_reserved',lambda:write('reservation-original.json',bad),lambda:write('reservation-original.json',reserved))
        a.native_preflight(root/'preflight.json',ctx,changed,selected)
    return dict(positive=1,refusals=rows,all_twenty_input_bytes_explicitly_synthetic=True,actual_native_archive_acquired=False)


def source_log_controls(c):
    receipt_path=ROOT/c['prior_adapter_controls']['receipt'];historical=a.q.decode(receipt_path.read_bytes())
    ctx=dict(source=historical['source'],run_id=historical['run_id'],attempt=1)
    raw=(receipt_path.parent/'logs/124633648879.log').read_bytes()
    records,proof=a.authenticate_source_log(ctx,raw)
    a.require(proof['full_raw_log']==historical['records']['logs/124633648879.log'],'actual prior raw log full byte identity')
    a.require(all(a.q.fingerprint(b)==historical['records']['readback/'+n]for n,b in records.items()),'actual four decoded records unchanged')
    synthetic=copy.deepcopy(records);rows=[]
    def emit(values):
        lines=[]
        for name,b in values.items():
            index=dict(path=name,bytes=len(b),sha256=a.q.fingerprint(b)['sha256'],chunks=1)
            lines+=['VIA2_M3_ADAPTER_CONTROL_INDEX '+json.dumps(index),'VIA2_M3_ADAPTER_CONTROL_CHUNK '+json.dumps(dict(path=name,index=0,base64=base64.b64encode(b).decode()))]
        return ('SYNTHETIC TRANSPORT FIXTURE\n'+'\n'.join(lines)+'\n').encode()
    sample=emit(synthetic);a.authenticate_source_log(ctx,sample)
    def rejected(name,fn):
        try:fn()
        except(AssertionError,KeyError,ValueError,TypeError):rows.append(name);return
        raise AssertionError('Accepted malformed source log '+name)
    lines=sample.splitlines();index=next(x for x in lines if b'CONTROL_INDEX 'in x);chunk=next(x for x in lines if b'CONTROL_CHUNK 'in x)
    rejected('duplicate_index',lambda:a.authenticate_source_log(ctx,sample+index+b'\n'))
    rejected('duplicate_chunk',lambda:a.authenticate_source_log(ctx,sample+chunk+b'\n'))
    rejected('missing_index',lambda:a.authenticate_source_log(ctx,b'\n'.join(x for x in lines if x!=index)))
    rejected('missing_chunk',lambda:a.authenticate_source_log(ctx,b'\n'.join(x for x in lines if x!=chunk)))
    rejected('unknown_record',lambda:a.authenticate_source_log(ctx,sample.replace(b'via2-m3-adapter-controls.stdout',b'foreign.json')))
    rejected('wrong_byte_count',lambda:a.authenticate_source_log(ctx,sample.replace(index,index.replace(b'"bytes": ',b'"bytes": 1'),1)))
    bad=json.loads(index.split(b'CONTROL_INDEX ',1)[1]);bad['sha256']='0'*64
    rejected('wrong_record_hash',lambda:a.authenticate_source_log(ctx,sample.replace(index,b'VIA2_M3_ADAPTER_CONTROL_INDEX '+json.dumps(bad).encode(),1)))
    bad_chunk=json.loads(chunk.split(b'CONTROL_CHUNK ',1)[1]);bad_chunk['base64']='!'
    rejected('nonbase64',lambda:a.authenticate_source_log(ctx,sample.replace(chunk,b'VIA2_M3_ADAPTER_CONTROL_CHUNK '+json.dumps(bad_chunk).encode(),1)))
    rejected('wrong_current_source',lambda:a.authenticate_source_log({**ctx,'source':'b'*40},sample))
    rejected('wrong_current_run',lambda:a.authenticate_source_log({**ctx,'run_id':ctx['run_id']+1},sample))
    name='cdr-via2-m3-adapter-controls/result.json';original=a.q.decode(synthetic[name])
    for key,value in(('passed',False),('native_payload_acquired',True),('actual_candidate_generated',True),('admission_refusals',39)):
        wrong={**synthetic,name:a.encode(dict(original,**{key:value}))}
        rejected('result_'+key,lambda:a.authenticate_source_log(ctx,emit(wrong)))
    policy=a.q.decode(synthetic['current-cdr-runtime-policy.json']);wrong={**synthetic,'current-cdr-runtime-policy.json':a.encode(dict(policy,run_id=ctx['run_id']+1))}
    rejected('policy_context',lambda:a.authenticate_source_log(ctx,emit(wrong)))
    with patch.object(a.subprocess,'check_output',return_value=b'unchanged\x1b[31mraw\x00')as call:
        got=a.read_source_log(123);a.require(got==b'unchanged\x1b[31mraw\x00'and call.call_args.args==(['gh','api','--allow-escape-sequences','repos/Melihakbulut221/nssoc/actions/jobs/123/logs'],),'full raw hosted source transport argv')
        for wrong in(0,-1,True,'123'):
            before=call.call_count;rejected('job_id_'+repr(wrong),lambda:a.read_source_log(wrong));a.require(call.call_count==before,'invalid job caused request')
    return dict(actual_prior_full_log=proof['full_raw_log'],decoded_prior_records=len(records),refusals=rows,synthetic_transport_only=True,native_payload_acquired=False)

def derivation_controls():
    def function(text,name):
        lines=text.splitlines(keepends=True);tree=ast.parse(text);nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name==name]
        a.require(len(nodes)==1,'unique reviewed function');n=nodes[0];return ''.join(lines[n.lineno-1:n.end_lineno]).rstrip()+'\n'
    native=(ROOT/'scripts/cdr_current_via2_m3_physical_native.py').read_text();original=(ROOT/'scripts/cdr_current_via2_m3_access_candidate.py').read_text()
    old=function(original,'generate_reviewed_candidate')
    before="def generate_reviewed_candidate(pya,selected,out,config,root=ROOT):\n    # This body is reviewable, but the source-only plan intentionally forbids entry.\n    plan=source_guard(root)\n    require(plan['candidate_generation_authorized']is True,'candidate generation is disabled pending execution adapter review')\n"
    after="def generate_current_candidate(pya,selected,out,config,preflight,root=ROOT):\n    ctx=a.context(os.environ);method=a.source_guard(ctx,root)\n    a.native_preflight(preflight,ctx,method,selected,root)\n    plan=json.loads(a.q.regular(root,method['candidate_plan']).read_bytes())\n    original.validate_plan(plan)\n"
    a.require(old.count(before)==1 and function(native,'generate_current_candidate')==old.replace(before,after),'only explicit independent entry changed; generation body exact')
    oldhost=(ROOT/'scripts/cloud_cdr_drain_m1_width_trial.py').read_text();newhost=(ROOT/'scripts/cloud_cdr_current_via2_m3_physical.py').read_text()
    for name in('derive_physical','validate_physical'):a.require(function(oldhost,name)==function(newhost,name),'unchanged full physical method '+name)
    oldpub=(ROOT/'scripts/publish_cdr_current_access_geometry.py').read_text();newpub=(ROOT/'scripts/publish_cdr_current_via2_m3_physical.py').read_text()
    for name in('inventory','prepare','validate_release','upload','publish'):a.require(function(oldpub,name)==function(newpub,name),'unchanged complete publisher '+name)
    return dict(explicit_entry_only=True,shared_original_geometry_helpers=True,full560_500_13_physical_methods_exact=True,complete_publication_methods_exact=True)

def lifecycle_controls():
    cases=[];ctx=a.context(env())
    with tempfile.TemporaryDirectory()as t:
        root=Path(t);primary=ValueError('synthetic native primary');secondary=OSError('synthetic emitter secondary')
        def failbody(ctx,c,r,controls,out):
            (out/'candidate.gds').write_bytes(b'EXPLICIT_SYNTHETIC_NATIVE_BYTES');raise primary
        def failemit(out):raise secondary
        try:host.run(ctx,{}, {},b'',root/'failure',body=failbody,emitter=failemit)
        except ValueError as e:a.require(e is primary,'primary replaced')
        else:raise AssertionError('native failure became pass')
        a.require((root/'failure'/'candidate.gds').read_bytes()==b'EXPLICIT_SYNTHETIC_NATIVE_BYTES'and(root/'failure'/'failure.json').is_file()and(root/'failure'/'derived-emission-error.json').is_file(),'full available failure bytes')
        cases.append('body_primary_and_emission_secondary_preserved')
        def success(*args):return dict(status='EXPLICIT_SYNTHETIC_ONLY')
        try:host.run(ctx,{}, {},b'',root/'emission',body=success,emitter=failemit)
        except OSError as e:a.require(e is secondary,'sole emission primary changed')
        else:raise AssertionError('failed emission became pass')
        cases.append('sole_emission_error_preserved')
        emitted=[];r=host.emit_derived(root/'failure',lambda s,**kw:emitted.append(s))
        a.require('candidate.gds'in r['complete_inventory']and'candidate.gds'not in r['emitted_derived'],'native only external complete inventory')
        a.require(not any('CHUNK 'in s and json.loads(s.split('CHUNK ',1)[1])['name']=='candidate.gds'for s in emitted),'native payload logged')
        a.require('failure.json'in r['emitted_derived'],'derived failure not emitted');cases.append('complete_native_inventory_but_text_only_emission')
        seen=[]
        class Supervisor:
            ACTIVE=None
            STOP=types.SimpleNamespace(set=lambda:seen.append('stop'))
            def stop_process(self,p):seen.append('cleanup');raise primary
        heartbeat=types.SimpleNamespace(join=lambda timeout:seen.append('join'),is_alive=lambda:False)
        actions,errors=host.finish(Supervisor(),heartbeat,{})
        a.require(seen==['cleanup','stop','join']and errors==[primary]and len(actions)==3,'cleanup isolation and complete lifecycle')
        cases.append('cleanup_failure_does_not_skip_stop_or_join')
    return cases

def main():
    ctx=a.context(os.environ);c=a.source_guard(ctx);out=Path('cdr-via2-m3-adapter-controls');out.mkdir(exist_ok=False)
    try:
        import pya
        plan=a.q.decode(a.q.regular(ROOT,c['candidate_plan']).read_bytes());geometry=a.q.decode(a.q.regular(ROOT,c['geometry_config']).read_bytes());prior=a.q.source_guard()
        original=original_controls.controls(pya,plan);admission=admission_controls(c,plan,geometry,prior);native_admission=native_preflight_controls(c,prior);source_log=source_log_controls(c);derivation=derivation_controls();lifecycle=lifecycle_controls()
        pubctx=publication_controls.p.context(os.environ,'nominal_late');pub=publication_controls.controls(pubctx)
        a.require(pub['counts']==dict(positive=7,refusals=33,lifecycle=4),'complete publication controls')
        counts=dict(cases=len(original['cases']),positive=sum(r.get('passed')is True for r in original['cases']),refusals=sum(r.get('rejected')is True for r in original['cases']))
        result=dict(status='PASS_CURRENT_VIA2_M3_PHYSICAL_ADAPTER_SOURCE_CONTROLS',passed=True,context=dict(source=ctx['source'],run_id=ctx['run_id'],attempt=1),
          original_geometry_controls=counts,admission_refusals=len(admission['refusals']),native_preflight_refusals=len(native_admission['refusals']),lifecycle_cases=len(lifecycle),publication_cases=7,publication_refusals=33,
          original=original,admission=admission,native_admission=native_admission,source_log=source_log,source_log_refusals=len(source_log['refusals']),derivation=derivation,lifecycle=lifecycle,publication=pub,native_payload_acquired=False,actual_candidate_generated=False,**a.FLAGS)
        a.bind_controls(a.encode(result),ctx);a.source_guard(ctx)
        (out/'result.json').write_bytes(a.encode(result));print('VIA2_M3_ADAPTER_CONTROLS '+a.encode(result).decode(),flush=True)
    except BaseException as error:
        result=dict(status='FAIL_CURRENT_VIA2_M3_PHYSICAL_ADAPTER_SOURCE_CONTROLS',passed=False,error=repr(error),traceback=traceback.format_exc(),native_payload_acquired=False,**a.FLAGS)
        (out/'failure.json').write_bytes(a.encode(result));raise
if __name__=='__main__':main()
