#!/usr/bin/env python3
"""Diagnostic inter-net power-metal contact scan, not a foundry DRC deck."""
import os,json,gzip,hashlib
from pathlib import Path
from collections import defaultdict,Counter
import odb
out=Path(os.environ['NSSOC_PDN_SHORT_OUT']);db=odb.dbDatabase.create();odb.read_db(db,str(out/'chip-pdn.odb'));block=db.getChip().getBlock()
power={'VDD','VSS','IOVDD','IOVSS'};shapes=defaultdict(list)
def add(layer,net,source,box,dx=0,dy=0):
    if layer is None or layer.getRoutingLevel()==0:return
    rect=[box.xMin()+dx,box.yMin()+dy,box.xMax()+dx,box.yMax()+dy]
    assert rect[0]<rect[2] and rect[1]<rect[3]
    shapes[layer.getName()].append([*rect,net,source])
for inst in block.getInsts():
    for term in inst.getITerms():
        if not term.getNet():continue
        for layer,rect in term.getGeometries():add(layer,term.getNet().getName(),'pin:'+inst.getName()+'/'+term.getMTerm().getName(),rect)
for term in block.getBTerms():
    for pin in term.getBPins():
        for box in pin.getBoxes():
            assert not box.isVia();add(box.getTechLayer(),term.getNet().getName(),'port:'+term.getName(),box)
via_count=0
for net in block.getNets():
    for wire in net.getSWires():
        for box in wire.getWires():
            if box.isVia():
                via=box.getTechVia() or box.getBlockVia();assert via
                x,y=box.getViaXY();via_count+=1
                for vb in via.getBoxes():add(vb.getTechLayer(),net.getName(),'via:'+via.getName(),vb,x,y)
            else:add(box.getTechLayer(),net.getName(),'wire',box)
def contact(a,b):return a[0]<=b[2]and b[0]<=a[2]and a[1]<=b[3]and b[1]<=a[3]
assert contact([0,0,10,10],[10,5,20,8]) and contact([0,0,10,10],[5,5,15,15]) and not contact([0,0,10,10],[11,0,20,10])
counts=Counter();samples=[];scanned=0
for layer,rows in shapes.items():
    active=[]
    for row in sorted(rows):
        active=[x for x in active if x[2]>=row[0]]
        for prev in active:
            if prev[4]==row[4]or not({prev[4],row[4]}&power):continue
            scanned+=1
            if contact(prev,row):
                key=layer+':'+':'.join(sorted([prev[4],row[4]]));counts[key]+=1
                if len(samples)<100:samples.append(dict(layer=layer,a=prev,b=row))
        active.append(row)
with gzip.open(out/'metal-shapes.json.gz','wt')as f:json.dump(dict(dbu=db.getTech().getDbUnitsPerMicron(),layers=shapes),f)
report=dict(status='POWER_METAL_CONTACTS_FOUND'if counts else 'NO_POWER_METAL_CONTACTS_IN_SCANNED_ABSTRACT_GEOMETRY',source_odb_sha256=hashlib.sha256((out/'chip-pdn.odb').read_bytes()).hexdigest(),shapes_by_layer={k:len(v)for k,v in shapes.items()},expanded_vias=via_count,candidate_pairs=scanned,contact_pairs=sum(counts.values()),contacts_by_layer_and_netpair=dict(counts),samples=samples,geometry_controls_passed=True,accepted=False,foundry_drc_qualified=False,scope='Native special wires and expanded via routing-metal boxes plus transformed all ITerm/BTerm pin rectangles. Counts rectangle contact pairs, not unique electrical shorts. Excludes hidden macro GDS, spacing/enclosure and non-metal DRC rules.')
(out/'short-audit.json').write_text(json.dumps(report,indent=2)+'\n')
