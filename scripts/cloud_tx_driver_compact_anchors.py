#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual terminal contact planes for all100 raw full-driver devices."""
import argparse,copy,json,os,sys
from collections import Counter
from pathlib import Path
import cloud_tx_input_driver_compact as physical
from run_cloud_tx_layout_repair import sha
ROOT=physical.ROOT;OUT=ROOT/'hw/soc/out/cloud-tx-driver-compact-anchors'
SOURCE={'run': 38890304004, 'group': 'tx-driver-compact-wires', 'root': 'cloud-tx-driver-compact-wires', 'bytes': 1330456, 'sha': '49c68a7e544ff51eecbf1fd5acc437808fd2695e82104ec9bb7227441aaeaf76', 'summary': '6c1b9f8c2afc94ef49a0f5ae4783268dc20745b6c08ba878a5fa94325663b431'}
def generate():
    import pya
    source=OUT/'inputs/tx-driver-compact-wires/cloud-tx-driver-compact-wires';physical_source=source/'inputs/tx-input-driver-compact/cloud-tx-input-driver-compact'
    gds=physical_source/'base/layout.gds';db=physical_source/'check-raw_flat_lvs/result.lvsdb'
    layout=pya.Layout();layout.read(str(gds));top=layout.cell(physical.TOP);assert top is not None
    native=pya.LayoutVsSchematic();native.read(str(db));c=native.netlist().circuit_by_name(physical.TOP)
    devices={d.id():d for d in c.each_device()};assert len(devices)==100
    wire=pya.LayoutToNetlist();wire.read(str(source/'native01/wires.l2n'));geometry=json.loads((source/'native01/result.json').read_text())
    mapping={int(k):v for k,v in geometry['native_layer_mapping'].items()};owner={v['component']:v['native_cluster'] for v in geometry['wire_components']};assert len(owner)==10
    poly=pya.Region(top.begin_shapes_rec(layout.layer(5,0))).merged();contacts=pya.Region(top.begin_shapes_rec(layout.layer(6,0))).merged();metal1=pya.Region(top.begin_shapes_rec(layout.layer(8,0))).merged()
    body={('sg13_hv_nmos','B'),('sg13_lv_nmos','B'),('sg13_lv_pmos','B'),('rppd','rppd_sub'),('ptap1','WELL'),('ntap1','WELL')}
    rows=[];anchors=[];by_point={};allowed={}
    def witness(m,point,expected,label=None):
        wn=wire.probe_net(wire.layer_by_name('gds_'+str(m)),point)
        nn=native.probe_net(native.layer_by_index(mapping[m]),point)
        assert wn is not None and nn is not None and nn.cluster_id==expected and owner[wn.cluster_id]==expected,'Reference point on wrong or missing conductor'
        key=(m,point.x,point.y)
        if key in by_point:
            a=by_point[key];assert a['native_cluster']==expected;return a
        a=dict(label=label or 'A'+str(len(anchors)).zfill(4),metal=m,point_dbu=[point.x,point.y],wire_component=wn.cluster_id,native_cluster=expected)
        by_point[key]=a;anchors.append(a);return a
    for did,d in devices.items():
        cls=d.device_class()
        for td in cls.terminal_definitions():
            net=d.net_for_terminal(td.id());key=(did,td.name)
            row=dict(device=did,model=cls.name,terminal=td.name,native_cluster=net.cluster_id)
            if(cls.name,td.name)in body:
                row['disposition']='RETAINED_FINITE_CONTACT_COMMON_BODY_NO_SPREADING_R';rows.append(row);continue
            shapes=native.shapes_of_terminal(d.terminal_ref(td.id()));region=pya.Region()
            for r in shapes.values():region+=r
            region=region.merged();assert not region.is_empty()
            conductor=poly.interacting(region).merged() if td.name=='G' else region
            candidate_regions=contacts.inside(conductor)
            candidates=[]
            for contact in candidate_regions.each():
                box=contact.bbox()
                if contact.area()!=box.area() or not(pya.Region(contact)-metal1).is_empty():continue
                point=box.center();nn=native.probe_net(native.layer_by_index(mapping[8]),point)
                if nn is not None and nn.cluster_id==net.cluster_id:candidates.append((8,point,'native_terminal_contact'))
            if not candidates and cls.name=='rppd':
                # Original PCell port rectangles are an independent resistor access witness.
                bounds=pya.Box()
                for term in cls.terminal_definitions():
                    if term.name=='rppd_sub':continue
                    for r in native.shapes_of_terminal(d.terminal_ref(term.id())).values():bounds+=r.bbox()
                instances=[i for i in top.each_inst() if i.cell.name.split('$')[0]=='rppd' and (i.cell.bbox().transformed(i.trans)&bounds)==bounds]
                assert len(instances)==1,('Resistor physical enclosure',did,len(instances))
                inst=instances[0]
                for shape in inst.cell.each_shape(layout.layer(8,2)):
                    if not shape.is_box():continue
                    box=shape.box.transformed(inst.trans);point=box.center()
                    nn=native.probe_net(native.layer_by_index(mapping[8]),point)
                    if nn is not None and nn.cluster_id==net.cluster_id and (pya.Region(box)-metal1).is_empty():candidates.append((8,point,'original_resistor_pin'))
            assert candidates,('No physical terminal contact',did,cls.name,td.name,str(region.bbox()))
            unique={(m,p.x,p.y):(m,p,kind) for m,p,kind in candidates};candidates=list(unique.values())
            allowed[key]=set(unique)
            center=region.bbox().center();m,point,kind=min(candidates,key=lambda v:((v[1].x-center.x)**2+(v[1].y-center.y)**2,v[1].x,v[1].y))
            a=witness(m,point,net.cluster_id)
            row.update(disposition='ACTUAL_CONTACT_REFERENCE_WITH_UNMODELED_POLY_DIFFUSION_R',reference_label=a['label'],metal=m,point_dbu=a['point_dbu'],wire_component=a['wire_component'],selection=kind,
                candidate_contacts=[dict(metal=m,point_dbu=[p.x,p.y],kind=k) for m,p,k in candidates])
            rows.append(row)
    public=[]
    record=json.loads((physical_source/'base/result.json').read_text())
    for name,b in record['ports'].items():
        box=pya.DBox.from_s(b).to_itype(layout.dbu);pin=next(p for p in c.each_pin() if p.name()==name);net=c.net_for_pin(pin.id())
        a=witness(67,box.center(),net.cluster_id,'P_'+name);assert a['label']=='P_'+name;public.append(dict(name=name,reference_label=a['label']))
    assert len(rows)==372 and sum('reference_label'in r for r in rows)==272 and len(public)==6
    assert {a['wire_component'] for a in anchors}==set(owner),'Unanchored physical component'
    def verify(observed):
        assert len(observed)==372 and len({(r['device'],r['terminal']) for r in observed})==372,'Missing or duplicate terminal'
        for row in observed:
            d=devices[row['device']];cls=d.device_class();td=next(t for t in cls.terminal_definitions()if t.name==row['terminal']);net=d.net_for_terminal(td.id())
            assert row['native_cluster']==net.cluster_id and row['model']==cls.name,'Native device terminal identity changed'
            if(cls.name,td.name)in body:
                assert 'reference_label'not in row and row['disposition']=='RETAINED_FINITE_CONTACT_COMMON_BODY_NO_SPREADING_R';continue
            x,y=row['point_dbu'];assert (row['metal'],x,y)in allowed[(row['device'],row['terminal'])],'Point is not an actual contact for this terminal'
            a=next(a for a in anchors if a['label']==row['reference_label'])
            assert a['metal']==row['metal'] and a['point_dbu']==row['point_dbu'] and a['native_cluster']==net.cluster_id,'Anchor association changed'
            wn=wire.probe_net(wire.layer_by_name('gds_'+str(row['metal'])),pya.Point(x,y));assert wn is not None and owner[wn.cluster_id]==net.cluster_id
    verify(rows);faults=[]
    for fault in ['missing_terminal','off_conductor','wrong_reference','body_as_wire']:
        altered=copy.deepcopy(rows);r=next(r for r in altered if 'reference_label'in r)
        if fault=='missing_terminal':altered.pop()
        elif fault=='off_conductor':r['point_dbu']=[-100000,-100000]
        elif fault=='wrong_reference':r['reference_label']=next(a['label'] for a in anchors if a['native_cluster']!=r['native_cluster'])
        else:next(r for r in altered if 'reference_label'not in r)['reference_label']=anchors[0]['label']
        try:verify(altered)
        except AssertionError as error:faults.append(dict(fault=fault,rejected=True,reason=str(error)))
        else:raise AssertionError('Accepted terminal reference corruption '+fault)
    result=dict(status='PASS_ALL372_DRIVER_TERMINALS_BOUND_WITH272_METAL100_BODY_AND_FOUR_FAULTS_NOT_RC_ACCEPTANCE',rows=rows,anchors=anchors,public=public,negative_controls=faults,
        counts=dict(devices=100,terminals=372,metal_terminals=272,body_terminals=100,public_ports=6,unique_reference_planes=len(anchors),wire_components=10),
        inputs={str(p):sha(p) for p in [gds,db,source/'native01/wires.l2n',source/'native01/wires.gds',source/'native01/result.json',physical_source/'base/result.json',Path(__file__).resolve()]},
        poly_diffusion_resistance_included=False,substrate_spreading_included=False,wire_rc_extracted=False,qualified_pex=False,serial_phy_complete=False)
    (OUT/'anchors.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'],result['counts'])
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--generate',action='store_true');args=parser.parse_args();assert os.environ.get('GITHUB_ACTIONS')=='true'
    if args.generate:generate();return
    OUT.mkdir(parents=True,exist_ok=False)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],source=SOURCE,qualified_pex=False,serial_phy_complete=False,qualified_timing=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        physical.OUT=OUT;source,prior=physical.restore(SOURCE)
        assert prior['status']=='PASS_FULL_DRIVER_METAL_VIA_GRAPH_BOUND_TO_ALL100_NATIVE_DEVICES_NO_RC'
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        sys.path.insert(0,str(ROOT/'hw/soc/flow'));from check_pcie_rx_cell import execute
        r['execution']=execute([app,'python',Path(__file__).resolve(),'--generate'],OUT,'generate');save()
        if r['execution']['returncode']:
            print((OUT/'generate.log').read_text(errors='replace')[-12000:]);raise RuntimeError('Driver terminal reference binding failed')
        r['binding']=json.loads((OUT/'anchors.json').read_text());r['status']=r['binding']['status']
        assert all(sha(source/p)==v for p,v in prior['outputs'].items())
    except BaseException as error:r.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
