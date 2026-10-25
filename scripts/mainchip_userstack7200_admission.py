#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Admit only the exact 40179732322 diagnostic capsule; never relabel its rejection."""
import copy,hashlib,json,os,re,subprocess
from pathlib import Path
import mainchip_latest_userstack_bridge as previous
ROOT=Path(__file__).resolve().parents[1]
METHOD='scripts/mainchip-userstack7200-methods.json'
CAPSULE_PATH='docs/evidence/mainchip-latest-userstack-next-diagnostic-capsule-20261025.json'
CAPSULE_SHA='f0f1f45935ffa2d05d1d74ee050b8062253531c54ecd0bfad685f0f05f979bd1'
RUN=40179732322
HEAD='e4d3ab6d8bc51b8a8c8f5c15e02897da018d44d3'
GROUP='mainchip-route12-userstack'
SUMMARY='62e30d30e57547f990f251313ade2c1a9a9a851b179e7510f7e3224798a3803a'
PARTS='0d516be574eed1e3e39113a3e25e189bd99e56c15f38f1ba039ef61398c4b741'
INNER='e621726bba68b2ae49cc95bf6a84a6714ec3412931ee01f74abb053ccfb711e7'
CONTROLLER='168f08a7ac2e550498638ff3f829294f44340a90daa886871002cb1670079598'
ELF='25a5e9ba1cbb76b820af97cfc8d87b7a2d1bc1203091d83ee4eee859c2e9a04b'
IMAGE='sha256:113cc2e5500e0152a2137336ae092c7caeccb5f8b95b17874fd649d097b8daf8'
NO_PROGRESS='No observable native DRT progress after cross-runner restore'
REQUIRED_INPUTS=copy.deepcopy(previous.ORIGINAL_REQUIRED)
STAGED=None
def sha(raw):return hashlib.sha256(raw).hexdigest()
def file_sha(path):
    with Path(path).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def capsule():
    raw=(ROOT/CAPSULE_PATH).read_bytes();assert sha(raw)==CAPSULE_SHA
    d=json.loads(raw);assert d['run_id']==RUN and d['source_head']==HEAD
    return d
def methods():
    m=json.loads((ROOT/METHOD).read_text())
    for p,h in m['protected'].items():assert file_sha(ROOT/p)==h,p
    assert m['latest_capsule_run']==RUN and m['latest_capsule_source']==HEAD
    assert m['route_segment_s']==7200 and m['original_budget_bounds_s']==[600,7200]
    assert m['gdb_attachment_authorized']is False and m['cold_restart_authorized']is False
    assert m['normal_continuation_preaccepted']is False and m['native_execution_claimed']is False
    return m
def activate_required_inputs():
    m=methods()
    for p,h in m['protected'].items():
        if p in REQUIRED_INPUTS:assert REQUIRED_INPUTS[p]==h
        REQUIRED_INPUTS[p]=h
    return m
def api(path,raw=False):
    cmd=['gh','api','repos/Melihakbulut221/nssoc/'+path]
    if raw:cmd+=['--allow-escape-sequences','-H','Accept: application/octet-stream']
    b=subprocess.check_output(cmd,timeout=180)
    return b if raw else json.loads(b)
def transport_identity(run,release,tag):
    assert run['id']==RUN and run['head_sha']==HEAD and run['run_attempt']==1
    assert run['status']=='completed' and run['conclusion']=='success'
    assert run['path']=='.github/workflows/mainchip-latest-userstack-controls-cloud.yml'
    assert release['id']==423280373 and release['tag_name']=='cloud-results-'+str(RUN)+'-1-'+GROUP
    assert release['draft']is False and tag['object']['type']=='commit' and tag['object']['sha']==HEAD
    assert release['target_commitish']==HEAD and tag['ref']=='refs/tags/'+release['tag_name']
    found={a['id']:a for a in release['assets']};assert len(found)==len(release['assets'])
    for ident,size,digest in [(674649253,21030878,SUMMARY),(674649337,1085,PARTS)]:
        a=found[ident];assert a['size']==size and a['digest']=='sha256:'+digest and a['state']=='uploaded'
    d=capsule()
    for want in d['remote_part_assets']:
        a=found[want['id']]
        assert all(a[k]==want[k]for k in ('name','size','digest'))
        assert a['state']=='uploaded'
    return True
