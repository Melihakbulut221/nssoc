#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted integrated actual-metadata and synthetic-process controls; no native acquisition."""
import ast,base64,copy,json,os,subprocess,sys,tempfile,types,traceback,zlib
from pathlib import Path
from unittest.mock import patch
import cdr_via2_m3_loaded_admission as a
import cloud_cdr_via2_m3_loaded as host
import check_cdr_via2_m3_loaded_producer as producer_controls
import check_cdr_via2_m3_loaded_runtime as runtime_controls
import check_cdr_via2_m3_loaded_native as native_controls
import check_cdr_via2_m3_loaded_publication as publication_controls
ROOT=a.ROOT

def env(mode='loaded',job='loaded'):
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
    disabled=copy.deepcopy(c);disabled['loaded_execution_authorized']=False
    reject(lambda:a.authorize_native(ctx,disabled));faults.append('explicit-disabled-authority')
    authorized=copy.deepcopy(c);authorized['loaded_execution_authorized']=True;a.authorize_native(ctx,authorized)
    actual_source_context=a.context(os.environ)
    a.require(actual_source_context['job']=='source-controls','actual source-control job identity')
    reject(lambda:a.authorize_native(actual_source_context,authorized));faults.append('actual-source-job-refused-with-enabled-config')
    for key in('generation_authorized','fresh_rc_execution_authorized'):
        bad=copy.deepcopy(authorized);bad[key]=True;reject(lambda:a.authorize_native(ctx,bad));faults.append(key)
    return faults


def current_run_controls():
    ctx=a.context(env());source=dict(id=11,run_id=ctx['run_id'],run_attempt=1,head_sha=ctx['source'],name='source-controls',status='completed',conclusion='success',steps=[dict(name='synthetic controls',conclusion='success')])
    rows=[source,dict(source,id=12,name='preserve-job-log'),dict(source,id=13,name='loaded',status='in_progress',conclusion=None,steps=[])]
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
    key='loaded-controls/result.json';records={'loaded-controls.stdout':b'\x1b[31mSYNTHETIC\x00COMPLETE','loaded-controls.stderr':b'',key:a.encode(result)}
    def log_bytes(values):
        lines=['EXPLICIT_SYNTHETIC_LOG_TRANSPORT_FIXTURE']
        for name,raw in values.items():
            pin=a.q.fingerprint(raw);lines.append('VIA2_M3_LOADED_CONTROL_INDEX '+json.dumps(dict(path=name,**pin,chunks=1)))
            lines.append('VIA2_M3_LOADED_CONTROL_CHUNK '+json.dumps(dict(path=name,index=0,base64=base64.b64encode(raw).decode())))
        return ('\n'.join(lines)+'\n').encode()
    log=log_bytes(records);observed,proof=a.authenticate_source_log(ctx,log,c)
    a.require(observed==records and proof['full_raw_log']==a.q.fingerprint(log),'complete exact three-record transport')
    refusals=[];lines=log.decode().splitlines()
    for label,modified in [('missing-index','\n'.join(x for x in lines if not(x.startswith('VIA2_M3_LOADED_CONTROL_INDEX ')and 'loaded-controls.stdout'in x)).encode()),('missing-chunk','\n'.join(x for x in lines if not(x.startswith('VIA2_M3_LOADED_CONTROL_CHUNK ')and 'loaded-controls.stdout'in x)).encode()),('duplicate-index',log+(lines[1]+'\n').encode()),('duplicate-chunk',log+(lines[2]+'\n').encode()),('bad-base64',log.replace(b'"base64": ""',b'"base64": "%"',1)),('extra-path',log.replace(b'loaded-controls.stdout',b'unexpected-path',1))]:
        reject(lambda:a.authenticate_source_log(ctx,modified,c));refusals.append(label)
    mutations=[('wrong-source',lambda r:r['context'].update(source='1'*40)),('wrong-run',lambda r:r['context'].update(run_id=2)),('bad-result',lambda r:r.update(passed=False))]
    mutations += [(name+'-missing',lambda r,n=name:r['controls'].__setitem__(n,0))for name in c['source_control_requirements']]
    mutations += [(name+'-claimed',lambda r,n=name:r.__setitem__(n,True))for name in ('native_payload_acquired','RC_executed','simulation_executed','layout_regenerated')]
    for label,mutate in mutations:
        bad=copy.deepcopy(result);mutate(bad);values=dict(records);values[key]=a.encode(bad);reject(lambda:a.authenticate_source_log(ctx,log_bytes(values),c));refusals.append(label)
    with patch.object(a.subprocess,'check_output',return_value=b'\x1b[31mRAW\x00BYTES')as execute:
        a.require(a.read_source_log(123,a.Deadline(60))==b'\x1b[31mRAW\x00BYTES','escape bytes unchanged')
        a.require(execute.call_count==1 and execute.call_args.args[0]==['gh','api','--allow-escape-sequences','repos/'+a.q.REPOSITORY+'/actions/jobs/123/logs']and 0<execute.call_args.kwargs['timeout']<=60,'bounded complete raw log API')
    return refusals



