#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Overlay verified XOR collector/supply paths without altering native devices."""
import argparse,json,re,sys
from pathlib import Path
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
TOP='nssoc_cdr_pd484_localbus_v12'
ALLOWED={(8,0),(10,0),(19,0),(29,0),(30,0),(49,0),(50,0),(66,0),(67,0)}
def rect(text):
 q=list(map(float,re.findall(r'-?\d+(?:\.\d+)?',text)));assert len(q)==4;return q
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
 child=json.loads((out/'inputs/xor/layout/result.json').read_text())
 assert child['expected_native_devices']==59 and len(child['core_devices'])==27
 routes=child['routes'];nets=sorted({r['net']for r in routes});assert {'n_42','n_46','avdd'}<=set(nets)
 devices=json.loads((out/'capture/source/wire/device-locations01.json').read_text())['devices']
 wire=pya.LayoutToNetlist();wire.read(str(out/'capture/source/wire/native05/wires.l2n'))
 overlay=L.create_cell('nssoc_cdr_xor_collector_access_v15')
 plan=[];buses=[];stitches=[];via_groups=[];translation={}
 def via(lo,hi,x,y,cols,rows,tag,net):
  # Keep every old cut at its measured coordinate. Add only missing native
  # single-cut stacks; native multi-cut PCells need not share the old pitch.
  cut_layer={'Metal3':29,'Metal4':49,'Metal5':66}[hi]
  old_count=4 if hi=='Metal3'else 2;half=.9 if hi=='Metal3'else .6
  window=pya.DBox(x-half,y-.2,x+half,y+.2).to_itype(L.dbu)
  oldcuts=[p.bbox()for p in before[(cut_layer,0)].interacting(pya.Region(window)).each()]
  assert len(oldcuts)==old_count and all(v.width()==v.height()==190 for v in oldcuts)
  ys={v.center().y for v in oldcuts};assert len(ys)==1 and rows%2==1
  cy=next(iter(ys));original_xs=sorted(v.center().x for v in oldcuts)
  xs=list(original_xs)
  while len(xs)<cols:xs=[xs[0]-410,*xs,xs[-1]+410]
  assert len(xs)==cols
  old_positions={(v.center().x,v.center().y)for v in oldcuts}
  desired={(xx,cy+dy*410)for xx in xs for dy in range(-(rows//2),rows//2+1)}
  assert old_positions<=desired
  added=sorted(desired-old_positions)
  c=L.create_cell('via_stack','SG13_dev',dict(b_layer=lo,t_layer=hi,vn_columns=1,vn_rows=1))
  assert c is not None and not c.is_empty()
  cuts=list(pya.Region(c.begin_shapes_rec(L.layer(cut_layer,0))).merged().each())
  assert len(cuts)==1 and cuts[0].bbox().width()==cuts[0].bbox().height()==190
  center=cuts[0].bbox().center()
  intermediate=[]
  for xx,yy in added:
   ox,oy=xx-center.x,yy-center.y;assert ox%5==oy%5==0
   tr=pya.DTrans(ox*L.dbu,oy*L.dbu)
   overlay.insert(pya.DCellInstArray(c.cell_index(),tr))
   if lo=='Metal1':
    intermediate.extend(p.bbox().transformed(pya.Trans(ox,oy))for p in pya.Region(c.begin_shapes_rec(L.layer(10,0))).merged().each())
   stitches.append(dict(macro=tag,net=net,bottom=lo,top=hi,columns=1,rows=1,
     reference_cut_layer=cut_layer,target_cut_center_dbu=[xx,yy],bbox_um=str(c.dbbox().transformed(tr)),translation_dbu=[ox,oy]))
  if lo=='Metal1':
   for oldcut in oldcuts:
    original_net=wire.probe_net(wire.layer_by_name('gds_10'),oldcut.center())
    assert original_net is not None and original_net.cluster_id==component
   assert intermediate
   landing=pya.Box(min(q.left for q in intermediate),min(q.bottom for q in intermediate),max(q.right for q in intermediate),max(q.top for q in intermediate))
   overlay.shapes(L.layer(10,0)).insert(landing)
  via_groups.append(dict(intermediate_m2_landing_um=str(landing.to_dtype(L.dbu))if lo=='Metal1'else None,macro=tag,net=net,bottom=lo,top=hi,old_cut_boxes=[str(v)for v in oldcuts],
   old_horizontal_pitch_dbu=[b-a for a,b in zip(original_xs,original_xs[1:])],
   retained_cut_count=len(oldcuts),added_native_single_cut_stacks=len(added),
   aggregate_columns=cols,aggregate_rows=rows,added_cut_center_dbu=[list(p)for p in added],
   original_cut_geometry_untouched=True))
 def probe(metal,x,y):
  n=wire.probe_net(wire.layer_by_name('gds_'+str(metal)),pya.DPoint(x,y).to_itype(L.dbu))
  assert n is not None,('No original wire at planned witness',metal,x,y)
  return n.cluster_id
 for tag in ('x','y'):
  p=old['placements'][tag];assert p['kind']=='xor'
  b=pya.DBox(*rect(p['bbox_um']));px,py=b.left,b.bottom
  first=child['core_devices'][0];assert first['model']=='rppd'and first['placement_um']==[30,30]
  candidates=[]
  for d in devices:
   if d['model']!='rppd':continue
   box=pya.DBox(*rect(d['pcell']['bbox']))
   if (box & b)!=box:continue
   dt=pya.DCplxTrans.from_s(d['pcell']['transform'])
   assert dt.mag==1 and dt.angle==0 and not dt.is_mirror()
   if abs(dt.disp.x-px-30)<1e-8:candidates.append((d,dt))
  assert len(candidates)==1
  witness,dt=candidates[0];dy=dt.disp.y-py-30
  translation[tag]=dict(parent_origin_um=[px,py],leaf_normalization_dy_um=dy,actual_first_resistor=witness)
  for net in ('n_42','n_46','avdd'):
   selected=[r for r in routes if r['net']==net]
   assert len(selected)==(2 if net=='avdd'else 8),(tag,net,len(selected))
   by=py+dy+150+nets.index(net)*6
   component=probe(67,px+5,by);xs=[]
   for row in selected:
    assert row['native_layer']==1
    pin=pya.DBox(*rect(row['pin']))
    x=px+round(pin.center().x/.005)*.005
    lane=px+row['escape'][0];y=py+dy+row['escape'][1]
    assert abs(y-(py+dy+pin.center().y))<=.04000001
    witnesses=[(8,x,y),(30,(lane+x)/2,y),(50,lane,(y+by)/2),(67,lane,by)]
    assert all(probe(m,xx,yy)==component for m,xx,yy in witnesses),('Original path conductor mismatch',tag,net,row)
    bridge=pya.DBox(lane-1.0,y-.6,x+1.8,y+.6)
    column=pya.DBox(lane-1.2,min(y-.2,by-1.0),lane+1.2,max(y+.2,by+1.0))
    overlay.shapes(L.layer(30,0)).insert(bridge)
    overlay.shapes(L.layer(50,0)).insert(column)
    via('Metal1','Metal3',x,y,8,1,tag,net)
    via('Metal3','Metal4',lane,y,4,1,tag,net)
    via('Metal4','Metal5',lane,by,4,3,tag,net)
    xs.append(lane)
    plan.append(dict(macro=tag,net=net,device=row['device'],native_wire_component=component,
      native_pin_um=str(pin.transformed(pya.DTrans(px,py+dy))),witnesses=witnesses,
      bridge_m3_um=str(bridge),column_m4_um=str(column),bus_y_um=by))
   bus=pya.DBox(px,by-2,max(xs)+1,by+2)
   overlay.shapes(L.layer(67,0)).insert(bus)
   buses.append(dict(macro=tag,net=net,native_wire_component=component,box_um=str(bus)))
 assert len(plan)==36 and len(buses)==6 and len(via_groups)==108 and len(stitches)==576
 assert sum(v['intermediate_m2_landing_um']is not None for v in via_groups)==36
 assert len({v['native_wire_component']for v in buses})==5
 assert len({v['native_wire_component']for v in buses if v['net']=='avdd'})==1
 top.insert(pya.DCellInstArray(overlay.cell_index(),pya.DTrans()));assert top.dbbox()==oldbox
 addition={(L.get_info(i).layer,L.get_info(i).datatype):pya.Region(overlay.begin_shapes_rec(i)).merged()for i in L.layer_indexes()}
 after={(L.get_info(i).layer,L.get_info(i).datatype):pya.Region(top.begin_shapes_rec(i)).merged()for i in L.layer_indexes()}
 assert {k for k,v in addition.items()if not v.is_empty()}<=ALLOWED
 keys=set(before)|set(after)|set(addition)
 expected={k:(before.get(k,pya.Region())+addition.get(k,pya.Region())).merged()for k in keys}
 def verdict(got):return all((got.get(k,pya.Region())^expected.get(k,pya.Region())).is_empty()for k in keys|set(got))
 assert verdict(after)and all((before.get(k,pya.Region())-after.get(k,pya.Region())).is_empty()for k in keys)
 # Preserve actual old cut positions and check the union of all original and
 # additional Via3/Via4 cuts before the unchanged native physical gates.
 cut_lattice={}
 for metal in (49,66):
  region=after[(metal,0)];count=0
  for poly in region.each():
   b=poly.bbox()
   assert b.width()==b.height()==190 and poly.area()==190*190,('Non-native merged via cut',metal,str(poly))
   nearby=region.interacting(pya.Region(pya.Box(b.left-220,b.bottom-220,b.right+220,b.top+220)))
   for other in nearby.each():
    q=other.bbox()
    if q==b:continue
    dx=max(b.left-q.right,q.left-b.right,0);dy=max(b.bottom-q.top,q.bottom-b.top,0)
    assert dx*dx+dy*dy>=220*220,('Actual via cuts violate native0.22um Euclidean spacing',metal,str(b),str(q))
   count+=1
  cut_lattice[str(metal)]=dict(actual_cuts=count,native_width_nm=190,minimum_euclidean_spacing_nm=220)
 faults=[]
 b=pya.DBox(*rect(buses[0]['box_um']))
 # Remove only a newly added edge of the widened bus, beyond the original0.6um half width.
 cut=pya.Region(pya.DBox(b.left+10,b.bottom+.1,b.left+11,b.bottom+.5).to_itype(L.dbu))
 bad=dict(after);bad[(67,0)]=after[(67,0)]-cut
 assert not verdict(bad);faults.append('cut_actual_new_collector_bus_edge')
 added=addition[(66,0)]-before.get((66,0),pya.Region());assert not added.is_empty()
 bad=dict(after);bad[(66,0)]=after[(66,0)]-added
 assert not verdict(bad);faults.append('remove_actual_added_collector_vias')
 bad=dict(after);bad[(5,0)]=after.get((5,0),pya.Region())+pya.Region(pya.Box(1,1,101,101))
 assert not verdict(bad);faults.append('unrelated_gate_geometry_added')
 opt=pya.SaveLayoutOptions();opt.select_cell(top.cell_index());L.write(str(dest/(TOP+'.gds')),opt)
 for name in ('schematic.cir',TOP+'.lef'):(dest/name).write_bytes((baseline/name).read_bytes())
 check=pya.Layout();check.read(str(dest/(TOP+'.gds')))
 saved={(check.get_info(i).layer,check.get_info(i).datatype):pya.Region(check.cell(TOP).begin_shapes_rec(i)).merged()for i in check.layer_indexes()}
 assert check.dbu==.001 and verdict(saved)
 proof=dict(status='PASS_NATIVE_XOR_COLLECTOR_OVERLAY_REQUIRES_DRC_LVS_AND_FRESH_RC',
   original_devices=484,xor_count=2,route_accesses=len(plan),bus_count=len(buses),native_via_stacks=len(stitches),via_group_count=len(via_groups),
   original_geometry_retained=True,all_layers_exact=True,serialized_gds_checked=True,
   reference_and_lef_byte_identical=True,via_cut_lattice=cut_lattice,plan=plan,buses=buses,stitches=stitches,via_groups=via_groups,translations=translation,rejected=faults,
   source_gds_sha256=sha(baseline/(TOP+'.gds')),candidate_gds_sha256=sha(dest/(TOP+'.gds')),
   electrical_accepted=False,qualified_pex=False,full_phy_accepted=False)
 (out/'geometry-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
 d=dict(old);d.update(status='GENERATED_XOR_COLLECTOR_OVERLAY_REQUIRES_NATIVE_DRC_LVS_RC_AND_LOADED_GATES',
   xor_collector_access=proof,original_generation_inputs=old['inputs'],
   inputs={str(q):sha(q)for q in [Path(__file__),baseline/(TOP+'.gds'),baseline/'schematic.cir',baseline/(TOP+'.lef'),baseline/'result.json',
     out/'inputs/xor/layout/result.json',out/'capture/source/wire/device-locations01.json',out/'capture/source/wire/native05/wires.l2n']})
 d['outputs']={q.name:sha(q)for q in dest.iterdir()if q.is_file()}
 (dest/'result.json').write_text(json.dumps(d,indent=2)+'\n');print(proof['status'])
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();generate(a.out.resolve())
