#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Actual same-net driver power feeds; preserve intrinsic geometry and ports."""
import copy,json,os,sys
from pathlib import Path
from run_cloud_tx_layout_repair import sha
TOP='nssoc_tx_output8088_parent_v1'
METALS=(8,10,30,50,67,126,134)
VIAS=(19,29,49,66,125,133)
def main(out):
 import pya
 root=Path(__file__).resolve().parents[1]
 pd=root/'pdk/libs.tech/klayout/python'
 sys.path[:0]=[str(pd),str(pd/'pycell4klayout-api/source/python')]
 import sg13g2_pycell_lib
 L=pya.Layout();L.read(str(out/'native/source/layout/layout.gds'));T=L.cell(TOP);assert L.dbu==.001 and T is not None
 native=pya.LayoutVsSchematic();native.read(str(out/'native/source/flat_lvs/result.lvsdb'))
 c=native.netlist().circuit_by_name(TOP);devices={d.id():d for d in c.each_device()};assert len(devices)==8088
 geom=json.loads((out/'native/native01/result.json').read_text())
 mapping={int(k):v for k,v in geom['native_layer_mapping'].items()}
 anchors=json.loads((out/'anchors/composed/intrinsic/source/anchors.json').read_text())
 bypoint={(a['metal'],*a['point_dbu']):a for a in anchors['anchors']}
 ar={a['label']:a for a in anchors['anchors']}
 rows=anchors['rows'];hand=json.loads((out/'parent/core/source/handoff-result.json').read_text())
 assert hand['routed_count']==64 and len(hand['placements'])==64
 assert set(p.name()for p in c.each_pin())=={p['name']for p in anchors['public']}
 def regions(layout,cell):
  return {(layout.get_info(i).layer,layout.get_info(i).datatype):pya.Region(cell.begin_shapes_rec(i)).merged()
   for i in layout.layer_indexes()if not pya.Region(cell.begin_shapes_rec(i)).is_empty()}
 original=regions(L,T);flat={m:original.get((m,0),pya.Region())for m in (*METALS,*VIAS)}
 def net_at(m,p):
  n=native.probe_net(native.layer_by_index(mapping[m]),p);assert n is not None
  return n
 def same(m,n):return native.shapes_of_net(n,native.layer_by_index(mapping[m]),True).merged()
 rails={}
 for rail,label in [('avdd','A11588'),('avss','A11583')]:
  a=ar[label];point=pya.Point(*a['point_dbu'])
  source_rows=[r for r in anchors['rows']if r.get('reference_label')==label]
  assert len(source_rows)==1 and source_rows[0]['model']=='rppd'
  placements=[p for p in hand['placements']if pya.Box.from_s(p['bbox_dbu']).contains(point)]
  assert len(placements)==1
  tr=pya.Trans.from_s(placements[0]['transform']);assert tr.angle==0 and not tr.is_mirror()
  net=net_at(8,point)
  rails[rail]=dict(local=point-tr.disp,cluster=net.cluster_id,term=source_rows[0]['terminal'],same={m:same(m,net)for m in METALS})
 assert rails['avdd']['cluster']!=rails['avss']['cluster']
 additions={};routes=[];blocked=[]
 def native_via(lo,hi,x,y,columns=3,rows=1):
  cell=L.create_cell('via_stack','SG13_dev',dict(b_layer='Metal'+str(lo),t_layer='Metal'+str(hi),
   vn_columns=columns,vn_rows=rows,vt1_columns=columns,vt1_rows=rows,vt2_columns=columns,vt2_rows=rows))
  assert cell is not None and not cell.is_empty()
  cuts={1:19,2:29,3:49,4:66}
  center=pya.Region(cell.begin_shapes_rec(L.layer(cuts[lo],0))).bbox().center()
  tr=pya.Trans(x-center.x,y-center.y)
  r=regions(L,cell);assert all(dt==0 for _,dt in r)
  return {m:v.transformed(tr)for(m,dt),v in r.items()}
 def line(a,b,half):
  assert a.x==b.x or a.y==b.y
  return pya.Region(pya.Box(min(a.x,b.x)-half,min(a.y,b.y)-half,max(a.x,b.x)+half,max(a.y,b.y)+half))
 def add(target,shape):
  for m,r in shape.items():target[m]=target.get(m,pya.Region())+r
 def obstruction(candidate,rail):
  bad={}
  for m in METALS:
   # Independent native ownership at the original endpoints does not permit
   # touching any other net elsewhere along a new route.
   foreign=flat[m]-rails[rail]['same'][m]
   foreign+=additions.get((m,'avss'if rail=='avdd'else'avdd'),pya.Region())
   overlap=candidate.get(m,pya.Region()).sized(400)&foreign
   if not overlap.is_empty():bad[str(m)]=dict(area=overlap.area(),bbox=str(overlap.bbox()))
  for m in VIAS:
   # Retain the exact existing central V1 cut; reject added cut interference
   # with all other native cuts. The native deck remains authoritative.
   new=(candidate.get(m,pya.Region())-flat[m]).merged()
   overlap=new.sized(250)&flat[m]
   if not overlap.is_empty():bad['cut'+str(m)]=dict(area=overlap.area(),bbox=str(overlap.bbox()))
  return bad
 for placement in hand['placements']:
  tr=pya.Trans.from_s(placement['transform']);assert tr.angle==0 and not tr.is_mirror()
  for rail in ('avdd','avss'):
   q=rails[rail]['local']+tr.disp
   anchor=bypoint[(8,q.x,q.y)]
   row=[v for v in rows if v.get('reference_label')==anchor['label']]
   assert len(row)==1 and row[0]['model']=='rppd'and row[0]['terminal']==rails[rail]['term']
   assert net_at(8,q).cluster_id==rails[rail]['cluster']
   public=pya.Box.from_s(placement['pins_dbu'][rail]);y=public.center().y
   # Power128 parent branches already feed the original M5 pin. Select the
   # actual same-net point above this device, never a different row's rail.
   chosen=None;attempts=[]
   for half in (3000,1600):
    for shift in (2000,-2000,3000,-3000,4000,-4000,6000,-6000):
     x=q.x+shift;landing=pya.Point(x,y)
     probe=native.probe_net(native.layer_by_index(mapping[67]),landing)
     if probe is None or probe.cluster_id!=rails[rail]['cluster']:continue
     candidate={}
     # The three-column V1 is centred on the original one-cut access.
     add(candidate,native_via(1,2,q.x,q.y))
     assert(candidate[8]-rails[rail]['same'][8]).is_empty(),'Intrinsic M1 pin would be enlarged'
     assert not(candidate[19]&flat[19]).is_empty()
     add(candidate,native_via(2,4,x,q.y))
     candidate[10]=candidate.get(10,pya.Region())+line(q,pya.Point(x,q.y),600)
     candidate[50]=candidate.get(50,pya.Region())+line(pya.Point(x,q.y),landing,half)
     add(candidate,native_via(4,5,x,y,columns=3,rows=3))
     bad=obstruction(candidate,rail)
     if not bad:chosen=(candidate,landing,half,shift);break
     attempts.append(dict(shift=shift,half=half,obstructions=bad))
    if chosen:break
   if chosen is None:
    blocked.append(dict(net=placement['net'],rail=rail,anchor=anchor,attempts=attempts));continue
   candidate,landing,half,shift=chosen
   for m,r in candidate.items():T.shapes(L.layer(m,0)).insert(r);additions[(m,rail)]=additions.get((m,rail),pya.Region())+r
   routes.append(dict(driver=placement['net'],rail=rail,anchor=anchor,terminal=row[0],landing_dbu=[landing.x,landing.y],
    vertical_width_um=2*half*.001,lateral_shift_dbu=shift,layers=sorted(candidate)))
  (out/'candidate-progress.json').write_text(json.dumps(dict(routes=routes,blocked=blocked),indent=2)+'\n')
 assert not blocked and len(routes)==128,('No safe actual feed for all128 driver rail terminals',len(routes),len(blocked))
 dest=out/'layout';dest.mkdir();L.write(str(dest/'layout.gds'))
 (dest/'schematic.cir').write_bytes((out/'parent/layout/schematic.cir').read_bytes())
 R=pya.Layout();R.read(str(dest/'layout.gds'));U=R.cell(TOP);actual=regions(R,U)
 expected={k:v.dup()for k,v in original.items()}
 for (m,rail),r in additions.items():expected[(m,0)]=expected.get((m,0),pya.Region())+r
 def exact(observed):
  assert set(observed)==set(expected)
  for k,v in expected.items():assert(v^observed[k]).is_empty(),('Unexpected geometry',k)
 exact(actual)
 faults=[];bad={k:v.dup()for k,v in actual.items()}
 # Removing a parallel added route need not break LVS. Independently reject
 # it with exact serialized geometry, rather than claim an LVS open.
 delta=actual[(50,0)]-original[(50,0)];assert not delta.is_empty()
 bad[(50,0)]-=pya.Region(next(delta.each()))
 try:exact(bad)
 except AssertionError:faults.append(dict(fault='missing_parallel_route',rejected=True))
 else:raise AssertionError('Missing route accepted')
 assert all((actual[k]^r).is_empty()for k,r in original.items()if k[1]!=0 or k[0]not in (*METALS,*VIAS))
 assert all((r-actual[k]).is_empty()for k,r in original.items())
 f=out/'faults';f.mkdir()
 # Actual source-access open: remove every V1 at one resistor, including its
 # old single cut. All parallel upper routes remain, so the original device
 # terminal must really disconnect in fresh native LVS.
 R=pya.Layout();R.read(str(dest/'layout.gds'));U=R.cell(TOP);U.flatten(True)
 q=pya.Point(*routes[0]['anchor']['point_dbu']);li=R.layer(19,0);cut=pya.Region(pya.Box(q.x-1900,q.y-180,q.x+1900,q.y+180))
 before=pya.Region(U.shapes(li));assert not(before&cut).is_empty()
 U.shapes(li).clear();U.shapes(li).insert(before-cut);R.write(str(f/'source_access_open.gds'))
 R=pya.Layout();R.read(str(dest/'layout.gds'));U=R.cell(TOP)
 p0=routes[0];p1=routes[1];a=pya.Point(*p0['landing_dbu']);b=pya.Point(*p1['landing_dbu'])
 short=line(a,pya.Point(a.x,b.y),500)+line(pya.Point(a.x,b.y),b,500)
 U.shapes(R.layer(67,0)).insert(short);R.write(str(f/'body_supply_short.gds'))
 text=(dest/'schematic.cir').read_text()
 wrong=text.replace('sg13_hv_nmos w=1u l=.45u','sg13_hv_nmos w=0.9u l=.45u',1);assert wrong!=text
 (f/'wrong_width.cir').write_text(wrong)
 R=pya.Layout();R.read(str(dest/'layout.gds'));U=R.cell(TOP)
 U.shapes(R.layer(67,0)).insert(pya.Box(-230001,-50000,-228001,-48000));R.write(str(f/'offgrid.gds'))
 result=dict(status='GENERATED_ACTUAL128_DRIVER_PIN_FEEDS_REQUIRES_NATIVE_DRC_LVS_FRESH_RC',source_gds_sha256=sha(out/'native/source/layout/layout.gds'),
  reference_devices=8088,route_count=len(routes),routes=routes,blocked=blocked,geometry_controls=faults,
  all_original_material_preserved=True,intrinsic_layers_and_all_port_shapes_unchanged=True,serialized_geometry_verified=True,
  full_phy_accepted=False,electrical_accepted=False,qualified_pex=False,no_new_simulation=True,
  scope='Parallel native metal/via feeds to64 original drivers. No device sizes, reference circuit, ports, source voltages or acceptance gates changed.')
 (out/'integration-result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main(Path(sys.argv[1]).resolve())
