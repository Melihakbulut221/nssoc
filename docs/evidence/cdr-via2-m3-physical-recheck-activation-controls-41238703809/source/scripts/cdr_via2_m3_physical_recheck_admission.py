#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Explicit physical-only reuse admission for a generated but unverified Via2/M3 candidate."""
import base64,hashlib,json,os,re,subprocess
from pathlib import Path
import cloud_cdr_current_eight_drain_wave_replay as q
ROOT=Path(__file__).resolve().parents[1]
BRANCH='codex/cdr-via2-m3-physical-recheck'
CONFIG='scripts/cdr-via2-m3-physical-recheck-inputs.json'
MANIFEST='scripts/cdr-via2-m3-physical-recheck-pins.json'
GROUP='cdr-via2-m3-physical-recheck-nominal_late'
WORKFLOW='.github/workflows/cloud-evidence-summary.yml'
require=q.require;encode=q.encode
FLAGS=dict(accepted=False,physical_acceptance=False,electrical_accepted=False,full_phy_accepted=False,timing_accepted=False,qualified_pex=False,causality_proven=False,new_simulation=False)
def context(env):
    require(env.get('GITHUB_ACTIONS')=='true'and env.get('RUNNER_ENVIRONMENT')=='github-hosted'and env.get('RUNNER_OS')=='Linux','hosted Linux only')
    require(env.get('GITHUB_REPOSITORY')==q.REPOSITORY and env.get('GITHUB_EVENT_NAME')=='workflow_dispatch','manual exact repository')
    require(env.get('GITHUB_REF')=='refs/heads/'+BRANCH and env.get('GITHUB_WORKFLOW_REF')==q.REPOSITORY+'/'+WORKFLOW+'@refs/heads/'+BRANCH,'exact branch/workflow')
    require(env.get('GITHUB_RUN_ATTEMPT')=='1','no rerun')
    head=env.get('GITHUB_SHA','');run=env.get('GITHUB_RUN_ID','')
    require(re.fullmatch('[0-9a-f]{40}',head)and re.fullmatch('[1-9][0-9]*',run),'source/run')
    require(env.get('APPROVED_SOURCE')==head,'explicit current source')
    mode=env.get('REQUESTED_MODE');job=env.get('GITHUB_JOB')
    require((mode,job)in(('controls','source-controls'),('recheck','source-controls'),('recheck','physical-recheck')),'bounded mode/job')
    return dict(source=head,run_id=int(run),attempt=1,mode=mode,job=job,case='nominal_late',group=GROUP,token=run+'-1')
def validate_config(c):
    require(c['schema']=='cdr-via2-m3-physical-recheck-v1'and c['branch']==BRANCH and c['repository']==q.REPOSITORY,'recheck identity')
    require(c['workflow']==WORKFLOW and c['workflow_id']==382556685 and c['case']=='nominal_late','registered workflow/case')
    require(c['source_controls_authorized']is True and c['all_acceptance_false']is True and c['native_payloads_cloud_only']is True,'scope')
    require(type(c['physical_verification_authorized'])is bool,'typed physical authority')
    require(c['generation_authorized']is c['fresh_rc_authorized']is c['electrical_simulation_authorized']is False,'no regeneration RC or waves')
    p=c['producer'];require(p['run_id']==41235314835 and p['source']=='db7077a9495229ef444d1155aed687cfe374f9ae'and p['attempt']==1 and p['run_conclusion']=='failure','real failed producer retained')
    require(p['job_id']==124638024143 and p['release_id']==430145282 and p['expected_members']==99,'exact completed generation producer')
    require(p['restore_root_relative']=='hw/soc/out/cloud-cdr-current-via2-m3-physical'and p['archive_root']=='cloud-cdr-current-via2-m3-physical','authentic original restore location')
    require(c['checker']==dict(bytes=15411,sha256='3ef6c47117a5467acc37ee4ea87af979a75e9be671cbf0a5153307974d082d66'),'unchanged full checker')
    require(c['full_physical']==dict(categories=560,devices=500,fault_controls=13,deep_and_flat=True,reference_variant='cd_shunt'),'unchanged physical gates')
    require(len(p['selected_inputs'])==len(p['frozen_generated_inputs'])==20 and len(p['assets'])==3 and len(p['layout_copy_members'])==4,'complete original source/candidate census')
    h=c['closure_controls'];require(h['run_id']==41237175898 and h['source']=='1c3e1d5c03264647ebeb46881c3af421474b04ee','tested complete source closure')
    require(h['counts']==dict(import_source_refusals=7,runtime_source_refusals=4,external_and_write_barriers=6,observed_repository_reads=118,first_native_boundary_calls=1),'complete original closure counts')
    require(len(c['source_closure']['analog_import_sources'])==7 and sum(x['count']for x in c['source_closure']['runtime_decks'].values())==98,'complete static/native source closure')
    return True

