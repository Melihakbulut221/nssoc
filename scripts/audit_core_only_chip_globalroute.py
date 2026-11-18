#!/usr/bin/env python3
import os,json
from pathlib import Path
import odb
out=Path(os.environ['NSSOC_CHIP_ROUTE_OUT'])
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
d0,b0=load('chip-pdn.odb');d1,b1=load('chip-globalroute.odb');assert snapshot(b0)==snapshot(b1)
guide_counts={n.getName():len(list(n.getGuides()))for n in b1.getNets()if list(n.getGuides())}
assert guide_counts and (out/'chip.guide').stat().st_size>0
unguided=[]
for n in b1.getNets():
    if str(n.getSigType())in['POWER','GROUND']:continue
    terminals=len(list(n.getITerms()))+len(list(n.getBTerms()))
    if terminals>1 and n.getName()not in guide_counts:unguided.append(dict(net=n.getName(),terminals=terminals))
report=dict(instances=len(list(b1.getInsts())),placements_connections_pin_shapes_and_power_geometry_unchanged=True,guided_nets=len(guide_counts),guide_rectangles=sum(guide_counts.values()),unguided_multi_terminal_nets=unguided,coverage_accepted=False,detailed_route=False,accepted=False)
(out/'route-audit.json').write_text(json.dumps(report,indent=2)+'\n')
