#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Freeze native extraction adaptation and independent design census."""
import ast,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PINS={'scripts/cloud_cdr_bias_access_v27_planes.py': '07b0e1dbdd112caf057d0b879870b399dd1a5913fb2bec7e6f39f827a8dedbab', 'scripts/cloud_cdr_bias_access_v27_wire_inputs.py': '374415925787de3be68541eaea13cc4a40202a53290f5819bca18c7d7fd953ec', 'scripts/cloud_cdr_bias_access_v27_binding.py': '9f701407666cb33d98af39af35a890ec3bca6496f019820055995041370dc058', 'scripts/cloud_cdr_bias_access_v27_rc.py': 'b0725798b1e8294645616786fd63a807ba8658d646ea0583f5b4691ded42d70c', 'scripts/cloud_cdr_bias_access_v27_extraction_stage.py': '698c65144c1e60933c585544cd586336d14ad326416feb4bf412e31deaa8d5c9', '.github/workflows/cdr-bias-access-v27-extraction-cloud.yml': '9626475ebb5c86dfe55243d06a50fefa9427724d511fa31fa2bfaf77ce163aea', 'docs/evidence/cdr-bias-access-v27-parent-physical-pass-20261021.json': '0dee45631abc50aee3ac9092050cee59802e37f9f65a1f4f18a2d8853774188b', 'scripts/cloud_cdr_input_access_v26_planes.py': '1a8972f2fc0c9034f27c80ef860528db40f23d61ee7b68c5cc4d0e0425571c9b', 'docs/evidence/cdr-input-access-v26-clean-parent-pass-20261021.json': '1e57b68b2969a02a3cf6ae36cb831e14a567e6b3ac129e1c89ec51be65d88788'}
def check():
    for name,digest in PINS.items():
        data=(ROOT/name).read_bytes()
        assert hashlib.sha256(data).hexdigest()==digest,name
        if name.endswith('.py'):ast.parse(data,filename=name)
    # Execute the actual pure parent validator before downloading any CAD archive.
    import copy
    receipt=json.loads((ROOT/'docs/evidence/cdr-bias-access-v27-parent-physical-pass-20261021.json').read_text())
    plane_source=(ROOT/'scripts/cloud_cdr_bias_access_v27_planes.py').read_text()
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
        elif fault=='wrong_resistor':altered['report']['replacement']['changed_reference_devices'][0]='Qsa_M_DP'
        elif fault=='missing_resistor':altered['report']['replacement']['changed_reference_devices'].pop()
        elif fault=='parent_geometry':altered['report']['replacement']['parent_geometry_unchanged']=False
        elif fault=='source_changed':altered['report']['sources_unchanged']=False
        elif fault=='wrong_child_geometry':altered['report']['child_geometry']['status']='FAIL'
        elif fault=='changed_cleanup':altered['baseline_clean_parent']['report']['cleanup']['removed_area_dbu2']['30']+=1
        elif fault=='child_touched':altered['baseline_clean_parent']['report']['cleanup']['all_child_geometry_unchanged']=False
        elif fault=='orphan_left':altered['baseline_clean_parent']['report']['strict_graph']['wire_component_count']=112
        elif fault=='label_union':altered['baseline_clean_parent']['report']['strict_graph']['no_component_union_by_native_label']=False
        else:altered['report']['outputs']['layout/nssoc_cdr_pd476_follower_v23.gds']='f'*64
        try:validate(altered,altered['report'])
        except AssertionError:rejected.append(fault)
        else:raise AssertionError('Native parent provenance fault accepted: '+fault)
    assert len(rejected)==14
    print(json.dumps(dict(actual_parent_validator_faults=rejected,whole_parent_receipt_valid=True)))
    # v27 changes eight bias resistor lengths on the exact cleaned v26 baseline; old cleanup checks remain, and the new strict graph is independently required by wire-inputs.
    census=dict(npn13g2=120,sg13_lv_nmos=46,rppd=98,cap_cmim=7,ptap1=205)
    counts=dict(npn13g2=4,sg13_lv_nmos=4,rppd=3,cap_cmim=2,ptap1=2)
    assert sum(census.values())==476
    assert sum(census[k]*counts[k]for k in census)==1382
    assert sum(v for k,v in census.items()if k!='cap_cmim')==469
    assert 1382-469==913 and 913+25==938
    # Compare the actual producer path helper with every dependent consumer.
    # This catches dynamic date/name drift before any CAD calculation.
    import runpy
    stage=runpy.run_path(str(ROOT/'scripts/cloud_cdr_bias_access_v27_extraction_stage.py'))
    for name,deps in stage['DEPS'].items():
        path=ROOT/('scripts/cloud_cdr_bias_access_v27_'+name.replace('-','_')+'.py')
        literals={n.value for n in ast.walk(ast.parse(path.read_text()))if isinstance(n,ast.Constant)and isinstance(n.value,str)}
        for dep in deps:
            expected=str(stage['receipt_path'](dep).relative_to(ROOT))
            assert expected in literals,('Producer/consumer receipt mismatch',name,dep,expected)
    print('PASS_FROZEN_PD476_NATIVE_EXTRACTION_AND_ACTUAL_DEPENDENCY_PATHS_NOT_ELECTRICAL_ACCEPTANCE')
if __name__=='__main__':check()
