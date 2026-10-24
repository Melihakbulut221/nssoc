#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual single-sink Ethernet A_MEN delay master alternatives, not a routed ECO."""
import json,hashlib,os
from pathlib import Path
import odb
from route_cloud_newer_postcts import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-ethernet-hold-screen';SOURCE=OUT/'source/routed.odb'
SOURCE_SHA='83beec1f190a814928dd0fcdce69a97dd0c2a9240ce55e457312060287f4a5da'
CELL='nssoc_refined_hold_delay_2'
def signature(i):
    return dict(master=i.getMaster().getName(),location=list(i.getLocation()),orientation=str(i.getOrient()),status=str(i.getPlacementStatus()),pins={t.getMTerm().getName():t.getNet().getName()if t.getNet()else None for t in i.getITerms()})
def connectivity(block):
    return hashlib.sha256(json.dumps(sorted((n.getName(),str(n.getSigType()),n.getNonDefaultRule().getName()if n.getNonDefaultRule()else None,sorted((t.getInst().getName(),t.getMTerm().getName())for t in n.getITerms()),sorted(t.getName()for t in n.getBTerms()))for n in block.getNets())).encode()).hexdigest()
assert os.environ.get('GITHUB_ACTIONS')=='true'and sha(SOURCE)==SOURCE_SHA
db=odb.dbDatabase.create();odb.read_db(db,str(SOURCE));block=db.getChip().getBlock()
assert len(block.getInsts())==114031 and len(block.getNets())==114103
original={i.getName():signature(i)for i in block.getInsts()};net_hash=connectivity(block)
inst=block.findInst(CELL);assert inst and inst.getMaster().getName()=='sg13g2_dlygate4sd1_1'
oldmaster=inst.getMaster();net=inst.findITerm('X').getNet()
assert net.getName()=='nssoc_refined_hold_branch_2'
terms={(t.getInst().getName(),t.getMTerm().getName(),str(t.getIoType()))for t in net.getITerms()}
assert terms=={(CELL,'X','OUTPUT'),(r'u_eth.u_mac.rx_fifo.fifo_inst.u_sram.g_bank\[6\].u_mem','A_MEN','INPUT')} and not list(net.getBTerms()),'Measured output is no longer a unique SRAM input branch'
masters=sorted(m.getName()for lib in db.getLibs()for m in lib.getMasters())
(OUT/'actual-master-inventory.json').write_text(json.dumps(masters,indent=2)+'\n')
results=[]
for replacement in ['sg13g2_dlygate4sd2_1','sg13g2_dlygate4sd3_1']:
    master=db.findMaster(replacement)
    if not master:
        results.append(dict(replacement=replacement,available=False));continue
    assert {(t.getName(),str(t.getIoType()),str(t.getSigType()))for t in master.getMTerms()}=={(t.getName(),str(t.getIoType()),str(t.getSigType()))for t in oldmaster.getMTerms()}
    anchor=inst.getLocation();assert inst.swapMaster(master);inst.setLocation(*anchor)
    expected=dict(original[CELL],master=replacement);assert signature(inst)==expected
    assert connectivity(block)==net_hash
    for cell in block.getInsts():assert signature(cell)==(expected if cell.getName()==CELL else original[cell.getName()]),'Unselected cell changed'
    target=OUT/(replacement+'.odb');odb.write_db(db,str(target))
    results.append(dict(replacement=replacement,available=True,instance=CELL,before=original[CELL],after=expected,before_width_dbu=oldmaster.getWidth(),after_width_dbu=master.getWidth(),odb=target.name,odb_sha256=sha(target),all_unselected_unchanged=114030))
    assert inst.swapMaster(oldmaster);inst.setLocation(*anchor);assert signature(inst)==original[CELL]
assert any(r['available']for r in results)
assert sha(SOURCE)==SOURCE_SHA and connectivity(block)==net_hash
(OUT/'native-sizing.json').write_text(json.dumps(dict(status='COMPLETE_EXACT_SINGLE_SINK_DELAY_MASTER_SUBSTITUTIONS_NOT_PHYSICAL_ECO',source_unchanged=True,source_odb_sha256=SOURCE_SHA,instances=114031,nets=114103,connectivity_sha256=net_hash,variants=results,physical_candidate=False,route_validated=False),indent=2)+'\n')
