#!/usr/bin/env python3
"""Read actual core-to-pad geometry and physical-only master signal inventory."""
import os,json,hashlib
from pathlib import Path
import odb
out=Path(os.environ['NSSOC_PARENT_CDC_OUT']);p=out/'chip-detailedroute.odb'
before=hashlib.sha256(p.read_bytes()).hexdigest()
db=odb.dbDatabase.create();odb.read_db(db,str(p));b=db.getChip().getBlock();scale=b.getDbUnitsPerMicron()
def box(r):return [r.xMin()/scale,r.yMin()/scale,r.xMax()/scale,r.yMax()/scale]
def term(t):
 i=t.getInst()
 return dict(pin=i.getName()+'/'+t.getMTerm().getName(),direction=str(t.getIoType()),master=i.getMaster().getName(),pin_bbox_um=box(t.getBBox()),instance_bbox_um=box(i.getBBox()),routing_shapes=[dict(layer=l.getName(),bbox_um=box(r))for l,r in t.getGeometries()if l.getRoutingLevel()>0])
core=b.findInst('u_core');assert core and core.getMaster().getName()=='soc_top'
rows=[]
for t in core.getITerms():
 if str(t.getIoType())!='OUTPUT' or str(t.getSigType())in ['POWER','GROUND'] or not t.getNet():continue
 net=t.getNet();drivers=[x for x in net.getITerms()if str(x.getIoType())=='OUTPUT']
 assert len(drivers)==1
 sinks=[x for x in net.getITerms()if x.getInst().getName()!='u_core']
 pads=[x for x in sinks if x.getInst().getMaster().getName().startswith('sg13g2_IOPad')and x.getMTerm().getName()in ['c2p','c2p_en']]
 if not pads:continue
 assert net.getWire()and str(net.getSigType())=='SIGNAL'
 rows.append(dict(net=net.getName(),driver=term(t),pad_sinks=[term(x)for x in pads],all_sinks=[term(x)for x in sinks],wire_length_um=net.getWire().getLength()/scale,boundary_ports=[x.getName()for x in net.getBTerms()]))
physical={}
for name in ['sg13g2_Corner','sg13g2_Filler10000','sg13g2_Filler4000','sg13g2_Filler200']:
 master=db.findMaster(name);assert master
 physical[name]=dict(instances=[i.getName()for i in b.getInsts()if i.getMaster().getName()==name],terminals=[dict(name=t.getName(),signal_type=str(t.getSigType()),direction=str(t.getIoType()))for t in master.getMTerms()])
violations=[line.split()[0]for line in (out/'slow-violations.rpt').read_text().splitlines()if '(VIOLATED)'in line]
report=dict(source_odb_sha256=before,source_unchanged=hashlib.sha256(p.read_bytes()).hexdigest()==before,instance_count=len(b.getInsts()),core_bbox_um=box(core.getBBox()),core_outputs_to_pads=rows,slow_slew_violations=len(violations),non_pad_slew_violations=[x for x in violations if not x.startswith('u_pad_')],physical_only_master_inventory=physical,accepted=False)
assert report['source_unchanged']and rows
(out/'electrical-inventory.json').write_text(json.dumps(report,indent=2)+'\n')
