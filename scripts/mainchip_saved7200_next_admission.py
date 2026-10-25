#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Admit exact saved 40185550438 files and reprove its log progress before restore."""
import copy,hashlib,json,math,os,re,subprocess,tarfile
from pathlib import Path,PurePosixPath
import mainchip_userstack7200_admission as frozen_admission
import cloud_mainchip_route12_drt_continuation as original
from cloud_verified_parts import JoinedParts
from cloud_chunked_results import verify_parts
ROOT=Path(__file__).resolve().parents[1]
METHOD='scripts/mainchip-saved7200-next-methods.json'
CAPSULE_PATH='docs/evidence/mainchip-userstack7200-next-capsule-descriptor-20261025.json'
CAPSULE_SHA='d3811b13ad8391b7b17ef12f711cd1de680cd2c2977107d0321ca5c1cf8e0972'
RUN=40185550438
HEAD='85f1aeee0e92eb4ad8c4f16fa98814ea30c3f60c'
GROUP='mainchip-route12-userstack7200'
SUMMARY='fdaaf970e566fd1fef38163048836fad0084657424b022677a1ff9815e3644db'
PARTS='75bb05599d2f54649cb46b3012c4d059eb772fcd48d0cdda5caa9c8c25303d30'
INNER='1882a7cc7e91ddd029f97d23cbc0f5b00b099a940a53def0554d53eb647993b4'
CONTROLLER='f9e517e4430f84d1cf7cb20f9232c91237bc8c928cc77d93b84b3c4d9e2d8622'
ELF=frozen_admission.ELF
IMAGE=frozen_admission.IMAGE
ADDONS={'criu-build.log','criu-build.json'}
REQUIRED_INPUTS=copy.deepcopy(frozen_admission.REQUIRED_INPUTS)
STAGED=None
PRIOR_EVIDENCE=None
def sha(raw):return hashlib.sha256(raw).hexdigest()
def file_sha(path):
    with Path(path).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def capsule():
    raw=(ROOT/CAPSULE_PATH).read_bytes();assert sha(raw)==CAPSULE_SHA
    d=json.loads(raw);assert d['run']==RUN and d['source_ref']==HEAD
    d['runtime_closure']=frozen_admission.capsule()['runtime_closure']
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
api=frozen_admission.api
def transport_identity(run,release,tag,jobs):
    assert run['id']==RUN and run['head_sha']==HEAD and run['run_attempt']==1
    assert run['status']=='completed' and run['conclusion']=='success'
    assert run['head_branch']=='codex/mainchip7200-native-85f1aeee'
    assert run['path']=='.github/workflows/mainchip-userstack7200-continuation-cloud.yml'
    assert {j['id']:j['name'] for j in jobs}=={121145461460:'source-controls',121145553802:'exact-saved-route'}
    assert all(j['status']=='completed'and j['conclusion']=='success'for j in jobs)
    assert release['id']==423327513 and release['tag_name']=='cloud-results-'+str(RUN)+'-1-'+GROUP
    assert release['draft']is False and release['prerelease']is True
    assert tag['object']['type']=='commit' and tag['object']['sha']==HEAD
    assert release['target_commitish']==HEAD and tag['ref']=='refs/tags/'+release['tag_name']
    found={a['id']:a for a in release['assets']};assert len(found)==len(release['assets'])
    assert len({a['name']for a in release['assets']})==len(found)
    for ident,name,size,digest in [
      (675060096,GROUP+'-'+str(RUN)+'-1.summary.json',55611,SUMMARY),
      (675060158,GROUP+'-'+str(RUN)+'-1.parts.json',1101,PARTS)]:
        a=found[ident];assert a['name']==name and a['size']==size and a['digest']=='sha256:'+digest and a['state']=='uploaded'
    for want in capsule()['part_assets']:
        a=found[want['id']]
        assert all(a[k]==want[k]for k in ('name','size','digest'))
        assert a['state']=='uploaded'
    return True
