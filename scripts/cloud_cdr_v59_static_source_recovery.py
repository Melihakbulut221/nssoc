#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Recover annotations/strict wires from the exact passed-layout, rejected-source capsule."""
import argparse,copy,hashlib,json,os,subprocess,sys,tarfile,traceback
from pathlib import Path
import cloud_cdr_v59_annotation_diagnostic as saved
import ensure_cloud_tested_source_release as release
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
METHOD='scripts/cdr-v59-static-source-recovery-methods.json'
CENSUS='docs/evidence/cdr-v59-saved-source-census-result-20261025.json'
CENSUS_SHA='7b99e37369fc022f8255a929ff75c767b142cc5ac5c046027e66bf9427e68dca'
CENSUS_RUN=40180385567
CENSUS_HEAD='abab9391fd7b07259294ab15e046117b712dabcb'
GROUP='cdr-v59-static-source-recovery'
SIDECAR='parent/inputs/sampler_cd/layout/native-rppd-v59-static-cd_shunt.gds'
HELPER='scripts/materialize_cdr_v59_static_annotations.py'
RUNTIME='docs/evidence/pcie-tx-layout-cloud-input-20261013.json'
def write(path,value):
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');temporary.replace(path)
def methods():
    m=json.loads((ROOT/METHOD).read_text())
    assert m['scope']=='EXACT_SAVED_CD_SHUNT_STATIC_ANNOTATION_SOURCE_AND_ORIGINAL_STRICT_WIRES'
    for n,h in m['protected'].items():assert sha(ROOT/n)==h,n
    assert sha(ROOT/CENSUS)==CENSUS_SHA
    saved.methods()
    return m
def validate_census(s):
    assert s['status']=='COMPLETE_READ_ONLY_V59_ANNOTATION_DIAGNOSTIC_ORIGINAL_REJECTION_RETAINED'
    assert s['source_head']==CENSUS_HEAD and s['run_id']==CENSUS_RUN
    assert s['preserved_candidate_gds_sha256']==saved.PINNED_OUTPUTS['parent/layout/nssoc_cdr_pd500_resistor_v59.gds']
    assert s['preserved_candidate_reference_sha256']==saved.PINNED_OUTPUTS['parent/layout/schematic.cir']
    assert s['restored_capsule_files_unchanged']and s['current_diagnostic_sources_unchanged']
    assert all(s[k]is False for k in('accepted','qualified_pex','electrical_accepted','full_phy_accepted',
      'geometry_regenerated','physical_checks_rerun','annotation_binding_accepted'))
    c=s['saved_new_source_census']
    assert c['source']=='parent/inputs/sampler_cd/layout/native-rppd-v59-cd_shunt.gds'
    assert c['bytes']==66 and c['sha256']==saved.PINNED_OUTPUTS[c['source']]
    raw=bytes.fromhex(c['exact_file_hex'])
    assert len(raw)==66 and hashlib.sha256(raw).hexdigest()==c['sha256']
    assert b''.join(bytes.fromhex(r['exact_record_hex'])for r in c['record_inventory'])==raw
    assert c['cell_count']==0 and c['cells']==[]and c['top_cells']==[]and c['dbu_um']==.001
    f=s['original_failure']
    assert f['code_file_sha256']==saved.PINNED_OUTPUTS['methods/cdr_v59_recover.py']
    assert f['function']=='recover'and f['line']==62 and f['original_rejection_retained']
    assert f['cell']=='rppd$v59_cd_shunt'
    assert f['key']==['rppd','26cb371619de68fbd6248f25a98a6b1c2ef649e3e75d56b082c7eafb9d35ec91']
    assert len(s['source_census_controls']['positive_cases'])==3 and len(s['source_census_controls']['rejected'])==5
    return True
