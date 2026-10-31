#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted meaningful synthetic admission controls for existing physical-only reuse."""
import ast,base64,copy,json,os,tempfile,types,traceback
from pathlib import Path
from unittest.mock import patch
import cdr_via2_m3_physical_recheck_admission as a
import cloud_cdr_via2_m3_physical_recheck as host
import check_cdr_via2_m3_physical_recheck_publication as publication_controls
ROOT=a.ROOT
def env(mode='recheck',job='physical-recheck'):
    return dict(GITHUB_ACTIONS='true',RUNNER_ENVIRONMENT='github-hosted',RUNNER_OS='Linux',GITHUB_EVENT_NAME='workflow_dispatch',
      GITHUB_REPOSITORY=a.q.REPOSITORY,GITHUB_REF='refs/heads/'+a.BRANCH,GITHUB_WORKFLOW_REF=a.q.REPOSITORY+'/'+a.WORKFLOW+'@refs/heads/'+a.BRANCH,
      GITHUB_RUN_ATTEMPT='1',GITHUB_SHA='a'*40,GITHUB_RUN_ID='12345',APPROVED_SOURCE='a'*40,REQUESTED_MODE=mode,GITHUB_JOB=job)

def reject(fn):
    try:fn()
    except(AssertionError,ValueError,FileNotFoundError,KeyError):return True
    raise AssertionError('Invalid fixture accepted')
def producer_controls(c):
    p=c['producer'];prefix=p['proof_prefix']
    values=[a.q.decode(a.q.regular(ROOT,prefix+n+'.json').read_bytes())for n in('run','jobs','release','tag-ref')]
    a.validate_producer(c,*values)
    faults=[]
    for label,index,mutate in[
      ('run-source',0,lambda x:x.update(head_sha='1'*40)),('run-success',0,lambda x:x.update(conclusion='success')),
      ('run-not-terminal',0,lambda x:x.update(status='in_progress')),('run-retry',0,lambda x:x.update(run_attempt=2)),
      ('missing-job',1,lambda x:x['jobs'].pop()),('altered-job-source',1,lambda x:x['jobs'][0].update(head_sha='2'*40)),
      ('altered-native-conclusion',1,lambda x:next(j for j in x['jobs']if j['id']==p['job_id']).update(conclusion='success')),
      ('altered-failure-step',1,lambda x:next(s for j in x['jobs']if j['id']==p['job_id']for s in j['steps']if s['conclusion']=='failure').update(name='different failure')),
      ('release-source',2,lambda x:x.update(target_commitish='3'*40)),('release-draft',2,lambda x:x.update(draft=True)),
      ('release-extra',2,lambda x:x['assets'].append(dict(x['assets'][0],id=123456789,name='unexpected'))),
      ('release-asset-bytes',2,lambda x:x['assets'][0].update(size=x['assets'][0]['size']+1)),
      ('release-asset-digest',2,lambda x:x['assets'][0].update(digest='sha256:'+'0'*64)),
      ('tag-source',3,lambda x:x['object'].update(sha='4'*40)),('tag-object',3,lambda x:x['object'].update(type='tag'))]:
        bad=copy.deepcopy(values);mutate(bad[index]);reject(lambda:a.validate_producer(c,*bad));faults.append(label)
    return faults

