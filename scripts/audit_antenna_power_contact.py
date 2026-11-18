#!/usr/bin/env python3
"""Direct LEF pin-to-special-rail contact for added diodes; not full PDN signoff."""
import json,os,hashlib
from pathlib import Path
from collections import defaultdict

def overlap(a,b):return min(a[2],b[2])>max(a[0],b[0])and min(a[3],b[3])>max(a[1],b[1])
def contacts(pins,rails,net):
 good=[];wrong=[]
 for layer,rect in pins:
  for rn,rr in rails.get(layer,[]):
   if overlap(rect,rr):(good if rn==net else wrong).append((layer,rn,rr))
 return good,wrong

def controls():
 pins=[('M1',(0,0,10,10))];rails={'M1':[('P',(0,0,20,4))]}
 assert contacts(pins,rails,'P')[0]
 assert not contacts(pins,{},'P')[0]
 assert not contacts(pins,{'M2':rails['M1']},'P')[0]
 assert contacts(pins,rails,'G')[1]and not contacts(pins,rails,'G')[0]
 assert not contacts([('M1',(20,20,30,30))],rails,'P')[0]
 assert not contacts([('M1',(20,4,30,10))],rails,'P')[0]
 return dict(positive_overlap=True,missing_rail_rejected=True,wrong_layer_rejected=True,wrong_supply_rejected=True,displaced_pin_rejected=True,point_contact_rejected=True)

def main():
 import odb
 path=Path(os.environ['ANTENNA_POWER_ODB']);out=Path(os.environ['ANTENNA_POWER_REPORT']);inventory=json.loads(Path(os.environ['ANTENNA_POWER_INVENTORY']).read_text())['new_cells']
 before=hashlib.sha256(path.read_bytes()).hexdigest();db=odb.dbDatabase.create();odb.read_db(db,str(path));block=db.getChip().getBlock();rails=defaultdict(list)
 def add(net,layer,r,dx=0,dy=0):
  if layer and layer.getRoutingLevel()>0:rails[layer.getName()].append((net,(r.xMin()+dx,r.yMin()+dy,r.xMax()+dx,r.yMax()+dy)))
 for net in block.getNets():
  if str(net.getSigType())not in ['POWER','GROUND']:continue
  for sw in net.getSWires():
   for box in sw.getWires():
    if box.isVia():
     via=box.getTechVia()or box.getBlockVia();assert via;dx,dy=box.getViaXY()
     for shape in via.getBoxes():add(net.getName(),shape.getTechLayer(),shape,dx,dy)
    else:add(net.getName(),box.getTechLayer(),box)
 expected=int(os.environ.get('ANTENNA_POWER_EXPECTED_DIODES','800'));assert expected>0 and len(inventory)==expected
 checked=[];failures=[];fault=None
 for name in sorted(inventory):
  inst=block.findInst(name);assert inst and inst.getMaster().getName()=='sg13g2_antennanp'
  terms=[t for t in inst.getITerms()if str(t.getMTerm().getSigType())in ['POWER','GROUND']];assert len(terms)==2
  for t in terms:
   label=name+'/'+t.getMTerm().getName();net=t.getNet();assert net and str(net.getSigType())==str(t.getMTerm().getSigType())
   pins=[(layer.getName(),(r.xMin(),r.yMin(),r.xMax(),r.yMax()))for layer,r in t.getGeometries()if layer.getRoutingLevel()>0]
   good,wrong=contacts(pins,rails,net.getName())
   rec=dict(terminal=label,net=net.getName(),pin_shapes=pins,matching_rail_contacts=len(good),wrong_supply_contacts=wrong)
   checked.append(rec)
   if not pins or not good or wrong:failures.append(rec)
   if fault is None and good and not wrong:
    reduced={layer:[x for x in rows if (layer,x[0],x[1])not in good]for layer,rows in rails.items()}
    assert not contacts(pins,reduced,net.getName())[0]
    fault=dict(terminal=label,removed_native_rail_shapes=len(good),loss_of_contact_detected=True)
 assert hashlib.sha256(path.read_bytes()).hexdigest()==before
 report=dict(accepted=False,source_odb_sha256=before,sources_unchanged=True,diodes=len(inventory),checked_power_terminals=len(checked),failures=failures,terminals=checked,synthetic_controls=controls(),native_rail_removal_control=fault,scope='Positive-area contact of added diode LEF power pins to same-net native special-wire metal/via landings. Does not establish global PDN connectivity, internal cell GDS, IR/EM, transistor LVS, or foundry signoff.')
 out.write_text(json.dumps(report,indent=2)+'\n')
 assert len(checked)==2*expected and not failures and fault,'Added diode physical supply contact incomplete'
if __name__=='__main__':main()
