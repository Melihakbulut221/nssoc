#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Compare complete actual GDS against frozen parent plus independently rebuilt native feed metal."""
import argparse,hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOP='nssoc_cdr_pd484_localbus_v12'

def run(baseline,passed,candidate,output):
    source=ROOT/'pdk/libs.tech/klayout/python'
    sys.path[:0]=[str(source),str(source/'pycell4klayout-api/source/python')]
    import pya
    import sg13g2_pycell_lib
    def rect(s):
        values=[float(v)for v in re.findall(r'-?\d+(?:\.\d+)?',s)]
        assert len(values)==4
        return pya.DBox(*values)
    old=json.loads((baseline/'result.json').read_text());new=json.loads((candidate/'result.json').read_text())
    pin=json.loads((ROOT/'docs/evidence/cdr-localbus-v12-parent-physical-pass-20261019.json').read_text())
    assert pin['run']==39249146302 and pin['source_head']=='99913550040b2c41e36802633b47a59da1ac51c1'
    assert hashlib.sha256((passed/(TOP+'.gds')).read_bytes()).hexdigest()==pin['report']['outputs']['layout/'+TOP+'.gds'], 'Immutable passed native parent hash differs'
    for key in old:
        if key not in ('status','inputs','outputs'):assert old[key]==new[key],('Changed original metadata',key)
    for name in ('schematic.cir',TOP+'.lef'):assert (baseline/name).read_bytes()==(candidate/name).read_bytes()
    assert old['primitive_census']==dict(npn13g2=116,sg13_lv_nmos=46,rppd=102,cap_cmim=11,ptap1=209)
    a=pya.Layout();a.read(str(baseline/(TOP+'.gds')))
    b=pya.Layout();b.read(str(candidate/(TOP+'.gds')))
    assert a.dbu==b.dbu==.001 and a.cell(TOP).dbbox()==b.cell(TOP).dbbox()
    def regions(layout):
        return {(layout.get_info(i).layer,layout.get_info(i).datatype):pya.Region(layout.cell(TOP).begin_shapes_rec(i)).merged()for i in layout.layer_indexes()}
    before=regions(a);after=regions(b)
    frozen=pya.Layout();frozen.read(str(passed/(TOP+'.gds')))
    frozen_regions=regions(frozen)
    assert all((before.get(k,pya.Region())^frozen_regions.get(k,pya.Region())).is_empty()for k in set(before)|set(frozen_regions)), 'Regenerated baseline drawing differs from immutable passed parent'
    for name in ('schematic.cir',TOP+'.lef'):assert (baseline/name).read_bytes()==(passed/name).read_bytes()
    frozen_meta=json.loads((passed/'result.json').read_text())
    for key in ('placements','routes','ports','bbox_um','primitive_census','supply_overlay'):assert old[key]==frozen_meta[key], ('Regenerated parent metadata differs',key)
    expected=pya.Layout();expected.dbu=.001;t=expected.create_cell('expected_native_parent_supply_additions')
    cursor=8.;gx=None
    for net in old['source_plan']['nets']:
        width=256 if net=='avss'else 64 if net in ('avdd','sub')else 3.2
        if net=='avdd':gx=cursor+width/2
        cursor+=width+8
    assert gx is not None
    targets=[];cuts=[]
    for tag,placed in old['placements'].items():
        names=[pin for pin in placed['ports']if pin.lower()=='avdd']
        if not names:continue
        assert len(names)==1
        bounds=rect(placed['bbox_um']);pin=rect(placed['ports'][names[0]])
        assert abs(bounds.left-cursor-40)<1e-6 and pin.left==bounds.left
        cx=bounds.left-22;fy=bounds.bottom-24;py=pin.center().y
        feed=pya.DBox(gx-16,fy-16,cx+8,fy+16);column=pya.DBox(cx-8,fy-8,cx+8,py+1.6)
        t.shapes(expected.layer(134,0)).insert(feed);t.shapes(expected.layer(126,0)).insert(column)
        for vx,vy,ny in [(gx,fy,4),(cx,fy,4),(cx,py,1)]:
            via=expected.create_cell('via_stack','SG13_dev',dict(b_layer='TopMetal1',t_layer='TopMetal2',vn_columns=2,vn_rows=1,vt1_columns=2,vt1_rows=1,vt2_columns=4,vt2_rows=ny))
            assert via is not None and not via.is_empty()
            box=via.dbbox()
            dx=round((vx-box.center().x)/.005)*.005;dy=round((vy-box.center().y)/.005)*.005
            t.insert(pya.DCellInstArray(via.cell_index(),pya.DTrans(float(dx),float(dy))))
        targets.append(tag);cuts.append((gx,cx,fy))
    assert set(targets)=={'sa','sb','sc','sd','da','dc','s0','s1','x','y','vi'}
    addition={(expected.get_info(i).layer,expected.get_info(i).datatype):pya.Region(t.begin_shapes_rec(i)).merged()for i in expected.layer_indexes()}
    assert {k for k,v in addition.items()if not v.is_empty()}=={(126,0),(133,0),(134,0)}
    keys=set(before)|set(after)|set(addition)
    want={k:(before.get(k,pya.Region())+addition.get(k,pya.Region())).merged()for k in keys}
    def verdict(got):
        return all((got.get(k,pya.Region())^want.get(k,pya.Region())).is_empty()for k in keys|set(got))
    assert verdict(after),'Actual GDS differs from frozen parent plus independent native overlay'
    assert all((before.get(k,pya.Region())-after.get(k,pya.Region())).is_empty()for k in keys)
    rejected=[]
    fault=dict(after);gx,cx,fy=cuts[0]
    cut=pya.Region(pya.DBox((gx+cx)/2-1,fy-16,(gx+cx)/2+1,fy+16).to_itype(.001))
    fault[(134,0)]=after[(134,0)]-cut
    assert not verdict(fault);rejected.append('cut_actual_new_feed')
    fault=dict(after);fault[(8,0)]=after.get((8,0),pya.Region())+pya.Region(pya.Box(1000000,1000,1000100,1100))
    assert not verdict(fault);rejected.append('add_unrelated_native_device_layer')
    fault=dict(after);fault[(133,0)]=after[(133,0)]-addition[(133,0)]
    assert not verdict(fault);rejected.append('remove_actual_new_native_vias')
    result=dict(status='PASS_FROZEN_PARENT_PLUS_ELEVEN_NATIVE_AVDD_FEEDS_AND_THREE_FAULTS',
        immutable_passed_parent_geometry_reproduced=True,all_original_geometry_retained=True,all_layers_exact=True,reference_and_lef_byte_identical=True,
        original_devices=484,original_macros=16,feed_tags=targets,native_via_stacks=33,
        layers=[dict(layer=list(k),baseline_area_dbu2=before.get(k,pya.Region()).area(),candidate_area_dbu2=after.get(k,pya.Region()).area(),added_area_dbu2=(after.get(k,pya.Region())-before.get(k,pya.Region())).area())for k in sorted(keys)],
        rejected=rejected,baseline_gds_sha256=hashlib.sha256((baseline/(TOP+'.gds')).read_bytes()).hexdigest(),
        candidate_gds_sha256=hashlib.sha256((candidate/(TOP+'.gds')).read_bytes()).hexdigest(),
        full_phy_accepted=False,electrical_accepted=False,qualified_pex=False)
    output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],feed_tags=targets)))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for arg in ('baseline','passed','candidate','output'):p.add_argument('--'+arg,type=Path,required=True)
    a=p.parse_args();run(a.baseline,a.passed,a.candidate,a.output)
