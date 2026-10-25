#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Place all64 native drivers and attempt real, obstacle-checked core handoffs.
This is a physical candidate, not LVS, RC, electrical or full-PHY acceptance.
"""
import json,re,sys
from pathlib import Path
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
TOP='nssoc_tx_full32_raw64_handoff_candidate_v1'
def main(out):
 import pya
 pd=ROOT/'pdk/libs.tech/klayout/python'
 sys.path[:0]=[str(pd),str(pd/'pycell4klayout-api/source/python')]
 import sg13g2_pycell_lib
 core=out/'core/layout';driver=out/'driver/inputs/tx-input-driver-localpins/cloud-tx-input-driver-localpins/base'
 cm=json.loads((core/'result.json').read_text());dm=json.loads((driver/'result.json').read_text())
 cg=next(core.glob('*.gds'));dg=driver/'layout.gds'
 assert sha(cg)=='d202185d3691cd7778b8040492bab73492f44a1cfb0896c5f0b8f31350e6bdff'
 assert sha(dg)=='6f7a7cf92c1dc25a259acdbff779c7cce841128991abb780e13478aa84b4eb62'
 C=pya.Layout();C.read(str(cg));D=pya.Layout();D.read(str(dg))
 ct=C.cell(cg.stem);dt=D.cell('nssoc_tx_input_driver_v7_physical_localpins_v1')
 assert ct is not None and dt is not None and C.dbu==D.dbu==.001
 L=pya.Layout();L.dbu=.001
 c=L.create_cell('native_core');c.copy_tree(ct)
 d=L.create_cell('native_driver');d.copy_tree(dt)
 T=L.create_cell(TOP);cshift=pya.Trans(600000,0);T.insert(pya.CellInstArray(c.cell_index(),cshift))
 def rect(s):
  v=list(map(float,re.findall(r'-?\d+(?:\.\d+)?',s)));assert len(v)==4
  return pya.DBox(*v).to_itype(L.dbu)
 def allregions(l,t):
  return {(l.get_info(i).layer,l.get_info(i).datatype):pya.Region(t.begin_shapes_rec(i)).merged()
   for i in l.layer_indexes() if not pya.Region(t.begin_shapes_rec(i)).is_empty()}
 def equal(a,b):
  assert a.keys()==b.keys()
  for k in a:assert (a[k]^b[k]).is_empty(),('Native geometry changed',k)
 equal(allregions(C,ct),allregions(L,c));equal(allregions(D,dt),allregions(L,d))
 corepins={n:rect(v).transformed(cshift)for n,v in cm['ports'].items()}
 dp={n:rect(v)for n,v in dm['ports'].items()};assert set(dp)=={'din','dout','avdd','dvdd','avss','sub'}
 names={f'd{i}{p}'for i in range(32)for p in ('p','n')}
 assert names<=set(corepins)
 groups={}
 for n in names:groups.setdefault(int(n[1:-1])%16,[]).append(n)
 placements=[];bboxes=[];bound={}
 for k,ns in sorted(groups.items(),key=lambda kv:min(corepins[n].bottom for n in kv[1])):
  ns.sort(key=lambda n:corepins[n].bottom);assert len(ns)==4
  y0=min(corepins[n].center().y for n in ns)-250000
  for j,n in enumerate(ns):
   tr=pya.Trans(40000,y0+130000*j)
   bb=d.bbox().transformed(tr)
   assert not bb.overlaps(c.bbox().transformed(cshift))
   assert all(not bb.overlaps(old)for old in bboxes)
   bboxes.append(bb);T.insert(pya.CellInstArray(d.cell_index(),tr))
   bound[n]={pin:r.transformed(tr)for pin,r in dp.items()}
   placements.append(dict(net=n,transform=str(tr),bbox_dbu=str(bb),
    pins_dbu={pin:str(r)for pin,r in bound[n].items()},core_pin_dbu=str(corepins[n])))
 assert len(placements)==64 and sum(1 for _ in T.each_inst())==65
 dest=out/'candidate';dest.mkdir()
 L.write(str(dest/'placed.gds'))
 original=allregions(L,T)
 metals=(67,126,134);flat={m:pya.Region(T.begin_shapes_rec(L.layer(m,0))).merged()for m in metals}
 def component(region,pin):
  found=list(region.interacting(pya.Region(pin)).each());assert len(found)==1,('Ambiguous real pin conductor',str(pin),len(found))
  result=pya.Region(found[0]);assert (pya.Region(pin)-result).is_empty()
  return result
 def native_via(bottom,top,x,y):
  cell=L.create_cell('via_stack','SG13_dev',dict(b_layer=bottom,t_layer=top,vn_columns=1,vn_rows=1,vt1_columns=1,vt1_rows=1,vt2_columns=1,vt2_rows=1))
  assert cell is not None and not cell.is_empty()
  # Native via_stack origin is checked from its actual upper cut, not bbox.
  cut_layer=133 if top=='TopMetal2' else 125
  cuts=pya.Region(cell.begin_shapes_rec(L.layer(cut_layer,0))).merged()
  assert not cuts.is_empty()
  q=cuts.bbox().center();tr=pya.Trans(x-q.x,y-q.y)
  regs=allregions(L,cell)
  assert all(dt==0 for layer,dt in regs),('Unexpected native via annotations',list(regs))
  return {layer:r.transformed(tr)for (layer,dt),r in regs.items()}
 def wire(x0,y0,x1,y1):
  assert x0==x1 or y0==y1
  return pya.Region(pya.Box(min(x0,x1)-1600,min(y0,y1)-1600,max(x0,x1)+1600,max(y0,y1)+1600))
 prior={m:pya.Region()for m in metals};routes=[];blocked=[]
 parent={}
 clearance=1645
 for row in sorted(placements,key=lambda v:corepins[v['net']].bottom):
  n=row['net'];s=bound[n]['dout'].center();t=corepins[n].center()
  allowed={67:component(flat[67],bound[n]['dout']),126:pya.Region(),134:component(flat[134],corepins[n])}
  chosen=None;best=None
  for x in range(380000,570001,10000):
   candidate={67:pya.Region(),126:wire(x,s.y,x,t.y),134:wire(s.x,s.y,x,s.y)+wire(x,t.y,t.x,t.y)}
   for bottom,top,qx,qy in [('Metal5','TopMetal2',s.x,s.y),('TopMetal1','TopMetal2',x,s.y),('TopMetal1','TopMetal2',x,t.y)]:
    for layer,r in native_via(bottom,top,qx,qy).items():candidate[layer]=candidate.get(layer,pya.Region())+r
   collisions={}
   for m in metals:
    foreign=(flat[m]-allowed[m])+prior[m]
    bad=candidate[m].sized(clearance)&foreign
    if not bad.is_empty():collisions[str(m)]=dict(area_dbu2=bad.area(),bbox_dbu=str(bad.bbox()),polygons=[str(p)for p in list(bad.each())[:6]])
   if not collisions:chosen=(x,candidate);break
   score=sum(v['area_dbu2']for v in collisions.values())
   if best is None or score<best['score']:best=dict(trunk_x_dbu=x,score=score,collisions=collisions)
  if chosen is None:
   blocked.append(dict(net=n,source_dbu=str(s),destination_dbu=str(t),best=best));continue
  x,candidate=chosen
  for layer,r in candidate.items():
   T.shapes(L.layer(layer,0)).insert(r)
   parent[layer]=parent.get(layer,pya.Region())+r
  for m in metals:prior[m]+=candidate[m]
  routes.append(dict(net=n,source_dbu=str(s),destination_dbu=str(t),trunk_x_dbu=x,
   centerline_length_um=(abs(x-s.x)+abs(s.y-t.y)+abs(t.x-x))*.001,
   real_via_stacks=3,metal_layers=sorted(candidate),foreign_clearance_dbu=clearance))
 assert len(routes)+len(blocked)==64 and {r['net']for r in routes+blocked}==names
 L.write(str(dest/'handoffs.gds'))
 # Reopen the actual serialized hierarchy; every native material shape must remain.
 R=pya.Layout();R.read(str(dest/'handoffs.gds'));U=R.cell(TOP)
 actual=allregions(R,U);expected={k:v.dup()for k,v in original.items()}
 for layer,region in parent.items():expected[(layer,0)]=expected.get((layer,0),pya.Region())+region
 equal(expected,actual)
 inst=list(U.each_inst());assert len(inst)==65
 assert sorted(str(i.trans)for i in inst if i.cell.name=='native_driver')==sorted(v['transform']for v in placements)
 # Independent physical endpoints must retain a one-to-one binding by named pin
 # position; a swapped signal mapping is rejected even when all geometry exists.
 def check_binding(rows):
  assert len(rows)==64 and {r['net']for r in rows}==names
  for r in rows:
   assert r['core_pin_dbu']==str(corepins[r['net']])
   assert r['pins_dbu']['dout']==str(bound[r['net']]['dout'])
 controls=[]
 bad=[dict(r)for r in placements];bad[0]['core_pin_dbu'],bad[1]['core_pin_dbu']=bad[1]['core_pin_dbu'],bad[0]['core_pin_dbu']
 for name,rows in [('missing_driver',placements[:-1]),('swapped_core_inputs',bad)]:
  try:check_binding(rows)
  except AssertionError:controls.append(dict(name=name,rejected=True))
  else:raise AssertionError('Accepted '+name)
 check_binding(placements)
 if parent:
  fault={k:v.dup()for k,v in actual.items()}
  # Remove only new parent TopMetal1 conductors, without touching native children.
  fault[(126,0)]-=parent[126]
  try:equal(expected,fault)
  except AssertionError:controls.append(dict(name='missing_parent_handoff_metal',rejected=True))
  else:raise AssertionError('Missing parent route accepted')
 result=dict(status='CONSTRUCTED_NATIVE_RAW64_PLACEMENT_AND_HANDOFF_CANDIDATE_NOT_PHYSICAL_OR_ELECTRICAL_ACCEPTANCE',
  original_core_gds_sha256=sha(cg),original_driver_gds_sha256=sha(dg),core_devices=1674,driver_instances=64,driver_raw_devices=6400,
  reference_total_devices=8074,placements=placements,routes=routes,blocked=blocked,placed_count=64,routed_count=len(routes),blocked_count=len(blocked),
  original_native_geometry_preserved=True,serialized_gds_verified=True,controls=controls,all_handoffs_routed=len(routes)==64,
  power_connections_routed=False,full_native_drc_lvs_passed=False,fresh_parent_rc_extracted=False,electrical_accepted=False,
  qualified_pex=False,full_phy_accepted=False,main_chip_integrated=False,
  scope='Actual native children and candidate metal/via geometry only. Geometry spacing screen does not replace native DRC/LVS. All four power/body nets per driver still need routing. Fresh full-parent RC and original fullwave tests are required.',
  outputs={p.name:sha(p)for p in dest.iterdir()if p.is_file()})
 (out/'handoff-result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main(Path(sys.argv[1]).resolve())
