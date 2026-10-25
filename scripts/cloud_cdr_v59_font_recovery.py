#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Recover exact saved font metadata and run unchanged strict wires; no new layout."""
import argparse,copy,hashlib,json,os,shutil,subprocess,sys,tarfile,traceback
from pathlib import Path
import cloud_cdr_v59_serialized_shape_diagnostic as diagnostic
import cdr_v59_font_roundtrip_contract as font
import ensure_cloud_tested_source_release as release
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
METHOD='scripts/cdr-v59-font-recovery-methods.json'
GROUP='cdr-v59-font-recovery'
COMPLETED_RUN=40185582304
COMPLETED_HEAD='04fa51061bcce36be4eef491d171a75dc93977c3'
COMPLETED_REPORT='docs/evidence/cdr-v59-serialized-shape-diagnostic-result-20261025.json'
COMPLETED_SHA='35fcb508dd467a22af7c7b545eec25e9d5e933577c736eb72aa2528b3200d360'
COMPLETED_ASSETS=[{"id":674768885,"name":"cdr-v59-serialized-shape-diagnostic-40185582304-1.derived-helper.py","size":14310,"digest":"sha256:a48374ae4cac836a818c6797341589be31baabedfcd2688be7545656f376ad64"},{"id":674768748,"name":"cdr-v59-serialized-shape-diagnostic-40185582304-1.materialization.json","size":4584,"digest":"sha256:764275e229d81a3703ab69fcfa34a048f11ec6cb175ffbb3aec7b77dfda90ee5"},{"id":674768613,"name":"cdr-v59-serialized-shape-diagnostic-40185582304-1.parts.json","size":892,"digest":"sha256:7880998edb45b4a1efa981aa5c23a04324cf5991a1c8a726519cbb2f1e71c83d"},{"id":674768821,"name":"cdr-v59-serialized-shape-diagnostic-40185582304-1.serialized-comparison.json","size":52200,"digest":"sha256:6d3f73f925ab9767c3b161f293ce0c105074ec03e9052f516ab6f1c2553530f4"},{"id":674768522,"name":"cdr-v59-serialized-shape-diagnostic-40185582304-1.summary.json","size":229022,"digest":"sha256:35fcb508dd467a22af7c7b545eec25e9d5e933577c736eb72aa2528b3200d360"},{"id":674768655,"name":"cdr-v59-serialized-shape-diagnostic-40185582304-1.tar.gz.part0000","size":23903827,"digest":"sha256:b11141e71b773df91824584bb1392940b8e09f5d4c840be211807a3cec614ff6"}]
def write(path,value):diagnostic.write(path,value)
def methods():
    m=json.loads((ROOT/METHOD).read_text())
    assert m['scope']=='EXACT_SAVED_FONT2_TO_NOFONT_RECOVERY_AND_UNCHANGED_STRICT_WIRES'
    for n,h in m['protected'].items():assert sha(ROOT/n)==h,n
    diagnostic.methods()
    assert sha(ROOT/COMPLETED_REPORT)==COMPLETED_SHA
    _,proof=font.derive((ROOT/font.observed.FROZEN).read_text())
    assert proof['generated_sha256']==m['native_derived_sha256']and len(proof['reversible_edits'])==3
    assert proof['unchanged_functions']==m['unchanged_native_functions']
    return m
def validate_completed_report(r):
    assert r['status']=='COMPLETE_EXACT_SAVED_SIDECAR_DIAGNOSIS_ORIGINAL_RAW_REJECTION_REPRODUCED'
    assert r['run_id']==COMPLETED_RUN and r['source_head']==COMPLETED_HEAD
    for k in('accepted','annotation_binding_accepted','strict_wires_executed','geometry_regenerated',
      'physical_checks_rerun','qualified_pex','electrical_accepted','full_phy_accepted'):assert r[k]is False
    for k in('all345_restored_files_unchanged','restored_failure_report_unchanged',
      'all339_analysis_originals_unchanged','runtime_unchanged','diagnostic_sources_unchanged',
      'exact_original_rejection_retained','no_representation_equivalence_assumed'):assert r[k]is True
    assert r['native_returncode']==1 and r['sidecar_bytes']==2910
    assert r['actual_sidecar_sha256']==font.observed.SIDECAR_SHA
    assert r['actual_shape_comparison']==json.loads((ROOT/font.COMPARISON).read_text())
    assert r['original_serialization_rejection']==json.loads((ROOT/'docs/evidence/cdr-v59-serialized-shape-diagnostic-materialization-20261025.json').read_text())
    return True
