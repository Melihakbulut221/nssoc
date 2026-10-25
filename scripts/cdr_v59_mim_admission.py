#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact recovered v59 inputs for MIM capture; no simulator or geometry producer."""
import copy,json,os,re
from collections import Counter
from pathlib import Path
import cdr_v59_binding_rc_source as saved
import cloud_cdr_v59_publication_recovery as recovery
import ensure_cloud_tested_source_release as release
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
METHOD='scripts/cdr-v59-mim-methods.json'
PREREQUISITE='scripts/cdr-v59-mim-prerequisites.json'
OUT=ROOT/'hw/soc/out/cloud-cdr-v59-mim-precision'
INPUTS=OUT/'inputs'
HEAD='572269f839f34435127a053bdea6a779c2b452fd'
RUN=40193186762
def write(path,value):
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');tmp.replace(path)
def methods():
    m=json.loads((ROOT/METHOD).read_text())
    assert m['scope']=='CURRENT_V59_500_DEVICE_SEVEN_MIM_TWO_ORDER_SOURCE_ONLY'
    for n,h in m['protected'].items():assert sha(ROOT/n)==h,n
    recovery.methods()
    p=json.loads((ROOT/PREREQUISITE).read_text())
    assert p['native_execution_authorized']is False and p['workflow_registered']is False
    assert p['native_census']==dict(devices=500,terminals=1446,ports=25,physical_components=113,
      native_nets=238,electrical_nets=114,logical_anchors=978,physical_anchors=978,
      metal_terminal_references=953,intrinsic_body_terminals=493,models=saved.CENSUS)
    assert p['original_native_run']['id']==RUN and p['original_native_run']['source']==HEAD
    assert p['original_native_run']['conclusion']=='failure'
    return m
def descriptor():return json.loads((ROOT/PREREQUISITE).read_text())
def authorize():
    m=methods()
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ['GITHUB_RUN_ATTEMPT']=='1'
    assert ROOT==saved.CANONICAL_ROOT
    assert m['native_extraction_authorized']is m['native_execution_authorized']is True
    assert m['simulation_authorized']is False and m['geometry_regeneration_authorized']is False
    return m
def local_summary(stage):
    return recovery.exact_summary(stage,recovery.evidence(stage,'-summary.json').read_bytes())
def stage_path(stage):
    assert stage in ('binding','rc')
    return ROOT/('docs/evidence/cdr-v59-'+stage+'-recovered-native-stage-20261025.json')
def stage_report(stage):
    p=descriptor();path=stage_path(stage);spec=p['exact_evidence'][str(path.relative_to(ROOT))]
    assert path.stat().st_size==spec['bytes']and sha(path)==spec['sha256']
    r=json.loads(path.read_text());validate_stage(stage,r)
    return r
def validate_stage(stage,r):
    assert r['source_head']==HEAD and r['sources_unchanged']is True
    assert r['status']==recovery.wrapper.PASS[stage]
    assert r['saved_capsule_integrity']==dict(files=706,all_hashes_unchanged=True)
    for k in ('qualified_pex','full_phy_accepted','closed_loop'):assert r[k]is False,k
    p=descriptor()
    if stage=='binding':
        b=r['binding'];saved.validate_bound_targets(b)
        assert b['census']==saved.CENSUS and len(b['native_ports'])==25 and len(b['node_map'])==114
        assert [d for d in b['devices']if d['model']=='cap_cmim']==p['current_seven_mim_models']
        assert [d for d in b['devices']if d['native_id']in saved.TARGETS]==p['target_lengths']
        assert len(r['controls'])==14 and all(c['rejected']is True for c in r['controls'])
        assert len(r['target_length_controls']['rejected'])==6 and r['target_length_controls']['actual_fresh_binding']is True
        assert len(r['native_contact_comparisons'])==221
        assert len(r['contact_model_controls']['rejected_geometry'])==len(r['contact_model_controls']['rejected_compact_models'])==3
        assert r['native_simulation_passed']is False and r['wire_rc_included']is False
    else:
        g=r['geometry'];a=r['anchors'];audit=r['audit']
        assert g['native_devices']==saved.CENSUS and g['native_device_count']==500
        assert g['native_terminal_count']==1446 and g['wire_component_count']==113
        assert g['native_net_count']==238 and g['native_electrical_net_count']==114
        assert a['logical_anchor_count']==a['physical_anchor_count']==978 and a['public_ports']==25
        assert a['inputs']==saved.ANCHOR_INPUTS
        assert a['dispositions']==dict(ACTUAL_TERMINAL_METAL_POINT_REFERENCE=953,RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE=493)
        assert r['capture']['returncode']==0 and r['capture']['status']=='NATIVE_COMPLETE_AWAITING_RC_AUDIT'
        assert audit['status']=='PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY'
        assert audit['original_devices']==500 and audit['geometry_probes']==978 and audit['physical_wire_components']==113
        assert audit['actual_exported_resistors']==p['raw_audit']['R']and audit['actual_exported_capacitors']==p['raw_audit']['C']
        assert r['controls']['status']=='PASS_REAL_NATIVE_BASELINE_AND13_RAW_CORRUPTION_CONTROLS'
        assert len(r['controls']['cases'])==13 and len(r['new_capsule_outputs'])==421
    return True
