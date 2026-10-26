#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact631 outer capsule and distinct617 native physical view admission; no native calls."""
import copy,hashlib,json,os,subprocess
from pathlib import Path
import cloud_chunked_results as chunks
import tx_phase_reset244_avss18_baseline as frozen
import ensure_cloud_tested_source_release as release
ROOT=Path(__file__).resolve().parents[1]
METHOD=ROOT/'scripts/tx-phase-reset334-tail-m4-rc-methods.json'
SUMMARY='docs/evidence/tx-phase-reset334-tail-M4-physical-native-20261026-summary.json'
NATIVE='docs/evidence/tx-phase-reset334-tail-M4-physical-native-20261026-result.json'
SOURCE={'run': 40375727831, 'job': 121758756410, 'head': '534f894ef21307c104f67abd2448893a9f86bd57', 'group': 'tx-phase-reset334-tail-m4-physical', 'release': 424599302, 'summary': '8e7dc82caeb1984e38e818755039be83c459f9eea0ec754dfb827194e04dad4c'}
NATIVE_SHA='c79aeb97562e606d8399def2e3612245e1acfe5be1d46a6a86cadd3e5a46b3b5'
NATIVE_SOURCE=dict(SOURCE,summary=NATIVE_SHA)
STEM=SOURCE['group']+'-'+str(SOURCE['run'])+'-1'
TAG='cloud-results-'+str(SOURCE['run'])+'-1-'+SOURCE['group']
ROOT_NAME='cloud-tx-phase-reset334-tail-m4-physical'
ASSETS={'summary': {'id': 679052009, 'name': 'tx-phase-reset334-tail-m4-physical-40375727831-1.summary.json', 'size': 6448223, 'sha256': '8e7dc82caeb1984e38e818755039be83c459f9eea0ec754dfb827194e04dad4c'}, 'native': {'id': 679052374, 'name': 'native-physical-result.json', 'size': 5960887, 'sha256': 'c79aeb97562e606d8399def2e3612245e1acfe5be1d46a6a86cadd3e5a46b3b5'}, 'p_material': {'id': 679052692, 'name': 'physical-p-native-material.json', 'size': 48847, 'sha256': 'ffcbde87467c80bfb825c89b8d2b43650a358f6980e9bfabb5f91673b90db1f6'}, 'n_material': {'id': 679052542, 'name': 'physical-n-native-material.json', 'size': 48847, 'sha256': '3a8b60f7b09d162facda70e16c8396429dc84c4cf28214d9846618b3de004160'}, 'runtime': {'id': 679052809, 'name': 'runtime-preflight.json', 'size': 3557, 'sha256': '5ebf19d9bf3041f600827b04d36cf15c36e1e2ea98f7fd5f653f3da97915d696'}, 'parts': {'id': 679052222, 'name': 'tx-phase-reset334-tail-m4-physical-40375727831-1.parts.json', 'size': 889, 'sha256': 'cfeef9be4be0c74d24fdfd14b65d5cbaee84724e5e1daf74fdc96dbba4c9690e'}, 'archive': {'id': 679052965, 'name': 'tx-phase-reset334-tail-m4-physical-40375727831-1.tar.gz.part0000', 'size': 23135405, 'sha256': 'a3a188dc2625d5dd744d1ac0fb0f67724c97273b55f1a55628bba6a2acc4f746'}}
GDS={'p': '5da78e8e80baf3efbb133075b4cf4060316bd4b347dbc68baff90647a8af4042', 'n': 'c0b9c6016f9df84d40a20d79737bda6cc88e38e820582bde7d3881d81ee365fd'}
TARGETS=[{'net': 'PHASE__XM__XDATA__TAIL', 'device': 'PHASE__XM__XDATA__XSA', 'role': 'XSA', 'terminal': 'E', 'placement_row': 10, 'escape_lane_um': 461.0, 'escape_y_um': 1675.99, 'bus_y_um': 1760.0, 'layer': [50, 0], 'old_source_box_dbu': [460400, 1675790, 461600, 1760200], 'new_source_box_dbu': [459800, 1675790, 462200, 1760200], 'old_native_box_dbu': [460400, 1671820, 461600, 1756230], 'new_native_box_dbu': [459800, 1671820, 462200, 1756230]}, {'net': 'PHASE__XM__XDATA__TAIL', 'device': 'PHASE__XM__XDATA__XSB', 'role': 'XSB', 'terminal': 'E', 'placement_row': 10, 'escape_lane_um': 485.0, 'escape_y_um': 1675.99, 'bus_y_um': 1760.0, 'layer': [50, 0], 'old_source_box_dbu': [484400, 1675790, 485600, 1760200], 'new_source_box_dbu': [483800, 1675790, 486200, 1760200], 'old_native_box_dbu': [484400, 1671820, 485600, 1756230], 'new_native_box_dbu': [483800, 1671820, 486200, 1756230]}, {'net': 'PHASE__XM__XDATA__TAIL', 'device': 'PHASE__XM__XDATA__XT', 'role': 'XT', 'terminal': 'C', 'placement_row': 10, 'escape_lane_um': 503.0, 'escape_y_um': 1677.28, 'bus_y_um': 1760.0, 'layer': [50, 0], 'old_source_box_dbu': [502400, 1677080, 503600, 1760200], 'new_source_box_dbu': [501800, 1677080, 504200, 1760200], 'old_native_box_dbu': [502400, 1673110, 503600, 1756230], 'new_native_box_dbu': [501800, 1673110, 504200, 1756230]}, {'net': 'PHASE__XM__XHOLD__TAIL', 'device': 'PHASE__XM__XHOLD__XSA', 'role': 'XSA', 'terminal': 'E', 'placement_row': 11, 'escape_lane_um': 461.0, 'escape_y_um': 1839.99, 'bus_y_um': 1924.0, 'layer': [50, 0], 'old_source_box_dbu': [460400, 1839790, 461600, 1924200], 'new_source_box_dbu': [459800, 1839790, 462200, 1924200], 'old_native_box_dbu': [460400, 1835820, 461600, 1920230], 'new_native_box_dbu': [459800, 1835820, 462200, 1920230]}, {'net': 'PHASE__XM__XHOLD__TAIL', 'device': 'PHASE__XM__XHOLD__XSB', 'role': 'XSB', 'terminal': 'E', 'placement_row': 11, 'escape_lane_um': 485.0, 'escape_y_um': 1839.99, 'bus_y_um': 1924.0, 'layer': [50, 0], 'old_source_box_dbu': [484400, 1839790, 485600, 1924200], 'new_source_box_dbu': [483800, 1839790, 486200, 1924200], 'old_native_box_dbu': [484400, 1835820, 485600, 1920230], 'new_native_box_dbu': [483800, 1835820, 486200, 1920230]}, {'net': 'PHASE__XM__XHOLD__TAIL', 'device': 'PHASE__XM__XHOLD__XT', 'role': 'XT', 'terminal': 'C', 'placement_row': 11, 'escape_lane_um': 503.0, 'escape_y_um': 1841.28, 'bus_y_um': 1924.0, 'layer': [50, 0], 'old_source_box_dbu': [502400, 1841080, 503600, 1924200], 'new_source_box_dbu': [501800, 1841080, 504200, 1924200], 'old_native_box_dbu': [502400, 1837110, 503600, 1920230], 'new_native_box_dbu': [501800, 1837110, 504200, 1920230]}, {'net': 'PHASE__XS__XDATA__TAIL', 'device': 'PHASE__XS__XDATA__XSA', 'role': 'XSA', 'terminal': 'E', 'placement_row': 13, 'escape_lane_um': 461.0, 'escape_y_um': 2167.995, 'bus_y_um': 2252.0, 'layer': [50, 0], 'old_source_box_dbu': [460400, 2167795, 461600, 2252200], 'new_source_box_dbu': [459800, 2167795, 462200, 2252200], 'old_native_box_dbu': [460400, 2163825, 461600, 2248230], 'new_native_box_dbu': [459800, 2163825, 462200, 2248230]}, {'net': 'PHASE__XS__XDATA__TAIL', 'device': 'PHASE__XS__XDATA__XSB', 'role': 'XSB', 'terminal': 'E', 'placement_row': 13, 'escape_lane_um': 485.0, 'escape_y_um': 2167.995, 'bus_y_um': 2252.0, 'layer': [50, 0], 'old_source_box_dbu': [484400, 2167795, 485600, 2252200], 'new_source_box_dbu': [483800, 2167795, 486200, 2252200], 'old_native_box_dbu': [484400, 2163825, 485600, 2248230], 'new_native_box_dbu': [483800, 2163825, 486200, 2248230]}, {'net': 'PHASE__XS__XDATA__TAIL', 'device': 'PHASE__XS__XDATA__XT', 'role': 'XT', 'terminal': 'C', 'placement_row': 13, 'escape_lane_um': 503.0, 'escape_y_um': 2169.28, 'bus_y_um': 2252.0, 'layer': [50, 0], 'old_source_box_dbu': [502400, 2169080, 503600, 2252200], 'new_source_box_dbu': [501800, 2169080, 504200, 2252200], 'old_native_box_dbu': [502400, 2165110, 503600, 2248230], 'new_native_box_dbu': [501800, 2165110, 504200, 2248230]}, {'net': 'PHASE__XS__XHOLD__TAIL', 'device': 'PHASE__XS__XHOLD__XSA', 'role': 'XSA', 'terminal': 'E', 'placement_row': 14, 'escape_lane_um': 461.0, 'escape_y_um': 2331.995, 'bus_y_um': 2416.0, 'layer': [50, 0], 'old_source_box_dbu': [460400, 2331795, 461600, 2416200], 'new_source_box_dbu': [459800, 2331795, 462200, 2416200], 'old_native_box_dbu': [460400, 2327825, 461600, 2412230], 'new_native_box_dbu': [459800, 2327825, 462200, 2412230]}, {'net': 'PHASE__XS__XHOLD__TAIL', 'device': 'PHASE__XS__XHOLD__XSB', 'role': 'XSB', 'terminal': 'E', 'placement_row': 14, 'escape_lane_um': 485.0, 'escape_y_um': 2331.995, 'bus_y_um': 2416.0, 'layer': [50, 0], 'old_source_box_dbu': [484400, 2331795, 485600, 2416200], 'new_source_box_dbu': [483800, 2331795, 486200, 2416200], 'old_native_box_dbu': [484400, 2327825, 485600, 2412230], 'new_native_box_dbu': [483800, 2327825, 486200, 2412230]}, {'net': 'PHASE__XS__XHOLD__TAIL', 'device': 'PHASE__XS__XHOLD__XT', 'role': 'XT', 'terminal': 'C', 'placement_row': 14, 'escape_lane_um': 503.0, 'escape_y_um': 2333.28, 'bus_y_um': 2416.0, 'layer': [50, 0], 'old_source_box_dbu': [502400, 2333080, 503600, 2416200], 'new_source_box_dbu': [501800, 2333080, 504200, 2416200], 'old_native_box_dbu': [502400, 2329110, 503600, 2412230], 'new_native_box_dbu': [501800, 2329110, 504200, 2412230]}]
sha=frozen.sha
def digest(data):return hashlib.sha256(data).hexdigest()
def methods():
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
    assert os.environ.get('GITHUB_REPOSITORY')==frozen.REPO and os.environ.get('GITHUB_RUN_ATTEMPT')=='1'
    m=json.loads(METHOD.read_bytes())
    for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
    for k in ('simulation_authorized','geometry_generation_authorized','continuation_authorized','zero_op_authorized'):
        assert m[k]is False
    assert type(m['native_execution_authorized'])is type(m['source_controls_authorized'])is bool
    assert m['extraction_authorized']is m['native_execution_authorized']
    return m