def validate_completed_run(r,j):
    assert r['id']==COMPLETED_RUN and r['head_sha']==COMPLETED_HEAD and r['run_attempt']==1
    assert r['path']=='.github/workflows/cdr-v59-serialized-shape-diagnostic-cloud.yml'
    assert r['event']=='workflow_dispatch'and r['status']=='completed'and r['conclusion']=='success'
    expected={121145558856:('controls','success'),121145648171:('read-only-saved-sidecar','success')}
    assert j['total_count']==len(j['jobs'])==2 and {v['id']for v in j['jobs']}==set(expected)
    for v in j['jobs']:
        assert v['run_id']==COMPLETED_RUN and v['head_sha']==COMPLETED_HEAD and v['status']=='completed'
        assert(v['name'],v['conclusion'])==expected[v['id']]
    return True
def validate_completed_assets(assets):
    keys=('id','name','size','digest')
    assert len(assets)==6 and len({a['name']for a in assets})==6
    actual=sorted([{k:a[k]for k in keys}for a in assets],key=lambda a:a['name'])
    assert actual==sorted(COMPLETED_ASSETS,key=lambda a:a['name'])
    return True
def completed_prerequisite():
    r=json.loads((ROOT/COMPLETED_REPORT).read_text());validate_completed_report(r)
    run=release.api('actions/runs/'+str(COMPLETED_RUN))
    jobs=release.api('actions/runs/'+str(COMPLETED_RUN)+'/attempts/1/jobs?per_page=100')
    validate_completed_run(run,jobs)
    tag='cloud-results-'+str(COMPLETED_RUN)+'-1-'+diagnostic.GROUP
    rel=release.api('releases/tags/'+tag);validate_completed_assets(rel['assets'])
    proof=release.validate_release(rel,release.api('git/ref/tags/'+tag),tag,COMPLETED_HEAD)
    return dict(run=COMPLETED_RUN,head=COMPLETED_HEAD,attempt=1,summary_sha256=COMPLETED_SHA,
      complete_comparison_sha256=font.COMPARISON_SHA,release=proof,original_rejection_preserved=True)
def controls():
    m=methods();inherited=diagnostic.controls();narrow=font.controls()
    assert len(inherited['rejected'])==20 and len(inherited['source_controls']['rejected'])==9
    assert len(inherited['inherited']['rejected'])==20
    assert len(inherited['inherited']['original_capsule_controls']['rejected'])==32
    assert len(narrow['rejected'])==16
    report=json.loads((ROOT/COMPLETED_REPORT).read_text());validate_completed_report(report);rejected=[]
    def reject(label,original,change,validate):
        q=copy.deepcopy(original);change(q)
        try:validate(q)
        except(AssertionError,KeyError):rejected.append(label)
        else:raise AssertionError('Accepted completed diagnostic corruption '+label)
    for key,value in(('status','PASS'),('source_head','0'*40),('run_id',1),('accepted',True),
      ('annotation_binding_accepted',True),('strict_wires_executed',True),
      ('all345_restored_files_unchanged',False),('runtime_unchanged',False),
      ('all339_analysis_originals_unchanged',False),('sidecar_bytes',2911)):
        reject(key,report,lambda q,k=key,v=value:q.__setitem__(k,v),validate_completed_report)
    run=dict(id=COMPLETED_RUN,head_sha=COMPLETED_HEAD,run_attempt=1,
      path='.github/workflows/cdr-v59-serialized-shape-diagnostic-cloud.yml',
      event='workflow_dispatch',status='completed',conclusion='success')
    jobs=dict(total_count=2,jobs=[dict(id=i,run_id=COMPLETED_RUN,head_sha=COMPLETED_HEAD,
      name=n,status='completed',conclusion='success')for i,n in
      ((121145558856,'controls'),(121145648171,'read-only-saved-sidecar'))])
    validate_completed_run(run,jobs)
    for key,value in(('run_attempt',2),('head_sha','0'*40),('conclusion','failure'),('status','in_progress')):
        reject('run_'+key,run,lambda q,k=key,v=value:q.__setitem__(k,v),lambda q:validate_completed_run(q,jobs))
    validate_completed_assets(COMPLETED_ASSETS)
    for key,value in(('id',1),('size',1),('digest','sha256:'+'0'*64),('name','unexpected')):
        reject('asset_'+key,COMPLETED_ASSETS,lambda q,k=key,v=value:q[0].__setitem__(k,v),validate_completed_assets)
    assert len(rejected)==18
    return dict(status='PASS_INHERITED81_PLUS16_FONT_PLUS18_ACTUAL_DIAGNOSTIC_CONTROLS',
      inherited=inherited,font=narrow,rejected=rejected,protected_files=len(m['protected']),native_executed=False)
