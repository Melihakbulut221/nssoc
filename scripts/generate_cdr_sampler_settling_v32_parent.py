#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Replace only four actual sampler leaves; preserve every parent polygon."""
import argparse,copy,hashlib,json,shutil
from pathlib import Path
TOP='nssoc_cdr_pd476_follower_v23'
LEAF='nssoc_rx_sampler_input_access_layout_v26'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 import pya
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();out=a.out.resolve()
 old=out/'baseline';fresh=out/'data/layout';dest=out/'layout';dest.mkdir(exist_ok=False)
 before=json.loads((old/'layout/result.json').read_text())
 oldleaf=json.loads((old/'inputs/sampler/layout/result.json').read_text())
 newleaf=json.loads((fresh/'result.json').read_text())
 assert oldleaf['bbox_um']==newleaf['bbox_um']==[0,0,1003,243.63]
 assert oldleaf['ports']==newleaf['ports'],'Different external pins require new routing'
 from check_cdr_sampler_settling_v32_geometry import check_records
 check_records(oldleaf,newleaf)
 L=pya.Layout();L.read(str(old/'layout'/(TOP+'.gds')))
 N=pya.Layout();N.read(str(fresh/(LEAF+'.gds')))
 T=L.cell(TOP);C=L.cell('pd_child_sampler');S=N.cell(LEAF)
 assert L.dbu==N.dbu==.001 and all(x is not None for x in (T,C,S))
 assert C.dbbox()==S.dbbox()
 def snapshot(layout,top):
  shapes={};texts={}
  for li in layout.layer_indexes():
   info=layout.get_info(li);key=(info.layer,info.datatype)
   reg=pya.Region(top.shapes(li)).flatten().merged()
   if not reg.is_empty():shapes[key]=reg
   rows=sorted(str(s.text)for s in top.shapes(li).each()if s.is_text())
   if rows:texts[key]=rows
  instances=sorted((i.cell.name,str(i.dcplx_trans),i.na,i.nb,str(i.a),str(i.b))for i in top.each_inst())
  return shapes,texts,instances
 snap=snapshot(L,T);bbox=T.dbbox()
 assert len(snap[2])==16 and sum(i.cell.name=='pd_child_sampler'for i in T.each_inst())==4
 metals=(8,10,30,50,67,126,134)
 for cell in L.each_cell():
  if cell.cell_index()==T.cell_index():continue
  for layer in metals:
   for dt in (2,25):assert cell.shapes(L.layer(layer,dt)).is_empty()
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
 assert T.dbbox()==bbox
 # No replay of historical M4 repairs: all existing parent metal stays exact.
 L.write(str(dest/(TOP+'.gds')))
 R=pya.Layout();R.read(str(dest/(TOP+'.gds')));U=R.cell(TOP);after=snapshot(R,U)
 def compare(a,b):
  assert a[1:]==b[1:],'Parent labels or transforms changed'
  assert a[0].keys()==b[0].keys()
  for layer in a[0]:assert(a[0][layer]^b[0][layer]).is_empty(),('Parent metal changed',layer)
 compare(snap,after);assert U.dbbox()==bbox
 reference=(old/'layout/schematic.cir').read_text();lines=reference.splitlines(keepends=True)
 dimensions={'BP':(4,1.1,.9),'BN':(4,1.1,.9),'S_BS':(1,12.8,6.4),'S_BH':(1,9.6,4.8)}
 targets={'R'+tag+'_'+device:values for tag in ('sa','sb','sc','sd')for device,values in dimensions.items()}
 changed=[]
 for i,line in enumerate(lines):
  f=line.split()
  if f and f[0]in targets:
   width,previous,candidate=targets[f[0]]
   assert line.count(f' l={previous:g}u ')==1 and f' w={width:g}u 'in line and ' rppd 'in line
   lines[i]=line.replace(f' l={previous:g}u ',f' l={candidate:g}u ');changed.append(f[0])
 assert set(changed)==set(targets)and len(changed)==16
 newreference=''.join(lines)
 assert sum(bool(l.split())and l[0]in 'QRCM'for l in lines)==476
 (dest/'schematic.cir').write_text(newreference)
 shutil.copyfile(old/'layout'/(TOP+'.lef'),dest/(TOP+'.lef'))
 meta=copy.deepcopy(before)
 assert meta['source_plan']['types']['sampler']['top']==LEAF
 assert meta['source_plan']['types']['sampler']['devices']==54
 meta['status']='GENERATED_PD476_SAMPLER_SETTLING_V32_REQUIRES_NATIVE_PHYSICAL_AND_ELECTRICAL_CHECKS'
 meta['source_plan']['source_sha256'].pop('rx_sampler_input_impedance_v30.spice',None)
 meta['source_plan']['source_sha256']['rx_sampler_settling_v32.spice']=sha(Path.cwd()/'hw/soc/analog/pcie/rx_sampler_settling_v32.spice')
 meta['sampler_settling_replacement']=dict(previous_parent_gds_sha256=sha(old/'layout'/(TOP+'.gds')),
  new_sampler_gds_sha256=sha(fresh/(LEAF+'.gds')),changed_native_reference_devices=sorted(changed),
  actual_v31_follower_children_retained=True)
 files=[p for name in ('baseline','data','inputs')for p in(out/name).rglob('*')if p.is_file()]+[out/'children.json']
 meta['inputs']={str(p):sha(p)for p in[Path(__file__),*files]}
 meta['outputs']={n:sha(dest/n)for n in(TOP+'.gds',TOP+'.lef','schematic.cir')}
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
 bad=(dict(after[0]),after[1],after[2]);bad[0][(50,0)]=after[0][(50,0)]+pya.Region(pya.Box(-10000,-10000,-9000,-9000))
 try:compare(snap,bad)
 except AssertionError:faults.append('added_parent_metal')
 else:raise AssertionError('Added parent metal accepted')
 assert len(faults)==3
 proof=dict(status='PASS_SERIALIZED_PARENT_UNCHANGED_WITH_FOUR_NATIVE_V32_SAMPLER_LEAVES',
  actual_sampler_instances=4,changed_reference_devices=sorted(changed),parent_geometry_unchanged=True,
  all_original_parent_geometry_retained=True,all_existing_collector_retime_trunks_retained=True,
  removed_child_port_annotations=removed,original_children_had_no_port_annotations=True,
  external_leaf_ports_and_bbox_unchanged=True,serialized_native_check=True,controls=faults,
  full_phy_accepted=False,qualified_pex=False)
 (out/'replacement-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
if __name__=='__main__':main()
