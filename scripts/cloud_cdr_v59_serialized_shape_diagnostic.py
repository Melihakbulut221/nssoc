#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read the exact failed static sidecar; retain every original rejection."""
import argparse,copy,hashlib,json,os,shutil,subprocess,sys,tarfile,traceback
from pathlib import Path
import cloud_cdr_v59_static_source_recovery as previous
import cdr_v59_serialized_shape_diagnostic as observer
import ensure_cloud_tested_source_release as release
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
METHOD='scripts/cdr-v59-serialized-shape-diagnostic-methods.json'
REPORT='docs/evidence/cdr-v59-static-source-first-result-20261025.json'
PARTS='docs/evidence/cdr-v59-static-source-first-parts-20261025.json'
NATIVE='docs/evidence/cdr-v59-static-source-first-materialization-20261025.json'
RUN=40182758502;HEAD='d0427b472ed9a1f3330adb7d95ef4cb31790d09f'
SUMMARY_SHA='305e2c3791cbbb7104da7a2e80e2ed93e5e00d44ee3a06906688eab67f031cef'
PARTS_SHA='b8cd62bcd3288a570061c720454d70edc27e196aa8dfe3dfaeb0e1a1075e841a'
NATIVE_SHA='f95dbec52d135dacb97f5757bb0ec106f4c59d604e476e9ac4c8f7d96583c9ab'
ARCHIVE_SHA='8c58f031e12d6e86de66722b865e6b5d5b9c2d7add326f4fcc2c4382ed8eb99e'
GROUP='cdr-v59-serialized-shape-diagnostic'
SOURCE_GROUP='cdr-v59-static-source-recovery'
ASSETS={
 'cdr-v59-static-source-recovery-40182758502-1.summary.json':(674685964,110110,SUMMARY_SHA),
 'cdr-v59-static-source-recovery-40182758502-1.parts.json':(674686030,877,PARTS_SHA),
 'cdr-v59-static-source-recovery-40182758502-1.materialization.json':(674686178,4203,NATIVE_SHA),
 'cdr-v59-static-source-recovery-40182758502-1.static-source.gds':(674686251,2910,observer.SIDECAR_SHA),
 'cdr-v59-static-source-recovery-40182758502-1.tar.gz.part0000':(674686103,11968301,ARCHIVE_SHA)}
def write(path,value):previous.write(path,value)
def methods():
    m=json.loads((ROOT/METHOD).read_text())
    assert m['scope']=='READ_ONLY_EXACT_FAILED_STATIC_SIDECAR_RAW_TEXT_PIN_DIAGNOSIS'
    for n,h in m['protected'].items():assert sha(ROOT/n)==h,n
    for n,h in((REPORT,SUMMARY_SHA),(PARTS,PARTS_SHA),(NATIVE,NATIVE_SHA)):assert sha(ROOT/n)==h
    previous.methods()
    _,proof=observer.derive((ROOT/observer.FROZEN).read_text())
    assert proof['generated_sha256']==m['native_derived_sha256']and len(proof['reversible_edits'])==4
    return m
def validate_report(r):
    assert r['status']=='FAIL_SAVED_CD_SHUNT_STATIC_SOURCE_OR_STRICT_WIRES'
    assert r['run_id']==RUN and r['source_head']==HEAD
    assert all(r[k]is False for k in('accepted','qualified_pex','wire_rc_extracted','electrical_accepted','full_phy_accepted','geometry_regenerated','physical_checks_rerun'))
    assert all(r[k]is True for k in('all339_original_files_unchanged','original_report_unchanged','runtime_files_unchanged','current_recovery_sources_unchanged'))
    assert r['error']=="AssertionError(('static-native-source-and-exact-recovery', 1))"
    assert r['commands']==[dict(label='static-native-source-and-exact-recovery',returncode=1,
      log_sha256='5b5387150aac56bb4de5ce6b499ec15a19279908afcdc2c352dbb512adb0fcfa')]
    original=json.loads((ROOT/previous.saved.REPORT).read_text());previous.saved.validate_report(original)
    assert len(r['outputs'])==345
    for n,h in original['outputs'].items():assert r['outputs']['capsule/'+n]==h,n
    assert r['outputs']['capsule/result.json']==previous.saved.SUMMARY_SHA
    assert r['outputs']['capsule/'+previous.SIDECAR]==observer.SIDECAR_SHA
    assert r['outputs']['native/materialization.json']==NATIVE_SHA
    assert 'annotation_materialization'not in r and 'strict_wire_graph'not in r
    return True
