#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Source-bound canonical-view admission; no RC, waves, or layout regeneration."""
import base64,hashlib,json,os,re,subprocess
from pathlib import Path
import cloud_cdr_current_eight_drain_wave_replay as q
ROOT=Path(__file__).resolve().parents[1]
BRANCH='codex/cdr-via2-m3-canonical-view-adapter'
CONFIG='scripts/cdr-via2-m3-canonical-view-adapter-inputs.json'
MANIFEST='scripts/cdr-via2-m3-canonical-view-adapter-pins.json'
GROUP='cdr-via2-m3-canonical-view-nominal_late'
WORKFLOW='.github/workflows/cloud-evidence-summary.yml'
require=q.require;encode=q.encode
FLAGS=dict(accepted=False,physical_acceptance=False,electrical_accepted=False,full_phy_accepted=False,timing_accepted=False,qualified_pex=False,causality_proven=False,new_simulation=False,new_RC_executed=False,layout_regenerated=False)
def context(env):
    require(env.get('GITHUB_ACTIONS')=='true'and env.get('RUNNER_ENVIRONMENT')=='github-hosted'and env.get('RUNNER_OS')=='Linux','hosted Linux only')
    require(env.get('GITHUB_REPOSITORY')==q.REPOSITORY and env.get('GITHUB_EVENT_NAME')=='workflow_dispatch','manual exact repository')
    require(env.get('GITHUB_REF')=='refs/heads/'+BRANCH and env.get('GITHUB_WORKFLOW_REF')==q.REPOSITORY+'/'+WORKFLOW+'@refs/heads/'+BRANCH,'exact branch/workflow')
    require(env.get('GITHUB_RUN_ATTEMPT')=='1','no rerun')
    head=env.get('GITHUB_SHA','');run=env.get('GITHUB_RUN_ID','')
    require(re.fullmatch('[0-9a-f]{40}',head)and re.fullmatch('[1-9][0-9]*',run),'source/run')
    require(env.get('APPROVED_SOURCE')==head,'explicit current source')
    mode=env.get('REQUESTED_MODE');job=env.get('GITHUB_JOB')
    require((mode,job)in(('controls','source-controls'),('view','source-controls'),('view','canonical-view')),'bounded mode/job')
    return dict(source=head,run_id=int(run),attempt=1,mode=mode,job=job,case='nominal_late',group=GROUP,token=run+'-1')

def validate_config(c):
    require(c['schema']=='cdr-via2-m3-canonical-view-adapter-v1'and c['branch']==BRANCH and c['repository']==q.REPOSITORY,'exact view adapter')
    require(c['workflow']==WORKFLOW and c['workflow_id']==382556685 and c['case']=='nominal_late','exact workflow/case')
    require(c['source_controls_authorized']is True and c['all_acceptance_false']is True and c['native_payloads_cloud_only']is True,'bounded cloud scope')
    require(type(c['view_execution_authorized'])is bool,'explicit typed view authority')
    require(c['generation_authorized']is c['fresh_rc_authorized']is c['electrical_simulation_authorized']is False,'no regeneration RC or waves')
    require(c['candidate']==dict(bytes=998644,sha256='42ed5bcd567518786b718248947771172e9f5cc419d0aaa8fc8c49d8cfa4e876'),'actual candidate identity')
    require(c['invariants']==dict(devices=500,terminals=1446,ports=25,added_records=16),'complete immutable observable scope')
    require(set(c['producers'])=={'reference','physical'},'exact two producers')
    for key,run,source,count,jobs in(('reference',41206809668,'de79f76bc60b3ef2b06c88736f4f3d0ee3491257',330,4),('physical',41238994098,'0b1ec86b35f8cb98928a5687f007a7ccd676f620',172,3)):
        p=c['producers'][key]
        require(p['key']==key and p['run_id']==run and p['source']==source and p['attempt']==1,'real terminal producer identity')
        require(p['expected_members']==len(p['complete_members'])==count and p['expected_jobs']==jobs and len(p['assets'])==3,'complete immutable producer census')
    g=c['generation_proof'];require(g['producer_run']==41235314835 and g['producer_source']=='db7077a9495229ef444d1155aed687cfe374f9ae','original failed generation producer retained')
    require(g['record_pin']==dict(bytes=4721,sha256='e6e1a9278ccc6b1f76972985c11727c4f2a887d4806102d43ef234c85bc2deac'),'actual sixteen additions record')
    return c