def complete_proof(prefix,want,root):
    raw=q.regular(root,prefix+'receipt.json').read_bytes();require(q.fingerprint(raw)['sha256']==want,'exact proof receipt')
    receipt=q.decode(raw)
    for name,pin in receipt['records'].items():require(q.file_pin(q.regular(root,prefix+name))==pin,'complete historical proof bytes: '+name)
    return receipt

def source_guard(ctx=None,root=ROOT):
    ctx=context(os.environ)if ctx is None else ctx
    require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()==ctx['source'],'exact checkout')
    raw=q.regular(root,MANIFEST).read_bytes();require(raw==subprocess.check_output(['git','show',ctx['source']+':'+MANIFEST],cwd=root),'immutable current manifest')
    m=q.decode(raw);require(m['schema']=='cdr-via2-m3-physical-recheck-pins-v1','current source manifest')
    for name,pin in m['files'].items():
        actual=q.file_pin(q.regular(root,name));require(actual['sha256']==pin['sha256']and('bytes'not in pin or actual['bytes']==pin['bytes']),'protected source changed: '+name)
    c=q.decode(q.regular(root,CONFIG).read_bytes());validate_config(c)
    require(m['physical_verification_authorized']is c['physical_verification_authorized']and m['generation_authorized']is False,'explicit consistent new authority')
    for name,pin in {**c['source_closure']['static_repository_files'],**c['source_closure']['analog_import_sources']}.items():
        require(q.file_pin(q.regular(root,name))==dict(bytes=pin['bytes'],sha256=pin['sha256']),'complete frozen physical source closure')
    p=c['producer'];pr=complete_proof(p['proof_prefix'],p['receipt_sha256'],root)
    require(pr['run_id']==p['run_id']and pr['source']==p['source']and pr['run_conclusion']=='failure','preserved failed producer proof')
    h=c['closure_controls'];hr=complete_proof(h['proof_prefix'],h['receipt_sha256'],root)
    require(hr['run_id']==h['run_id']and hr['source']==h['source']and hr['run_conclusion']=='success'and hr['counts']==h['counts'],'actual complete closure proof')
    index,parts=metadata(c,root);require(len(index['files'])==99,'complete producer99 outputs')
    return c

def authorize_native(ctx,c):
    require(ctx['mode']=='recheck'and ctx['job']=='physical-recheck'and c['physical_verification_authorized']is True,'explicit actual physical-only authority')
    require(c['generation_authorized']is c['fresh_rc_authorized']is c['electrical_simulation_authorized']is False,'no regeneration or electrical authority')

def metadata(c,root=ROOT):
    p=c['producer'];result=[]
    for key in('index','parts'):
        raw=q.regular(root,p[key+'_path']).read_bytes();require(q.fingerprint(raw)['sha256']==p[key+'_sha256'],'actual published '+key+' bytes');result.append(q.decode(raw))
    index,parts=result
    require(index['context']==dict(attempt=1,case='nominal_late',group='cdr-current-via2-m3-physical-nominal_late',run=p['run_id'],source=p['source'],tag=p['tag']),'exact producer index context')
    require(len(index['files'])==99 and {n:v for n,v in index['files'].items()if n.startswith('inputs/')}==p['selected_inputs'],'all20 original inputs from full99 map')
    require(index['files'][p['candidate_member']]==dict(bytes=998644,sha256='42ed5bcd567518786b718248947771172e9f5cc419d0aaa8fc8c49d8cfa4e876'),'actual generated GDS')
    require(index['files'][p['exact_checker_member']]==c['checker'],'actual original checker identity')
    require(parts['source_directory']==p['archive_root']and len(parts['parts'])==1 and parts['bytes']==4736150 and parts['sha256']=='de059522bde31ba069e6f0b687bd9e40498635fdb3ac175a8b57b1c30daf9d6e','complete actual archive identity')
    require(parts['verification']==dict(parts=1,bytes=parts['bytes'],sha256=parts['sha256'],all_parts_and_combined_bytes_verified=True),'original publication verified parts')
    require(parts['parts'][0]['index']==0 and parts['parts'][0]['bytes']==parts['bytes']and parts['parts'][0]['sha256']==parts['sha256'],'single exact immutable native part')
    require({x['name']for x in p['assets']}=={'complete-output-index.json',Path(p['parts_path']).name,parts['parts'][0]['name']},'all three original assets')
    return index,parts