def validate_manifest(m):
    assert m['format']=='ordered-tar-gzip-parts-v1'
    assert m['stem']=='cdr-v59-static-source-recovery-40182758502-1'
    assert m['source_directory']=='cloud-cdr-v59-static-source-recovery'
    assert m['bytes']==11968301 and m['sha256']==ARCHIVE_SHA
    assert m['parts']==[dict(index=0,name=m['stem']+'.tar.gz.part0000',bytes=11968301,sha256=ARCHIVE_SHA)]
    return True
def validate_assets(assets):
    assert len(assets)==5 and {a['name']for a in assets}==set(ASSETS)
    for a in assets:
        ident,size,h=ASSETS[a['name']]
        assert a['id']==ident and a['size']==size and a['digest']=='sha256:'+h
    return True
def validate_run(r,j):
    assert r['id']==RUN and r['head_sha']==HEAD and r['run_attempt']==1
    assert r['path']=='.github/workflows/cdr-v59-static-source-recovery-cloud.yml'
    assert r['event']=='workflow_dispatch'and r['status']=='completed'and r['conclusion']=='failure'
    expected={121137112524:('controls','success'),121137203223:('static-source-and-strict-wires','failure')}
    assert j['total_count']==len(j['jobs'])==2 and {v['id']for v in j['jobs']}==set(expected)
    for v in j['jobs']:
        assert v['run_id']==RUN and v['head_sha']==HEAD and v['status']=='completed'
        assert(v['name'],v['conclusion'])==expected[v['id']]
    return True
def controls():
    m=methods();inherited=previous.controls();assert len(inherited['rejected'])==20
    assert len(inherited['original_capsule_controls']['rejected'])==32
    source=observer.controls();assert len(source['rejected'])==9
    r=json.loads((ROOT/REPORT).read_text());validate_report(r);rejected=[]
    def reject(label,original,change,validate):
        q=copy.deepcopy(original);change(q)
        try:validate(q)
        except(AssertionError,KeyError):rejected.append(label)
        else:raise AssertionError('Accepted '+label)
    for key,value in [('status','PASS'),('source_head','0'*40),('run_id',1),
      ('accepted',True),('geometry_regenerated',True),('all339_original_files_unchanged',False),
      ('runtime_files_unchanged',False),('error','different')]:
        reject(key,r,lambda q,k=key,v=value:q.__setitem__(k,v),validate_report)
    for label,change in [
      ('changed_actual_sidecar',lambda q:q['outputs'].__setitem__('capsule/'+previous.SIDECAR,'0'*64)),
      ('changed_original_gds',lambda q:q['outputs'].__setitem__('capsule/parent/layout/nssoc_cdr_pd500_resistor_v59.gds','0'*64)),
      ('changed_original_report',lambda q:q['outputs'].__setitem__('capsule/result.json','0'*64)),
      ('missing_original_member',lambda q:q['outputs'].pop(next(iter(q['outputs']))))]:
        reject(label,r,change,validate_report)
    run=dict(id=RUN,head_sha=HEAD,run_attempt=1,path='.github/workflows/cdr-v59-static-source-recovery-cloud.yml',
      event='workflow_dispatch',status='completed',conclusion='failure')
    jobs=dict(total_count=2,jobs=[dict(id=i,run_id=RUN,head_sha=HEAD,name=n,status='completed',conclusion=c)
      for i,n,c in((121137112524,'controls','success'),(121137203223,'static-source-and-strict-wires','failure'))])
    validate_run(run,jobs)
    for key,value in(('run_attempt',2),('head_sha','0'*40),('conclusion','success'),('status','in_progress')):
        reject('runtime_'+key,run,lambda q,k=key,v=value:q.__setitem__(k,v),lambda q:validate_run(q,jobs))
    manifest=json.loads((ROOT/PARTS).read_text());validate_manifest(manifest)
    for key,value in(('sha256','0'*64),('bytes',11968300)):
        reject('archive_'+key,manifest,lambda q,k=key,v=value:q.__setitem__(k,v),validate_manifest)
    assets=[dict(name=n,id=i,size=s,digest='sha256:'+h)for n,(i,s,h)in ASSETS.items()];validate_assets(assets)
    reject('asset_wrong_id',assets,lambda q:q[0].__setitem__('id',1),validate_assets)
    reject('asset_wrong_digest',assets,lambda q:q[-1].__setitem__('digest','sha256:'+'0'*64),validate_assets)
    assert len(rejected)==20
    return dict(status='PASS52_INHERITED_PLUS9_SOURCE_PLUS20_FAILED_SIDECAR_CONTROLS',
      inherited=inherited,source_controls=source,rejected=rejected,protected_files=len(m['protected']),native_executed=False)
