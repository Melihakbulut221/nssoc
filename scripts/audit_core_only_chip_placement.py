#!/usr/bin/env python3
"""Independently preserve native chip topology, fixed geometry and top pin shapes."""
import json,os
from pathlib import Path
import odb
out=Path(os.environ['NSSOC_PLACEMENT_OUT'])
def read(name):
    db=odb.dbDatabase.create();odb.read_db(db,str(out/name));return db,db.getChip().getBlock()
def rect(b):return [b.xMin(),b.yMin(),b.xMax(),b.yMax()]
def snapshot(b):
    instances={i.getName():[i.getMaster().getName(),str(i.getPlacementStatus()),str(i.getOrient()),rect(i.getBBox())]for i in b.getInsts()}
    connections=sorted((i.getName(),t.getMTerm().getName(),t.getNet().getName()if t.getNet()else None)for i in b.getInsts()for t in i.getITerms())
    pins=sorted((t.getName(),t.getNet().getName(),str(t.getIoType()),str(t.getSigType()),sorted((str(p.getPlacementStatus()),sorted((x.getTechLayer().getName(),rect(x))for x in p.getBoxes()))for p in t.getBPins()))for t in b.getBTerms())
    return instances,connections,pins,rect(b.getDieArea())
db0,b0=read('chip-initial.odb');db1,b1=read('chip-placed.odb')
a,c,p,d=snapshot(b0);aa,cc,pp,dd=snapshot(b1)
assert set(a)==set(aa) and c==cc and p==pp and d==dd
fixed=[n for n,x in a.items()if x[1]=='LOCKED'];movable=[n for n in a if n not in fixed]
assert len(fixed)==297 and len(movable)==1253
assert all(a[n]==aa[n]for n in fixed)
assert all(a[n][0]==aa[n][0] and aa[n][1]=='PLACED' for n in movable)
assert len(list(b1.getRows()))>0
# Independent rectangle checks supplement native row/site/spacing legality.
for n in movable:
    x=aa[n][3];assert d[0]<=x[0]<x[2]<=d[2] and d[1]<=x[1]<x[3]<=d[3]
    for m,y in aa.items():
        if m==n:continue
        z=y[3];assert min(x[2],z[2])<=max(x[0],z[0])or min(x[3],z[3])<=max(x[1],z[1]),('overlap',n,m)
odb.write_db(db1,str(out/'chip-readback.odb'));db2,b2=read('chip-readback.odb');assert snapshot(b2)==snapshot(b1)
(out/'audit.json').write_text(json.dumps(dict(fixed_instances=len(fixed),placed_shell_instances=len(movable),connections=len(c),top_pins=len(p),rows=len(list(b1.getRows())),fixed_geometry_unchanged=True,topology_unchanged=True,top_pin_shapes_unchanged=True,readback_equal=True,rectangle_overlap_count=0,accepted=False),indent=2)+'\n')