def complete_proof(prefix,want,record_key,root):
    raw=q.regular(root,prefix+'receipt.json').read_bytes();require(q.fingerprint(raw)['sha256']==want,'exact complete proof receipt')
    receipt=q.decode(raw);require(record_key in('files','records')and receipt[record_key],'complete proof map')
    for name,pin in receipt[record_key].items():require(q.file_pin(q.regular(root,prefix+name))==pin,'complete historical proof bytes '+name)
    return receipt

def source_guard(ctx=None,root=ROOT):
    ctx=context(os.environ)if ctx is None else ctx
    require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()==ctx['source'],'exact actual checkout')
    raw=q.regular(root,MANIFEST).read_bytes();require(raw==subprocess.check_output(['git','show',ctx['source']+':'+MANIFEST],cwd=root),'immutable current source manifest')
    m=q.decode(raw);require(m['schema']=='cdr-via2-m3-canonical-view-adapter-pins-v1','source manifest schema')
    for name,pin in m['files'].items():
        actual=q.file_pin(q.regular(root,name));require(actual['sha256']==pin['sha256']and('bytes'not in pin or actual['bytes']==pin['bytes']),'protected source changed '+name)
    c=validate_config(q.decode(q.regular(root,CONFIG).read_bytes()))
    require(m['view_execution_authorized']is c['view_execution_authorized'],'consistent separate view authority')
    for key,p in c['producers'].items():
        r=complete_proof(p['proof_prefix'],p['receipt_sha256'],p['receipt_key'],root)
        require(r.get('run_id',r.get('run'))==p['run_id']and r['source']==p['source']and r.get('run_conclusion',r.get('workflow_conclusion'))=='success','actual successful producer proof')
        metadata(c,key,root)
    g=c['generation_proof'];r=complete_proof(g['prefix'],g['receipt_sha256'],'records',root)
    require(r['run_id']==g['producer_run']and r['source']==g['producer_source']and r['run_conclusion']=='failure','original failed producer remains failed')
    raw=q.regular(root,g['prefix']+g['record']).read_bytes();require(q.fingerprint(raw)==g['record_pin'],'actual generation bytes')
    gen=q.decode(raw);require(gen['geometry_generated']is True and gen['original_full_rails_unchanged']is True and gen['proof']['structural_reversal_exact']is True,'real reversible sixteen additions')
    require(len(gen['proof']['added_records'])==16 and gen['proof']['candidate']==c['candidate'],'same actual candidate')
    return c

def authorize_native(ctx,c):
    validate_config(c)
    require(ctx['mode']=='view'and ctx['job']=='canonical-view'and c['view_execution_authorized']is True,'separate exact-source actual view authority required')

def metadata(c,key,root=ROOT):
    p=c['producers'][key];values=[]
    for kind in('index','parts'):
        raw=q.regular(root,p[kind+'_path']).read_bytes();require(q.fingerprint(raw)['sha256']==p[kind+'_sha256'],'actual published '+kind+' bytes');values.append(q.decode(raw))
    index,parts=values
    require(index['context']==p['index_context']and index['files']==p['complete_members'],'complete exact producer member map and context')
    require(parts['source_directory']==p['archive_root']and parts['bytes']==p['archive_bytes']and parts['sha256']==p['archive_sha256'],'actual native archive identity')
    require(len(parts['parts'])==1 and parts['parts'][0]['index']==0 and parts['parts'][0]['bytes']==parts['bytes']and parts['parts'][0]['sha256']==parts['sha256'],'single complete original native part')
    require(parts['verification']==dict(parts=1,bytes=parts['bytes'],sha256=parts['sha256'],all_parts_and_combined_bytes_verified=True),'producer part verification record')
    require({a['name']for a in p['assets']}=={'complete-output-index.json',Path(p['parts_path']).name,parts['parts'][0]['name']},'complete three-asset original publication')
    return index,parts

