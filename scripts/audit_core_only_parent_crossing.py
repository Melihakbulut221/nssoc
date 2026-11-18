#!/usr/bin/env python3
"""Reject legalization that loses the intended perimeter placement."""
import os,json,hashlib
from pathlib import Path
import odb
out=Path(os.environ['NSSOC_PAD_REPAIR_OUT'])
p=out/'chip-pad-repair-unrouted.odb';before=hashlib.sha256(p.read_bytes()).hexdigest()
db=odb.dbDatabase.create();odb.read_db(db,str(p));b=db.getChip().getBlock();scale=b.getDbUnitsPerMicron()
selection=json.loads((out/'repair-selection.json').read_text());x0,y0,x1,y1=selection['core_bbox_um']
positions={}
for name,desired in selection['planned_buffers'].items():
 i=b.findInst(name);assert i and i.getMaster().getName()=='sg13g2_buf_4'
 r=i.getBBox();box=[r.xMin()/scale,r.yMin()/scale,r.xMax()/scale,r.yMax()/scale]
 assert box[2]<=x0 or box[0]>=x1 or box[3]<=y0 or box[1]>=y1,('Macro overlap',name,box)
 actual=[(box[0]+box[2])/2,(box[1]+box[3])/2]
 distance=sum(abs(a-z)for a,z in zip(actual,desired['center_um']))
 assert distance<=100,('Legalization lost perimeter corridor',name,distance)
 positions[name]=dict(bbox_um=box,displacement_um=distance)
assert len(b.getInsts())==2031+len(positions)
assert hashlib.sha256(p.read_bytes()).hexdigest()==before
(out/'perimeter-placement-audit.json').write_text(json.dumps(dict(new_buffers=len(positions),positions=positions,source_unchanged=True,source_sha256=before,accepted=False),indent=2)+'\n')