def validate_producer(c,run,jobs,release,ref,root=ROOT):
    p=c['producer'];prefix=p['proof_prefix']
    historical_run=q.decode(q.regular(root,prefix+'run.json').read_bytes())
    historical_jobs=q.decode(q.regular(root,prefix+'jobs.json').read_bytes())
    for key in('id','head_sha','head_branch','run_attempt','event','workflow_id','path','status','conclusion'):
        require(run[key]==historical_run[key],'immutable original run: '+key)
    require(run['status']=='completed'and run['conclusion']=='failure'and run['head_sha']==p['source'],'failed original run retained')
    require(jobs['total_count']==len(jobs['jobs'])==len(historical_jobs['jobs'])==3,'complete original three jobs')
    historical={j['id']:j for j in historical_jobs['jobs']}
    require({j['id']for j in jobs['jobs']}==set(historical),'original job identities')
    for j in jobs['jobs']:
        old=historical[j['id']]
        for key in('id','run_id','run_attempt','head_sha','name','status','conclusion','steps'):require(j[key]==old[key],'actual original terminal job '+key)
    case=next(j for j in jobs['jobs']if j['id']==p['job_id'])
    require(case['conclusion']=='failure'and [s['name']for s in case['steps']if s['conclusion']=='failure']==['Generate exact sixteen shapes and run unchanged full physical gates'],'exact known source-import failure')
    require(all(j['conclusion']=='success'for j in jobs['jobs']if j['id']!=p['job_id']),'original source/log prerequisites')
    assets=q.release_binding(release,ref,p['tag'],p['source'])
    require(release['id']==p['release_id']and set(assets)=={x['name']for x in p['assets']},'complete original exact-source release')
    for pin in p['assets']:
        a=assets[pin['name']]
        require(a['id']==pin['id']and a['size']==pin['bytes']and a['digest']=='sha256:'+pin['sha256'],'original asset bytes')
        for key in('state','content_type','created_at','updated_at'):require(a[key]==pin[key],'immutable original asset '+key)
    return dict(run_id=p['run_id'],source=p['source'],attempt=1,release_id=p['release_id'],job_id=p['job_id'],original_conclusion='failure',generation_evidence_requires_archive_authentication=True,physical_execution_in_original=False)

def validate_restored(c,restore,full,root=ROOT):
    p=c['producer'];index,parts=metadata(c,root)
    require(restore==root/p['restore_root_relative']and restore.resolve()==restore and not restore.is_symlink(),'authentic absolute restore root, no rewrite')
    require(full['every_member_authenticated']is True and full['full_member_count']==99 and full['full_members']==index['files']and full['selected']==index['files'],'full99 member byte authentication')
    for name,pin in index['files'].items():require(q.file_pin(q.regular(restore,name))==pin,'retained authentic producer file')
    generated=q.decode(q.regular(restore,p['generated_layout_member']).read_bytes())
    generation=q.decode(q.regular(restore,p['generation_member']).read_bytes())
    require(generated['inputs']==p['frozen_generated_inputs'],'original layout result inputs must remain unchanged')
    expected={str(restore/name):pin['sha256']for name,pin in p['selected_inputs'].items()}
    require(generated['inputs']==expected,'original absolute input paths must bind authentic restored bytes')
    require(len(generated['ports'])==25 and len(set(generated['ports']))==25,'original25 physical ports')
    layout=restore/'native/layout'
    require(generated['outputs']=={Path(n).name:index['files'][n]['sha256']for n in p['layout_copy_members']if not n.endswith('/result.json')},'exact original three physical outputs')
    for n,h in generated['inputs'].items():require(q.file_pin(Path(n))['sha256']==h,'all20 actual absolute input hashes')
    require(generation['status']=='GENERATED_DECLARED_VIA2_M3_CANDIDATE_REQUIRES_FRESH_DRC_LVS_RC_WAVES'and generation['geometry_generated']is True and generation['original_full_rails_unchanged']is True,'actual completed generation')
    require(generation['DRC_executed']is generation['LVS_executed']is generation['RC_executed']is False,'original no physical acceptance')
    require(generation['proof']['structural_reversal_exact']is True and len(generation['proof']['added_records'])==16 and generation['proof']['original_file_byte_equality_claimed']is False,'actual16 reversible additions')
    require(generation['proof']['candidate']==index['files'][p['candidate_member']],'actual candidate byte identity')
    for key in FLAGS: 
        if key in generation:require(generation[key]is False,'no original downstream acceptance')
    return dict(original_layout_result=q.file_pin(layout/'result.json'),original_generation=q.file_pin(restore/p['generation_member']),candidate=q.file_pin(restore/p['candidate_member']),all99_authenticated=True,all20_absolute_inputs_preserved=True,layout_regenerated=False,result_rewritten=False)

