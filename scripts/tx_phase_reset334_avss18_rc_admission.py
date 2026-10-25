#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact AVSS18 physical admission and full saved-file restoration, no native calls."""
import copy,hashlib,json,os,subprocess
from pathlib import Path
import cloud_chunked_results as chunks
import tx_phase_reset244_avss18_baseline as frozen
import ensure_cloud_tested_source_release as release
ROOT=Path(__file__).resolve().parents[1]
METHOD=ROOT/'scripts/tx-phase-reset334-avss18-rc-methods.json'
SUMMARY='docs/evidence/tx-phase-reset244-avss18-physical-native-result-20261025.json'
SOURCE=dict(run=40211309923,job=121223092798,head='5ddb5be6843a967305dbb5a45b426070c0f8fabd',
 group='tx-phase-reset244-avss18-physical',release=423515853,
 summary='6d1cc609af69edd9e1c34558b67f976997afd950b27c90db158652d369ce9d17')
STEM=SOURCE['group']+'-'+str(SOURCE['run'])+'-1'
TAG='cloud-results-'+str(SOURCE['run'])+'-1-'+SOURCE['group']
ROOT_NAME='cloud-tx-phase-reset244-avss18-physical'
ASSETS=dict(summary=dict(id=675527771,name=STEM+'.summary.json',size=5754736,sha256=SOURCE['summary']),
 parts=dict(id=675527853,name=STEM+'.parts.json',size=883,sha256='4bc339b08667b762eff306f543235b6f6b16ed6dd9ed4e9e8856b5c16301d4ed'),
 archive=dict(id=675528201,name=STEM+'.tar.gz.part0000',size=9585939,sha256='ef46185dc1fa4890bc59b95e478ed1a2ea33ba011fcc81c971e6b58cea286c8d'))
GDS=dict(p='d81e0dadaa74dc649399b02fdb0bd71583835e1754787b40784ba3ce2559c0b7',
 n='2b726595cf7d220974ecdb8a7cb04f3e12ca488b858622fa276c08eb4ca85467')
sha=frozen.sha
def digest(data):return hashlib.sha256(data).hexdigest()
def methods():
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
    assert os.environ.get('GITHUB_REPOSITORY')==frozen.REPO and os.environ.get('GITHUB_RUN_ATTEMPT')=='1'
    m=json.loads(METHOD.read_bytes())
    for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
    assert m['simulation_authorized']is m['geometry_generation_authorized']is False
    assert type(m['native_execution_authorized'])is bool
    assert m['extraction_authorized']is m['native_execution_authorized']
    return m

def physical():
    b=(ROOT/SUMMARY).read_bytes();assert len(b)==ASSETS['summary']['size']and digest(b)==SOURCE['summary']
    r=json.loads(b);validate(r);return b,r

def validate(r):
    assert r['source_head']==SOURCE['head']and r['sources_unchanged']and not r['validation_errors']
    assert r['status']=='PASS_BOTH_AVSS18_EXACT_MATERIAL_334_PHYSICAL_1010_TERMINALS_REQUIRES_FRESH_MIM_RC_LOADED'
    assert set(r['variants'])=={'p','n'}and len(r['outputs'])==406
    assert r['original_baseline_byte_unchanged']and r['exact_one_native_rectangle_per_polarity_proved']
    assert r['original_electrical_rejection_preserved']and r['old_R_rescaled']is False
    assert r['fresh_RC_required']and r['fresh_loaded_waveforms_required']
    for k in ('accepted','qualified_pex','electrical_accepted','physical_reset_qualified','all31_clock_tree_accepted','PLL_connected','full_phy_accepted'):assert r[k]is False
    for pol,v in r['variants'].items():
        top='nssoc_tx_phase_reset244_'+pol+'_v1'
        assert v['status']=='PASS_AVSS18_MATERIAL20_FAULTS334_DRC_DEEP_FLAT_LVS9_FAULTS1010_TERMINALS7_FAULTS_REQUIRES_FRESH_RC_LOADED'
        assert v['sources_unchanged']and v['generation']['preset_polarity']==pol
        assert v['generation']['output_sha256'][top+'.gds']==r['outputs'][pol+'/layout/'+top+'.gds']==GDS[pol]
        assert v['generation']['primitive_counts']==dict(hbt=106,rppd=130,cmim=8,physical_ptap=90)
        assert v['generation']['exactly243_other_compact_devices_unchanged']
        assert v['generation']['sole_device_dimension_delta']==dict(name='PHASE__XRUN__XAND_SKEW',old_L_um=32,new_L_um=20,W_um=1)
        d=v['steps']['drc']['measurement'];assert d['status']=='PASS'and d['markers']==0 and d['category_count']==560
        for mode in ('deep_lvs','flat_lvs'):
            d=v['steps'][mode];a=d['audit']
            assert d['expected_verdict_observed']and d['ports']['passed']and d['ports']['actual_count']==d['ports']['expected_count']==11
            assert a['status']=='PASS within comparison scope'and not a['reasons']and not a['extraction_diagnostics']
            assert a['circuit_status_counts']=={'Match':1}and len(a['circuits'])==1
            assert a['circuits'][0]['layout_devices_recursive']==a['circuits'][0]['schematic_devices_recursive']==334
        faults=[x for k,x in v['steps'].items()if k not in ('drc','deep_lvs','flat_lvs')]
        assert len(faults)==9 and all(x['expected_verdict_observed']and not x['positive']for x in faults)
        w=v['wires'];g=w['graph'];a=w['anchors']
        assert w['sources_unchanged']and w['physical_GDS_sha256']==GDS[pol]and w['wire_rc_extracted']is False
        assert g['native_device_count']==334 and g['native_terminal_count']==1010
        assert g['native_electrical_net_count']==120 and g['wire_component_count']==119
        assert g['no_wire_geometry_change']and g['no_component_union_by_native_label']
        assert a['counts']==dict(devices=334,terminals=1010,metal_terminals=684,body_terminals=326,public_ports=11,unique_reference_planes=695,wire_components=119)
        assert len(a['negative_controls'])==7 and all(x['rejected']for x in a['negative_controls'])
        m=v['native_material'];c=m['native_comparison'];plan=m['generation_comparison']
        assert m['polarity']==pol and m['native_geometry_delta_proved']and m['all_inputs_byte_unchanged']and m['no_GDS_written']
        assert m['runtime_klayout_version']=='0.30.7'and m['actual_topmetal1_layer']==[126,0]
        assert m['post_fault_positive']==c and c['changed_shape_records']==1 and c['all_non_target_shapes_text_properties_instances_equal']
        assert c['old_box_dbu']=='(109000,85030;115000,2367030)'and c['new_box_dbu']=='(103000,85030;121000,2367030)'
        assert plan['source_old_rect_um']==[109.,89.,115.,2371.]and plan['source_new_rect_um']==[103.,89.,121.,2371.]
        assert len(m['actual_native_faults'])==20 and all(x['rejected']for x in m['actual_native_faults'])
        assert len(m['actual_text_serialization_positives'])==2 and all(x['json_roundtrip']for x in m['actual_text_serialization_positives'])
        assert r['outputs']['physical-'+pol+'-native-material.json']==digest((json.dumps(m,indent=2)+'\n').encode())
    return True

