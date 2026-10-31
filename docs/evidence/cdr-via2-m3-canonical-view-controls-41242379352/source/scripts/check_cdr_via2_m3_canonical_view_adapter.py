#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted source controls; actual project/native archives are never acquired."""
import ast,base64,copy,json,os,tempfile,types,traceback
from pathlib import Path
from unittest.mock import patch
import cdr_via2_m3_canonical_view_admission as a
import cloud_cdr_via2_m3_canonical_view as host
import check_cdr_via2_m3_canonical_view_publication as publication_controls
import check_cdr_via2_m3_canonical_core as core_controls
import check_cdr_via2_m3_canonical_view as seam_controls
ROOT=a.ROOT
def env(mode='view',job='canonical-view'):
    return dict(GITHUB_ACTIONS='true',RUNNER_ENVIRONMENT='github-hosted',RUNNER_OS='Linux',GITHUB_EVENT_NAME='workflow_dispatch',
      GITHUB_REPOSITORY=a.q.REPOSITORY,GITHUB_REF='refs/heads/'+a.BRANCH,GITHUB_WORKFLOW_REF=a.q.REPOSITORY+'/'+a.WORKFLOW+'@refs/heads/'+a.BRANCH,
      GITHUB_RUN_ATTEMPT='1',GITHUB_SHA='a'*40,GITHUB_RUN_ID='12345',APPROVED_SOURCE='a'*40,REQUESTED_MODE=mode,GITHUB_JOB=job)

def reject(fn):
    try:fn()
    except(AssertionError,ValueError,FileNotFoundError,KeyError):return True
    raise AssertionError('Invalid fixture accepted')

def producer_controls(c):
    faults=[]
    for key,p in c['producers'].items():
        prefix=p['proof_prefix'];values=[a.q.decode(a.q.regular(ROOT,prefix+n+'.json').read_bytes())for n in('run','jobs','release','tag-ref')]
        a.validate_producer(c,key,*values)
        for label,index,mutate in[
          ('run-source',0,lambda x:x.update(head_sha='1'*40)),('run-failure',0,lambda x:x.update(conclusion='failure')),
          ('run-not-terminal',0,lambda x:x.update(status='in_progress')),('run-retry',0,lambda x:x.update(run_attempt=2)),
          ('missing-job',1,lambda x:x['jobs'].pop()),('altered-job-source',1,lambda x:x['jobs'][0].update(head_sha='2'*40)),
          ('altered-job-conclusion',1,lambda x:x['jobs'][0].update(conclusion='failure')),
          ('altered-step',1,lambda x:x['jobs'][0]['steps'][0].update(name='different exact step')),
          ('release-source',2,lambda x:x.update(target_commitish='3'*40)),('release-draft',2,lambda x:x.update(draft=True)),
          ('release-extra',2,lambda x:x['assets'].append(dict(x['assets'][0],id=123456789,name='unexpected'))),
          ('release-asset-bytes',2,lambda x:x['assets'][0].update(size=x['assets'][0]['size']+1)),
          ('release-asset-digest',2,lambda x:x['assets'][0].update(digest='sha256:'+'0'*64)),
          ('tag-source',3,lambda x:x['object'].update(sha='4'*40)),('tag-object',3,lambda x:x['object'].update(type='tag'))]:
            bad=copy.deepcopy(values);mutate(bad[index]);reject(lambda:a.validate_producer(c,key,*bad));faults.append(key+':'+label)
    return faults

