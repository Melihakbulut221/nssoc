#!/usr/bin/env python3
"""Small measured-path resize candidate; exact connectivity and frozen surroundings."""
import os,json,re
from pathlib import Path
import odb
from buffer_core_only_chip_controls import load,identity,geom,connections
out=Path(os.environ['NSSOC_CRITICAL_ECO_OUT']);mode=os.environ['NSSOC_CRITICAL_ECO_MODE']
resize={name:('sg13g2_buf_1','sg13g2_buf_4') for name in ['fanout677','fanout657','fanout644','fanout541','nssoc_sta_i_59322']}
resize['nssoc_sta_i_15034']=('sg13g2_a21oi_1','sg13g2_a21oi_2')
d,b=load(out/'source.odb');assert len(list(b.getInsts()))==106083
if mode=='prepare':
 lib=(out/'std.lib').read_text()
 def function(name):
  m=re.search(r'cell\s*\(\s*"?'+re.escape(name)+r'"?\s*\)\s*\{',lib);assert m
  j=m.end();start=j;depth=1
  while depth:depth+=(lib[j]=='{')-(lib[j]=='}');j+=1
  funcs=re.findall(r'\bfunction\s*:\s*([^;]+)',lib[start:j]);assert len(funcs)==1
  return funcs[0]
 statuses={i.getName():str(i.getPlacementStatus())for i in b.getInsts()};before=connections(b);proof={}
 for name,(old,new)in resize.items():
  assert function(old)==function(new);i=b.findInst(name);master=d.findMaster(new)
  assert i and master and i.getMaster().getName()==old and statuses[name]=='PLACED'
  pins={(t.getMTerm().getName(),str(t.getIoType()),str(t.getSigType()))for t in i.getITerms()}
  assert i.swapMaster(master)
  assert pins=={(t.getMTerm().getName(),str(t.getIoType()),str(t.getSigType()))for t in i.getITerms()}
  proof[name]=dict(old=old,new=new,function=function(old))
 assert connections(b)==before
 for i in b.getInsts():
  if i.getName()not in resize and str(i.getPlacementStatus())=='PLACED':i.setPlacementStatus('FIRM')
 for n in b.getNets():
  n.clearGuides()
  if n.getWire():odb.dbWire.destroy(n.getWire())
 odb.write_db(d,str(out/'before-legalize.odb'))
 (out/'plan.json').write_text(json.dumps(dict(resizes=proof,original_statuses=statuses,accepted=False),indent=2)+'\n')
elif mode=='audit':
 dd,bb=load(out/'legalized.odb');plan=json.loads((out/'plan.json').read_text())
 old={i.getName():i for i in b.getInsts()};new={i.getName():i for i in bb.getInsts()};assert set(old)==set(new)
 assert geom(b)==geom(bb) and connections(b)==connections(bb)
 assert {(n.getName(),str(n.getSigType()))for n in b.getNets()}=={(n.getName(),str(n.getSigType()))for n in bb.getNets()}
 moves={};units=bb.getDbUnitsPerMicron()
 for name,i in old.items():
  j=new[name]
  if name not in resize:assert identity(i)==identity(j),name
  else:
   assert i.getMaster().getName()==resize[name][0] and j.getMaster().getName()==resize[name][1]
   assert str(j.getPlacementStatus())=='PLACED'
   x,y=i.getLocation();xx,yy=j.getLocation();moves[name]=(abs(x-xx)+abs(y-yy))/units;assert moves[name]<=100,(name,moves[name])
  j.setPlacementStatus(plan['original_statuses'][name])
 for n in bb.getNets():assert not n.getWire()
 odb.write_db(dd,str(out/'candidate-unrouted.odb'))
 (out/'audit.json').write_text(json.dumps(dict(accepted=False,instances=len(new),resized_cells=len(resize),displacement_um=moves,exact_terminal_connections=True,all_other_instances_preserved=True,net_types_preserved=True,special_wires_ports_die_preserved=True,all_antenna_cells_preserved=True,requires_new_routing_rc_timing=True),indent=2)+'\n')
else:raise ValueError(mode)