def validate_metadata(run,job,info,ref):
    assert run['id']==SOURCE['run']and run['head_sha']==SOURCE['head']and run['run_attempt']==1
    assert run['status']=='completed'and run['conclusion']=='success'
    assert run['path']=='.github/workflows/tx-phase-reset244-avss18-physical-cloud.yml'
    assert run['head_branch']=='codex/phase318-saved-capture-diagnosis'
    assert job['id']==SOURCE['job']and job['run_id']==SOURCE['run']and job['head_sha']==SOURCE['head']
    assert job['run_attempt']==1 and job['status']=='completed'and job['conclusion']=='success'
    assert info['id']==SOURCE['release'];release.validate_release(info,ref,TAG,SOURCE['head'])
    for a in ASSETS.values():
        matches=[x for x in info['assets']if x['name']==a['name']];assert len(matches)==1
        actual=matches[0];assert actual['id']==a['id']and actual['size']==a['size']and actual['state']=='uploaded'
        assert actual['digest']=='sha256:'+a['sha256']
    return True

def prerequisite():
    b,r=physical()
    run=frozen.api('actions/runs/'+str(SOURCE['run']));job=frozen.api('actions/jobs/'+str(SOURCE['job']))
    info=frozen.api('releases/'+str(SOURCE['release']));ref=frozen.api('git/ref/tags/'+TAG)
    validate_metadata(run,job,info,ref)
    assert frozen.raw_asset(ASSETS['summary'])==b
    return r,dict(source=SOURCE,run=run,job=job,release=info,tag=ref)

def expected_files(r):
    validate(r);expected=dict(r['outputs']);assert 'result.json'not in expected
    expected['result.json']=SOURCE['summary'];assert len(expected)==407
    return expected

def restore(r,destination):
    b,exact=physical();assert r==exact
    _,pre=prerequisite()
    transport=destination.parent/'physical-transport';transport.mkdir(exist_ok=False)
    (transport/'summary.json').write_bytes(b)
    raw=frozen.raw_asset(ASSETS['parts']);(transport/'parts.json').write_bytes(raw);m=json.loads(raw);a=ASSETS['archive']
    assert m['format']=='ordered-tar-gzip-parts-v1'
    assert m['stem']==STEM and m['source_directory']==ROOT_NAME
    assert m['bytes']==a['size']and m['sha256']==a['sha256']
    assert m['parts']==[dict(index=0,name=a['name'],bytes=a['size'],sha256=a['sha256'])]
    part=transport/a['name']
    with part.open('xb')as output:
        subprocess.run(['gh','api','--allow-escape-sequences','-H','Accept: application/octet-stream',
          'repos/'+frozen.REPO+'/releases/assets/'+str(a['id'])],stdout=output,check=True)
    proof=chunks.verify_parts(m,transport)
    inventory=frozen.audit_archive(part,expected_files(r),destination,ROOT_NAME)
    assert(destination/'result.json').read_bytes()==b
    for pol in ('p','n'):
        assert json.loads((destination/pol/'layout/result.json').read_bytes())==r['variants'][pol]['generation']
        assert json.loads((destination/('physical-'+pol+'-native-material.json')).read_bytes())==r['variants'][pol]['native_material']
    return dict(prerequisite=pre,directory=str(destination),inventory=inventory,transport=proof,
      all407_files_authenticated=True,original_electrical_rejection_preserved=True)
