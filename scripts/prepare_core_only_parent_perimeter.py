#!/usr/bin/env python3
"""Split four measured long parent nets along the left core perimeter."""
import os,json,math
from pathlib import Path
import odb
out=Path(os.environ['NSSOC_PAD_REPAIR_OUT'])
db=odb.dbDatabase.create();odb.read_db(db,str(out/'chip-detailedroute.odb'));b=db.getChip().getBlock()
scale=b.getDbUnitsPerMicron()
inv=json.loads((out/'electrical-inventory.json').read_text())
assert inv['instance_count']==1975 and len(b.getInsts())==1975
rows=[r for r in inv['violations']if r['pin'].startswith('wire')]
assert sorted(r['net']for r in rows)==['net73','net78','net83','net89']
flags={n.getName():n.isDoNotTouch()for n in b.getNets()}
statuses={i.getName():str(i.getPlacementStatus())for i in b.getInsts()}
for i in b.getInsts():
 if str(i.getPlacementStatus())=='PLACED':i.setPlacementStatus('FIRM')
for n in b.getNets():
 n.clearGuides()
 if n.getWire():odb.dbWire.destroy(n.getWire())
master=db.findMaster('sg13g2_buf_4');assert master
core=b.findInst('u_core');assert core
rect=core.getBBox();corebox=[rect.xMin()/scale,rect.yMin()/scale,rect.xMax()/scale,rect.yMax()/scale]
assert corebox==[336.96,362.88,3663.36,2838.78],corebox
targets={};placements={}
def center(t):
 q=t.getBBox();return [(q.xMin()+q.xMax())/(2*scale),(q.yMin()+q.yMax())/(2*scale)]
for index,row in enumerate(sorted(rows,key=lambda x:x['net'])):
 net=b.findNet(row['net']);assert net and str(net.getSigType())=='SIGNAL'
 its=list(net.getITerms());assert len(its)==2 and not list(net.getBTerms())
 drivers=[t for t in its if str(t.getIoType())=='OUTPUT'];sinks=[t for t in its if str(t.getIoType())=='INPUT']
 assert len(drivers)==len(sinks)==1
 driver,sink=drivers[0],sinks[0]
 source=center(driver);dest=center(sink)
 assert source[1]<corebox[1] and dest[1]>corebox[3]
 assert driver.getInst().getMaster().getName()==sink.getInst().getMaster().getName()=='sg13g2_buf_4'
 targets[net.getName()]=dict(driver=driver.getInst().getName()+'/'+driver.getMTerm().getName(),violating_pins=[row['pin']],measured_wire_length_um=row['wire_length_um'])
 # Explicit dogleg follows legal side-channel rows, instead of placing through the macro.
 left=280+index*7
 vertices=[source,[left,source[1]],[left,dest[1]],dest]
 points=[]
 for a,z in zip(vertices,vertices[1:]):
  distance=abs(z[0]-a[0])+abs(z[1]-a[1]);count=math.ceil(distance/400)
  for j in range(1,count+1):
   p=[a[k]+(z[k]-a[k])*j/count for k in range(2)]
   if p!=dest:points.append(p)
 current=net
 for j,(x,y)in enumerate(points):
  name=f'nssoc_perimeter_{index}_{j}';assert not b.findInst(name)
  inst=odb.dbInst.create(b,master,name);assert inst
  inst.setLocation(round((x-master.getWidth()/(2*scale))*scale),round((y-master.getHeight()/(2*scale))*scale))
  inst.setPlacementStatus('PLACED')
  n=odb.dbNet.create(b,name+'_net');assert n;n.setSigType('SIGNAL')
  inst.findITerm('A').connect(current);inst.findITerm('X').connect(n)
  inst.findITerm('VDD').connect(b.findNet('VDD'));inst.findITerm('VSS').connect(b.findNet('VSS'))
  placements[name]=dict(center_um=[x,y],source_net=net.getName());current=n
 sink.connect(current)
assert 40<=len(placements)<=80,len(placements)
odb.write_db(db,str(out/'repair-input.odb'))
selection=dict(targets=targets,original_net_flags=flags,original_placement_statuses=statuses,planned_buffers=placements,core_bbox_um=corebox,placement_strategy='left-perimeter chain with nominal segments at most 400um; native legalization must stay within 100um of requested point',accepted=False)
(out/'repair-selection.json').write_text(json.dumps(selection,indent=2)+'\n')
