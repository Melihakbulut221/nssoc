#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""New exact-source fresh RC admission; no historical producer or environment substitution."""
import base64,json,os,re,subprocess
from pathlib import Path
import cloud_cdr_current_eight_drain_wave_replay as q
import cdr_via2_m3_fresh_rc_producer as producer
ROOT=Path(__file__).resolve().parents[1]
BRANCH='codex/cdr-via2-m3-fresh-rc-adapter'
CONFIG='scripts/cdr-via2-m3-fresh-rc-adapter-inputs.json'
MANIFEST='scripts/cdr-via2-m3-fresh-rc-adapter-pins.json'
PRODUCER='scripts/cdr-via2-m3-fresh-rc-producer-inputs.json'
WORKFLOW='.github/workflows/cloud-evidence-summary.yml'
GROUP='cdr-via2-m3-fresh-rc-nominal_late'
OUT=ROOT/'hw/soc/out/cloud-cdr-via2-m3-fresh-rc'
ORIGINAL=ROOT/'hw/soc/out/cloud-cdr-via2-m3-canonical-view'
require=q.require;encode=q.encode
def context(env):
    require(env.get('GITHUB_ACTIONS')=='true'and env.get('RUNNER_ENVIRONMENT')=='github-hosted'and env.get('RUNNER_OS')=='Linux','hosted Linux only')
    require(env.get('GITHUB_REPOSITORY')==q.REPOSITORY and env.get('GITHUB_EVENT_NAME')=='workflow_dispatch','manual exact repository')
    require(env.get('GITHUB_REF')=='refs/heads/'+BRANCH and env.get('GITHUB_WORKFLOW_REF')==q.REPOSITORY+'/'+WORKFLOW+'@refs/heads/'+BRANCH,'exact branch/workflow')
    require(env.get('GITHUB_RUN_ATTEMPT')=='1','no rerun')
    head=env.get('GITHUB_SHA','');run=env.get('GITHUB_RUN_ID','')
    require(re.fullmatch('[0-9a-f]{40}',head)and re.fullmatch('[1-9][0-9]*',run),'source/run')
    require(env.get('APPROVED_SOURCE')==head,'explicit current source')
    mode=env.get('REQUESTED_MODE');job=env.get('GITHUB_JOB')
    require((mode,job)in(('controls','source-controls'),('rc','source-controls'),('rc','fresh-rc')),'bounded mode/job')
    return dict(source=head,run_id=int(run),attempt=1,mode=mode,job=job,case='nominal_late',group=GROUP,token=run+'-1')

def validate_config(c):
    require(c['schema']=='cdr-via2-m3-fresh-rc-adapter-v1'and c['branch']==BRANCH and c['repository']==q.REPOSITORY,'exact fresh RC adapter')
    require(c['workflow']==WORKFLOW and c['workflow_id']==382556685 and c['case']=='nominal_late','actual workflow and producer case label')
    require(c['source_controls_authorized']is True and c['native_payloads_cloud_only']is True and c['all_acceptance_false']is True,'cloud-only bounded scope')
    require(type(c['fresh_rc_execution_authorized'])is bool,'explicit typed fresh RC authority')
    require(c['generation_authorized']is c['electrical_simulation_authorized']is False,'no generation or waveform authority')
    require(c['producer_path']==PRODUCER and c['original_output_root']==str(ORIGINAL)and c['fresh_output_root']==str(OUT),'separate original and fresh roots')
    require(c['core']is not None and c['namespace_source']=='0a9e1741232bf60fdf4f4c443ea3466575b7c6b3','qualified corrected core binding required')
    required={'producer_positive','producer_refusals','namespace_positive','namespace_refusals','core_controls','context_refusals','current_job_refusals','source_log_refusals','lifecycle_cases','publication_cases','publication_refusals','emission_refusals','runtime_positive','runtime_refusals','phase_controls'}
    require(set(c['source_control_requirements'])==required and all(type(v)is int and v>0 for v in c['source_control_requirements'].values()),'complete positive actual source-control requirements')
    return c