def validate_outer(r):
    d=capsule()
    assert r['source_head']==HEAD and str(r['run_id'])==str(RUN) and r['group']==GROUP
    assert r['status']=='SAVED_SAME_PROCESS_ORIGINAL_LOG_PROGRESS_GATES_PASSED_NOT_ROUTE_COMPLETE'
    assert r['generated_program_sha256']==CONTROLLER
    assert r['inner_controller_result_sha256']==INNER==r['outputs']['inner-controller-result.json']
    assert r['native_controller_outcome']=='SAVED_CROSS_RUNNER_ACTIVE_DRT_PROGRESS_REQUIRES_FURTHER_CONTINUATION_AND_SIGNOFF'
    assert r['continuation_accepted']is True and r['requested_budget_s']==7200
    assert all(r[k]is False for k in ('native_route_returned','routing_complete','final_timing_complete','full_phy_accepted','historical_sources_unchanged_proven','gdb_attached','cold_restart'))
    assert r['old_scheduling_perturbation_retained']is True
    assert r['new_saved_process_images']==d['saved_images'] and len(r['new_saved_process_images'])==23
    assert r['outputs']==d['expected_outputs'] and len(r['outputs'])==74
    assert {n.removeprefix('checkpoints/state/'):h for n,h in r['outputs'].items()if n.startswith('checkpoints/')}==r['new_saved_process_images']
    assert len([n for n in r['outputs']if n.startswith('work/')])==14
    a=r['current_inputs_after']
    assert a['phase']=='after_restore'and a['independent_streamed_hashes_verified']is True
    assert a['historical_sources_unchanged_proven']is False and a['normal_continuation_allowed']is False
    assert a['files'] and all(x['expected_sha256']==x['actual_sha256']for x in a['files'].values())
    return r
def source_report(raw):
    assert len(raw)==55611 and sha(raw)==SUMMARY
    return validate_outer(json.loads(raw))
def inner_fields(inner,report):
    assert inner['status']=='SAVED_CROSS_RUNNER_ACTIVE_DRT_PROGRESS_REQUIRES_FURTHER_CONTINUATION_AND_SIGNOFF'
    assert inner['native_process_saved']is True and inner['restored_native_process']is True
    assert inner['sources_unchanged']is True and inner['active_drt_cross_runner_progress_proven']is True
    assert inner['source_head']==HEAD and inner['run_id']==RUN and inner['stage']=='cross'
    assert inner['route_complete']is False and inner['final_timing_complete']is False and inner['full_phy_accepted']is False
    assert 'error'not in inner and 'traceback'not in inner
    assert inner['controller_sha256']==CONTROLLER and inner['checkpointed_elf_sha256']==ELF
    assert inner['image_id']==IMAGE and inner['checkpoint_images']==report['new_saved_process_images']
    assert all(inner[k]==v for k,v in original.GLOBAL_INPUTS.items())
    assert inner['retained_timing_contract']['clock_periods_ns']==[20,4,8,8]
    assert inner['retained_timing_contract']['derating_percent']==5
    assert inner['retained_timing_contract']['new_native_sta_run_required']is True
    assert inner['native_log']['single_entrypoint']is True
    assert inner['native_log']['sha256']==report['outputs']['work/native.log']
    assert all(inner['outputs'][n]==h for n,h in report['outputs'].items()if n.startswith(('work/','checkpoints/')))
    c=inner['continuation']
    assert {k:c[k]for k in ('run','attempt','group','source_head','controller_sha256')}==dict(run=RUN,attempt=1,group=GROUP,source_head=HEAD,controller_sha256=CONTROLLER)
    assert c['native_process_saved']is True and c['next_phase']=='continue_same_native_process'
    v=inner['unobserved_runtime_binding']
    assert v['status']=='PASS_EXACT_RUNTIME_CLOSURE_WITHOUT_GDB'and v['runtime_closure']==capsule()['runtime_closure']
    assert v['target_detached']is True and v['gdb_attached']is False
    assert type(inner['segment_elapsed_s'])in(int,float)and math.isfinite(inner['segment_elapsed_s'])and inner['segment_elapsed_s']>0
    return True
def native_log_evidence(inner,old_inner,raw,boots):
    """Recompute the original saved-segment predicates; no CPU-only acceptance."""
    got=original.log_proof(raw,boots)
    assert got==inner['native_log']
    n=old_inner['native_log']['bytes'];assert type(n)is int and 0<n<len(raw)
    prefix=raw[:n];assert sha(prefix)==old_inner['native_log']['sha256']
    assert original.log_proof(prefix,boots)==old_inner['native_log']
    assert len(raw)>len(prefix),'No observable native DRT progress after cross-runner restore'
    appended=raw[len(prefix):].decode()
    assert re.search(r'Completing\s+\d+%|Start \d+(?:st|nd|rd|th) optimization iteration|Number of violations',appended),'No native optimization progress witness after restore'
    assert inner['restored_work_prefixes_verified']['work/native.log']==sha(prefix)
    controls=original.log_controls(raw,boots);assert controls==inner['controls'] and len(controls)==4
    return dict(status='PASS_RECOMPUTED_ORIGINAL_SAVED_SEGMENT_LOG_GATES_NOT_ROUTE_COMPLETION',
        complete_log=got,prior_prefix_bytes=n,prior_prefix_sha256=sha(prefix),
        appended_bytes=len(raw)-n,appended_sha256=sha(raw[n:]),original_four_log_controls=controls,
        segment_elapsed_s=inner['segment_elapsed_s'],early_checkpoint_reason=inner.get('early_checkpoint_reason'),
        routing_complete=False,final_timing_complete=False,historical_sources_unchanged_proven=False,
        old_scheduling_perturbation_retained=True)
