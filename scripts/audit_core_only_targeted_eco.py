#!/usr/bin/env python3
"""Prove bounded resize/hold ECO against the exact routed baseline."""
import os,json
from pathlib import Path
import odb
from buffer_core_only_chip_controls import load,identity,geom,connections
out=Path(os.environ['NSSOC_CORE_TARGETED_ECO_OUT']);d0,b0=load(out/'core-routed.odb');d1,b1=load(out/'eco-legalized.odb');p=json.loads((out/'eco-plan.json').read_text())
old={i.getName():i for i in b0.getInsts()};new={i.getName():i for i in b1.getInsts()};assert set(new)==set(old)|set(p['hold_buffers'])
assert geom(b0)==geom(b1),'Original PG or boundary pin geometry changed'
selected=p['selected_buffers'];moves={}
for name,i in old.items():
 j=new[name]
 if name not in selected:assert identity(i)==identity(j),('Original instance changed',name)
 else:
  assert i.getMaster().getName()=='sg13g2_buf_1'and j.getMaster().getName()==p['new_master']
  x,y=i.getLocation();xx,yy=j.getLocation();move=(abs(x-xx)+abs(y-yy))/b1.getDbUnitsPerMicron();assert move<=100,('Nonlocal resized buffer',name,move);moves[name]=move
  assert str(j.getPlacementStatus())=='PLACED'
expected=connections(b0);actual=connections(b1)
# Reconnect the only moved original endpoint for exact original terminal comparison.
sink=b1.findInst('u_ram.g_ram_2048x64_ecc.u_b2').findITerm('A_MEN');last=b1.findNet(p['hold_buffers'][-1]+'_net');assert sink.getNet().getName()==last.getName()
for idx,name in enumerate(p['hold_buffers']):
 i=new[name];assert i.getMaster().getName()=='sg13g2_buf_1'and str(i.getPlacementStatus())=='PLACED'
 source=p['hold_source_net']if idx==0 else p['hold_buffers'][idx-1]+'_net'
 assert i.findITerm('A').getNet().getName()==source
 net=b1.findNet(name+'_net');assert i.findITerm('X').getNet().getName()==net.getName()
 target=p['hold_buffers'][idx+1]+'/A'if idx+1<len(p['hold_buffers'])else p['hold_sink']
 terms={t.getInst().getName()+'/'+t.getMTerm().getName()for t in net.getITerms()};assert terms=={name+'/X',target}and not list(net.getBTerms())
 for pin,rail in p['rails'].items():assert i.findITerm(pin).getNet()and i.findITerm(pin).getNet().getName()==rail
sink.disconnect();sink.connect(b1.findNet(p['hold_source_net']))
contracted=connections(b1)
for key,value in expected.items():assert contracted[key]==value,('Original terminal changed',key)
sink.disconnect();sink.connect(last)
assert len(list(b1.getNets()))==len(list(b0.getNets()))+len(p['hold_buffers'])
removed=0
for net in b1.getNets():
 net.clearGuides()
 if net.getWire():odb.dbWire.destroy(net.getWire());removed+=1
for name,status in p['original_statuses'].items():new[name].setPlacementStatus(status)
odb.write_db(d1,str(out/'core-eco-placed-unrouted.odb'))
r=dict(upsized_buffers=len(selected),upsized_locations_delta_um=moves,hold_buffers=len(p['hold_buffers']),original_other_instances_geometry_unchanged=True,original_pins_power_geometry_unchanged=True,buffer_only_function_preserved=True,exact_original_terminals_preserved_after_explicit_hold_chain_contraction=True,hold_chain_sources_sinks_and_power_verified=True,stale_routes_removed=removed,accepted=False,requires_fresh_route_rcx_all_corner_timing=True)
(out/'eco-audit.json').write_text(json.dumps(r,indent=2)+'\n')
