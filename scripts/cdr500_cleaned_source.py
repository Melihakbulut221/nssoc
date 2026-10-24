#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Frozen clean-PD500 source contract shared by intrinsic binding and wire RC."""
import copy,hashlib,json
from collections import Counter
from decimal import Decimal
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PIN=ROOT/'docs/evidence/cdr500-floating-wire-cleanup-pass-20261024.json'
IDENTITY=dict(group='cdr500-floating-wire-cleanup',run=40076590920,source_head='2627eb651ebff31b96abac985d19e1bc9b76d6a8',summary_sha256='817bdcb956662d9f3384ddcd72e237a4b9afb77e2cae3703eb4c063b0def90a2',parts_sha256='ee011be772093b73ceaa45c735aaa2591eb9d321b4f35260c795c1df290839c6')
GDS='e6ab61471595cd3635c8e2ef3922a09d6b128db0a5338fd6106f3a8e4aefc2f3'
CENSUS=dict(npn13G2=124,sg13_lv_nmos=50,rppd=98,cap_cmim=7,ptap1=221)
METHODS={'probe01.py':'d0ff17e291afae70873724369a89304dfd845ace8a5b9ed438e478c05b9a3790','locate01.py':'610e440b4c234baa6cd887bba2dfecf9506fd073d2e013e68ba3b37200f08882','anchors01.py':'ac1306425f72b6d4e8688eca0350e0baac75727c244e45007d43b0722989fba7','dedup01.py':'58ec392e70a89e2b4b6175fbef01413e3417b1d5fb1389aabd6fa7b95b743544'}
def validate(pin,prior=None):
    assert all(pin[k]==v for k,v in IDENTITY.items())
    r=pin['report']if prior is None else prior
    assert r==pin['report'] and r['source_head']==IDENTITY['source_head'] and r['sources_unchanged']
    assert r['status']=='PASS_PD500_FLOATING_ROOT_CLEANUP_FULL_PHYSICAL_AND_UNCHANGED_STRICT_WIRES_REQUIRES_FRESH_RC'
    assert r['outputs']['parent/layout/nssoc_cdr_pd500_active_input_v57.gds']==GDS
    assert r['unchanged_wire_method_sha256']==METHODS
    cleanup=r['cleanup'];assert cleanup['removed_component_count']==10 and cleanup['removed_metal_area_dbu2']==285675500
    assert len(cleanup['controls'])==7 and all(x['rejected']for x in cleanup['controls'])
    for key in ('all_other_root_geometry_unchanged','all_child_and_intrinsic_drawings_unchanged','all_labels_and_instance_transforms_unchanged','serialized_geometry_exact','schematic_and_lef_bytes_unchanged'):assert cleanup[key]
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
    record=json.loads((ROOT/'scripts/cdr500-cleaned-extraction-methods.json').read_text())
    for name,value in record['protected'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==value,name
    return record

def check():
    methods();pin=json.loads(PIN.read_text());validate(pin);controls=[]
    changes=[('wrong_source_hash',lambda p:p.__setitem__('summary_sha256','0'*64)),('stale_gds',lambda p:p['report']['outputs'].__setitem__('parent/layout/nssoc_cdr_pd500_active_input_v57.gds','0'*64)),('wrong_component_census',lambda p:p['report']['strict_wire_graph'].__setitem__('wire_component_count',123)),('missing_cleanup_control',lambda p:p['report']['cleanup']['controls'].pop()),('missing_intrinsic_mim',lambda p:p['report']['device_locations']['devices'].remove(next(x for x in p['report']['device_locations']['devices']if x['model']=='cap_cmim'))),('rounded_gain_mos',lambda p:next(x for x in p['report']['device_locations']['devices']if x['model']=='sg13_lv_nmos'and x['parameters']['W']==53.335)['parameters'].__setitem__('W',53.33))]
    for name,change in changes:
        bad=copy.deepcopy(pin);change(bad)
        try:validate(bad)
        except AssertionError:controls.append(name)
        else:raise AssertionError('Accepted '+name)
    assert len(controls)==6
    return dict(status='PASS_FROZEN_CLEAN_PD500_SOURCE_AND_SIX_CORRUPTIONS',controls=controls)
if __name__=='__main__':print(json.dumps(check(),indent=2))