def census_identity(run,jobs):
    assert run['id']==CENSUS_RUN and run['run_attempt']==1 and run['head_sha']==CENSUS_HEAD
    assert run['event']=='workflow_dispatch'and run['status']=='completed'and run['conclusion']=='success'
    assert run['path']=='.github/workflows/cdr-v59-annotation-diagnostic-cloud.yml'
    assert jobs['total_count']==len(jobs['jobs'])==2
    expected={121129994561:'controls',121130071837:'read-only-native-geometry'}
    assert {j['id']for j in jobs['jobs']}==set(expected)
    for j in jobs['jobs']:
        assert j['run_id']==CENSUS_RUN and j['head_sha']==CENSUS_HEAD
        assert j['name']==expected[j['id']]and j['status']=='completed'and j['conclusion']=='success'
    return True
def controls():
    m=methods();original=saved.controls();assert len(original['rejected'])==32
    source=json.loads((ROOT/CENSUS).read_text());validate_census(source);rejected=[]
    def reject(label,mutate):
        s=copy.deepcopy(source);mutate(s)
        try:validate_census(s)
        except(AssertionError,ValueError):rejected.append(label)
        else:raise AssertionError('Accepted static-source prerequisite fault '+label)
    for k,v in [('status','PASS'),('source_head','0'*40),('run_id',1),
      ('preserved_candidate_gds_sha256','0'*64),('preserved_candidate_reference_sha256','0'*64),
      ('restored_capsule_files_unchanged',False),('annotation_binding_accepted',True)]:
        reject(k,lambda s,k=k,v=v:s.__setitem__(k,v))
    for k,v in [('bytes',65),('cell_count',1),('cells',[{}]),('top_cells',[{}]),
      ('dbu_um',.002),('exact_file_hex','00')]:
        reject('census_'+k,lambda s,k=k,v=v:s['saved_new_source_census'].__setitem__(k,v))
    reject('wrong_failure_line',lambda s:s['original_failure'].__setitem__('line',63))
    reject('wrong_failure_key',lambda s:s['original_failure'].__setitem__('key',['rppd','0'*64]))
    reject('missing_census_fault',lambda s:s['source_census_controls']['rejected'].pop())
    assert len(rejected)==16
    run=dict(id=CENSUS_RUN,run_attempt=1,head_sha=CENSUS_HEAD,event='workflow_dispatch',
      status='completed',conclusion='success',path='.github/workflows/cdr-v59-annotation-diagnostic-cloud.yml')
    jobs=dict(total_count=2,jobs=[dict(id=i,run_id=CENSUS_RUN,head_sha=CENSUS_HEAD,name=n,
      status='completed',conclusion='success')for i,n in((121129994561,'controls'),(121130071837,'read-only-native-geometry'))])
    census_identity(run,jobs)
    for label,mutate in (
      ('census_runtime_source',lambda r,j:r.__setitem__('head_sha','0'*40)),
      ('census_runtime_attempt',lambda r,j:r.__setitem__('run_attempt',2)),
      ('census_runtime_not_terminal',lambda r,j:r.__setitem__('status','in_progress')),
      ('census_runtime_wrong_job',lambda r,j:j['jobs'][1].__setitem__('id',1))):
        r,j=copy.deepcopy(run),copy.deepcopy(jobs);mutate(r,j)
        try:census_identity(r,j)
        except AssertionError:rejected.append(label)
        else:raise AssertionError('Accepted '+label)
    assert len(rejected)==20
    return dict(status='PASS32_ORIGINAL_AND20_STATIC_SOURCE_PREREQUISITE_CONTROLS',
      original_capsule_controls=original,rejected=rejected,protected_files=len(m['protected']),
      native_executed=False,geometry_changed=False)