def validate_outer(r):
    d=capsule()
    assert r['source_head']==HEAD and str(r['run_id'])==str(RUN)
    assert r['status']=='PASS_EXACT_SAVED_USERSTACK_DIAGNOSIS_NOT_ROUTING_OR_CONTINUATION'
    assert r['generated_program_sha256']==CONTROLLER
    assert r['inner_controller_result_sha256']==INNER==r['outputs']['inner-controller-result.json']
    assert r['expected_rejection']==d['expected_rejection']
    assert r['native_controller_outcome']=='FAIL_OR_ERROR' and r['native_route_returned']is False
    assert all(r[k]is False for k in ('routing_complete','continuation_accepted','final_timing_complete','full_phy_accepted','historical_sources_unchanged_proven'))
    assert r['scheduling_perturbed']is True
    assert r['new_saved_process_images']==d['new_saved_process_images'] and len(r['new_saved_process_images'])==23
    assert r['outputs']==d['all_output_member_hashes']
    assert {n.removeprefix('checkpoints/state/'):h for n,h in r['outputs'].items()if n.startswith('checkpoints/')}==r['new_saved_process_images']
    assert len([n for n in r['outputs']if n.startswith('work/')])==13
    done=r['native_userstack_finished'];assert done['returncode']==0 and done['target_detached_before_checkpoint']is True
    assert done['report_sha256']==r['observations']['result_sha256']==r['outputs']['native-userstack/result.json']
    report=done['report'];assert report['status']=='PASS_20_EXACT_SAVED_NATIVE_STACK_SAMPLES'
    assert report['runtime_closure']==d['runtime_closure'] and len(report['samples'])==20
    for i,s in enumerate(report['samples']):
        assert s['index']==i and s['reader']['detached']is True
        assert s['command']['returncode']==0 and s['command']['cleanup']['live_remaining']is False
    return r
def source_report(raw):
    assert len(raw)==21030878 and sha(raw)==SUMMARY
    return validate_outer(json.loads(raw))
def selected_names(report):
    selected=sorted(n for n in report['outputs']if n.startswith(('work/','checkpoints/')))
    assert len(selected)==36
    return selected+['inner-controller-result.json','current-inputs-before.json','current-inputs-after.json']
def inner_fields(inner,report):
    assert inner['status']=='FAIL_OR_ERROR' and inner['native_process_saved']is True
    assert inner['source_head']==HEAD and inner['run_id']==RUN and inner['stage']=='cross'
    assert inner['route_complete']is False and inner['final_timing_complete']is False and inner['full_phy_accepted']is False
    assert inner['controller_sha256']==CONTROLLER and inner['checkpointed_elf_sha256']==ELF
    assert inner['image_id']==IMAGE and inner['checkpoint_images']==report['new_saved_process_images']
    assert inner['error']==repr(AssertionError(NO_PROGRESS))
    assert inner['retained_timing_contract']['clock_periods_ns']==[20,4,8,8]
    assert inner['retained_timing_contract']['derating_percent']==5
    assert inner['native_log']['single_entrypoint']is True
    assert inner['native_log']['sha256']==report['outputs']['work/native.log']
    assert 'sources_unchanged'not in inner and 'active_drt_cross_runner_progress_proven'not in inner
    assert all(inner['outputs'][n]==report['outputs'][n]for n in selected_names(report)if n.startswith(('work/','checkpoints/')))
    return True
def validate_restored(report,folder):
    folder=Path(folder);names=selected_names(report)
    for n in names:
        p=folder/n
        assert p.is_file()and not p.is_symlink()and p.resolve().is_relative_to(folder.resolve())
        assert file_sha(p)==report['outputs'][n],n
    raw=(folder/'inner-controller-result.json').read_bytes();assert sha(raw)==INNER
    inner=json.loads(raw);inner_fields(inner,report)
    log=(folder/'work/native.log').read_bytes();boots=(folder/'work/boots.log').read_bytes()
    assert boots==b'native-entrypoint\n' and log.count(b'NSSOC_SAVED_GLOBAL_DRT_BEGIN')==1
    assert sha(log)==inner['native_log']['sha256']
    after=json.loads((folder/'current-inputs-after.json').read_bytes())
    assert after['independent_streamed_hashes_verified']is True
    assert after['historical_sources_unchanged_proven']is False and after['normal_continuation_allowed']is False
    return dict(status='ADMITTED_EXACT_DIAGNOSTIC_FILES_NOT_ACCEPTED_ROUTE_PROGRESS',inner_report=inner,
        preserved_inner_sha256=INNER,image_count=23,work_count=13,native_process_restored=False,
        cold_restart=False,normal_continuation_preaccepted=False)
