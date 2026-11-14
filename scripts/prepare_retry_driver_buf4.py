# SPDX-License-Identifier: Apache-2.0
"""Swap on an independent OpenDB, without STA callbacks or timing claims."""
import odb,json,pathlib
# Deliberately independent database, not OpenROAD's STA-attached database.
db=odb.dbDatabase.create();odb.read_db(db,'out/native/source.odb');block=db.getChip().getBlock()
assert len(block.getInsts())==159934
inst=block.findInst('place31551');assert inst and inst.getMaster().getName()=='sg13g2_buf_1'
assert not inst.isFixed() and not inst.isDoNotTouch()
term=inst.findITerm('X');assert term
net=term.getNet();assert net and net.getName()=='net31551' and str(net.getSigType())=='SIGNAL' and not net.isDoNotTouch()
assert len(net.getBTerms())==0 and sum(str(t.getIoType())=='OUTPUT' for t in net.getITerms())==1
master=db.findMaster('sg13g2_buf_4');assert master
schema=lambda m:sorted((t.getName(),str(t.getIoType()),str(t.getSigType())) for t in m.getMTerms())
assert schema(inst.getMaster())==schema(master)
def signature(i):return {'master':i.getMaster().getName(),'location':list(i.getLocation()),'orientation':str(i.getOrient()),'status':str(i.getPlacementStatus()),'pins':sorted((t.getMTerm().getName(),t.getNet().getName() if t.getNet() else None) for t in i.getITerms())}
before={i.getName():signature(i) for i in block.getInsts()}
anchor=inst.getLocation();assert inst.swapMaster(master);inst.setLocation(*anchor)
for i in block.getInsts():
 expected=dict(before[i.getName()])
 if i.getName()=='place31551':expected['master']='sg13g2_buf_4'
 assert signature(i)==expected,('Unexpected swap effect',i.getName())
odb.write_db(db,'out/native/buf4-unplaced.odb')
pathlib.Path('out/derived/swap-proof.json').write_text(json.dumps({'swap_invariants_passed':True,'instance_count':len(before),'target':'place31551','old_master':'sg13g2_buf_1','new_master':'sg13g2_buf_4','placement_validated':False,'timing_validated':False},indent=2))