def qualification_controls(c):
    value=dict(status='PASS_WHOLE_MIM_PD500_LOADED_SCREEN_NOT_CLOSED_LOOP_OR_PHY_SIGNOFF',
      case='nominal_late',transient_executed=True,sources_unchanged=True,devices_passed=True,data_passed=True,
      vi=dict(passed=True),accepted=False,cdr_accepted=False,full_phy_accepted=False,qualified_pex=False,closed_loop=False)
    a.require(host.require_qualification(value,c)is value,'complete same synthetic qualification object')
    refusals=[]
    cases=[('empty',{}),('wrong-status',dict(value,status='SYNTHETIC_PASS'))]
    for name,bad in [('case','nominal_early'),('transient_executed',False),('sources_unchanged',False),('devices_passed',False),('data_passed',False),('vi',dict(passed=False))]:
        cases.append((name,dict(value,**{name:bad})))
    cases += [(name,dict(value,**{name:True}))for name in ('accepted','cdr_accepted','full_phy_accepted','qualified_pex','closed_loop')]
    for name,bad in cases:
        reject(lambda:host.require_qualification(bad,c));refusals.append(name)
    with tempfile.TemporaryDirectory(prefix='synthetic-low-disk-')as t:
        out=Path(t)
        with patch.object(host.shutil,'disk_usage',return_value=types.SimpleNamespace(free=7)):
            reject(lambda:host.storage_check(out,8))
        a.require(a.q.decode((out/'initial-storage.json').read_bytes())==dict(free_bytes=7,required_bytes=8),'actual low disk preserved before rejection')
    return dict(positive=['full_qualification_identity','low_disk_receipt_before_refusal'],refusals=refusals)

def complete_core(out,ctx):
    command=[sys.executable,'-B',str(ROOT/'scripts/check_cdr_via2_m3_loaded_core.py'),'--out',str(out/'core')]
    record=dict(argv=command,cwd=str(ROOT),source=ctx['source'],run_id=ctx['run_id'],scope='UNCHANGED_QUALIFIED_27_SOURCE_CONTROLS_IN_ISOLATED_CHILD',timeout_seconds=300)
    a.q.write_new(out/'core-command.json',a.encode(record))
    with (out/'core.stdout').open('xb')as stdout,(out/'core.stderr').open('xb')as stderr:
        completed=subprocess.run(command,cwd=ROOT,stdout=stdout,stderr=stderr,timeout=300)
    record.update(returncode=completed.returncode,stdout=a.q.file_pin(out/'core.stdout'),stderr=a.q.file_pin(out/'core.stderr'))
    a.q.write_new(out/'core-command-result.json',a.encode(record))
    result=a.q.decode(a.q.regular(out/'core','result.json').read_bytes())
    a.require(completed.returncode==0 and result['successful']is True and result['tests']==27 and result['failures']==result['errors']==result['skips']==0,'all unchanged27 tests without skips')
    a.require(result['source']==ctx['source']and result['run']==str(ctx['run_id']),'actual current source identity retained in child')
    a.require(all(result[k]is False for k in('actual_engine_executed','loaded_simulation_executed','native_model_card_validation_executed','electrical_accepted','qualified_pex','full_phy_accepted')),'synthetic core is not native or electrical qualification')
    return result