def native_physical():
    raw=(ROOT/NATIVE).read_bytes()
    assert len(raw)==ASSETS['native']['size']and digest(raw)==NATIVE_SHA
    r=json.loads(raw);validate(r);return raw,r

def physical():
    raw=(ROOT/SUMMARY).read_bytes()
    assert len(raw)==ASSETS['summary']['size']and digest(raw)==SOURCE['summary']
    r=json.loads(raw);_,native=native_physical();validate_outer(r,native);return raw,r

def validate_outer(r,native):
    validate(native)
    assert (r['source_head'],r['run_id'],r['run_attempt'])==(SOURCE['head'],SOURCE['run'],1)
    assert r['status']==native['status']
    assert r['native_result']==native and r['native_result_sha256']==NATIVE_SHA
    assert r['native_result_bytes']==ASSETS['native']['size']and r['native_result_raw_path']=='native-physical-result.json'
    for k in ('native_generation_completed','physical_gates_passed','protected_sources_unchanged',
              'native_result_present','fresh_RC_required','fresh_loaded_waveforms_required','original_electrical_rejection_preserved'):
        assert r[k]is True,k
    for k in ('electrical_accepted','full_phy_accepted','simulation_executed','extraction_executed','continuation_executed','old_R_rescaled'):
        assert r[k]is False,k
    s=r['supervisor']
    assert s['returncode']==0 and s['supervision_failure']is None and s['memory_read_error']is None
    assert s['process_group_cleanup']['remaining_live']==[]
    assert s['minimum_available_kib']==2097152 and s['maximum_group_rss_kib']==10485760
    assert len(r['outputs'])==630 and 'result.json'not in r['outputs']
    assert r['outputs']['native/result.json']==r['outputs']['native-physical-result.json']==NATIVE_SHA
    assert all(r['outputs']['native/'+p]==h for p,h in native['outputs'].items())
    for k in ('native','p_material','n_material','runtime'):
        assert r['outputs'][ASSETS[k]['name']]==ASSETS[k]['sha256']
    return True