def binding_pin():
    return dict(run=RUN,source_head=HEAD,summary_sha256=recovery.PIN['binding']['summary_sha256'],report=stage_report('binding'))
def validate_runs(old,jobs,new,newjobs):
    assert old['id']==RUN and old['run_attempt']==1 and old['head_sha']==HEAD
    assert old['path']==recovery.WORKFLOW and old['event']=='workflow_dispatch'
    assert old['status']=='completed'and old['conclusion']=='failure'
    wanted={121168387181:('controls','success'),121168500687:('native (binding)','failure'),121168500631:('native (rc)','failure')}
    assert jobs['total_count']==len(jobs['jobs'])==3 and {j['id']for j in jobs['jobs']}==set(wanted)
    for j in jobs['jobs']:
        assert j['run_id']==RUN and j['head_sha']==HEAD and j['status']=='completed'
        assert(j['name'],j['conclusion'])==wanted[j['id']]
    p=descriptor();expected=p['recovery_run']
    for key in ('id','head_sha','head_branch','event','run_attempt','status','conclusion'):assert new[key]==expected[key],key
    assert new['path']=='.github/workflows/cdr-v59-publication-recovery-cloud.yml'
    assert newjobs['total_count']==len(newjobs['jobs'])==3
    rows={j['id']:j for j in newjobs['jobs']}
    assert set(rows)=={j['id']for j in p['recovery_jobs']}
    for j in p['recovery_jobs']:
        actual=rows[j['id']]
        assert actual['run_id']==new['id']and actual['head_sha']==new['head_sha']
        assert actual['name']==j['name']and actual['status']=='completed'and actual['conclusion']=='success'
    return True
def validate_release(stage,info,ref):
    pin=descriptor()['publications'][stage]
    assert info['id']==pin['id']
    proof=release.validate_release(info,ref,pin['tag_name'],HEAD)
    keys=('id','name','size','digest')
    assert sorted([{k:a[k]for k in keys}for a in info['assets']],key=lambda a:a['id'])==sorted(
      [{k:a[k]for k in keys}for a in pin['assets']],key=lambda a:a['id'])
    return proof
def expected_bundle(stage):
    r=local_summary(stage)
    return {**r['outputs'],'result.json':recovery.PIN[stage]['summary_sha256']}
def canonical_inventory():
    return {n:v['sha256']for n,v in local_summary('rc')['source_capsule_copy'].items()}
def view_inventory():
    return {n[len('analysis-capsule/'):]:h for n,h in canonical_inventory().items()if n.startswith('analysis-capsule/')}
def manifest(stage):
    path=ROOT/('docs/evidence/cdr-v59-'+stage+'-recovered-native-parts-20261025.json')
    spec=descriptor()['exact_evidence'][str(path.relative_to(ROOT))]
    assert sha(path)==spec['sha256']and path.stat().st_size==spec['bytes']
    return json.loads(path.read_text())
