#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Resolve actual short-path input branches in immutable routed146ODB; read only."""
import json,os
from pathlib import Path
import odb
from route_cloud_newer_postcts import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-route146-branch-margins'
p=ROOT/'cloud-refined-hold-eco/routed.odb';assert sha(p)=='1e97e6c345d9529a7a40b9435a15b58382971d9c94d5f24ff18daaa3e381a747'
db=odb.dbDatabase.create();odb.read_db(db,str(p));block=db.getChip().getBlock()
assert len(block.getInsts())==113937 and len(block.getNets())==114009
requests=json.loads((OUT/'branch-requests.json').read_text());rows=[]
for r in requests:
    driver,pin=r['driver_pin'].rsplit('/',1);sink=r['next_pin'].rsplit('/',1)[0]
    d=block.findInst(driver);s=block.findInst(sink);assert d and s
    dp=d.findITerm(pin);assert dp and str(dp.getIoType())=='OUTPUT';net=dp.getNet();assert net
    assert str(net.getSigType())=='SIGNAL' and not net.getBTerms() and not net.getNonDefaultRule()
    outputs=[t for t in net.getITerms()if str(t.getIoType())=='OUTPUT'];assert len(outputs)==1 and outputs[0].getId()==dp.getId()
    pins=[t for t in s.getITerms()if str(t.getIoType())=='INPUT'and t.getNet()and t.getNet().getId()==net.getId()]
    row=dict(r,driver_master=d.getMaster().getName(),sink_master=s.getMaster().getName(),net=net.getName(),net_iterm_count=len(net.getITerms()),matching_input_pins=[t.getMTerm().getName()for t in pins])
    assert pins,('Native timing edge has no physical input connection',r)
    if len(pins)==1:row['branch_pin']=sink+'/'+pins[0].getMTerm().getName()
    else:row['unresolved_reason']='Multiple inputs on same net; no guessed branch'
    rows.append(row)
assert sha(p)=='1e97e6c345d9529a7a40b9435a15b58382971d9c94d5f24ff18daaa3e381a747'
(OUT/'branches.json').write_text(json.dumps(rows,indent=2)+'\n')