def restore_controls(c):
    faults=[]
    with tempfile.TemporaryDirectory()as temporary:
        root=Path(temporary);restore=root/c['producer']['restore_root_relative'];restore.mkdir(parents=True)
        config=copy.deepcopy(c);producer=config['producer'];original,_=a.metadata(c)
        # Every byte here is explicitly synthetic; real GDS/models/archives are never acquired.
        for name in original['files']:
            target=restore/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(('EXPLICIT_SYNTHETIC_SOURCE_CLOSURE '+name+'\n').encode())
        selected={n:a.q.file_pin(restore/n)for n in producer['selected_inputs']}
        producer['selected_inputs']=selected;producer['frozen_generated_inputs']={str(restore/n):v['sha256']for n,v in selected.items()}
        generated=dict(inputs=producer['frozen_generated_inputs'],outputs={Path(n).name:a.q.file_pin(restore/n)['sha256']for n in producer['layout_copy_members']if not n.endswith('/result.json')},ports=['P'+str(i)for i in range(25)])
        generation=dict(status='GENERATED_DECLARED_VIA2_M3_CANDIDATE_REQUIRES_FRESH_DRC_LVS_RC_WAVES',geometry_generated=True,original_full_rails_unchanged=True,
          DRC_executed=False,LVS_executed=False,RC_executed=False,proof=dict(structural_reversal_exact=True,added_records=[dict(explicit_synthetic=i)for i in range(16)],original_file_byte_equality_claimed=False,candidate=a.q.file_pin(restore/producer['candidate_member'])),**a.FLAGS)
        def fixture_call(generated_record=generated,generation_record=generation,restore_path=restore,full_transform=None):
            (restore/producer['generated_layout_member']).write_bytes(a.encode(generated_record))
            (restore/producer['generation_member']).write_bytes(a.encode(generation_record))
            files={n:a.q.file_pin(restore/n)for n in original['files']}
            full=dict(every_member_authenticated=True,full_member_count=99,full_members=files,selected=copy.deepcopy(files))
            if full_transform:full_transform(full)
            with patch.object(a,'metadata',return_value=(dict(files=files),{})):
                return a.validate_restored(config,restore_path,full,root=root)
        positive=fixture_call();a.require(positive['result_rewritten']is False and positive['all20_absolute_inputs_preserved']is True,'actual fixture validator positive')
        for label,kind,change in[
          ('wrong-absolute-input','layout',lambda d:d['inputs'].update({'/unowned/source':d['inputs'].pop(next(iter(d['inputs'])))})),
          ('missing-input','layout',lambda d:d['inputs'].pop(next(iter(d['inputs'])))),
          ('changed-output','layout',lambda d:d['outputs'].update({'nssoc_cdr_pd500_resistor_v59.gds':'0'*64})),
          ('duplicate-port','layout',lambda d:d['ports'].__setitem__(1,d['ports'][0])),
          ('15-shapes','generation',lambda d:d['proof']['added_records'].pop()),
          ('reversal-false','generation',lambda d:d['proof'].update(structural_reversal_exact=False)),
          ('fullrail-changed','generation',lambda d:d.update(original_full_rails_unchanged=False)),
          ('DRC-already-claimed','generation',lambda d:d.update(DRC_executed=True)),
          ('wrong-candidate','generation',lambda d:d['proof']['candidate'].update(sha256='1'*64))]:
            g=copy.deepcopy(generated);v=copy.deepcopy(generation);change(g if kind=='layout'else v)
            reject(lambda:fixture_call(g,v));faults.append(label)
        reject(lambda:fixture_call(restore_path=restore.parent/'other'));faults.append('wrong-restore-root')
        reject(lambda:fixture_call(full_transform=lambda d:d.update(full_member_count=98)));faults.append('partial99-census')
        reject(lambda:fixture_call(full_transform=lambda d:d['selected'].pop(next(iter(d['selected'])))));faults.append('partial-retained-members')
    return faults

def context_controls(c):
    value=env();ctx=a.context(value);faults=[]
    for key,bad in [('GITHUB_SHA','bad'),('APPROVED_SOURCE','b'*40),('GITHUB_RUN_ATTEMPT','2'),('GITHUB_REF','refs/heads/main'),('GITHUB_JOB','candidate'),('GITHUB_EVENT_NAME','push'),('GITHUB_REPOSITORY','other/repo'),('RUNNER_ENVIRONMENT','self-hosted')]:
        modified=dict(value);modified[key]=bad;reject(lambda:a.context(modified));faults.append(key)
    reject(lambda:a.authorize_native(ctx,c));faults.append('disabled-actual-authority')
    authorized=copy.deepcopy(c);authorized['physical_verification_authorized']=True;a.authorize_native(ctx,authorized)
    for key in('generation_authorized','fresh_rc_authorized','electrical_simulation_authorized'):
        bad=copy.deepcopy(authorized);bad[key]=True;reject(lambda:a.authorize_native(ctx,bad));faults.append(key)
    return faults

