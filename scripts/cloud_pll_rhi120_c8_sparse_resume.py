#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact RHI120 ordinary-to-sparse native continuation and publication contract."""
import ast,copy,hashlib,json,os,subprocess,tempfile
from pathlib import Path
import cloud_pll_rhi120_c8_recovery as baseline
import cloud_pll_rhi120_c8_sparse_io as storage
ROOT=Path(__file__).resolve().parents[1]
CONTROLLER='scripts/cloud_pll_rhi120_c8_sparse.py'
MANIFEST='scripts/pll-rhi120-c8-sparse-resume-delta.json'
OLD='scripts/cloud_pll_rhi120_c8_recovery.py'
GIB=1024**3
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def source_contract(root=ROOT):
    m=json.loads((root/MANIFEST).read_text())
    assert baseline.method_hashes()==m['baseline_method_hashes'],'Recovery methods changed'
    for p,h in m['current_files'].items():assert sha(root/p)==h,p
    text=(root/OLD).read_text()
    for e in m['edits']:
        assert text.count(e['before'])==e['count'],e['before'][:80]
        text=text.replace(e['before'],e['after'])
    assert text==(root/CONTROLLER).read_text(),'Unreviewed controller delta'
    original={n.name:ast.dump(n,include_attributes=False)for n in ast.parse((root/OLD).read_text()).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
    actual={n.name:ast.dump(n,include_attributes=False)for n in ast.parse(text).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
    assert set(original)==set(actual)
    changed={k for k in original if original[k]!=actual[k]}
    assert changed==set(m['changed_functions'])
    for n in ('command','process_contract','validate_bound_deck','verify_new_physical','verify_native_flags','verify_column_qualification'):
        assert actual[n]==original[n],n
    current={k:v for k,v in m['baseline_method_hashes'].items()if k!=OLD}
    current[CONTROLLER]=sha(root/CONTROLLER)
    current.update({p:sha(root/p)for p in m['added_methods']})
    return m,current
def verify_resume_methods(report,current):
    m,expected=source_contract()
    assert current==expected
    if report['controller_sha256']==current[CONTROLLER]:
        assert report['method_hashes']==current,'Sparse method changed'
        return dict(mode='exact-current-RHI120-sparse',native_methods_unchanged=True)
    # The exact original initial method map is admitted only by source_gate's
    # audited terminal-publication fallback, never as a live-progress fork.
    proof=baseline.verify_resume_methods(report,m['baseline_method_hashes'])
    return dict(mode='explicit-RHI120-lossless-sparse-storage-only-migration',baseline=proof,
        native_methods_unchanged=True,original_all_columns_solver_loads_duration_and_gates_unchanged=True)
def source_gate(run,spec,report):
    assert set(spec)=={'run','attempt','stage','summary_sha256','parts_sha256'}
    assert str(spec['run']).isdigit()and str(spec['attempt'])=='1'
    assert spec['stage']in ('initial','recovery','sparse')
    if spec['stage']=='initial':
        assert spec==baseline.INITIAL_SPEC,'Only the last verified durable initial capsule may recover'
        original=baseline.source_gate(run,spec,report)
        proof,_=fallback_authorization()
        return dict(original,terminal_publication_fallback=proof,
            cold_start_allowed=False,failed_newer_run_preserved=True)
    assert run['id']==int(spec['run'])and run['id']>=39941648965
    assert run['run_attempt']==1 and run['status']=='completed'and run['conclusion']=='success'
    assert run['head_branch']=='codex/complete-open-work'
    expected='.github/workflows/pll-rhi120-c8-native-'+spec['stage']+'-cloud.yml'
    assert run['path']==expected
    assert report['source_head']==run['head_sha']
    assert report['run_id']==str(spec['run'])and report['run_attempt']=='1'and report['stage']==spec['stage']
    assert report['status']==baseline.CHECKPOINT_STATUS and report['checkpoint_saved']is True
    assert report['full_capture']is False and report['protected_inputs_unchanged']is True
    assert report['prior_payload_unchanged']is True and report['native_position']['columns']==5106
    assert report['checkpoint_images']
    assert int(spec['run'])!=int(os.environ.get('GITHUB_RUN_ID','0'))
    return dict(original_run=39925042125,original_failure_preserved=True,
        previous_successful_recovery_run=spec['run'],no_live_source_or_initial_replay=True)
def fallback_gate(run,job,annotations,artifacts,release_exists):
    assert run['id']==39941648965 and run['run_attempt']==1
    assert run['status']=='completed'and run['conclusion']=='cancelled'
    assert run['head_sha']=='d171e9d4f886b7cdb92ae1f152f70f8133aa4177'
    assert run['head_branch']=='codex/complete-open-work'
    assert run['path']=='.github/workflows/pll-rhi120-c8-native-recovery-cloud.yml'
    assert job['id']==120374455456 and job['status']=='completed'and job['conclusion']=='cancelled'
    assert any(a['annotation_level']=='failure'and a['message']=='The job has exceeded the maximum execution time of 3h0m0s'for a in annotations)
    native=next(s for s in job['steps']if s['name']=='Recover only the audited saved RHI120 process with exact qualified tables')
    publication=next(s for s in job['steps']if s['name']=='Preserve every native byte and checkpoint including failed evidence')
    assert native['status']=='completed'and native['conclusion']=='success'
    assert publication['conclusion']!='success'
    assert artifacts['total_count']==0 and artifacts['artifacts']==[]and release_exists is False
    return dict(run=39941648965,job=120374455456,terminal_publication_timeout=True,
        no_published_capsule_available=True,no_native_electrical_failure_inferred=True)
def fallback_authorization():
    repo='repos/Melihakbulut221/nssoc/'
    api=lambda p:json.loads(subprocess.check_output(['gh','api',repo+p]))
    run=api('actions/runs/39941648965');job=api('actions/jobs/120374455456')
    annotations=api('check-runs/120374455456/annotations')
    artifacts=api('actions/runs/39941648965/artifacts')
    release=subprocess.run(['gh','api',repo+'releases/tags/cloud-results-39941648965-1-pll-rhi120-c8-native-recovery'],capture_output=True,text=True)
    if release.returncode:
        body=json.loads(release.stdout)
        assert str(body.get('status'))=='404'and body.get('message')=='Not Found','Uncertain release access is not absence'
        release_exists=False
    else:release_exists=True
    proof=fallback_gate(run,job,annotations,artifacts,release_exists)
    owner=int(os.environ['GITHUB_RUN_ID'])
    inspected=[]
    for workflow in ('initial','recovery','sparse'):
        page=1
        while True:
            rows=api('actions/workflows/pll-rhi120-c8-native-'+workflow+'-cloud.yml/runs?event=workflow_dispatch&per_page=100&page='+str(page))['workflow_runs']
            if not rows:break
            for other in rows:
                if other['created_at']<run['created_at']:continue
                inspected.append(dict(run=other['id'],event=other['event'],status=other['status'],conclusion=other['conclusion']))
                assert other['id']in (owner,39941648965),'Another native attempt exists; inspect its capsule instead of replaying initial'
            page+=1
    proof['checked_later_dispatches']=inspected
    return proof,dict(run=run,job=job,annotations=annotations,artifacts=artifacts,release_exists=release_exists)
def fallback_controls():
    proof,audit=fallback_authorization()
    rejected=[]
    for label in ('live-run','other-run','wrong-head','live-job','wrong-job','other-timeout','artifact-available','release-available','failed-native','publication-passed','missing-publication-step'):
        bad=copy.deepcopy(audit)
        if label=='live-run':bad['run']['status']='in_progress'
        elif label=='other-run':bad['run']['id']=39941648966
        elif label=='wrong-head':bad['run']['head_sha']='a'*40
        elif label=='live-job':bad['job']['status']='in_progress'
        elif label=='wrong-job':bad['job']['id']=120374455457
        elif label=='other-timeout':bad['annotations']=[]
        elif label=='artifact-available':bad['artifacts']=dict(total_count=1,artifacts=[{'id':1}])
        elif label=='release-available':bad['release_exists']=True
        elif label=='failed-native':next(s for s in bad['job']['steps']if s['name'].startswith('Recover only'))['conclusion']='failure'
        elif label=='publication-passed':next(s for s in bad['job']['steps']if s['name'].startswith('Preserve every'))['conclusion']='success'
        else:bad['job']['steps']=[s for s in bad['job']['steps']if not s['name'].startswith('Preserve every')]
        try:fallback_gate(**bad)
        except (AssertionError,StopIteration):rejected.append(label)
        else:raise AssertionError('Invalid fallback accepted: '+label)
    raw=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/releases/assets/668715744','-H','Accept: application/octet-stream'])
    assert hashlib.sha256(raw).hexdigest()==baseline.INITIAL_SPEC['summary_sha256']
    prior=json.loads(raw)
    run=json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/actions/runs/39925042125']))
    assert source_gate(run,baseline.INITIAL_SPEC,prior)['terminal_publication_fallback']
    _,current=source_contract()
    assert verify_resume_methods(prior,current)['baseline']['mode']=='exact-failed-RHI120-initial-with-qualified-table-reader'
    assert len(rejected)==11
    return dict(actual_terminal_failure=proof,rejected=rejected,
        actual_initial_method_identity_verified=True,native_process_activated=False,
        scope='Exact last durable native checkpoint fallback after audited terminal publication timeout only')

def qualification():
    api=lambda p:json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/'+p]))
    run=api('actions/runs/39954614699')
    assert run['status']=='completed'and run['conclusion']=='success'
    assert run['head_sha']=='9690bb870b2afde732bca4a900a272caff23f771'
    data=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/releases/assets/669122845','-H','Accept: application/octet-stream'])
    assert hashlib.sha256(data).hexdigest()=='7ad5df24b5368bb62d1dbd6dc8dd80baff6bb3237fc1708c096c95f50ffd2a62'
    r=json.loads(data)
    assert r['complete_logical_raw_and_payload_hashes_match']and r['all_recorded_source_members_verified']
    assert r['all_ordered_archive_bytes_verified']and r['verified_source_member_count']==1856
    assert len(r['controls']['negative_controls'])==16 and not r['native_activation_performed']
    assert r['logical_proof']['bytes']==25342824379
    assert r['logical_proof']['sha256']=='2dd133ea5eb78a7a7d87a5836612bd135f20fa1da32fb7a2a6331d71ce89f166'
    return dict(run=39954614699,summary_sha256=hashlib.sha256(data).hexdigest(),
        storage_only_proven=True,native_resume_previously_qualified=False)
def reserve_bytes(checkpoint_bytes,part_bytes=256*1024**2):
    assert type(checkpoint_bytes)is int and checkpoint_bytes>=0
    assert type(part_bytes)is int and 0<part_bytes<=GIB
    # Two copies of saved CRIU pages plus 8 GiB for growth between polls, runner
    # activity and logs; two bounded publication/download parts. No whole archive.
    return max(12*GIB,2*checkpoint_bytes+8*GIB+2*part_bytes)
def disk_plan(root):
    checkpoints=root/'checkpoints'
    size=sum(p.stat().st_size for p in checkpoints.rglob('*')if p.is_file())if checkpoints.exists()else 0
    paths=list(root.rglob('*'));files=[p for p in paths if p.is_file()]
    return dict(source_tree_bytes=sum(p.stat().st_size for p in files),
        physical_allocated_bytes=sum(p.stat().st_blocks*512 for p in files),
        checkpoint_bytes=size,archive_copies=0,archive_reserve_bytes=reserve_bytes(size),
        publication_part_bytes=256*1024**2,checkpoint_and_poll_margin_bytes=8*GIB,
        storage_policy='Verified streamed ordinary logical archive; source archive remains immutable')
def controls():
    m,current=source_contract()
    old=dict(controller_sha256=m['baseline_method_hashes'][OLD],method_hashes=m['baseline_method_hashes'])
    same=dict(controller_sha256=current[CONTROLLER],method_hashes=current)
    verify_resume_methods(old,current);verify_resume_methods(same,current)
    rejected=[]
    for label,target,key in [('unknown-controller','new',CONTROLLER),('changed-native','new','scripts/cloud_native_checkpoint_probe.py'),
        ('changed-parser','new','scripts/read_pll_rhi120_c8_all_native.py'),('changed-storage','new','scripts/cloud_pll_rhi120_c8_sparse_io.py'),
        ('changed-old-native','old','scripts/cloud_native_checkpoint_probe.py'),('extra-method','new','unexpected')]:
        bad=copy.deepcopy(old if target=='old'else same)
        if label=='unknown-controller':bad['controller_sha256']='0'*64
        else:bad['method_hashes'][key]='0'*64
        try:verify_resume_methods(bad,current)
        except AssertionError:rejected.append(label)
        else:raise AssertionError('Accepted method corruption '+label)
    spec=dict(run=39941648965,attempt=1,stage='recovery',summary_sha256='1'*64,parts_sha256='2'*64)
    run=dict(id=spec['run'],run_attempt=1,status='completed',conclusion='success',
        head_branch='codex/complete-open-work',path='.github/workflows/pll-rhi120-c8-native-recovery-cloud.yml',head_sha='a'*40)
    report=dict(source_head='a'*40,run_id=str(spec['run']),run_attempt='1',stage='recovery',
        status=baseline.CHECKPOINT_STATUS,checkpoint_saved=True,full_capture=False,
        protected_inputs_unchanged=True,prior_payload_unchanged=True,native_position=dict(columns=5106),
        checkpoint_images={'pages-1.img':'3'*64})
    source_gate(run,spec,report)
    for label,where,key,value in [('live','run','status','in_progress'),('failed','run','conclusion','failure'),
        ('rerun','run','run_attempt',2),('wrong-workflow','run','path','other'),
        ('wrong-head','report','source_head','b'*40),('initial','spec','stage','initial'),
        ('wrong-stage','report','stage','sparse'),('no-checkpoint','report','checkpoint_saved',False),
        ('complete','report','full_capture',True),('changed-input','report','protected_inputs_unchanged',False),
        ('changed-prefix','report','prior_payload_unchanged',False),('wrong-columns','report','native_position',dict(columns=5105)),
        ('empty-images','report','checkpoint_images',{})]:
        rr,ss,pp=copy.deepcopy((run,spec,report))
        {'run':rr,'spec':ss,'report':pp}[where][key]=value
        try:source_gate(rr,ss,pp)
        except AssertionError:rejected.append(label)
        else:raise AssertionError('Accepted source corruption '+label)
    for value in (0,GIB,10*GIB):
        assert reserve_bytes(value)>=2*value+8*GIB+512*1024**2
    for args in [(-1,), (0,0), (0,2*GIB)]:
        try:reserve_bytes(*args)
        except AssertionError:rejected.append('invalid-reserve-'+str(args))
        else:raise AssertionError('Invalid reserve accepted')
    with tempfile.TemporaryDirectory(prefix='rhi120-sparse-controls-')as temp:
        fixture=storage.sparse.controls(Path(temp)/'fixtures')
    assert len(rejected)==22
    from publish_pll_rhi120_c8_sparse_checkpoint import controls as publish_controls
    return dict(qualification=qualification(),terminal_publication_fallback=fallback_controls(),source_and_reserve_rejections=rejected,storage_fixture=fixture,
        publication=publish_controls(),baseline_resume=baseline.resume_controls(),
        native_activation_performed=False,full_capture_accepted=False)
if __name__=='__main__':
    print(json.dumps(controls()))
