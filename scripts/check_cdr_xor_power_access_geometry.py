#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent whole-drawing reconstruction of the real local power additions."""
import argparse,hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--baseline',type=Path,required=True);ap.add_argument('--candidate',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    src=ROOT/'pdk/libs.tech/klayout/python';sys.path[:0]=[str(src),str(src/'pycell4klayout-api/source/python')]
    import pya
    import sg13g2_pycell_lib
    oldname='nssoc_cdr_xor_hybrid_tail_layout_v3';newname='nssoc_cdr_xor_power_access_layout_v4'
    old=json.loads((a.baseline/'result.json').read_text());new=json.loads((a.candidate/'result.json').read_text())
    for key in ['core_devices','substrate_contacts','local_mos_contacts','routes','ports','bbox_um']:
        assert old[key]==new[key],('Original device/routing metadata changed',key)
    for directory,data in [(a.baseline,old),(a.candidate,new)]:
        assert all(sha(directory/name)==digest for name,digest in data['outputs'].items())
    assert (a.baseline/'schematic.cir').read_text().replace(oldname,newname)==(a.candidate/'schematic.cir').read_text()
    assert (a.baseline/(oldname+'.lef')).read_text().replace(oldname,newname)==(a.candidate/(newname+'.lef')).read_text()
    def rect(raw):
        v=list(map(float,re.findall(r'-?\d+(?:\.\d+)?',raw)));assert len(v)==4;return pya.DBox(*v)
    nets=sorted({r['net']for r in old['routes']});shifts=[rect(v).center().y-(150+6*nets.index(n))for n,v in old['ports'].items()]
    assert max(shifts)-min(shifts)<1e-9;dy=shifts[0]
    def drawing(directory,name):
        l=pya.Layout();l.read(str(directory/(name+'.gds')));t=l.cell(name);assert t is not None and l.dbu==.001
        return l,t,{(l.get_info(i).layer,l.get_info(i).datatype):pya.Region(t.begin_shapes_rec(i)).merged()for i in l.layer_indexes()if l.get_info(i).datatype==0}
    lo,to,before=drawing(a.baseline,oldname);ln,tn,actual=drawing(a.candidate,newname)
    assert to.dbbox()==tn.dbbox()
    e=pya.Layout();e.dbu=.001;overlay=e.create_cell('independent_power_additions');source_records=[]
    def box(layer,l,b,r,t):overlay.shapes(e.layer(layer,0)).insert(pya.DBox(l,b+dy,r,t+dy))
    for record in old['core_devices']:
        if record['model']!='sg13_lv_nmos':continue
        x,y=record['placement_um'];params=record['params']
        c=e.create_cell('nmos','SG13_dev',dict(w=params['w'],l=params['l'],ng=1));assert c is not None
        pins=sorted([s.dbbox().transformed(pya.DTrans(x,y))for s in c.each_shape(e.layer(8,2))],key=lambda b:b.center().x)
        assert len(pins)==2;pin=pins[0];assert record['nets'][2]=='avss'
        nativepin=pya.Region(pin.transformed(pya.DTrans(0,dy)).to_itype(e.dbu));assert (nativepin-before[(8,0)]).is_empty()
        sx=round(pin.center().x/.005)*.005;lower=round((pin.bottom+.4)/.005)*.005;upper=round((pin.top-1.2)/.005)*.005;middle=round(pin.center().y/.005)*.005
        mandatory={lower,middle,upper};periodic={round((lower+4*k)/.005)*.005 for k in range(1,100)if lower+4*k<upper}
        ys=sorted(mandatory|{v for v in periodic if all(abs(v-q)>=1.5 for q in mandatory)})
        assert all(b-a>=1.5 for a,b in zip(ys,ys[1:]))
        meta=next(v for v in new['distributed_source_access']if v['device']==record['instance'])
        assert meta['via_y_um']==ys and meta['source_x_um']==sx and meta['native_source_pin']==str(pin)
        stack=e.create_cell('via_stack','SG13_dev',dict(b_layer='Metal1',t_layer='Metal3',vn_columns=1,vn_rows=1,vt1_columns=2,vt1_rows=1,vt2_columns=1,vt2_rows=1));assert stack is not None
        bb=stack.dbbox()
        for yy in ys[1:]:
            dx=round((sx-bb.center().x)/.005)*.005;ty=round((yy-bb.center().y)/.005)*.005+dy
            overlay.insert(pya.DCellInstArray(stack.cell_index(),pya.DTrans(dx,ty)))
        box(30,sx-.2,lower-.2,sx+.2,upper+.2)
        source_records.append(dict(device=record['instance'],source_x_um=sx,via_y_um=ys,added_vias=len(ys)-1))
    assert len(source_records)==3
    loads={v['instance']for v in old['core_devices']if v['model']=='rppd'and'avdd'in v['nets'][:2]};widened=[]
    for route in old['routes']:
        if route['net']!='avdd'or route['device']not in loads:continue
        lane,y=route['escape'];x=round(rect(route['pin']).center().x/.005)*.005
        box(30,lane-.2,y-.6,x+.2,y+.6);widened.append(route['device'])
    assert set(widened)==loads and loads
    addition={(e.get_info(i).layer,e.get_info(i).datatype):pya.Region(overlay.begin_shapes_rec(i)).merged()for i in e.layer_indexes()if e.get_info(i).datatype==0}
    keys=set(before)|set(actual)|set(addition);empty=pya.Region()
    expected={key:(before.get(key,empty)+addition.get(key,empty)).merged()for key in keys}
    def verify(regions):
        for key in keys|set(regions):
            assert (expected.get(key,empty)^regions.get(key,empty)).is_empty(),('Unexpected drawing delta',key)
    verify(actual);changed=[]
    for key in sorted(keys):
        delta=actual.get(key,empty)-before.get(key,empty)
        assert (before.get(key,empty)-actual.get(key,empty)).is_empty(),('Original geometry removed',key)
        if not delta.is_empty():
            assert key in {(8,0),(19,0),(10,0),(29,0),(30,0)},('Changed device or unrelated layer',key)
            changed.append(dict(layer=list(key),added_area_dbu2=delta.area()))
    controls=[]
    for fault,key in [('missing_source_via',(19,0)),('missing_source_metal',(30,0))]:
        added=actual[key]-before[key];assert not added.is_empty();cut=pya.Region(next(added.each()))
        mutated=dict(actual);mutated[key]=actual[key]-cut
        try:verify(mutated)
        except AssertionError:controls.append(dict(fault=fault,rejected=True,removed_area_dbu2=cut.area()))
        else:raise AssertionError('Actual removed geometry accepted')
    key=next(k for k,v in actual.items()if k not in {(8,0),(19,0),(10,0),(29,0),(30,0)}and not v.is_empty());cut=pya.Region(next(actual[key].each()));mutated=dict(actual);mutated[key]=actual[key]-cut
    try:verify(mutated)
    except AssertionError:controls.append(dict(fault='changed_original_device_layer',layer=list(key),rejected=True,removed_area_dbu2=cut.area()))
    else:raise AssertionError('Device-layer mutation accepted')
    assert len(controls)==3
    inputs={str(p):sha(p)for p in [Path(__file__),a.baseline/'result.json',a.candidate/'result.json',a.baseline/(oldname+'.gds'),a.candidate/(newname+'.gds'),a.baseline/'schematic.cir',a.candidate/'schematic.cir']}
    report=dict(status='PASS_EXACT_NATIVE_XOR59_POWER_ADDITIONS_AND_THREE_GEOMETRY_FAULTS',all_drawing_layers_checked=len(keys),changed_layers=changed,source_access=source_records,widened_avdd_loads=widened,original_routes_devices_ports_boundary_preserved=True,schematic_and_lef_equal_except_top=True,controls=controls,inputs=inputs,electrical_accepted=False)
    a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k not in ['inputs','source_access']}))
if __name__=='__main__':main()
