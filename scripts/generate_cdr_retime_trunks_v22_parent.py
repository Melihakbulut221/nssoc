#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Shorten four internal retime-input trunks without changing native leaves or pins."""
import argparse,copy,hashlib,json,re,shutil
from pathlib import Path
TOP='nssoc_cdr_pd484_localbus_v12'
TARGET_NETS=('cun','cup','dun','dup')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 import pya
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();out=a.out.resolve()
 old=out/'baseline/layout';dest=out/'layout';dest.mkdir(exist_ok=False)
 meta=json.loads((old/'result.json').read_text())
 assert sha(old/(TOP+'.gds'))=='3fdfff892b3c84d78349c7358699dfa2ec8fd98a98b887573beb4f4b3219c936'
 assert not(set(TARGET_NETS)&set(meta['source_plan']['ports']))
 L=pya.Layout();L.read(str(old/(TOP+'.gds')));T=L.cell(TOP)
 assert T is not None and L.dbu==.001
 def rect(s):
  v=list(map(float,re.findall(r'-?\d+(?:\.\d+)?',s)));assert len(v)==4
  return pya.DBox(*v)
 assert min(rect(p['bbox_um']).left for p in meta['placements'].values())==993.6
 def regions(top):
  return {(L.get_info(i).layer,L.get_info(i).datatype):pya.Region(top.shapes(i)).flatten().merged()
   for i in L.layer_indexes() if not pya.Region(top.shapes(i)).is_empty()}
 def snapshot(layout,top):
  shapes={};labels={}
  for i in layout.layer_indexes():
   key=(layout.get_info(i).layer,layout.get_info(i).datatype)
   r=pya.Region(top.shapes(i)).flatten().merged()
   if not r.is_empty():shapes[key]=r
   texts=sorted(str(s.text)for s in top.shapes(i).each()if s.is_text())
   if texts:labels[key]=texts
  instances=sorted((i.cell.name,str(i.dcplx_trans),i.na,i.nb,str(i.a),str(i.b))for i in top.each_inst())
  return shapes,labels,instances
 before=snapshot(L,T);old_bbox=T.dbbox()
 # Plan against actual flattened native metal, including wide AVDD shapes
 # outside macro bboxes. Disjoint vertical spans may reuse an X coordinate.
 retained_tm1=pya.Region(T.begin_shapes_rec(L.layer(126,0))).merged()
 spans={}
 for net in TARGET_NETS:
  boxes=[rect(r['box_um'])for r in meta['routes']if r['net']==net]
  xs={round(b.left+1.6,6)for b in boxes};assert len(xs)==1
  ox=xs.pop();ys=[b.center().y for b in boxes]
  original=pya.DBox(ox-1.6,min(ys)-1.6,ox+1.6,max(ys)+1.6)
  retained_tm1-=pya.Region(original.to_itype(L.dbu))
  spans[net]=(ox,min(ys),max(ys))
 clearance=1645 # conservative native1.64um spacing plus one5nm planning grid
 def corridor(x,y0,y1):
  return pya.Region(pya.DBox(x-1.6,y0-1.6,x+1.6,y1+1.6).to_itype(L.dbu))
 planned=pya.Region();targets={};selection=[]
 start=min(rect(p['bbox_um']).left for p in meta['placements'].values())-12.
 for net in TARGET_NETS:
  ox,y0,y1=spans[net];chosen=None
  for step in range(2000):
   x=round((start-step)/.005)*.005
   if x<=ox+20:break
   candidate=corridor(x,y0,y1)
   if (candidate.sized(clearance)&(retained_tm1+planned).merged()).is_empty():
    chosen=x;break
  assert chosen is not None,('No shorter DRC-spaced native TM1 corridor',net)
  targets[net]=chosen;planned+=corridor(chosen,y0,y1)
  selection.append(dict(net=net,original_x_um=ox,new_x_um=chosen,y_span_um=[y0,y1],skipped_grid_positions=step))
 assert (planned.sized(clearance)&retained_tm1).is_empty()
 known_short=pya.Region(pya.Box(963400,1324320,966600,2189410))
 assert not(known_short&retained_tm1).is_empty(),'Known native AVDD short must be rejected by corridor proof'
 corridor_proof=dict(actual_original_tm1_checked=True,foreign_metal_clearance_dbu=clearance,
   original_gds_sha256=sha(old/(TOP+'.gds')),selection=selection,
   prior_measured_avdd_short_rejected=True,disjoint_y_spans_may_reuse_x=True)
 changes=[];junction_changes=[];moved=[];total=0.;new_meta=copy.deepcopy(meta)
 def encloses(outer,inner):
  return outer.left<=inner.left and outer.bottom<=inner.bottom and outer.right>=inner.right and outer.top>=inner.top
 def replace_rectangle(layer,oldbox,newbox):
  li=L.layer(layer,0);ib=oldbox.to_itype(L.dbu);nb=newbox.to_itype(L.dbu)
  found=[s for s in T.shapes(li).each() if not s.is_text() and not s.is_edge() and s.bbox()==ib
    and pya.Region(s.polygon).area()==ib.area()]
  assert len(found)==1,('Expected one exact parent wire rectangle',layer,str(ib),len(found))
  found[0].delete();T.shapes(li).insert(nb)
  changes.append(dict(layer=layer,before_box_dbu=str(ib),after_box_dbu=str(nb)))
 for net,nx in targets.items():
  rows=[r for r in meta['routes']if r['net']==net]
  assert len(rows)==2
  boxes=[rect(r['box_um'])for r in rows];xs={round(b.left+1.6,6)for b in boxes}
  assert len(xs)==1;ox=xs.pop();ys=[b.center().y for b in boxes]
  assert nx>ox and all(abs(b.height()-3.2)<1e-7 and abs(b.right-989.2)<1e-7 for b in boxes)
  oldtrunk=pya.DBox(ox-1.6,min(ys)-1.6,ox+1.6,max(ys)+1.6)
  newtrunk=pya.DBox(nx-1.6,min(ys)-1.6,nx+1.6,max(ys)+1.6)
  replace_rectangle(126,oldtrunk,newtrunk)
  for row,b,y in zip(rows,boxes,ys,strict=True):
   assert row['layer']==134
   n=pya.DBox(nx-1.6,b.bottom,b.right,b.top);replace_rectangle(134,b,n)
   # Native v20 parent flattened junctions into top-level drawing polygons.
   # Move their exact cut and enclosure rectangles, not an invented via cell.
   window=pya.DBox(ox-2,y-2,ox+2,y+2).to_itype(L.dbu)
   cut=pya.DBox(ox-.45,y-.45,ox+.45,y+.45).to_itype(L.dbu)
   junction=[]
   # Native serialization merged metal enclosures into the long route
   # rectangles. Prove the full 3.2um enclosure square exists before/after;
   # the independent native deck still checks actual enclosure rules.
   enclosure=pya.DBox(ox-1.6,y-1.6,ox+1.6,y+1.6).to_itype(L.dbu)
   translated=enclosure.transformed(pya.Trans(round((nx-ox)/L.dbu),0))
   for metal in (126,134):
    assert (pya.Region(enclosure)-before[0][(metal,0)]).is_empty(),('Original enclosure absent',net,metal)
    current=pya.Region(T.shapes(L.layer(metal,0))).merged()
    assert (pya.Region(translated)-current).is_empty(),('New enclosure absent',net,metal)
    assert (pya.Region(cut)&current).is_empty(),('Unaccounted old junction metal',net,metal)
   for layer in (133,):
    found=[sh for sh in T.shapes(L.layer(layer,0)).each()
      if not sh.is_text() and encloses(window,sh.bbox()) and encloses(sh.bbox(),cut)]
    assert len(found)==1 and found[0].bbox()==cut,('Expected exact flattened native cut',net,ox,y)
    for sh in found:
     oldbox=sh.bbox();assert pya.Region(sh.polygon).area()==oldbox.area()
     newbox=oldbox.transformed(pya.Trans(round((nx-ox)/L.dbu),0))
     sh.delete();T.shapes(L.layer(layer,0)).insert(newbox)
     change=dict(layer=layer,before_box_dbu=str(oldbox),after_box_dbu=str(newbox))
     junction_changes.append(change);junction.append(change)
   moved.append(dict(net=net,representation='flattened_native_cut_with_enclosures_merged_in_route_rectangles',
      old_center_um=[ox,y],new_center_um=[nx,y],rectangles=junction))
   target=[v for v in new_meta['routes']if (v['net'],v['tag'],v['pin'])==(row['net'],row['tag'],row['pin'])]
   assert len(target)==1;target[0]['box_um']=str(n);total+=nx-ox
 assert len(changes)==12 and len(moved)==8 and total>2500
 assert T.dbbox()==old_bbox
 # The unchanged native deck independently checks all new spacing and connectivity.
 expected=snapshot(L,T)
 allowed={(126,0),(133,0),(134,0)}
 assert before[1:]==expected[1:],'All original labels and sixteen child instances must remain unchanged'
 assert before[0].keys()==expected[0].keys()
 for key in before[0]:
  if key not in allowed:assert (before[0][key]^expected[0][key]).is_empty()
 # Prove exact region delta consists only of the twelve declared rectangles.
 for key in allowed:
  r=before[0][key].dup()
  for c in [*changes,*junction_changes]:
   if c['layer']==key[0]:
    r-=pya.Region(pya.Box.from_s(c['before_box_dbu']))
    r+=pya.Region(pya.Box.from_s(c['after_box_dbu']))
  assert (r.merged()^expected[0][key]).is_empty(),('Undeclared parent edit',key)
 L.write(str(dest/(TOP+'.gds')))
 R=pya.Layout();R.read(str(dest/(TOP+'.gds')));U=R.cell(TOP);actual=snapshot(R,U)
 def equal(a,b):
  assert a[1:]==b[1:] and a[0].keys()==b[0].keys()
  for key in a[0]:assert (a[0][key]^b[0][key]).is_empty(),key
 equal(expected,actual)
 faults=[]
 bad=(dict(actual[0]),actual[1],actual[2]);bad[0][(126,0)]=pya.Region()
 try:equal(expected,bad)
 except AssertionError:faults.append('missing_parent_tm1')
 else:raise AssertionError('Missing trunk accepted')
 bad=(dict(actual[0]),actual[1],actual[2]);bad[0][(133,0)]=pya.Region()
 try:equal(expected,bad)
 except AssertionError:faults.append('missing_native_via')
 else:raise AssertionError('Missing via accepted')
 bad=(dict(actual[0]),actual[1],actual[2]);bad[0][(134,0)]=bad[0][(134,0)]+pya.Region(pya.Box(9999999,9999999,10000000,10000000))
 try:equal(expected,bad)
 except AssertionError:faults.append('undeclared_one_grid_metal')
 else:raise AssertionError('Extra metal accepted')
 for name in ('schematic.cir',TOP+'.lef'):shutil.copyfile(old/name,dest/name);assert sha(old/name)==sha(dest/name)
 proof=dict(status='SERIALIZED_FOUR_INTERNAL_RETIME_TRUNKS_REQUIRES_NATIVE_DRC_LVS_AND_FRESH_RC',
  targets_um=targets,native_corridor_proof=corridor_proof,changed_rectangles=changes,junction_rectangles=junction_changes,moved_native_tm1_tm2_vias=moved,
  horizontal_length_removed_um=total,primitive_parameters_unchanged=True,all_leaf_transforms_unchanged=True,
  schematic_and_lef_byte_identical=True,external_ports_unchanged=True,controls=faults,
  sources_unchanged=True,full_phy_accepted=False,qualified_pex=False)
 new_meta['status']=proof['status'];new_meta['retime_input_trunk_relocation']=proof
 new_meta['inputs']={str(p):sha(p)for p in [Path(__file__),*old.iterdir()]if p.is_file()}
 new_meta['outputs']={p.name:sha(p)for p in dest.iterdir()if p.is_file()}
 (dest/'result.json').write_text(json.dumps(new_meta,indent=2)+'\n')
 (out/'routing-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
if __name__=='__main__':main()
