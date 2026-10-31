#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Independent current-source admission for one Via2/M3 generation and physical trial."""
import base64,hashlib,json,os,re,subprocess
from pathlib import Path
import cloud_cdr_current_eight_drain_wave_replay as q
import cdr_current_via2_m3_access_candidate as original
ROOT=Path(__file__).resolve().parents[1]
BRANCH='codex/cdr-current-via2-m3-physical-adapter'
CONFIG='scripts/cdr-current-via2-m3-physical-inputs.json'
MANIFEST='scripts/cdr-current-via2-m3-physical-source-pins.json'
GROUP='cdr-current-via2-m3-physical-nominal_late'
WORKFLOW='.github/workflows/cloud-evidence-summary.yml'
FLAGS=dict(accepted=False,physical_acceptance=False,electrical_accepted=False,full_phy_accepted=False,
 timing_accepted=False,qualified_pex=False,causality_proven=False,new_simulation=False)
require=q.require
encode=q.encode

def context(env):
    require(env.get('GITHUB_ACTIONS')=='true'and env.get('RUNNER_ENVIRONMENT')=='github-hosted'and env.get('RUNNER_OS')=='Linux','hosted Linux only')
    require(env.get('GITHUB_REPOSITORY')==q.REPOSITORY and env.get('GITHUB_EVENT_NAME')=='workflow_dispatch','manual exact repository')
    require(env.get('GITHUB_REF')=='refs/heads/'+BRANCH and env.get('GITHUB_WORKFLOW_REF')==q.REPOSITORY+'/'+WORKFLOW+'@refs/heads/'+BRANCH,'exact branch/workflow')
    require(env.get('GITHUB_RUN_ATTEMPT')=='1','no rerun')
    head=env.get('GITHUB_SHA','');run=env.get('GITHUB_RUN_ID','')
    require(re.fullmatch('[0-9a-f]{40}',head)and re.fullmatch('[1-9][0-9]*',run),'source/run')
    require(env.get('APPROVED_SOURCE')==head,'explicit current source')
    mode=env.get('REQUESTED_MODE');job=env.get('GITHUB_JOB')
    require((mode,job)in(('controls','source-controls'),('candidate','source-controls'),('candidate','candidate')),'bounded mode/job')
    return dict(source=head,run_id=int(run),attempt=1,mode=mode,job=job,case='nominal_late',group=GROUP,token=run+'-1')

def validate_config(c,plan,geometry,prior):
    require(c['schema']=='cdr-current-via2-m3-physical-adapter-v1'and c['branch']==BRANCH and c['repository']==q.REPOSITORY,'adapter identity')
    require(c['workflow']==WORKFLOW and c['workflow_id']==382556685 and c['case']=='nominal_late','exact registered workflow/case')
    require(c['source_controls_authorized']is True and c['all_acceptance_false']is True and c['native_payloads_cloud_only']is True,'scope')
    for k in('generation_authorized','physical_verification_authorized'):require(type(c[k])is bool,'typed authority')
    require(c['generation_authorized']is c['physical_verification_authorized'],'generation and full physical admission coupled')
    require(c['fresh_rc_authorized']is False and c['electrical_simulation_authorized']is False,'no RC or new waves')
    original.validate_plan(plan)
    require(c['candidate_source']=='f2220e2fed3e21a8138b58f8be3c7a62fdbde1d2'and c['candidate_control_run']==41232355399,'tested original candidate')
    require(c['expected_native_member_count']==2991 and c['original_producer']==prior['producer']==geometry['original_producer'],'exact current producer')
    support=c['support_members'];base='native/current-mim-bundle/canonical-current-view/parent/layout/'
    require(support==dict(lef=base+'nssoc_cdr_pd500_resistor_v59.lef',schematic=base+'schematic.cir',layout_result=base+'result.json'),'three exact original physical references')
    require(len(c['selected'])==len(c['selected_bytes'])==20 and set(c['selected'])==set(geometry['selected'])|set(support.values()),'exact17plus3 inputs')
    require({n:c['selected'][n]for n in geometry['selected']}==geometry['selected']and{n:c['selected_bytes'][n]for n in geometry['selected']}==geometry['selected_bytes'],'original17 byte pins unchanged')
    require(all(re.fullmatch('[0-9a-f]{64}',h)and type(c['selected_bytes'][n])is int and c['selected_bytes'][n]>0 for n,h in c['selected'].items()),'complete20 byte pins')
    require(c['full_physical']==dict(categories=560,devices=500,fault_controls=13,deep_and_flat=True,reference_variant='cd_shunt'),'unchanged full physical gates')
    require(c['appimage']==geometry['appimage'],'original immutable tool runtime')
    historical=c['prior_adapter_controls']
    require(historical['run_id']==41233939886 and historical['source']=='77f23e8cb2627ffb62281dd8bea1c7005db1acf5' and historical['records']==25,'actual reviewed adapter controls')
    return True

