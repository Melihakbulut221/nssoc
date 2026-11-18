#!/usr/bin/env python3
"""Explicit remaining electrical candidate; retain all cells and antenna loads."""
import os,json,re
from pathlib import Path
import odb
from buffer_core_only_chip_controls import load,center,terminal_key
out=Path(os.environ['NSSOC_CORE_TARGETED_ECO_OUT']);d,b=load(out/'core-routed.odb');assert len(list(b.getInsts()))==105239
statuses={i.getName():str(i.getPlacementStatus())for i in b.getInsts()}
resize={'nssoc_sta_i_66156':['sg13g2_nor4_1','sg13g2_nor4_2'],'nssoc_sta_i_8532':['sg13g2_a21oi_1','sg13g2_a21oi_2']}
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
 oldpins={(t.getMTerm().getName(),str(t.getIoType()),str(t.getSigType()))for t in i.getITerms()}
 assert i.swapMaster(master)
 assert oldpins=={(t.getMTerm().getName(),str(t.getIoType()),str(t.getSigType()))for t in i.getITerms()}
 proof[name]=dict(old=old,new=new,function=function(old))
targets=[('clkbuf_6_31_0_clk_npu','X',3,'sg13g2_buf_8','CLOCK'),('nssoc_sta_i_78595','Q',2,'sg13g2_buf_4','SIGNAL'),('u_ram.g_ram_2048x64_ecc.u_b1','A_DOUT[0]',1,'sg13g2_buf_4','SIGNAL')]
plan=[];buffers=[];roots={}
for index,(name,pin,count,mastername,sig)in enumerate(targets):
 inst=b.findInst(name);assert inst;driver=inst.findITerm(pin);assert driver and str(driver.getIoType())=='OUTPUT';net=driver.getNet();assert net and str(net.getSigType())==sig and not list(net.getBTerms())
 drivers=[terminal_key(t)for t in net.getITerms()if str(t.getIoType())=='OUTPUT'];assert drivers==[(name,pin)]
 sinks=[t for t in net.getITerms()if terminal_key(t)!=(name,pin)];assert all(str(t.getIoType())=='INPUT'for t in sinks)
 if sig=='CLOCK':
  assert net.getName()=='clknet_6_31_0_clk_npu'and len(sinks)==17
  logic=sorted([t for t in sinks if str(t.getInst().getMaster().getType())!='CORE_ANTENNACELL'],key=center)
  antenna=sorted([t for t in sinks if str(t.getInst().getMaster().getType())=='CORE_ANTENNACELL'],key=center)
  assert len(logic)==6 and len(antenna)==11
  groups=[logic[k::count]for k in range(count)]
  for t in antenna:
   point=center(t)
   def distance(group):return sum(abs(point[a]-sum(center(x)[a]for x in group)//len(group))for a in range(2))
   group=min([g for g in groups if len(g)<8],key=distance);group.append(t)
 else:
  assert len(sinks)>=count
  sinks.sort(key=center);groups=[sinks[k::count]for k in range(count)]
 assert all(0<len(g)<=8 for g in groups)
 branches=[]
 for k,group in enumerate(groups):
  tag=f'nssoc_residualbuf_{index}_{k}';assert not b.findInst(tag)
  cell=odb.dbInst.create(b,d.findMaster(mastername),tag);wire=odb.dbNet.create(b,tag+'_net');assert cell and wire;wire.setSigType(sig)
  if sig=='CLOCK':
   avg=tuple(sum(center(t)[a]for t in group)//len(group)for a in range(2));anchor=min(group,key=lambda t:sum(abs(center(t)[a]-avg[a])for a in range(2))).getInst();x,y=anchor.getLocation();cell.setOrient(anchor.getOrient())
  else:x,y=inst.getLocation();x+=(k+1)*2*b.getDbUnitsPerMicron();cell.setOrient(inst.getOrient())
  cell.setLocation(x,y);cell.setPlacementStatus('PLACED');cell.findITerm('A').connect(net);cell.findITerm('X').connect(wire)
  for pinname,power in [('VDD','VPWR'),('VSS','VGND')]:assert b.findNet(power);cell.findITerm(pinname).connect(b.findNet(power))
  keys=[list(terminal_key(t))for t in group]
  for t in group:t.connect(wire)
  roots[wire.getName()]=net.getName();buffers.append(tag);branches.append(dict(buffer=tag,net=wire.getName(),master=mastername,sinks=keys,signal_type=sig))
 plan.append(dict(driver=name+'/'+pin,source_net=net.getName(),branches=branches))
for i in b.getInsts():
 if i.getName()in statuses and i.getName()not in resize and str(i.getPlacementStatus())=='PLACED':i.setPlacementStatus('FIRM')
for n in b.getNets():
 n.clearGuides()
 assert not n.getWire()
odb.write_db(d,str(out/'eco-before-legalize.odb'))
(out/'eco-plan.json').write_text(json.dumps(dict(resizes=proof,branches=plan,new_buffers=buffers,new_net_roots=roots,original_statuses=statuses,accepted=False),indent=2)+'\n')
