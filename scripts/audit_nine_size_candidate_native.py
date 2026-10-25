#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent actual-parent versus actual-routed nine-size database census."""
import hashlib,json,os
from pathlib import Path
import odb
from route_cloud_newer_postcts import sha
from review_nine_size_candidate import TARGETS,PARENT_ODB
OUT=Path(os.environ['NSSOC_NINE_REVIEW_OUT']);SOURCE=OUT/'source'
def load(p):
    d=odb.dbDatabase.create();odb.read_db(d,str(p));return d
def cells(b):
    return {i.getName():dict(master=i.getMaster().getName(),location=list(i.getLocation()),origin=list(i.getOrigin()),orientation=str(i.getOrient()),status=str(i.getPlacementStatus()),pins={t.getMTerm().getName():None if t.getNet()is None else t.getNet().getName()for t in i.getITerms()})for i in b.getInsts()}
def electrical(b):
    return {n.getName():(str(n.getSigType()),sorted((t.getInst().getName(),t.getMTerm().getName())for t in n.getITerms()),sorted(p.getName()for p in n.getBTerms()),None if n.getNonDefaultRule()is None else n.getNonDefaultRule().getName())for n in b.getNets()}
def pg_and_ports(d):
    b=d.getChip().getBlock()
    power=[(n.getName(),[(box.isVia(),box.getTechVia().getName()if box.isVia()and box.getTechVia()else None,box.getBlockVia().getName()if box.isVia()and box.getBlockVia()else None,box.getTechLayer().getName()if not box.isVia()else None,box.xMin(),box.yMin(),box.xMax(),box.yMax())for wire in n.getSWires()for box in wire.getWires()])for n in b.getNets()if str(n.getSigType())in ('POWER','GROUND')]
    ports=[(p.getName(),str(p.getIoType()),str(p.getSigType()),[(x.getTechLayer().getName(),x.xMin(),x.yMin(),x.xMax(),x.yMax())for pin in p.getBPins()for x in pin.getBoxes()])for p in b.getBTerms()]
    rules=[]
    for n in b.getNets():
        r=n.getNonDefaultRule()
        if r:rules.append((n.getName(),r.getName(),r.getHardSpacing(),[(l.getName(),r.getLayerRule(l).getWidth(),r.getLayerRule(l).getSpacing())for l in d.getTech().getLayers()if r.getLayerRule(l)]))
    return dict(power=power,ports=ports,rules=rules)
assert sha(SOURCE/'parent/routed.odb')==PARENT_ODB
old=load(SOURCE/'parent/routed.odb');new=load(SOURCE/'routed.odb')
ob=old.getChip().getBlock();nb=new.getChip().getBlock()
before=cells(ob);nets=electrical(ob);fixed=pg_and_ports(old)
def verify():
    after=cells(nb)
    assert len(before)==len(after)==114025 and set(before)==set(after)
    assert electrical(nb)==nets and len(nets)==114097,'Actual net membership changed'
    assert pg_and_ports(new)==fixed,'Actual PG, NDR or boundary changed'
    changes=[]
    for name,a in before.items():
        z=after[name]
        if name not in TARGETS:
            assert a==z,('Unselected actual cell changed',name)
        else:
            oldmaster,newmaster=TARGETS[name];assert a['master']==oldmaster and z['master']==newmaster
            assert a['pins']==z['pins']and a['status']==z['status'],'Sized cell connectivity or status changed'
            assert z['orientation']in ('R0','R180','MX','MY')
            delta=[z['location'][k]-a['location'][k]for k in (0,1)]
            assert max(map(abs,delta))<=200*new.getTech().getDbUnitsPerMicron()
            changes.append(dict(instance=name,before=a,after=z,displacement_dbu=delta))
    assert len(changes)==9
    return sorted(changes,key=lambda x:x['instance'])
changes=verify()
# Corrupt a real connected input in memory; the files are never changed.
victim=next(t for i in nb.getInsts()for t in i.getITerms()if i.getName()not in TARGETS and str(t.getIoType())=='INPUT'and t.getNet()and str(t.getNet().getSigType())=='SIGNAL')
net=victim.getNet();identity=victim.getInst().getName()+'/'+victim.getMTerm().getName();victim.disconnect()
try:verify()
except AssertionError as error:assert 'Actual net membership changed'in str(error)
else:raise AssertionError('Disconnected physical input escaped independent audit')
victim.connect(net);assert verify()==changes
receipt=json.loads((SOURCE/'geometry-proof.json').read_text())
reported={x['instance']:x for x in receipt['changes']}
for c in changes:
    for side in ('before','after'):
        assert {k:v for k,v in c[side].items()if k!='origin'}==reported[c['instance']][side],'Producer geometry receipt differs from actual database'
assert sha(SOURCE/'parent/routed.odb')==PARENT_ODB
r=dict(status='PASS_INDEPENDENT_ACTUAL_NINE_SIZE_DATABASE_CENSUS_NOT_SIGNOFF',accepted=False,instances=114025,nets=114097,selected=9,unselected_unchanged=114016,changes=changes,net_membership_unchanged=True,pg_ndr_boundary_unchanged=True,negative_control=dict(fault='real_disconnected_input',pin=identity,rejected=True,source_files_modified=False),source_parent_sha256=PARENT_ODB,routed_odb_sha256=sha(SOURCE/'routed.odb'))
(OUT/'native-nine-audit.json').write_text(json.dumps(r,indent=2)+'\n')
print(r['status'],flush=True)
