#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Authenticate one rejected saved capsule and inspect annotations without changing geometry."""
import argparse,copy,json,os,subprocess,sys,traceback
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import ensure_cloud_tested_source_release as release
from run_cloud_tx_layout_repair import sha
from cloud_cdr500_resistor_v59_physical import precreated
ROOT=Path(__file__).resolve().parents[1]
METHOD='scripts/cdr-v59-annotation-diagnostic-methods.json'
REPORT='docs/evidence/cdr-v59-cd-shunt-first-physical-result-20261025.json'
PARTS='docs/evidence/cdr-v59-cd-shunt-first-physical-parts-20261025.json'
GROUP='cdr-v59-annotation-diagnostic'
SOURCE_GROUP='cdr500-resistor-v59-cd_shunt'
RUN=40176503143
HEAD='384ca20f3f482b65687e951d94fedc29dec42613'
SUMMARY_SHA='c07cfcd6f1172d54dd1fdda3cf5d8c69e0522121fcc245a0b85d58ac5fa9258f'
PARTS_SHA='e99e76e6bc8705ef32e1c5ddde0d49666216980ecf670a90647a73d51a2d0b90'
ARCHIVE_SHA='036ea23a5931f10445544eb47a7991de8228a7221cc11e599a114dcd90e8cf68'
APP_SHA='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
PINNED_OUTPUTS={
 'parent/layout/nssoc_cdr_pd500_resistor_v59.gds':'fb2a773c4d3a3ffab6acfe7718a55fa5db0c2621a6c75377940c95a7989b70b5',
 'parent/layout/schematic.cir':'9f70d7af1f26aa07029c8b473e7596f27cd6a50e1dacae4ea16bfd4559fc9f13',
 'parent/inputs/sampler_cd/layout/native-rppd-v59-cd_shunt.gds':'d0463267c8b53af161a7f47384eb6a83578f7d588bf03453729a0d077c66dd18',
 'methods/cdr_v59_recover.py':'29b92f3ae273b3f5bf6f0f9ae4b144c3257b73bf38307500c27f8853d00d90ea',
 'source-annotation-recovery.log':'5fc456912bbe247c195efd39c51e416319d339436c05b2910f744cc66e53d2c9'}
ASSETS={
 'cdr500-resistor-v59-cd_shunt-40176503143-1.summary.json':(674503879,1114546,SUMMARY_SHA),
 'cdr500-resistor-v59-cd_shunt-40176503143-1.parts.json':(674503960,871,PARTS_SHA),
 'cdr500-resistor-v59-cd_shunt-40176503143-1.tar.gz.part0000':(674504018,11816413,ARCHIVE_SHA)}
def write(path,value):
    temporary=path.with_suffix(path.suffix+'.tmp');temporary.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');temporary.replace(path)
def methods():
    m=json.loads((ROOT/METHOD).read_text())
    assert m['scope']=='READ_ONLY_EXISTING_CD_SHUNT_ANNOTATION_WITNESS_NO_GEOMETRY_OR_QUALIFICATION'
    for n,h in m['protected'].items():assert sha(ROOT/n)==h,n
    assert sha(ROOT/REPORT)==SUMMARY_SHA and sha(ROOT/PARTS)==PARTS_SHA
    return m
def validate_run(run,jobs):
    assert run['id']==RUN and run['run_attempt']==1 and run['head_sha']==HEAD
    assert run['path']=='.github/workflows/cdr500-resistor-v59-physical-cloud.yml'
    assert run['event']=='workflow_dispatch'and run['status']=='completed'and run['conclusion']=='failure'
    assert jobs['total_count']==len(jobs['jobs'])==2
    expected={121118217210:('controls','success'),121118312037:('native-physical-and-wires','failure')}
    assert {j['id']for j in jobs['jobs']}==set(expected)
    for j in jobs['jobs']:
        assert j['run_id']==RUN and j['head_sha']==HEAD
        assert(j['name'],j['conclusion'])==expected[j['id']]and j['status']=='completed'
    return True
def validate_assets(assets):
    assert {a['name']for a in assets}==set(ASSETS)and len(assets)==3
    for a in assets:
        ident,size,digest=ASSETS[a['name']]
        assert a['id']==ident and a['size']==size and a['digest']=='sha256:'+digest
    return True
def validate_manifest(m):
    assert m['format']=='ordered-tar-gzip-parts-v1'
    assert m['stem']=='cdr500-resistor-v59-cd_shunt-40176503143-1'
    assert m['source_directory']=='cloud-cdr500-resistor-v59-cd_shunt'
    assert m['bytes']==11816413 and m['sha256']==ARCHIVE_SHA
    assert m['parts']==[dict(index=0,name=m['stem']+'.tar.gz.part0000',bytes=11816413,sha256=ARCHIVE_SHA)]
    return True
