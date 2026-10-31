#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Integrated GitHub-only source and explicit synthetic controls; no native acquisition."""
import ast,base64,copy,json,os,tempfile,types,traceback,zlib
from pathlib import Path
from unittest.mock import patch
import cdr_via2_m3_fresh_rc_admission as a
import cloud_cdr_via2_m3_fresh_rc as host
import cdr_via2_m3_fresh_rc_runtime as runtime
import check_cdr_via2_m3_fresh_rc_producer as producer_controls
import check_cdr_via2_m3_fresh_rc_runtime as runtime_controls
import check_cdr_via2_m3_fresh_rc_publication as publication_controls
import check_cdr_via2_m3_fresh_rc_namespaces as namespace_controls
import check_cdr_via2_m3_fresh_rc_core as core_controls
ROOT=a.ROOT

def env(mode='rc',job='fresh-rc'):
    return dict(GITHUB_ACTIONS='true',RUNNER_ENVIRONMENT='github-hosted',RUNNER_OS='Linux',GITHUB_EVENT_NAME='workflow_dispatch',
      GITHUB_REPOSITORY=a.q.REPOSITORY,GITHUB_REF='refs/heads/'+a.BRANCH,GITHUB_WORKFLOW_REF=a.q.REPOSITORY+'/'+a.WORKFLOW+'@refs/heads/'+a.BRANCH,
      GITHUB_RUN_ATTEMPT='1',GITHUB_SHA='a'*40,GITHUB_RUN_ID='12345',APPROVED_SOURCE='a'*40,REQUESTED_MODE=mode,GITHUB_JOB=job)

def reject(fn):
    try:fn()
    except(AssertionError,ValueError,FileNotFoundError,KeyError):return True
    raise AssertionError('Invalid fixture accepted')

def context_controls(c):
    value=env();ctx=a.context(value);faults=[]
    for key,bad in [('GITHUB_SHA','bad'),('APPROVED_SOURCE','b'*40),('GITHUB_RUN_ATTEMPT','2'),('GITHUB_REF','refs/heads/main'),('GITHUB_JOB','candidate'),('GITHUB_EVENT_NAME','push'),('GITHUB_REPOSITORY','other/repo'),('RUNNER_ENVIRONMENT','self-hosted')]:
        modified=dict(value);modified[key]=bad;reject(lambda:a.context(modified));faults.append(key)
    disabled=copy.deepcopy(c);disabled['fresh_rc_execution_authorized']=False
    reject(lambda:a.authorize_native(ctx,disabled));faults.append('explicit-disabled-authority')
    authorized=copy.deepcopy(c);authorized['fresh_rc_execution_authorized']=True;a.authorize_native(ctx,authorized)
    actual_source_context=a.context(os.environ)
    a.require(actual_source_context['job']=='source-controls','actual source-control job identity')
    reject(lambda:a.authorize_native(actual_source_context,authorized));faults.append('actual-source-job-refused-with-enabled-config')
    for key in('generation_authorized','electrical_simulation_authorized'):
        bad=copy.deepcopy(authorized);bad[key]=True;reject(lambda:a.authorize_native(ctx,bad));faults.append(key)
    return faults

def current_run_controls():
    ctx=a.context(env());source=dict(id=11,run_id=ctx['run_id'],run_attempt=1,head_sha=ctx['source'],name='source-controls',status='completed',conclusion='success',steps=[dict(name='synthetic controls',conclusion='success')])
    rows=[source,dict(source,id=12,name='preserve-job-log'),dict(source,id=13,name='fresh-rc',status='in_progress',conclusion=None,steps=[])]
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

