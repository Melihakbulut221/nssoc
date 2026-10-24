#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Add native parent AVDD feed bypasses; preserve every original device and route."""
import argparse,json,re,sys
from pathlib import Path
import generate_cdr_retimed_localbus_v12_parent as original
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
TOP=original.TOP

def rect(pya,s):
    v=list(map(float,re.findall(r'-?\d+(?:\.\d+)?',s)))
    assert len(v)==4
    return pya.DBox(*v)

def generate(out):
    original.generate(out)
    dest=out/'layout';baseline=out/'baseline-localbus'
    dest.rename(baseline);dest.mkdir()
    frozen={str(p):sha(p)for p in baseline.iterdir()if p.is_file()}
    d=json.loads((baseline/'result.json').read_text())
    import pya
    L=pya.Layout();L.read(str(baseline/(TOP+'.gds')))
    assert L.dbu==.001
    top=L.cell(TOP);assert top is not None
    before={L.get_info(li).to_s():pya.Region(top.begin_shapes_rec(li)).merged()for li in L.layer_indexes()}
    oldbox=top.dbbox()
    overlay=L.create_cell('nssoc_cdr_parent_avdd_feeds_v13')
    m6=pya.Region(top.begin_shapes_rec(L.layer(126,0))).merged()
    m7=pya.Region(top.begin_shapes_rec(L.layer(134,0))).merged()
    rows=[];stitches=[]
    def addbox(layer,b):overlay.shapes(L.layer(layer,0)).insert(b)
    def via(x,y,rows_count,owner):
        cell=L.create_cell('via_stack','SG13_dev',dict(b_layer='TopMetal1',t_layer='TopMetal2',vn_columns=2,vn_rows=1,vt1_columns=2,vt1_rows=1,vt2_columns=4,vt2_rows=rows_count))
        assert cell is not None and not cell.is_empty()
        b=cell.dbbox();tx=round((x-b.center().x)/.005)*.005;ty=round((y-b.center().y)/.005)*.005
        tr=pya.DTrans(float(tx),float(ty));placed=b.transformed(tr)
        assert placed.width()<=16 and placed.height()<=(32 if rows_count==4 else 3.2)+1e-6,('Via enclosure exceeds intended rail',str(placed))
        overlay.insert(pya.DCellInstArray(cell.cell_index(),tr))
        stitches.append(dict(tag=owner,center_um=[x,y],columns=4,rows=rows_count,bbox_um=str(placed)))
    targets=[(tag,p)for tag,p in d['placements'].items()if any(pin.lower()=='avdd'for pin in p['ports'])]
    assert len(targets)==11
    for tag,placed in targets:
        bounds=rect(pya,placed['bbox_um'])
        pin=next(pin for pin in placed['ports']if pin.lower()=='avdd')
        port=rect(pya,placed['ports'][pin]);py=port.center().y
        route=[r for r in d['routes']if r['tag']==tag and r['net']=='avdd'];assert len(route)==1
        branch=rect(pya,route[0]['box_um']);assert abs(branch.height()-3.2)<1e-6
        gx=branch.left+1.6+24
        x=bounds.left-22.;y=bounds.bottom-24.
        assert abs(branch.center().y-py)<1e-6 and abs(branch.right-(bounds.left-4.4))<1e-6
        feed=pya.DBox(gx-16,y-16,x+8,y+16)
        column=pya.DBox(x-8,y-8,x+8,py+1.6)
        f=pya.Region(feed.to_itype(L.dbu));c=pya.Region(column.to_itype(L.dbu))
        # Actual existing shapes, not just bounding-box expectations.
        assert (f.sized(2005)&m7).is_empty(),('No clear actual TM2 gap',tag)
        assert (c.sized(1645)&m6).is_empty(),('No clear actual TM1 side corridor',tag)
        landing=pya.Region(pya.DBox(gx-8,y-8,gx+8,y+8).to_itype(L.dbu))
        assert (landing-m6).is_empty(),('No real global AVDD rail under via',tag)
        touch=pya.Region(pya.DBox(x-7,py-1.6,x+7,py+1.6).to_itype(L.dbu))
        assert (touch-m7).is_empty(),('No actual original AVDD branch at destination',tag)
        addbox(134,feed);addbox(126,column)
        via(gx,y,4,tag);via(x,y,4,tag);via(x,py,1,tag)
        rows.append(dict(tag=tag,net='avdd',feed_tm2_um=str(feed),column_tm1_um=str(column),source_global_rail_x_um=gx,original_branch_um=str(branch),target_port_um=str(port),actual_existing_clearance_checked=True))
    top.insert(pya.DCellInstArray(overlay.cell_index(),pya.DTrans()))
    assert top.dbbox()==oldbox
    delta=[]
    for li in L.layer_indexes():
        key=L.get_info(li).to_s();old=before.get(key,pya.Region())
        new=pya.Region(top.begin_shapes_rec(li)).merged();extra=pya.Region(overlay.begin_shapes_rec(li)).merged()
        assert (old-new).is_empty() and (new^(old+extra).merged()).is_empty()
        if not extra.is_empty():
            info=L.get_info(li);assert (info.layer,info.datatype)in {(126,0),(133,0),(134,0)}
            delta.append(dict(layer=key,added_area_dbu2=(new-old).area()))
    opt=pya.SaveLayoutOptions();opt.select_cell(top.cell_index());L.write(str(dest/(TOP+'.gds')),opt)
    for name in ['schematic.cir',TOP+'.lef']:(dest/name).write_bytes((baseline/name).read_bytes())
    assert all(sha(Path(p))==h for p,h in frozen.items())
    d.update(status='GENERATED_PARENT_AVDD_BYPASSES_REQUIRES_NATIVE_PHYSICAL_FRESH_RC_AND_ORIGINAL_WAVES',
        parent_avdd_bypass=dict(feeds=rows,stitches=stitches,geometry_delta=delta,feed_width_um=32,column_width_um=16,
          full_phy_accepted=False,electrical_accepted=False,scope='Eleven parent AVDD branches bypassed through native TM1/TM2; original branches, child geometry and all device values retained. Fresh RC and unchanged loaded gates required.'),
        baseline_localbus_inputs=frozen)
    d['inputs'][str(Path(__file__).resolve())]=sha(Path(__file__).resolve())
    d['outputs']={p.name:sha(p)for p in dest.iterdir()if p.is_file()}
    (dest/'result.json').write_text(json.dumps(d,indent=2)+'\n')
    print(json.dumps(dict(status=d['status'],feeds=len(rows),stitches=len(stitches))))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();generate(a.out.resolve())