def validate_producer(c,key,run,jobs,release,ref,root=ROOT):
    p=c['producers'][key];prefix=p['proof_prefix']
    historical_run=q.decode(q.regular(root,prefix+'run.json').read_bytes());historical_jobs=q.decode(q.regular(root,prefix+'jobs.json').read_bytes())
    for field in('id','head_sha','head_branch','run_attempt','event','workflow_id','path','status','conclusion'):require(run[field]==historical_run[field],'immutable original run '+field)
    require(run['id']==p['run_id']and run['head_sha']==p['source']and run['run_attempt']==1 and run['status']=='completed'and run['conclusion']=='success','actual successful source-bound run')
    require(jobs['total_count']==len(jobs['jobs'])==len(historical_jobs['jobs'])==p['expected_jobs'],'complete original jobs')
    old={j['id']:j for j in historical_jobs['jobs']};require({j['id']for j in jobs['jobs']}==set(old),'original job identities')
    for j in jobs['jobs']:
        for field in('id','run_id','run_attempt','head_sha','name','status','conclusion','steps'):require(j[field]==old[j['id']][field],'actual original terminal job '+field)
        require(j['conclusion']=='success'and all(s['conclusion']in('success','skipped')for s in j['steps']),'actual successful original steps')
    assets=q.release_binding(release,ref,p['tag'],p['source']);require(release['id']==p['release_id']and set(assets)=={a['name']for a in p['assets']},'complete exact-source original release')
    for pin in p['assets']:
        row=assets[pin['name']];require(row['id']==pin['id']and row['size']==pin['bytes']and row['digest']=='sha256:'+pin['sha256'],'actual original asset bytes')
        for field in('state','content_type','created_at','updated_at'):require(row[field]==pin[field],'immutable original asset '+field)
    return dict(key=key,run_id=p['run_id'],source=p['source'],attempt=1,release_id=p['release_id'],complete_jobs=p['expected_jobs'],complete_members=p['expected_members'],conclusion='success')

def validate_restored(c,key,restore,full,root=ROOT):
    index,parts=metadata(c,key,root);p=c['producers'][key]
    require(restore.is_absolute()and restore.resolve()==restore and not restore.is_symlink(),'owned exact restore directory')
    require(full['every_member_authenticated']is True and full['full_member_count']==p['expected_members']and full['full_members']==index['files']and full['selected']==index['files'],'every original native member authenticated')
    for name,pin in index['files'].items():require(q.file_pin(q.regular(restore,name))==pin,'retained complete producer bytes')
    result=dict(key=key,member_count=p['expected_members'],all_members_authenticated=True,original_result_rewritten=False)
    if key=='physical':
        raw=q.regular(restore,'native/physical/result.json').read_bytes();report=q.decode(raw)
        require(report['status']=='PASS_NATIVE_PDK_CDR_PD500_DRC_LVS_AND_FAULT_CONTROLS','actual full physical result')
        s=report['steps'];require(s['drc']['status']=='PASS'and s['drc']['measurement']['category_count']==560 and s['drc']['measurement']['markers']==0,'all560 DRC zero markers')
        for mode in('lvs','lvs_flat'):require(s[mode]['status']=='PASS'and s[mode]['audit']['status']=='PASS within comparison scope'and sum(s[mode]['native_primitive_census'].values())==500,'actual deep and flat500 LVS')
        faults=[n for n in s if n not in('drc','lvs','lvs_flat')];require(len(faults)==13 and all(s[n]['status']=='REJECTED_EXPECTED_FAULT'for n in faults),'all13 actual expected faults')
        layout=q.decode(q.regular(restore,'native/layout/result.json').read_bytes())
        original=q.decode(q.regular(root,c['generation_proof']['prefix']+'readback/native/layout/result.json').read_bytes())
        require(layout==original and len(layout['inputs'])==20 and len(layout['ports'])==25,'original absolute layout input record retained without rewriting')
        require(q.file_pin(q.regular(restore,'native/layout/nssoc_cdr_pd500_resistor_v59.gds'))==c['candidate'],'same actual generated GDS')
        result.update(physical_report=q.fingerprint(raw),absolute_input_record_retained=True,candidate=c['candidate'])
    return result

def validate_current_run(ctx,run,jobs):
    require(run['id']==ctx['run_id']and run['head_sha']==ctx['source']and run['head_branch']==BRANCH and run['run_attempt']==1,'actual current run identity')
    require(run['event']=='workflow_dispatch'and run['workflow_id']==382556685 and run['path']==WORKFLOW and run['status']=='in_progress','actual authoritative workflow')
    rows=jobs['jobs'];require(len(rows)==jobs['total_count']==3,'exact source/log/canonical-view jobs')
    require(all(j['run_id']==ctx['run_id']and j['run_attempt']==1 and j['head_sha']==ctx['source']for j in rows),'every actual job source')
    by={j['name']:j for j in rows};require(set(by)=={'source-controls','preserve-job-log','canonical-view'},'exact job names')
    for name in('source-controls','preserve-job-log'):
        j=by[name];require(j['status']=='completed'and j['conclusion']=='success','same-run prerequisite success')
        require(all(s['conclusion']in('success','skipped')for s in j['steps'])and any(s['conclusion']=='success'for s in j['steps']),'successful prerequisite steps')
    require(by['canonical-view']['status']=='in_progress'and by['canonical-view']['conclusion']is None,'single current canonical-view job')
    return dict(current_source=ctx['source'],run_id=ctx['run_id'],source_job=by['source-controls']['id'],log_job=by['preserve-job-log']['id'],candidate_job=by['canonical-view']['id'])

