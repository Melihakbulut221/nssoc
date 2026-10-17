#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Resolve measured output drivers against immutable146ODB; never write an ODB."""
import json
from pathlib import Path
import odb
from route_cloud_newer_postcts import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-route146-setup-margins'
p=ROOT/'cloud-refined-hold-eco/routed.odb'
assert sha(p)=='1e97e6c345d9529a7a40b9435a15b58382971d9c94d5f24ff18daaa3e381a747'
db=odb.dbDatabase.create();odb.read_db(db,str(p));block=db.getChip().getBlock()
assert len(block.getInsts())==113937 and len(block.getNets())==114009
rows=[]
for r in json.loads((OUT/'driver-requests.json').read_text()):
    name,pin=r['pin'].rsplit('/',1);inst=block.findInst(name)
    assert inst and inst.getMaster().getName()==r['master']
    terminal=inst.findITerm(pin);assert terminal and str(terminal.getIoType())=='OUTPUT'
    net=terminal.getNet();assert net and str(net.getSigType())=='SIGNAL'
    outputs=[t for t in net.getITerms()if str(t.getIoType())=='OUTPUT']
    assert len(outputs)==1 and outputs[0].getInst().getName()==name and outputs[0].getMTerm().getName()==pin
    sinks=[dict(instance=t.getInst().getName(),pin=t.getMTerm().getName(),master=t.getInst().getMaster().getName(),location_dbu=list(t.getInst().getLocation()))for t in net.getITerms()if str(t.getIoType())=='INPUT']
    assert sinks
    box=terminal.getBBox()
    rows.append(dict(r,net=net.getName(),net_iterm_count=len(net.getITerms()),sinks=sinks,location_dbu=list(inst.getLocation()),driver_pin_bbox_dbu=[box.xMin(),box.yMin(),box.xMax(),box.yMax()],ndr=net.getNonDefaultRule().getName()if net.getNonDefaultRule()else None,block_ports=[b.getName()for b in net.getBTerms()]))
assert len(rows)==15 and sha(p)=='1e97e6c345d9529a7a40b9435a15b58382971d9c94d5f24ff18daaa3e381a747'
(OUT/'drivers.json').write_text(json.dumps(rows,indent=2)+'\n')
