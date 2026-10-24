#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read immutable native target geometry; never alter the layout."""
import copy,json,os,sys
from pathlib import Path
from run_cloud_tx_layout_repair import sha
TOP='nssoc_tx_output8088_parent_v1'
METALS=(8,10,30,50,67,126,134)
VIAS=(19,29,49,66,125,133)
TARGETS=('A11588','A11580','A10612','A10592','A11583','A11591','A10615','A10595','A0856','A0877')
def main(out):
 import pya
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 source=out/'native';gds=source/'source/layout/layout.gds';db=source/'source/flat_lvs/result.lvsdb'
 L=pya.Layout();L.read(str(gds));T=L.cell(TOP);assert T is not None and L.dbu==.001
 native=pya.LayoutVsSchematic();native.read(str(db));c=native.netlist().circuit_by_name(TOP)
 devices={d.id():d for d in c.each_device()};assert len(devices)==8088
 wire=pya.LayoutToNetlist();wire.read(str(source/'native01/wires.l2n'))
 geom=json.loads((source/'native01/result.json').read_text())
 mapping={int(k):v for k,v in geom['native_layer_mapping'].items()}
 owner={v['component']:v['native_cluster']for v in geom['wire_components']}
 anchors=json.loads((out/'anchors/composed/intrinsic/source/anchors.json').read_text())
 ar={a['label']:a for a in anchors['anchors']};assert len(ar)==13370
 rows=anchors['rows']
 flat={m:pya.Region(T.begin_shapes_rec(L.layer(m,0))).merged()for m in (*METALS,*VIAS)}
 def record(r):
  r=r.merged();return dict(area_dbu2=r.area(),bbox_dbu=str(r.bbox()),polygons=[str(p)for p in r.each()])
 def match(a):
  p=pya.Point(*a['point_dbu']);m=a['metal']
  nn=native.probe_net(native.layer_by_index(mapping[m]),p)
  wn=wire.probe_net(wire.layer_by_name('gds_'+str(m)),p)
  assert nn is not None and wn is not None and nn.cluster_id==a['native_cluster']and wn.cluster_id==a['wire_component']
  assert owner[wn.cluster_id]==nn.cluster_id
  return nn
 def validate(a):
  nn=match(a);hits=[r for r in rows if r.get('reference_label')==a['label']]
  assert hits
  for r in hits:
   d=devices[r['device']];td=next(t for t in d.device_class().terminal_definitions()if t.name==r['terminal'])
   assert d.device_class().name==r['model']and d.net_for_terminal(td.id()).cluster_id==nn.cluster_id
   assert r['point_dbu']==a['point_dbu']and r['metal']==a['metal']
  return hits
 faults=[]
 a=copy.deepcopy(ar[TARGETS[0]])
 for kind in ('off_conductor','wrong_native_cluster','wrong_wire_component','swapped_anchor_identity'):
  bad=copy.deepcopy(a)
  if kind=='off_conductor':bad['point_dbu']=[-99999999,-99999999]
  elif kind=='wrong_native_cluster':bad['native_cluster']=-1
  elif kind=='wrong_wire_component':bad['wire_component']=-1
  else:bad['label']='A11583'
  try:validate(bad)
  except AssertionError:faults.append(dict(fault=kind,rejected=True))
  else:raise AssertionError('Accepted '+kind)
 def dist(box,p):
  return max(box.left-p.x,0,p.x-box.right)**2+max(box.bottom-p.y,0,p.y-box.top)**2
 def walk(cell,tr,path,window,found):
  if not cell.bbox().transformed(tr).overlaps(window):return
  own={}
  for m in (*METALS,*VIAS):
   r=pya.Region(cell.shapes(L.layer(m,0))).transformed(tr)&pya.Region(window)
   if not r.is_empty():own[str(m)]=record(r)
  if own:found.append(dict(path=path,cell=cell.name,transform=str(tr),bbox_dbu=str(cell.bbox().transformed(tr)),own_shapes=own))
  for inst in cell.each_inst():
   for i in range(max(1,inst.na)):
    for j in range(max(1,inst.nb)):
     off=pya.Trans(i*inst.a.x+j*inst.b.x,i*inst.a.y+j*inst.b.y)
     walk(inst.cell,tr*off*inst.trans,path+'/'+inst.cell.name+':'+str(i)+','+str(j),window,found)
 result=dict(status='READING',accepted=False,full_phy_accepted=False,dbu_um=L.dbu,targets={},negative_controls=faults)
 for label in TARGETS:
  a=ar[label];hit=validate(a);net=match(a);p=pya.Point(*a['point_dbu'])
  window=pya.Box(p.x-60000,p.y-60000,p.x+60000,p.y+60000)
  target=dict(anchor=a,terminals=hit,window_dbu=str(window),metals={},vias={})
  for m in METALS:
   same=native.shapes_of_net(net,native.layer_by_index(mapping[m]),True).merged()
   # Independently compare local same-net extracted shapes to actual drawn metal.
   local=same&pya.Region(window);assert(local-flat[m]).is_empty()
   nearest=sorted(list(same.each()),key=lambda poly:dist(poly.bbox(),p))[:3]
   target['metals'][str(m)]=dict(same_net_local=record(local),foreign_local=record((flat[m]-same)&pya.Region(window)),
    nearest_same_net=[dict(distance_lower_bound_dbu2=dist(poly.bbox(),p),geometry=record(pya.Region(poly)))for poly in nearest])
  for m in VIAS:target['vias'][str(m)]=record(flat[m]&pya.Region(window))
  found=[];walk(T,pya.Trans(),TOP,window,found);target['hierarchy']=found
  result['targets'][label]=target
  (out/'geometry.json').write_text(json.dumps(result,indent=2)+'\n')
  print(label,'native cluster',net.cluster_id,'hierarchy cells',len(found),flush=True)
 result['status']='COMPLETE_IMMUTABLE_NATIVE_RAIL_ACCESS_GEOMETRY_NOT_REPAIR'
 result['source_hashes']={str(p.relative_to(out)):sha(p)for p in (gds,db,source/'native01/wires.l2n',out/'anchors/composed/intrinsic/source/anchors.json')}
 (out/'geometry.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main(Path(sys.argv[1]).resolve())
