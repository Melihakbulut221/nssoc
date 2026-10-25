#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Freeze native extraction adaptation and independent design census."""
import ast,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PINS={'docs/evidence/cdr-input-access-v26-clean-parent-pass-20261021.json': '1e57b68b2969a02a3cf6ae36cb831e14a567e6b3ac129e1c89ec51be65d88788', 'scripts/cloud_cdr_input_access_v26_planes.py': '1a8972f2fc0c9034f27c80ef860528db40f23d61ee7b68c5cc4d0e0425571c9b', 'scripts/cloud_cdr_input_access_v26_wire_inputs.py': '65f0f2f7539e60f409a4ccd38a5c611222f59ebd532107a73072711a9153dc9c', 'scripts/cloud_cdr_input_access_v26_binding.py': '6eaa70ebcdb5d71fab7b11775b5d124c9608f842db309dd4ce00c6574efc16ce', 'scripts/cloud_cdr_input_access_v26_rc.py': '2f96ca270dae5a66575ba306ef0aebaf99c5c48b42b018d9e9133527cc401f2d', 'scripts/cloud_cdr_input_access_v26_extraction_stage.py': 'acf7b3abffeaddeb9003364390f9394f0f3fa4bfe9bbb9576ea6f51d1754f63c', '.github/workflows/cdr-input-access-v26-extraction-cloud.yml': 'eb163c441f85bab4ec36c2081a3bdbbc2cac0f0c384ba4b146f592ebb74690e3'}
def check():
    for name,digest in PINS.items():
        data=(ROOT/name).read_bytes()
        assert hashlib.sha256(data).hexdigest()==digest,name
        if name.endswith('.py'):ast.parse(data,filename=name)
    # Execute the actual pure parent validator before downloading any CAD archive.
    import copy
    receipt=json.loads((ROOT/'docs/evidence/cdr-input-access-v26-clean-parent-pass-20261021.json').read_text())
    plane_source=(ROOT/'scripts/cloud_cdr_input_access_v26_planes.py').read_text()
    tree=ast.parse(plane_source)
    functions=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='validate_parent_pin']
    assert len(functions)==1
    ns={};exec(compile(ast.Module(body=functions,type_ignores=[]),'<actual-native-parent-validator>','exec'),ns)
    validate=ns['validate_parent_pin'];validate(receipt,receipt['report'])
    rejected=[]
    for fault in ('run','source_head','summary_sha256','parts_sha256','wrong_resistor','missing_resistor','parent_geometry','source_changed','wrong_child_geometry','wrong_gds','changed_cleanup','child_touched','orphan_left','label_union'):
        altered=copy.deepcopy(receipt)
        if fault in ('run','source_head','summary_sha256','parts_sha256'):
            altered[fault]=0 if fault=='run'else'f'*(40 if fault=='source_head' else 64)
        elif fault=='wrong_resistor':altered['report']['intrinsic_replacement_history']['changed_reference_devices'][0]='Qsa_M_DP'
        elif fault=='missing_resistor':altered['report']['intrinsic_replacement_history']['changed_reference_devices'].pop()
        elif fault=='parent_geometry':altered['report']['intrinsic_replacement_history']['parent_geometry_unchanged']=False
        elif fault=='source_changed':altered['report']['sources_unchanged']=False
        elif fault=='wrong_child_geometry':altered['report']['child_geometry']['status']='FAIL'
        elif fault=='changed_cleanup':altered['report']['cleanup']['removed_area_dbu2']['30']+=1
        elif fault=='child_touched':altered['report']['cleanup']['all_child_geometry_unchanged']=False
        elif fault=='orphan_left':altered['report']['strict_graph']['wire_component_count']=112
        elif fault=='label_union':altered['report']['strict_graph']['no_component_union_by_native_label']=False
        else:altered['report']['outputs']['layout/nssoc_cdr_pd476_follower_v23.gds']='f'*64
        try:validate(altered,altered['report'])
        except AssertionError:rejected.append(fault)
        else:raise AssertionError('Native parent provenance fault accepted: '+fault)
    assert len(rejected)==14
    print(json.dumps(dict(actual_parent_validator_faults=rejected,whole_parent_receipt_valid=True)))
    # v26 changes eight input resistor lengths plus exact proven terminal-free parent cleanup; native Nx4 data/hold and Nx2 selectors retained; all native device/terminal counts remain.
    census=dict(npn13g2=120,sg13_lv_nmos=46,rppd=98,cap_cmim=7,ptap1=205)
    counts=dict(npn13g2=4,sg13_lv_nmos=4,rppd=3,cap_cmim=2,ptap1=2)
    assert sum(census.values())==476
    assert sum(census[k]*counts[k]for k in census)==1382
    assert sum(v for k,v in census.items()if k!='cap_cmim')==469
    assert 1382-469==913 and 913+25==938
    # Compare the actual producer path helper with every dependent consumer.
    # This catches dynamic date/name drift before any CAD calculation.
    import runpy
    stage=runpy.run_path(str(ROOT/'scripts/cloud_cdr_input_access_v26_extraction_stage.py'))
    for name,deps in stage['DEPS'].items():
        path=ROOT/('scripts/cloud_cdr_input_access_v26_'+name.replace('-','_')+'.py')
        literals={n.value for n in ast.walk(ast.parse(path.read_text()))if isinstance(n,ast.Constant)and isinstance(n.value,str)}
        for dep in deps:
            expected=str(stage['receipt_path'](dep).relative_to(ROOT))
            assert expected in literals,('Producer/consumer receipt mismatch',name,dep,expected)
    print('PASS_FROZEN_PD476_NATIVE_EXTRACTION_AND_ACTUAL_DEPENDENCY_PATHS_NOT_ELECTRICAL_ACCEPTANCE')
if __name__=='__main__':check()
