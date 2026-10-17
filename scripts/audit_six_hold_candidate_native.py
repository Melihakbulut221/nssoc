#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent actual-parent versus actual-routed nine-size database census."""
import hashlib,json,os
from pathlib import Path
import odb
from route_cloud_newer_postcts import sha
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

PARENT_SHA='72c2e2cd51be4f075b551b48ccd23a57bebf41d978a94b64f6a1164848662e87'
CHILD_SHA='83beec1f190a814928dd0fcdce69a97dd0c2a9240ce55e457312060287f4a5da'
assert sha(SOURCE/'parent/routed.odb')==PARENT_SHA and sha(SOURCE/'routed.odb')==CHILD_SHA
old=load(SOURCE/'parent/routed.odb');new=load(SOURCE/'routed.odb')
ob=old.getChip().getBlock();nb=new.getChip().getBlock()
before=cells(ob);net_before=electrical(ob);fixed=pg_and_ports(old)
ADDED={'nssoc_nine_hold_delay_'+str(i)for i in range(6)}
BRANCHES={'nssoc_nine_hold_branch_'+str(i)for i in range(6)}
def verify():
    after=cells(nb);assert len(before)==114025 and len(after)==114031 and set(after)-set(before)==ADDED and set(before)<=set(after)
    assert len(ob.getNets())==114097 and len(nb.getNets())==114103
    assert {n.getName()for n in nb.getNets()}==set(net_before)|BRANCHES
    assert pg_and_ports(new)==fixed,'Actual PG, NDR or boundary changed'
    changes=[];aliases={}
    for index in range(6):
        name='nssoc_nine_hold_delay_'+str(index);inst=nb.findInst(name);assert inst.getMaster().getName()=='sg13g2_dlygate4sd3_1'
        a=inst.findITerm('A').getNet();x=inst.findITerm('X').getNet()
        assert a and x and a.getName()in net_before and x.getName()=='nssoc_nine_hold_branch_'+str(index)
        assert str(a.getSigType())==str(x.getSigType())=='SIGNAL' and not x.getNonDefaultRule()and not list(x.getBTerms())
        terms=list(x.getITerms());assert len(terms)==2
        sink=next(t for t in terms if t.getInst().getName()!=name);assert str(sink.getIoType())=='INPUT' and sink.getInst().getName()in before
        old_sink=ob.findInst(sink.getInst().getName()).findITerm(sink.getMTerm().getName());assert old_sink.getNet().getName()==a.getName()
        for term in inst.getITerms():
            kind=str(term.getSigType())
            if kind in ('POWER','GROUND'):
                assert term.getNet()and term.getNet().getName()in net_before
                peers=[t for t in old_sink.getInst().getITerms()if str(t.getSigType())==kind]
                assert len(peers)==1 and peers[0].getNet().getName()==term.getNet().getName(),'Added delay power domain differs'
        aliases[x.getName()]=a.getName()
        changes.append(dict(buffer=name,buffer_master=inst.getMaster().getName(),sink=sink.getInst().getName(),sink_pin=sink.getMTerm().getName(),original_net=a.getName(),local_net=x.getName(),signature=after[name]))
    for name,sig in before.items():
        actual=dict(after[name],pins={p:aliases.get(n,n)for p,n in after[name]['pins'].items()})
        assert actual==sig,('Parent cell geometry or undeclared connection changed',name)
    # Independently remove only six added buffers and collapse only six named
    # split branches; every original net membership must then match exactly.
    collapsed={name:[kind,[],list(ports),ndr]for name,(kind,terms,ports,ndr)in net_before.items()}
    for n in nb.getNets():
        target=aliases.get(n.getName(),n.getName());expected=collapsed[target]
        assert str(n.getSigType())==expected[0]
        if n.getName()not in aliases:
            assert sorted(p.getName()for p in n.getBTerms())==expected[2]
            assert (None if n.getNonDefaultRule()is None else n.getNonDefaultRule().getName())==expected[3]
        expected[1]+=[(t.getInst().getName(),t.getMTerm().getName())for t in n.getITerms()if t.getInst().getName()not in ADDED]
    assert {n:(v[0],sorted(v[1]),v[2],v[3])for n,v in collapsed.items()}==net_before,'Actual original net membership changed'
    return changes
changes=verify()
victim=next(t for i in nb.getInsts()for t in i.getITerms()if i.getName()not in ADDED and str(t.getIoType())=='INPUT'and t.getNet()and str(t.getNet().getSigType())=='SIGNAL')
net=victim.getNet();identity=victim.getInst().getName()+'/'+victim.getMTerm().getName();victim.disconnect()
try:verify()
except AssertionError as error:reason=str(error)
else:raise AssertionError('Disconnected native input escaped audit')
victim.connect(net);assert verify()==changes
receipt=json.loads((SOURCE/'geometry-proof.json').read_text());reported={r['buffer']:r for r in receipt['changes']}
assert set(reported)==ADDED
for row in changes:
    for k in ['buffer','buffer_master','sink','sink_pin','original_net','local_net']:assert reported[row['buffer']][k]==row[k]
assert sha(SOURCE/'parent/routed.odb')==PARENT_SHA and sha(SOURCE/'routed.odb')==CHILD_SHA
r=dict(status='PASS_INDEPENDENT_SIX_DELAY_NATIVE_CENSUS_NOT_SIGNOFF',accepted=False,instances=114031,nets=114103,added=6,original_cells_preserved=114025,changes=changes,
    original_net_membership_preserved_after_exact_six_branch_collapse=True,pg_ndr_boundary_unchanged=True,
    negative_control=dict(fault='actual_disconnected_input',pin=identity,rejected=True,reason=reason,source_files_modified=False),
    source_parent_sha256=PARENT_SHA,routed_odb_sha256=CHILD_SHA)
(OUT/'native-nine-audit.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],flush=True)