def validate_current_run(ctx,run,jobs):
    require(run['id']==ctx['run_id']and run['head_sha']==ctx['source']and run['head_branch']==BRANCH and run['run_attempt']==1,'actual current run identity')
    require(run['event']=='workflow_dispatch'and run['workflow_id']==382556685 and run['path']==WORKFLOW and run['status']=='in_progress','actual authoritative workflow')
    rows=jobs['jobs'];require(len(rows)==jobs['total_count']==3,'exact source/log/physical-recheck jobs')
    require(all(j['run_id']==ctx['run_id']and j['run_attempt']==1 and j['head_sha']==ctx['source']for j in rows),'every actual job source')
    by={j['name']:j for j in rows};require(set(by)=={'source-controls','preserve-job-log','physical-recheck'},'exact job names')
    for name in('source-controls','preserve-job-log'):
        j=by[name];require(j['status']=='completed'and j['conclusion']=='success','same-run prerequisite success')
        require(all(s['conclusion']in('success','skipped')for s in j['steps'])and any(s['conclusion']=='success'for s in j['steps']),'successful prerequisite steps')
    require(by['physical-recheck']['status']=='in_progress'and by['physical-recheck']['conclusion']is None,'single current physical-recheck job')
    return dict(current_source=ctx['source'],run_id=ctx['run_id'],source_job=by['source-controls']['id'],log_job=by['preserve-job-log']['id'],candidate_job=by['physical-recheck']['id'])

def read_source_log(job):
    require(type(job)is int and job>0,'source job id')
    return subprocess.check_output(['gh','api','--allow-escape-sequences','repos/'+q.REPOSITORY+'/actions/jobs/'+str(job)+'/logs'])

def bind_controls(raw,ctx):
    r=q.decode(raw)
    require(r['status']=='PASS_PHYSICAL_ONLY_REUSE_SOURCE_CONTROLS'and r['passed']is True,'complete actual reuse source controls')
    require(r['context']==dict(source=ctx['source'],run_id=ctx['run_id'],attempt=1),'same source/run controls')
    require(r['producer_refusals']>=12 and r['restore_refusals']>=8 and r['context_refusals']>=6,'meaningful source admission refusal census')
    require(r['lifecycle_cases']==4 and r['publication_cases']==7 and r['publication_refusals']==33,'complete unchanged lifecycle/publication controls')
    require(r['source_log_refusals']>=14,'complete source log transport refusals')
    require(r['closure_counts']==dict(import_source_refusals=7,runtime_source_refusals=4,external_and_write_barriers=6,observed_repository_reads=118,first_native_boundary_calls=1),'same original complete closure gates')
    require(r['native_candidate_acquired']is r['geometry_generated']is r['drc_executed']is r['lvs_executed']is False,'source controls only')
    return q.fingerprint(raw)