def emission_controls():
    positive={'result.json':b'{"explicit_synthetic":true}', 'failure.stderr':b'actual failure mentions x.gds and schematic.spice without redaction', 'worker.stdout':b'explicit synthetic stdout', 'summary.jsonl':b'{"synthetic":true}\n', 'trace.log':b'explicit synthetic log'}
    suffixes=('.odb','.gds','.gds2','.gdsii','.oas','.oasis','.def','.lef','.spef','.spice','.sp','.cir','.l2n','.lvsdb','.lyrdb','.ext','.raw','.wave','.vcd','.fst','.bin','.tar','.gz','.zip','.7z')
    negative={('native/view/payload'+suffix+('.log'if suffix in('.spice','.sp','.cir')else'.json')):b'EXPLICIT_SYNTHETIC_NOT_NATIVE_BYTES'for suffix in suffixes}
    negative.update({'.gds.json':b'EXPLICIT_SYNTHETIC_NOT_NATIVE_BYTES','.gds/result.json':b'EXPLICIT_SYNTHETIC_NOT_NATIVE_BYTES','native/view/UPPER.GDS.JsOn':b'EXPLICIT_SYNTHETIC_NOT_NATIVE_BYTES','native/model.gds/result.json':b'EXPLICIT_SYNTHETIC_NOT_NATIVE_BYTES','inputs/result.json':b'EXPLICIT_SYNTHETIC_NOT_NATIVE_BYTES','unknown.txt':b'EXPLICIT_SYNTHETIC_NOT_NATIVE_BYTES','invalid.json':b'\xff\xfe'})
    with tempfile.TemporaryDirectory(prefix='synthetic-derived-name-boundary-')as temp:
        root=Path(temp);emitted=[]
        for name,raw in{**positive,**negative}.items():
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
        result=host.emit_derived(root,lambda line,**kw:emitted.append(line))
        a.require(set(result['complete_inventory'])==set(positive)|set(negative),'all known and unknown bytes retained in full cloud inventory')
        a.require(set(result['emitted_derived'])==set(positive),'composite native suffix, unknown text and invalid UTF8 are cloud-only')
        chunks=[json.loads(line.split('CHUNK ',1)[1])for line in emitted if 'CHUNK 'in line]
        a.require({row['name']for row in chunks}==set(positive),'no native-classified payload emitted')
        for name,raw in positive.items():
            rows=sorted((row for row in chunks if row['name']==name),key=lambda row:row['index'])
            restored=zlib.decompress(b''.join(base64.b64decode(row['data'],validate=True)for row in rows))
            a.require(restored==raw,'valid failure/stdout bytes remain complete and unredacted')
    return dict(positive=sorted(positive),refused=sorted(negative),positive_count=len(positive),refusal_count=len(negative),native_payloads_synthetic=True)

def transport_controls(ctx,result,c):
    key='fresh-rc-controls/result.json';records={'fresh-rc-controls.stdout':b'\x1b[31mSYNTHETIC\x00COMPLETE','fresh-rc-controls.stderr':b'',key:a.encode(result)}
    def log_bytes(values):
        lines=['EXPLICIT_SYNTHETIC_LOG_TRANSPORT_FIXTURE']
        for name,raw in values.items():
            pin=a.q.fingerprint(raw);lines.append('VIA2_M3_RC_CONTROL_INDEX '+json.dumps(dict(path=name,**pin,chunks=1)))
            lines.append('VIA2_M3_RC_CONTROL_CHUNK '+json.dumps(dict(path=name,index=0,base64=base64.b64encode(raw).decode())))
        return ('\n'.join(lines)+'\n').encode()
    log=log_bytes(records);observed,proof=a.authenticate_source_log(ctx,log,c)
    a.require(observed==records and proof['full_raw_log']==a.q.fingerprint(log),'complete exact three-record transport')
    refusals=[];lines=log.decode().splitlines()
    for label,modified in [('missing-index','\n'.join(x for x in lines if not(x.startswith('VIA2_M3_RC_CONTROL_INDEX ')and 'fresh-rc-controls.stdout'in x)).encode()),('missing-chunk','\n'.join(x for x in lines if not(x.startswith('VIA2_M3_RC_CONTROL_CHUNK ')and 'fresh-rc-controls.stdout'in x)).encode()),('duplicate-index',log+(lines[1]+'\n').encode()),('duplicate-chunk',log+(lines[2]+'\n').encode()),('bad-base64',log.replace(b'"base64": ""',b'"base64": "%"',1)),('extra-path',log.replace(b'fresh-rc-controls.stdout',b'unexpected-path',1))]:
        reject(lambda:a.authenticate_source_log(ctx,modified,c));refusals.append(label)
    mutations=[('wrong-source',lambda r:r['context'].update(source='1'*40)),('wrong-run',lambda r:r['context'].update(run_id=2)),('bad-result',lambda r:r.update(passed=False))]
    mutations += [(name+'-missing',lambda r,n=name:r['controls'].__setitem__(n,0))for name in c['source_control_requirements']]
    mutations += [(name+'-claimed',lambda r,n=name:r.__setitem__(n,True))for name in ('native_payload_acquired','RC_executed','simulation_executed','layout_regenerated')]
    for label,mutate in mutations:
        bad=copy.deepcopy(result);mutate(bad);values=dict(records);values[key]=a.encode(bad);reject(lambda:a.authenticate_source_log(ctx,log_bytes(values),c));refusals.append(label)
    with patch.object(a.subprocess,'check_output',return_value=b'\x1b[31mRAW\x00BYTES')as execute:
        a.require(a.read_source_log(123)==b'\x1b[31mRAW\x00BYTES','escape bytes unchanged')
        execute.assert_called_once_with(['gh','api','--allow-escape-sequences','repos/'+a.q.REPOSITORY+'/actions/jobs/123/logs'])
    return refusals

