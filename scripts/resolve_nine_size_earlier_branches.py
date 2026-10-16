#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Resolve actual short-path input branches in immutable routed nine-size ODB; read only."""
import json,os
from pathlib import Path
import odb
from route_cloud_newer_postcts import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-nine-size-earlier-branches'
p=ROOT/'cloud-route234-sized-eco/routed.odb';assert sha(p)=='72c2e2cd51be4f075b551b48ccd23a57bebf41d978a94b64f6a1164848662e87'
db=odb.dbDatabase.create();odb.read_db(db,str(p));block=db.getChip().getBlock()
assert len(block.getInsts())==114025 and len(block.getNets())==114097
requests=json.loads((OUT/'branch-requests.json').read_text());rows=[]
for r in requests:
    driver,pin=r['driver_pin'].rsplit('/',1);sink=r['next_pin'].rsplit('/',1)[0]
    d=block.findInst(driver);s=block.findInst(sink);assert d and s
    dp=d.findITerm(pin);assert dp and str(dp.getIoType())=='OUTPUT';net=dp.getNet();assert net
    assert str(net.getSigType())=='SIGNAL' and not net.getBTerms() and not net.getNonDefaultRule()
    outputs=[t for t in net.getITerms()if str(t.getIoType())=='OUTPUT'];assert len(outputs)==1 and outputs[0].getInst().getName()==driver and outputs[0].getMTerm().getName()==pin
    pins=[t for t in s.getITerms()if str(t.getIoType())=='INPUT'and t.getNet()and t.getNet().getName()==net.getName()]
    row=dict(r,driver_master=d.getMaster().getName(),sink_master=s.getMaster().getName(),net=net.getName(),net_iterm_count=len(net.getITerms()),matching_input_pins=[t.getMTerm().getName()for t in pins])
    assert pins,('Native timing edge has no physical input connection',r)
    if len(pins)==1:row['branch_pin']=sink+'/'+pins[0].getMTerm().getName()
    else:row['unresolved_reason']='Multiple inputs on same net; no guessed branch'
    rows.append(row)
assert sha(p)=='72c2e2cd51be4f075b551b48ccd23a57bebf41d978a94b64f6a1164848662e87'
(OUT/'branches.json').write_text(json.dumps(rows,indent=2)+'\n')
