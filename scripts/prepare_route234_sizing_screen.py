#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Frozen-wire sizing hypothesis only; the resulting ODB is NOT a routed candidate."""
import hashlib,json,struct
from pathlib import Path
import odb
from route_cloud_newer_postcts import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-route234-sizing-screen'
SOURCE=ROOT/'cloud-branch-hold-eco/routed.odb'
SOURCE_SHA='4a044ffdb4d92ec3e9150cb4a9696ed7dbfacc05361e64bc6b278259e6c3eeb4'
def signature(i):
    return dict(master=i.getMaster().getName(),location=list(i.getLocation()),orientation=str(i.getOrient()),status=str(i.getPlacementStatus()),pins={t.getMTerm().getName():t.getNet().getName()if t.getNet()else None for t in i.getITerms()})
def connectivity(block):
    rows=[]
    for n in block.getNets():
        rows.append((n.getName(),str(n.getSigType()),n.getNonDefaultRule().getName()if n.getNonDefaultRule()else None,sorted((t.getInst().getName(),t.getMTerm().getName())for t in n.getITerms()),sorted(t.getName()for t in n.getBTerms())))
    return hashlib.sha256(json.dumps(sorted(rows)).encode()).hexdigest()
assert sha(SOURCE)==SOURCE_SHA
db=odb.dbDatabase.create();odb.read_db(db,str(SOURCE));block=db.getChip().getBlock()
assert len(block.getInsts())==114025 and len(block.getNets())==114097
requests=json.loads((OUT/'driver-requests.json').read_text())
assert len(requests)==15 and [r['index']for r in requests]==list(range(15))
original={i.getName():signature(i)for i in block.getInsts()};net_hash=connectivity(block)
resolved=[];changes=[];unavailable=[]
master_names=sorted(m.getName()for lib in db.getLibs()for m in lib.getMasters())
(OUT/'actual-master-inventory.json').write_text(json.dumps(master_names,indent=2)+'\n')
for r in requests:
    name,pin=r['pin'].rsplit('/',1);inst=block.findInst(name)
    assert inst and inst.getMaster().getName()==r['master']
    terminal=inst.findITerm(pin);assert terminal and str(terminal.getIoType())=='OUTPUT'
    net=terminal.getNet();assert net and str(net.getSigType())=='SIGNAL'
    assert sum(str(t.getIoType())=='OUTPUT'for t in net.getITerms())==1
    row=dict(r,net=net.getName(),location_dbu=list(inst.getLocation()),terminal_count=len(net.getITerms()),selected=r['index']!=14)
    if row['selected']:
        prefix,drive=r['master'].rsplit('_',1);assert drive in ('1','2')
        replacement=prefix+'_'+str(2*int(drive));master=db.findMaster(replacement)
        if not master:
            row.update(selected=False,requested_replacement=replacement,reason='Requested doubled master is absent from the exact source ODB library',available_same_family=[n for n in master_names if n.rsplit('_',1)[0]==prefix])
            unavailable.append(row);resolved.append(row);continue
        oldmaster=inst.getMaster()
        assert {(t.getName(),str(t.getIoType()),str(t.getSigType()))for t in master.getMTerms()}=={(t.getName(),str(t.getIoType()),str(t.getSigType()))for t in oldmaster.getMTerms()}
        row.update(replacement=replacement,before_width_dbu=oldmaster.getWidth(),after_width_dbu=master.getWidth())
        anchor=inst.getLocation();assert inst.swapMaster(master);inst.setLocation(*anchor)
        expected=dict(original[name],master=replacement)
        assert signature(inst)==expected,('Unexpected sizing change',name)
        changes.append(row)
    resolved.append(row)
assert 0<len(changes)<=14 and len(changes)+len(unavailable)==14 and connectivity(block)==net_hash
selected={r['pin'].rsplit('/',1)[0]:r['replacement']for r in changes}
for i in block.getInsts():
    expected=dict(original[i.getName()])
    if i.getName()in selected:expected['master']=selected[i.getName()]
    assert signature(i)==expected,('Unexpected cell change',i.getName())
assert sha(SOURCE)==SOURCE_SHA
odb.write_db(db,str(OUT/'unlegalized-frozen-wire.odb'))
(OUT/'native-sizing.json').write_text(json.dumps(dict(status='COMPLETE_FROZEN_WIRE_MASTER_SUBSTITUTION_NOT_PHYSICAL_ECO',accepted=False,source_odb_sha256=SOURCE_SHA,source_unchanged=True,instances=114025,nets=114097,connectivity_sha256=net_hash,all_unselected_cells_unchanged=True,placement_legal=False,route_validated=False,requested_count=14,implemented_count=len(changes),unavailable=unavailable,changes=changes,rows=resolved,scope='Only available requested actual master substitutions at unchanged anchors; PDK master pin types and all net membership preserved. Pin geometry/width changes invalidate route geometry. No legalization, fresh RC, DRC, LVS or physical acceptance.'),indent=2)+'\n')
