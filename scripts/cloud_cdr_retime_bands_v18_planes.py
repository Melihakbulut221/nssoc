#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bind all physical PD484 interfaces to the unsimplified native LVS database.

This prepares whole-parent extraction. It does not reuse old XOR wire RC or
claim that metal capacitance, substrate impedance or closed-loop timing passed.
"""
import argparse,copy,json,os,re,subprocess
from collections import Counter
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-cdr-retime-bands-v18-planes'
TOP='nssoc_cdr_pd484_localbus_v12'

def native():
    import pya
    P=OUT/'parent';A=P/'layout';D=P/'physical/lvs_flat'
    record=json.loads((A/'result.json').read_text());plan=record['source_plan']
    from check_cdr_localbus_v12_parent_geometry import check
    parent_geometry=check(P)
    audit=json.loads((D/'audit.json').read_text())
    assert audit['status']=='PASS within comparison scope' and not audit['extraction_diagnostics']
    assert audit['circuit_status_counts']=={'Match':1}
    assert len(audit['circuits'])==1
    assert audit['circuits'][0]['layout_devices_recursive']==audit['circuits'][0]['schematic_devices_recursive']==484
    L=pya.Layout();L.read(str(A/(TOP+'.gds')));T=L.cell(TOP)
    assert T is not None and L.dbu==.001
    db=pya.LayoutVsSchematic();db.read(str(D/'result.lvsdb'))
    circuit=db.netlist().top_circuit();assert circuit.name==TOP and circuit.pin_count()==25
    census=Counter(d.device_class().name.lower() for d in circuit.each_device())
    assert dict(census)==record['primitive_census'],dict(census)
    assert sum(census.values())==484
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
    assert len(rows)==len(expected)==158
    def validate(candidate):
        assert len(candidate)==len(expected) and len({x['label']for x in candidate})==len(expected)
        assert {x['label']for x in candidate}==set(expected)
        groups={}
        for x in candidate:
            assert x['logical_net']==expected[x['label']]
            groups.setdefault(x['logical_net'],set()).add(x['native_cluster'])
        assert set(groups)==set(plan['nets']) and len(groups)==51
        assert all(len(v)==1for v in groups.values()),'Open logical net'
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
    assert len(terminals)==1394 and dict(census)==dict(npn13g2=116,sg13_lv_nmos=46,rppd=102,cap_cmim=11,ptap1=209)
    # Native reader observation is retained; this alone is not LEF signoff.
    F=pya.Layout();F.read(str(A/(TOP+'.lef')));cell=F.cell(TOP);assert cell is not None
    lef=dict(native_read_succeeded=True,bbox_um=str(cell.dbbox()),layers=[str(F.get_info(i))for i in F.layer_indices()],qualified=False)
    result=dict(status='PASS_PD484_NATIVE158_PLANES_51_NETS_19_FAULTS',parent_geometry=parent_geometry,anchors=rows,controls=faults,native_devices=dict(census),native_terminal_count=len(terminals),native_terminals=terminals,native_layer_mapping=mapping,lef_reader=lef,
        inputs={str(p):sha(p)for p in [Path(__file__),A/'result.json',A/(TOP+'.gds'),A/(TOP+'.lef'),D/'result.lvsdb',D/'audit.json']},qualified_pex=False,closed_loop=False,full_phy_accepted=False)
    assert len(faults)==19
    (OUT/'native-planes.json').write_text(json.dumps(result,indent=2)+'\n')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--native',action='store_true');args=parser.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    if args.native:native();return
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,qualified_pex=False,closed_loop=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        pin=json.loads((ROOT/'docs/evidence/cdr-retime-bands-v18-physical-pass-20261020.json').read_text())
        assert pin['run']==39379285294 and pin['source_head']=='6fae6cae4e8242e3436fe8873b5e42bed7e112be'
        assert pin['summary_sha256']=='9d7300c3965d2a9487882e1a569cf17c5328acc130bbf2dc0ee9c993e0c210d3'
        assert pin['parts_sha256']=='b58458f2193418c85cfb1ea89a1716749f5028b2b5ce58558524b1b097f1bdb3'
        selected=[n for n in pin['report']['outputs']if n.startswith(('layout/','physical/lvs_flat/','inputs/','children.json'))]
        prior,proof=reports.restore_report('cdr-retime-band-reorder',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'parent',selected)
        assert prior==pin['report'] and prior['sources_unchanged'] and prior['source_head']==pin['source_head']
        assert prior['status']=='PASS_PD484_V16_BAND_REORDER_PHYSICAL_REQUIRES_FRESH_FULL_RC_AND_ORIGINAL_LOADED_GATES'
        assert prior['physical']['status']=='PASS_NATIVE_PDK_CDR_PD484_DRC_LVS_AND_FAULT_CONTROLS'
        geometry=prior['geometry']
        assert geometry['source_gds_sha256']=='c920186862bde235868d3fa009fedcff868246750f0fa38874e3c6b42ba7255e'
        assert geometry['candidate_gds_sha256']=='27321a65507bccd81228e05933676158794b3c099186535fd4f9b892afacb37e'
        assert geometry['enumerated']==720 and geometry['candidate_target_span_um']<geometry['original_target_span_um']
        assert geometry['candidate_order']==['sd','bd','sb','sa','sc','ac','dfa','da','se','dfc','dc','s0','x','s1','y','vi']
        assert all(geometry[k]for k in ('original_child_hierarchy_preserved','all_parent_band_geometry_conserved',
            'all_original_v13_v14_v15_v16_local_overlays_preserved','exact_serialized_geometry_checked','reference_byte_identical'))
        assert len(geometry['controls'])==2
        assert prior['child_geometry']['status']=='PASS_ALL16_ACTUAL_PLACEMENTS_AND_EIGHT_NATIVE_LEAF_DRAWINGS'
        assert len(prior['child_geometry']['controls'])==3
        assert sha(OUT/'parent/layout'/(TOP+'.gds'))==geometry['candidate_gds_sha256']
        r['band_reorder_geometry']=geometry
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
        r['status']='PASS_RETIMED_PD484_NATIVE_PLANES_REQUIRES_FRESH_RC_AND_CLOSED_LOOP'
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
