#!/usr/bin/env python3
"""Preserve all original placements/connections and inventory native supply geometry."""
import os,json
from pathlib import Path
import odb
out=Path(os.environ['NSSOC_PDN_OUT'])
def load(n):
    db=odb.dbDatabase.create();odb.read_db(db,str(out/n));return db,db.getChip().getBlock()
def snapshot(b):
    return dict(instances=sorted((i.getName(),i.getMaster().getName(),str(i.getPlacementStatus()),str(i.getOrient()),i.getBBox().xMin(),i.getBBox().yMin(),i.getBBox().xMax(),i.getBBox().yMax())for i in b.getInsts()),connections=sorted((i.getName(),t.getMTerm().getName(),t.getNet().getName()if t.getNet()else None)for i in b.getInsts()for t in i.getITerms()),ports=sorted((t.getName(),t.getNet().getName(),str(t.getIoType()),str(t.getSigType()))for t in b.getBTerms()))
d0,b0=load('chip-cts.odb');d1,b1=load('chip-pdn.odb');assert snapshot(b0)==snapshot(b1)
rails={}
for name in ['VDD','VSS','IOVDD','IOVSS']:
    n=b1.findNet(name);assert n and n.getName()==name
    rails[name]=dict(terminals=len(list(n.getITerms())),special_wires=len(list(n.getSWires())),special_boxes=sum(len(list(w.getWires()))for w in n.getSWires()))
assert rails['VDD']['special_boxes']>0 and rails['VSS']['special_boxes']>0
report=dict(instances=len(list(b1.getInsts())),placements_and_connections_unchanged=True,supply_geometry=rails,distinct_logical_supply_nets=True,physical_shorts_checked=False,ir_em_qualified=False,accepted=False)
(out/'pdn-audit.json').write_text(json.dumps(report,indent=2)+'\n')