def descriptor():
    return dict(run=RUN,attempt=1,group=GROUP,source_head=HEAD,summary_sha256=SUMMARY,parts_sha256=PARTS,
        exact_inner_sha256=INNER,generated_controller_sha256=CONTROLLER,
        native_process_saved=True,normal_continuation_preaccepted=False,
        next_phase='reviewed_7200s_same_process_route_attempt')
def rejected_receipt():
    global STAGED
    assert STAGED is None and os.environ.get('GITHUB_ACTIONS')=='true'
    m=activate_required_inputs();assert m['native_process_restore_authorized']is True
    release=api('releases/423280373')
    transport_identity(api('actions/runs/'+str(RUN)),release,api('git/ref/tags/'+release['tag_name']))
    outer=source_report(api('releases/assets/674649253',raw=True))
    import compare_cloud_routed_endpoints as reports
    target=reports.OUT/'latest-admitted-files'
    assert not target.exists()and target.parent.is_dir()
    got,transport=reports.restore_report(GROUP,RUN,SUMMARY,PARTS,target,selected_names(outer))
    assert got==outer
    proof=validate_restored(outer,target);inner=proof['inner_report']
    STAGED=dict(path=target,proof=proof,transport=transport,outer=outer,inner=copy.deepcopy(inner))
    return dict(group=GROUP,run=RUN,summary_sha256=SUMMARY,parts_sha256=PARTS,source_head=HEAD,
        report=inner,exact_inner_sha256=INNER,descriptor=descriptor(),normal_continuation_preaccepted=False)
def restore_failed_capsule(pin,target,old_names):
    global STAGED
    assert STAGED is not None
    assert pin['run']==RUN and pin['source_head']==HEAD and pin['summary_sha256']==SUMMARY and pin['parts_sha256']==PARTS
    assert pin['exact_inner_sha256']==INNER and pin['report']==STAGED['inner'] and pin['descriptor']==descriptor()
    expected=sorted(n for n in STAGED['outer']['outputs']if n.startswith(('work/','checkpoints/')))
    assert sorted(old_names)==expected and len(expected)==36
    target=Path(target);assert not target.exists()and target.parent==STAGED['path'].parent
    first=validate_restored(STAGED['outer'],STAGED['path']);assert first['inner_report']==pin['report']
    STAGED['path'].rename(target)
    second=validate_restored(STAGED['outer'],target);assert second['inner_report']==pin['report']
    proof=dict(exact_diagnostic_file_admission=STAGED['proof'],archive=STAGED['transport'],
        revalidated_after_same_parent_rename=True,latest_run=RUN,latest_inner_sha256=INNER,
        old_admissions_unchanged=True,normal_continuation_preaccepted=False,native_process_restored=False)
    STAGED=None
    return second['inner_report'],proof
# validate_current_rows is appended byte-exact from the qualified previous bridge.

def validate_current_rows(rows,phase,previous=None,required=None):
    assert phase in('before_restore','after_restore')
    assert isinstance(rows,dict)and rows
    required=REQUIRED_INPUTS if required is None else required
    seen={};copy_rows={}
    for label,row in rows.items():
        assert isinstance(label,str)and label and set(row)=={'path','expected_sha256','actual_sha256'}
        p=Path(row['path']);assert p.is_absolute()and p.resolve()==p and p.is_file()and not p.is_symlink()
        assert str(p)not in seen
        expected=row['expected_sha256'];assert re.fullmatch('[0-9a-f]{64}',expected)
        assert row['actual_sha256']==expected and file_sha(p)==expected
        seen[str(p)]=expected;copy_rows[label]=dict(row)
    for n,h in required.items():assert seen.get(str(ROOT/n))==h,('Missing authenticated current input',n)
    if previous is not None:
        assert phase=='after_restore'and previous['phase']=='before_restore'
        assert {k:(v['path'],v['expected_sha256'])for k,v in copy_rows.items()}=={k:(v['path'],v['expected_sha256'])for k,v in previous['files'].items()}
    return dict(phase=phase,files=copy_rows,independent_streamed_hashes_verified=True,
        historical_sources_unchanged_proven=False,normal_continuation_allowed=False)

def verify_current_inputs(callback,phase,previous=None):
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    activate_required_inputs()
    return validate_current_rows(callback(),phase,previous)
