#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Add native midpoint MOS-source contacts without moving any original geometry."""
import argparse,json,re,sys
from pathlib import Path
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
TOP='nssoc_cdr_pd484_localbus_v12'
ALLOWED={(8,0),(10,0),(19,0),(29,0),(30,0),(49,0),(50,0)}
def generate(out):
    source=ROOT/'pdk/libs.tech/klayout/python'
    sys.path[:0]=[str(source),str(source/'pycell4klayout-api/source/python')]
    import pya
    import sg13g2_pycell_lib
    baseline=out/'baseline/layout';dest=out/'layout';dest.mkdir()
    L=pya.Layout();L.read(str(baseline/(TOP+'.gds')));assert L.dbu==.001
    top=L.cell(TOP);assert top is not None
    old=json.loads((baseline/'result.json').read_text());oldbox=top.dbbox()
    before={(L.get_info(i).layer,L.get_info(i).datatype):pya.Region(top.begin_shapes_rec(i)).merged()for i in L.layer_indexes()}
    anchor_data=json.loads((out/'capture/wire/anchors08.json').read_text())
    anchors={a['label']:a for a in anchor_data['anchors']}
    terminals={(a['device'],a['terminal']):a for a in anchor_data['rows']}
    devices=json.loads((out/'capture/source/wire/device-locations01.json').read_text())['devices']
    wire=pya.LayoutToNetlist();wire.read(str(out/'capture/source/wire/native05/wires.l2n'))
    placement={}
    for tag in ('sa','sb','sc','sd'):
        v=old['placements'][tag];assert v['kind']=='sampler'
        box=list(map(float,re.findall(r'-?\d+(?:\.\d+)?',v['bbox_um'])));assert len(box)==4
        placement[tag]=pya.DBox(*box)
    plan=[];inventory=[]
    for d in devices:
        if d['model']!='sg13_lv_nmos':continue
        row=terminals[d['native_id'],'S'];a=anchors[row['wire_anchor']]
        pt=pya.Point(*a['point_dbu']);dp=pt.to_dtype(L.dbu)
        tags=[tag for tag,b in placement.items()if b.contains(dp)]
        if not tags:continue
        assert len(tags)==1 and row['native_net']=='avss' and row['metal']==8
        dt=pya.DCplxTrans.from_s(d['pcell']['transform'])
        assert dt.mag==1 and dt.angle==0 and not dt.is_mirror()
        tr=pya.ICplxTrans(1,0,False,round(dt.disp.x/L.dbu),round(dt.disp.y/L.dbu))
        cell=L.cell(d['pcell']['cell']);assert cell is not None
        region=pya.Region(cell.begin_shapes_rec(L.layer(8,0))).transformed(tr).merged()
        witness=pya.Region(pya.Box(pt.x-1,pt.y-1,pt.x+1,pt.y+1))
        assert (witness-region).is_empty()
        hit=list(region.interacting(witness).each());assert len(hit)==1
        pin=hit[0].bbox().to_dtype(L.dbu)
        observed=dict(native_id=d['native_id'],tag=tags[0],source_anchor=row['wire_anchor'],
            source_pin_um=str(pin),width_um=pin.width(),height_um=pin.height(),native_pcell=d['pcell'])
        inventory.append(observed)
        (out/'source-pin-inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
        assert pin.width()<=.5,('Unexpected source strip width',observed)
        # The unchanged reference has eight 36um tails and one 8um reference per sampler.
        if 7<pin.height()<9:
            observed['selection']='unchanged_8um_reference'
            continue
        assert 35<pin.height()<37,('Unexpected tail source strip height',observed)
        observed['selection']='36um_tail_midpoint_access'
        x=round(pin.center().x/.005)*.005;y=round(pin.center().y/.005)*.005
        lane=round((dt.disp.x-18)/.005)*.005
        for metal,px in [(8,x),(50,lane)]:
            net=wire.probe_net(wire.layer_by_name('gds_'+str(metal)),pya.DPoint(px,y).to_itype(L.dbu))
            assert net is not None and net.cluster_id==a['wire_component'],('Source midpoint or existing column is not original AVSS',d['native_id'],metal,px,y)
        assert 17< x-lane <20
        plan.append(dict(native_id=d['native_id'],tag=tags[0],source_anchor=row['wire_anchor'],
            native_source_net=row['native_net'],wire_component=a['wire_component'],source_pin_um=str(pin),
            source_center_um=[x,y],original_source_column_x_um=lane,native_pcell=d['pcell']))
    (out/'source-pin-inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
    assert len(inventory)==36 and len(plan)==32
    assert all(sum(p['tag']==tag for p in plan)==8 for tag in placement)
    assert all(sum(p['tag']==tag and p['selection']=='unchanged_8um_reference' for p in inventory)==1 for tag in placement)
    assert any(p['native_id']==1 and p['source_anchor']=='T001_S'for p in plan)
    overlay=L.create_cell('nssoc_cdr_sampler_source_midpoint_access_v14')
    stitches=[]
    def via(bottom,upper,x,y,cols,rows,owner):
        cell=L.create_cell('via_stack','SG13_dev',dict(b_layer=bottom,t_layer=upper,vn_columns=cols,vn_rows=rows))
        assert cell is not None and not cell.is_empty()
        b=cell.dbbox();tr=pya.DTrans(round((x-b.center().x)/.005)*.005,round((y-b.center().y)/.005)*.005)
        overlay.insert(pya.DCellInstArray(cell.cell_index(),tr))
        stitches.append(dict(native_id=owner,bottom=bottom,top=upper,columns=cols,rows=rows,center_um=[x,y],bbox_um=str(b.transformed(tr))))
    for p in plan:
        x,y=p['source_center_um'];lane=p['original_source_column_x_um']
        via('Metal1','Metal3',x,y,1,16,p['native_id'])
        vb=list(map(float,re.findall(r'-?\d+(?:\.\d+)?',stitches[-1]['bbox_um'])))
        sb=list(map(float,re.findall(r'-?\d+(?:\.\d+)?',p['source_pin_um'])))
        assert len(vb)==len(sb)==4 and sb[1]+.5<vb[1]<vb[3]<sb[3]-.5,('Native via does not fit tail source height',p,stitches[-1])
        via('Metal3','Metal4',lane,y,8,1,p['native_id'])
        bridge=pya.DBox(lane-.6,y-.6,x+.3,y+.6)
        overlay.shapes(L.layer(30,0)).insert(bridge)
        p['bridge_m3_um']=str(bridge)
    top.insert(pya.DCellInstArray(overlay.cell_index(),pya.DTrans()))
    assert top.dbbox()==oldbox
    addition={(L.get_info(i).layer,L.get_info(i).datatype):pya.Region(overlay.begin_shapes_rec(i)).merged()for i in L.layer_indexes()}
    after={(L.get_info(i).layer,L.get_info(i).datatype):pya.Region(top.begin_shapes_rec(i)).merged()for i in L.layer_indexes()}
    assert {k for k,v in addition.items()if not v.is_empty()}<=ALLOWED
    keys=set(before)|set(after)|set(addition)
    expected={k:(before.get(k,pya.Region())+addition.get(k,pya.Region())).merged()for k in keys}
    def verdict(got):
        return all((got.get(k,pya.Region())^expected.get(k,pya.Region())).is_empty()for k in keys|set(got))
    assert verdict(after)and all((before.get(k,pya.Region())-after.get(k,pya.Region())).is_empty()for k in keys)
    faults=[]
    p=plan[0];x,y=p['source_center_um'];lane=p['original_source_column_x_um']
    cut=pya.Region(pya.DBox(lane+5,y-.6,lane+6,y+.6).to_itype(.001))
    broken=dict(after);broken[(30,0)]=after[(30,0)]-cut
    assert not verdict(broken);faults.append('cut_actual_new_source_bridge')
    broken=dict(after);broken[(19,0)]=after[(19,0)]-addition[(19,0)]
    assert not verdict(broken);faults.append('remove_actual_new_source_vias')
    broken=dict(after);broken[(5,0)]=after.get((5,0),pya.Region())+pya.Region(pya.Box(1,1,101,101))
    assert not verdict(broken);faults.append('unrelated_gate_geometry_added')
    opt=pya.SaveLayoutOptions();opt.select_cell(top.cell_index());L.write(str(dest/(TOP+'.gds')),opt)
    for name in ('schematic.cir',TOP+'.lef'):(dest/name).write_bytes((baseline/name).read_bytes())
    # Verify serialized geometry, not only the in-memory pre-write database.
    check=pya.Layout();check.read(str(dest/(TOP+'.gds')))
    saved={(check.get_info(i).layer,check.get_info(i).datatype):pya.Region(check.cell(TOP).begin_shapes_rec(i)).merged()for i in check.layer_indexes()}
    assert check.dbu==.001 and verdict(saved)
    proof=dict(status='PASS_NATIVE_SOURCE_MIDPOINT_OVERLAY_GEOMETRY_REQUIRES_DRC_LVS_AND_FRESH_RC',
        original_devices=484,sampler_count=4,observed_source_pins=len(inventory),unchanged_reference_sources=4,source_accesses=len(plan),native_via_stacks=len(stitches),
        original_geometry_retained=True,all_layers_exact=True,serialized_gds_checked=True,
        reference_and_lef_byte_identical=True,plan=plan,stitches=stitches,rejected=faults,
        source_gds_sha256=sha(baseline/(TOP+'.gds')),candidate_gds_sha256=sha(dest/(TOP+'.gds')),
        electrical_accepted=False,qualified_pex=False,full_phy_accepted=False)
    (out/'geometry-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    d=dict(old)
    d.update(status='GENERATED_SOURCE_MIDPOINT_ACCESSES_REQUIRES_NATIVE_DRC_LVS_RC_AND_LOADED_GATES',
        source_midpoint_access=proof,original_generation_inputs=old['inputs'],
        inputs={str(p):sha(p)for p in [Path(__file__),baseline/(TOP+'.gds'),baseline/'schematic.cir',baseline/(TOP+'.lef'),baseline/'result.json',
            out/'capture/wire/anchors08.json',out/'capture/source/wire/device-locations01.json',out/'capture/source/wire/native05/wires.l2n']})
    d['outputs']={p.name:sha(p)for p in dest.iterdir()if p.is_file()}
    (dest/'result.json').write_text(json.dumps(d,indent=2)+'\n')
    print(json.dumps(dict(status=d['status'],source_accesses=len(plan),native_via_stacks=len(stitches))))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();generate(a.out.resolve())
