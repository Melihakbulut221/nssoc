#!/usr/bin/env python3
"""Validate exact mixed resize/buffer candidate including clock signal types."""
import os,json
from pathlib import Path
import odb
from buffer_core_only_chip_controls import load,identity,geom,connections
out=Path(os.environ['NSSOC_CORE_TARGETED_ECO_OUT']);d0,b0=load(out/'core-routed.odb');d1,b1=load(out/'eco-legalized.odb');p=json.loads((out/'eco-plan.json').read_text())
old={i.getName():i for i in b0.getInsts()};new={i.getName():i for i in b1.getInsts()};assert len(old)==105239 and set(new)==set(old)|set(p['new_buffers'])and len(p['new_buffers'])==6
assert geom(b0)==geom(b1);moves={}
for net in b0.getNets():
 current=b1.findNet(net.getName());assert current and str(current.getSigType())==str(net.getSigType()),('original_net_type',net.getName())
for name,i in old.items():
 j=new[name]
 if name not in p['resizes']:assert identity(i)==identity(j),name
 else:
  assert str(j.getOrient()) in {'R0','R180','MX','MY'},('illegal_resize_orientation',name,str(j.getOrient()))
  change=p['resizes'][name];assert i.getMaster().getName()==change['old']and j.getMaster().getName()==change['new']
  x,y=i.getLocation();xx,yy=j.getLocation();delta=(abs(x-xx)+abs(y-yy))/b1.getDbUnitsPerMicron();assert delta<=100;moves[name]=delta
  assert str(j.getPlacementStatus())=='PLACED'
expected=connections(b0);actual=connections(b1)
for key,net in expected.items():assert p['new_net_roots'].get(actual[key],actual[key])==net,(key,net,actual[key])
assert len(list(b1.getNets()))==len(list(b0.getNets()))+6
for target in p['branches']:
 name,pin=target['driver'].rsplit('/',1);driver=b1.findInst(name).findITerm(pin);net=driver.getNet();assert net.getName()==target['source_net']
 expected_inputs=set()
 for branch in target['branches']:
  i=new[branch['buffer']];assert i.getMaster().getName()==branch['master']and str(i.getPlacementStatus())=='PLACED'
  assert i.findITerm('A').getNet().getName()==net.getName();expected_inputs.add(i.getName()+'/A')
  wire=i.findITerm('X').getNet();assert wire.getName()==branch['net']and str(wire.getSigType())==branch['signal_type']and not list(wire.getBTerms())
  terms={t.getInst().getName()+'/'+t.getMTerm().getName()for t in wire.getITerms()};assert terms=={i.getName()+'/X'}|{'/'.join(k)for k in branch['sinks']}
  for pinname,rail in [('VDD','VPWR'),('VSS','VGND')]:assert i.findITerm(pinname).getNet().getName()==rail
 assert {t.getInst().getName()+'/'+t.getMTerm().getName()for t in net.getITerms()}=={target['driver']}|expected_inputs
for name,status in p['original_statuses'].items():new[name].setPlacementStatus(status)
for net in b1.getNets():net.clearGuides();assert not net.getWire()
odb.write_db(d1,str(out/'core-eco-placed-unrouted.odb'))
r=dict(new_buffers=6,resized_logic_cells=2,resize_displacement_um=moves,all_other_instances_geometry_preserved=True,original_terminal_classes_preserved=True,pins_and_power_geometry_preserved=True,branch_sinks_drivers_rails_and_signal_types_verified=True,all_original_antenna_cells_preserved=True,original_net_signal_types_preserved=True,resized_cell_orientations_legal=True,clock_buffers=3,clock_timing_requalification_required=True,antenna_requalification_required=True,accepted=False)
(out/'eco-audit.json').write_text(json.dumps(r,indent=2)+'\n')
