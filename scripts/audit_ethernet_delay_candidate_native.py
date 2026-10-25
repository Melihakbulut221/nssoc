#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent actual six-hold parent versus single Ethernet delay-master candidate census."""
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

PARENT_SHA='83beec1f190a814928dd0fcdce69a97dd0c2a9240ce55e457312060287f4a5da'
CHILD_SHA=os.environ['NSSOC_ETHERNET_CHILD_SHA']
assert sha(SOURCE/'parent/routed.odb')==PARENT_SHA and sha(SOURCE/'routed.odb')==CHILD_SHA
old=load(SOURCE/'parent/routed.odb');new=load(SOURCE/'routed.odb')
ob=old.getChip().getBlock();nb=new.getChip().getBlock()
before=cells(ob);net_before=electrical(ob);fixed=pg_and_ports(old)
CELL='nssoc_refined_hold_delay_2'
assert before[CELL]['master']=='sg13g2_dlygate4sd1_1'
def verify():
    after=cells(nb)
    assert len(before)==len(after)==114031 and set(after)==set(before)
    assert len(ob.getNets())==len(nb.getNets())==114103
    assert electrical(nb)==net_before,'Actual net membership changed'
    assert pg_and_ports(new)==fixed,'Actual PG, NDR or boundary changed'
    for name,prior in before.items():
        expected=dict(prior,master='sg13g2_dlygate4sd2_1')if name==CELL else prior
        assert after[name]==expected,('Cell master, geometry or connection changed outside declared ECO',name)
    inst=nb.findInst(CELL);net=inst.findITerm('X').getNet()
    assert net.getName()=='nssoc_refined_hold_branch_2'
    assert {(t.getInst().getName(),t.getMTerm().getName())for t in net.getITerms()}=={(CELL,'X'),(r'u_eth.u_mac.rx_fifo.fifo_inst.u_sram.g_bank\[6\].u_mem','A_MEN')}
    assert not list(net.getBTerms())
    return dict(instance=CELL,before=before[CELL],after=after[CELL],all_unselected_preserved=114030)
change=verify()
victim=next(t for i in nb.getInsts()for t in i.getITerms()if i.getName()!=CELL and str(t.getIoType())=='INPUT'and t.getNet()and str(t.getNet().getSigType())=='SIGNAL')
net=victim.getNet();identity=victim.getInst().getName()+'/'+victim.getMTerm().getName();victim.disconnect()
try:verify()
except AssertionError as error:reason=str(error)
else:raise AssertionError('Disconnected native input escaped audit')
victim.connect(net);assert verify()==change
inst=nb.findInst(CELL);wanted=inst.getMaster();anchor=inst.getLocation()
assert inst.swapMaster(new.findMaster('sg13g2_dlygate4sd1_1'));inst.setLocation(*anchor)
try:verify()
except AssertionError as error:master_reason=str(error)
else:raise AssertionError('Reverted delay master escaped audit')
assert inst.swapMaster(wanted);inst.setLocation(*anchor);assert verify()==change
receipt=json.loads((SOURCE/'geometry-proof.json').read_text());assert len(receipt['changes'])==1
reported=receipt['changes'][0];assert reported['instance']==CELL and reported['displacement_dbu']==[0,0]
for which in ['before','after']:
    for k,value in reported[which].items():assert change[which][k]==value
assert sha(SOURCE/'parent/routed.odb')==PARENT_SHA and sha(SOURCE/'routed.odb')==CHILD_SHA
r=dict(status='PASS_INDEPENDENT_SINGLE_ETHERNET_DELAY_NATIVE_CENSUS_NOT_SIGNOFF',accepted=False,instances=114031,nets=114103,added=0,changed_masters=1,all_cell_positions_preserved=True,changes=[change],original_net_membership_preserved=True,pg_ndr_boundary_unchanged=True,
    negative_control=dict(fault='actual_disconnected_input',pin=identity,rejected=True,reason=reason,source_files_modified=False),
    master_control=dict(fault='actual_old_delay_master_restored',rejected=True,reason=master_reason,source_files_modified=False),
    source_parent_sha256=PARENT_SHA,routed_odb_sha256=CHILD_SHA)
(OUT/'native-nine-audit.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],flush=True)
