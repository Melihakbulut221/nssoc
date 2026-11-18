#!/usr/bin/env python3
"""Read-only native inventory; never substitutes for electrical closure."""
import os,json,hashlib
from pathlib import Path
import odb
out=Path(os.environ['NSSOC_PARENT_CDC_OUT'])
path=out/'chip-detailedroute.odb'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before=sha(path)
db=odb.dbDatabase.create();odb.read_db(db,str(path));b=db.getChip().getBlock()
scale=b.getDbUnitsPerMicron()
def box(rect):return [rect.xMin()/scale,rect.yMin()/scale,rect.xMax()/scale,rect.yMax()/scale]
def term(t):
 i=t.getInst()
 return dict(pin=i.getName()+'/'+t.getMTerm().getName(),direction=str(t.getIoType()),master=i.getMaster().getName(),instance_bbox_um=box(i.getBBox()),pin_bbox_um=box(t.getBBox()),placement_status=str(i.getPlacementStatus()))
rows=[];known=[]
for line in (out/'slow-violations.rpt').read_text().splitlines():
 if '(VIOLATED)' not in line:continue
 values=line.split();pin=values[0];name,port=pin.rsplit('/',1)
 inst=b.findInst(name);assert inst
 t=inst.findITerm(port);assert t and t.getNet()
 net=t.getNet();ts=[term(x)for x in net.getITerms()]
 drivers=[x for x in ts if x['direction']=='OUTPUT']
 row=dict(pin=pin,limit_ns=float(values[1]),slew_ns=float(values[2]),slack_ns=float(values[3]),net=net.getName(),net_type=str(net.getSigType()),terminals=ts,boundary_ports=[x.getName()for x in net.getBTerms()],has_wire=bool(net.getWire()))
 if net.getWire():row['wire_length_um']=net.getWire().getLength()/scale
 if name.startswith('wire'):
  assert len(drivers)==1 and drivers[0]['master']=='sg13g2_buf_4'
  known.append(net.getName())
 row['driver_class']='core_output_missing_timing_model'if any(x['master']=='soc_top'for x in drivers)else 'native_cell_driver'if drivers else 'boundary_or_bidirectional'
 rows.append(row)
assert len(rows)==53
result=dict(source_odb_sha256=before,source_unchanged=sha(path)==before,instance_count=len(b.getInsts()),violation_count=len(rows),known_buffer_nets=sorted(known),db_units_per_micron=scale,die_bbox_um=box(b.getDieArea()),placement_rows=[dict(name=r.getName(),bbox_um=box(r.getBBox()),orientation=str(r.getOrient()))for r in b.getRows()],violations=rows,accepted=False)
assert result['source_unchanged']
(out/'electrical-inventory.json').write_text(json.dumps(result,indent=2)+'\n')
