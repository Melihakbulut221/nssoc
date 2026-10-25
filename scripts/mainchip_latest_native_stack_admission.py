#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Strict file admission for the latest saved process. Never restores/starts a process."""
import copy,hashlib,json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASIS=ROOT/'hw/soc/diagnostic-source-basis/userstack'
RUN=40120760532
HEAD='84b513cb437b68af0f4cb22bc4707db1a35958cf'
GROUP='mainchip-route12-observed'
SUMMARY='1e21e2c65b9264727bd6abd502da805023b53c1e3a0d943aba8743c072ebc0c2'
PARTS='1cd467372d2b8629169f2d77290164a611a844ebfc61e5fc486aa68b1a8c36d1'
INNER='2681afcb8475beca15fc6cf1b1b21c48703a28105abd3e05ae8159b9221a0440'
CONTROLLER='adc703fa0b22d259393fd19b5419d974193b59dcbd2ae9c462a8983e23c0e244'
ELF='25a5e9ba1cbb76b820af97cfc8d87b7a2d1bc1203091d83ee4eee859c2e9a04b'
IMAGE='sha256:113cc2e5500e0152a2137336ae092c7caeccb5f8b95b17874fd649d097b8daf8'
NATIVE_PROCESS_RESTORE_AUTHORIZED=False
def sha(raw):return hashlib.sha256(raw).hexdigest()
def file_sha(p):
    with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()

def source_report(raw):
    assert sha(raw)==SUMMARY and len(raw)==25625
    r=json.loads(raw)
    assert r['source_head']==HEAD and str(r['run_id'])==str(RUN)
    assert r['generated_program_sha256']==CONTROLLER
    assert r['status']=='PASS_IDENTITY_BOUND_PROCESS_DIAGNOSIS_NOT_ROUTING_OR_CONTINUATION'
    assert r['expected_rejection']['original_no_log_progress_rejection_reproduced']is True
    assert r['expected_rejection']['code_object_bound']is True
    assert r['native_controller_outcome']=='FAIL_OR_ERROR' and r['native_route_returned']is False
    assert r['inner_controller_result_sha256']==INNER==r['outputs']['inner-controller-result.json']
    assert all(r[k]is False for k in ('routing_complete','continuation_accepted','final_timing_complete','full_phy_accepted'))
    images=r['new_saved_process_images']
    assert len(images)==23 and all('/'not in n and n not in ('.','..')for n in images)
    assert {n.removeprefix('checkpoints/state/'):h for n,h in r['outputs'].items()if n.startswith('checkpoints/')}==images
    work={n:h for n,h in r['outputs'].items()if n.startswith('work/')}
    assert len(work)==13
    assert work['work/native.log']=='bcfc275fba12aaae1879727ebf90a8fdc9d9833dbd9aa23dd131619498d0f41e'
    assert work['work/boots.log']=='d6517f61034b9578e0ffe62cf86a12ca3a675a8281fa6ed80f9c4e4fcfd40d48'
    return r

def transport_identity(run,release,tag):
    assert run['id']==RUN and run['head_sha']==HEAD and run['run_attempt']==1
    assert run['status']=='completed' and run['conclusion']=='success'
    assert run['path']=='.github/workflows/mainchip-observed-diagnostic-cloud.yml'
    assert release['id']==422907570 and release['tag_name']=='cloud-results-'+str(RUN)+'-1-'+GROUP
    assert release['draft']is False and tag['object']['type']=='commit' and tag['object']['sha']==HEAD
    pins={673038055:(25625,SUMMARY),673038110:(1081,PARTS)}
    found={a['id']:a for a in release['assets']}
    assert len(found)==len(release['assets'])
    for ident,(size,digest)in pins.items():
        a=found[ident];assert a['size']==size and a['digest']=='sha256:'+digest and a['state']=='uploaded'
    return True

def selected_names(report):
    selected=sorted(n for n in report['outputs']if n.startswith(('work/','checkpoints/')))
    assert len(selected)==36
    return selected+['inner-controller-result.json','current-inputs-before.json','current-inputs-after.json']

def validate_restored(report,folder):
    folder=Path(folder);names=selected_names(report)
    for n in names:
        p=folder/n
        assert p.is_file()and not p.is_symlink()and p.resolve().is_relative_to(folder.resolve())
        assert file_sha(p)==report['outputs'][n],n
    raw=(folder/'inner-controller-result.json').read_bytes()
    assert len(raw)==79432 and sha(raw)==INNER
    inner=json.loads(raw)
    assert inner['status']=='FAIL_OR_ERROR' and inner['native_process_saved']is True
    assert inner['native_log']['single_entrypoint']is True
    assert inner['controller_sha256']==CONTROLLER and inner['checkpointed_elf_sha256']==ELF
    assert inner['image_id']==IMAGE and inner['checkpoint_images']==report['new_saved_process_images']
    assert inner['retained_timing_contract']['clock_periods_ns']==[20,4,8,8]
    assert inner['retained_timing_contract']['derating_percent']==5
    assert all(inner['outputs'][n]==report['outputs'][n]for n in names if n.startswith(('work/','checkpoints/')))
    # Exact bytes and entrypoint are checked again; no new source_unchanged claim is invented.
    log=(folder/'work/native.log').read_bytes();boots=(folder/'work/boots.log').read_bytes()
    assert boots==b'native-entrypoint\n'
    assert log.count(b'NSSOC_SAVED_GLOBAL_DRT_BEGIN')==1
    assert sha(log)==inner['native_log']['sha256']
    return dict(status='ADMITTED_EXACT_SAVED_FILES_NOT_LIVE_RESTORE',inner_report=inner,
        preserved_inner_sha256=INNER,image_count=23,work_count=13,native_process_restored=False,
        native_process_started=False,normal_continuation_accepted=False,route_progress_proven=False)

def restore_files_only(target):
    """Future reviewed controller may call this; fixture workflow never does."""
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    assert NATIVE_PROCESS_RESTORE_AUTHORIZED is False
    m=json.loads((ROOT/'scripts/mainchip-userstack-fixture-methods.json').read_text())
    assert m['native_process_restore_authorized']is False and m['native_attachment_authorized']is False
    for p,h in m['protected'].items():assert file_sha(ROOT/p)==h,p
    import compare_cloud_routed_endpoints as reports
    import subprocess
    def api(p):return json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/'+p]))
    raw=(BASIS/'mainchip-observed-native-result.json').read_bytes();r=source_report(raw)
    release=api('releases/422907570')
    transport_identity(api('actions/runs/'+str(RUN)),release,api('git/ref/tags/'+release['tag_name']))
    target=Path(target);assert target.is_absolute()and not target.exists()
    assert target.parent.is_dir()and target.parent.resolve()==target.parent
    reports.OUT=target.parent/'latest-capsule-transport'
    reports.OUT.mkdir(exist_ok=False)
    got,proof=reports.restore_report(GROUP,RUN,SUMMARY,PARTS,target,selected_names(r))
    assert got==r
    admitted=validate_restored(r,target);admitted['archive_proof']=proof
    return admitted