def main():
    ctx=a.context(os.environ);c,p=a.source_guard(ctx)
    out=ROOT/'loaded-controls';a.require(not out.exists()and not out.is_symlink(),'new integrated source evidence');out.mkdir()
    primary=None;observations={};counts={}
    def save(stage):
        a.q.write_new(out/('stage-%02d.json'%len(list(out.glob('stage-*.json')))),a.encode(dict(stage=stage,controls=counts,observations=observations,source=ctx['source'],run_id=ctx['run_id'],native_payload_acquired=False)))
    try:
        a.require(ctx['job']=='source-controls','only actual source controls job')
        prod=producer_controls.controls(ROOT,out/'producer');observations['producer']=prod
        counts.update(producer_positive=prod['positive'],producer_refusals=prod['refusals']);save('producer')
        rt=runtime_controls.controls(ROOT,out/'runtime');observations['runtime']=rt
        counts.update(runtime_positive=rt['positive'],runtime_refusals=rt['refusals']);save('runtime')
        core=complete_core(out,ctx);observations['core']=core;counts['core_controls']=core['tests'];save('core')
        native=native_controls.controls(out/'native',lambda:a.source_guard(ctx));observations['native']=native
        counts.update(native_positive=native['positive'],native_refusals=native['refusals']);save('native-process')
        e=context_controls(c);j=current_run_controls();l=lifecycle_controls();em=emission_controls();qualification=qualification_controls(c)
        observations.update(context=e,current_jobs=j,lifecycle=l,emission=em,qualification=qualification)
        counts.update(context_refusals=len(e),current_job_refusals=len(j),lifecycle_cases=len(l),emission_refusals=em['refusal_count'],core_refusals=len(qualification['refusals']));save('admission')
        pub=publication_controls.controls(dict(source=ctx['source'],run_id=ctx['run_id'],attempt=1));a.require(pub['passed']is True,'complete publication controls');observations['publication']=pub
        counts.update(publication_cases=pub['counts']['positive'],publication_refusals=pub['counts']['refusals'])
        counts['lifecycle_cases']+=pub['counts']['lifecycle'];save('publication')
        # The transport fixture first needs a complete synthetic successful result;
        # its measured refusal count then replaces this declared minimum.
        counts['source_log_refusals']=c['source_control_requirements']['source_log_refusals']
        result=dict(status='PASS_CURRENT_VIA2_M3_LOADED_SOURCE_CONTROLS',passed=True,
          context=dict(source=ctx['source'],run_id=ctx['run_id'],attempt=1),controls=counts,observations=observations,
          native_payload_acquired=False,RC_executed=False,simulation_executed=False,layout_regenerated=False,qualified_pex=False,electrical_accepted=False,full_phy_accepted=False)
        transport=transport_controls(ctx,result,c);observations['transport']=transport;counts['source_log_refusals']=len(transport)
        a.bind_controls(a.encode(result),ctx,c);a.source_guard(ctx);save('complete')
    except BaseException as error:
        primary=error;result=dict(status='FAIL_CURRENT_VIA2_M3_LOADED_SOURCE_CONTROLS',passed=False,
          context=dict(source=ctx['source'],run_id=ctx['run_id'],attempt=1),error=repr(error),traceback=traceback.format_exc(),controls=counts,observations=observations,
          native_payload_acquired=False,RC_executed=False,simulation_executed=False,layout_regenerated=False)
    try:a.q.write_new(out/'result.json',a.encode(result))
    except BaseException as secondary:
        print('UNSAVED_LOADED_CONTROLS '+json.dumps(dict(result,secondary_error=repr(secondary)),sort_keys=True),flush=True)
        if primary is None:raise
    print(json.dumps(result,sort_keys=True),flush=True)
    if primary is not None:raise primary

if __name__=='__main__':main()
