#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Require exact native parent500 evidence and reject stale/incorrect handoffs."""
import ast,copy,hashlib,json,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    pins=json.loads((ROOT/'scripts/cdr-sampler-active-input-v57-extraction-pins.json').read_text())
    for n,digest in pins.items():
        b=(ROOT/n).read_bytes();assert hashlib.sha256(b).hexdigest()==digest,n
        if n.endswith('.py'):ast.parse(b,filename=n)
    from cloud_cdr_sampler_active_input_v57_planes import validate_parent_pin
    receipt=json.loads((ROOT/'docs/evidence/cdr-sampler-active-input-v57-parent-physical-pass-20261024.json').read_text())
    validate_parent_pin(receipt,receipt['report'])
    faults=['run','source_head','summary_sha256','parts_sha256','gds','census','tags','AB','control','count','physical','sources','geometry','child','lvs','baseline','leaf','bypass','widening','wire-short']
    for fault in faults:
        p=copy.deepcopy(receipt);r=p['report'];g=r['replacement']
        if fault in ('run','source_head','summary_sha256','parts_sha256'):p[fault]=0 if fault=='run'else 'f'*64
        elif fault=='gds':r['outputs']['layout/nssoc_cdr_pd500_active_input_v57.gds']='f'*64
        elif fault=='census':r['layout']['primitive_census']['npn13g2']-=1
        elif fault=='tags':g['changed_sampler_tags']=['sa','sb']
        elif fault=='AB':r['layout']['placements']['sa']['kind']='sampler_cd'
        elif fault=='control':g['controls'].pop()
        elif fault=='count':g['preserved_reference_devices']-=1
        elif fault=='physical':r['physical']['status']='FAIL'
        elif fault=='sources':r['sources_unchanged']=False
        elif fault=='geometry':g['parent_geometry_changes']['all_other_parent_layers_unchanged']=False
        elif fault=='child':r['child_geometry']['controls'].pop()
        elif fault=='lvs':r['physical']['steps']['lvs_flat']['audit']['circuits'][0]['layout_devices_recursive']=476
        elif fault=='baseline':r['parent_source']['manifest_sha256']='f'*64
        elif fault=='leaf':r['data_source']['manifest_sha256']='f'*64
        elif fault=='bypass':g['parent_geometry_changes']['m4_enclosures'][0]['root_owned_via_contacts']['49']=99
        elif fault=='widening':g['parent_geometry_changes']['additional_widening_ring_removals'].pop()
        elif fault=='wire-short':g['parent_geometry_changes']['drawing_only_supply_separation']['separate']=False
        try:validate_parent_pin(p,r)
        except AssertionError:pass
        else:raise AssertionError('Accepted invalid parent '+fault)
    census=dict(npn13g2=124,sg13_lv_nmos=50,rppd=98,cap_cmim=7,ptap1=221)
    terminals=dict(npn13g2=4,sg13_lv_nmos=4,rppd=3,cap_cmim=2,ptap1=2)
    assert sum(census.values())==500 and sum(census[k]*terminals[k]for k in census)==1446
    assert 1446-493==953 and 953+25==978
    old=ast.parse((ROOT/'scripts/cloud_cdr_sampler_settling_v32_wire_inputs.py').read_text())
    new=ast.parse((ROOT/'scripts/cloud_cdr_sampler_active_input_v57_wire_inputs.py').read_text())
    a=next(n for n in old.body if isinstance(n,ast.FunctionDef)and n.name=='recover')
    b=next(n for n in new.body if isinstance(n,ast.FunctionDef)and n.name=='recover')
    assert ast.dump(a)==ast.dump(b),'Native primitive signature/annotation matcher changed'
    stage=runpy.run_path(str(ROOT/'scripts/cloud_cdr_sampler_active_input_v57_extraction_stage.py'))
    assert stage['DEPS']=={'planes':[],'wire-inputs':['planes']}
    for name,deps in stage['DEPS'].items():
        source=ROOT/('scripts/cloud_cdr_sampler_active_input_v57_'+name.replace('-','_')+'.py')
        literals={n.value for n in ast.walk(ast.parse(source.read_text()))if isinstance(n,ast.Constant)and isinstance(n.value,str)}
        for dep in deps:assert str(stage['receipt_path'](dep).relative_to(ROOT))in literals
        assert 'docs/evidence/cdr-sampler-active-input-v57-parent-physical-pass-20261024.json'in literals
        assert 'docs/evidence/cdr-sampler-settling-v32-parent-physical-pass-20261022.json'not in literals
    return dict(status='PASS_PARENT500_IDENTITY_20_CORRUPTIONS_AND_NATIVE_EXTRACTION_HANDOFF',faults=faults,full_phy_accepted=False)
if __name__=='__main__':print(json.dumps(check()))