def frozen_methods():
    def function(text,name):
        lines=text.splitlines(keepends=True);nodes=[n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)and n.name==name]
        a.require(len(nodes)==1,'unique frozen function');n=nodes[0];return ''.join(lines[n.lineno-1:n.end_lineno]).rstrip()+'\n'
    old=(ROOT/'scripts/cloud_cdr_current_via2_m3_physical.py').read_text();new=(ROOT/'scripts/cloud_cdr_via2_m3_physical_recheck.py').read_text()
    for name in('derive_physical','validate_physical','finish','tokenless'):a.require(function(old,name)==function(new,name),'frozen method '+name)
    oldpub=(ROOT/'scripts/publish_cdr_current_via2_m3_physical.py').read_text();newpub=(ROOT/'scripts/publish_cdr_via2_m3_physical_recheck.py').read_text()
    for name in('inventory','prepare','validate_release','upload','publish'):a.require(function(oldpub,name)==function(newpub,name),'frozen publisher '+name)
    a.require('exact16-via2-m3-generation'not in new and 'ROOT/NATIVE'not in new,'no generator entry in recheck host')
    return dict(frozen_physical_and_lifecycle_methods=4,frozen_publication_methods=5,native_generator_invocation=False)
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


def transport_controls(ctx,result):
    records={n:b''for n in('recheck-controls.stdout','recheck-controls.stderr','recheck-source-closure.stdout','recheck-source-closure.stderr','recheck-decks.stdout','recheck-decks.stderr')}
    for name in('result.json','deck-source-preparation.json'):
        path='hw/soc/out/cdr-via2-m3-physical-recheck-source-closure-controls/'+name;records[path]=(ROOT/path).read_bytes()
    key='cdr-via2-m3-recheck-controls/result.json';records[key]=a.encode(result)
    def log_bytes(values):
        lines=['EXPLICIT_SYNTHETIC_LOG_TRANSPORT_FIXTURE']
        for name,raw in values.items():
            pin=a.q.fingerprint(raw)
            lines.append('VIA2_M3_RECHECK_CONTROL_INDEX '+json.dumps(dict(path=name,**pin,chunks=1)))
            lines.append('VIA2_M3_RECHECK_CONTROL_CHUNK '+json.dumps(dict(path=name,index=0,base64=base64.b64encode(raw).decode())))
        return ('\n'.join(lines)+'\n').encode()
    log=log_bytes(records);observed,proof=a.authenticate_source_log(ctx,log)
    a.require(observed==records and proof['full_raw_log']==a.q.fingerprint(log),'actual nine-record transport and bytes')
    refusals=[]
    lines=log.decode().splitlines()
    for label,modified in [('missing-index','\n'.join(x for x in lines if not(x.startswith('VIA2_M3_RECHECK_CONTROL_INDEX ')and 'recheck-controls.stdout'in x)).encode()),('missing-chunk','\n'.join(x for x in lines if not(x.startswith('VIA2_M3_RECHECK_CONTROL_CHUNK ')and 'recheck-controls.stdout'in x)).encode()),('duplicate-index',log+(lines[1]+'\n').encode()),('duplicate-chunk',log+(lines[2]+'\n').encode()),('bad-base64',log.replace(b'"base64": ""',b'"base64": "%"',1)),('extra-path',log.replace(b'recheck-controls.stdout',b'unexpected-path',1))]:
        reject(lambda:a.authenticate_source_log(ctx,modified));refusals.append(label)
    for label,mutate in [('wrong-source',lambda r:r['context'].update(source='1'*40)),('wrong-run',lambda r:r['context'].update(run_id=2)),('bad-result',lambda r:r.update(passed=False)),('missing-refusals',lambda r:r.update(restore_refusals=0)),('native-claimed',lambda r:r.update(drc_executed=True))]:
        bad=copy.deepcopy(result);mutate(bad);values=dict(records);values[key]=a.encode(bad);reject(lambda:a.authenticate_source_log(ctx,log_bytes(values)));refusals.append(label)
    closure_key='hw/soc/out/cdr-via2-m3-physical-recheck-source-closure-controls/result.json'
    for label,mutate in [('closure-source',lambda r:r.update(source='2'*40)),('closure-checker',lambda r:r['checker'].update(sha256='0'*64)),('closure-environment',lambda r:r.update(github_environment_spoofed=True))]:
        bad=a.q.decode(records[closure_key]);mutate(bad);values=dict(records);values[closure_key]=a.encode(bad);reject(lambda:a.authenticate_source_log(ctx,log_bytes(values)));refusals.append(label)
    return refusals