def validate_observation(comparison,native,generated):
    assert comparison['status']=='CAPTURED_ACTUAL_NATIVE_AND_EXACT_SAVED_SHAPES_BEFORE_ORIGINAL_ASSERTION'
    assert comparison['frozen_helper_sha256']==observer.FROZEN_SHA and comparison['saved_sidecar_sha256']==observer.SIDECAR_SHA
    assert len(comparison['cells'])==2 and [v['serialized_cell']for v in comparison['cells']]==list(observer.frozen.NAMES)
    for row in comparison['cells']:observer.validate_pair(row)
    first=comparison['cells'][0]
    assert first['all_layer_sets_equal']and first['all_layer_material_equal']and not first['raw_difference']['equal']
    assert comparison['annotation_binding_accepted']is False and comparison['strict_wires_executed']is False
    assert native['status']=='FAIL_STATIC_NATIVE_ANNOTATION_RECOVERY'
    assert native['error']=="AssertionError('Changed complete raw native shapes')"
    identity=native['raw_failure_identity']
    assert identity['function']=='exact_static'and identity['line']==40
    assert identity['serialized_cell']==observer.frozen.NAMES[0]and identity['native_cell']==first['native_cell']
    assert identity['first_native_and_saved_cell_objects_bound']is True and identity['executing_helper_sha256']==sha(generated)
    expected='File "'+str(generated)+'", line 40, in exact_static'
    assert expected in native['traceback']and native['traceback'].rstrip().endswith('AssertionError: Changed complete raw native shapes')
    assert native['all339_original_files_unchanged']and native['original_report_unchanged']
    assert 'recovered_annotation_sha256'not in native and 'native_controls'not in native
    return True
