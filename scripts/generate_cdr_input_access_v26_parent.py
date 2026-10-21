#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Replace four native samplers; retain every original parent polygon and other leaf."""
import argparse,copy,hashlib,json,re,shutil
from pathlib import Path
TOP='nssoc_cdr_pd476_follower_v23'
LEAF='nssoc_rx_sampler_input_access_layout_v26'
OLDLEAF='nssoc_rx_sampler_selector_small_layout_v24'
INPUT_RESISTORS={'IP','IN'}
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
 # Retain every original parent polygon, including already shortened
 # collector/retime trunks and the verified v23 cleanup. No cleanup waiver.
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
 changed=[];targets={'R'+tag+'_'+s for tag in ('sa','sb','sc','sd')for s in INPUT_RESISTORS}
 for i,line in enumerate(lines):
  f=line.split()
  if f and f[0]in targets:
   assert line.count(' l=3.6u ')==1
   lines[i]=line.replace(' l=3.6u ',' l=0.9u ');changed.append(f[0])
 assert set(changed)==targets and len(changed)==8
 (dest/'schematic.cir').write_text(''.join(lines))
 shutil.copyfile(old/'layout'/(TOP+'.lef'),dest/(TOP+'.lef'))
 meta=copy.deepcopy(before);meta['source_plan']['types']['sampler']['top']=LEAF
 meta['status']='GENERATED_PD476_INPUT_ACCESS_V26_REQUIRES_NATIVE_PHYSICAL_AND_ELECTRICAL_CHECKS'
 meta.pop('native_reorder',None)
 meta['input_resistor_replacement']=dict(previous_parent_gds_sha256=sha(old/'layout'/(TOP+'.gds')),
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
 proof=dict(status='PASS_SERIALIZED_UNCHANGED_PARENT_WITH_FOUR_NATIVE_INPUT_ACCESS_V26_SAMPLERS',
  actual_sampler_instances=4,changed_reference_devices=sorted(changed),parent_geometry_unchanged=True,all_existing_collector_retime_trunks_retained=True,
  removed_child_port_annotations=removed,original_children_had_no_port_annotations=True,
  external_leaf_ports_and_bbox_unchanged=True,serialized_native_check=True,controls=faults,
  full_phy_accepted=False,qualified_pex=False)
 (out/'replacement-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
if __name__=='__main__':main()