def validate(r):
    assert r['source_head']==SOURCE['head']and r['sources_unchanged']and not r['validation_errors']
    assert r['status']=='PASS_BOTH_TAIL_M4_EXACT12_MATERIAL_334_PHYSICAL_1010_TERMINALS_REQUIRES_FRESH_MIM_RC_LOADED'
    assert set(r['variants'])=={'p','n'}and len(r['outputs'])==616
    assert r['original_baseline_byte_unchanged']and r['exact12_native_M4_rectangles_per_polarity_proved']
    assert r['original_electrical_rejection_preserved']and r['old_R_rescaled']is False
    assert r['fresh_RC_required']and r['fresh_loaded_waveforms_required']
    for k in ('accepted','qualified_pex','electrical_accepted','physical_reset_qualified','all31_clock_tree_accepted','PLL_connected','full_phy_accepted'):assert r[k]is False
    for pol,v in r['variants'].items():
        top='nssoc_tx_phase_reset244_'+pol+'_v1'
        assert v['status']=='PASS_TAIL_M4_MATERIAL40_FAULTS334_DRC_DEEP_FLAT_LVS9_FAULTS1010_TERMINALS7_FAULTS_REQUIRES_FRESH_RC_LOADED'
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
        assert m['runtime_klayout_version']=='0.30.7'and m['actual_metal4_layer']==[50,0]
        assert m['post_fault_positive']==c and c['changed_shape_records']==12 and c['all_non_target_shapes_text_properties_instances_equal']
        assert c['exact_target_plan']==TARGETS and plan['expected_native_box_deltas']==TARGETS
        assert plan['changed_M4_rectangles']==12 and plan['all_other_report_fields_equal']
        assert c['dbu_um']==.001 and len(c['materials'])==33
        metal=[x for x in c['materials']if x['layer']==[50,0]];assert len(metal)==1
        assert metal[0]['exact_expected_union']and metal[0]['removed_area_dbu2']==0
        assert metal[0]['added_area_dbu2']==1209288000
        assert all(x['unchanged']is True for x in c['materials']if x['layer']!=[50,0])
        assert len(m['actual_native_faults'])==40 and len({x['name']for x in m['actual_native_faults']})==40
        assert all(x['rejected']for x in m['actual_native_faults'])
        assert len(m['actual_text_serialization_positives'])==2 and all(x['json_roundtrip']for x in m['actual_text_serialization_positives'])
        assert r['outputs']['physical-'+pol+'-native-material.json']==digest((json.dumps(m,indent=2)+'\n').encode())
    return True

