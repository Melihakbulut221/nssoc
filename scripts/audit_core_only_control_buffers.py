#!/usr/bin/env python3
"""Verify legalized buffer ECO preserves every original instance and signal."""
import os,json
from pathlib import Path
from buffer_core_only_chip_controls import load,geom,identity,connections
OUT=Path(os.environ['NSSOC_CONTROL_BUFFER_OUT'])
r=json.loads((OUT/'buffer-eco.json').read_text());d0,b0=load(OUT/'chip-detailedroute.odb');d1,b1=load(OUT/'chip-buffered-placed.odb')
assert geom(b0)==geom(b1)
for name,old in r['original_instances'].items():assert list(identity(b1.findInst(name)))==old,name
actual=connections(b1);roots=r['new_net_roots']
for key,value in r['original_connections']:assert roots.get(actual[tuple(key)],actual[tuple(key)])==value,key
assert len(list(b1.getInsts()))==len(r['original_instances'])+len(r['new_buffers'])
for name in r['new_buffers']:
 i=b1.findInst(name);assert str(i.getPlacementStatus())=='PLACED'and i.getMaster().getName()in ('sg13g2_buf_4','sg13g2_buf_8')
 a=i.findITerm('A').getNet().getName();x=i.findITerm('X').getNet().getName();assert roots.get(a,a)==roots[x]
 assert i.findITerm('VDD').getNet().getName()=='VDD'and i.findITerm('VSS').getNet().getName()=='VSS'
# Trace actual buffer drivers rather than trusting recorded net-root aliases.
original_nets={n.getName()for n in b0.getNets()}
parents={}
for netname in roots:
 n=b1.findNet(netname);assert n
 drivers=[t for t in n.getITerms()if str(t.getIoType())=='OUTPUT']
 assert len(drivers)==1
 driver=drivers[0];assert driver.getInst().getName()in r['new_buffers']and driver.getMTerm().getName()=='X'
 parents[netname]=driver.getInst().findITerm('A').getNet().getName()
def trace(net,links):
 seen=set()
 while net in links:
  assert net not in seen,'Buffer cycle';seen.add(net);net=links[net]
 assert net in original_nets,'Unknown buffer source'
 return net
for net,expected in roots.items():assert trace(net,parents)==expected
for key,value in r['original_connections']:
 n=actual[tuple(key)]
 assert (trace(n,parents)if n is not None else None)==value,key
victim=next(iter(parents));bad=dict(parents);bad[victim]=victim
try:trace(victim,bad)
except AssertionError:pass
else:raise AssertionError('Buffer-cycle control not detected')
bad=dict(parents);bad[victim]='__missing_original_net__'
try:trace(victim,bad)
except AssertionError:pass
else:raise AssertionError('Unknown-source control not detected')

assert not any(n.getWire()for n in b1.getNets())
(OUT/'legalized-audit.json').write_text(json.dumps(dict(original_instance_geometry_unchanged=True,pins_and_special_geometry_unchanged=True,buffer_only_terminal_equivalence=True,actual_driver_graph_verified=True,cycle_and_unknown_source_controls=True,new_buffers=len(r['new_buffers']),targets=r['targets'],accepted=False,requires_fresh_route_and_extraction=True),indent=2)+'\n')
