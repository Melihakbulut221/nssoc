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
# pdngen -dont_add_pins removes BPin geometry on the generated domain.
# Restore only the authenticated external pad geometry, never mesh proxy ports.
def pin_shapes(b):
    return {t.getName():sorted((str(p.getPlacementStatus()),sorted((x.getTechLayer().getName(),x.xMin(),x.yMin(),x.xMax(),x.yMax())for x in p.getBoxes()))for p in t.getBPins())for t in b.getBTerms()}
original=pin_shapes(b0);before=pin_shapes(b1);restored=[]
for name in original:
    if original[name]==before[name]:continue
    assert name in ['VDD','VSS'] and not before[name] and original[name],('Unexpected top pin change',name)
    terminal=b1.findBTerm(name)
    for placement,boxes in original[name]:
        bp=odb.dbBPin.create(terminal);bp.setPlacementStatus(placement)
        for layer,x0,y0,x1,y1 in boxes:
            odb.dbBox.create(bp,d1.getTech().findLayer(layer),x0,y0,x1,y1)
    restored.append(name)
assert pin_shapes(b1)==original
odb.write_db(d1,str(out/'chip-pdn.odb'));odb.write_def(b1,str(out/'chip-pdn.def'))
d2,b2=load('chip-pdn.odb');assert snapshot(b2)==snapshot(b0) and pin_shapes(b2)==original

rails={}
for name in ['VDD','VSS','IOVDD','IOVSS']:
    n=b1.findNet(name);assert n and n.getName()==name
    rails[name]=dict(terminals=len(list(n.getITerms())),special_wires=len(list(n.getSWires())),special_boxes=sum(len(list(w.getWires()))for w in n.getSWires()))
assert rails['VDD']['special_boxes']>0 and rails['VSS']['special_boxes']>0
report=dict(instances=len(list(b1.getInsts())),placements_and_connections_unchanged=True,top_pin_shapes_unchanged=True,restored_original_supply_pins=restored,readback_equal=True,supply_geometry=rails,distinct_logical_supply_nets=True,physical_shorts_checked=False,ir_em_qualified=False,accepted=False)
(out/'pdn-audit.json').write_text(json.dumps(report,indent=2)+'\n')