def acquisition_failure_controls():
    cases=[]
    with tempfile.TemporaryDirectory(prefix='explicit-acquisition-primary-')as tmp:
        root=Path(tmp);out=root/'fresh';out.mkdir();primary=ValueError('explicit synthetic API acquisition failure')
        c,d=runtime.records(ROOT);namespace=dict(vars(runtime))
        namespace['records']=lambda:(c,d)
        namespace['a']=types.SimpleNamespace(OUT=out,ROOT=root,source_guard=lambda ctx:None,native_preflight=lambda *args:None)
        fixture=types.FunctionType(runtime.acquire.__code__,namespace,'explicit_synthetic_acquire',runtime.acquire.__defaults__)
        a.require(fixture.__code__ is runtime.acquire.__code__,'same acquisition body')
        def failing_api(path):raise primary
        try:fixture(out,out/'preflight.json',{}, {},{},api_call=failing_api)
        except ValueError as error:a.require(error is primary,'actual API primary preserved')
        else:raise AssertionError('acquisition failure became success')
        evidence=a.q.decode((out/'runtime-inputs/result.json').read_bytes())
        a.require(evidence['status']=='FAIL_RUNTIME_ACQUISITION'and evidence['error']==repr(primary)and evidence['native_extraction_executed']is False,'actual pre-supervisor runtime failure saved')
        a.require(not list(root.glob('fresh-rc-runtime-*')),'owned temporary archive directory cleaned')
        cases.append('same_acquire_code_api_failure_retained_before_supervisor')
        low=root/'low';low.mkdir()
        with patch.object(host.shutil,'disk_usage',return_value=types.SimpleNamespace(free=7)):
            reject(lambda:host.storage_check(low,8))
        a.require(a.q.decode((low/'initial-storage.json').read_bytes())==dict(free_bytes=7,required_bytes=8),'actual low-disk bytes saved before refusal')
        cases.append('low_disk_measured_once_and_preserved_before_refusal')
    return cases

def qualification_controls(c):
    value=dict(status=c['core']['qualification_status'],fresh_RC_pipeline_complete=True,qualified_pex=False,electrical_accepted=False,full_phy_accepted=False,loaded_simulation_passed=False)
    a.require(host.require_qualification(value,c)is value,'same complete qualification object')
    cases=['complete_qualification_identity_preserved']
    for name,bad in [('arbitrary',{}),('partial',dict(value,fresh_RC_pipeline_complete=False)),('synthetic',dict(value,status='PASS_SYNTHETIC_PHASE_REPORT_VALIDATION_ONLY'))]+[(name,dict(value,**{name:True}))for name in ('qualified_pex','electrical_accepted','full_phy_accepted','loaded_simulation_passed')]:
        reject(lambda:host.require_qualification(bad,c));cases.append('refuse_'+name)
    tree=ast.parse((ROOT/'scripts/cloud_cdr_via2_m3_fresh_rc.py').read_text())
    body=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='perform')
    statements=[n for n in ast.walk(body)if isinstance(n,ast.Try)][0].body
    positions=[i for i,n in enumerate(statements)if isinstance(n,ast.Assign)and isinstance(n.value,ast.Call)and isinstance(n.value.func,ast.Name)and n.value.func.id=='pipeline']
    a.require(len(positions)==1,'one actual pipeline call');following=statements[positions[0]+1]
    a.require(ast.dump(following,include_attributes=False)==ast.dump(ast.parse('require_qualification(qualification,c)').body[0],include_attributes=False),'outer guard immediately after actual pipeline return')
    cases.append('actual_perform_ast_requires_gate_before_success')
    return cases

