#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Replace C/D sampler leaves with explicit native-witnessed parent metal relocations and supply detours."""
import argparse,copy,hashlib,json,re,sys
from collections import Counter
from decimal import Decimal
from pathlib import Path
from generate_cdr_retimed_parallel_v3_base import flatten
OLD_TOP='nssoc_cdr_pd476_follower_v23'
TOP='nssoc_cdr_pd500_active_input_v57'
OLD_LEAF='nssoc_rx_sampler_input_access_layout_v26'
LEAF='nssoc_rx_sampler_active_input_layout_v57'
EXPECTED=dict(npn13g2=124,sg13_lv_nmos=50,rppd=98,cap_cmim=7,ptap1=221)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def nums(s):return list(map(float,re.findall(r'-?\d+(?:\.\d+)?',s)))
def main():
 import pya
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();out=a.out.resolve()
 old=out/'baseline';fresh=out/'data/layout';dest=out/'layout';dest.mkdir(exist_ok=False)
 before=json.loads((old/'layout/result.json').read_text())
 oldleaf=json.loads((old/'inputs/sampler/layout/result.json').read_text());newleaf=json.loads((fresh/'result.json').read_text())
 assert oldleaf['ports']==newleaf['ports'] and oldleaf['bbox_um']==[0,0,1003,243.63] and newleaf['bbox_um']==[0,0,1323,243.63]
 assert before['primitive_census']==dict(npn13g2=120,sg13_lv_nmos=46,rppd=98,cap_cmim=7,ptap1=205)
 L=pya.Layout();L.read(str(old/'layout'/(OLD_TOP+'.gds')))
 N=pya.Layout();N.read(str(fresh/(LEAF+'.gds')))
 T=L.cell(OLD_TOP);S=N.cell(LEAF)
 assert L.dbu==N.dbu==.001 and T is not None and S is not None
 def snapshot(layout,top):
  shapes={};texts={}
  for li in layout.layer_indexes():
   info=layout.get_info(li);key=(info.layer,info.datatype)
   reg=pya.Region(top.shapes(li)).flatten().merged()
   if not reg.is_empty():shapes[key]=reg
   rows=sorted(str(s.text)for s in top.shapes(li).each()if s.is_text())
   if rows:texts[key]=rows
  inst=sorted((i.cell.name,str(i.dcplx_trans),i.na,i.nb,str(i.a),str(i.b))for i in top.each_inst())
  return shapes,texts,inst
 def compare(expected,actual):
  assert expected[1:]==actual[1:],'Parent labels or specified hierarchy changed'
  assert expected[0].keys()==actual[0].keys()
  for k in expected[0]:assert(expected[0][k]^actual[0][k]).is_empty(),('Parent geometry changed',k)
 snap=snapshot(L,T);assert len(snap[2])==16
 original_m3_vias={m:pya.Region(T.begin_shapes_rec(L.layer(m,0))).flatten().merged()for m in (29,49)}
 replacements={}
 for tag in ('sc','sd'):
  bounds=before['placements'][tag]['bbox_um']
  found=[i for i in T.each_inst()if i.cell.name=='pd_child_sampler'and str(i.dbbox())==bounds]
  assert len(found)==1
  replacements[tag]=found[0]
 expected_instances=[]
 for row in snap[2]:
  changed=any(row[1]==str(i.dcplx_trans)and row[0]==i.cell.name for i in replacements.values())
  expected_instances.append(('pd_child_sampler_cd'if changed else row[0],*row[1:]))
 assert sum(r[0]=='pd_child_sampler_cd'for r in expected_instances)==2
 assert sum(r[0]=='pd_child_sampler'for r in expected_instances)==2
 C=L.create_cell('pd_child_sampler_cd');C.copy_tree(S)
 removed=[]
 for cell in list(L.each_cell()):
  if cell.cell_index()==T.cell_index():continue
  for layer in (8,10,30,50,67,126,134):
   for dt in (2,25):
    shapes=cell.shapes(L.layer(layer,dt))
    if not shapes.is_empty():removed.append(dict(cell=cell.name,layer=layer,datatype=dt,count=shapes.size()))
    shapes.clear()
 assert removed and C.dbbox()==S.dbbox()
 for i in replacements.values():i.cell_index=C.cell_index()
 T.name=TOP
 expected=(snap[0],snap[1],sorted(expected_instances))
 # Diagnose and relocate only proven old C/D MOS enclosure strips.
 diagnosis_path=Path.cwd()/'docs/evidence/cdr-sampler-active-input-v57-parent-drc-marker-frames-20261024.json'
 diagnosis=json.loads(diagnosis_path.read_text())['report']['diagnosis']
 assert diagnosis['status']=='PASS_ACTUAL54_MARKER_AND_GEOMETRY_READBACK'
 m1_index=L.layer(8,0);m5_index=L.layer(67,0)
 old_direct=pya.Region(T.shapes(m1_index)).flatten().merged()
 assert old_direct.count()==64
 moved=pya.Region();shifted=pya.Region();m1_records=[]
 old_core=pya.Region(L.cell('pd_child_sampler').begin_shapes_rec(m1_index)).flatten().merged()
 new_core=pya.Region(C.begin_shapes_rec(m1_index)).flatten().merged()
 for tag in ('sc','sd'):
  origin=nums(before['placements'][tag]['bbox_um'])[:2];tr=pya.Trans(round(origin[0]/L.dbu),round(origin[1]/L.dbu))
  limits=pya.DBox(*nums(before['placements'][tag]['bbox_um'])).to_itype(L.dbu)
  source=old_core.transformed(tr).merged();target=new_core.transformed(tr).merged()
  candidates=[q for q in old_direct.each()if (limits & q.bbox())==q.bbox()]
  assert len(candidates)==16,('C/D old enclosure census',tag,len(candidates))
  for polygon in candidates:
   r=pya.Region(polygon);b=polygon.bbox()
   assert polygon.area()==b.area() and b.width()==65 and b.height()==7490
   # Both before and after strips must touch one identical translated native
   # primitive component. This is a tracked conductor relocation, not deletion.
   connected=source.interacting(r)
   assert connected.count()==1,('Old enclosure connection differs',tag,str(b),connected.count())
   delta=pya.Trans(320000,0);candidate=r.transformed(delta)
   new_connected=target.interacting(candidate)
   assert new_connected.count()==1,('New enclosure connection differs',tag,str(b),new_connected.count())
   assert(connected.transformed(delta)^new_connected).is_empty(),'Native attachment changed'
   moved+=r;shifted+=candidate
   m1_records.append(dict(tag=tag,before_box_dbu=str(b),after_box_dbu=str(b.transformed(delta)),translation_dbu=[320000,0],same_translated_native_metal_component=True))
 assert len(m1_records)==32 and moved.count()==32
 for marker in diagnosis['markers']:
  if marker['category'].startswith('M1.'):
   box=pya.DBox(*nums(marker['bbox_um'])).to_itype(L.dbu)
   assert not moved.interacting(pya.Region(box.enlarged(1))).is_empty()
 corrected=(old_direct-moved)+shifted
 T.shapes(m1_index).clear();T.shapes(m1_index).insert(corrected)
 expected_metal=dict(expected[0]);expected_metal[(8,0)]=corrected.merged()
 # Resolve six hierarchical markers to four actual notch locations before filling.
 m5_before=pya.Region(T.begin_shapes_rec(m5_index)).flatten().merged()
 parent_m5=pya.Region(T.shapes(m5_index)).flatten().merged()
 m5_fill=pya.Region();m5_records=[]
 normalized={};source_markers=[]
 for marker_index,marker in enumerate(diagnosis['markers']):
  if marker['category']!='M5.b':continue
  source_markers.append(marker_index)
  local=pya.DBox(*nums(marker['bbox_um'])).to_itype(L.dbu)
  if marker['cell']==TOP:boxes=[local]
  else:
   assert marker['cell']=='pd_child_sampler_cd',marker['cell']
   boxes=[local.transformed(i.cplx_trans)for i in T.each_inst()if i.cell.name==marker['cell']]
   assert len(boxes)==2
  for b in boxes:
   key=(b.left,b.bottom,b.right,b.top)
   normalized.setdefault(key,[]).append(dict(marker_index=marker_index,cell=marker['cell'],source_values=marker['values']))
 assert len(source_markers)==6 and len(normalized)==4 and sum(map(len,normalized.values()))==8
 for key,sources in sorted(normalized.items()):
  b=pya.Box(*key)
  box=pya.Box((b.left//5)*5-5,(b.bottom//5)*5-5,((b.right+4)//5)*5+5,((b.top+4)//5)*5+5)
  patch=pya.Region(box);touch=m5_before.interacting(patch)
  assert touch.count()==1,('Notch spans different M5 components',str(box),touch.count())
  assert (patch-m5_before).area()>0,'No actual notch gap covered'
  assert any((pya.DBox(*nums(before['placements'][tag]['bbox_um'])).to_itype(L.dbu) & box)==box for tag in ('sc','sd'))
  m5_fill+=patch;m5_records.append(dict(box_dbu=str(box),source_markers=sources,touched_existing_m5_components=touch.count(),added_area_dbu2=(patch-m5_before).area()))
 assert len(m5_records)==4 and (m5_before+m5_fill).merged().count()==m5_before.count()
 assert {v['marker_index']for r in m5_records for v in r['source_markers']}==set(source_markers)
 T.shapes(m5_index).insert(m5_fill)
 expected_metal[(67,0)]=(parent_m5+m5_fill).merged()
 # Reroute the two witnessed old AVSS M3 bridges around new SUB contacts.
 collision_path=Path.cwd()/'docs/evidence/cdr-sampler-active-input-v57-parent-supply-collision-20261024.json'
 collision_pin=json.loads(collision_path.read_text())
 assert collision_pin['run']==40065658287
 collision=collision_pin['report']['native']
 assert collision['old_avss_and_sub_separate']and collision['leaf_avss_and_sub_separate']
 witnesses=collision['collisions'];assert len(witnesses)==2
 m3_index=L.layer(30,0)
 m3_direct=pya.Region(T.shapes(m3_index)).flatten().merged()
 new_m3=pya.Region(C.begin_shapes_rec(m3_index)).flatten().merged()
 m3_removed=pya.Region();m3_added=pya.Region();m3_records=[]
 for witness in witnesses:
  assert witness['metal']==30 and witness['old_parent_net']=='avss'and witness['new_leaf_net']=='sub'
  assert len(witness['parent_components'])==len(witness['intersections'])==1
  candidates=[q for q in m3_direct.each()if str(q)==witness['parent_components'][0]]
  assert len(candidates)==1,'Native-witnessed parent component missing or changed'
  polygon=candidates[0];r=pya.Region(polygon)
  instances=[i for i in replacements.values()if str(i.dcplx_trans)==witness['transform']]
  assert len(instances)==1
  instance=instances[0]
  collision_box=pya.Box(*[int(v)for v in re.findall(r'-?\d+',witness['intersections'][0]['bbox_dbu'])])
  assert collision_box.width()==1110 and collision_box.height()==290
  # 1.2um root bridge, 0.6um actual clearance from the foreign M3 landing.
  # Preserve original vias and connectivity; no translation of parent endpoints.
  width=1200;half=width//2;gap=600;keep=collision_box.enlarged(gap)
  left=keep.left-half;right=keep.right+half;bottom=keep.bottom-half;center=collision_box.center().y
  assert all(v%5==0 for v in (keep.left,keep.right,keep.bottom,keep.top,left,right,bottom,center))
  jog=pya.Region()
  for box in (pya.Box(left-half,bottom-half,right+half,bottom+half),
              pya.Box(left-half,bottom-half,left+half,center+half),
              pya.Box(right-half,bottom-half,right+half,center+half)):
   jog+=pya.Region(box)
  candidate=((r-pya.Region(keep))+jog).merged()
  assert candidate.count()==1,'Supply detour split the existing root component'
  assert(candidate & pya.Region(collision_box.enlarged(gap-1))).is_empty(),'Insufficient foreign-landing clearance'
  original_vias={}
  for v,via_region in original_m3_vias.items():
   original_contacts=via_region & r
   assert(original_contacts-candidate).is_empty(),('Removed original parent via contact',v)
   original_vias[str(v)]=dict(count=original_contacts.count(),area_dbu2=original_contacts.area(),all_original_contacts_preserved=True)
  assert sum(q['area_dbu2']for q in original_vias.values())>0,'Unbound old parent component'
  placed_new=new_m3.transformed(instance.cplx_trans).merged()
  assert candidate.interacting(placed_new).is_empty(),'Detour touches a new leaf M3 conductor'
  assert(candidate-r).interacting(m3_direct-r).is_empty(),'Detour touches another parent M3 conductor'
  tag=next(k for k,v in replacements.items()if str(v.dcplx_trans)==witness['transform'])
  m3_removed+=r;m3_added+=candidate
  m3_records.append(dict(tag=tag,before_polygon_dbu=str(polygon),after_polygons_dbu=[str(q)for q in candidate.each()],
   original_parent_via_contacts=original_vias,connected_component_count_after=1,clearance_dbu=gap,bridge_width_dbu=width,
   no_new_leaf_m3_contact=True,no_other_parent_m3_contact=True,old_parent_native_net='avss',unintended_new_leaf_net='sub',
   prior_native_intersections=witness['intersections']))
 assert len(m3_records)==2 and m3_removed.count()==2
 corrected_m3=(m3_direct-m3_removed)+m3_added
 T.shapes(m3_index).clear();T.shapes(m3_index).insert(corrected_m3)
 expected_metal[(30,0)]=corrected_m3.merged()
 # Reconcile original C/D Metal4 enclosures with the replacement child.
 # These pieces were attached to old child routes, not floating metal.
 m4_path=Path.cwd()/'docs/evidence/cdr-sampler-active-input-v57-parent-m4-attachments-20261024.json'
 m4_pin=json.loads(m4_path.read_text());assert m4_pin['run']==40070690392
 witnesses=m4_pin['report']['native']['records'];assert len(witnesses)==48
 m4_index=L.layer(50,0);m4_direct=pya.Region(T.shapes(m4_index)).flatten().merged()
 old_m4=pya.Region(L.cell('pd_child_sampler').begin_shapes_rec(m4_index)).flatten().merged()
 new_m4=pya.Region(C.begin_shapes_rec(m4_index)).flatten().merged()
 root_vias={v:pya.Region(T.shapes(L.layer(v,0))).flatten().merged()for v in(49,66)}
 m4_removed=pya.Region();m4_added=pya.Region();m4_records=[]
 for witness in witnesses:
  candidates=[q for q in m4_direct.each()if str(q)==witness['polygon_dbu']]
  assert len(candidates)==1,'Measured root M4 polygon changed'
  polygon=candidates[0];r=pya.Region(polygon);box=polygon.bbox()
  instances=[i for i in replacements.values()if str(i.dcplx_trans)==witness['transform']]
  assert len(instances)==1;instance=instances[0]
  tag=next(k for k,v in replacements.items()if str(v.dcplx_trans)==witness['transform'])
  old_bounds=pya.DBox(*nums(before['placements'][tag]['bbox_um'])).to_itype(L.dbu)
  assert(old_bounds & box)==box,'M4 piece extends beyond replaced child'
  old_touch=old_m4.transformed(instance.cplx_trans).interacting(r)
  assert old_touch.count()==witness['old_child_touch_count']==1
  assert witness['old_component_only_this_root']is False
  # Child vias are intentionally replaced with their verified child. Root-owned
  # vias are different: none may depend on a relocated/removed old enclosure.
  contacts={str(v):q.interacting(r).count()for v,q in root_vias.items()}
  assert all(n==0 for n in contacts.values()),('Root endpoint depends on old M4 enclosure',tag,str(box),contacts)
  assert m4_direct.interacting(r).count()==1,'External root M4 attachment'
  if witness['shifted_old_attachment_matches']:
   assert box.width()==1225 and box.height()==290 and polygon.area()==355250
   candidate=r.transformed(pya.Trans(320000,0))
   target=new_m4.transformed(instance.cplx_trans).interacting(candidate)
   assert target.count()==1 and(old_touch.transformed(pya.Trans(320000,0))^target).is_empty()
   m4_added+=candidate;action='RELOCATE_WITH_IDENTICAL_RETAINED_CHILD_COMPONENT'
   after=[str(q)for q in candidate.each()]
  else:
   assert box.width()==4150 and polygon.holes()>=1,'Not a witnessed old route enclosure'
   # Old overlay touches only one old child route and no root-owned via.
   # New child is independently DRC/LVS passed and keeps its own full routes.
   # Full parent native checks below must prove their new connectivity.
   action='REMOVE_OBSOLETE_PARENT_ENCLOSURE_OVER_REPLACED_CHILD_ROUTE';after=[]
  m4_removed+=r
  m4_records.append(dict(tag=tag,action=action,before_polygon_dbu=str(polygon),after_polygons_dbu=after,
   old_child_attachment_count=1,old_piece_was_floating=False,root_owned_via_contacts=contacts,
   confined_to_replaced_child=True,no_external_parent_m4_component=True,
   exact_translated_attachment=bool(witness['shifted_old_attachment_matches'])))
 assert len(m4_records)==48 and sum(r['exact_translated_attachment']for r in m4_records)==32
 assert sum(not r['exact_translated_attachment']for r in m4_records)==16
 corrected_m4=((m4_direct-m4_removed)+m4_added).merged()
 T.shapes(m4_index).clear();T.shapes(m4_index).insert(corrected_m4)
 expected_metal[(50,0)]=corrected_m4
 # Independent drawing-only proof after every parent edit; no text union.
 def supply_separation(layout,top):
  metals=(8,10,30,50,67,126,134);vias=(19,29,49,66,125,133)
  regions={m:pya.Region(top.begin_shapes_rec(layout.layer(m,0))).flatten().merged()for m in(*metals,*vias)}
  extractor=pya.LayoutToNetlist('PD500_SUPPLY_WIRES',layout.dbu)
  for m,r in regions.items():extractor.register(r,'gds_'+str(m));extractor.connect(r)
  for lo,v,hi in zip(metals,vias,metals[1:]):
   extractor.connect(regions[lo],regions[v]);extractor.connect(regions[v],regions[hi])
  extractor.extract_netlist()
  nets={}
  for name in('avss','sub'):
   point=pya.DBox(*nums(before['ports'][name])).to_itype(layout.dbu).center()
   n=extractor.probe_net(regions[134],point);assert n is not None
   nets[name]=n.cluster_id
  assert nets['avss']!=nets['sub'],'Physical AVSS/SUB wire short remains'
  return dict(method='Seven drawing metals and six via layers without text union',clusters=nets,separate=True)
 wire_separation=supply_separation(L,T)
 expected=(expected_metal,expected[1],expected[2])
 metal_delta=dict(status='TRACKED_C_D_M1_M4_RECONCILIATION_M3_SUPPLY_DETOUR_AND_SAME_COMPONENT_M5_FILL',diagnosis_sha256=sha(diagnosis_path),m1_strips=m1_records,m4_enclosures=m4_records,m4_diagnosis_sha256=sha(m4_path),drawing_only_supply_separation=wire_separation,m3_reroutes=m3_records,m3_diagnosis_sha256=sha(collision_path),m5_patches=m5_records,m5_component_count_before=m5_before.count(),m5_component_count_after=(m5_before+m5_fill).merged().count(),all_other_parent_layers_unchanged=True,all_parent_labels_and_transforms_unchanged=True,all_children_unchanged=True)
 compare(expected,snapshot(L,T))
 assert T.dbbox()==pya.DBox(0,0,2316.6,4715.48)
 options=pya.SaveLayoutOptions();options.select_cell(T.cell_index());L.write(str(dest/(TOP+'.gds')),options)
 R=pya.Layout();R.read(str(dest/(TOP+'.gds')));U=R.cell(TOP);after=snapshot(R,U)
 compare(expected,after);assert U.dbbox()==T.dbbox()
 assert supply_separation(R,U)['separate']
 plan=copy.deepcopy(before['source_plan']);by_tag={n['tag']:n for n in plan['nodes']}
 reference=(old/'layout/schematic.cir').read_text();lines=reference.splitlines(keepends=True)
 reference_rows={l.split()[0]:' '.join(l.split())for l in lines if l and l[0]in 'QRCM'}
 assert len(reference_rows)==476
 updated={};removed_names=[]
 for tag in ('sc','sd'):
  old_rows,old_census=flatten((old/'inputs/sampler/layout/schematic.cir').read_text(),OLD_LEAF,tag,by_tag[tag]['pins'])
  new_rows,new_census=flatten((fresh/'schematic.cir').read_text(),LEAF,tag,by_tag[tag]['pins'])
  assert len(old_rows)==54 and len(new_rows)==66
  for row in old_rows:
   name=row.split()[0];assert reference_rows[name]==row,('Old sampler reference mismatch',tag,name)
   removed_names.append(name)
  updated[tag]=new_rows
 newlines=[];inserted=set()
 for line in lines:
  f=line.split()
  if f and f[0]in removed_names:
   tag=f[0][1:].split('_')[0];assert tag in updated
   if tag not in inserted:newlines += [v+'\n'for v in updated[tag]];inserted.add(tag)
  else:newlines.append(line.replace(OLD_TOP,TOP))
 newreference=''.join(newlines);assert inserted=={'sc','sd'} and len(removed_names)==108
 census=Counter()
 for line in newreference.splitlines():
  f=line.split()
  if f and f[0][0]in 'QRCM':
   model=[m for m in EXPECTED if m in [v.lower()for v in f]];assert len(model)==1;census[model[0]]+=1
 assert dict(census)==EXPECTED
 preserved=[l for l in lines if l.split()and l.split()[0]in reference_rows and l.split()[0]not in removed_names]
 assert len(preserved)==368 and all(l in newreference for l in preserved)
 (dest/'schematic.cir').write_text(newreference)
 meta=copy.deepcopy(before);meta['status']='GENERATED_PD500_ACTIVE_INPUT_V57_REQUIRES_NATIVE_PHYSICAL_AND_FRESH_RC'
 for key in ('sampler_settling_replacement','child_geometry_conservation'):meta.pop(key,None)
 plan['types']['sampler_cd']=dict(top=LEAF,devices=66,layer=67)
 for tag in ('sc','sd'):
  by_tag[tag]['kind']='sampler_cd';meta['placements'][tag]['kind']='sampler_cd'
  candidates=[i for i in U.each_inst()if i.cell.name=='pd_child_sampler_cd'and list(nums(str(i.dbbox())))[:2]==nums(before['placements'][tag]['bbox_um'])[:2]]
  assert len(candidates)==1;meta['placements'][tag]['bbox_um']=str(candidates[0].dbbox())
 assert all(meta['placements'][tag]==before['placements'][tag]for tag in before['placements']if tag not in ('sc','sd'))
 plan['expected_devices']=500;plan['primitive_census']=EXPECTED;meta['primitive_census']=EXPECTED
 circuit=Path.cwd()/'hw/soc/analog/pcie/rx_sampler_active_input_v57.spice'
 plan['source_sha256'][circuit.name]=sha(circuit);meta['source_plan']=plan;meta['bbox_um']=str(U.dbbox())
 sys.path.insert(0,str(Path.cwd()/'hw/soc/flow'));import make_pcie_clock_vco_v6_local_v1 as writer
 writer.TOP=TOP;writer.PORTS=plan['ports'];writer.use_direction=lambda n:('POWER','INOUT')if n=='avdd'else('GROUND','INOUT')if n in ('avss','sub')else('SIGNAL','OUTPUT'if n in ('xp','xn','yp','yn','vip','vin')else'INPUT')
 public={n:('TopMetal2',pya.DBox(*nums(b)))for n,b in meta['ports'].items()}
 for n,(_,b)in public.items():
  assert(pya.Region(b.to_itype(R.dbu))-pya.Region(U.shapes(R.layer(134,2)))).is_empty()
  assert(pya.Region(b.to_itype(R.dbu))-pya.Region(U.shapes(R.layer(134,0)))).is_empty()
 lef=writer.lef(pya,R.dbu,U.dbbox(),public);(dest/(TOP+'.lef')).write_text(lef)
 def grid(values):
  exact=[Decimal(str(v))/Decimal(str(R.dbu))for v in values]
  assert all(v==v.to_integral_value()for v in exact),'LEF value off exact native grid'
  return tuple(int(v)for v in exact)
 def check_lef(text):
  assert f'MACRO {TOP}'in text and f'END {TOP}'in text
  size=re.findall(r'SIZE ([\d.]+) BY ([\d.]+) ;',text);assert len(size)==1
  assert grid(size[0])==(U.bbox().width(),U.bbox().height())
  for n,(_,b)in public.items():
   chunk=text.split('  PIN '+n+'\n')[1].split('  END '+n+'\n')[0]
   assert 'LAYER TopMetal2 ;'in chunk
   rects=re.findall(r'RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+) ;',chunk)
   ib=b.to_itype(R.dbu)
   assert len(rects)==1 and grid(rects[0])==(ib.left,ib.bottom,ib.right,ib.top)
  obs=text.split('  OBS\n')[1].split('  END\n')[0]
  for metal in ('Metal1','Metal2','Metal3','Metal4','Metal5','TopMetal1','TopMetal2'):
   chunks=obs.split('    LAYER '+metal+' ;\n');assert len(chunks)==2
   section=chunks[1].split('    LAYER ')[0];actual=pya.Region()
   for r in re.findall(r'RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+) ;',section):actual+=pya.Region(pya.Box(*grid(r)))
   expected=pya.Region(U.dbbox().to_itype(R.dbu))
   for layer,b in public.values():
    if layer==metal:expected-=pya.Region(b.to_itype(R.dbu))
   assert(actual^expected).is_empty(),('Wrong LEF obstruction',metal)
 check_lef(lef)
 faults=[]
 for name,bad in [('removed_parent_geometry',(dict(after[0]),after[1],after[2])),('removed_parent_instance',(after[0],after[1],after[2][:-1])),('added_parent_metal',(dict(after[0]),after[1],after[2]))]:
  if name=='removed_parent_geometry':bad[0][next(iter(bad[0]))]=pya.Region()
  if name=='added_parent_metal':bad[0][(50,0)]=bad[0].get((50,0),pya.Region())+pya.Region(pya.Box(-10000,-10000,-9000,-9000))
  try:compare(expected,bad)
  except AssertionError:faults.append(name)
  else:raise AssertionError(name+' accepted')
 bad=list(after[2]);i=next(i for i,r in enumerate(bad)if r[0]=='pd_child_sampler');bad[i]=('pd_child_sampler_cd',*bad[i][1:])
 try:compare(expected,(after[0],after[1],sorted(bad)))
 except AssertionError:faults.append('replaced_A_or_B')
 else:raise AssertionError('A/B replacement accepted')
 for name,bad in [('old_lef_size',lef.replace('SIZE 2316.600 BY','SIZE 1996.600 BY')),('old_lef_obstructions',lef.replace('2316.600','1996.600'))]:
  assert bad!=lef
  try:check_lef(bad)
  except AssertionError:faults.append(name)
  else:raise AssertionError(name+' accepted')
 for name,layer in [('unmoved_old_m1_patch',(8,0)),('unrepaired_old_m3_bridge',(30,0)),('stale_old_m4_enclosures',(50,0)),('missing_m5_fill',(67,0))]:
  bad=dict(after[0]);bad[layer]=snap[0][layer]
  try:compare(expected,(bad,after[1],after[2]))
  except AssertionError:faults.append(name)
  else:raise AssertionError(name+' accepted')
 files=[p for name in ('baseline','data','inputs')for p in(out/name).rglob('*')if p.is_file()]+[out/'children.json',Path(__file__),Path(writer.__file__),circuit,diagnosis_path,collision_path,m4_path]
 meta['inputs']={str(p):sha(p)for p in files}
 meta['active_input_parent_metal_delta']=metal_delta
 meta['active_input_replacement']=dict(tags=['sc','sd'],old_devices_per_leaf=54,new_devices_per_leaf=66,preserved_reference_devices=368,one_reference_per_sampler=True,source_parent_gds_sha256=sha(old/'layout'/(OLD_TOP+'.gds')),source_leaf_gds_sha256=sha(fresh/(LEAF+'.gds')))
 meta['outputs']={n:sha(dest/n)for n in (TOP+'.gds',TOP+'.lef','schematic.cir')}
 (dest/'result.json').write_text(json.dumps(meta,indent=2)+'\n')
 proof=dict(status='PASS_C_D_REPLACEMENT_WITH_TRACKED_M1_M4_RECONCILIATION_M3_SUPPLY_DETOUR_AND_M5_FILL',changed_sampler_tags=['sc','sd'],parent_geometry_unchanged=False,parent_geometry_changes=metal_delta,all_parent_labels_and_transforms_unchanged=True,removed_child_port_annotations=removed,preserved_reference_devices=368,old_bbox_um=before['bbox_um'],new_bbox_um=str(U.dbbox()),external_leaf_pins_unchanged=True,actual_lef_size_pins_and_all_seven_obstruction_planes_checked=True,controls=faults,full_phy_accepted=False,qualified_pex=False)
 assert len(faults)==10
 (out/'replacement-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
if __name__=='__main__':main()
