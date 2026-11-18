#!/usr/bin/env python3
import os,json
from pathlib import Path
import odb
out=Path(os.environ['NSSOC_CHIP_DRT_OUT'])
def load(n):
    d=odb.dbDatabase.create();odb.read_db(d,str(out/n));return d,d.getChip().getBlock()
def snapshot(b):
    geometry=[]
    for n in b.getNets():
        for w in n.getSWires():
            for x in w.getWires():
                if x.isVia():
                    v=x.getTechVia()or x.getBlockVia();geometry.append((n.getName(),'via',v.getName(),*x.getViaXY()))
                else:geometry.append((n.getName(),'metal',x.getTechLayer().getName(),x.xMin(),x.yMin(),x.xMax(),x.yMax()))
    return dict(instances=sorted((i.getName(),i.getMaster().getName(),str(i.getPlacementStatus()),str(i.getOrient()),i.getBBox().xMin(),i.getBBox().yMin(),i.getBBox().xMax(),i.getBBox().yMax())for i in b.getInsts()),connections=sorted((i.getName(),t.getMTerm().getName(),t.getNet().getName()if t.getNet()else None)for i in b.getInsts()for t in i.getITerms()),pins=sorted((t.getName(),t.getNet().getName(),str(t.getIoType()),str(t.getSigType()),sorted((str(p.getPlacementStatus()),sorted((x.getTechLayer().getName(),x.xMin(),x.yMin(),x.xMax(),x.yMax())for x in p.getBoxes()))for p in t.getBPins()))for t in b.getBTerms()),special_geometry=sorted(geometry))
d0,b0=load('chip-globalroute.odb');d1,b1=load('chip-detailedroute.odb');assert snapshot(b0)==snapshot(b1)
assert all(b1.findNet(n).isSpecial()for n in ['VDD','VSS','IOVDD','IOVSS'])
guided={n.getName()for n in b0.getNets()if list(n.getGuides())};assert len(guided)==1691
unwired=sorted(n for n in guided if not b1.findNet(n).getWire())
report=dict(instances=len(list(b1.getInsts())),placements_connections_pin_shapes_and_power_geometry_unchanged=True,guided_nets=len(guided),unwired_guided_nets=unwired,wire_presence_is_not_connectivity_proof=True,accepted=False,extracted_timing=False)
(out/'route-audit.json').write_text(json.dumps(report,indent=2)+'\n')