def main():
    p=argparse.ArgumentParser();p.add_argument('--controls',action='store_true');a=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ['GITHUB_RUN_ATTEMPT']=='1'
    if a.controls:print(json.dumps(controls(),indent=2));return
    m=methods();assert m['recovery_authorized']is True
    reservation=saved.precreated(GROUP,wait=True)
    out=ROOT/'hw/soc/out/cloud-cdr-v59-static-source-recovery';out.mkdir(parents=True,exist_ok=False)
    saved.reports.OUT=out
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],run_id=int(os.environ['GITHUB_RUN_ID']),
      release=reservation,accepted=False,qualified_pex=False,wire_rc_extracted=False,electrical_accepted=False,
      full_phy_accepted=False,geometry_regenerated=False,physical_checks_rerun=False,
      historical_sources_unchanged_field_was_not_reached=True)
    def save():write(out/'result.json',result)
    def run(command,label):
        log=out/(label+'.log')
        with log.open('wb')as f:rc=subprocess.call(list(map(str,command)),cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,
          env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
        result.setdefault('commands',[]).append(dict(label=label,returncode=rc,log_sha256=sha(log)));save()
        if rc:print(log.read_text(errors='replace')[-20000:],flush=True)
        assert rc==0,(label,rc)
    capsule=out/'capsule';prior=None;runtime=None
    save()
    try:
        census=json.loads((ROOT/CENSUS).read_text());validate_census(census)
        cr=release.api('actions/runs/'+str(CENSUS_RUN))
        cj=release.api('actions/runs/'+str(CENSUS_RUN)+'/attempts/1/jobs?per_page=100')
        census_identity(cr,cj);result['actual_census_prerequisite']=dict(run=CENSUS_RUN,head=CENSUS_HEAD,summary_sha256=CENSUS_SHA)
        prior=json.loads((ROOT/saved.REPORT).read_text());saved.validate_report(prior)
        saved.validate_manifest(json.loads((ROOT/saved.PARTS).read_text()))
        sr=release.api('actions/runs/'+str(saved.RUN))
        sj=release.api('actions/runs/'+str(saved.RUN)+'/attempts/1/jobs?per_page=100')
        saved.validate_run(sr,sj)
        tag='cloud-results-40176503143-1-'+saved.SOURCE_GROUP
        rel=release.api('releases/tags/'+tag);saved.validate_assets(rel['assets'])
        result['original_release']=release.validate_release(rel,release.api('git/ref/tags/'+tag),tag,saved.HEAD)
        restored,proof=saved.reports.restore_report(saved.SOURCE_GROUP,saved.RUN,saved.SUMMARY_SHA,
          saved.PARTS_SHA,capsule,list(prior['outputs']))
        assert restored==prior and sha(capsule/'result.json')==saved.SUMMARY_SHA
        for n,h in prior['outputs'].items():assert sha(capsule/n)==h,n
        result['restoration']=proof;save()
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==saved.APP_SHA
        spec=json.loads((ROOT/RUNTIME).read_text())
        assert spec['receipt']['bytes']==667167 and spec['receipt']['sha256']=='8caa4db1ae881af8fe57fa9d01df16bd57a2f31ece40fecd9bc4e8e139952ac2'
        packed=out/'runtime.tar.gz';fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed)
        assert packed.stat().st_size==spec['receipt']['bytes']
        with tarfile.open(packed)as tar:tar.extractall(ROOT,filter='data')
        packed.unlink()
        runtime=json.loads((ROOT/'manifest.json').read_text())
        assert all(sha(ROOT/n)==v['sha256']for n,v in runtime['files'].items())
        methods()
        result['runtime_manifest_sha256']=sha(ROOT/'manifest.json');save()
        run([app,'python',ROOT/HELPER,'--capsule',capsule,'--pdk',ROOT/'pdk','--out',out/'native'],
          'static-native-source-and-exact-recovery')
        native=json.loads((out/'native/materialization.json').read_text())
        assert native['status']=='PASS_STATIC_NATIVE_SIDECAR_AND_UNCHANGED_EXACT_ANNOTATION_RECOVERY_REQUIRES_STRICT_WIRES'
        assert native['all339_original_files_unchanged']and native['original_report_unchanged']
        assert native['original_recovery_source_unchanged']and native['all_original_source_pin_sets_preserved']
        assert not native['signature_fallback_used']and len(native['native_controls']['rejected'])==10
        assert native['sidecar']['path']==SIDECAR and sha(capsule/SIDECAR)==native['sidecar']['sha256']
        assert native['native_parameters_before']==prior['candidate_delta']['native_pcell_parameters_before']
        assert native['native_parameters_after']==prior['candidate_delta']['native_pcell_parameters_after']
        result['annotation_materialization']=native;save()
        for name in('probe01.py','locate01.py','anchors01.py','dedup01.py'):
            path=capsule/'wire'/name
            assert sha(path)==prior['outputs']['wire/'+name]
            run([app,'python',path],name)
        graph=json.loads((capsule/'wire/native05/result.json').read_text())
        devices=json.loads((capsule/'wire/device-locations01.json').read_text())
        anchors=json.loads((capsule/'wire/anchors08.json').read_text())
        assert graph['native_device_count']==500 and graph['native_terminal_count']==1446
        assert graph['wire_component_count']==113
        assert devices['status']=='PASS_ALL_500_DEVICES_HAVE_UNIQUE_PHYSICAL_PCELL_ENCLOSURE'
        assert len(devices['devices'])==500 and devices['native_terminal_count']==1446
        assert anchors['logical_anchor_count']==978 and anchors['public_ports']==25
        assert anchors['dispositions']==dict(ACTUAL_TERMINAL_METAL_POINT_REFERENCE=953,
          RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE=493)
        result.update(status='PASS_SAVED_CD_SHUNT_PHYSICAL_EVIDENCE_STATIC_SOURCE_AND_FRESH_STRICT_WIRES_REQUIRES_MIM_RC',
          original_physical_summary_sha256=saved.SUMMARY_SHA,
          original_physical_status=prior['physical']['status'],
          original_physical_and_planes_rerun=False,
          strict_wire_graph={k:graph[k]for k in('native_device_count','native_terminal_count','wire_component_count')},
          device_locations=dict(status=devices['status'],device_count=len(devices['devices']),native_terminal_count=devices['native_terminal_count']),
          anchors={k:anchors[k]for k in('logical_anchor_count','public_ports','dispositions')},
          complete_reports={n:dict(path='capsule/'+n,bytes=(capsule/n).stat().st_size,sha256=sha(capsule/n))
            for n in('wire/source-pins.json','wire/native05/result.json','wire/device-locations01.json','wire/anchors08.json')},
          preserved_candidate_gds_sha256=sha(capsule/'parent/layout/nssoc_cdr_pd500_resistor_v59.gds'),
          preserved_candidate_reference_sha256=sha(capsule/'parent/layout/schematic.cir'))
    except BaseException as error:
        result.update(status='FAIL_SAVED_CD_SHUNT_STATIC_SOURCE_OR_STRICT_WIRES',error=repr(error),traceback=traceback.format_exc());raise
    finally:
        try:
            if prior is not None and(capsule/'result.json').exists():
                result['all339_original_files_unchanged']=all(sha(capsule/n)==h for n,h in prior['outputs'].items())
                result['original_report_unchanged']=sha(capsule/'result.json')==saved.SUMMARY_SHA
                assert result['all339_original_files_unchanged']and result['original_report_unchanged']
            if runtime is not None:
                assert all(sha(ROOT/n)==v['sha256']for n,v in runtime['files'].items())
                result['runtime_files_unchanged']=True
            methods();result['current_recovery_sources_unchanged']=True
        except BaseException as error:
            result.update(status='FAIL_STATIC_SOURCE_RECOVERY_INTEGRITY',integrity_error=repr(error));raise
        finally:
            result['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and p!=out/'result.json'}
            save()
if __name__=='__main__':main()
