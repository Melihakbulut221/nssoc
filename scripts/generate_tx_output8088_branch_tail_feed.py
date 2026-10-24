#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Parallel actual branch and tail feeds, preserving all original device geometry."""
import json,sys
from pathlib import Path
from run_cloud_tx_layout_repair import sha
TOP='nssoc_tx_output8088_parent_v1'
METALS=(8,10,30,50,67,126,134)
VIAS=(19,29,49,66,125,133)
def main(out):
 import pya
 root=Path(__file__).resolve().parents[1];pd=root/'pdk/libs.tech/klayout/python'
 sys.path[:0]=[str(pd),str(pd/'pycell4klayout-api/source/python')]
 import sg13g2_pycell_lib
 gds=out/'native/source/source/layout/layout.gds'
 L=pya.Layout();L.read(str(gds));T=L.cell(TOP);assert L.dbu==.001 and T is not None
 native=pya.LayoutVsSchematic();native.read(str(out/'native/source/source/flat_lvs/result.lvsdb'))
 c=native.netlist().circuit_by_name(TOP);devices={d.id():d for d in c.each_device()};assert len(devices)==8088
 geom=json.loads((out/'native/source/native01/result.json').read_text())
 mapping={int(k):v for k,v in geom['native_layer_mapping'].items()}
 anchors=json.loads((out/'anchors/intrinsic/source/anchors.json').read_text())
 refs={a['label']:a for a in anchors['anchors']};bypoint={(a['metal'],*a['point_dbu']):a for a in anchors['anchors']}
 rows=anchors['rows'];parent=json.loads((out/'parent/integration-result.json').read_text())
 assert parent['route_count']==128 and parent['intrinsic_layers_and_all_port_shapes_unchanged']
 assert set(p.name()for p in c.each_pin())=={p['name']for p in anchors['public']}
 def regions(layout,cell):
  return {(layout.get_info(i).layer,layout.get_info(i).datatype):pya.Region(cell.begin_shapes_rec(i)).merged()
   for i in layout.layer_indexes()if not pya.Region(cell.begin_shapes_rec(i)).is_empty()}
 original=regions(L,T);flat={m:original.get((m,0),pya.Region())for m in (*METALS,*VIAS)}
 def net_at(m,p):
  n=native.probe_net(native.layer_by_index(mapping[m]),p);assert n is not None
  return n
 rails={}
 for public in anchors['public']:
  if public['name'].lower()not in ('avdd','avss'):continue
  a=refs[public['reference_label']];n=net_at(a['metal'],pya.Point(*a['point_dbu']))
  same={m:native.shapes_of_net(n,native.layer_by_index(mapping[m]),True).merged()for m in METALS}
  rails[public['name'].lower()]=dict(cluster=n.cluster_id,same=same,foreign={m:flat[m]-same[m]for m in METALS})
 assert len(rails)==2 and rails['avdd']['cluster']!=rails['avss']['cluster']
 additions={};routes=[];blocked=[]
 def line(a,b,half):
  assert a.x==b.x or a.y==b.y
  return pya.Region(pya.Box(min(a.x,b.x)-half,min(a.y,b.y)-half,max(a.x,b.x)+half,max(a.y,b.y)+half))
 def add(dst,src):
  for m,v in src.items():dst[m]=dst.get(m,pya.Region())+v
 def via(lo,hi,x,y,columns=3,rows=3):
  names=['Metal1','Metal2','Metal3','Metal4','Metal5','TopMetal1','TopMetal2'];cuts=[19,29,49,66,125,133]
  v=L.create_cell('via_stack','SG13_dev',dict(b_layer=names[lo-1],t_layer=names[hi-1],
   vn_columns=columns,vn_rows=rows,vt1_columns=columns,vt1_rows=rows,vt2_columns=columns,vt2_rows=rows))
  assert v is not None and not v.is_empty()
  center=pya.Region(v.begin_shapes_rec(L.layer(cuts[lo-1],0))).bbox().center()
  tr=pya.Trans(x-center.x,y-center.y);r=regions(L,v);assert all(dt==0 for _,dt in r)
  return {m:s.transformed(tr)for(m,dt),s in r.items()}
 def obstruction(candidate,rail):
  bad={}
  for m in METALS:
   foreign=rails[rail]['foreign'][m].dup()+additions.get((m,'avss'if rail=='avdd'else'avdd'),pya.Region())
   overlap=candidate.get(m,pya.Region()).sized(2000 if m in (126,134)else 400)&foreign
   if not overlap.is_empty():bad[str(m)]=dict(area=overlap.area(),bbox=str(overlap.bbox()))
  for m in VIAS:
   new=(candidate.get(m,pya.Region())-flat[m]).merged()
   other=flat[m]-candidate.get(m,pya.Region())
   overlap=new.sized(420 if m in (125,133)else 290)&other
   if not overlap.is_empty():bad['cut'+str(m)]=dict(area=overlap.area(),bbox=str(overlap.bbox()))
  return bad
 def commit_shapes(candidate,rail):
  for m,v in candidate.items():
   T.shapes(L.layer(m,0)).insert(v)
   additions[(m,rail)]=additions.get((m,rail),pya.Region())+v
 for old in parent['routes']:
  rail=old['rail'];q=pya.Point(*old['anchor']['point_dbu']);a=bypoint[(8,q.x,q.y)]
  hits=[r for r in rows if r.get('reference_label')==a['label']]
  assert len(hits)==1 and hits[0]['model']=='rppd'and hits[0]['terminal']==old['terminal']['terminal']
  assert net_at(8,q).cluster_id==rails[rail]['cluster']
  end=pya.Point(*old['landing_dbu']);assert net_at(67,end).cluster_id==rails[rail]['cluster']
  chosen=None;attempts=[]
  for startx in (60000,70000,80000,90000,100000):
   start=pya.Point(startx,end.y)
   probe=native.probe_net(native.layer_by_index(mapping[67]),start)
   if probe is None or probe.cluster_id!=rails[rail]['cluster']:continue
   for half in (2000,1640):
    candidate={126:line(start,end,half)}
    add(candidate,via(5,6,start.x,start.y));add(candidate,via(5,6,end.x,end.y))
    assert(candidate[67]-rails[rail]['same'][67]).is_empty(),'M5 access pad leaves original same-net branch'
    bad=obstruction(candidate,rail)
    if not bad:chosen=(candidate,start,half);break
    attempts.append(dict(startx=startx,width=2*half,obstructions=bad))
   if chosen:break
  if chosen is None:blocked.append(dict(kind='driver',driver=old['driver'],rail=rail,attempts=attempts));break
  candidate,start,half=chosen;commit_shapes(candidate,rail)
  routes.append(dict(kind='driver',driver=old['driver'],rail=rail,anchor=a,terminal=hits[0],start_dbu=[start.x,start.y],
   landing_dbu=[end.x,end.y],width_um=2*half*.001,layers=sorted(candidate)))
  print('ACTUAL_BRANCH',old['driver'],rail,'routes',len(routes),flush=True)
 tail_boxes=[]
 if not blocked:
  for label in ('A0856','A0877'):
   old=refs[label];q=pya.Point(*old['point_dbu']);a=bypoint[(8,q.x,q.y)]
   hits=[r for r in rows if r.get('reference_label')==a['label']]
   assert len(hits)==1 and hits[0]['model'].lower()=='npn13g2'and hits[0]['terminal']=='E'
   rail='avss';same=rails[rail]['same'];assert net_at(8,q).cluster_id==rails[rail]['cluster']
   assert net_at(10,q).cluster_id==rails[rail]['cluster']
   bar=[p for p in same[10].each()if p.bbox().contains(q)];assert len(bar)==1
   bar=pya.Region(bar[0]);bb=bar.bbox();assert bb.width()==14800 and bb.height()==1555
   existing=flat[29]&bar&same[30]
   cuts=list(existing.each());assert cuts
   y=min((p.bbox().center().y for p in cuts),key=lambda v:abs(v-q.y))
   point=pya.Point(q.x,y);assert net_at(30,point).cluster_id==rails[rail]['cluster']
   slice=same[67]&pya.Region(pya.Box(bb.left,y-5,bb.right,y+5))
   landing_polys=list(slice.each());assert len(landing_polys)==1
   end=pya.Point(landing_polys[0].bbox().center().x,y);assert net_at(67,end).cluster_id==rails[rail]['cluster']
   candidate={67:line(point,end,600)};add(candidate,via(2,5,point.x,point.y,columns=3,rows=1))
   assert(candidate[10]-bar).is_empty()and(candidate[30]-same[30]).is_empty()
   bad=obstruction(candidate,rail)
   if bad:blocked.append(dict(kind='tail',label=label,obstructions=bad));break
   commit_shapes(candidate,rail);tail_boxes.append(str(bb))
   routes.append(dict(kind='tail',rail=rail,anchor=a,terminal=hits[0],start_dbu=[point.x,point.y],
    landing_dbu=[end.x,end.y],emitter_bar_dbu=str(bb),width_um=1.2,layers=sorted(candidate)))
   print('ACTUAL_TAIL',label,'routes',len(routes),flush=True)
 (out/'candidate-progress.json').write_text(json.dumps(dict(routes=routes,blocked=blocked),indent=2)+'\n')
 assert not blocked and len(routes)==130,('No safe actual branch/tail feed',len(routes),blocked)
 dest=out/'layout';dest.mkdir();L.write(str(dest/'layout.gds'))
 (dest/'schematic.cir').write_bytes((out/'parent/layout/schematic.cir').read_bytes())
 R=pya.Layout();R.read(str(dest/'layout.gds'));U=R.cell(TOP);actual=regions(R,U)
 expected={k:v.dup()for k,v in original.items()}
 for(m,rail),v in additions.items():expected[(m,0)]=expected.get((m,0),pya.Region())+v
 def exact(obs):
  assert set(obs)==set(expected)
  for k,v in expected.items():assert(v^obs[k]).is_empty(),('Unexpected serialized geometry',k)
 exact(actual)
 bad={k:v.dup()for k,v in actual.items()};delta=actual[(126,0)]-original[(126,0)];assert not delta.is_empty()
 bad[(126,0)]-=pya.Region(next(delta.each()))
 try:exact(bad)
 except AssertionError:controls=[dict(fault='missing_parallel_route',rejected=True)]
 else:raise AssertionError('Missing route accepted')
 assert all((v-actual[k]).is_empty()for k,v in original.items())
 assert all((actual[k]^v).is_empty()for k,v in original.items()if k[1]!=0 or k[0]not in(*METALS,*VIAS))
 assert(actual[(8,0)]^original[(8,0)]).is_empty()and(actual[(19,0)]^original[(19,0)]).is_empty()
 f=out/'faults';f.mkdir()
 def delete_v1(box,path):
  Q=pya.Layout();Q.read(str(dest/'layout.gds'));C=Q.cell(TOP);C.flatten(True);li=Q.layer(19,0)
  before=pya.Region(C.shapes(li));cut=pya.Region(box);assert not(before&cut).is_empty()
  C.shapes(li).clear();C.shapes(li).insert(before-cut);Q.write(str(path))
 q=pya.Point(*routes[0]['anchor']['point_dbu'])
 delete_v1(pya.Box(q.x-1900,q.y-180,q.x+1900,q.y+180),f/'source_access_open.gds')
 delete_v1(pya.Box.from_s(tail_boxes[0]),f/'tail_access_open.gds')
 Q=pya.Layout();Q.read(str(dest/'layout.gds'));C=Q.cell(TOP)
 a=pya.Point(*routes[0]['start_dbu']);b=pya.Point(*routes[1]['start_dbu'])
 C.shapes(Q.layer(126,0)).insert(line(a,pya.Point(a.x,b.y),1640)+line(pya.Point(a.x,b.y),b,1640));Q.write(str(f/'body_supply_short.gds'))
 text=(dest/'schematic.cir').read_text();wrong=text.replace('sg13_hv_nmos w=1u l=.45u','sg13_hv_nmos w=0.9u l=.45u',1);assert wrong!=text
 (f/'wrong_width.cir').write_text(wrong)
 Q=pya.Layout();Q.read(str(dest/'layout.gds'));C=Q.cell(TOP)
 C.shapes(Q.layer(67,0)).insert(pya.Box(-230001,-50000,-228001,-48000));Q.write(str(f/'offgrid.gds'))
 result=dict(status='GENERATED_ACTUAL128_BRANCH_AND2_TAIL_FEEDS_REQUIRES_NATIVE_DRC_LVS_FRESH_RC',
  source_gds_sha256=sha(gds),reference_devices=8088,route_count=130,driver_routes=128,tail_routes=2,routes=routes,blocked=blocked,
  geometry_controls=controls,all_original_material_preserved=True,intrinsic_layers_and_all_port_shapes_unchanged=True,
  original_m1_and_via1_unchanged=True,serialized_geometry_verified=True,full_phy_accepted=False,electrical_accepted=False,
  qualified_pex=False,no_new_simulation=True,scope='Actual parallel native metal/via routing only. No intrinsic device dimensions, ports, bias, clocks or engineering gates changed.')
 (out/'integration-result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main(Path(sys.argv[1]).resolve())