previous=diagnostic.previous
observer=font.observed
REPORT=diagnostic.REPORT;PARTS=diagnostic.PARTS
RUN=diagnostic.RUN;HEAD=diagnostic.HEAD;SOURCE_GROUP=diagnostic.SOURCE_GROUP
SUMMARY_SHA=diagnostic.SUMMARY_SHA;PARTS_SHA=diagnostic.PARTS_SHA
validate_report=diagnostic.validate_report;validate_manifest=diagnostic.validate_manifest
validate_run=diagnostic.validate_run;validate_assets=diagnostic.validate_assets
def main():
    p=argparse.ArgumentParser();p.add_argument('--controls',action='store_true');a=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ['GITHUB_RUN_ATTEMPT']=='1'
    if a.controls:print(json.dumps(controls(),indent=2));return
    m=methods();assert m['recovery_authorized']is True
    reservation=previous.saved.precreated(GROUP,wait=True)
    out=ROOT/'hw/soc/out/cloud-cdr-v59-font-recovery';out.mkdir(parents=True,exist_ok=False)
    previous.saved.reports.OUT=out
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],run_id=int(os.environ['GITHUB_RUN_ID']),
      release=reservation,accepted=False,annotation_binding_accepted=False,strict_wires_executed=False,
      geometry_regenerated=False,physical_checks_rerun=False,qualified_pex=False,wire_rc_extracted=False,electrical_accepted=False,full_phy_accepted=False)
    def save():write(out/'result.json',result)
    def run(command,label):
        log=out/(label+'.log')
        with log.open('wb')as f:rc=subprocess.call(list(map(str,command)),cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,
          env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(ROOT/'scripts')})
        result.setdefault('commands',[]).append(dict(label=label,returncode=rc,log_sha256=sha(log)));save()
        if rc:print(log.read_text(errors='replace')[-20000:],flush=True)
        assert rc==0,(label,rc)
    restored=out/'restored';analysis=out/'analysis-capsule';prior=None;original=None;runtime=None;save()
    try:
        result['actual_diagnostic_prerequisite']=completed_prerequisite();save()
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
        generated,derivation=font.derive((ROOT/observer.FROZEN).read_text())
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
        run([app,'python',program,'--capsule',analysis,'--pdk',ROOT/'pdk',
          '--out',out/'native','--saved-sidecar',sidecar],'font-native-source-and-exact-recovery')
        native=json.loads((out/'native/materialization.json').read_text())
        contract=json.loads((out/'native/font-roundtrip.json').read_text())
        result['font_roundtrip']=contract;result['annotation_materialization']=native;save()
        assert contract['status']=='PASS_ONLY_EXACT_OBSERVED_FONT2_TO_NoFont_TRANSITION_ALL_OTHER_FIELDS_EXACT'
        assert contract['comparison_sha256']==font.COMPARISON_SHA and contract['source_audit_sha256']==font.AUDIT_SHA
        assert contract['original_failure']['original_rejection_preserved']and contract['original_failure']['line']==40
        assert contract['original_failure']['exact_code_object_bound']and contract['original_failure']['actual_first_native_and_saved_cell_objects_bound']
        assert len(contract['native_controls']['rejected'])==28 and contract['native_controls']['positive_exact_saved_copies']==28
        assert len(contract['serialized'])==2
        for row in contract['serialized']:
            assert row['actual_font_fields']['native_font']==2 and row['actual_font_fields']['serialized_font']==-1
        assert native['status']=='PASS_STATIC_NATIVE_SIDECAR_AND_UNCHANGED_EXACT_ANNOTATION_RECOVERY_REQUIRES_STRICT_WIRES'
        assert native['all339_original_files_unchanged']and native['original_report_unchanged']
        assert native['original_recovery_source_unchanged']and native['all_original_source_pin_sets_preserved']
        assert not native['signature_fallback_used']and len(native['native_controls']['rejected'])==10
        assert native['sidecar']['path']==previous.SIDECAR
        assert sha(analysis/previous.SIDECAR)==sha(sidecar)==native['sidecar']['sha256']==observer.SIDECAR_SHA
        assert native['native_parameters_before']==original['candidate_delta']['native_pcell_parameters_before']
        assert native['native_parameters_after']==original['candidate_delta']['native_pcell_parameters_after']
        result['strict_wires_started']=True;save()
        for name in('probe01.py','locate01.py','anchors01.py','dedup01.py'):
            path=analysis/'wire'/name
            assert sha(path)==original['outputs']['wire/'+name]
            run([app,'python',path],name)
        graph=json.loads((analysis/'wire/native05/result.json').read_text())
        devices=json.loads((analysis/'wire/device-locations01.json').read_text())
        anchors=json.loads((analysis/'wire/anchors08.json').read_text())
        assert graph['native_device_count']==500 and graph['native_terminal_count']==1446
        assert graph['wire_component_count']==113
        assert devices['status']=='PASS_ALL_500_DEVICES_HAVE_UNIQUE_PHYSICAL_PCELL_ENCLOSURE'
        assert len(devices['devices'])==500 and devices['native_terminal_count']==1446
        assert anchors['logical_anchor_count']==978 and anchors['public_ports']==25
        assert anchors['dispositions']==dict(ACTUAL_TERMINAL_METAL_POINT_REFERENCE=953,
          RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE=493)
        result.update(status='PASS_EXACT_SAVED_FONT_ROUNDTRIP_AND_STRICT_WIRES_REQUIRES_MIM_RC',
          annotation_binding_accepted=True,strict_wires_executed=True,original_font_rejection_preserved=True,
          original_physical_summary_sha256=previous.saved.SUMMARY_SHA,
          original_physical_status=original['physical']['status'],
          original_physical_and_planes_rerun=False,
          strict_wire_graph={k:graph[k]for k in('native_device_count','native_terminal_count','wire_component_count')},
          device_locations=dict(status=devices['status'],device_count=len(devices['devices']),native_terminal_count=devices['native_terminal_count']),
          anchors={k:anchors[k]for k in('logical_anchor_count','public_ports','dispositions')},
          complete_reports={n:dict(path='analysis-capsule/'+n,bytes=(analysis/n).stat().st_size,sha256=sha(analysis/n))
            for n in('wire/source-pins.json','wire/native05/result.json','wire/device-locations01.json','wire/anchors08.json')},
          preserved_candidate_gds_sha256=sha(analysis/'parent/layout/nssoc_cdr_pd500_resistor_v59.gds'),
          preserved_candidate_reference_sha256=sha(analysis/'parent/layout/schematic.cir'))
    except BaseException as error:
        result.update(status='FAIL_EXACT_FONT_RECOVERY_OR_STRICT_WIRES',error=repr(error),traceback=traceback.format_exc());raise
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
            methods();result['font_recovery_sources_unchanged']=True
        except BaseException as error:
            result.update(status='FAIL_EXACT_FONT_RECOVERY_INTEGRITY',integrity_error=repr(error));raise
        finally:
            result['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and p!=out/'result.json'};save()
if __name__=='__main__':main()