def restore_controls(c):
    faults=[]
    with tempfile.TemporaryDirectory(prefix='explicit-synthetic-two-archive-inputs-')as temporary:
        root=Path(temporary).resolve()
        for key in('reference','physical'):
            restore=root/key;restore.mkdir();config=copy.deepcopy(c);index,_=a.metadata(c,key)
            # No native input: placeholders except already-published derived JSON.
            for name in index['files']:
                p=restore/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(('EXPLICIT_SYNTHETIC_NOT_NATIVE '+name+'\n').encode())
            if key=='physical':
                prefix=c['producers']['physical']['proof_prefix']
                for name in('native/layout/result.json','native/physical/result.json'):
                    (restore/name).write_bytes(a.q.regular(ROOT,prefix+'readback/'+name).read_bytes())
                config['candidate']=a.q.file_pin(restore/'native/layout/nssoc_cdr_pd500_resistor_v59.gds')
            files={n:a.q.file_pin(restore/n)for n in index['files']}
            full=dict(every_member_authenticated=True,full_member_count=len(files),full_members=files,selected=copy.deepcopy(files))
            def call(full_record=full):
                with patch.object(a,'metadata',return_value=(dict(files=files),{})):
                    return a.validate_restored(config,key,restore,full_record)
            positive=call();a.require(positive['all_members_authenticated']is True,'real complete-byte validator on explicit fixture')
            for label,change in(('census',lambda d:d.update(full_member_count=len(files)-1)),('unverified',lambda d:d.update(every_member_authenticated=False)),('partial-map',lambda d:d['full_members'].pop(next(iter(d['full_members'])))),('partial-selection',lambda d:d['selected'].pop(next(iter(d['selected']))))):
                bad=copy.deepcopy(full);change(bad);reject(lambda:call(bad));faults.append(key+':'+label)
            first=next(iter(files));path=restore/first;saved=path.read_bytes();path.write_bytes(saved+b'CORRUPTION');reject(call);path.write_bytes(saved);faults.append(key+':changed-retained-byte')
            if key=='physical':
                report_path=restore/'native/physical/result.json';saved=report_path.read_bytes()
                for label,mutate in(('DRC-marker',lambda r:r['steps']['drc']['measurement'].update(markers=1)),('LVS-device',lambda r:r['steps']['lvs']['native_primitive_census'].update(npn13g2=123)),('fault-accepted',lambda r:r['steps'][next(k for k in r['steps']if k not in('drc','lvs','lvs_flat'))].update(status='PASS'))):
                    bad=a.q.decode(saved);mutate(bad);report_path.write_bytes(a.encode(bad));files['native/physical/result.json']=a.q.file_pin(report_path);full['selected']=copy.deepcopy(files)
                    reject(call);faults.append('physical:'+label)
                report_path.write_bytes(saved);files['native/physical/result.json']=a.q.file_pin(report_path);full['selected']=copy.deepcopy(files)
                path=restore/'native/layout/result.json';saved=path.read_bytes();bad=a.q.decode(saved);n=next(iter(bad['inputs']));bad['inputs']['/rewritten/input']=bad['inputs'].pop(n);path.write_bytes(a.encode(bad));files['native/layout/result.json']=a.q.file_pin(path);full['selected']=copy.deepcopy(files)
                reject(call);faults.append('physical:original-absolute-input-rewritten');path.write_bytes(saved)
    return faults

def context_controls(c):
    value=env();ctx=a.context(value);faults=[]
    for key,bad in [('GITHUB_SHA','bad'),('APPROVED_SOURCE','b'*40),('GITHUB_RUN_ATTEMPT','2'),('GITHUB_REF','refs/heads/main'),('GITHUB_JOB','candidate'),('GITHUB_EVENT_NAME','push'),('GITHUB_REPOSITORY','other/repo'),('RUNNER_ENVIRONMENT','self-hosted')]:
        modified=dict(value);modified[key]=bad;reject(lambda:a.context(modified));faults.append(key)
    disabled=copy.deepcopy(c);disabled['view_execution_authorized']=False
    reject(lambda:a.authorize_native(ctx,disabled));faults.append('explicit-disabled-authority')
    authorized=copy.deepcopy(c);authorized['view_execution_authorized']=True;a.authorize_native(ctx,authorized)
    actual_source_context=a.context(os.environ)
    a.require(actual_source_context['job']=='source-controls','actual source-control job identity')
    reject(lambda:a.authorize_native(actual_source_context,authorized));faults.append('actual-source-job-refused-with-enabled-config')
    for key in('generation_authorized','fresh_rc_authorized','electrical_simulation_authorized'):
        bad=copy.deepcopy(authorized);bad[key]=True;reject(lambda:a.authorize_native(ctx,bad));faults.append(key)
    return faults