def restore_inputs():
    methods();assert ROOT==saved.CANONICAL_ROOT and not INPUTS.exists()and not saved.CAPSULE.exists()
    INPUTS.mkdir(parents=True)
    old=release.api('actions/runs/'+str(RUN));jobs=release.api('actions/runs/'+str(RUN)+'/attempts/1/jobs?per_page=100')
    nr=descriptor()['recovery_run']['id']
    new=release.api('actions/runs/'+str(nr));nj=release.api('actions/runs/'+str(nr)+'/attempts/1/jobs?per_page=100')
    validate_runs(old,jobs,new,nj)
    proof=dict(original_run_failed=True,recovery_run=nr,stages={},geometry_regenerated=False)
    for stage in ('binding','rc'):
        summary=local_summary(stage);report=stage_report(stage)
        recovery.exact_log(stage,recovery.evidence(stage,'.log').read_bytes())
        spec=descriptor()['publications'][stage];tag=spec['tag_name']
        info=release.api('releases/tags/'+tag)
        reserved=validate_release(stage,info,release.api('git/ref/tags/'+tag))
        folder=INPUTS/(stage+'-transport');folder.mkdir()
        for asset in spec['assets']:
            path=folder/asset['name'];fetch(asset['browser_download_url'],asset['digest'].removeprefix('sha256:'),path)
            assert path.stat().st_size==asset['size']and sha(path)==asset['digest'].removeprefix('sha256:')
        stem=recovery.names(stage)['stem']
        assert (folder/(stem+'.summary.json')).read_bytes()==recovery.evidence(stage,'-summary.json').read_bytes()
        assert (folder/(stem+'.stage-result.json')).read_bytes()==stage_path(stage).read_bytes()
        packed=json.loads((folder/(stem+'.parts.json')).read_text());assert packed==manifest(stage)
        restored=saved.exact_extract(packed,folder,INPUTS/(stage+'-bundle'),expected_bundle(stage))
        assert restored['regular_members']==recovery.PIN[stage]['bundle_files']
        assert sha(INPUTS/(stage+'-bundle/stage/result.json'))==recovery.PIN[stage]['stage_sha256']
        proof['stages'][stage]=dict(run=RUN,head=HEAD,group='cdr-v59-'+stage,
          summary_sha256=recovery.PIN[stage]['summary_sha256'],stage_sha256=recovery.PIN[stage]['stage_sha256'],
          reservation=reserved,full_archive=restored)
        for part in packed['parts']:(folder/part['name']).unlink()
    expected=canonical_inventory();assert len(expected)==1127
    saved.copy_selected(INPUTS/'rc-bundle/source-capsule',saved.CAPSULE,list(expected),expected)
    saved.validate_geometry(json.loads(saved.PIN.read_text()))
    assert all(expected[n]==h for n,h in saved.expected_files(json.loads(saved.PIN.read_text())).items())
    write(INPUTS/'restoration.json',proof)
    verify_restored()
    return proof
def verify_restored():
    for stage in ('binding','rc'):saved.verify_files(INPUTS/(stage+'-bundle'),expected_bundle(stage))
    proof=saved.verify_files(saved.CAPSULE,canonical_inventory())
    saved.validate_geometry(json.loads(saved.PIN.read_text()))
    return dict(all1127_saved_files_unchanged=proof['all_hashes_unchanged'],original706_unchanged=True,
      full_binding763_and_rc1136_bundle_hashes_verified=True,canonical_anchor_paths_unchanged=True)
def project_for_capture(out):
    assert out.parent==OUT and out.name in ('precise','precise_reversed')
    verify_restored();prior=stage_report('rc');bound=stage_report('binding')
    expected=view_inventory();saved.copy_selected(saved.ANALYSIS,out/'source',list(expected),expected)
    binding_files={n:v['sha256']for n,v in local_summary('binding')['stage_copy'].items()}
    saved.copy_selected(INPUTS/'binding-bundle/stage',out/'model-binding',list(binding_files),binding_files)
    binding=json.loads((out/'model-binding/binding.json').read_text());assert binding==bound['binding']
    proof=json.loads((INPUTS/'restoration.json').read_text())
    return prior,proof['stages']['rc'],bound,proof['stages']['binding'],binding
def verify_projection(out):
    saved.verify_files(out/'source',view_inventory())
    binding_files={n:v['sha256']for n,v in local_summary('binding')['stage_copy'].items()}
    saved.verify_files(out/'model-binding',binding_files)
    return verify_restored()
