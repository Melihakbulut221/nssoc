#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Require verified clean baseline, exact v29 physical replacement and fresh native extraction."""
import ast,copy,hashlib,json,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    # Keep every original clean-v27 geometry/orphan/raw-source control active.
    from check_cdr_bias_access_v27_extraction_sources import check as baseline_check
    baseline_check()
    manifest=json.loads((ROOT/'scripts/cdr-gain-headroom-v29-extraction-pins.json').read_text())
    for name,digest in manifest.items():
        data=(ROOT/name).read_bytes();assert hashlib.sha256(data).hexdigest()==digest,name
        if name.endswith('.py'):ast.parse(data,filename=name)
    receipt=json.loads((ROOT/'docs/evidence/cdr-gain-headroom-v29-parent-physical-pass-20261022.json').read_text())
    plane_source=(ROOT/'scripts/cloud_cdr_gain_headroom_v29_planes.py').read_text()
    tree=ast.parse(plane_source);f=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='validate_parent_pin'];assert len(f)==1
    ns={};exec(compile(ast.Module(body=f,type_ignores=[]),'<actual-v29-parent-validator>','exec'),ns)
    validate=ns['validate_parent_pin'];validate(receipt,receipt['report'])
    faults=('run','source_head','summary_sha256','parts_sha256','wrong_resistor','missing_resistor','duplicate_resistor','parent_geometry','source_changed','wrong_child_geometry','wrong_gds','wrong_clean_baseline','wrong_baseline_manifest','wrong_leaf','wrong_leaf_manifest','missing_physical','changed_ports','changed_trunks','missing_geometry_control','notch_area','notch_component_count','notch_via','notch_patch','notch_coordinate','notch_same_component','notch_metal_removed')
    rejected=[]
    for fault in faults:
        a=copy.deepcopy(receipt);r=a['report'];g=r['replacement']
        if fault in ('run','source_head','summary_sha256','parts_sha256'):a[fault]=0 if fault=='run'else'f'*(40 if fault=='source_head'else 64)
        elif fault=='wrong_resistor':g['changed_reference_devices'][0]='Qsa_M_DP'
        elif fault=='missing_resistor':g['changed_reference_devices'].pop()
        elif fault=='duplicate_resistor':g['changed_reference_devices'][0]=g['changed_reference_devices'][1]
        elif fault=='parent_geometry':g['all_original_parent_geometry_retained']=False
        elif fault=='source_changed':r['sources_unchanged']=False
        elif fault=='wrong_child_geometry':r['child_geometry']['status']='FAIL'
        elif fault=='wrong_gds':r['outputs']['layout/nssoc_cdr_pd476_follower_v23.gds']='f'*64
        elif fault=='wrong_clean_baseline':r['parent_source']['summary_sha256']='f'*64
        elif fault=='wrong_baseline_manifest':r['parent_source']['manifest_sha256']='f'*64
        elif fault=='wrong_leaf':r['data_source']['summary_sha256']='f'*64
        elif fault=='wrong_leaf_manifest':r['data_source']['manifest_sha256']='f'*64
        elif fault=='missing_physical':r['physical']['status']='FAIL'
        elif fault=='changed_ports':g['external_leaf_ports_and_bbox_unchanged']=False
        elif fault=='changed_trunks':g['all_existing_collector_retime_trunks_retained']=False
        elif fault=='missing_geometry_control':g['controls'].pop()
        elif fault=='notch_area':g['m4_notch_fill']['added_flat_metal_area_dbu2']+=1
        elif fault=='notch_component_count':g['m4_notch_fill']['new_component_count']-=1
        elif fault=='notch_via':g['m4_notch_fill']['no_new_via_connections']=False
        elif fault=='notch_patch':g['m4_notch_fill']['patches'].pop()
        elif fault=='notch_coordinate':g['m4_notch_fill']['patches'][0]['box_dbu'][0]+=5
        elif fault=='notch_same_component':g['m4_notch_fill']['patches'][0]['touched_existing_m4_components']=2
        elif fault=='notch_metal_removed':g['m4_notch_fill']['all_original_metal_preserved']=False
        try:validate(a,r)
        except AssertionError:rejected.append(fault)
        else:raise AssertionError('Invalid actual v29 source accepted: '+fault)
    assert len(rejected)==26
    # Intrinsic census remains physical476/1382; actual wire topology is remeasured.
    census=dict(npn13g2=120,sg13_lv_nmos=46,rppd=98,cap_cmim=7,ptap1=205)
    counts=dict(npn13g2=4,sg13_lv_nmos=4,rppd=3,cap_cmim=2,ptap1=2)
    assert sum(census.values())==476 and sum(census[k]*counts[k]for k in census)==1382
    assert 1382-469==913 and 913+25==938
    stage=runpy.run_path(str(ROOT/'scripts/cloud_cdr_gain_headroom_v29_extraction_stage.py'))
    for name,deps in stage['DEPS'].items():
        path=ROOT/('scripts/cloud_cdr_gain_headroom_v29_'+name.replace('-','_')+'.py')
        literals={n.value for n in ast.walk(ast.parse(path.read_text()))if isinstance(n,ast.Constant)and isinstance(n.value,str)}
        for dep in deps:assert str(stage['receipt_path'](dep).relative_to(ROOT))in literals,('Producer/consumer mismatch',name,dep)
    def parent_binding(text):
        tree=ast.parse(text);literals={n.value for n in ast.walk(tree)if isinstance(n,ast.Constant)and isinstance(n.value,str)}
        assert 'docs/evidence/cdr-gain-headroom-v29-parent-physical-pass-20261022.json'in literals
        assert 'docs/evidence/cdr-bias-access-v27-clean-parent-pass-20261021.json'not in literals
        calls=[n for n in ast.walk(tree)if isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)and n.func.attr=='restore_report'and n.args and isinstance(n.args[0],ast.Constant)]
        groups=[n.args[0].value for n in calls if 'parent'in str(n.args[0].value)]
        assert groups==['cdr-gain-headroom-v29-parent']
    for suffix in ('planes','wire_inputs'):
        s=(ROOT/('scripts/cloud_cdr_gain_headroom_v29_'+suffix+'.py')).read_text();parent_binding(s)
        for bad in (s.replace('cdr-gain-headroom-v29-parent-physical-pass-20261022.json','cdr-bias-access-v27-clean-parent-pass-20261021.json'),s.replace("restore_report('cdr-gain-headroom-v29-parent',","restore_report('cdr-bias-access-v27-clean-parent',")):
            assert bad!=s
            try:parent_binding(bad)
            except AssertionError:pass
            else:raise AssertionError('Stale v27 consumer accepted')
    # Critical native measurement bodies are byte-identical to the verified prior method.
    for suffix,functions in [('planes',['native']),('wire_inputs',['recover']),('binding',['native_export','verify','controls','build','geometry_readback_matches','geometry_readback_controls'])]:
        old=ast.parse((ROOT/('scripts/cloud_cdr_bias_access_v27_'+suffix+'.py')).read_text())
        new=ast.parse((ROOT/('scripts/cloud_cdr_gain_headroom_v29_'+suffix+'.py')).read_text())
        for function in functions:
            a=[n for n in old.body if isinstance(n,ast.FunctionDef)and n.name==function]
            b=[n for n in new.body if isinstance(n,ast.FunctionDef)and n.name==function]
            assert len(a)==len(b)==1 and ast.dump(a[0])==ast.dump(b[0]),(suffix,function)
    old_rc=(ROOT/'scripts/cloud_cdr_input_loading_v28_rc.py').read_text()
    expected_rc=old_rc.replace('cdr-input-loading-v28','cdr-gain-headroom-v29').replace('cdr_input_loading_v28','cdr_gain_headroom_v29').replace('20261021','20261022')
    assert (ROOT/'scripts/cloud_cdr_gain_headroom_v29_rc.py').read_text()==expected_rc,'Native RC controls or extractor changed'
    print(json.dumps(dict(status='PASS_V29_PHYSICAL_SOURCE_26FAULTS_AND_FRESH_EXTRACTION_HANDOFF',rejected=rejected,full_phy_accepted=False)))
if __name__=='__main__':check()