def validate_report(r):
    assert r['status']=='FAIL_CDR_V59_NATIVE_PHYSICAL_OR_STRICT_WIRES'
    assert r['source_head']==HEAD and r['arm']=='cd_shunt'
    assert all(r[k]is False for k in('accepted','full_phy_accepted','qualified_pex','wire_rc_extracted','loaded_simulation_started'))
    assert 'sources_unchanged'not in r and 'strict_wire_graph'not in r and 'anchors'not in r
    assert r['error']=="AssertionError(('source-annotation-recovery', 1))"
    assert[(v['label'],v['returncode'])for v in r['commands']]==[
      ('native-generation',0),('physical',0),('fresh-native-planes',0),('source-annotation-recovery',1)]
    assert r['commands'][-1]['log_sha256']==PINNED_OUTPUTS['source-annotation-recovery.log']
    assert len(r['outputs'])==339
    for n,h in PINNED_OUTPUTS.items():assert r['outputs'][n]==h
    physical=r['physical'];assert physical['status']=='PASS_NATIVE_PDK_CDR_PD500_DRC_LVS_AND_FAULT_CONTROLS'
    d=physical['steps']['drc']['measurement'];assert d['status']=='PASS'and d['category_count']==560 and d['markers']==0
    assert len(physical['steps'])==16
    for mode in('lvs','lvs_flat'):
        a=physical['steps'][mode]['audit']
        assert a['status']=='PASS within comparison scope'and a['circuit_status_counts']=={'Match':1}and not a['extraction_diagnostics']
        assert len(a['circuits'])==1 and a['circuits'][0]['layout_devices_recursive']==a['circuits'][0]['schematic_devices_recursive']==500
    assert all(v['status']=='REJECTED_EXPECTED_FAULT'for n,v in physical['steps'].items()if n not in('drc','lvs','lvs_flat'))
    assert r['native_planes']['status']=='PASS_PD500_NATIVE160_PLANES_51_NETS_19_FAULTS'
    assert len(r['native_planes']['controls'])==19 and len(r['native_planes']['parent_geometry']['controls'])==5
    return True
def controls():
    m=methods();r=json.loads((ROOT/REPORT).read_text());parts=json.loads((ROOT/PARTS).read_text())
    run=dict(id=RUN,run_attempt=1,head_sha=HEAD,path='.github/workflows/cdr500-resistor-v59-physical-cloud.yml',
      event='workflow_dispatch',status='completed',conclusion='failure')
    jobs=dict(total_count=2,jobs=[dict(id=i,run_id=RUN,head_sha=HEAD,name=n,status='completed',conclusion=c)
      for i,n,c in[(121118217210,'controls','success'),(121118312037,'native-physical-and-wires','failure')]])
    assets=[dict(name=n,id=i,size=b,digest='sha256:'+h)for n,(i,b,h)in ASSETS.items()]
    assert validate_run(run,jobs)and validate_report(r)and validate_manifest(parts)and validate_assets(assets)
    rejected=[]
    def reject(name,fn):
        try:fn()
        except(AssertionError,KeyError,TypeError):rejected.append(name)
        else:raise AssertionError('Accepted '+name)
    for key,value in [('id',RUN+1),('run_attempt',2),('head_sha','0'*40),('path','other.yml'),
      ('event','push'),('status','in_progress'),('conclusion','success')]:
        a=copy.deepcopy(run);a[key]=value;reject('source_run_'+key,lambda:validate_run(a,jobs))
    for key,value in [('id',1),('run_id',1),('head_sha','0'*40),('status','in_progress'),('conclusion','success')]:
        a=copy.deepcopy(jobs);a['jobs'][1][key]=value;reject('source_job_'+key,lambda:validate_run(run,a))
    edits=[
      ('changed_status',lambda a:a.update(status='PASS')),
      ('claimed_acceptance',lambda a:a.update(accepted=True)),
      ('wrong_arm',lambda a:a.update(arm='ab_hold')),
      ('invented_historical_sources_check',lambda a:a.update(sources_unchanged=True)),
      ('invented_wire_pass',lambda a:a.update(strict_wire_graph={})),
      ('different_failure',lambda a:a.update(error='different')),
      ('missing_original_failure_command',lambda a:a['commands'].pop()),
      ('changed_original_error_log',lambda a:a['commands'][-1].update(log_sha256='0'*64)),
      ('changed_candidate_GDS',lambda a:a['outputs'].update({next(iter(PINNED_OUTPUTS)):'0'*64})),
      ('waived_DRC',lambda a:a['physical']['steps']['drc']['measurement'].update(markers=1)),
      ('missing_old_length_fault',lambda a:a['physical']['steps'].pop('v59_old_length')),
      ('changed_deep_LVS',lambda a:a['physical']['steps']['lvs']['audit']['circuits'][0].update(layout_devices_recursive=499)),
      ('changed_planes',lambda a:a['native_planes']['controls'].pop())]
    for name,edit in edits:
        a=copy.deepcopy(r);edit(a);reject(name,lambda:validate_report(a))
    for key,value in [('bytes',11816412),('sha256','0'*64),('source_directory','other')]:
        a=copy.deepcopy(parts);a[key]=value;reject('manifest_'+key,lambda:validate_manifest(a))
    a=copy.deepcopy(parts);a['parts'][0]['index']=1;reject('manifest_order',lambda:validate_manifest(a))
    for key,value in [('id',1),('size',1),('digest','sha256:'+'0'*64)]:
        a=copy.deepcopy(assets);a[0][key]=value;reject('asset_'+key,lambda:validate_assets(a))
    assert len(rejected)==32
    return dict(status='PASS_32_EXACT_REJECTED_CAPSULE_CONTROLS_NO_NATIVE_EXECUTION',
      rejected=rejected,protected_files=len(m['protected']),original_report_sha256=SUMMARY_SHA,
      native_executed=False,geometry_changed=False,qualification=False)
