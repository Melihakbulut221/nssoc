#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bind all physical PD500 interfaces to the unsimplified native LVS database.

This prepares whole-parent extraction. It does not reuse old XOR wire RC or
claim that metal capacitance, substrate impedance or closed-loop timing passed.
"""
import argparse,copy,json,os,re,subprocess
from collections import Counter
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-cdr-sampler-active-input-v57-planes'
TOP='nssoc_cdr_pd500_resistor_v59'

def native():
    import pya
    P=OUT/'parent';A=P/'layout';D=P/'physical/lvs_flat'
    record=json.loads((A/'result.json').read_text());plan=record['source_plan']
    from check_width_parent_geometry import check
    parent_geometry=check(P)
    audit=json.loads((D/'audit.json').read_text())
    assert audit['status']=='PASS within comparison scope' and not audit['extraction_diagnostics']
    assert audit['circuit_status_counts']=={'Match':1}
    assert len(audit['circuits'])==1
    assert audit['circuits'][0]['layout_devices_recursive']==audit['circuits'][0]['schematic_devices_recursive']==500
    L=pya.Layout();L.read(str(A/(TOP+'.gds')));T=L.cell(TOP)
    assert T is not None and L.dbu==.001
    db=pya.LayoutVsSchematic();db.read(str(D/'result.lvsdb'))
    circuit=db.netlist().top_circuit();assert circuit.name==TOP and circuit.pin_count()==25
    census=Counter(d.device_class().name.lower() for d in circuit.each_device())
    assert dict(census)==record['primitive_census'],dict(census)
    assert sum(census.values())==500
    layers={};mapping={}
    for metal in (67,134):
        full=pya.Region(T.begin_shapes_rec(L.layer(metal,0))).merged()
        candidates=[i for i in db.layer_indexes() if (db.layer_by_index(i)^full).is_empty()]
        assert len(candidates)==1,(metal,candidates)
        mapping[metal]=candidates[0];layers[metal]=db.layer_by_index(candidates[0])
    def point(raw):
        f=list(map(float,re.findall(r'-?\d+(?:\.\d+)?',raw)));assert len(f)==4
        return pya.DBox(*f).to_itype(L.dbu).center()
    rows=[]
    def bind(label,raw,metal,net):
        pt=point(raw);n=db.probe_net(layers[metal],pt);assert n is not None,(label,raw)
        rows.append(dict(label=label,point_dbu=[pt.x,pt.y],metal=metal,logical_net=net,native_cluster=n.cluster_id,native_name=n.name))
    expected={}
    for node in plan['nodes']:
        tag=node['tag'];place=record['placements'][tag]
        assert place['kind']==node['kind'] and set(place['ports'])==set(node['pins'])
        for pin,net in node['pins'].items():
            label='A_'+tag+'_'+pin;expected[label]=net
            bind(label,place['ports'][pin],plan['types'][node['kind']]['layer'],net)
    assert set(record['ports'])==set(plan['ports'])
    for port,raw in record['ports'].items():
        label='P_'+port;expected[label]=port;bind(label,raw,134,port)
    assert len(rows)==len(expected)==160
    def validate(candidate):
        assert len(candidate)==len(expected) and len({x['label']for x in candidate})==len(expected)
        assert {x['label']for x in candidate}==set(expected)
        groups={}
        for x in candidate:
            assert x['logical_net']==expected[x['label']]
            groups.setdefault(x['logical_net'],set()).add(x['native_cluster'])
        assert set(groups)==set(plan['nets']) and len(groups)==51
        assert all(len(v)==1 for v in groups.values()),'Open logical net'
        assert len(set.union(*groups.values()))==51,'Different logical nets shorted'
        public={p.name():circuit.net_for_pin(p.id()).cluster_id for p in circuit.each_pin()}
        assert set(public)==set(plan['ports'])
        for x in candidate:
            if x['label'].startswith('P_'):assert public[x['logical_net']]==x['native_cluster']
    validate(rows)
    faults=[]
    def reject(name,changed):
        try:validate(changed)
        except AssertionError:faults.append(dict(name=name,rejected=True))
        else:raise AssertionError('Accepted '+name)
    for node in plan['nodes']:
        pair=next((a,b)for a in node['pins']for b in node['pins']if node['pins'][a]!=node['pins'][b])
        changed=copy.deepcopy(rows);a=next(x for x in changed if x['label']=='A_'+node['tag']+'_'+pair[0]);b=next(x for x in changed if x['label']=='A_'+node['tag']+'_'+pair[1])
        a['native_cluster'],b['native_cluster']=b['native_cluster'],a['native_cluster']
        reject('swap_actual_clusters_'+node['tag'],changed)
    reject('missing_plane',rows[:-1]);reject('duplicate_plane',rows[:-1]+[rows[0]])
    changed=copy.deepcopy(rows);next(x for x in changed if x['label']=='P_sub')['native_cluster']=next(x for x in rows if x['label']=='P_avss')['native_cluster'];reject('short_sub_to_avss',changed)
    terminals=[]
    for device in circuit.each_device():
        dc=device.device_class()
        for terminal in dc.terminal_definitions():
            net=device.net_for_terminal(terminal.id());assert net is not None
            terminals.append(dict(device=device.id(),model=dc.name,terminal=terminal.name,native_cluster=net.cluster_id,native_name=net.name))
    assert len(terminals)==1446 and dict(census)==dict(npn13g2=124,sg13_lv_nmos=50,rppd=98,cap_cmim=7,ptap1=221)
    # Native reader observation is retained; this alone is not LEF signoff.
    F=pya.Layout();F.read(str(A/(TOP+'.lef')));cell=F.cell(TOP);assert cell is not None
    lef=dict(native_read_succeeded=True,bbox_um=str(cell.dbbox()),layers=[str(F.get_info(i))for i in F.layer_indices()],qualified=False)
    result=dict(status='PASS_PD500_NATIVE160_PLANES_51_NETS_19_FAULTS',parent_geometry=parent_geometry,anchors=rows,controls=faults,native_devices=dict(census),native_terminal_count=len(terminals),native_terminals=terminals,native_layer_mapping=mapping,lef_reader=lef,
        inputs={str(p):sha(p)for p in [Path(__file__),A/'result.json',A/(TOP+'.gds'),A/(TOP+'.lef'),D/'result.lvsdb',D/'audit.json']},qualified_pex=False,closed_loop=False,full_phy_accepted=False)
    assert len(faults)==19
    (OUT/'native-planes.json').write_text(json.dumps(result,indent=2)+'\n')

EXPECTED_PARENT = {'run': 40073349301, 'source_head': 'fcb5c0f19e8dfa2161361790f5bf505d898291b9', 'summary_sha256': 'ebd36ac051b0e3ea95c682e86688f4441456b6fc785dd7667dead89101e0f083', 'parts_sha256': 'd2ec0c34fdb57e786380961714f59230c8fed492169a7579f6939f9f61f1bf4e'}
EXPECTED_GDS = '681c9af79a502807a06eaf96c32f28b409303c02a4c66eb1ed04e162dc0a34fc'
def validate_parent_pin(pin,prior):
    assert all(pin[k]==v for k,v in EXPECTED_PARENT.items())
    assert prior==pin['report'] and prior['sources_unchanged'] and prior['source_head']==pin['source_head']
    assert prior['status']=='PASS_PD500_C_D_ACTIVE_INPUT_V57_PARENT_PHYSICAL_REQUIRES_FRESH_RC_AND_ORIGINAL_LOADED_GATES'
    assert prior['physical']['status']=='PASS_NATIVE_PDK_CDR_PD500_DRC_LVS_AND_FAULT_CONTROLS'
    geometry=prior['replacement']
    assert geometry['status']=='PASS_C_D_REPLACEMENT_WITH_TRACKED_M1_M4_RECONCILIATION_M3_SUPPLY_DETOUR_AND_M5_FILL'
    assert geometry['changed_sampler_tags']==['sc','sd'] and not geometry['parent_geometry_unchanged']
    delta=geometry['parent_geometry_changes'];assert delta==prior['layout']['active_input_parent_metal_delta']
    assert delta['status']=='TRACKED_C_D_M1_M4_RECONCILIATION_M3_SUPPLY_DETOUR_AND_SAME_COMPONENT_M5_FILL'
    assert len(delta['m1_strips'])==32 and len(delta['m3_reroutes'])==2 and len(delta['m5_patches'])==4
    assert all(v['connected_component_count_after']==1 and v['clearance_dbu']==600 and v['bridge_width_dbu']==1200 and v['no_new_leaf_m3_contact']and v['no_other_parent_m3_contact']and v['old_parent_native_net']=='avss'and v['unintended_new_leaf_net']=='sub'and all(q['all_original_contacts_preserved']for q in v['original_parent_via_contacts'].values())for v in delta['m3_reroutes'])
    assert all(v['translation_dbu']==[320000,0]and v['same_translated_native_metal_component']for v in delta['m1_strips'])
    assert all(v['touched_existing_m5_components']==1 and v['added_area_dbu2']>0 for v in delta['m5_patches'])
    assert delta['m5_component_count_before']==delta['m5_component_count_after']
    m4=delta['m4_enclosures'];assert len(m4)==48
    preserved=[v for v in m4 if v['preserved_v14_source_bypass']];removed=[v for v in m4 if not v['preserved_v14_source_bypass']]
    assert len(preserved)==32 and len(removed)==16
    assert all(v['action']=='PRESERVE_V14_SOURCE_BYPASS_METAL_AND_ALL_ROOT_VIAS'and v['root_owned_via_contacts']=={'49':3,'66':0}and v['after_polygons_dbu']==[v['before_polygon_dbu']]for v in preserved)
    assert all(v['action']=='REMOVE_OBSOLETE_V16_PARENT_WIDENING_OVERLAY'and v['root_owned_via_contacts']=={'49':0,'66':0}and v['after_polygons_dbu']==[]for v in removed)
    assert all(v['old_child_attachment_count']==1 and not v['old_piece_was_floating']and v['confined_to_replaced_child']and v['no_external_parent_m4_component']for v in m4)
    assert delta['drawing_only_supply_separation']['separate']and delta['drawing_only_supply_separation']['clusters']['avss']!=delta['drawing_only_supply_separation']['clusters']['sub']

    extra=delta['additional_widening_ring_removals'];assert len(extra)==16
    assert sum(v['metal']==30 for v in extra)==4 and sum(v['metal']==67 for v in extra)==12
    assert all(v['old_child_attachment_count']==1 and v['confined_to_replaced_child']and v['no_external_parent_component']and v['after_polygons_dbu']==[]and all(n==0 for n in v['root_owned_via_contacts'].values())for v in extra)
    assert delta['additional_widening_ring_summary']=={'30':{'removed_count':4,'removed_area_dbu2':35180000,'retired_prior_fill_area_dbu2':0,'root_owned_vias_unchanged':True},'67':{'removed_count':12,'removed_area_dbu2':913305000,'retired_prior_fill_area_dbu2':0,'root_owned_vias_unchanged':True}}
    assert delta['all_other_parent_layers_unchanged'] and delta['all_parent_labels_and_transforms_unchanged'] and delta['all_children_unchanged']
    assert geometry['all_parent_labels_and_transforms_unchanged'] and geometry['external_leaf_pins_unchanged']
    assert geometry['preserved_reference_devices']==368 and geometry['actual_lef_size_pins_and_all_seven_obstruction_planes_checked']
    assert geometry['controls']==['removed_parent_geometry','removed_parent_instance','added_parent_metal','replaced_A_or_B','old_lef_size','old_lef_obstructions','unmoved_old_m1_patch','unrepaired_old_m3_bridge','stale_old_m4_enclosures','missing_m5_fill']
    assert prior['child_geometry']['status']=='PASS_ALL16_ACTUAL_PLACEMENTS_AND_NINE_NATIVE_LEAF_DRAWINGS'
    assert len(prior['child_geometry']['controls'])==5 and len(prior['child_geometry']['actual_placements'])==16
    m=prior['layout'];assert m['primitive_census']==dict(npn13g2=124,sg13_lv_nmos=50,rppd=98,cap_cmim=7,ptap1=221)
    assert m['source_plan']['primitive_census']==m['primitive_census'] and m['source_plan']['expected_devices']==500
    assert all(m['placements'][tag]['kind']=='sampler_cd'for tag in ('sc','sd'))
    assert all(m['placements'][tag]['kind']=='sampler'for tag in ('sa','sb'))
    assert prior['outputs']['layout/nssoc_cdr_pd500_resistor_v59.gds']==EXPECTED_GDS
    assert prior['parent_source']['run']==39738683936 and prior['parent_source']['summary_sha256']=='946587a69d7843b31025493531a10f1bfad2454029fe91df703cb0967ea71ae1'
    assert prior['parent_source']['manifest_sha256']=='12dd772565fa034f923d7768908ce48f9137efccc365dea1ca8824bf8d47bfd4'
    assert prior['data_source']['run']==40060383240 and prior['data_source']['summary_sha256']=='7d2f8549a3dcc26788fb77ded7e805a2a06d11d56d1c52625ed368fe2358481d'
    assert prior['data_source']['manifest_sha256']=='6402b317c4dfc513dcb2cec2c6be618bc9e0eb5444ec67b1a150cd663f87fcf5'
    for kind in ('lvs','lvs_flat'):
        audit=prior['physical']['steps'][kind]['audit']
        assert audit['status']=='PASS within comparison scope' and audit['circuit_status_counts']=={'Match':1} and not audit['extraction_diagnostics']
        assert len(audit['circuits'])==1 and audit['circuits'][0]['layout_devices_recursive']==audit['circuits'][0]['schematic_devices_recursive']==500
    drc=prior['physical']['steps']['drc']['measurement']
    assert drc['status']=='PASS'and drc['markers']==0 and drc['category_count']==560
    assert all(v['status']=='REJECTED_EXPECTED_FAULT'for k,v in prior['physical']['steps'].items()if k not in ('drc','lvs','lvs_flat'))
    assert len(prior['physical']['steps'])==15
    return dict(replacement=geometry,strict_graph_status='REQUIRES_FRESH_NATIVE_GRAPH_ON_ACTUAL_PD500_GEOMETRY')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--native',action='store_true');args=parser.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    if args.native:native();return
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,qualified_pex=False,closed_loop=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        pin=json.loads((ROOT/'docs/evidence/cdr-sampler-active-input-v57-parent-physical-pass-20261024.json').read_text())
        validate_parent_pin(pin,pin['report'])
        selected=[n for n in pin['report']['outputs']if n.startswith(('layout/','physical/lvs_flat/','inputs/','children.json'))]
        prior,proof=reports.restore_report('cdr-sampler-active-input-v57-parent',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'parent',selected)
        geometry=validate_parent_pin(pin,prior)
        assert sha(OUT/'parent/layout'/(TOP+'.gds'))==EXPECTED_GDS
        r['retime_parent_geometry']=geometry
        r['physical_source']=proof
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        r['runtime_sha256']=sha(app);save()
        with (OUT/'native.log').open('w')as log:rc=subprocess.call([str(app),'python',str(Path(__file__).resolve()),'--native'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        r['native_returncode']=rc
        if rc:print((OUT/'native.log').read_text()[-16000:],flush=True)
        assert rc==0
        r['native_planes']=json.loads((OUT/'native-planes.json').read_text())
        assert all(sha(OUT/'parent'/n)==prior['outputs'][n]for n in selected)
        r['sources_unchanged']=True
        r['status']='PASS_RETIMED_PD500_NATIVE_PLANES_REQUIRES_FRESH_RC_AND_CLOSED_LOOP'
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