def current_run_controls():
    ctx=a.context(env());source=dict(id=11,run_id=ctx['run_id'],run_attempt=1,head_sha=ctx['source'],name='source-controls',status='completed',conclusion='success',steps=[dict(name='synthetic controls',conclusion='success')])
    rows=[source,dict(source,id=12,name='preserve-job-log'),dict(source,id=13,name='canonical-view',status='in_progress',conclusion=None,steps=[])]
    jobs=dict(total_count=3,jobs=rows);run=dict(id=ctx['run_id'],head_sha=ctx['source'],head_branch=a.BRANCH,run_attempt=1,event='workflow_dispatch',workflow_id=382556685,path=a.WORKFLOW,status='in_progress')
    a.validate_current_run(ctx,run,jobs);faults=[]
    for label,target,mutate in [('run-source',0,lambda d:d.update(head_sha='b'*40)),('run-branch',0,lambda d:d.update(head_branch='main')),('run-retry',0,lambda d:d.update(run_attempt=2)),('run-event',0,lambda d:d.update(event='push')),('run-workflow',0,lambda d:d.update(workflow_id=1)),('run-terminal',0,lambda d:d.update(status='completed')),('jobs-partial',1,lambda d:d['jobs'].pop()),('job-source',1,lambda d:d['jobs'][0].update(head_sha='b'*40)),('source-failed',1,lambda d:d['jobs'][0].update(conclusion='failure')),('source-step-failed',1,lambda d:d['jobs'][0]['steps'][0].update(conclusion='failure')),('log-pending',1,lambda d:d['jobs'][1].update(status='in_progress')),('native-already-complete',1,lambda d:d['jobs'][2].update(status='completed')),('duplicate-name',1,lambda d:d['jobs'][2].update(name='source-controls'))]:
        values=copy.deepcopy([run,jobs]);mutate(values[target]);reject(lambda:a.validate_current_run(ctx,*values));faults.append(label)
    return faults

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

def frozen_methods():
    def function(text,name):
        lines=text.splitlines(keepends=True);nodes=[n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)and n.name==name]
        a.require(len(nodes)==1,'unique frozen function');n=nodes[0];return ''.join(lines[n.lineno-1:n.end_lineno]).rstrip()+'\n'
    old=(ROOT/'scripts/cloud_cdr_via2_m3_physical_recheck.py').read_text();new=(ROOT/'scripts/cloud_cdr_via2_m3_canonical_view.py').read_text()
    for name in('finish','tokenless'):a.require(function(old,name)==function(new,name),'frozen lifecycle '+name)
    oldpub=(ROOT/'scripts/publish_cdr_via2_m3_physical_recheck.py').read_text();newpub=(ROOT/'scripts/publish_cdr_via2_m3_canonical_view.py').read_text()
    for name in('inventory','prepare','validate_release','upload','publish'):a.require(function(oldpub,name)==function(newpub,name),'frozen publisher '+name)
    a.require('exact16-via2-m3-generation'not in new and 'fresh-current500-wire-RC'not in new,'no geometry/RC invocation')
    return dict(frozen_lifecycle_methods=2,frozen_publication_methods=5,geometry_regenerated=False,RC_executed=False)

def transport_controls(ctx,result):
    key='canonical-view-controls/result.json';records={'canonical-view-controls.stdout':b'','canonical-view-controls.stderr':b'',key:a.encode(result)}
    def log_bytes(values):
        lines=['EXPLICIT_SYNTHETIC_LOG_TRANSPORT_FIXTURE']
        for name,raw in values.items():
            pin=a.q.fingerprint(raw);lines.append('VIA2_M3_VIEW_CONTROL_INDEX '+json.dumps(dict(path=name,**pin,chunks=1)))
            lines.append('VIA2_M3_VIEW_CONTROL_CHUNK '+json.dumps(dict(path=name,index=0,base64=base64.b64encode(raw).decode())))
        return ('\n'.join(lines)+'\n').encode()
    log=log_bytes(records);observed,proof=a.authenticate_source_log(ctx,log)
    a.require(observed==records and proof['full_raw_log']==a.q.fingerprint(log),'complete exact three-record transport')
    refusals=[];lines=log.decode().splitlines()
    for label,modified in [('missing-index','\n'.join(x for x in lines if not(x.startswith('VIA2_M3_VIEW_CONTROL_INDEX ')and 'canonical-view-controls.stdout'in x)).encode()),('missing-chunk','\n'.join(x for x in lines if not(x.startswith('VIA2_M3_VIEW_CONTROL_CHUNK ')and 'canonical-view-controls.stdout'in x)).encode()),('duplicate-index',log+(lines[1]+'\n').encode()),('duplicate-chunk',log+(lines[2]+'\n').encode()),('bad-base64',log.replace(b'"base64": ""',b'"base64": "%"',1)),('extra-path',log.replace(b'canonical-view-controls.stdout',b'unexpected-path',1))]:
        reject(lambda:a.authenticate_source_log(ctx,modified));refusals.append(label)
    for label,mutate in [('wrong-source',lambda r:r['context'].update(source='1'*40)),('wrong-run',lambda r:r['context'].update(run_id=2)),('bad-result',lambda r:r.update(passed=False)),('missing-refusals',lambda r:r.update(restore_refusals=0)),('native-claimed',lambda r:r.update(actual_view_executed=True)),('core-not-passed',lambda r:r.update(core_controls_passed=False)),('seam-incomplete',lambda r:r.update(seam_test_count=0)),('simulation-claimed',lambda r:r.update(simulation_executed=True))]:
        bad=copy.deepcopy(result);mutate(bad);values=dict(records);values[key]=a.encode(bad);reject(lambda:a.authenticate_source_log(ctx,log_bytes(values)));refusals.append(label)
    with patch.object(a.subprocess,'check_output',return_value=b'\x1b[31mRAW\x00BYTES')as execute:
        a.require(a.read_source_log(123)==b'\x1b[31mRAW\x00BYTES','escape bytes unchanged')
        execute.assert_called_once_with(['gh','api','--allow-escape-sequences','repos/'+a.q.REPOSITORY+'/actions/jobs/123/logs'])
    return refusals