def main():
    ctx=a.context(os.environ);c,p=a.source_guard(ctx);out=ROOT/'fresh-rc-controls';a.require(not out.exists(),'new integrated source evidence');out.mkdir();primary=None;observations={};counts={}
    try:
        a.require(ctx['job']=='source-controls','source control job only')
        prod=producer_controls.controls(ROOT,p);observations['producer']=prod;counts.update(producer_positive=len(prod['positive_controls']),producer_refusals=len(prod['refusal_controls']))
        rt=runtime_controls.controls(ROOT);observations['runtime']=rt;counts.update(runtime_positive=len(rt['positive_controls']),runtime_refusals=len(rt['refusal_controls']))
        e=context_controls(c);j=current_run_controls();l=lifecycle_controls()+acquisition_failure_controls()+qualification_controls(c);em=emission_controls()
        observations.update(context=e,current_jobs=j,lifecycle=l,emission=em);counts.update(context_refusals=len(e),current_job_refusals=len(j),lifecycle_cases=len(l),emission_refusals=em['refusal_count'])
        pub=publication_controls.controls(dict(source=ctx['source'],run_id=ctx['run_id'],attempt=1));a.require(pub['passed']is True,'complete publication controls');observations['publication']=pub
        counts.update(publication_cases=pub['counts']['positive'],publication_refusals=pub['counts']['refusals'])
        ns=a.q.decode(a.q.regular(ROOT,'scripts/cdr-via2-m3-fresh-rc-namespace-inputs.json').read_bytes());namespace_controls.RECORDS.clear();observations['namespace']=namespace_controls.RECORDS
        namespace_controls.definition_controls(ns);namespace_controls.real_schema_source_control();namespace_controls.binding_controls(ns)
        observations['namespace']=namespace_controls.RECORDS
        counts.update(namespace_positive=sum(x['kind']!='expected_refusal'for x in namespace_controls.RECORDS),namespace_refusals=sum(x['kind']=='expected_refusal'for x in namespace_controls.RECORDS))
        core_controls.RECORDS.clear();observations['core']=core_controls.RECORDS;core_controls.definition_controls()
        with tempfile.TemporaryDirectory(prefix='explicit-core-fixture-',dir=out)as tmp:
            copyroot=Path(tmp)/'copy';copyroot.mkdir();core_controls.copy_and_command_controls(copyroot)
        import check_cdr_via2_m3_fresh_rc_native as phase_controls
        phase=phase_controls.controls(ctx,out/'phase-fixtures');observations['phase']=phase
        a.require(phase['status']=='PASS_SOURCE_ONLY_PHASE_CONTROLS'and phase['failed']==0 and phase['native_acquired']is False and phase['native_executed']is False,'complete explicit synthetic phase controls')
        observations['full_numerical_fixture']=phase['full_numerical_fixture'];observations['core']=core_controls.RECORDS
        counts.update(core_controls=len(core_controls.RECORDS),phase_controls=len(phase['records']))
        if(out/'phase-fixtures').exists():observations['phase_fixture_files']=host.publisher.inventory(out/'phase-fixtures')
        counts['source_log_refusals']=c['source_control_requirements']['source_log_refusals']
        result=dict(status='PASS_CURRENT_VIA2_M3_FRESH_RC_SOURCE_CONTROLS',passed=True,context=dict(source=ctx['source'],run_id=ctx['run_id'],attempt=1),controls=counts,observations=observations,native_payload_acquired=False,RC_executed=False,simulation_executed=False,layout_regenerated=False,qualified_pex=False,electrical_accepted=False,full_phy_accepted=False)
        transport=transport_controls(ctx,result,c);observations['transport']=transport;counts['source_log_refusals']=len(transport)
        a.bind_controls(a.encode(result),ctx,c);a.source_guard(ctx)
    except BaseException as error:
        primary=error;result=dict(status='FAIL_CURRENT_VIA2_M3_FRESH_RC_SOURCE_CONTROLS',passed=False,context=dict(source=ctx['source'],run_id=ctx['run_id'],attempt=1),error=repr(error),traceback=traceback.format_exc(),controls=counts,observations=observations,native_payload_acquired=False,RC_executed=False,simulation_executed=False,layout_regenerated=False)
    (out/'result.json').write_bytes(a.encode(result));print(json.dumps(result,sort_keys=True))
    if primary is not None:raise primary
if __name__=='__main__':main()