def validate_metadata(run,job,info,ref):
    assert run['id']==SOURCE['run']and run['head_sha']==SOURCE['head']and run['run_attempt']==1
    assert run['status']=='completed'and run['conclusion']=='success'
    assert run['path']=='.github/workflows/tx-phase-reset334-tail-m4-physical-cloud.yml'
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
    raw,outer=physical();native_raw,native=native_physical()
    run=frozen.api('actions/runs/'+str(SOURCE['run']));job=frozen.api('actions/jobs/'+str(SOURCE['job']))
    info=frozen.api('releases/'+str(SOURCE['release']));ref=frozen.api('git/ref/tags/'+TAG)
    validate_metadata(run,job,info,ref)
    assert frozen.raw_asset(ASSETS['summary'])==raw
    assert frozen.raw_asset(ASSETS['native'])==native_raw
    return native,dict(source=SOURCE,native_source=NATIVE_SOURCE,run=run,job=job,release=info,tag=ref,
        outer_summary_sha256=SOURCE['summary'],native_result_sha256=NATIVE_SHA,
        full631_outer_capsule_required=True,distinct617_native_physical_view=True)

def expected_files(outer):
    _,native=native_physical();validate_outer(outer,native)
    expected=dict(outer['outputs']);assert 'result.json'not in expected
    expected['result.json']=SOURCE['summary'];assert len(expected)==631
    return expected