def source_guard(ctx=None,root=ROOT):
    ctx=context(os.environ)if ctx is None else ctx
    require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()==ctx['source'],'exact checkout')
    raw=q.regular(root,MANIFEST).read_bytes()
    require(raw==subprocess.check_output(['git','show',ctx['source']+':'+MANIFEST],cwd=root),'immutable current manifest')
    m=q.decode(raw);require(m['schema']=='cdr-current-via2-m3-physical-source-pins-v1','source manifest identity')
    for name,pin in m['files'].items():
        actual=q.file_pin(q.regular(root,name));require(actual['sha256']==pin['sha256']and('bytes'not in pin or actual['bytes']==pin['bytes']),'protected source changed: '+name)
    c=q.decode(q.regular(root,CONFIG).read_bytes());plan=q.decode(q.regular(root,c['candidate_plan']).read_bytes())
    geometry=q.decode(q.regular(root,c['geometry_config']).read_bytes());prior=q.source_guard(root)
    require(q.file_pin(q.regular(root,c['candidate_plan']))['sha256']==c['candidate_plan_sha256'],'tested candidate plan')
    require(q.file_pin(q.regular(root,c['geometry_config']))['sha256']==c['geometry_config_sha256'],'qualified geometry config')
    receipt=q.regular(root,c['candidate_control_receipt']).read_bytes()
    require(q.fingerprint(receipt)['sha256']==c['candidate_control_receipt_sha256'],'original hosted source controls proof')
    r=q.decode(receipt);require(r['source']==c['candidate_source']and r['run_id']==c['candidate_control_run']and r['run_conclusion']=='success'and r['counts']==dict(cases=30,positive=9,refusals=21),'original30actual controls')
    validate_config(c,plan,geometry,prior)
    historical=c['prior_adapter_controls'];receipt_path=q.regular(root,historical['receipt']);historical_raw=receipt_path.read_bytes()
    require(q.fingerprint(historical_raw)['sha256']==historical['sha256'],'full original adapter controls receipt')
    h=q.decode(historical_raw);require(h['source']==historical['source']and h['run_id']==historical['run_id']and h['run_conclusion']=='success'and len(h['records'])==historical['records'],'actual prior adapter controls identity')
    require(h['counts']==dict(original_geometry=dict(cases=30,positive=9,refusals=21),admission_refusals=53,native_preflight_refusals=7,lifecycle_cases=4,publication_positive=7,publication_refusals=33),'original complete actual control counts')
    for name,pin in h['records'].items():require(q.file_pin(q.regular(receipt_path.parent,name))==pin,'complete historical control proof bytes')
    raw_census=q.regular(root,c['input_census']).read_bytes();require(q.fingerprint(raw_census)['sha256']==c['input_census_sha256'],'actual complete original census proof')
    census=q.decode(raw_census);require(census['every_member_authenticated']is True and census['full_member_count']==2991,'authentic entire original native member proof')
    require({n:census['full_members'][n]for n in c['selected']}=={n:dict(bytes=c['selected_bytes'][n],sha256=h)for n,h in c['selected'].items()},'exact20 input sizes and hashes from actual full member proof')
    require(m['generation_authorized']is c['generation_authorized']and m['physical_verification_authorized']is c['physical_verification_authorized'],'explicit adapter authority consistent')
    return c

def authorize_native(ctx,c):
    require(ctx['mode']=='candidate'and ctx['job']=='candidate','native work only in its bounded current job')
    require(c['generation_authorized']is True and c['physical_verification_authorized']is True,'native generation/full physical authority disabled')
    require(c['fresh_rc_authorized']is False and c['electrical_simulation_authorized']is False,'no extraction or simulation authority')
    return True

def bind_controls(raw,ctx):
    r=q.decode(raw)
    require(r['status']=='PASS_CURRENT_VIA2_M3_PHYSICAL_ADAPTER_SOURCE_CONTROLS'and r['passed']is True,'complete actual controls')
    require(r['context']==dict(source=ctx['source'],run_id=ctx['run_id'],attempt=1),'same-source same-run control context')
    require(r['original_geometry_controls']==dict(cases=30,positive=9,refusals=21),'actual original Pya controls')
    require(r['native_payload_acquired']is False and r['actual_candidate_generated']is False,'source controls scope')
    require(r['admission_refusals']>=40 and r['native_preflight_refusals']>=7 and r['lifecycle_cases']==4 and r['publication_cases']==7 and r['publication_refusals']==33,'complete source controls census')
    return q.fingerprint(raw)

