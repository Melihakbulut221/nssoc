#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Replace four actual sampler children while retaining all parent wires and transforms."""
import argparse,copy,hashlib,json,re,shutil
from pathlib import Path
TOP='nssoc_cdr_pd484_localbus_v12'
LEAF='nssoc_rx_sampler_data_layout_v20'
OLDLEAF='nssoc_rx_sampler_selector_layout_v19'
DATA_PAIRS={f'{s}_{k}'for s in ('M','S')for k in ('DP','DN','LP','LN')}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 import pya
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();out=a.out.resolve()
 old=out/'baseline';fresh=out/'data/layout';dest=out/'layout';dest.mkdir(exist_ok=False)
 before=json.loads((old/'layout/result.json').read_text())
 oldleaf=json.loads((old/'inputs/sampler/layout/result.json').read_text())
 newleaf=json.loads((fresh/'result.json').read_text())
 assert oldleaf['bbox_um']==newleaf['bbox_um']==[0,0,1003,243.63]
 assert oldleaf['ports']==newleaf['ports'],'Different external pin locations need a new parent route'
 assert oldleaf['primitive_counts']==newleaf['primitive_counts']
 L=pya.Layout();L.read(str(old/'layout'/(TOP+'.gds')))
 N=pya.Layout();N.read(str(fresh/(LEAF+'.gds')))
 T=L.cell(TOP);C=L.cell('pd_child_sampler');S=N.cell(LEAF)
 assert L.dbu==N.dbu==.001 and all(x is not None for x in (T,C,S))
 assert C.dbbox()==S.dbbox()
 def parent_snapshot(layout,top):
  shapes={};texts={}
  for li in layout.layer_indexes():
   info=layout.get_info(li);key=(info.layer,info.datatype)
   reg=pya.Region(top.shapes(li)).flatten().merged()
   if not reg.is_empty():shapes[key]=reg
   rows=sorted(str(s.text)for s in top.shapes(li).each()if s.is_text())
   if rows:texts[key]=rows
  instances=sorted((i.cell.name,str(i.dcplx_trans),i.na,i.nb,str(i.a),str(i.b))for i in top.each_inst())
  return shapes,texts,instances
 snap=parent_snapshot(L,T)
 assert sum(i.cell.name=='pd_child_sampler'for i in T.each_inst())==4
 # Original parent construction strips child port-purpose annotations.
 metals=(8,10,30,50,67,126,134)
 for cell in L.each_cell():
  if cell.cell_index()==T.cell_index():continue
  for layer in metals:
   for dt in (2,25):assert cell.shapes(L.layer(layer,dt)).is_empty(),('Unexpected original child port annotation',cell.name,layer,dt)
 # Copy from actual newly verified PCell hierarchy, never from an ideal primitive.
 C.clear();C.copy_tree(S)
 removed=[]
 for cell in list(L.each_cell()):
  if cell.cell_index()==T.cell_index():continue
  for layer in metals:
   for dt in (2,25):
    shapes=cell.shapes(L.layer(layer,dt))
    if not shapes.is_empty():removed.append(dict(cell=cell.name,layer=layer,datatype=dt,count=shapes.size()))
    shapes.clear()
 assert removed and all(row['datatype']in (2,25)for row in removed)
 # Previous v20 native DRC identifies obsolete parent-level M3 access overlays.
 # Keep the independently verified new leaf untouched; remove whole obsolete
 # parent polygons only inside sampler interiors and touching measured markers.
 marker_path=out/'failed-v20/physical/drc/drc.lyrdb'
 assert sha(marker_path)=='90881765db42ac4499d84d40cac7827f165346e27f243c7ed9a6d16a7f3b9faf'
 import xml.etree.ElementTree as ET
 markers=[];categories={}
 for item in ET.parse(marker_path).findall('.//items/item'):
  category=item.findtext('category');assert category in ("'M3.a'","'M3.b'")
  categories[category]=categories.get(category,0)+1
  values=item.findall('values/value');assert len(values)==1
  nums=list(map(float,re.findall(r'-?\d+(?:\.\d+)?',values[0].text)))
  assert len(nums)==8
  xs=nums[::2];ys=nums[1::2]
  markers.append(pya.Region(pya.Box(round(min(xs)/L.dbu)-300,round(min(ys)/L.dbu)-300,
      round(max(xs)/L.dbu)+300,round(max(ys)/L.dbu)+300)))
 assert categories=={"'M3.a'":16,"'M3.b'":8}and len(markers)==24
 m3=L.layer(30,0);original_m3=pya.Region(T.shapes(m3)).flatten().merged()
 assert not original_m3.is_empty()
 bounds={name:list(map(float,re.findall(r'-?\d+(?:\.\d+)?',before['placements'][name]['bbox_um'])))for name in ('sa','sb','sc','sd')}
 def sampler_owner(poly):
  b=poly.bbox().to_dtype(L.dbu)
  found=[name for name,(x0,y0,x1,y1)in bounds.items()if b.left>=x0+5 and b.bottom>=y0+5 and b.right<=x1-5 and b.top<=y1-5]
  assert len(found)==1,'Attempt to remove non-interior or non-sampler parent M3'
  return found[0]
 removed_region=pya.Region();removed_rows=[];covered=set()
 for poly in original_m3.each():
  region=pya.Region(poly);hits=[i for i,marker in enumerate(markers)if not(region&marker).is_empty()]
  if not hits:continue
  macro=sampler_owner(poly)
  removed_region+=region;covered.update(hits)
  removed_rows.append(dict(macro=macro,polygon_dbu=str(poly),area_dbu2=poly.area(),marker_indices=hits))
 assert covered==set(range(24))and {r['macro']for r in removed_rows}==set(bounds)
 replacement_m3=(original_m3-removed_region).merged()
 assert (replacement_m3&removed_region).is_empty()and (replacement_m3+removed_region).merged()==original_m3
 T.shapes(m3).clear();T.shapes(m3).insert(replacement_m3)
 expected_shapes=dict(snap[0])
 if replacement_m3.is_empty():del expected_shapes[(30,0)]
 else:expected_shapes[(30,0)]=replacement_m3
 snap=(expected_shapes,snap[1],snap[2])
 try:sampler_owner(next(removed_region.each()).transformed(pya.Trans(10000000,0)))
 except AssertionError:outside_control=True
 else:raise AssertionError('Out-of-sampler metal-removal control accepted')
 cleanup_proof=dict(status='REMOVED_ONLY_OBSOLETE_PARENT_M3_TOUCHING_MEASURED_NATIVE_MARKERS',
  source_run=39418862656,source_report_sha256=sha(marker_path),source_categories=categories,
  removed_polygons=removed_rows,removed_area_dbu2=removed_region.area(),
  retained_parent_m3_area_dbu2=replacement_m3.area(),all24markers_covered=True,
  native_child_geometry_untouched=True,all_other_parent_layers_unchanged=True,
  out_of_sampler_removal_rejected=outside_control,requires_full_drc_lvs=True)
 L.write(str(dest/(TOP+'.gds')))
 R=pya.Layout();R.read(str(dest/(TOP+'.gds')));U=R.cell(TOP)
 after=parent_snapshot(R,U)
 def compare(a,b):
  assert a[1:]==b[1:],'Parent labels or transforms changed'
  assert a[0].keys()==b[0].keys()
  for layer in a[0]:assert (a[0][layer]^b[0][layer]).is_empty(),('Parent metal changed',layer)
 compare(snap,after)
 # Fresh serialized children are independently compared against all eight sources next.
 reference=(old/'layout/schematic.cir').read_text();lines=reference.splitlines(keepends=True)
 changed=[];targets={'Q'+tag+'_'+s for tag in ('sa','sb','sc','sd')for s in DATA_PAIRS}
 for i,line in enumerate(lines):
  f=line.split()
  if f and f[0]in targets:
   assert line.count(' Nx=8 ')==1
   lines[i]=line.replace(' Nx=8 ',' Nx=4 ');changed.append(f[0])
 assert set(changed)==targets and len(changed)==32
 (dest/'schematic.cir').write_text(''.join(lines))
 shutil.copyfile(old/'layout'/(TOP+'.lef'),dest/(TOP+'.lef'))
 meta=copy.deepcopy(before);meta['source_plan']['types']['sampler']['top']=LEAF
 meta['status']='GENERATED_PD484_DATA_NX4_REQUIRES_NATIVE_PHYSICAL_AND_ELECTRICAL_CHECKS'
 meta.pop('native_reorder',None)
 meta['obsolete_parent_m3_cleanup']=cleanup_proof
 meta['data_replacement']=dict(previous_parent_gds_sha256=sha(old/'layout'/(TOP+'.gds')),
  new_sampler_gds_sha256=sha(fresh/(LEAF+'.gds')),changed_native_reference_devices=sorted(changed))
 files=[p for name in ('baseline','data','inputs')for p in (out/name).rglob('*')if p.is_file()]+[out/'children.json']
 meta['inputs']={str(p):sha(p)for p in [Path(__file__),*files]}
 meta['outputs']={n:sha(dest/n)for n in (TOP+'.gds',TOP+'.lef','schematic.cir')}
 (dest/'result.json').write_text(json.dumps(meta,indent=2)+'\n')
 faults=[]
 bad=(dict(after[0]),after[1],after[2]);key=next(k for k,v in bad[0].items()if not v.is_empty());bad[0][key]=pya.Region()
 try:compare(snap,bad)
 except AssertionError:faults.append('removed_parent_geometry')
 else:raise AssertionError('Parent geometry fault accepted')
 bad=(after[0],after[1],after[2][:-1])
 try:compare(snap,bad)
 except AssertionError:faults.append('removed_parent_instance')
 else:raise AssertionError('Parent hierarchy fault accepted')
 assert len(faults)==2
 proof=dict(status='PASS_SERIALIZED_PARENT_WITH_DECLARED_M3_CLEANUP_AND_FOUR_NATIVE_DATA4_SAMPLERS',
  actual_sampler_instances=4,changed_reference_devices=sorted(changed),parent_geometry_unchanged=False,obsolete_parent_m3_cleanup=cleanup_proof,
  removed_child_port_annotations=removed,original_children_had_no_port_annotations=True,
  external_leaf_ports_and_bbox_unchanged=True,serialized_native_check=True,controls=faults,
  full_phy_accepted=False,qualified_pex=False)
 (out/'replacement-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
if __name__=='__main__':main()
