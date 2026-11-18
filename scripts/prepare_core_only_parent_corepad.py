#!/usr/bin/env python3
"""Place core-output isolation and perimeter chains without changing logical nets."""
import os,json,math
from pathlib import Path
import odb
out=Path(os.environ['NSSOC_PAD_REPAIR_OUT'])
db=odb.dbDatabase.create();odb.read_db(db,str(out/'chip-detailedroute.odb'));b=db.getChip().getBlock();scale=b.getDbUnitsPerMicron()
inv=json.loads((out/'electrical-inventory.json').read_text())
assert inv['instance_count']==2045 and len(b.getInsts())==2045
rows=inv['core_outputs_to_pads'];assert len(rows)==79
core=b.findInst('u_core');assert core
r=core.getBBox();cb=[r.xMin()/scale,r.yMin()/scale,r.xMax()/scale,r.yMax()/scale]
assert cb==inv['core_bbox_um']==[336.96,362.88,3663.36,2838.78]
L,B,R,T=cb[0]-24,cb[1]-24,cb[2]+24,cb[3]+24
W=R-L;H=T-B;P=2*(W+H)
def center(t):
 q=t.getBBox();return [(q.xMin()+q.xMax())/(2*scale),(q.yMin()+q.yMax())/(2*scale)]
def project(p,source=False):
 x,y=p
 candidates=[[L,min(T,max(B,y))],[R,min(T,max(B,y))],[min(R,max(L,x)),B],[min(R,max(L,x)),T]]
 if source:
  distances=[abs(x-cb[0]),abs(x-cb[2]),abs(y-cb[1]),abs(y-cb[3])]
  index=min(range(4),key=lambda k:distances[k]);assert distances[index]<=.5
  return candidates[index]
 return min(candidates,key=lambda q:abs(q[0]-x)+abs(q[1]-y))
def parameter(p):
 x,y=p
 if abs(y-B)<1e-6:return x-L
 if abs(x-R)<1e-6:return W+y-B
 if abs(y-T)<1e-6:return W+H+R-x
 assert abs(x-L)<1e-6
 return 2*W+H+T-y
def point(t):
 t=t%P
 if t<=W:return [L+t,B]
 if t<=W+H:return [R,B+t-W]
 if t<=2*W+H:return [R-(t-W-H),T]
 return [L,T-(t-2*W-H)]
def path(a,z):
 sa,sz=parameter(a),parameter(z);cw=(sz-sa)%P
 sign=1 if cw<=P-cw else -1;distance=min(cw,P-cw)
 events=[]
 for c in [0,W,W+H,2*W+H]:
  d=((c-sa)if sign==1 else(sa-c))%P
  if 1e-6<d<distance-1e-6:events.append(d)
 vertices=[a]+[point(sa+sign*d)for d in sorted(events)]+[z]
 points=[a]
 for p,q in zip(vertices,vertices[1:]):
  dx,dy=q[0]-p[0],q[1]-p[1];assert abs(dx)<1e-6 or abs(dy)<1e-6
  length=abs(dx)+abs(dy)
  if length<1e-6:continue
  n=math.ceil(length/300)
  points.extend([[p[k]+(q[k]-p[k])*j/n for k in range(2)]for j in range(1,n+1)])
 return points
flags={n.getName():n.isDoNotTouch()for n in b.getNets()}
statuses={i.getName():str(i.getPlacementStatus())for i in b.getInsts()}
for i in b.getInsts():
 if str(i.getPlacementStatus())=='PLACED':i.setPlacementStatus('FIRM')
for n in b.getNets():
 n.clearGuides()
 if n.getWire():odb.dbWire.destroy(n.getWire())
master=db.findMaster('sg13g2_buf_4');assert master
targets={};placements={};chains={}
for index,row in enumerate(sorted(rows,key=lambda x:x['net'])):
 driver=core.findITerm(row['driver']['pin'].split('/',1)[1]);assert driver and str(driver.getIoType())=='OUTPUT'
 net=driver.getNet();assert net and net.getName()==row['net']and str(net.getSigType())=='SIGNAL'
 ds=[t for t in net.getITerms()if str(t.getIoType())=='OUTPUT'];assert len(ds)==1 and ds[0].getInst().getName()=='u_core'
 assert len(row['pad_sinks'])==1
 name,port=row['pad_sinks'][0]['pin'].rsplit('/',1);pad=b.findInst(name);assert pad
 sink=pad.findITerm(port);assert sink and sink.getNet().getName()==net.getName()and port in ['c2p','c2p_en']
 source=center(driver);dest=center(sink)
 points=path(project(source,True),project(dest))
 assert sum(abs(a-z)for a,z in zip(source,points[0]))<25
 assert sum(abs(a-z)for a,z in zip(dest,points[-1]))<400
 targets[net.getName()]=dict(driver=row['driver']['pin'],violating_pins=[row['pad_sinks'][0]['pin']],measured_wire_length_um=row['wire_length_um'],core_output_isolation=True)
 current=net;names=[]
 for j,(x,y)in enumerate(points):
  name=f'nssoc_corepad_{index}_{j}';assert not b.findInst(name)
  i=odb.dbInst.create(b,master,name);assert i
  i.setLocation(round((x-master.getWidth()/(2*scale))*scale),round((y-master.getHeight()/(2*scale))*scale));i.setPlacementStatus('PLACED')
  n=odb.dbNet.create(b,name+'_net');assert n;n.setSigType('SIGNAL')
  i.findITerm('A').connect(current);i.findITerm('X').connect(n)
  i.findITerm('VDD').connect(b.findNet('VDD'));i.findITerm('VSS').connect(b.findNet('VSS'))
  placements[name]=dict(center_um=[x,y],source_net=net.getName(),source_pin=row['driver']['pin'],first=j==0,last=j==len(points)-1)
  current=n;names.append(name)
 sink.connect(current);chains[net.getName()]=dict(buffers=names,source_pin=row['driver']['pin'],sink_pin=row['pad_sinks'][0]['pin'])
assert 79<=len(placements)<=2000
odb.write_db(db,str(out/'repair-input.odb'))
(out/'repair-selection.json').write_text(json.dumps(dict(targets=targets,original_net_flags=flags,original_placement_statuses=statuses,planned_buffers=placements,core_bbox_um=cb,chains=chains,frame_bbox_um=[L,B,R,T],max_planned_segment_um=300,accepted=False),indent=2)+'\n')
