# SPDX-License-Identifier: Apache-2.0
"""Move named nets' TopMetal route guides down (TopMetal2 to Metal5, TopMetal1 to Metal4) and drop their wires (OpenROAD -python).

The foundry antenna deck flags gates that see a long TopMetal2 run (Ant.e_TopMetal2)
which the LEF antenna model accepts. Directions are kept (TopMetal2 and Metal5
horizontal, TopMetal1 and Metal4 vertical); each guide keeps its box, and the net's wire is destroyed
so the detailed router rebuilds it within the new guides. Clock, power and
special nets are refused. Nothing else in the database changes.
"""
import json,sys
import odb
from openroad import Design,Tech
src,names,dst,report=sys.argv[1:5]
t=Tech();d=Design(t);d.readDb(src);b=d.getBlock();tech=b.getTech()
down={'TopMetal2':tech.findLayer('Metal5'),'TopMetal1':tech.findLayer('Metal4')};out={}
for name in [l.strip()for l in open(names)if l.strip()]:
    n=b.findNet(name)
    if n is None:out[name]='missing';continue
    if n.isSpecial()or n.getSigType()in('POWER','GROUND','CLOCK')or name.startswith('clknet_'):raise SystemExit(f'refusing {name}')
    moved=0;kept=0
    for g in list(n.getGuides()):
        target=down.get(g.getLayer().getName())
        if target is not None:
            via=g.getViaLayer()
            if via is not None and via.getName()in down:via=down[via.getName()]
            odb.dbGuide.create(n,target,via,g.getBox(),g.isCongested());odb.dbGuide.destroy(g);moved+=1
        else:kept+=1
    if n.getWire()is not None:odb.dbWire.destroy(n.getWire())
    out[name]=dict(moved_guides=moved,kept_guides=kept)
json.dump(out,open(report,'w'),indent=1);print('NSSOC_RELAYER',json.dumps(out))
d.writeDb(dst)
