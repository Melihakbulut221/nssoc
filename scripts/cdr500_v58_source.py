#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Frozen physically qualified PD500 v58 source for fresh intrinsic binding and wire RC."""
import copy,hashlib,json
from collections import Counter
from decimal import Decimal
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PIN=ROOT/'docs/evidence/cdr500-input-access-v58-physical-pass-20261024.json'
IDENTITY={'group': 'cdr500-input-access-v58-physical', 'run': 40096705004, 'source_head': '9e7f3d3dd55ec452dfbb27520a73b67f5078067a', 'summary_sha256': 'c757b2d7416031b94f625591f8568a08ff61a60d62ec02c5822325083827515c', 'parts_sha256': 'c0b75c3dc414160400f8a722e09a94679f8e123725e86edc49b5933bdbd207bc'}
GDS='c51ba01ba4c94a4fd59bb4a7462386b474818caf26739e6bb35dbbd9a38ce125'
CENSUS=dict(npn13G2=124,sg13_lv_nmos=50,rppd=98,cap_cmim=7,ptap1=221)
METHODS={'probe01.py': '3d7f3a64ca43bd9f1205d4b403a128f795167be0a0d4ab93df7b1d9c555284df', 'locate01.py': 'ea102b38a4a9dac72fd7a0dea655e8140d2db0e58ca1ce37e3927c510c6f1a43', 'anchors01.py': 'f735b6b43d00d49b0f01eefe1ae9de4ddea76d52a3767f0f8e74c3e25ea321fc', 'dedup01.py': '58ec392e70a89e2b4b6175fbef01413e3417b1d5fb1389aabd6fa7b95b743544'}
def validate(pin,prior=None):
    assert all(pin[k]==v for k,v in IDENTITY.items())
    r=pin['report']if prior is None else prior
    assert r==pin['report'] and r['source_head']==IDENTITY['source_head'] and r['sources_unchanged']
    assert r['status']=='PASS_PD500_V58_OWNED_ACCESS_FULL_PHYSICAL_AND_STRICT_WIRES_REQUIRES_FRESH_MIM_RC'
    assert r['outputs']['parent/layout/nssoc_cdr_pd500_input_access_v58.gds']==GDS
    assert {k:v['generated_sha256']for k,v in r['strict_wire_method_adaptations'].items()}==METHODS
    delta=r['candidate_delta']
    assert delta['added_via_instances']==24 and delta['added_route_rectangles']==20
    assert len(delta['controls'])==9 and len(delta['high_endpoint_cut_controls'])==3
    assert len(delta['native_survey_selection_controls'])==8 and len(delta['serialization_integrity_controls'])==3
    assert delta['original_high_endpoint_two_cut_sets_preserved']==8
    assert delta['native_survey_sha256']=='2e41ff33706aea82769eaa9d9afacec1f373916c2dbd3866f63b2233bd3c4e54'
    for key in ('original_children_drawings_and_placements_preserved','original_public_labels_and_boundary_preserved',
      'serialized_metal_and_via_delta_exact','original_sampler_via1_via2_material_preserved',
      'all_intrinsic_device_bias_and_stimulus_sources_unchanged','serialized_region_materialized_before_exact_xor'):assert delta[key]
    assert not delta['reduced_resistance_claim']and not delta['electrical_accepted']
    assert delta['gds_sha256']==GDS
    physical=r['physical'];assert physical['status']=='PASS_NATIVE_PDK_CDR_PD500_DRC_LVS_AND_FAULT_CONTROLS'
    drc=physical['steps']['drc']['measurement'];assert drc['category_count']==560 and drc['markers']==0
    for mode in ('lvs','lvs_flat'):
        audit=physical['steps'][mode]['audit'];assert audit['status']=='PASS within comparison scope'and not audit['extraction_diagnostics']and audit['circuit_status_counts']=={'Match':1}
        assert len(audit['circuits'])==1 and audit['circuits'][0]['layout_devices_recursive']==audit['circuits'][0]['schematic_devices_recursive']==500
    controls=[v for k,v in physical['steps'].items()if k not in ('drc','lvs','lvs_flat')]
    assert len(controls)==12 and all(v['status']=='REJECTED_EXPECTED_FAULT'for v in controls)
    planes=r['native_planes'];assert planes['status']=='PASS_PD500_NATIVE160_PLANES_51_NETS_19_FAULTS'and len(planes['controls'])==19 and len(planes['anchors'])==160
    child=planes['parent_geometry'];assert child['status']=='PASS_ALL16_ACTUAL_PLACEMENTS_AND_NINE_NATIVE_LEAF_DRAWINGS'and len(child['controls'])==5
    wire=r['strict_wire_graph'];assert wire['status']=='PASS_GEOMETRIC_PUMP_WIRE_COMPONENT_BINDING_NO_RC'
    assert wire['native_devices']==CENSUS and wire['native_device_count']==500 and wire['native_terminal_count']==1446
    assert wire['wire_component_count']==113 and wire['native_net_count']==238
    assert not any(x['metal_area_dbu2']and not x['device_terminals']for x in wire['native_net_coverage'])
    anchors=r['anchors'];assert anchors['logical_anchor_count']==anchors['physical_anchor_count']==978 and anchors['public_ports']==25
    assert anchors['dispositions']==dict(ACTUAL_TERMINAL_METAL_POINT_REFERENCE=953,RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE=493)
    devices=r['device_locations']['devices'];assert Counter(x['model']for x in devices)==CENSUS
    assert Counter(Decimal(str(x['parameters']['W']))for x in devices if x['model']=='sg13_lv_nmos')=={Decimal(8):8,Decimal(32):2,Decimal(36):32,Decimal('53.335'):4,Decimal(64):4}
    assert Counter((Decimal(str(x['parameters']['A'])),Decimal(str(x['parameters']['P'])))for x in devices if x['model']=='ptap1')=={(Decimal(4),Decimal(8)):217,(Decimal(40),Decimal(44)):4}
    return r

