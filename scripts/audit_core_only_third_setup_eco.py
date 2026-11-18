#!/usr/bin/env python3
"""Exact topology/geometry audit for the third setup-only buffer resize."""
import os,json
from pathlib import Path
import odb
from buffer_core_only_chip_controls import load,geom,identity,connections
out=Path(os.environ['NSSOC_CORE_TARGETED_ECO_OUT']);d0,b0=load(out/'core-routed.odb');d1,b1=load(out/'eco-legalized.odb');p=json.loads((out/'eco-plan.json').read_text())
old={i.getName():i for i in b0.getInsts()};new={i.getName():i for i in b1.getInsts()};assert set(old)==set(new)and len(old)==104891
assert geom(b0)==geom(b1)and connections(b0)==connections(b1)
moves={}
for name,i in old.items():
 j=new[name]
 if name not in p['selected_buffers']:assert identity(i)==identity(j),name
 else:
  assert i.getMaster().getName()=='sg13g2_buf_1'and j.getMaster().getName()=='sg13g2_buf_4'
  x,y=i.getLocation();xx,yy=j.getLocation();delta=(abs(x-xx)+abs(y-yy))/b1.getDbUnitsPerMicron();assert delta<=100
  assert str(j.getPlacementStatus())=='PLACED';moves[name]=delta
for n in b1.getNets():
 n.clearGuides()
 if n.getWire():odb.dbWire.destroy(n.getWire())
for name,status in p['original_statuses'].items():new[name].setPlacementStatus(status)
odb.write_db(d1,str(out/'core-eco-placed-unrouted.odb'))
(out/'eco-audit.json').write_text(json.dumps(dict(upsized_buffers=4,upsized_locations_delta_um=moves,all_original_terminals_preserved=True,all_other_instances_geometry_preserved=True,pins_and_power_geometry_preserved=True,no_instances_added_or_removed=True,previous_hold_chain_unchanged=True,stale_routes_removed=True,accepted=False,requires_fresh_route_rcx_all_corner_timing=True),indent=2)+'\n')
