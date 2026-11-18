#!/usr/bin/env python3
"""Buffer-only repair for measured slew drivers without larger library variants."""
import os,json
from pathlib import Path
import odb
from buffer_core_only_chip_controls import load,terminal_key
out=Path(os.environ['NSSOC_CORE_TARGETED_ECO_OUT']);d,b=load(out/'core-routed.odb');u=b.getDbUnitsPerMicron();assert len(list(b.getInsts()))==105251
statuses={i.getName():str(i.getPlacementStatus())for i in b.getInsts()};checks=(out/'slow-checks.rpt').read_text()
names=[('nssoc_sta_i_64237','Y'),('nssoc_sta_i_54306','Y'),('nssoc_sta_i_52754','Y'),('nssoc_sta_i_66325','Y'),('nssoc_sta_i_78908','Q')]
branches=[];roots={};buffers=[];drivers={};observed=[]
def xy(t):
 r=t.getBBox();assert r.xMax()>r.xMin()and r.yMax()>r.yMin();return ((r.xMin()+r.xMax())//2,(r.yMin()+r.yMax())//2)
for index,(name,pname)in enumerate(names):
 assert any(name+'/'+pname in line and 'VIOLATED'in line for line in checks.splitlines());inst=b.findInst(name);assert inst;driver=inst.findITerm(pname);assert driver and str(driver.getIoType())=='OUTPUT';net=driver.getNet();assert str(net.getSigType())=='SIGNAL'and not list(net.getBTerms());root=net.getName();assert root not in drivers;drivers[root]=[name,pname]
 assert [terminal_key(t)for t in net.getITerms()if str(t.getIoType())=='OUTPUT']==[(name,pname)]
 sinks=[t for t in net.getITerms()if terminal_key(t)!=(name,pname)];assert 1<=len(sinks)<=8 and all(str(t.getIoType())=='INPUT'for t in sinks)
 groups=[sinks]
 if index==4:
  assert len(sinks)>=2;axis=max(range(2),key=lambda a:max(xy(t)[a]for t in sinks)-min(xy(t)[a]for t in sinks));sinks.sort(key=lambda t:(xy(t)[axis],xy(t)[1-axis],terminal_key(t)));split=max(range(1,len(sinks)),key=lambda k:xy(sinks[k])[axis]-xy(sinks[k-1])[axis]);groups=[sinks[:split],sinks[split:]]
 px,py=xy(driver);observed.append(dict(driver=name+'/'+pname,master=inst.getMaster().getName(),original_sinks=len(sinks),driver_pin_center_um=[px/u,py/u]))
 for j,group in enumerate(groups):
  tag=f'nssoc_slewiso_{index}_{j}';assert not b.findInst(tag);cell=odb.dbInst.create(b,d.findMaster('sg13g2_buf_4'),tag);wire=odb.dbNet.create(b,tag+'_net');assert cell and wire;wire.setSigType('SIGNAL');cell.setLocation(px+(j+1)*8*u,py);cell.setPlacementStatus('PLACED');cell.findITerm('A').connect(net);cell.findITerm('X').connect(wire)
  for pin,rail in [('VDD','VPWR'),('VSS','VGND')]:cell.findITerm(pin).connect(b.findNet(rail))
  keys=[list(terminal_key(t))for t in group]
  for t in group:t.connect(wire)
  branches.append(dict(buffer=tag,master='sg13g2_buf_4',input_net=root,net=wire.getName(),sinks=keys));roots[wire.getName()]=root;buffers.append(tag)
for i in b.getInsts():
 if i.getName()in statuses and str(i.getPlacementStatus())=='PLACED':i.setPlacementStatus('FIRM')
removed=0
for net in b.getNets():
 net.clearGuides()
 if net.getWire():odb.dbWire.destroy(net.getWire());removed+=1
odb.write_db(d,str(out/'eco-before-legalize.odb'))
(out/'eco-plan.json').write_text(json.dumps(dict(resizes={},branches=branches,new_net_roots=roots,new_buffers=buffers,root_drivers=drivers,observed_drivers=observed,original_statuses=statuses,removed_stale_wires=removed,accepted=False),indent=2)+'\n')