def authenticate_source_log(ctx,log):
    require(type(log)is bytes and len(log)>0,'complete raw source job log')
    expected={'recheck-controls.stdout','recheck-controls.stderr','recheck-source-closure.stdout','recheck-source-closure.stderr','recheck-decks.stdout','recheck-decks.stderr','hw/soc/out/cdr-via2-m3-physical-recheck-source-closure-controls/result.json','hw/soc/out/cdr-via2-m3-physical-recheck-source-closure-controls/deck-source-preparation.json','cdr-via2-m3-recheck-controls/result.json'}
    indexes={};chunks={}
    for line in log.decode('utf-8',errors='strict').splitlines():
        found=re.search(r'VIA2_M3_RECHECK_CONTROL_INDEX (\{.*\})\s*$',line)
        if found:
            row=q.decode(found[1].encode());name=row['path']
            require(name in expected and name not in indexes,'unique exact source index')
            require(type(row['bytes'])is int and row['bytes']>=0 and type(row['chunks'])is int and row['chunks']>0 and re.fullmatch('[0-9a-f]{64}',row['sha256']),'source index fields')
            indexes[name]=row
        found=re.search(r'VIA2_M3_RECHECK_CONTROL_CHUNK (\{.*\})\s*$',line)
        if found:
            row=q.decode(found[1].encode());name=row['path'];i=row['index']
            require(name in expected and type(i)is int and i>=0 and i not in chunks.setdefault(name,{}),'unique exact source chunk')
            chunks[name][i]=base64.b64decode(row['base64'],validate=True)
    require(set(indexes)==set(chunks)==expected,'nine complete emitted control records')
    records={}
    for name,row in indexes.items():
        require(set(chunks[name])==set(range(row['chunks'])),'all source chunks')
        raw=b''.join(chunks[name][i]for i in range(row['chunks']))
        require(q.fingerprint(raw)==dict(bytes=row['bytes'],sha256=row['sha256']),'actual emitted source bytes');records[name]=raw
    result=records['cdr-via2-m3-recheck-controls/result.json'];proof=bind_controls(result,ctx)
    closure=q.decode(records['hw/soc/out/cdr-via2-m3-physical-recheck-source-closure-controls/result.json'])
    require(closure['status']=='PASS_UNCHANGED_PHYSICAL_CHECKER_IMPORT_TO_FIRST_NATIVE_BOUNDARY_ONLY'and closure['source']==ctx['source']and closure['run_id']==ctx['run_id'],'same-run actual unchanged-checker closure')
    require(closure['checker']==dict(bytes=15411,sha256='3ef6c47117a5467acc37ee4ea87af979a75e9be671cbf0a5153307974d082d66')and closure['github_environment_spoofed']is False,'original checker and actual environment')
    return records,dict(source=ctx['source'],run_id=ctx['run_id'],attempt=1,full_raw_log=q.fingerprint(log),records={n:q.fingerprint(b)for n,b in records.items()},controls=proof,native_acquisition=False)
def native_preflight(path,ctx,c,restore,root=ROOT):
    authorize_native(ctx,c)
    value=q.decode(q.regular(path.parent,path.name).read_bytes())
    require(value['context']==ctx and value['physical_verification_authorized']is True and value['generation_authorized']is False,'actual physical-only preflight')
    require(value['restore_root']==str(restore)and restore==root/c['producer']['restore_root_relative'],'authentic immutable input restore path')
    require(value['all99_authenticated']is True and value['original_failure_preserved']is True and value['result_rewritten']is False,'complete original result preserved')
    evidence=path.parent
    controls=q.regular(evidence,'same-source-controls.json').read_bytes()
    require(bind_controls(controls,ctx)==value['source_controls'],'actual current source control bytes')
    require(validate_current_run(ctx,q.decode(q.regular(evidence,'current-run.json').read_bytes()),q.decode(q.regular(evidence,'current-jobs.json').read_bytes()))==value['current_run_binding'],'actual current job binding')
    producer=validate_producer(c,*[q.decode(q.regular(evidence,'producer-'+n+'.json').read_bytes())for n in('run','jobs','release','ref')],root=root)
    require(producer==value['producer_binding'],'actual immutable failed producer source')
    reserved=q.decode(q.regular(evidence,'reservation-original.json').read_bytes())
    proof=q.reservation(ctx,reserved,q.decode(q.regular(evidence,'result-release-empty.json').read_bytes()),q.decode(q.regular(evidence,'result-tag.json').read_bytes()))
    require(proof==value['reservation_binding'],'independent empty exact-source reservation')
    index,parts=metadata(c,root)
    for name,pin in index['files'].items():require(q.file_pin(q.regular(restore,name))==pin,'all99 authenticated originals unchanged')
    require(value['restore_proof']['candidate']==index['files'][c['producer']['candidate_member']]and value['restore_proof']['all20_absolute_inputs_preserved']is True,'physical source binding')
    return value
