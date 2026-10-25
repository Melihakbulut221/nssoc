#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bind all physical PD476 interfaces to the unsimplified native LVS database.

This prepares whole-parent extraction. It does not reuse old XOR wire RC or
claim that metal capacitance, substrate impedance or closed-loop timing passed.
"""
import argparse,copy,json,os,re,subprocess
from collections import Counter
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-cdr-input-access-v26-planes'
TOP='nssoc_cdr_pd476_follower_v23'

def native():
    import pya
    P=OUT/'parent';A=P/'layout';D=P/'physical/lvs_flat'
    record=json.loads((A/'result.json').read_text());plan=record['source_plan']
    from check_cdr_follower_v23_parent_geometry import check
    parent_geometry=check(P)
    audit=json.loads((D/'audit.json').read_text())
    assert audit['status']=='PASS within comparison scope' and not audit['extraction_diagnostics']
    assert audit['circuit_status_counts']=={'Match':1}
    assert len(audit['circuits'])==1
    assert audit['circuits'][0]['layout_devices_recursive']==audit['circuits'][0]['schematic_devices_recursive']==476
    L=pya.Layout();L.read(str(A/(TOP+'.gds')));T=L.cell(TOP)
    assert T is not None and L.dbu==.001
    db=pya.LayoutVsSchematic();db.read(str(D/'result.lvsdb'))
    circuit=db.netlist().top_circuit();assert circuit.name==TOP and circuit.pin_count()==25
    census=Counter(d.device_class().name.lower() for d in circuit.each_device())
    assert dict(census)==record['primitive_census'],dict(census)
    assert sum(census.values())==476
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
    assert len(terminals)==1382 and dict(census)==dict(npn13g2=120,sg13_lv_nmos=46,rppd=98,cap_cmim=7,ptap1=205)
    # Native reader observation is retained; this alone is not LEF signoff.
    F=pya.Layout();F.read(str(A/(TOP+'.lef')));cell=F.cell(TOP);assert cell is not None
    lef=dict(native_read_succeeded=True,bbox_um=str(cell.dbbox()),layers=[str(F.get_info(i))for i in F.layer_indices()],qualified=False)
    result=dict(status='PASS_PD476_NATIVE160_PLANES_51_NETS_19_FAULTS',parent_geometry=parent_geometry,anchors=rows,controls=faults,native_devices=dict(census),native_terminal_count=len(terminals),native_terminals=terminals,native_layer_mapping=mapping,lef_reader=lef,
        inputs={str(p):sha(p)for p in [Path(__file__),A/'result.json',A/(TOP+'.gds'),A/(TOP+'.lef'),D/'result.lvsdb',D/'audit.json']},qualified_pex=False,closed_loop=False,full_phy_accepted=False)
    assert len(faults)==19
    (OUT/'native-planes.json').write_text(json.dumps(result,indent=2)+'\n')

def validate_parent_pin(pin,prior):
    assert pin['run']==39531419538 and pin['source_head']=='0803c9e3d3e18521b4ca3765180180473e05c9a8'
    assert pin['summary_sha256']=='9182d81d1edd700aa7a5884b2f29f4611e254c298ad278fa8fc6898ee77c6856'
    assert pin['parts_sha256']=='91761e2afbd8cdaf6d481415db08b83cdce63b39b205af8022fc1d3c6c5e09b7'
    assert prior==pin['report'] and prior['sources_unchanged'] and prior['source_head']==pin['source_head']
    assert prior['status']=='PASS_PD476_V26_CLEAN_PARENT_PHYSICAL_AND_STRICT111_COMPONENT_GRAPH_REQUIRES_FRESH_RC'
    assert prior['physical']['status']=='PASS_NATIVE_PDK_CDR_PD476_DRC_LVS_AND_FAULT_CONTROLS'
    geometry=prior['intrinsic_replacement_history']
    assert geometry['status']=='PASS_SERIALIZED_UNCHANGED_PARENT_WITH_FOUR_NATIVE_INPUT_ACCESS_V26_SAMPLERS'
    assert geometry['actual_sampler_instances']==4
    expected_changed={f'Rs{sampler}_{leg}' for sampler in 'abcd' for leg in ('IP','IN')}
    assert len(geometry['changed_reference_devices'])==8 and set(geometry['changed_reference_devices'])==expected_changed
    assert geometry['parent_geometry_unchanged'] and geometry['all_existing_collector_retime_trunks_retained']
    assert geometry['external_leaf_ports_and_bbox_unchanged'] and geometry['serialized_native_check']
    assert len(geometry['controls'])==2
    assert prior['parent_source']['summary_sha256']=='44361f37b6558c13937c127027e911cd6136d60a96ede44c061d7e0da52c0dae'
    assert prior['child_geometry']['status']=='PASS_ALL16_ACTUAL_PLACEMENTS_AND_EIGHT_NATIVE_LEAF_DRAWINGS'
    assert len(prior['child_geometry']['controls'])==3
    assert prior['outputs']['layout/nssoc_cdr_pd476_follower_v23.gds']=='c6be489346bba16ce781ff09a919618dbaf9fee17a85714149400b70b3445458'
    cleanup=prior['cleanup']
    assert cleanup['status']=='PASS_EXACT_EIGHT_NATIVE_TERMINAL_FREE_PARENT_COMPONENTS_REMOVED'
    assert cleanup['before_gds_sha256']=='4a0567c696b994f087440b17a41162e760c70dd6495d3f9317e416496ce5ca51'
    assert cleanup['after_gds_sha256']==prior['outputs']['layout/nssoc_cdr_pd476_follower_v23.gds']
    assert cleanup['removed_components']==8 and len(cleanup['clusters'])==8
    assert cleanup['removed_area_dbu2']=={'30':23180000,'67':9540000}
    assert cleanup['only_parent_metal_changed'] and cleanup['all_child_geometry_unchanged']
    assert cleanup['all_16_parent_instances_unchanged'] and cleanup['schematic_and_lef_unchanged']
    assert cleanup['original_terminal_and_port_count']==[1382,25] and len(cleanup['controls'])==4
    graph=prior['strict_graph']
    assert graph['status']=='PASS_GEOMETRIC_PUMP_WIRE_COMPONENT_BINDING_NO_RC'
    assert graph['native_device_count']==476 and graph['native_terminal_count']==1382 and graph['wire_component_count']==111
    assert graph['no_wire_geometry_change'] and graph['no_component_union_by_native_label']
    assert prior['graph_source_delta']['only_parent_input_paths_changed']
    return dict(intrinsic_replacement_history=geometry,actual_parent_cleanup=cleanup,strict_graph_status=graph['status'])

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--native',action='store_true');args=parser.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    if args.native:native();return
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,qualified_pex=False,closed_loop=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        pin=json.loads((ROOT/'docs/evidence/cdr-input-access-v26-clean-parent-pass-20261021.json').read_text())
        validate_parent_pin(pin,pin['report'])
        selected=[n for n in pin['report']['outputs']if n.startswith(('layout/','physical/lvs_flat/','inputs/','children.json'))]
        prior,proof=reports.restore_report('cdr-input-access-v26-clean-parent',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'parent',selected)
        geometry=validate_parent_pin(pin,prior)
        assert sha(OUT/'parent/layout'/(TOP+'.gds'))=='c6be489346bba16ce781ff09a919618dbaf9fee17a85714149400b70b3445458'
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
        r['status']='PASS_RETIMED_PD476_NATIVE_PLANES_REQUIRES_FRESH_RC_AND_CLOSED_LOOP'
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