def methods():
    record=json.loads((ROOT/'scripts/cdr500-v58-extraction-methods.json').read_text())
    for name,value in record['protected'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==value,name
    return record

def check():
    methods();pin=json.loads(PIN.read_text());validate(pin);controls=[]
    changes=[
      ('wrong_source_hash',lambda p:p.__setitem__('summary_sha256','0'*64)),
      ('stale_gds',lambda p:p['report']['outputs'].__setitem__('parent/layout/nssoc_cdr_pd500_input_access_v58.gds','0'*64)),
      ('wrong_component_census',lambda p:p['report']['strict_wire_graph'].__setitem__('wire_component_count',123)),
      ('missing_serialized_material_control',lambda p:p['report']['candidate_delta']['serialization_integrity_controls'].pop()),
      ('missing_intrinsic_mim',lambda p:p['report']['device_locations']['devices'].remove(next(x for x in p['report']['device_locations']['devices']if x['model']=='cap_cmim'))),
      ('rounded_gain_mos',lambda p:next(x for x in p['report']['device_locations']['devices']if x['model']=='sg13_lv_nmos'and x['parameters']['W']==53.335)['parameters'].__setitem__('W',53.33)),
      ('nonzero_DRC',lambda p:p['report']['physical']['steps']['drc']['measurement'].__setitem__('markers',1)),
      ('failed_flat_LVS',lambda p:p['report']['physical']['steps']['lvs_flat']['audit'].__setitem__('circuit_status_counts',{'Mismatch':1})),
      ('missing_body_anchor',lambda p:p['report']['anchors']['dispositions'].__setitem__('RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE',492)),
      ('wrong_large_tap_area',lambda p:next(x for x in p['report']['device_locations']['devices']if x['model']=='ptap1'and x['parameters']['A']==40)['parameters'].__setitem__('A',39)),
    ]
    for name,change in changes:
        bad=copy.deepcopy(pin);change(bad)
        try:validate(bad)
        except AssertionError:controls.append(name)
        else:raise AssertionError('Accepted '+name)
    assert len(controls)==10
    return dict(status='PASS_FROZEN_PHYSICAL_V58_SOURCE_AND_TEN_CORRUPTIONS',controls=controls)
if __name__=='__main__':print(json.dumps(check(),indent=2))