def canonical_member(entry,prefix,seen):
    name=entry.name;p=PurePosixPath(name)
    assert isinstance(name,str)and name and '\\'not in name and str(p)==name
    assert not p.is_absolute()and '..'not in p.parts and p.parts[0]==prefix
    assert name not in seen and (entry.isfile()or entry.isdir()),'Duplicate or special member'
    seen.add(name)
    return str(p.relative_to(prefix))
def complete_extract(manifest,parts,destination,expected):
    """All recorded bytes plus two source-derived publication additions, once."""
    proof=verify_parts(manifest,parts)
    prefix=manifest['source_directory'];assert Path(prefix).name==prefix and prefix not in('','.','..')
    assert expected and not(ADDONS&set(expected))
    for n in expected:
        assert str(PurePosixPath(n))==n and not PurePosixPath(n).is_absolute()and '..'not in PurePosixPath(n).parts and '\\'not in n
    destination=Path(destination);assert not destination.exists();destination.mkdir(parents=True)
    seen=set();found={};addons={}
    with JoinedParts([parts/p['name']for p in manifest['parts']])as joined:
        with tarfile.open(fileobj=joined,mode='r|gz')as archive:
            for entry in archive:
                relative=canonical_member(entry,prefix,seen)
                if entry.isdir():
                    assert relative=='.'or any(n.startswith(relative+'/')for n in set(expected)|ADDONS),'Unrecorded directory'
                    continue
                assert relative in expected or relative in ADDONS,'Unrecorded original file: '+relative
                target=destination/relative;target.parent.mkdir(parents=True,exist_ok=True)
                digest=hashlib.sha256();total=0
                with archive.extractfile(entry)as source,target.open('xb')as output:
                    for block in iter(lambda:source.read(1048576),b''):output.write(block);digest.update(block);total+=len(block)
                assert total==entry.size
                row=dict(bytes=total,sha256=digest.hexdigest())
                if relative in expected:
                    assert row['sha256']==expected[relative],relative;found[relative]=row
                else:
                    row['attestation']='Whole authenticated archive only; workflow-added after result inventory'
                    addons[relative]=row
    assert set(found)==set(expected)and set(addons)==ADDONS
    return dict(archive=proof,original_members=found,publication_additions=addons,
        full_archive_verified_before_extraction=True,all_original_members_verified=True)
def validate_restored(report,folder):
    folder=Path(folder)
    for n,h in report['outputs'].items():
        p=folder/n
        assert p.is_file()and not p.is_symlink()and p.resolve().is_relative_to(folder.resolve())
        assert file_sha(p)==h,n
    assert file_sha(folder/'result.json')==SUMMARY
    raw=(folder/'inner-controller-result.json').read_bytes();assert sha(raw)==INNER
    inner=json.loads(raw);inner_fields(inner,report)
    prior=frozen_admission.source_report((folder/'initial/result.json').read_bytes())
    oldraw=(folder/'initial/inner-controller-result.json').read_bytes()
    assert sha(oldraw)==frozen_admission.INNER
    old_inner=json.loads(oldraw);frozen_admission.inner_fields(old_inner,prior)
    log=(folder/'work/native.log').read_bytes();boots=(folder/'work/boots.log').read_bytes()
    logproof=native_log_evidence(inner,old_inner,log,boots)
    assert json.loads((folder/'current-inputs-after.json').read_bytes())==report['current_inputs_after']
    assert json.loads((folder/'no-gdb-runtime-result.json').read_bytes())==inner['unobserved_runtime_binding']
    return dict(status='ADMITTED_EXACT_SAVED_SEGMENT_AND_RECOMPUTED_LOG_GATES_BEFORE_RESTORE',
        inner_report=inner,prior_diagnostic_inner_sha256=frozen_admission.INNER,
        inner_sha256=INNER,native_log=logproof,image_count=23,work_count=14,
        native_process_restored=False,cold_restart=False,normal_continuation_preaccepted=False,
        historical_sources_unchanged_proven=False,old_scheduling_perturbation_retained=True)
