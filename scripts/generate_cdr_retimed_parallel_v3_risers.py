#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Add actual TopMetal1 supply risers and TopMetal2 shunts to the AVSS256 PD484.

The original children, placements, signal routes and circuit remain. Added native
M5-to-M7 vias stitch each continuous M5 supply bus to a real M7 conductor. Fresh
native physical checks, full MIM-aware RC and loaded waveforms are mandatory.
"""
import argparse,hashlib,json,re,sys
from pathlib import Path
import generate_cdr_retimed_parallel_v3_base as base
import cdr_retimed_parallel_v3_parent_plan as plan
from cdr_retimed_parallel_v3_parent_plan import TYPES
ROOT=Path(__file__).resolve().parents[1]
TOP='nssoc_cdr_pd484_parallel_supply_risers_v2'

def generate(out):
    delta=json.loads((ROOT/'scripts/cdr-avss256-placement-delta.json').read_text())
    raw=(ROOT/delta['baseline_path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==delta['baseline_sha256']
    adapted=raw.decode()
    for edit in delta['edits']:
        assert adapted.count(edit['before'])==edit['count']
        adapted=adapted.replace(edit['before'],edit['after'])
    assert (ROOT/delta['candidate_path']).read_bytes()==adapted.encode()
    assert hashlib.sha256(adapted.encode()).hexdigest()==delta['candidate_sha256']
    base.TYPES=plan.TYPES;base.build=plan.build;base.verify=plan.verify
    base.generate(out)
    original=out/'layout';baseline=out/'baseline-avss256';original.rename(baseline)
    frozen={str(p):base.sha(p)for p in baseline.iterdir()if p.is_file()}
    data=json.loads((baseline/'result.json').read_text())
    import pya
    L=pya.Layout();L.read(str(baseline/(base.TOP+'.gds')))
    top=L.cell(base.TOP);assert top is not None and L.dbu==.001
    old_bbox=top.dbbox()
    before={(L.get_info(li).layer,L.get_info(li).datatype):pya.Region(top.begin_shapes_rec(li)).merged()for li in L.layer_indexes()}
    overlay=L.create_cell('nssoc_pd484_parallel_supply_risers_v2')
    m5=pya.Region(top.begin_shapes_rec(L.layer(67,0))).merged()
    straps=[];cuts=0
    def rect(raw):
        values=list(map(float,re.findall(r'-?\d+(?:\.\d+)?',raw)));assert len(values)==4
        return pya.DBox(*values)
    def via(x,y):
        nonlocal cuts
        c=L.create_cell('via_stack','SG13_dev',dict(b_layer='Metal5',t_layer='TopMetal2',vn_columns=2,vn_rows=1,vt1_columns=2,vt1_rows=1,vt2_columns=1,vt2_rows=1))
        assert c is not None and not c.is_empty()
        b=c.dbbox();dx=round((x-b.center().x)/.005)*.005;dy=round((y-b.center().y)/.005)*.005
        overlay.insert(pya.DCellInstArray(c.cell_index(),pya.DTrans(dx,dy)))
        overlay.shapes(L.layer(126,0)).insert(pya.DBox(x-1.6,y-1.6,x+1.6,y+1.6));cuts+=1
    # Plan same-net riser endpoints from the exact native child metadata.
    # Every endpoint below is independently checked against actual M4 and
    # physically written by the unchanged riser construction later.
    child_manifest=json.loads((out/'children.json').read_text())
    planned_riser_ends=[];suppressed_shunt_vias=[]
    for tag,placed in data['placements'].items():
        kind=placed['kind'];bounds=rect(placed['bbox_um'])
        child=json.loads((out/child_manifest['children'][kind]['directory']/'result.json').read_text())
        dx=child['origin_translation_um'][0]if kind=='sampler'else 0.
        for route in child['routes']:
            pin=route['net'];net=pin.lower()
            if net not in ('avdd','avss'):continue
            x=route['escape_lane_um']if kind=='sampler'else route['escape'][0]
            planned_riser_ends.append(dict(tag=tag,net=net,device=route['device'],point=[x+dx+bounds.left,rect(placed['ports'][pin]).center().y]))
    for tag,placed in data['placements'].items():
        if TYPES[placed['kind']]['layer']!=67:continue
        bounds=rect(placed['bbox_um'])
        for pin,raw in placed['ports'].items():
            if pin.lower()not in ('avdd','avss'):continue
            p=rect(raw);y=p.center().y
            selected=m5.interacting(pya.Region(p.to_itype(L.dbu)))
            assert selected.count()==1,(tag,pin,selected.count())
            region_box=selected.bbox().to_dtype(L.dbu)
            x0=p.left;x1=region_box.right
            assert abs(x0-bounds.left)<.001 and x1<=bounds.right+.001 and x1-x0>20
            # Only an uninterrupted existing M5 conductor can receive the shunt.
            centerline=pya.Region(pya.DBox(x0,y-.1,x1,y+.1).to_itype(L.dbu))
            assert (centerline-selected).is_empty(),(tag,pin,'noncontinuous supply bus')
            strap=pya.DBox(x0,y-1.6,x1,y+1.6)
            overlay.shapes(L.layer(134,0)).insert(strap)
            xs=[];x=x0+(4 if placed['kind']=='sampler' else 12)
            while x<=x1-4:
                nearby=[r for r in planned_riser_ends if r['tag']==tag and r['net']==pin.lower()and abs(r['point'][1]-y)<1e-6 and abs(r['point'][0]-x)<(5. if placed['kind']=='sampler' else 4.)]
                if nearby:
                    assert len(nearby)==1
                    suppressed_shunt_vias.append(dict(tag=tag,net=pin.lower(),omitted_shunt_center_um=[x,y],retained_riser=nearby[0]))
                else:
                    via(x,y);xs.append(x)
                x+=20
            assert xs
            straps.append(dict(tag=tag,kind=placed['kind'],net=pin.lower(),original_m5_bus_bbox_um=str(region_box),new_m7_box_um=str(strap),via_centers_um=[[x,y]for x in xs]))
    # Reinforce the actual long M4 device-to-rail escapes with native M6.
    # M4 remains untouched; each new riser joins it through a physical via at
    # its recorded start and joins the same M5/M7 supply at its actual endpoint.
    manifest=json.loads((out/'children.json').read_text())
    risers=[]
    m4=pya.Region(top.begin_shapes_rec(L.layer(50,0))).merged()
    for tag,placed in data['placements'].items():
        kind=placed['kind']
        child=json.loads((out/manifest['children'][kind]['directory']/'result.json').read_text())
        bounds=rect(placed['bbox_um'])
        if kind=='sampler':
            dx,dy=child['origin_translation_um']
        else:
            dx=0.;nets=sorted({route['net']for route in child['routes']})
            shifts=[rect(raw).center().y-(150+6*nets.index(pin))for pin,raw in child['ports'].items()]
            assert max(shifts)-min(shifts)<1e-6
            dy=shifts[0]
        for route in child['routes']:
            pin=route['net'];net=pin.lower()
            if net not in ('avdd','avss'):continue
            assert pin in placed['ports']
            if kind=='sampler':x,sy=route['escape_lane_um'],route['escape_y_um']
            else:x,sy=route['escape']
            x+=dx+bounds.left;sy+=dy+bounds.bottom
            ey=rect(placed['ports'][pin]).center().y
            assert ey>sy+20 and bounds.left<x<bounds.right
            strip=pya.Region(pya.DBox(x-.1,sy,x+.1,ey).to_itype(L.dbu))
            assert (strip-m4).is_empty(),(tag,pin,'escape metadata does not match actual M4')
            c=L.create_cell('via_stack','SG13_dev',dict(b_layer='Metal4',t_layer='TopMetal1',vn_columns=2,vn_rows=1,vt1_columns=2,vt1_rows=1))
            assert c is not None and not c.is_empty()
            b=c.dbbox();vx=round((x-b.center().x)/.005)*.005;vy=round((sy-b.center().y)/.005)*.005
            # Compare against REAL existing M6, including child QP/QN via
            # patches and already inserted supply patches/risers. Even a
            # DRC-clean merged conductor may short different logical nets.
            blockers=(pya.Region(top.begin_shapes_rec(L.layer(126,0)))+
                      pya.Region(overlay.begin_shapes_rec(L.layer(126,0)))).merged()
            clearance=round(1.645/L.dbu)  # native1.64um + one5nm routing grid
            shift=0.0;clearance_checked=False;bridges=[]
            def span(offset):
                rx=x+offset
                vertical=pya.DBox(rx-1.6,sy-1.6,rx+1.6,ey+1.6)
                joins=[] if offset==0 else [pya.DBox(min(x,rx)-1.6,by-1.6,max(x,rx)+1.6,by+1.6)for by in (sy,ey)]
                reg=pya.Region(vertical.to_itype(L.dbu))
                for join in joins:reg+=pya.Region(join.to_itype(L.dbu))
                return vertical,joins,reg.merged()
            if kind=='sampler':
                chosen=None
                for step in range(2001):
                    for candidate in ([0.]if step==0 else[step*.005,-step*.005]):
                        vertical,joins,reg=span(candidate)
                        if vertical.left<bounds.left or vertical.right>bounds.right:continue
                        if (reg.sized(clearance)&blockers).is_empty():
                            chosen=(candidate,vertical,joins);break
                    if chosen is not None:break
                assert chosen is not None,('No actual M6 clearance corridor',tag,net,route['device'])
                shift,riser,joins=chosen;clearance_checked=True
                assert (span(shift)[2].sized(clearance)&blockers).is_empty()
            else:riser,joins,_=span(0.)
            # Actual original M4 start and M5 supply end remain connected.
            overlay.insert(pya.DCellInstArray(c.cell_index(),pya.DTrans(vx,vy)))
            overlay.shapes(L.layer(126,0)).insert(riser)
            for bridge in joins:
                overlay.shapes(L.layer(126,0)).insert(bridge);bridges.append(str(bridge))
            via(x,ey)
            risers.append(dict(tag=tag,kind=kind,net=net,device=route['device'],m4_start_um=[x,sy],supply_end_um=[x,ey],new_m6_box_um=str(riser),span_shift_um=shift,new_m6_endpoint_bridges_um=bridges,actual_m6_clearance_checked=clearance_checked,clearance_um=1.645 if clearance_checked else None))
    shifted={(r['tag'],r['device'])for r in risers if r['span_shift_um']}
    assert {(tag,device)for tag in ('sa','sb','sc','sd')for device in ('M_T3','S_T0','S_RP')}<=shifted
    assert all(r['actual_m6_clearance_checked'] for r in risers if r['kind']=='sampler')
    assert all(r['span_shift_um']==0 for r in risers if r['kind']!='sampler')
    assert all(len(r['new_m6_endpoint_bridges_um'])==2 and abs(r['span_shift_um'])<=10 for r in risers if r['span_shift_um'])
    actual_riser_ends={(r['tag'],r['net'],r['device'],tuple(r['supply_end_um']))for r in risers}
    assert {(r['tag'],r['net'],r['device'],tuple(r['point']))for r in planned_riser_ends}==actual_riser_ends
    # Preserve the two measured XOR collisions; new sampler widths can place
    # additional redundant same-net shunt stacks near real retained risers.
    xor_suppressed=[r for r in suppressed_shunt_vias if r['tag'] in ('x','y')]
    assert len(xor_suppressed)==2
    assert {(r['tag'],r['net'],r['retained_riser']['device'])for r in xor_suppressed}=={('x','avss','D21'),('y','avss','D21')}
    assert all(abs(r['omitted_shunt_center_um'][0]-r['retained_riser']['point'][0])==1. for r in xor_suppressed)
    for r in suppressed_shunt_vias:
        keep=r['retained_riser']
        assert r['tag']==keep['tag'] and r['net']==keep['net']
        assert r['omitted_shunt_center_um'][1]==keep['point'][1]
        assert abs(r['omitted_shunt_center_um'][0]-keep['point'][0])<5.
        assert r['tag'] in ('x','y','sa','sb','sc','sd')
    assert len({r['tag']for r in risers})==16 and len(risers)>=80
    assert len(straps)==27 and cuts>100,(len(straps),cuts)

    top.insert(pya.DCellInstArray(overlay.cell_index(),pya.DTrans()))
    assert top.dbbox()==old_bbox,'Supply reinforcement changed the external boundary'
    delta=[];allowed={(50,0),(66,0),(67,0),(125,0),(126,0),(133,0),(134,0)}
    for li in L.layer_indexes():
        info=L.get_info(li);key=(info.layer,info.datatype)
        old=before.get(key,pya.Region());added=pya.Region(overlay.begin_shapes_rec(li)).merged();after=pya.Region(top.begin_shapes_rec(li)).merged()
        assert (old-after).is_empty(),'An original shape was removed'
        assert (after^(old+added).merged()).is_empty(),'Unrecorded geometry change'
        if not added.is_empty():
            assert key in allowed,('Unexpected overlay layer',key)
            delta.append(dict(layer=key,added_area_dbu2=(after-old).area(),overlay_area_dbu2=added.area()))
        elif key not in allowed:assert (before.get(key,pya.Region())^after).is_empty()
    assert delta
    top.name=TOP
    dest=out/'layout';dest.mkdir()
    opt=pya.SaveLayoutOptions();opt.select_cell(top.cell_index());L.write(str(dest/(TOP+'.gds')),opt)
    schematic=(baseline/'schematic.cir').read_text();assert schematic.count(base.TOP)==2
    (dest/'schematic.cir').write_text(schematic.replace(base.TOP,TOP))
    lef=(baseline/(base.TOP+'.lef')).read_text();assert lef.count(base.TOP)==2
    (dest/(TOP+'.lef')).write_text(lef.replace(base.TOP,TOP))
    assert all(base.sha(Path(p))==h for p,h in frozen.items())
    data.update(status='GENERATED_PD484_NATIVE_SUPPLY_RISERS_REQUIRES_PHYSICAL_RC_AND_LOADED_VALIDATION',baseline_v2_inputs=frozen,
        supply_overlay=dict(straps=straps,risers=risers,suppressed_redundant_shunt_vias=suppressed_shunt_vias,all_planned_riser_endpoints_written=True,riser_width_um=3.2,riser_count=len(risers),via_stacks_m5_m7=cuts,via_stacks_m4_m6=len(risers),width_um=3.2,pitch_um=20.,geometry_delta=delta,all_original_drawing_geometry_retained=True,only_native_vias_and_supply_metal_added=True,all_device_layers_unchanged=True,placements_signals_ports_and_schematic_unchanged_except_top_name=True,
            scope='Candidate to reduce measured local supply losses through physical M4-to-M6 risers in sixteen macros. Horizontal shunt via X offsets are4um for samplers and12um for other leaves to avoid opposite-rail riser crossings. Does not bypass any wire model or intrinsic device. Native fresh extraction and loaded gate remeasurement required. New XOR children have Metal5 ports and receive actual supply shunts and risers.'))
    data['inputs'].update({str(Path(__file__)):base.sha(Path(__file__)),str(ROOT/'scripts/generate_cdr_retimed_avss256_base.py'):base.sha(ROOT/'scripts/generate_cdr_retimed_avss256_base.py')})
    data['outputs']={p.name:base.sha(p)for p in dest.iterdir()if p.is_file()}
    (dest/'result.json').write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps(dict(status=data['status'],straps=len(straps),risers=len(risers),via_stacks=cuts,bbox_um=data['bbox_um'])))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();generate(a.out.resolve())