def historical_controls(root,c):
    for name,spec in c['historical_source_controls'].items():
        prefix=spec['prefix'];raw=q.regular(root,prefix+'/receipt.json').read_bytes()
        require(q.fingerprint(raw)==spec['receipt'],'exact historical source proof '+name);receipt=q.decode(raw)
        require(receipt['source']==spec['source']and receipt['run']==spec['run_id']and receipt['attempt']==1 and receipt['conclusion']=='success','actual historical source-control execution')
        require(len(receipt['files'])+1==spec['files'],'complete historical proof file census')
        for relative,pin in receipt['files'].items():require(q.fingerprint(q.regular(root,prefix+'/'+relative).read_bytes())==pin,'complete historical proof bytes '+relative)
        if name=='core':
            require(receipt['top_level_passed']==28 and receipt['failed']==0 and receipt['native_acquired']is receipt['native_executed']is False,'actual full numerical source controls only')
        elif name=='namespace':
            require(receipt['tests']==48 and receipt['expected_refusals']==42 and receipt['positives']==6 and receipt['native_acquisition']is receipt['native_execution']is False,'actual corrected model-schema namespace source controls')
        else:raise AssertionError('unexpected historical source-control group')
    for name,pin in c['core']['source_files'].items():require(q.file_pin(q.regular(root,name))==pin,'exact qualified numerical core closure '+name)
    return True

def source_guard(ctx=None,root=ROOT):
    ctx=context(os.environ)if ctx is None else ctx
    require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()==ctx['source'],'actual exact checkout')
    raw=q.regular(root,MANIFEST).read_bytes();require(raw==subprocess.check_output(['git','show',ctx['source']+':'+MANIFEST],cwd=root),'immutable current manifest')
    m=q.decode(raw);require(m['schema']=='cdr-via2-m3-fresh-rc-adapter-pins-v1','exact new source manifest')
    for name,pin in m['files'].items():
        actual=q.file_pin(q.regular(root,name));require(actual['sha256']==pin['sha256']and('bytes'not in pin or actual['bytes']==pin['bytes']),'protected source changed '+name)
    c=validate_config(q.decode(q.regular(root,CONFIG).read_bytes()))
    require(m['fresh_rc_execution_authorized']is c['fresh_rc_execution_authorized'],'separate authority consistent with manifest')
    p=q.decode(q.regular(root,PRODUCER).read_bytes());producer.metadata(root,p)
    require(p['native_authorization_asserted_by_this_record']is False,'producer evidence grants no execution authority')
    historical_controls(root,c)
    return c,p

def authorize_native(ctx,c):
    validate_config(c)
    require(ctx['mode']=='rc'and ctx['job']=='fresh-rc'and c['fresh_rc_execution_authorized']is True,'separate exact-source fresh RC authority required')

def validate_current_run(ctx,run,jobs):
    require(run['id']==ctx['run_id']and run['head_sha']==ctx['source']and run['head_branch']==BRANCH and run['run_attempt']==1,'actual current run identity')
    require(run['event']=='workflow_dispatch'and run['workflow_id']==382556685 and run['path']==WORKFLOW and run['status']=='in_progress','actual authoritative workflow')
    rows=jobs['jobs'];require(len(rows)==jobs['total_count']==3,'exact source/log/fresh-rc jobs')
    require(all(j['run_id']==ctx['run_id']and j['run_attempt']==1 and j['head_sha']==ctx['source']for j in rows),'every actual job source')
    by={j['name']:j for j in rows};require(set(by)=={'source-controls','preserve-job-log','fresh-rc'},'exact job names')
    for name in('source-controls','preserve-job-log'):
        j=by[name];require(j['status']=='completed'and j['conclusion']=='success','same-run prerequisite success')
        require(all(s['conclusion']in('success','skipped')for s in j['steps'])and any(s['conclusion']=='success'for s in j['steps']),'successful prerequisite steps')
    require(by['fresh-rc']['status']=='in_progress'and by['fresh-rc']['conclusion']is None,'single current fresh-rc job')
    return dict(current_source=ctx['source'],run_id=ctx['run_id'],source_job=by['source-controls']['id'],log_job=by['preserve-job-log']['id'],candidate_job=by['fresh-rc']['id'])

def read_source_log(job):
    require(type(job)is int and job>0,'source job id')
    return subprocess.check_output(['gh','api','--allow-escape-sequences','repos/'+q.REPOSITORY+'/actions/jobs/'+str(job)+'/logs'])