def main():
    ctx=a.context(os.environ);method=a.source_guard(ctx);out=ROOT/'cdr-via2-m3-recheck-controls'
    a.require(not out.exists(),'new source control output');out.mkdir();primary=None
    try:
        a.require(ctx['job']=='source-controls','synthetic controls only')
        p=producer_controls(method);r=restore_controls(method);e=context_controls(method);f=frozen_methods();l=lifecycle_controls()
        pub=publication_controls.controls(dict(source=ctx['source'],run_id=ctx['run_id'],attempt=1));a.require(pub['passed']is True,'full publisher controls')
        closure_path=ROOT/'hw/soc/out/cdr-via2-m3-physical-recheck-source-closure-controls/result.json';closure=a.q.decode(closure_path.read_bytes())
        a.require(closure['source']==ctx['source']and closure['run_id']==ctx['run_id']and closure['status']=='PASS_UNCHANGED_PHYSICAL_CHECKER_IMPORT_TO_FIRST_NATIVE_BOUNDARY_ONLY','actual same-run frozen checker fixture')
        counts=dict(import_source_refusals=len(closure['import_source_refusals']),runtime_source_refusals=len(closure['runtime_source_refusals']),external_and_write_barriers=len(closure['external_barriers']),observed_repository_reads=len(closure['observed_repository_reads']),first_native_boundary_calls=len(closure['calls']))
        result=dict(status='PASS_PHYSICAL_ONLY_REUSE_SOURCE_CONTROLS',passed=True,context=dict(source=ctx['source'],run_id=ctx['run_id'],attempt=1),producer_refusals=len(p),restore_refusals=len(r),context_refusals=len(e),lifecycle_cases=len(l),publication_cases=pub['counts']['positive'],publication_refusals=pub['counts']['refusals'],closure_counts=counts,closure_result=a.q.file_pin(closure_path),producer_cases=p,restore_cases=r,context_cases=e,lifecycle=l,publication=pub,frozen_methods=f,native_candidate_acquired=False,geometry_generated=False,drc_executed=False,lvs_executed=False,**a.FLAGS)
        result['source_log_refusals']=14
        transport=transport_controls(ctx,result);result['source_log_refusals']=len(transport);result['source_log_cases']=transport
        a.bind_controls(a.encode(result),ctx);a.source_guard(ctx)
    except BaseException as error:
        primary=error;result=dict(status='FAIL_PHYSICAL_ONLY_REUSE_SOURCE_CONTROLS',passed=False,error=repr(error),traceback=traceback.format_exc(),**a.FLAGS)
    (out/'result.json').write_bytes(a.encode(result));print(json.dumps(result,sort_keys=True))
    if primary is not None:raise primary
if __name__=='__main__':main()
