#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Apply exactly nine measured sizes, legalize only them, preserve every other cell and net."""
import hashlib,json,os
from pathlib import Path
import odb
from route_cloud_newer_postcts import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-route234-sized-eco';PARENT=OUT/'parent/routed.odb'
SOURCE_SHA='4a044ffdb4d92ec3e9150cb4a9696ed7dbfacc05361e64bc6b278259e6c3eeb4'
def signature(i):
    return dict(master=i.getMaster().getName(),location=list(i.getLocation()),orientation=str(i.getOrient()),status=str(i.getPlacementStatus()),pins={t.getMTerm().getName():t.getNet().getName()if t.getNet()else None for t in i.getITerms()})
def fixed(db):
    block=db.getChip().getBlock();rows=[]
    for n in block.getNets():
        rule=n.getNonDefaultRule()
        rows.append(('net',n.getName(),str(n.getSigType()),sorted((t.getInst().getName(),t.getMTerm().getName())for t in n.getITerms()),sorted(t.getName()for t in n.getBTerms())))
        if rule:rows.append(('ndr',n.getName(),rule.getName(),rule.getHardSpacing(),[(l.getName(),rule.getLayerRule(l).getWidth(),rule.getLayerRule(l).getSpacing())for l in db.getTech().getLayers()if rule.getLayerRule(l)]))
        if str(n.getSigType())in ('POWER','GROUND'):
            rows.append(('power',n.getName(),[(b.isVia(),b.getTechVia().getName()if b.isVia()and b.getTechVia()else None,b.getBlockVia().getName()if b.isVia()and b.getBlockVia()else None,b.getTechLayer().getName()if not b.isVia()else None,b.xMin(),b.yMin(),b.xMax(),b.yMax())for w in n.getSWires()for b in w.getWires()]))
    rows += [('port',p.getName(),str(p.getIoType()),str(p.getSigType()),[(b.getTechLayer().getName(),b.xMin(),b.yMin(),b.xMax(),b.yMax())for pin in p.getBPins()for b in pin.getBoxes()])for p in block.getBTerms()]
    return hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()
def load(path):
    db=odb.dbDatabase.create();odb.read_db(db,str(path));return db
assert sha(PARENT)==SOURCE_SHA
source=load(PARENT);base=source.getChip().getBlock()
assert len(base.getInsts())==114025 and len(base.getNets())==114097
original={i.getName():signature(i)for i in base.getInsts()};fixed_hash=fixed(source)
screen=json.loads((OUT/'sizing-screen.json').read_text())
assert screen['status']=='COMPLETE_AVAILABLE_DRIVER_FROZEN_RC_SIZING_SCREEN_NOT_PHYSICAL_ACCEPTANCE'
changes=screen['preparation']['changes'];assert len(changes)==9 and [r['index']for r in changes]==[2,5,7,8,9,10,11,12,13]
targets={r['pin'].rsplit('/',1)[0]:r for r in changes}
mode=os.environ['NSSOC_SIZED_ECO_MODE']
def validate(db,restore_status=False):
    b=db.getChip().getBlock();assert len(b.getInsts())==114025 and len(b.getNets())==114097 and {i.getName()for i in b.getInsts()}==set(original)
    delta=[];limit=200*db.getTech().getDbUnitsPerMicron()
    for i in b.getInsts():
        name=i.getName();observed=signature(i);expected=dict(original[name])
        if name in targets:
            expected['master']=targets[name]['replacement']
            displacement=[observed['location'][k]-expected['location'][k]for k in (0,1)]
            assert max(map(abs,displacement))<=limit,('Selected move outside200um',name)
            expected['location']=observed['location']
            assert observed['orientation'] in ('R0','MX'),('Unsupported cell row orientation',name)
            expected['orientation']=observed['orientation']
            delta.append(dict(instance=name,before=original[name],after=dict(observed,status=original[name]['status']),displacement_dbu=displacement))
        observed['status']=expected['status']
        assert observed==expected,('Unexpected retained cell change',name)
        if restore_status:i.setPlacementStatus(original[name]['status'])
    assert fixed(db)==fixed_hash,'Net membership, PG, NDR or top pins changed'
    return sorted(delta,key=lambda x:x['instance'])
if mode=='prepare':
    db=load(PARENT);b=db.getChip().getBlock()
    for i in b.getInsts():i.setPlacementStatus('FIRM')
    for name,row in targets.items():
        i=b.findInst(name);assert original[name]['master']==row['master']and original[name]['location']==row['location_dbu']
        m=db.findMaster(row['replacement']);assert m
        assert {(t.getName(),str(t.getIoType()),str(t.getSigType()))for t in m.getMTerms()}=={(t.getName(),str(t.getIoType()),str(t.getSigType()))for t in i.getMaster().getMTerms()}
        anchor=i.getLocation();assert i.swapMaster(m);i.setLocation(*anchor);i.setPlacementStatus('PLACED')
    validate(db)
    odb.write_db(db,str(OUT/'proposed.odb'))
elif mode=='audit':
    db=load(OUT/'legalized.odb');delta=validate(db,True);b=db.getChip().getBlock()
    control=next(i for i in b.getInsts()if i.getName()not in targets);anchor=control.getLocation();control.setLocation(anchor[0]+1000,anchor[1])
    try:validate(db)
    except AssertionError as e:assert 'Unexpected retained cell change'in str(e)
    else:raise AssertionError('Unselected movement fault escaped')
    control.setLocation(*anchor);assert validate(db)==delta
    selected=sorted({t.getNet().getName()for name in targets for t in b.findInst(name).getITerms()if t.getNet()and str(t.getNet().getSigType())not in ('POWER','GROUND')})
    assert selected
    odb.write_db(db,str(OUT/'candidate.odb'))
    (OUT/'geometry-proof.json').write_text(json.dumps(dict(status='PASS_EXACT_NINE_SIZES_ONLY_SELECTED_LEGAL_MOVEMENT',parent_odb_sha256=SOURCE_SHA,instances=114025,nets=114097,changes=delta,selected_nets=selected,fixed_net_pg_ndr_pin_sha256=fixed_hash,unselected_movement_control='REJECTED',accepted=False),indent=2)+'\n')
elif mode=='audit-routed':
    db=load(OUT/'routed.odb');validate(db);b=db.getChip().getBlock();reference=load(OUT/'candidate.odb')
    assert {i.getName():signature(i)for i in b.getInsts()}=={i.getName():signature(i)for i in reference.getChip().getBlock().getInsts()}
    (OUT/'post-route-geometry.json').write_text(json.dumps(dict(status='PASS_NINE_SIZED_CELLS_AND_ALL_NET_MEMBERSHIP_PRESERVED_AFTER_ROUTE',routed_odb_sha256=sha(OUT/'routed.odb'),candidate_odb_sha256=sha(OUT/'candidate.odb'),instances=114025,nets=114097,accepted=False),indent=2)+'\n')
else:raise AssertionError('Unsupported mode')
assert sha(PARENT)==SOURCE_SHA
