#!/usr/bin/env python3
"""Strengthen four measured slew drivers and split the final cap-violating net."""
import os,json,re
from pathlib import Path
import odb
from buffer_core_only_chip_controls import load,terminal_key
out=Path(os.environ['NSSOC_CORE_TARGETED_ECO_OUT']);d,b=load(out/'core-routed.odb');u=b.getDbUnitsPerMicron();assert len(list(b.getInsts()))==105251
statuses={i.getName():str(i.getPlacementStatus())for i in b.getInsts()};lib=(out/'std.lib').read_text();checks=(out/'slow-checks.rpt').read_text()
names=['nssoc_sta_i_64237','nssoc_sta_i_54306','nssoc_sta_i_52754','nssoc_sta_i_66325']
def function(name):
 m=re.search(r'cell\s*\(\s*"?'+re.escape(name)+r'"?\s*\)\s*\{',lib);assert m
 j=m.end();start=j;depth=1
 while depth:depth+=(lib[j]=='{')-(lib[j]=='}');j+=1
 funcs=re.findall(r'\bfunction\s*:\s*([^;]+)',lib[start:j]);assert len(funcs)==1
 return funcs[0]
proof={}
for name in names:
 assert any(name+'/Y'in line and 'VIOLATED'in line for line in checks.splitlines())
 i=b.findInst(name);assert i and str(i.getMaster().getType())=='CORE'and str(i.findITerm('Y').getIoType())=='OUTPUT';old=i.getMaster().getName();prefix,strength=old.rsplit('_',1);strength=int(strength)
 choices=[prefix+'_'+str(x)for x in [1,2,4,8,16]if x>strength and d.findMaster(prefix+'_'+str(x))];assert choices,old;new=choices[0];assert function(old)==function(new)
 pins={(t.getMTerm().getName(),str(t.getIoType()),str(t.getSigType()))for t in i.getITerms()};assert i.swapMaster(d.findMaster(new));assert pins=={(t.getMTerm().getName(),str(t.getIoType()),str(t.getSigType()))for t in i.getITerms()};i.setPlacementStatus('PLACED');proof[name]=dict(old=old,new=new,function=function(old))
def xy(t):
 r=t.getBBox();assert r.xMax()>r.xMin()and r.yMax()>r.yMin();return ((r.xMin()+r.xMax())//2,(r.yMin()+r.yMax())//2)
name='nssoc_sta_i_78908';pname='Q';assert any(name+'/'+pname in line and 'VIOLATED'in line for line in checks.splitlines());driver=b.findInst(name).findITerm(pname);net=driver.getNet();assert str(net.getSigType())=='SIGNAL'and not list(net.getBTerms());root=net.getName()
assert [terminal_key(t)for t in net.getITerms()if str(t.getIoType())=='OUTPUT']==[(name,pname)]
sinks=[t for t in net.getITerms()if terminal_key(t)!=(name,pname)];assert 2<=len(sinks)<=8 and all(str(t.getIoType())=='INPUT'for t in sinks)
axis=max(range(2),key=lambda a:max(xy(t)[a]for t in sinks)-min(xy(t)[a]for t in sinks));sinks.sort(key=lambda t:(xy(t)[axis],xy(t)[1-axis],terminal_key(t)));split=max(range(1,len(sinks)),key=lambda k:xy(sinks[k])[axis]-xy(sinks[k-1])[axis]);groups=[sinks[:split],sinks[split:]];px,py=xy(driver)
branches=[];roots={};buffers=[]
for j,group in enumerate(groups):
 tag=f'nssoc_slewcapbuf_{j}';assert not b.findInst(tag);cell=odb.dbInst.create(b,d.findMaster('sg13g2_buf_4'),tag);wire=odb.dbNet.create(b,tag+'_net');wire.setSigType('SIGNAL');cell.setLocation(px+(j+1)*8*u,py);cell.setPlacementStatus('PLACED');cell.findITerm('A').connect(net);cell.findITerm('X').connect(wire)
 for pin,rail in [('VDD','VPWR'),('VSS','VGND')]:cell.findITerm(pin).connect(b.findNet(rail))
 keys=[list(terminal_key(t))for t in group]
 for t in group:t.connect(wire)
 branches.append(dict(buffer=tag,master='sg13g2_buf_4',input_net=root,net=wire.getName(),sinks=keys));roots[wire.getName()]=root;buffers.append(tag)
for i in b.getInsts():
 if i.getName()in statuses and i.getName()not in names and str(i.getPlacementStatus())=='PLACED':i.setPlacementStatus('FIRM')
removed=0
for net in b.getNets():
 net.clearGuides()
 if net.getWire():odb.dbWire.destroy(net.getWire());removed+=1
odb.write_db(d,str(out/'eco-before-legalize.odb'))
(out/'eco-plan.json').write_text(json.dumps(dict(resizes=proof,branches=branches,new_net_roots=roots,new_buffers=buffers,root_drivers={root:[name,pname]},original_statuses=statuses,removed_stale_wires=removed,accepted=False),indent=2)+'\n')