def restore(native,destination):
    raw,outer=physical();native_raw,exact=native_physical();assert native==exact
    _,pre=prerequisite()
    transport=destination.parent/'physical-transport';transport.mkdir(exist_ok=False)
    (transport/'summary.json').write_bytes(raw)
    part_raw=frozen.raw_asset(ASSETS['parts']);(transport/'parts.json').write_bytes(part_raw)
    manifest=json.loads(part_raw);asset=ASSETS['archive']
    assert manifest['format']=='ordered-tar-gzip-parts-v1'
    assert manifest['stem']==STEM and manifest['source_directory']==ROOT_NAME
    assert manifest['bytes']==asset['size']and manifest['sha256']==asset['sha256']
    assert manifest['parts']==[dict(index=0,name=asset['name'],bytes=asset['size'],sha256=asset['sha256'])]
    part=transport/asset['name']
    with part.open('xb')as output:
        subprocess.run(['gh','api','--allow-escape-sequences','-H','Accept: application/octet-stream',
          'repos/'+frozen.REPO+'/releases/assets/'+str(asset['id'])],stdout=output,check=True)
    proof=chunks.verify_parts(manifest,transport)
    inventory=frozen.audit_archive(part,expected_files(outer),destination,ROOT_NAME)
    assert(destination/'result.json').read_bytes()==raw
    view=destination/'native'
    assert(view/'result.json').read_bytes()==native_raw
    assert(destination/'native-physical-result.json').read_bytes()==native_raw
    view_expected=dict(native['outputs'],**{'result.json':NATIVE_SHA})
    assert len(view_expected)==617
    actual={str(p.relative_to(view)):sha(p)for p in view.rglob('*')if p.is_file()}
    assert actual==view_expected
    for pol in ('p','n'):
        assert json.loads((view/pol/'layout/result.json').read_bytes())==native['variants'][pol]['generation']
        for base in (destination,view):
            assert json.loads((base/('physical-'+pol+'-native-material.json')).read_bytes())==native['variants'][pol]['native_material']
    return dict(prerequisite=pre,directory=str(destination),physical_view=str(view),inventory=inventory,transport=proof,
      all631_files_authenticated=True,native617_view_authenticated=True,
      outer_summary_sha256=SOURCE['summary'],native_result_sha256=NATIVE_SHA,
      original_electrical_rejection_preserved=True)
