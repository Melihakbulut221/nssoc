#!/usr/bin/env python3
"""Small measured-path resize candidate; exact connectivity and frozen surroundings."""
import os,json,re
from pathlib import Path
import odb
from buffer_core_only_chip_controls import load,identity,geom,connections
out=Path(os.environ['NSSOC_CRITICAL_ECO_OUT']);mode=os.environ['NSSOC_CRITICAL_ECO_MODE']
resize={'nssoc_sta_i_61007':('sg13g2_nor3_1','sg13g2_nor3_2'),'nssoc_sta_i_63722':('sg13g2_a21oi_1','sg13g2_a21oi_2')}
d,b=load(out/'source.odb');assert len(list(b.getInsts()))==106656
assert all(b.findInst(name) for name in resize)
invalidated={t.getNet().getName()for name in resize for t in b.findInst(name).getITerms()if str(t.getSigType())not in ['POWER','GROUND']}
assert 4<=len(invalidated)<=8
assert {'nssoc_sta_n_60783','nssoc_sta_n_63198'}<=invalidated
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
 assert {t.getNet().getName()for name in resize for t in b.findInst(name).getITerms()if str(t.getSigType())not in ['POWER','GROUND']}==invalidated
 for netname in invalidated:
  n=b.findNet(netname);assert str(n.getSigType())=='SIGNAL'
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
 def records(block,path):
  odb.write_def(block,str(path));text=path.read_text();m=re.search(r'^NETS (\d+) ;\n(.*?)^END NETS',text,re.M|re.S);assert m
  entries=re.findall(r'^[ \t]*- (\S+) (.*?);',m.group(2),re.M|re.S);r={n:' '.join(v.split())for n,v in entries};assert len(r)==len(entries)==int(m.group(1));return r
 left=records(b,out/'source-route-audit.def');right=records(bb,out/'candidate-route-audit.def');assert set(left)==set(right)
 checked=0
 for name,value in left.items():
  if name not in invalidated:assert right[name]==value,('unaffected_net_changed',name);checked+=1
 # DEF includes both VPWR and VGND records; the route guard separately excludes them.
 assert len(left)==103090 and checked==103090-len(invalidated),(len(left),checked)
 assert all(name in left for name in ['VPWR','VGND'])
 clocks=[n.getName()for n in b.getNets()if str(n.getSigType())=='CLOCK']
 assert len(clocks)==2113 and not set(clocks)&invalidated
 assert all(right[n]==left[n]for n in clocks)
 for name in invalidated:assert not bb.findNet(name).getWire()
 (out/'preserved-route-audit.json').write_text(json.dumps(dict(checked_net_records=checked,checked_clock_nets=len(clocks),invalidated_data_nets=sorted(invalidated),all_other_routes_preserved=True),indent=2)+'\n')
 (out/'power-inventory.json').write_text(json.dumps(dict(new_cells={name:dict(master=pair[1])for name,pair in resize.items()}),indent=2)+'\n')
 odb.write_db(dd,str(out/'candidate-partially-routed.odb'))
 (out/'audit.json').write_text(json.dumps(dict(accepted=False,instances=len(new),resized_cells=len(resize),displacement_um=moves,exact_terminal_connections=True,all_other_instances_preserved=True,net_types_preserved=True,special_wires_ports_die_preserved=True,all_antenna_cells_preserved=True,requires_new_routing_rc_timing=True),indent=2)+'\n')
else:raise ValueError(mode)
