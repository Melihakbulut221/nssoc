#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Widen actual output AVSS spans while retaining the core power128feed32 geometry."""
import json,sys
from pathlib import Path
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
TOP='nssoc_tx_output8088_parent_v1'
def main(out):
 import pya
 pd=ROOT/'pdk/libs.tech/klayout/python';sys.path[:0]=[str(pd),str(pd/'pycell4klayout-api/source/python')]
 import sg13g2_pycell_lib
 core=out/'core';leaf=out/'output';meta=json.loads((core/'power-result.json').read_text())
 C=pya.Layout();C.read(str(core/'layout/layout.gds'));ct=C.cell('nssoc_tx_full32_raw64_handoff_candidate_v1')
 D=pya.Layout();D.read(str(leaf/'layout/nssoc_tx_cml_layout.gds'));dt=D.cell('nssoc_tx_cml_layout')
 assert ct is not None and dt is not None and C.dbu==D.dbu==.001
 assert meta['reference_devices']==8074 and len(meta['external_ports'])==163
 L=pya.Layout();L.dbu=.001;T=L.create_cell(TOP);T.copy_tree(ct)
 output=L.create_cell('actual_output14');output.copy_tree(dt)
 def regions(layout,cell):
  return {(layout.get_info(i).layer,layout.get_info(i).datatype):pya.Region(cell.begin_shapes_rec(i)).merged()for i in layout.layer_indexes()if not pya.Region(cell.begin_shapes_rec(i)).is_empty()}
 def equal(a,b):
  assert a.keys()==b.keys()
  for k in a:assert(a[k]^b[k]).is_empty(),('Native material changed',k)
 equal(regions(C,ct),regions(L,T));equal(regions(D,dt),regions(L,output))
 cp={n:(v['layer'],pya.Box.from_s(v['box_dbu']))for n,v in meta['external_ports'].items()}
 assert cp['mp'][0]==cp['mn'][0]==cp['avss'][0]==cp['sub'][0]==134
 op={}
 for shape in output.shapes(L.layer(67,25)).each():
  if not shape.is_text():continue
  name=shape.text.string;point=shape.text.trans.disp
  pins=[s.box for s in output.shapes(L.layer(67,2)).each()if s.is_box()and s.box.contains(point)]
  assert len(pins)==1 and name not in op
  op[name]=pins[0]
 assert set(op)=={'INP','INN','OUTP','OUTN','AVDD','AVSS','SUB','IREF'}
 oldbbox=T.bbox()
 dx=((oldbbox.right+120000+4)//5)*5
 dy=cp['mp'][1].center().y-op['INP'].center().y
 assert dx%5==dy%5==0
 trans=pya.Trans(dx,dy);instance=T.insert(pya.CellInstArray(output.cell_index(),trans))
 assert not oldbbox.overlaps(output.bbox().transformed(trans))
 op={n:b.transformed(trans)for n,b in op.items()}
 # Remove only now-internal/public-child net names; every native material and pin rectangle stays.
 edits=[]
 for cell in L.each_cell():
  names=set(op)if cell.cell_index()==output.cell_index()else {'mp','mn'}if cell.name in (TOP,'native_core')else set()
  for li in L.layer_indexes():
   if L.get_info(li).datatype!=25:continue
   shapes=[s for s in cell.shapes(li).each()if s.is_text()and s.text.string in names]
   for s in shapes:edits.append(dict(cell=cell.name,text=s.text.string,layer=L.get_info(li).layer));s.delete()
 assert len([e for e in edits if e['cell']=='actual_output14'])==8
 assert {e['text']for e in edits if e['cell']!='actual_output14'}=={'mp','mn'}
 L.write(str(out/'placed-layout.gds'))
 baseline=regions(L,T);metals=(67,126,134)
 flat={m:pya.Region(T.begin_shapes_rec(L.layer(m,0))).merged()for m in metals}
 def component(m,p):
  choices=list(flat[m].interacting(pya.Region(p)).each());assert len(choices)==1,('Ambiguous actual conductor',m,str(p),len(choices))
  reg=pya.Region(choices[0]);assert(pya.Region(p)-reg).is_empty()
  return reg
 def wire(x0,y0,x1,y1,h=1600):
  assert x0==x1 or y0==y1
  return pya.Region(pya.Box(min(x0,x1)-h,min(y0,y1)-h,max(x0,x1)+h,max(y0,y1)+h))
 def via(bottom,top,x,y):
  cell=L.create_cell('via_stack','SG13_dev',dict(b_layer=bottom,t_layer=top,vn_columns=1,vn_rows=1,vt1_columns=1,vt1_rows=1,vt2_columns=1,vt2_rows=1))
  assert cell is not None and not cell.is_empty()
  q=pya.Region(cell.begin_shapes_rec(L.layer(133,0))).bbox().center();tr=pya.Trans(x-q.x,y-q.y)
  rs=regions(L,cell);assert all(dt==0 for _,dt in rs)
  return {m:r.transformed(tr)for(m,dt),r in rs.items()}
 added={};prior={m:pya.Region()for m in metals};routes=[];route_shapes={}
 def attach(candidate,bottom,x,y):
  for m,r in via(bottom,'TopMetal2',x,y).items():candidate[m]=candidate.get(m,pya.Region())+r
 def collisions(candidate,allowed):
  bad={}
  for m in metals:
   overlap=candidate.get(m,pya.Region()).sized(1645)&((flat[m]-allowed.get(m,pya.Region()))+prior[m])
   if not overlap.is_empty():bad[str(m)]=dict(area_dbu2=overlap.area(),bbox_dbu=str(overlap.bbox()))
  return bad
 def commit(name,candidate,source,target):
  for m,r in candidate.items():T.shapes(L.layer(m,0)).insert(r);added[m]=added.get(m,pya.Region())+r
  for m in metals:prior[m]+=candidate.get(m,pya.Region())
  route_shapes[name]=candidate
  L.write(str(out/'partial-layout.gds'))
  routes.append(dict(net=name,source_dbu=str(source),destination_dbu=str(target),foreign_clearance_dbu=1645,layers=sorted(candidate)))
 dest=out/'layout';dest.mkdir();faults=out/'faults';faults.mkdir()
 for name,pin in [('mp','INP'),('mn','INN')]:
  s=cp[name][1].center();t=op[pin].center()
  allowed={134:component(134,cp[name][1]),67:component(67,op[pin])}
  if name=='mp':
   assert s.y==t.y
   candidate={134:wire(s.x,s.y,t.x,t.y)};attach(candidate,'Metal5',t.x,t.y)
  else:
   x=dx+35000
   candidate={134:wire(s.x,s.y,x,s.y)+wire(x,t.y,t.x,t.y),126:wire(x,s.y,x,t.y)}
   attach(candidate,'TopMetal1',x,s.y);attach(candidate,'TopMetal1',x,t.y);attach(candidate,'Metal5',t.x,t.y)
  bad=collisions(candidate,allowed)
  (out/(name+'-obstructions.json')).write_text(json.dumps(bad,indent=2)+'\n')
  assert not bad,('Actual signal handoff blocked',name,bad)
  commit(name,candidate,s,t)
 lower=min(oldbbox.bottom,output.bbox().transformed(trans).bottom)-100000
 for ordinal,(name,pin)in enumerate([('avss','AVSS'),('sub','SUB')]):
  source=cp[name][1];t=op[pin].center();y=lower-40000*ordinal;x=dx-60000+20000*ordinal
  allowed={134:component(134,source),67:component(67,op[pin])}
  chosen=None;failed=[]
  offsets=[0,-10000,10000,-20000,20000]if name=='avss'else[0]
  for offset in offsets:
   s=pya.Point(source.center().x+offset,source.center().y)
   assert source.contains(s)
   # Exit the actual TopMetal2 pin before introducing a new TopMetal1 landing.
   # The original pad has underlying native TopMetal1 material; never assume its net.
   anchor=pya.Point(s.x,source.bottom-15000)
   candidate={126:wire(anchor.x,anchor.y,s.x,y,3000)+wire(x,y,x,t.y,3000),134:wire(s.x,s.y,anchor.x,anchor.y,3000)+wire(s.x,y,x,y,3000)+wire(x,t.y,t.x,t.y,3000)}
   if name=='avss':
    original_return={m:r.dup()for m,r in candidate.items()}
    spans=[(126,anchor.x,anchor.y,s.x,y),(134,s.x,y,x,y),
           (126,x,y,x,t.y),(134,x,t.y,t.x,t.y)]
    for metal,ax,ay,bx,by in spans:
     assert ax==bx or ay==by
     distance=abs(bx-ax)+abs(by-ay)
     assert distance>40000,('Return span too short for preserved endpoint access',metal,distance)
     ux=0 if ax==bx else 1 if bx>ax else -1
     uy=0 if ay==by else 1 if by>ay else -1
     shift=-2000 if metal==126 and ax==bx==x else 0
     candidate[metal]+=wire(ax+20000*ux+shift,ay+20000*uy,bx-20000*ux+shift,by-20000*uy,16000)
    assert all((region-candidate[m]).is_empty()for m,region in original_return.items())
   for q in [anchor,pya.Point(s.x,y),pya.Point(x,y),pya.Point(x,t.y)]:attach(candidate,'TopMetal1',q.x,q.y)
   attach(candidate,'Metal5',t.x,t.y)
   bad=collisions(candidate,allowed)
   if not bad:chosen=(candidate,s);break
   failed.append(dict(offset=offset,collisions=bad))
  (out/(name+'-obstructions.json')).write_text(json.dumps(failed,indent=2)+'\n')
  assert chosen is not None,('Actual power/body route blocked',name,failed)
  commit(name,chosen[0],chosen[1],t)
 ports={n:v for n,v in cp.items()if n not in ('mp','mn')}
 for native,name in [('OUTP','op'),('OUTN','on'),('AVDD','tvdd'),('IREF','tr')]:
  p=op[native];ports[name]=(67,p);T.shapes(L.layer(67,2)).insert(p);q=p.center();T.shapes(L.layer(67,25)).insert(pya.Text(name,q.x,q.y))
 assert len(ports)==165 and len(routes)==4
 # Parallel physical power delivery to the64 native drivers. The measured
 # predecessor has up to1.404V AVDD droop; no source voltage/model is changed.
 hand=json.loads((core/'source/handoff-result.json').read_text())
 assert hand['routed_count']==64 and hand['blocked_count']==0 and len(hand['placements'])==64
 power_flat={m:pya.Region(T.begin_shapes_rec(L.layer(m,0))).merged()for m in metals}
 def power_component(m,p):
  choices=list(power_flat[m].interacting(pya.Region(p)).each())
  assert len(choices)==1,('Ambiguous original power conductor',m,str(p),len(choices))
  reg=pya.Region(choices[0]);assert(pya.Region(p)-reg).is_empty()
  return reg
 def power_via(bottom,upper,x,y):
  cell=L.create_cell('via_stack','SG13_dev',dict(b_layer=bottom,t_layer=upper,
   vn_columns=1,vn_rows=1,vt1_columns=4,vt1_rows=1,vt2_columns=4,vt2_rows=1))
  assert cell is not None and not cell.is_empty()
  cut=133 if upper=='TopMetal2'else 125
  point=pya.Region(cell.begin_shapes_rec(L.layer(cut,0))).bbox().center()
  transform=pya.Trans(x-point.x,y-point.y)
  rs=regions(L,cell);assert all(dt==0 for _,dt in rs)
  return {m:r.transformed(transform)for(m,dt),r in rs.items()}
 power_prior={m:pya.Region()for m in metals};power_routes=[]
 original_power={r['net']:r for r in meta['power_routes']}
 for name,x in [('avdd',-150000),('avss',-350000)]:
  pins=[pya.Box.from_s(row['pins_dbu'][name])for row in hand['placements']]
  root=cp[name][1].center();original_x=original_power[name]['trunk_x_dbu']
  assert cp[name][0]==134 and original_x in (30000,50000)
  ys=[root.y,*[pin.center().y for pin in pins]]
  # The previous6um bridge ended at the original narrow trunk. Feed the
  # parallel trunk from the actual public pad across the entire root span.
  # Do not change the pin, its source, native devices or any acceptance gate.
  assert root.x>original_x>x and cp[name][1].height()>=32000
  candidate={126:wire(x,min(ys),x,max(ys),64000),
             134:wire(x,root.y,root.x,root.y,16000),67:pya.Region()}
  allowed={67:pya.Region(),126:pya.Region(),134:power_component(134,cp[name][1])}
  def pv(bottom,upper,qx,qy):
   for m,region in power_via(bottom,upper,qx,qy).items():
    candidate[m]=candidate.get(m,pya.Region())+region
    if m==134:
     # The four-column via landing extends beyond the original bridge end.
     # Fill its full lateral span to6um width; preserve every native via cut.
     pad=region.bbox();assert pad.bottom>=qy-3000 and pad.top<=qy+3000
     candidate[m]+=pya.Region(pya.Box(pad.left,qy-3000,pad.right,qy+3000))
  pv('TopMetal1','TopMetal2',x,root.y)
  for pin in pins:
   q=pin.center();allowed[67]+=power_component(67,pin)
   candidate[67]+=wire(x,q.y,q.x,q.y,1600)
   pv('Metal5','TopMetal1',x,q.y)
  obstacles={}
  for m in metals:
   bad=candidate.get(m,pya.Region()).sized(1645)&((power_flat[m]-allowed[m])+power_prior[m])
   if not bad.is_empty():
    obstacles[str(m)]=dict(area_dbu2=bad.area(),bbox_dbu=str(bad.bbox()),polygons=[str(p)for p in list(bad.each())[:16]])
  (out/(name+'-power128feed32-obstructions.json')).write_text(json.dumps(obstacles,indent=2)+'\n')
  assert not obstacles,('New power path crosses foreign material',name,obstacles)
  for m,region in candidate.items():
   T.shapes(L.layer(m,0)).insert(region);added[m]=added.get(m,pya.Region())+region
  for m in metals:power_prior[m]+=candidate.get(m,pya.Region())
  power_routes.append(dict(net=name,parallel_trunk_x_dbu=x,trunk_width_um=128.,
   driver_branches=64,branch_width_um=3.2,bridge_width_um=32.,
   bridge_to_public_pin_center_dbu=str(root),original_trunk_x_dbu=original_x,core_public_pin_unchanged=str(cp[name][1]),
   via_columns=4,via_rows=1,foreign_clearance_dbu=1645,
   original_paths_and_every_native_primitive_preserved=True))
 assert len(power_routes)==2

 L.write(str(dest/'layout.gds'))
 R=pya.Layout();R.read(str(dest/'layout.gds'));U=R.cell(TOP)
 expected={k:v.dup()for k,v in baseline.items()}
 for m,r in added.items():expected[(m,0)]=expected.get((m,0),pya.Region())+r
 for name in ('op','on','tvdd','tr'):
  m,p=ports[name];expected[(m,2)]=expected.get((m,2),pya.Region())+pya.Region(p)
 equal(expected,regions(R,U))
 lines=(core/'layout/schematic.cir').read_text().splitlines();header=next(l.split()for l in lines if l.startswith('.subckt'))
 assert len(header[2:])==163 and set(header[2:])==set(cp)
 refs=['* Actual8074 core plus actual14 output, common physical BULK; explicit supply/bias boundaries.',
  '.subckt '+TOP+' '+' '.join([n for n in header[2:]if n not in ('mp','mn')]+['op','on','tvdd','tr'])]
 refs += [l for l in lines if l and l[0]in 'QRM']
 assert len(refs)==8076
 mapping=dict(INP='mp',INN='mn',OUTP='op',OUTN='on',AVDD='tvdd',AVSS='avss',SUB='sub',IREF='tr',BULK='BULK',TAIL='output_tail')
 count=0
 for l in (leaf/'layout/schematic.cir').read_text().splitlines():
  if not l or l[0]not in 'QR':continue
  f=l.split();n=4 if f[0][0]=='Q'else 2 if f[3]=='ptap1'else 3
  f[0]=f[0][0]+'output_'+f[0][1:];f[1:n+1]=[mapping[x]for x in f[1:n+1]];refs.append(' '.join(f));count+=1
 assert count==14
 refs+=['.ends '+TOP,''];text='\n'.join(refs);(dest/'schematic.cir').write_text(text)
 assert sum(l.startswith(('Q','R','M'))for l in refs)==8088
 # Native corruption controls on new real joins, in addition to old MOS geometry and strict port checks.
 li=L.layer(134,0);saved=pya.Region(T.shapes(li));cut=route_shapes['mn'][134]
 T.shapes(li).clear();T.shapes(li).insert(saved-cut);L.write(str(faults/'handoff_open.gds'));T.shapes(li).clear();T.shapes(li).insert(saved)
 # Open the entire widened output-return bottom span; no narrower old path may hide the fault.
 ground_route=next(row for row in routes if row['net']=='avss')
 start=pya.Point.from_s(ground_route['source_dbu'])
 middle=((start.x+dx-60000)//2//5)*5
 li=L.layer(134,0);saved=pya.Region(T.shapes(li))
 sever=pya.Region(pya.Box(middle-5000,lower-18000,middle+5000,lower+18000))
 assert not (saved&sever).is_empty()
 T.shapes(li).clear();T.shapes(li).insert(saved-sever)
 L.write(str(faults/'output_return_open.gds'));T.shapes(li).clear();T.shapes(li).insert(saved)
 li=L.layer(126,0);saved=pya.Region(T.shapes(li))
 T.shapes(li).insert(wire(dx-60000,lower+20000,dx-40000,lower+20000))
 L.write(str(faults/'body_supply_short.gds'));T.shapes(li).clear();T.shapes(li).insert(saved)
 wrong=text.replace('sg13_hv_nmos w=1u l=.45u','sg13_hv_nmos w=0.9u l=.45u',1);assert wrong!=text;(faults/'wrong_width.cir').write_text(wrong)
 original=next(l for l in refs if l.startswith('Qoutput_P '))
 wrong=text.replace(original,original.replace('Nx=8','Nx=4'),1);assert wrong!=text;(faults/'wrong_output_Nx.cir').write_text(wrong)
 bad=text
 for name in ('P','N'):
  line=next(l for l in refs if l.startswith('Qoutput_'+name+' '));f=line.split();assert f[2]in ('mp','mn');f[2]='mn'if f[2]=='mp'else'mp';bad=bad.replace(line,' '.join(f),1)
 assert bad!=text;(faults/'swap_output_inputs.cir').write_text(bad)
 q=cp['mp'][1].center();label=T.shapes(L.layer(134,25)).insert(pya.Text('mp',q.x,q.y));L.write(str(faults/'internal_port_alias.gds'));label.delete()
 shape=T.shapes(L.layer(67,0)).insert(pya.Box(dx+200001,dy,dx+202001,dy+2000));L.write(str(faults/'offgrid.gds'));shape.delete()
 r=dict(status='GENERATED_ACTUAL8088_POWER128RETURN32_PARENT_REQUIRES_NATIVE_DRC_LVS_AND_FRESH_RC',source_core_gds_sha256=sha(core/'layout/layout.gds'),source_output_gds_sha256=sha(leaf/'layout/nssoc_tx_cml_layout.gds'),reference_devices=8088,output_transform=str(trans),routes=routes,parallel_power_routes=power_routes,external_ports={n:dict(layer=m,box_dbu=str(p))for n,(m,p)in ports.items()},internal_port_annotation_changes=edits,native_material_preserved=True,serialized_geometry_verified=True,actual_output_mapping=mapping,all_four_handoffs_routed=True,full_phy_accepted=False,main_chip_integrated=False,qualified_pex=False,electrical_accepted=False,remaining='Native clock modulation, clock/bias macro integration, output bias feed and supply endpoints, fresh whole-parent RC, full loaded waves and mainchip closure remain.')
 r['output_return_repair']=dict(net='avss',middle_width_um=32.,unchanged_endpoint_access_um=20.,old_width_um=6.,every_old_return_polygon_retained=True,native_devices_and_ports_unchanged=True,full_width_open_fault='output_return_open.gds',electrical_effect_unproven_until_fresh_extraction=True)
 (out/'integration-result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main(Path(sys.argv[1]).resolve())