def bind_controls(raw,ctx,c):
    r=q.decode(raw)
    require(r['status']=='PASS_CURRENT_VIA2_M3_FRESH_RC_SOURCE_CONTROLS'and r['passed']is True,'actual integrated source controls')
    require(r['context']==dict(source=ctx['source'],run_id=ctx['run_id'],attempt=1),'same exact source and run')
    required=c['source_control_requirements'];require(set(r['controls'])==set(required),'complete integrated control groups')
    for name,count in required.items():require(type(r['controls'][name])is int and r['controls'][name]>=count,'required source-control group '+name)
    require(r['native_payload_acquired']is r['RC_executed']is r['simulation_executed']is r['layout_regenerated']is False,'source controls cannot claim native execution')
    return q.fingerprint(raw)

def authenticate_source_log(ctx,log,c):
    require(type(log)is bytes and len(log)>0,'complete raw source job log')
    expected={'fresh-rc-controls.stdout','fresh-rc-controls.stderr','fresh-rc-controls/result.json'}
    indexes={};chunks={}
    for line in log.decode('utf-8',errors='strict').splitlines():
        found=re.search(r'VIA2_M3_RC_CONTROL_INDEX (\{.*\})\s*$',line)
        if found:
            row=q.decode(found[1].encode());name=row['path']
            require(name in expected and name not in indexes,'unique exact source index')
            require(type(row['bytes'])is int and row['bytes']>=0 and type(row['chunks'])is int and row['chunks']>0 and re.fullmatch('[0-9a-f]{64}',row['sha256']),'source index fields')
            indexes[name]=row
        found=re.search(r'VIA2_M3_RC_CONTROL_CHUNK (\{.*\})\s*$',line)
        if found:
            row=q.decode(found[1].encode());name=row['path'];i=row['index']
            require(name in expected and type(i)is int and i>=0 and i not in chunks.setdefault(name,{}),'unique exact source chunk')
            chunks[name][i]=base64.b64decode(row['base64'],validate=True)
    require(set(indexes)==set(chunks)==expected,'three complete emitted control records')
    records={}
    for name,row in indexes.items():
        require(set(chunks[name])==set(range(row['chunks'])),'all source chunks')
        raw=b''.join(chunks[name][i]for i in range(row['chunks']))
        require(q.fingerprint(raw)==dict(bytes=row['bytes'],sha256=row['sha256']),'actual emitted source bytes');records[name]=raw
    result=records['fresh-rc-controls/result.json'];proof=bind_controls(result,ctx,c)
    return records,dict(source=ctx['source'],run_id=ctx['run_id'],attempt=1,full_raw_log=q.fingerprint(log),records={n:q.fingerprint(b)for n,b in records.items()},controls=proof,native_acquisition=False)

def native_preflight(path,ctx,c,p,root=ROOT):
    authorize_native(ctx,c);value=q.decode(q.regular(path.parent,path.name).read_bytes())
    require(path.parent==OUT and value['context']==ctx and value['fresh_rc_execution_authorized']is True,'actual fresh RC preflight context')
    require(value['generation_authorized']is value['electrical_simulation_authorized']is False,'bounded extraction only')
    require(value['restore_root']==str(ORIGINAL)and value['current_view_root']==producer.CURRENT_ROOT,'original absolute report roots preserved')
    require(bind_controls(q.regular(OUT,'same-source-controls.json').read_bytes(),ctx,c)==value['source_controls'],'same-source prerequisite controls')
    require(validate_current_run(ctx,q.decode(q.regular(OUT,'current-run.json').read_bytes()),q.decode(q.regular(OUT,'current-jobs.json').read_bytes()))==value['current_run_binding'],'actual authoritative current jobs')
    reserved=q.decode(q.regular(OUT,'reservation-original.json').read_bytes())
    require(q.reservation(ctx,reserved,q.decode(q.regular(OUT,'result-release-empty.json').read_bytes()),q.decode(q.regular(OUT,'result-tag.json').read_bytes()))==value['reservation_binding'],'independent empty exact-source destination')
    original=producer.metadata(root,p)
    live=producer.validate_live(p,original,*[q.decode(q.regular(OUT,'view-producer-'+n+'.json').read_bytes())for n in('run','jobs','release','ref')])
    require(live==value['producer_binding'],'original current view live binding')
    full=q.decode(q.regular(OUT,'view-complete-input-census.json').read_bytes())
    require(producer.validate_restored(ORIGINAL,p,full,original)==value['restore_proof'],'entire original665/current78 byte binding')
    require(value['original_absolute_results_rewritten']is False and value['historical_producer_context_substituted']is False,'no rewritten or substituted producer context')
    return value

if __name__=='__main__':
    raise SystemExit('Admission library only; no standalone native execution authority')
