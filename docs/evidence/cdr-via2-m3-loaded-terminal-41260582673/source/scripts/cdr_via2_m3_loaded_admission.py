#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""New exact-source loaded nominal_late admission; no historical producer or environment substitution."""
import base64,contextlib,json,os,re,signal,subprocess,threading,time
from pathlib import Path
import cloud_cdr_current_eight_drain_wave_replay as q
import cdr_via2_m3_loaded_producer as producer
ROOT=Path(__file__).resolve().parents[1]
BRANCH='codex/cdr-via2-m3-loaded-adapter'
CONFIG='scripts/cdr-via2-m3-loaded-adapter-inputs.json'
MANIFEST='scripts/cdr-via2-m3-loaded-adapter-pins.json'
PRODUCER='scripts/cdr-via2-m3-loaded-producer-inputs.json'
WORKFLOW='.github/workflows/cloud-evidence-summary.yml'
GROUP='cdr-via2-m3-loaded-nominal_late'
OUT=ROOT/'hw/soc/out/cloud-cdr-via2-m3-loaded'
ORIGINAL=ROOT/'hw/soc/out/cloud-cdr-via2-m3-fresh-rc'
require=q.require;encode=q.encode

class Deadline:
    """A single monotonic phase deadline shared by all blocking child calls."""
    def __init__(self,seconds):
        require(type(seconds)in(int,float)and 0<seconds<=21600,'bounded phase deadline')
        self.ends=time.monotonic()+seconds
    def timeout(self,limit):
        remaining=self.ends-time.monotonic()
        require(remaining>0,'explicit phase deadline exceeded')
        return min(float(limit),remaining)

def api(endpoint,budget):
    require(isinstance(budget,Deadline)and isinstance(endpoint,str)and endpoint and not endpoint.startswith('/'),'explicit bounded repository API')
    return q.decode(subprocess.check_output(['gh','api','repos/'+q.REPOSITORY+'/'+endpoint],timeout=budget.timeout(60)))


def download(pin,path,budget):
    require(isinstance(budget,Deadline)and not path.exists()and not path.is_symlink(),'bounded exclusive download')
    primary=None;stderr=path.parent/('download-'+str(pin['id'])+'.stderr')
    report=dict(asset=pin,path=str(path),native_bytes_remain_cloud_only=True,status='RUNNING')
    try:
        with path.open('xb')as stream,stderr.open('xb')as errors:
            completed=subprocess.run(['gh','api','-H','Accept: application/octet-stream','repos/'+q.REPOSITORY+'/releases/assets/'+str(pin['id'])],stdout=stream,stderr=errors,check=True,timeout=budget.timeout(1800))
        report['actual_file']=q.file_pin(path)
        require(report['actual_file']=={k:pin[k]for k in('bytes','sha256')},'complete downloaded bytes')
        report['status']='PASS_EXACT_ASSET_BYTES'
    except BaseException as error:
        primary=error;report.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        try:
            if path.is_file()and not path.is_symlink():report['retained_file']=q.file_pin(path)
            if stderr.is_file()and not stderr.is_symlink():report['stderr']=q.file_pin(stderr)
            q.write_new(path.parent/('download-'+str(pin['id'])+'.json'),q.encode(report))
        except BaseException as error:
            try:print(json.dumps(dict(unsaved_download_observation=report,secondary_error=repr(error)),sort_keys=True),flush=True)
            except BaseException:pass
            if primary is None:raise

@contextlib.contextmanager
def phase_budget(seconds):
    """Bound Python hashing/extraction as well as child IO; no nested timer spoof."""
    budget=Deadline(seconds)
    require(threading.current_thread()is threading.main_thread(),'phase watchdog requires real main thread')
    require(signal.getitimer(signal.ITIMER_REAL)==(0.0,0.0),'no inherited phase timer')
    previous=signal.getsignal(signal.SIGALRM)
    def expired(signum,frame):raise TimeoutError('Explicit loaded host phase deadline exceeded')
    signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,seconds)
    try:yield budget
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,previous)

def context(env):
    require(env.get('GITHUB_ACTIONS')=='true'and env.get('RUNNER_ENVIRONMENT')=='github-hosted'and env.get('RUNNER_OS')=='Linux','hosted Linux only')
    require(env.get('GITHUB_REPOSITORY')==q.REPOSITORY and env.get('GITHUB_EVENT_NAME')=='workflow_dispatch','manual exact repository')
    require(env.get('GITHUB_REF')=='refs/heads/'+BRANCH and env.get('GITHUB_WORKFLOW_REF')==q.REPOSITORY+'/'+WORKFLOW+'@refs/heads/'+BRANCH,'exact branch/workflow')
    require(env.get('GITHUB_RUN_ATTEMPT')=='1','no rerun')
    head=env.get('GITHUB_SHA','');run=env.get('GITHUB_RUN_ID','')
    require(re.fullmatch('[0-9a-f]{40}',head)and re.fullmatch('[1-9][0-9]*',run),'source/run')
    require(env.get('APPROVED_SOURCE')==head,'explicit current source')
    mode=env.get('REQUESTED_MODE');job=env.get('GITHUB_JOB')
    require((mode,job)in(('controls','source-controls'),('loaded','source-controls'),('loaded','loaded')),'bounded mode/job')
    return dict(source=head,run_id=int(run),attempt=1,mode=mode,job=job,case='nominal_late',group=GROUP,token=run+'-1')

