#!/usr/bin/env python3
"""Measured pin-aware signal repair and targeted timing-margin candidate."""
import os,json,re
from pathlib import Path
import odb
from buffer_core_only_chip_controls import load,terminal_key
out=Path(os.environ['NSSOC_CORE_TARGETED_ECO_OUT']);d,b=load(out/'core-routed.odb');u=b.getDbUnitsPerMicron();assert len(list(b.getInsts()))==105245
statuses={i.getName():str(i.getPlacementStatus())for i in b.getInsts()}
resize={'nssoc_sta_i_8470':['sg13g2_a21oi_1','sg13g2_a21oi_2'],'fanout4263':['sg13g2_buf_1','sg13g2_buf_4'],'nssoc_sta_i_27642':['sg13g2_buf_1','sg13g2_buf_4'],'fanout478':['sg13g2_buf_1','sg13g2_buf_4']}
lib=(out/'std.lib').read_text()
def function(name):
 m=re.search(r'cell\s*\(\s*"?'+re.escape(name)+r'"?\s*\)\s*\{',lib);assert m
 j=m.end();start=j;depth=1
 while depth:depth+=(lib[j]=='{')-(lib[j]=='}');j+=1
 funcs=re.findall(r'\bfunction\s*:\s*([^;]+)',lib[start:j]);assert len(funcs)==1
 return funcs[0]
proof={}
for name,(old,new)in resize.items():
 assert function(old)==function(new);i=b.findInst(name);master=d.findMaster(new);assert i and master and i.getMaster().getName()==old
 pins={(t.getMTerm().getName(),str(t.getIoType()),str(t.getSigType()))for t in i.getITerms()};assert i.swapMaster(master)
 assert pins=={(t.getMTerm().getName(),str(t.getIoType()),str(t.getSigType()))for t in i.getITerms()}
 i.setPlacementStatus('PLACED');proof[name]=dict(old=old,new=new,function=function(old))
def xy(t):
 r=t.getBBox();assert r.xMax()>r.xMin()and r.yMax()>r.yMin();return ((r.xMin()+r.xMax())//2,(r.yMin()+r.yMax())//2)
macro=b.findInst('u_ram.g_ram_2048x64_ecc.u_b1');pin=macro.findITerm('A_DOUT[0]');iso=b.findInst('nssoc_residualbuf_2_0');assert iso and iso.getMaster().getName()=='sg13g2_buf_4'
assert iso.findITerm('A').getNet().getName()==pin.getNet().getName()
px,py=xy(pin);oldxy=xy(iso.findITerm('A'));iso.setPlacementStatus('PLACED');iso.setOrient('R0');iso.setLocation(px-2*u,macro.getBBox().yMax()+12*u)
relocation=dict(instance=iso.getName(),driver=list(terminal_key(pin)),before_pin_distance_um=(abs(oldxy[0]-px)+abs(oldxy[1]-py))/u,max_final_pin_distance_um=75)
branches=[];roots={};buffers=[];root_drivers={}
def add(tag,master,source,root,sinks,point):
 assert not b.findInst(tag);i=odb.dbInst.create(b,d.findMaster(master),tag);net=odb.dbNet.create(b,tag+'_net');assert i and net;net.setSigType('SIGNAL')
 i.setLocation(*point);i.setPlacementStatus('PLACED');i.findITerm('A').connect(source);i.findITerm('X').connect(net)
 for pname,rail in [('VDD','VPWR'),('VSS','VGND')]:i.findITerm(pname).connect(b.findNet(rail))
 keys=[list(terminal_key(t))for t in sinks]
 for t in sinks:t.connect(net)
 branches.append(dict(buffer=tag,master=master,input_net=source.getName(),net=net.getName(),sinks=keys));roots[net.getName()]=root;buffers.append(tag)
 return i,net
for idx,(name,pname)in enumerate([('nssoc_sta_i_10894','X'),('nssoc_sta_i_78691','Q')]):
 driver=b.findInst(name).findITerm(pname);net=driver.getNet();assert str(net.getSigType())=='SIGNAL'and not list(net.getBTerms());root=net.getName();root_drivers[root]=[name,pname]
 assert [terminal_key(t)for t in net.getITerms()if str(t.getIoType())=='OUTPUT']==[(name,pname)]
 sinks=[t for t in net.getITerms()if terminal_key(t)!=(name,pname)];assert len(sinks)==(8 if idx==0 else 7)and all(str(t.getIoType())=='INPUT'for t in sinks)
 axis=max(range(2),key=lambda a:max(xy(t)[a]for t in sinks)-min(xy(t)[a]for t in sinks));sinks.sort(key=lambda t:(xy(t)[axis],xy(t)[1-axis],terminal_key(t)))
 split=max(range(1,len(sinks)),key=lambda k:xy(sinks[k])[axis]-xy(sinks[k-1])[axis]);groups=[sinks[:split],sinks[split:]];px,py=xy(driver)
 for j,group in enumerate(groups):add(f'nssoc_pinbuf_{idx}_{j}','sg13g2_buf_4',net,root,group,(px+(j+1)*8*u,py))
driver=b.findInst('nssoc_sta_i_45238').findITerm('Y');sink=b.findInst('nssoc_sta_i_77169').findITerm('D');net=driver.getNet();assert net.getName()=='nssoc_sta_n_6892'and sink.getNet().getName()==net.getName()
assert {terminal_key(t)for t in net.getITerms()}=={terminal_key(driver),terminal_key(sink)};root=net.getName();root_drivers[root]=list(terminal_key(driver));px,py=xy(sink)
first,wire=add('nssoc_margin_hold_0','sg13g2_buf_1',net,root,[],(px+4*u,py))
second,wire2=add('nssoc_margin_hold_1','sg13g2_buf_1',wire,root,[sink],(px+8*u,py));branches[-2]['sinks']=[[second.getName(),'A']]
for i in b.getInsts():
 if i.getName()in statuses and i.getName()not in resize and i.getName()!=iso.getName()and str(i.getPlacementStatus())=='PLACED':i.setPlacementStatus('FIRM')
removed=0
for net in b.getNets():
 net.clearGuides()
 if net.getWire():odb.dbWire.destroy(net.getWire());removed+=1
odb.write_db(d,str(out/'eco-before-legalize.odb'))
(out/'eco-plan.json').write_text(json.dumps(dict(resizes=proof,relocation=relocation,branches=branches,new_net_roots=roots,new_buffers=buffers,root_drivers=root_drivers,original_statuses=statuses,removed_stale_wires=removed,accepted=False),indent=2)+'\n')