def main():
    p=argparse.ArgumentParser();p.add_argument('--controls',action='store_true');a=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ['GITHUB_RUN_ATTEMPT']=='1'
    if a.controls:print(json.dumps(controls(),indent=2));return
    m=methods();assert m['readback_authorized']is True
    reservation=previous.saved.precreated(GROUP,wait=True)
    out=ROOT/'hw/soc/out/cloud-cdr-v59-serialized-shape-diagnostic';out.mkdir(parents=True,exist_ok=False)
    previous.saved.reports.OUT=out
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],run_id=int(os.environ['GITHUB_RUN_ID']),
      release=reservation,accepted=False,annotation_binding_accepted=False,strict_wires_executed=False,
      geometry_regenerated=False,physical_checks_rerun=False,qualified_pex=False,electrical_accepted=False,full_phy_accepted=False)
    def save():write(out/'result.json',result)
    restored=out/'restored';analysis=out/'analysis-capsule';prior=None;original=None;runtime=None;save()
    try:
        prior=json.loads((ROOT/REPORT).read_text());validate_report(prior)
        validate_manifest(json.loads((ROOT/PARTS).read_text()))
        r=release.api('actions/runs/'+str(RUN));j=release.api('actions/runs/'+str(RUN)+'/attempts/1/jobs?per_page=100');validate_run(r,j)
        tag='cloud-results-'+str(RUN)+'-1-'+SOURCE_GROUP
        rel=release.api('releases/tags/'+tag);validate_assets(rel['assets'])
        result['failed_release']=release.validate_release(rel,release.api('git/ref/tags/'+tag),tag,HEAD)
        actual,proof=previous.saved.reports.restore_report(SOURCE_GROUP,RUN,SUMMARY_SHA,PARTS_SHA,
          restored,list(prior['outputs']))
        assert actual==prior and sha(restored/'result.json')==SUMMARY_SHA
        for n,h in prior['outputs'].items():assert sha(restored/n)==h,n
        result['restoration']=proof;save()
        source=restored/'capsule';original=json.loads((source/'result.json').read_text())
        assert sha(source/'result.json')==previous.saved.SUMMARY_SHA
        previous.saved.validate_report(original)
        analysis.mkdir(exist_ok=False)
        # A separate byte-exact original view excludes the later extra sidecar.
        # Restored failure evidence, including its saved sidecar, is never edited.
        for n,h in{**original['outputs'],'result.json':previous.saved.SUMMARY_SHA}.items():
            dst=analysis/n;dst.parent.mkdir(parents=True,exist_ok=True)
            assert not dst.exists();shutil.copyfile(source/n,dst);assert sha(dst)==h
        sidecar=source/previous.SIDECAR
        assert sidecar.stat().st_size==2910 and sha(sidecar)==observer.SIDECAR_SHA
        assert not(analysis/previous.SIDECAR).exists()
        generated,derivation=observer.derive((ROOT/observer.FROZEN).read_text())
        program=out/'derived_materialization.py';program.write_text(generated)
        result['derivation']=derivation;save()
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==previous.saved.APP_SHA
        spec=json.loads((ROOT/previous.RUNTIME).read_text())
        assert spec['receipt']['bytes']==667167 and spec['receipt']['sha256']=='8caa4db1ae881af8fe57fa9d01df16bd57a2f31ece40fecd9bc4e8e139952ac2'
        packed=out/'runtime.tar.gz';fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed)
        assert packed.stat().st_size==667167
        with tarfile.open(packed)as tar:tar.extractall(ROOT,filter='data')
        packed.unlink();runtime=json.loads((ROOT/'manifest.json').read_text())
        assert all(sha(ROOT/n)==v['sha256']for n,v in runtime['files'].items())
        methods();result['runtime_manifest_sha256']=sha(ROOT/'manifest.json');save()
        log=out/'native-observation.log'
        with log.open('wb')as f:
            rc=subprocess.call(list(map(str,[app,'python',program,'--capsule',analysis,'--pdk',ROOT/'pdk',
              '--out',out/'native','--saved-sidecar',sidecar])),cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,
              env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(ROOT/'scripts')})
        result['native_returncode']=rc;result['native_log_sha256']=sha(log);save()
        assert rc==1,'Expected exact preserved AssertionError process exit'
        native=json.loads((out/'native/materialization.json').read_text())
        comparison=json.loads((out/'native/serialized-comparison.json').read_text())
        validate_observation(comparison,native,program)
        assert sha(analysis/previous.SIDECAR)==sha(sidecar)==observer.SIDECAR_SHA
        assert not(analysis/'wire/source-pins.json').exists()
        result.update(status='COMPLETE_EXACT_SAVED_SIDECAR_DIAGNOSIS_ORIGINAL_RAW_REJECTION_REPRODUCED',
          original_serialization_rejection=native,actual_shape_comparison=comparison,
          actual_sidecar_sha256=sha(sidecar),sidecar_bytes=sidecar.stat().st_size,
          exact_original_rejection_retained=True,no_representation_equivalence_assumed=True)
    except BaseException as error:
        result.update(status='FAIL_SAVED_SIDECAR_DIAGNOSIS',error=repr(error),traceback=traceback.format_exc());raise
    finally:
        try:
            if prior is not None and(restored/'result.json').exists():
                result['all345_restored_files_unchanged']=all(sha(restored/n)==h for n,h in prior['outputs'].items())
                result['restored_failure_report_unchanged']=sha(restored/'result.json')==SUMMARY_SHA
                assert result['all345_restored_files_unchanged']and result['restored_failure_report_unchanged']
            if original is not None and(analysis/'result.json').exists():
                result['all339_analysis_originals_unchanged']=all(sha(analysis/n)==h for n,h in original['outputs'].items())
                assert result['all339_analysis_originals_unchanged']and sha(analysis/'result.json')==previous.saved.SUMMARY_SHA
            if runtime is not None:
                assert all(sha(ROOT/n)==v['sha256']for n,v in runtime['files'].items());result['runtime_unchanged']=True
            methods();result['diagnostic_sources_unchanged']=True
        except BaseException as error:
            result.update(status='FAIL_SIDECAR_DIAGNOSTIC_INTEGRITY',integrity_error=repr(error));raise
        finally:
            result['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and p!=out/'result.json'};save()
if __name__=='__main__':main()
