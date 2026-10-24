#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Two-device bridge terminal planes from actual native PCell pins and contacts."""
import copy,json,os,sys,hashlib
from collections import Counter
from pathlib import Path
TOP='nssoc_tx_final_clock_bridge_layout_v1'
PCELL_SHA='58d53384ef0bb92a4fa413d3c92e8dcbcb8f422c5205da9260129049f07f1d6b'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def generate(source=None,physical_source=None):
    import pya
    source=Path(source) if source is not None else OUT
    physical_source=Path(physical_source) if physical_source is not None else source/'source'
    gds=physical_source/'layout'/(TOP+'.gds');db=physical_source/'check/lvs_flat/result.lvsdb'
    layout=pya.Layout();layout.read(str(gds));top=layout.cell(TOP);assert top is not None
    native=pya.LayoutVsSchematic();native.read(str(db));c=native.netlist().circuit_by_name(TOP)
    devices={d.id():d for d in c.each_device()};assert len(devices)==2
    record=json.loads((physical_source/'layout/result.json').read_text())
    pcell=OUT/'rppd_code.py'
    source_pins=[v for k,v in record['inputs'].items() if k.endswith('/ihp/rppd_code.py')]
    assert source_pins==[PCELL_SHA] and sha(pcell)==PCELL_SHA
    assert Counter(d.device_class().name for d in devices.values())==Counter(rppd=1,ptap1=1)
    wire=pya.LayoutToNetlist();wire.read(str(source/'native01/wires.l2n'));geometry=json.loads((source/'native01/result.json').read_text())
    mapping={int(k):v for k,v in geometry['native_layer_mapping'].items()};owner={v['component']:v['native_cluster'] for v in geometry['wire_components']};assert len(owner)==3
    poly=pya.Region(top.begin_shapes_rec(layout.layer(5,0))).merged();contacts=pya.Region(top.begin_shapes_rec(layout.layer(6,0))).merged();metal1=pya.Region(top.begin_shapes_rec(layout.layer(8,0))).merged()
    body={('rppd','rppd_sub'),('ptap1','WELL')}
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
    record=json.loads((physical_source/'layout/result.json').read_text())
    for name,b in record['ports'].items():
        box=pya.DBox.from_s(b).to_itype(layout.dbu);pin=next(p for p in c.each_pin() if p.name()==name);net=c.net_for_pin(pin.id())
        a=witness(67,box.center(),net.cluster_id,'P_'+name);assert a['label']=='P_'+name;public.append(dict(name=name,reference_label=a['label']))
    assert len(rows)==5 and sum('reference_label'in r for r in rows)==3 and len(public)==3
    assert {a['wire_component'] for a in anchors}==set(owner),'Unanchored physical component'
    def verify(observed):
        assert len(observed)==5 and len({(r['device'],r['terminal']) for r in observed})==5,'Missing or duplicate terminal'
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
    for fault in ['missing_terminal','off_conductor','wrong_reference','body_as_wire','resistor_endpoint_planes_swapped','duplicate_terminal']:
        altered=copy.deepcopy(rows);r=next(r for r in altered if 'reference_label'in r)
        if fault=='missing_terminal':altered.pop()
        elif fault=='off_conductor':r['point_dbu']=[-100000,-100000]
        elif fault=='wrong_reference':r['reference_label']=next(a['label'] for a in anchors if a['native_cluster']!=r['native_cluster'])
        elif fault=='body_as_wire':next(r for r in altered if 'reference_label'not in r)['reference_label']=anchors[0]['label']
        elif fault=='duplicate_terminal':altered[-1]=copy.deepcopy(altered[0])
        else:
            c=next(r for r in altered if r['model']=='rppd'and r['terminal']=='rppd_1')
            b=next(r for r in altered if r['model']=='rppd'and r['terminal']=='rppd_2')
            assert c['native_cluster']!=b['native_cluster']and c['point_dbu']!=b['point_dbu']
            for k in ['reference_label','metal','point_dbu','wire_component']:c[k],b[k]=b[k],c[k]
        try:verify(altered)
        except AssertionError as error:faults.append(dict(fault=fault,rejected=True,reason=str(error)))
        else:raise AssertionError('Accepted terminal reference corruption '+fault)
    result=dict(status='PASS_ALL5_BRIDGE_TERMINALS_BOUND_WITH3_METAL2_BODY_AND_SIX_FAULTS_NOT_RC_ACCEPTANCE',rows=rows,anchors=anchors,public=public,negative_controls=faults,
        counts=dict(devices=2,terminals=5,metal_terminals=3,body_terminals=2,public_ports=3,unique_reference_planes=len(anchors),wire_components=3),
        inputs={str(p):sha(p) for p in [gds,db,source/'native01/wires.l2n',source/'native01/wires.gds',source/'native01/result.json',physical_source/'layout/result.json',pcell,Path(__file__).resolve()]},
        poly_diffusion_resistance_included=False,substrate_spreading_included=False,wire_rc_extracted=False,qualified_pex=False,serial_phy_complete=False)
    (OUT/'anchors.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'],result['counts'])
if __name__=='__main__':
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT=Path(sys.argv[1]);generate()