def validate_config(c):
    require(c['schema']=='cdr-via2-m3-loaded-adapter-v1'and c['branch']==BRANCH and c['repository']==q.REPOSITORY,'exact loaded nominal_late adapter')
    require(c['workflow']==WORKFLOW and c['workflow_id']==382556685 and c['case']=='nominal_late','actual workflow and producer case label')
    require(c['source_controls_authorized']is True and c['native_payloads_cloud_only']is True and c['all_acceptance_false']is True,'cloud-only bounded scope')
    require(type(c['loaded_execution_authorized'])is bool,'explicit typed loaded nominal_late authority')
    require(c['generation_authorized']is c['fresh_rc_execution_authorized']is False,'no generation or RC authority')
    require(c['producer_path']==PRODUCER and c['original_output_root']==str(ORIGINAL)and c['fresh_output_root']==str(OUT),'separate original and fresh roots')
    required={'producer_positive','producer_refusals','core_controls','context_refusals','current_job_refusals','source_log_refusals','lifecycle_cases','publication_cases','publication_refusals','emission_refusals','runtime_positive','runtime_refusals','core_refusals','native_positive','native_refusals'}
    require(set(c['source_control_requirements'])==required and all(type(v)is int and v>0 for v in c['source_control_requirements'].values()),'complete positive actual source-control requirements')
    require(c['resources']==dict(metadata_seconds=180,acquisition_seconds=900,engine_seconds=1200,publication_seconds=900),'fixed original engine and bounded host phase budgets')
    return c

def core_source_closure(root,c):
    require(c['core']is not None and c['core']['native_authorization_asserted_by_this_record']is False,'explicit source-only numerical core')
    for name,pin in c['core']['source_files'].items():require(q.file_pin(q.regular(root,name))==pin,'complete exact numerical core source '+name)
    return True

def source_guard(ctx=None,root=ROOT,budget=None):
    budget=Deadline(120)if budget is None else budget
    ctx=context(os.environ)if ctx is None else ctx
    require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True,timeout=budget.timeout(30)).strip()==ctx['source'],'actual exact checkout')
    raw=q.regular(root,MANIFEST).read_bytes();require(raw==subprocess.check_output(['git','show',ctx['source']+':'+MANIFEST],cwd=root,timeout=budget.timeout(30)),'immutable current manifest')
    m=q.decode(raw);require(m['schema']=='cdr-via2-m3-loaded-adapter-pins-v1','exact new source manifest')
    for name,pin in m['files'].items():
        actual=q.file_pin(q.regular(root,name));require(actual['sha256']==pin['sha256']and('bytes'not in pin or actual['bytes']==pin['bytes']),'protected source changed '+name)
    c=validate_config(q.decode(q.regular(root,CONFIG).read_bytes()))
    require(m['loaded_execution_authorized']is c['loaded_execution_authorized'],'separate authority consistent with manifest')
    p=q.decode(q.regular(root,PRODUCER).read_bytes());producer.metadata(root,p)
    require(p['native_authorization_asserted_by_this_record']is False,'producer evidence grants no execution authority')
    core_source_closure(root,c);budget.timeout(1)
    return c,p

def authorize_native(ctx,c):
    validate_config(c)
    require(ctx['mode']=='loaded'and ctx['job']=='loaded'and c['loaded_execution_authorized']is True,'separate exact-source loaded nominal_late authority required')

def validate_current_run(ctx,run,jobs):
    require(run['id']==ctx['run_id']and run['head_sha']==ctx['source']and run['head_branch']==BRANCH and run['run_attempt']==1,'actual current run identity')
    require(run['event']=='workflow_dispatch'and run['workflow_id']==382556685 and run['path']==WORKFLOW and run['status']=='in_progress','actual authoritative workflow')
    rows=jobs['jobs'];require(len(rows)==jobs['total_count']==3,'exact source/log/loaded jobs')
    require(all(j['run_id']==ctx['run_id']and j['run_attempt']==1 and j['head_sha']==ctx['source']for j in rows),'every actual job source')
    by={j['name']:j for j in rows};require(set(by)=={'source-controls','preserve-job-log','loaded'},'exact job names')
    for name in('source-controls','preserve-job-log'):
        j=by[name];require(j['status']=='completed'and j['conclusion']=='success','same-run prerequisite success')
        require(all(s['conclusion']in('success','skipped')for s in j['steps'])and any(s['conclusion']=='success'for s in j['steps']),'successful prerequisite steps')
    require(by['loaded']['status']=='in_progress'and by['loaded']['conclusion']is None,'single current loaded job')
    return dict(current_source=ctx['source'],run_id=ctx['run_id'],source_job=by['source-controls']['id'],log_job=by['preserve-job-log']['id'],candidate_job=by['loaded']['id'])