def validate_current_run(ctx,run,jobs):
    require(run['id']==ctx['run_id']and run['head_sha']==ctx['source']and run['head_branch']==BRANCH and run['run_attempt']==1,'actual current run identity')
    require(run['event']=='workflow_dispatch'and run['workflow_id']==382556685 and run['path']==WORKFLOW and run['status']=='in_progress','actual authoritative workflow')
    rows=jobs['jobs'];require(len(rows)==jobs['total_count']==3,'exact source/log/candidate jobs')
    require(all(j['run_id']==ctx['run_id']and j['run_attempt']==1 and j['head_sha']==ctx['source']for j in rows),'every actual job source')
    by={j['name']:j for j in rows};require(set(by)=={'source-controls','preserve-job-log','candidate'},'exact job names')
    for name in('source-controls','preserve-job-log'):
        j=by[name];require(j['status']=='completed'and j['conclusion']=='success','same-run prerequisite success')
        require(all(s['conclusion']in('success','skipped')for s in j['steps'])and any(s['conclusion']=='success'for s in j['steps']),'successful prerequisite steps')
    require(by['candidate']['status']=='in_progress'and by['candidate']['conclusion']is None,'single current candidate job')
    return dict(current_source=ctx['source'],run_id=ctx['run_id'],source_job=by['source-controls']['id'],log_job=by['preserve-job-log']['id'],candidate_job=by['candidate']['id'])

def native_preflight(path,ctx,c,selected,root=ROOT):
    authorize_native(ctx,c);p=q.decode(q.regular(path.parent,path.name).read_bytes())
    require(p['context']==ctx and p['generation_authorized']is True and p['physical_verification_authorized']is True,'current explicit native preflight')
    require(p['all2991_authenticated']is True and p['selected']=={n:dict(bytes=c['selected_bytes'][n],sha256=h)for n,h in c['selected'].items()},'complete20 input preflight')
    require(p['selected_root']==str(selected.resolve()),'owned selected root')
    for n,pin in p['selected'].items():require(q.file_pin(q.regular(selected,n))==pin,'actual selected native bytes')
    evidence=path.parent
    controls=q.regular(evidence,'same-source-controls.json').read_bytes();require(bind_controls(controls,ctx)==p['controls'],'real current control bytes')
    require(validate_current_run(ctx,q.decode(q.regular(evidence,'current-run.json').read_bytes()),q.decode(q.regular(evidence,'current-jobs.json').read_bytes()))==p['current_run_binding'],'actual current job binding')
    prior=q.source_guard(root);case=c['case']
    producer=q.validate_current_case_live(prior,case,*[q.decode(q.regular(evidence,'producer-'+n+'.json').read_bytes())for n in('run','jobs','release','ref')])
    require(producer==p['producer_binding'],'actual immutable producer source')
    reserved=q.decode(q.regular(evidence,'reservation-original.json').read_bytes())
    proof=q.reservation(ctx,reserved,q.decode(q.regular(evidence,'result-release-empty.json').read_bytes()),q.decode(q.regular(evidence,'result-tag.json').read_bytes()))
    require(proof==p['reservation_binding'],'independent empty exact-source reservation')
    return p

def read_source_log(job):
    require(type(job)is int and job>0,'source job id')
    return subprocess.check_output(['gh','api','--allow-escape-sequences','repos/'+q.REPOSITORY+'/actions/jobs/'+str(job)+'/logs'])

def authenticate_source_log(ctx,log):
    require(type(log)is bytes and len(log)>0,'complete raw source job log')
    expected={'via2-m3-adapter-controls.stdout','via2-m3-adapter-controls.stderr','current-cdr-runtime-policy.json','cdr-via2-m3-adapter-controls/result.json'}
    indexes={};chunks={}
    for line in log.decode('utf-8',errors='strict').splitlines():
        found=re.search(r'VIA2_M3_ADAPTER_CONTROL_INDEX (\{.*\})\s*$',line)
        if found:
            row=q.decode(found[1].encode());name=row['path']
            require(name in expected and name not in indexes,'unique exact source index')
            require(type(row['bytes'])is int and row['bytes']>=0 and type(row['chunks'])is int and row['chunks']>0 and re.fullmatch('[0-9a-f]{64}',row['sha256']),'source index fields')
            indexes[name]=row
        found=re.search(r'VIA2_M3_ADAPTER_CONTROL_CHUNK (\{.*\})\s*$',line)
        if found:
            row=q.decode(found[1].encode());name=row['path'];i=row['index']
            require(name in expected and type(i)is int and i>=0 and i not in chunks.setdefault(name,{}),'unique exact source chunk')
            chunks[name][i]=base64.b64decode(row['base64'],validate=True)
    require(set(indexes)==set(chunks)==expected,'four complete emitted control records')
    records={}
    for name,row in indexes.items():
        require(set(chunks[name])==set(range(row['chunks'])),'all source chunks')
        raw=b''.join(chunks[name][i]for i in range(row['chunks']))
        require(q.fingerprint(raw)==dict(bytes=row['bytes'],sha256=row['sha256']),'actual emitted source bytes')
        records[name]=raw
    result=records['cdr-via2-m3-adapter-controls/result.json'];proof=bind_controls(result,ctx)
    policy=q.decode(records['current-cdr-runtime-policy.json'])
    require(policy['source']==ctx['source']and policy['run_id']==ctx['run_id']and policy['attempt']==1 and policy['native_geometry_executed']is False,'source-only runtime fixture policy binding')
    return records,dict(source=ctx['source'],run_id=ctx['run_id'],attempt=1,full_raw_log=q.fingerprint(log),records={n:q.fingerprint(b)for n,b in records.items()},controls=proof,native_acquisition=False)