def read_source_log(job):
    require(type(job)is int and job>0,'source job id')
    return subprocess.check_output(['gh','api','--allow-escape-sequences','repos/'+q.REPOSITORY+'/actions/jobs/'+str(job)+'/logs'])

def bind_controls(raw,ctx):
    r=q.decode(raw)
    require(r['status']=='PASS_CANONICAL_VIEW_ADAPTER_SOURCE_CONTROLS'and r['passed']is True,'complete actual adapter controls')
    require(r['context']==dict(source=ctx['source'],run_id=ctx['run_id'],attempt=1),'same exact source/run controls')
    require(r['producer_refusals']>=24 and r['restore_refusals']>=8 and r['context_refusals']>=8 and r['source_log_refusals']>=14,'complete source admission refusals')
    require(r['lifecycle_cases']==4 and r['publication_cases']==7 and r['publication_refusals']==33,'complete unchanged lifecycle/publication controls')
    require(r['core_controls_passed']is True and r['core_test_count']>=59 and r['seam_test_count']>=18,'complete hosted core and projection controls')
    require(r['native_payload_acquired']is r['actual_view_executed']is r['RC_executed']is r['simulation_executed']is False,'source controls never native evidence')
    return q.fingerprint(raw)

def authenticate_source_log(ctx,log):
    require(type(log)is bytes and len(log)>0,'complete raw source job log')
    expected={'canonical-view-controls.stdout','canonical-view-controls.stderr','canonical-view-controls/result.json'}
    indexes={};chunks={}
    for line in log.decode('utf-8',errors='strict').splitlines():
        found=re.search(r'VIA2_M3_VIEW_CONTROL_INDEX (\{.*\})\s*$',line)
        if found:
            row=q.decode(found[1].encode());name=row['path']
            require(name in expected and name not in indexes,'unique exact source index')
            require(type(row['bytes'])is int and row['bytes']>=0 and type(row['chunks'])is int and row['chunks']>0 and re.fullmatch('[0-9a-f]{64}',row['sha256']),'source index fields')
            indexes[name]=row
        found=re.search(r'VIA2_M3_VIEW_CONTROL_CHUNK (\{.*\})\s*$',line)
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
    result=records['canonical-view-controls/result.json'];proof=bind_controls(result,ctx)
    return records,dict(source=ctx['source'],run_id=ctx['run_id'],attempt=1,full_raw_log=q.fingerprint(log),records={n:q.fingerprint(b)for n,b in records.items()},controls=proof,native_acquisition=False)

def native_preflight(path,ctx,c,reference,physical,root=ROOT):
    authorize_native(ctx,c);value=q.decode(q.regular(path.parent,path.name).read_bytes())
    require(value['context']==ctx and value['view_execution_authorized']is True and value['generation_authorized']is False,'actual source-bound view-only preflight')
    require(value['restore_roots']==dict(reference=str(reference),physical=str(physical)),'exact authenticated input roots')
    evidence=path.parent
    require(reference==evidence/'inputs/reference'and physical==evidence/'inputs/physical','owned native input locations')
    require(bind_controls(q.regular(evidence,'same-source-controls.json').read_bytes(),ctx)==value['source_controls'],'same current source controls')
    require(validate_current_run(ctx,q.decode(q.regular(evidence,'current-run.json').read_bytes()),q.decode(q.regular(evidence,'current-jobs.json').read_bytes()))==value['current_run_binding'],'actual current job binding')
    reserved=q.decode(q.regular(evidence,'reservation-original.json').read_bytes())
    require(q.reservation(ctx,reserved,q.decode(q.regular(evidence,'result-release-empty.json').read_bytes()),q.decode(q.regular(evidence,'result-tag.json').read_bytes()))==value['reservation_binding'],'independent empty exact-source destination')
    for key,restore in(('reference',reference),('physical',physical)):
        producer=validate_producer(c,key,*[q.decode(q.regular(evidence,key+'-producer-'+n+'.json').read_bytes())for n in('run','jobs','release','ref')],root=root)
        require(producer==value['producer_bindings'][key],'actual original producer identity')
        full=q.decode(q.regular(evidence,key+'-complete-input-census.json').read_bytes())
        require(validate_restored(c,key,restore,full,root)==value['restore_proofs'][key],'full immutable input byte binding')
    require(value['original_absolute_results_rewritten']is False and value['fresh_RC_executed']is False,'no rewritten original proofs or RC authority')
    return value
