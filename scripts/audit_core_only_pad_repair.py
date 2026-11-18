#!/usr/bin/env python3
"""Contract only genuine new buffers and prove original connectivity classes."""
import os,json,re
from pathlib import Path
import odb
from buffer_core_only_chip_controls import load,geom,identity,connections
out=Path(os.environ['NSSOC_PAD_REPAIR_OUT']);d0,b0=load(out/'chip-detailedroute.odb');d1,b1=load(out/'repair-placed.odb')
selection=json.loads((out/'repair-selection.json').read_text());old={i.getName():identity(i)for i in b0.getInsts()};new={i.getName():i for i in b1.getInsts()if i.getName()not in old}
changes=[n for n,v in old.items()if not b1.findInst(n)or identity(b1.findInst(n))!=v]
assert not changes,('Original instance changed',changes)
assert geom(b0)==geom(b1)
assert new,'No repair buffers inserted'
parent={}
def root(n):
 parent.setdefault(n,n)
 while parent[n]!=n:parent[n]=parent[parent[n]];n=parent[n]
 return n
def union(a,b):parent[root(a)]=root(b)
for name,i in new.items():
 assert re.fullmatch(r'sg13g2_buf_(1|2|4|8|16)',i.getMaster().getName()),('Non-buffer ECO',name,i.getMaster().getName())
 assert str(i.getPlacementStatus())=='PLACED'
 for p,n in [('VDD','VDD'),('VSS','VSS')]:
  term=i.findITerm(p);assert term and term.getNet(),('Missing new buffer power connection',name,p)
  assert term.getNet().getName()==n,('Wrong new buffer power rail',name,p)
 a=i.findITerm('A').getNet();x=i.findITerm('X').getNet();assert a and x;union(a.getName(),x.getName())
actual=connections(b1);expected=connections(b0);old_to_new={};new_to_old={}
for key,net in expected.items():
 value=actual[key];assert (net is None)==(value is None)
 if net is None:continue
 representative=root(value)
 assert old_to_new.setdefault(net,representative)==representative,('Original net split',key)
 assert new_to_old.setdefault(representative,net)==net,('Original nets shorted',key)
 if net not in selection['targets']:assert value==net,('Non-target connection changed',key)
# Reject directed buffer cycles, floating inputs and ambiguous drivers.
def upstream(name,seen):
 assert name not in seen,'Buffer cycle';seen=seen|{name};i=new[name]
 n=i.findITerm('A').getNet();drivers=[t for t in n.getITerms()if str(t.getIoType())=='OUTPUT'];assert len(drivers)==1
 t=drivers[0];other=t.getInst().getName()
 if other in new:return upstream(other,seen)
 assert other in old
 return other+'/'+t.getMTerm().getName()
allowed={x['driver']for x in selection['targets'].values()}
for name in new:assert upstream(name,set())in allowed,'Buffer not driven by selected pad'
for n in b1.getNets():
 n.setDoNotTouch(selection['original_net_flags'].get(n.getName(),False))
 n.clearGuides()
 if n.getWire():odb.dbWire.destroy(n.getWire())
for name,status in selection['original_placement_statuses'].items():b1.findInst(name).setPlacementStatus(status)
odb.write_db(d1,str(out/'chip-pad-repair-unrouted.odb'))
report=dict(new_buffers=len(new),buffer_masters=sorted({i.getMaster().getName()for i in new.values()}),original_instances_pins_and_power_geometry_unchanged=True,original_connectivity_classes_preserved=True,only_selected_pad_nets_modified=True,actual_buffer_sources_verified=True,stale_routes_removed=True,target_nets=selection['targets'],accepted=False,requires_fresh_routing_rcx_and_corner_timing=True)
(out/'repair-audit.json').write_text(json.dumps(report,indent=2)+'\n')
