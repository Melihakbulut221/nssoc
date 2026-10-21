#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Replace four native samplers and fill eight same-net M4 notches."""
import argparse,copy,hashlib,json,re,shutil
from pathlib import Path
TOP='nssoc_cdr_pd476_follower_v23'
# Leaf keeps the serialized top name used by the actual verified v29 run.
LEAF='nssoc_rx_sampler_input_access_layout_v26'
OLDLEAF='nssoc_rx_sampler_input_access_layout_v26'
CHANGED_RESISTORS={'BP':(2.4,2.2),'BN':(2.4,2.2),**{n:(2.12,2.6)for n in ('M_RP','M_RN','S_RP','S_RN')}}
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
 # collector/retime trunks. Add only eight diagnosed same-component notch fills; no waiver.
 from repair_cdr_v29_parent_m4_notches import apply as repair_m4
 bridges,m4_proof=repair_m4(L,T,Path(__file__).resolve().parents[1]/'pdk/libs.tech/klayout/tech/sg13g2.lyp')
 L.write(str(dest/(TOP+'.gds')))
 R=pya.Layout();R.read(str(dest/(TOP+'.gds')));U=R.cell(TOP)
 after=parent_snapshot(R,U)
 def compare(a,b):
  assert a[1:]==b[1:],'Parent labels or transforms changed'
  assert a[0].keys()==b[0].keys()
  for layer in a[0]:
   expected=(a[0][layer]+bridges).merged() if layer==(50,0) else a[0][layer]
   assert (expected^b[0][layer]).is_empty(),('Unexpected parent metal change',layer)
 compare(snap,after)
 # Fresh serialized children are independently compared against all eight sources next.
 reference=(old/'layout/schematic.cir').read_text();lines=reference.splitlines(keepends=True)
 changed=[];targets={'R'+tag+'_'+s:limits for tag in ('sa','sb','sc','sd')for s,limits in CHANGED_RESISTORS.items()}
 for i,line in enumerate(lines):
  f=line.split()
  if f and f[0]in targets:
   previous,candidate=targets[f[0]]
   assert line.count(f' l={previous:g}u ')==1
   lines[i]=line.replace(f' l={previous:g}u ',f' l={candidate:g}u ');changed.append(f[0])
 assert set(changed)==set(targets)and len(changed)==24
 (dest/'schematic.cir').write_text(''.join(lines))
 shutil.copyfile(old/'layout'/(TOP+'.lef'),dest/(TOP+'.lef'))
 meta=copy.deepcopy(before);meta['source_plan']['types']['sampler']['top']=LEAF
 meta['status']='GENERATED_PD476_GAIN_HEADROOM_V29_REQUIRES_NATIVE_PHYSICAL_AND_ELECTRICAL_CHECKS'
 meta.pop('native_reorder',None)
 meta['v29_same_net_m4_notch_fill']=m4_proof
 meta['collector_and_bias_resistor_replacement']=dict(previous_parent_gds_sha256=sha(old/'layout'/(TOP+'.gds')),
  new_sampler_gds_sha256=sha(fresh/(LEAF+'.gds')),changed_native_reference_devices=sorted(changed))
 files=[p for name in ('baseline','data','inputs')for p in (out/name).rglob('*')if p.is_file()]+[out/'children.json']
 meta['inputs']={str(p):sha(p)for p in [Path(__file__),Path(__file__).with_name('repair_cdr_v29_parent_m4_notches.py'),Path(__file__).with_name('cdr-v29-parent-m4-diagnosis.json'),*files]}
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
 bad=(dict(after[0]),after[1],after[2]);bad[0][(50,0)]=snap[0][(50,0)]
 try:compare(snap,bad)
 except AssertionError:faults.append('missing_required_notch_fill')
 else:raise AssertionError('Missing notch fill accepted')
 assert len(faults)==3
 proof=dict(status='PASS_SERIALIZED_PARENT_PLUS_EIGHT_SAME_NET_NOTCH_FILLS_WITH_FOUR_NATIVE_V29_SAMPLERS',
  actual_sampler_instances=4,changed_reference_devices=sorted(changed),parent_geometry_unchanged=False,all_original_parent_geometry_retained=True,all_existing_collector_retime_trunks_retained=True,m4_notch_fill=m4_proof,
  removed_child_port_annotations=removed,original_children_had_no_port_annotations=True,
  external_leaf_ports_and_bbox_unchanged=True,serialized_native_check=True,controls=faults,
  full_phy_accepted=False,qualified_pex=False)
 (out/'replacement-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
if __name__=='__main__':main()