def descriptor():
    return dict(run=RUN,attempt=1,group=GROUP,source_head=HEAD,summary_sha256=SUMMARY,parts_sha256=PARTS,
        exact_inner_sha256=INNER,generated_controller_sha256=CONTROLLER,native_process_saved=True,
        normal_continuation_preaccepted=False,next_phase='reviewed_7200s_same_process_route_attempt')
def saved_receipt():
    global STAGED,PRIOR_EVIDENCE
    assert STAGED is None and PRIOR_EVIDENCE is None and os.environ.get('GITHUB_ACTIONS')=='true'
    m=activate_required_inputs();assert m['native_process_restore_authorized']is True
    release=api('releases/423327513')
    transport_identity(api('actions/runs/'+str(RUN)),release,api('git/ref/tags/'+release['tag_name']),
        api('actions/runs/'+str(RUN)+'/jobs?per_page=100')['jobs'])
    summary_raw=api('releases/assets/675060096',raw=True);outer=source_report(summary_raw)
    manifest_raw=api('releases/assets/675060158',raw=True);assert len(manifest_raw)==1101 and sha(manifest_raw)==PARTS
    manifest=json.loads(manifest_raw);d=capsule()
    assert manifest['bytes']==d['archive_bytes']and manifest['sha256']==d['archive_sha256']
    stem=GROUP+'-'+str(RUN)+'-1'
    assert manifest['stem']==stem and manifest['source_directory']=='cloud-'+GROUP
    assert len(manifest['parts'])==2
    import compare_cloud_routed_endpoints as reports
    folder=reports.OUT/'saved7200-capsule-transport';folder.mkdir()
    (folder/'summary.json').write_bytes(summary_raw)
    (folder/'parts.json').write_bytes(manifest_raw)
    for i,p in enumerate(manifest['parts']):
        assert p['index']==i and p['name']==stem+'.tar.gz.part'+str(i).zfill(4)
        a=d['part_assets'][i];assert a['name']==p['name']and a['size']==p['bytes']and a['digest']=='sha256:'+p['sha256']
        reports.fetch(a['browser_download_url'],p['sha256'],folder/p['name'])
    target=reports.OUT/'latest-admitted-files';expected=dict(outer['outputs']);expected['result.json']=SUMMARY
    transport=complete_extract(manifest,folder,target,expected)
    for p in manifest['parts']:(folder/p['name']).unlink()
    proof=validate_restored(outer,target);inner=proof['inner_report'];PRIOR_EVIDENCE=copy.deepcopy(proof)
    (reports.OUT/'prior-capsule-admission.json').write_text(json.dumps(proof,indent=2)+'\n')
    for src,dst in [('inner-controller-result.json','prior-inner-controller-result.json'),('work/native.log','prior-native.log')]:
        (reports.OUT/dst).write_bytes((target/src).read_bytes())
    STAGED=dict(path=target,proof=proof,transport=transport,outer=outer,inner=copy.deepcopy(inner))
    return dict(group=GROUP,run=RUN,summary_sha256=SUMMARY,parts_sha256=PARTS,source_head=HEAD,
        report=inner,exact_inner_sha256=INNER,descriptor=descriptor(),normal_continuation_preaccepted=False)
def restore_saved_capsule(pin,target,old_names):
    global STAGED
    assert STAGED is not None
    assert pin['run']==RUN and pin['source_head']==HEAD and pin['summary_sha256']==SUMMARY and pin['parts_sha256']==PARTS
    assert pin['exact_inner_sha256']==INNER and pin['report']==STAGED['inner'] and pin['descriptor']==descriptor()
    expected=sorted(n for n in STAGED['outer']['outputs']if n.startswith(('work/','checkpoints/')))
    assert sorted(old_names)==expected and len(expected)==37
    target=Path(target);assert not target.exists()and target.parent==STAGED['path'].parent
    first=validate_restored(STAGED['outer'],STAGED['path']);assert first['inner_report']==pin['report']
    STAGED['path'].rename(target)
    second=validate_restored(STAGED['outer'],target);assert second['inner_report']==pin['report']
    proof=dict(exact_saved_segment_admission=STAGED['proof'],archive=STAGED['transport'],
        revalidated_after_same_parent_rename=True,latest_run=RUN,latest_inner_sha256=INNER,
        old_admissions_unchanged=True,normal_continuation_preaccepted=False,native_process_restored=False)
    STAGED=None
    return second['inner_report'],proof

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