def read_source_log(job,budget):
    require(type(job)is int and job>0,'source job id')
    return subprocess.check_output(['gh','api','--allow-escape-sequences','repos/'+q.REPOSITORY+'/actions/jobs/'+str(job)+'/logs'],timeout=budget.timeout(60))

def bind_controls(raw,ctx,c):
    r=q.decode(raw)
    require(r['status']=='PASS_CURRENT_VIA2_M3_LOADED_SOURCE_CONTROLS'and r['passed']is True,'actual integrated source controls')
    require(r['context']==dict(source=ctx['source'],run_id=ctx['run_id'],attempt=1),'same exact source and run')
    required=c['source_control_requirements'];require(set(r['controls'])==set(required),'complete integrated control groups')
    for name,count in required.items():require(type(r['controls'][name])is int and r['controls'][name]>=count,'required source-control group '+name)
    require(r['native_payload_acquired']is r['RC_executed']is r['simulation_executed']is r['layout_regenerated']is False,'source controls cannot claim native execution')
    return q.fingerprint(raw)

def authenticate_source_log(ctx,log,c):
    require(type(log)is bytes and len(log)>0,'complete raw source job log')
    expected={'loaded-controls.stdout','loaded-controls.stderr','loaded-controls/result.json'}
    indexes={};chunks={}
    for line in log.decode('utf-8',errors='strict').splitlines():
        found=re.search(r'VIA2_M3_LOADED_CONTROL_INDEX (\{.*\})\s*$',line)
        if found:
            row=q.decode(found[1].encode());name=row['path']
            require(name in expected and name not in indexes,'unique exact source index')
            require(type(row['bytes'])is int and row['bytes']>=0 and type(row['chunks'])is int and row['chunks']>0 and re.fullmatch('[0-9a-f]{64}',row['sha256']),'source index fields')
            indexes[name]=row
        found=re.search(r'VIA2_M3_LOADED_CONTROL_CHUNK (\{.*\})\s*$',line)
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
    result=records['loaded-controls/result.json'];proof=bind_controls(result,ctx,c)
    return records,dict(source=ctx['source'],run_id=ctx['run_id'],attempt=1,full_raw_log=q.fingerprint(log),records={n:q.fingerprint(b)for n,b in records.items()},controls=proof,native_acquisition=False)

def native_preflight(path,ctx,c,p,root=ROOT):
    authorize_native(ctx,c);value=q.decode(q.regular(path.parent,path.name).read_bytes())
    require(path.parent==OUT and value['context']==ctx and value['loaded_execution_authorized']is True,'actual loaded nominal_late preflight context')
    require(value['generation_authorized']is value['fresh_rc_execution_authorized']is False,'single original nominal_late only')
    require(value['restore_root']==str(ORIGINAL)==producer.CURRENT_ROOT,'original absolute report roots preserved')
    require(bind_controls(q.regular(OUT,'same-source-controls.json').read_bytes(),ctx,c)==value['source_controls'],'same-source prerequisite controls')
    require(validate_current_run(ctx,q.decode(q.regular(OUT,'current-run.json').read_bytes()),q.decode(q.regular(OUT,'current-jobs.json').read_bytes()))==value['current_run_binding'],'actual authoritative current jobs')
    reserved=q.decode(q.regular(OUT,'reservation-original.json').read_bytes())
    require(q.reservation(ctx,reserved,q.decode(q.regular(OUT,'result-release-empty.json').read_bytes()),q.decode(q.regular(OUT,'result-tag.json').read_bytes()))==value['reservation_binding'],'independent empty exact-source destination')
    original=producer.metadata(root,p)
    live=producer.validate_live(p,original,*[q.decode(q.regular(OUT,'rc-producer-'+n+'.json').read_bytes())for n in('run','jobs','release','ref')])
    require(live==value['producer_binding'],'original current view live binding')
    full=q.decode(q.regular(OUT,'rc-complete-input-census.json').read_bytes())
    require(producer.validate_restored(ORIGINAL,p,full,original)==value['restore_proof'],'entire original3091 byte binding')
    require(value['original_absolute_results_rewritten']is False and value['historical_producer_context_substituted']is False,'no rewritten or substituted producer context')
    return value

if __name__=='__main__':
    raise SystemExit('Admission library only; no standalone native execution authority')
