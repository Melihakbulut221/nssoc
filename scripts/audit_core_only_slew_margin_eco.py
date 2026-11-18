#!/usr/bin/env python3
"""Exact original connectivity, unchanged clocks/PG, and pin-distance audit."""
import os,json
from pathlib import Path
import odb
from buffer_core_only_chip_controls import load,identity,geom,connections
out=Path(os.environ['NSSOC_CORE_TARGETED_ECO_OUT']);d0,b0=load(out/'core-routed.odb');d1,b1=load(out/'eco-legalized.odb');p=json.loads((out/'eco-plan.json').read_text());u=b1.getDbUnitsPerMicron()
old={i.getName():i for i in b0.getInsts()};new={i.getName():i for i in b1.getInsts()};assert len(old)==105251 and set(new)==set(old)|set(p['new_buffers'])and len(p['new_buffers'])==2
assert geom(b0)==geom(b1);moves={}
assert set(p['resizes'])=={'nssoc_sta_i_64237','nssoc_sta_i_54306','nssoc_sta_i_52754','nssoc_sta_i_66325'}
for name,i in old.items():
 j=new[name]
 if name not in p['resizes']:assert identity(i)==identity(j),name
 else:
  if name in p['resizes']:
   c=p['resizes'][name];assert i.getMaster().getName()==c['old']and j.getMaster().getName()==c['new'];x,y=i.getLocation();xx,yy=j.getLocation();moves[name]=(abs(x-xx)+abs(y-yy))/u;assert moves[name]<=100
  assert str(j.getPlacementStatus())=='PLACED'and str(j.getOrient())in {'R0','MX','MY','R180'}
for net in b0.getNets():assert str(b1.findNet(net.getName()).getSigType())==str(net.getSigType())
expected=connections(b0);actual=connections(b1)
for key,net in expected.items():assert p['new_net_roots'].get(actual[key],actual[key])==net,(key,net,actual[key])
assert len(list(b1.getNets()))==len(list(b0.getNets()))+2
for branch in p['branches']:
 i=new[branch['buffer']];assert i.getMaster().getName()==branch['master']and branch['master']in {'sg13g2_buf_1','sg13g2_buf_4'}and str(i.getPlacementStatus())=='PLACED'
 a=i.findITerm('A').getNet();wire=i.findITerm('X').getNet();assert a and a.getName()==branch['input_net']and wire and wire.getName()==branch['net']and str(wire.getSigType())=='SIGNAL'and not list(wire.getBTerms())
 assert {t.getInst().getName()+'/'+t.getMTerm().getName()for t in wire.getITerms()}=={i.getName()+'/X'}|{'/'.join(k)for k in branch['sinks']}
 for pin,rail in [('VDD','VPWR'),('VSS','VGND')]:n=i.findITerm(pin).getNet();assert n and n.getName()==rail
for root,driver in p['root_drivers'].items():
 net=b1.findNet(root);assert not list(net.getBTerms());wanted={'/'.join(driver)}|{x['buffer']+'/A'for x in p['branches']if x['input_net']==root};assert {t.getInst().getName()+'/'+t.getMTerm().getName()for t in net.getITerms()}==wanted
for name,status in p['original_statuses'].items():new[name].setPlacementStatus(status)
for net in b1.getNets():net.clearGuides();assert not net.getWire()
odb.write_db(d1,str(out/'core-eco-placed-unrouted.odb'))
r=dict(new_buffers=2,resized_cells=4,resize_displacement_um=moves,all_other_instance_geometry_preserved=True,original_terminal_classes_preserved=True,original_net_signal_types_preserved=True,pins_and_power_geometry_preserved=True,all_original_antenna_cells_preserved=True,clock_geometry_and_connectivity_preserved=True,accepted=False,timing_qualified=False)
(out/'eco-audit.json').write_text(json.dumps(r,indent=2)+'\n')