def main():
    p=argparse.ArgumentParser();p.add_argument('--controls',action='store_true');args=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ['GITHUB_RUN_ATTEMPT']=='1'
    if args.controls:print(json.dumps(controls(),indent=2));return
    m=methods();assert m['readback_authorized']is True
    reservation=precreated(GROUP,wait=True)
    out=ROOT/'hw/soc/out/cloud-cdr-v59-annotation-diagnostic';out.mkdir(parents=True,exist_ok=False)
    staging=ROOT/'.cdr-v59-annotation-source';staging.mkdir(exist_ok=False);reports.OUT=staging
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],run_id=int(os.environ['GITHUB_RUN_ID']),
      release=reservation,accepted=False,qualified_pex=False,electrical_accepted=False,full_phy_accepted=False,
      geometry_regenerated=False,physical_checks_rerun=False,annotation_binding_accepted=False)
    def save():write(out/'result.json',result)
    save()
    try:
        prior=json.loads((ROOT/REPORT).read_text());manifest=json.loads((ROOT/PARTS).read_text())
        validate_report(prior);validate_manifest(manifest)
        run=release.api('actions/runs/'+str(RUN));jobs=release.api('actions/runs/'+str(RUN)+'/attempts/1/jobs?per_page=100')
        validate_run(run,jobs)
        tag='cloud-results-40176503143-1-'+SOURCE_GROUP
        rel=release.api('releases/tags/'+tag);validate_assets(rel['assets'])
        result['original_release']=release.validate_release(rel,release.api('git/ref/tags/'+tag),tag,HEAD)
        capsule=staging/'capsule'
        restored,proof=reports.restore_report(SOURCE_GROUP,RUN,SUMMARY_SHA,PARTS_SHA,capsule,list(prior['outputs']))
        assert restored==prior
        for n,h in prior['outputs'].items():assert sha(capsule/n)==h,n
        assert sha(capsule/'result.json')==SUMMARY_SHA
        result.update(source_run=RUN,source_head_failed=HEAD,restoration=proof,
          preserved_candidate_gds_sha256=PINNED_OUTPUTS['parent/layout/nssoc_cdr_pd500_resistor_v59.gds'],
          preserved_candidate_reference_sha256=PINNED_OUTPUTS['parent/layout/schematic.cir'],
          historical_sources_unchanged_field_was_not_reached=True);save()
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==APP_SHA
        command=[str(app),'python',str(ROOT/'scripts/diagnose_cdr_v59_annotation_native.py'),'--capsule',str(capsule),'--out',str(out/'native')]
        with(out/'native.log').open('wb')as log:rc=subprocess.call(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,
          env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
        result['native_diagnostic']=dict(returncode=rc,log_sha256=sha(out/'native.log'));save()
        if rc:print((out/'native.log').read_text(errors='replace')[-20000:],flush=True)
        assert rc==0
        diagnosis=json.loads((out/'native/diagnosis.json').read_text())
        assert diagnosis['status']=='COMPLETE_READ_ONLY_V59_ANNOTATION_WITNESS_ORIGINAL_REJECTION_RETAINED'
        assert diagnosis['original_failure']['original_rejection_retained']
        assert diagnosis['restored_capsule_files_unchanged']and diagnosis['restored_report_unchanged']
        assert len(diagnosis['native_controls']['rejected'])==4
        assert all(diagnosis[k]is False for k in('annotation_binding_accepted','target_geometry_edited',
          'strict_wire_qualification','qualified_pex','electrical_accepted'))
        for n,h in prior['outputs'].items():assert sha(capsule/n)==h,n
        assert sha(capsule/'result.json')==SUMMARY_SHA
        methods()
        result.update(status='COMPLETE_READ_ONLY_V59_ANNOTATION_DIAGNOSTIC_ORIGINAL_REJECTION_RETAINED',
          diagnosis_sha256=sha(out/'native/diagnosis.json'),
          original_failure=diagnosis['original_failure'],
          missing_primitives=[{k:r[k]for k in('target_cell','original_signature','material_equal_annotated_source_count',
            'distinct_equal_source_pin_sets','unique_pin_set_observed')}for r in diagnosis['all_original_hash_missing_primitives']],
          restored_capsule_files_unchanged=True,current_diagnostic_sources_unchanged=True)
    except BaseException as error:
        result.update(status='FAIL_READ_ONLY_V59_ANNOTATION_DIAGNOSTIC',error=repr(error),traceback=traceback.format_exc());raise
    finally:
        result['outputs']={str(q.relative_to(out)):sha(q)for q in out.rglob('*')if q.is_file()and q!=out/'result.json'};save()
if __name__=='__main__':main()