def main():
    ctx=a.context(os.environ);method=a.source_guard(ctx);out=ROOT/'canonical-view-controls';a.require(not out.exists(),'new source controls output');out.mkdir();primary=None
    try:
        a.require(ctx['job']=='source-controls','source controls only')
        p=producer_controls(method);r=restore_controls(method);e=context_controls(method);j=current_run_controls();f=frozen_methods();l=lifecycle_controls()
        pub=publication_controls.controls(dict(source=ctx['source'],run_id=ctx['run_id'],attempt=1));a.require(pub['passed']is True,'complete publisher controls')
        core_config=a.q.decode(a.q.regular(ROOT,method['core']['config_path']).read_bytes())
        core_controls.RECORDS.clear();core_controls.source_definition_controls(core_config);core_controls.count_controls();core_controls.material_controls(core_config);core_controls.scope_controls(core_config);core_controls.incremental_preservation_controls(core_config)
        core_records={str(p.relative_to(ROOT)):a.q.file_pin(p)for p in sorted(core_controls.RESULT.rglob('*'))if p.is_file()}
        a.require(len(core_controls.RECORDS)==59 and len(core_records)==15,'all original core59 and actual15 synthetic evidence files')
        seam=seam_controls.controls(a.q.decode(a.q.regular(ROOT,'scripts/cdr-via2-m3-canonical-view-inputs.json').read_bytes()))
        result=dict(status='PASS_CANONICAL_VIEW_ADAPTER_SOURCE_CONTROLS',passed=True,context=dict(source=ctx['source'],run_id=ctx['run_id'],attempt=1),producer_refusals=len(p),restore_refusals=len(r),context_refusals=len(e),current_job_refusals=len(j),lifecycle_cases=len(l),publication_cases=pub['counts']['positive'],publication_refusals=pub['counts']['refusals'],producer_cases=p,restore_cases=r,context_cases=e,current_job_cases=j,lifecycle=l,publication=pub,frozen_methods=f,core_controls_passed=True,core_test_count=len(core_controls.RECORDS),core_controls=core_controls.RECORDS,core_incremental_records=core_records,seam_test_count=len(seam['cases']),seam=seam,native_payload_acquired=False,actual_view_executed=False,RC_executed=False,simulation_executed=False,**a.FLAGS)
        result['source_log_refusals']=14;transport=transport_controls(ctx,result);result['source_log_refusals']=len(transport);result['source_log_cases']=transport
        a.bind_controls(a.encode(result),ctx);a.source_guard(ctx)
    except BaseException as error:primary=error;result=dict(status='FAIL_CANONICAL_VIEW_ADAPTER_SOURCE_CONTROLS',passed=False,error=repr(error),traceback=traceback.format_exc(),**a.FLAGS)
    (out/'result.json').write_bytes(a.encode(result));print(json.dumps(result,sort_keys=True))
    if primary is not None:raise primary
if __name__=='__main__':main()
