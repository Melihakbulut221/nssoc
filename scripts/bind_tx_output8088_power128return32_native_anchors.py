#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fresh native8088 terminal planes; no guessed or ideal interface aliases."""
import copy,json,os
from pathlib import Path
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-tx-output8088-power128return32-native-anchors'
TOP='nssoc_tx_output8088_parent_v1'
def generate(source=None,physical_source=None):
    import pya
    source=Path(source) if source is not None else OUT/'source'
    physical_source=Path(physical_source) if physical_source is not None else source/'source'
    gds=physical_source/'layout/layout.gds';db=physical_source/'flat_lvs/result.lvsdb'
    layout=pya.Layout();layout.read(str(gds));top=layout.cell(TOP);assert top is not None
    native=pya.LayoutVsSchematic();native.read(str(db));c=native.netlist().circuit_by_name(TOP)
    devices={d.id():d for d in c.each_device()};assert len(devices)==8088
    wire=pya.LayoutToNetlist();wire.read(str(source/'native01/wires.l2n'));geometry=json.loads((source/'native01/result.json').read_text())
    mapping={int(k):v for k,v in geometry['native_layer_mapping'].items()};owner={v['component']:v['native_cluster'] for v in geometry['wire_components']};assert len(owner)==703
    poly=pya.Region(top.begin_shapes_rec(layout.layer(5,0))).merged();contacts=pya.Region(top.begin_shapes_rec(layout.layer(6,0))).merged();metal1=pya.Region(top.begin_shapes_rec(layout.layer(8,0))).merged()
    body={('npn13G2','S'),('sg13_hv_nmos','B'),('sg13_lv_nmos','B'),('sg13_lv_pmos','B'),('rppd','rppd_sub'),('rsil','rsil_sub'),('ptap1','WELL'),('ntap1','WELL')}
    # Walk real GDS hierarchy for resistor pin witnesses; never infer an
    # access point from an invented transistor model or reference label.
    resistor_instances=[];hbt_instances=[];output_hbt_instances=[]
    def walk(cell,tr,in_output=False):
        name=cell.name.split('$')[0].lower()
        in_output=in_output or name=='actual_output14'
        if name in ('rppd','rsil'):
            resistor_instances.append((cell,tr));return
        if name=='npn13g2':
            hbt_instances.append((cell,tr))
            if in_output:output_hbt_instances.append((cell,tr))
            return
        for inst in cell.each_inst():
            for i in range(max(1,inst.na)):
                for j in range(max(1,inst.nb)):
                    offset=pya.Trans(i*inst.a.x+j*inst.b.x,i*inst.a.y+j*inst.b.y)
                    walk(inst.cell,tr*offset*inst.trans,in_output)
    walk(top,pya.Trans())
    assert len(resistor_instances)==506 and len(hbt_instances)==593
    assert len(output_hbt_instances)==4
    pcell=OUT/'npn13G2_code.py'
    record=json.loads((OUT/'output_leaf_proof/layout/result.json').read_text())
    pcell_sha='634cda63717ab4122f15e0fef5f3e8475e90e67e043823f5b8ed208e695f1729'
    assert sha(pcell)==pcell_sha
    assert [v for k,v in record['input_sha256'].items()if k.endswith('/ihp/npn13G2_code.py')]==[pcell_sha]
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
    # Visit HBTs first so an HBT access failure does not wait for all MOS probes.
    # The census and every geometry/native ownership predicate remain unchanged.
    for did,d in sorted(devices.items(),key=lambda item:(item[1].device_class().name!='npn13G2',item[0])):
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
            if not candidates and cls.name=='npn13G2':
                # Native HBT terminal polygons can already be Metal1 access
                # planes rather than contact cuts. Intersect actual material,
                # then independently probe both conductor databases below.
                access=(region&metal1).merged()
                for polygon in access.decompose_trapezoids_to_region().each():
                    box=polygon.bbox()
                    if polygon.area()!=box.area()or box.width()<2 or box.height()<2:continue
                    point=box.center();nn=native.probe_net(native.layer_by_index(mapping[8]),point)
                    if nn is not None and nn.cluster_id==net.cluster_id:candidates.append((8,point,'native_hbt_terminal_metal_intersection'))
            if not candidates and cls.name=='npn13G2':
                # Native extractor terminal polygons need not include the full
                # PCell collector access. Find the actual unique PCell enclosing
                # all three native C/B/E terminal regions, then probe its actual
                # metal pin rectangles. No inferred nominal pin coordinates.
                bounds=pya.Box()
                for term in cls.terminal_definitions():
                    if term.name=='S':continue
                    for r in native.shapes_of_terminal(d.terminal_ref(term.id())).values():bounds+=r.bbox()
                instances=[(cell,tr)for cell,tr in hbt_instances if (cell.bbox().transformed(tr)&bounds)==bounds]
                assert len(instances)==1,('HBT physical enclosure',did,len(instances),str(bounds))
                cell,tr=instances[0]
                for metal in (8,10):
                    for shape in cell.each_shape(layout.layer(metal,2)):
                        if not shape.is_box():continue
                        box=shape.box.transformed(tr);point=box.center()
                        nn=native.probe_net(native.layer_by_index(mapping[metal]),point)
                        wn=wire.probe_net(wire.layer_by_name('gds_'+str(metal)),point)
                        if nn is not None and nn.cluster_id==net.cluster_id and wn is not None and owner[wn.cluster_id]==net.cluster_id:
                            candidates.append((metal,point,'original_hbt_pin_dual_native_probe'))
            if not candidates and cls.name in ('rppd','rsil'):
                # Original PCell port rectangles are an independent resistor access witness.
                bounds=pya.Box()
                for term in cls.terminal_definitions():
                    if term.name in ('rppd_sub','rsil_sub'):continue
                    for r in native.shapes_of_terminal(d.terminal_ref(term.id())).values():bounds+=r.bbox()
                instances=[(cell,tr)for cell,tr in resistor_instances if cell.name.split('$')[0].lower()==cls.name and (cell.bbox().transformed(tr)&bounds)==bounds]
                assert len(instances)==1,('Resistor physical enclosure',did,len(instances))
                cell,tr=instances[0]
                for shape in cell.each_shape(layout.layer(8,2)):
                    if not shape.is_box():continue
                    box=shape.box.transformed(tr);point=box.center()
                    nn=native.probe_net(native.layer_by_index(mapping[8]),point)
                    if nn is not None and nn.cluster_id==net.cluster_id and (pya.Region(box)-metal1).is_empty():candidates.append((8,point,'original_resistor_pin'))
            if cls.name=='npn13G2':
                bounds=pya.Box()
                for term in cls.terminal_definitions():
                    if term.name=='S':continue
                    for rr in native.shapes_of_terminal(d.terminal_ref(term.id())).values():bounds+=rr.bbox()
                output_instances=[(cell,tr)for cell,tr in output_hbt_instances if(cell.bbox().transformed(tr)&bounds)==bounds]
                if output_instances:
                    assert len(output_instances)==1 and d.parameter('Nx')in(1,8)
                    cell,tr=output_instances[0]
                    assert tr.angle==0 and not tr.is_mirror()
                    pins={m:[shape.box for shape in cell.each_shape(layout.layer(m,2))if shape.is_box()]for m in(8,10)}
                    assert len(pins[8])==2 and len(pins[10])==1
                    base,collector=sorted(pins[8],key=lambda box:box.center().y)
                    assert base.center().y<collector.center().y
                    m,local={'C':(8,collector),'B':(8,base),'E':(10,pins[10][0])}[td.name]
                    box=local.transformed(tr);point=box.center()
                    conductor=pya.Region(top.begin_shapes_rec(layout.layer(m,0))).merged()
                    assert(pya.Region(box)-conductor).is_empty()
                    nn=native.probe_net(native.layer_by_index(mapping[m]),point)
                    assert nn is not None and nn.cluster_id==net.cluster_id
                    # Override all same-net generic candidates with the actual
                    # pinned PCell terminal plane, preserving REF C/B separation.
                    candidates=[(m,point,'pinned_native_output_hbt_'+td.name+'_pin')]
            assert candidates,('No physical terminal contact',did,cls.name,td.name,str(region.bbox()))
            unique={(m,p.x,p.y):(m,p,kind) for m,p,kind in candidates};candidates=list(unique.values())
            allowed[key]=set(unique)
            center=region.bbox().center();m,point,kind=min(candidates,key=lambda v:((v[1].x-center.x)**2+(v[1].y-center.y)**2,v[1].x,v[1].y))
            a=witness(m,point,net.cluster_id)
            row.update(disposition='ACTUAL_TERMINAL_METAL_REFERENCE_WITH_UNMODELED_DEVICE_ACCESS_R',reference_label=a['label'],metal=m,point_dbu=a['point_dbu'],wire_component=a['wire_component'],selection=kind,
                candidate_contacts=[dict(metal=m,point_dbu=[p.x,p.y],kind=k) for m,p,k in candidates])
            rows.append(row)
    public=[]
    parent_ports={}
    for metal in (67,134):
        boxes=[s.box for s in top.each_shape(layout.layer(metal,2))if s.is_box()]
        for s in top.each_shape(layout.layer(metal,25)):
            if not s.is_text():continue
            name=s.text.string;matches=[b for b in boxes if b.contains(s.text.trans.disp)]
            assert len(matches)==1 and name not in parent_ports
            parent_ports[name]=(metal,matches[0])
    assert len(parent_ports)==165 and set(parent_ports)=={p.name()for p in c.each_pin()}
    for name,(metal,box)in sorted(parent_ports.items()):
        pin=next(p for p in c.each_pin()if p.name()==name);net=c.net_for_pin(pin.id())
        a=witness(metal,box.center(),net.cluster_id,'P_'+name);assert a['label']=='P_'+name;public.append(dict(name=name,reference_label=a['label']))
    assert len(rows)==28620 and sum('reference_label'in r for r in rows)==20532 and len(public)==165
    assert {a['wire_component'] for a in anchors}==set(owner),'Unanchored physical component'
    anchor_by_label={a["label"]:a for a in anchors};assert len(anchor_by_label)==len(anchors)
    def verify(observed):
        assert len(observed)==28620 and len({(r['device'],r['terminal']) for r in observed})==28620,'Missing or duplicate terminal'
        for row in observed:
            d=devices[row['device']];cls=d.device_class();td=next(t for t in cls.terminal_definitions()if t.name==row['terminal']);net=d.net_for_terminal(td.id())
            assert row['native_cluster']==net.cluster_id and row['model']==cls.name,'Native device terminal identity changed'
            if(cls.name,td.name)in body:
                assert 'reference_label'not in row and row['disposition']=='RETAINED_FINITE_CONTACT_COMMON_BODY_NO_SPREADING_R';continue
            x,y=row['point_dbu'];assert (row['metal'],x,y)in allowed[(row['device'],row['terminal'])],'Point is not an actual contact for this terminal'
            a=anchor_by_label[row['reference_label']]
            assert a['metal']==row['metal'] and a['point_dbu']==row['point_dbu'] and a['native_cluster']==net.cluster_id,'Anchor association changed'
            wn=wire.probe_net(wire.layer_by_name('gds_'+str(row['metal'])),pya.Point(x,y));assert wn is not None and owner[wn.cluster_id]==net.cluster_id
    verify(rows);faults=[]
    for fault in ['missing_terminal','off_conductor','wrong_reference','body_as_wire','output_hbt_collector_base_planes_swapped','duplicate_terminal']:
        altered=copy.deepcopy(rows);r=next(r for r in altered if 'reference_label'in r)
        if fault=='missing_terminal':altered.pop()
        elif fault=='off_conductor':r['point_dbu']=[-100000,-100000]
        elif fault=='wrong_reference':r['reference_label']=next(a['label'] for a in anchors if a['native_cluster']!=r['native_cluster'])
        elif fault=='body_as_wire':next(r for r in altered if 'reference_label'not in r)['reference_label']=anchors[0]['label']
        elif fault=='duplicate_terminal':altered[-1]=copy.deepcopy(altered[0])
        else:
            paired=[]
            for did in devices:
                rs=[r for r in altered if r['device']==did and r.get('selection','').startswith('pinned_native_output_hbt_')]
                if not rs:continue
                cc=next(r for r in rs if r['terminal']=='C');bb=next(r for r in rs if r['terminal']=='B')
                if cc['native_cluster']==bb['native_cluster']:paired.append((cc,bb))
            assert len(paired)==1
            cc,bb=paired[0];assert cc['point_dbu']!=bb['point_dbu']
            for k in ['reference_label','metal','point_dbu','wire_component']:cc[k],bb[k]=bb[k],cc[k]
        try:verify(altered)
        except AssertionError as error:faults.append(dict(fault=fault,rejected=True,reason=str(error)))
        else:raise AssertionError('Accepted terminal reference corruption '+fault)
    result=dict(status='PASS_ALL28620_FULL_PARENT_TERMINALS_WITH20532_METAL8088_BODY_AND_SIX_FAULTS_NOT_RC_ACCEPTANCE',rows=rows,anchors=anchors,public=public,negative_controls=faults,
        counts=dict(devices=8088,terminals=28620,metal_terminals=20532,body_terminals=8088,public_ports=165,unique_reference_planes=len(anchors),wire_components=703),
        inputs={str(p):sha(p) for p in [gds,db,source/'native01/wires.l2n',source/'native01/wires.gds',source/'native01/result.json',pcell,OUT/'output_leaf_proof/layout/result.json',Path(__file__).resolve()]},
        poly_diffusion_resistance_included=False,substrate_spreading_included=False,wire_rc_extracted=False,qualified_pex=False,serial_phy_complete=False)
    (OUT/'anchors.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'],result['counts'])
if __name__=='__main__':
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    generate()
