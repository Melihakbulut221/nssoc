#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Explicit positive buffers on source-measured slow-corner PCIe loads."""
import hashlib,json,os
from pathlib import Path
import odb
from measured_hold_targets import TARGETS,COUNT,DIRECTORY,PROFILE,PARENT_ODB_SHA
from route_cloud_newer_postcts import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/DIRECTORY
SOURCE=OUT/'parent/routed.odb'
def signature(i):
    return dict(master=i.getMaster().getName(),location=list(i.getLocation()),origin=list(i.getOrigin()),orientation=str(i.getOrient()),status=str(i.getPlacementStatus()),pins={t.getMTerm().getName():t.getNet().getName() if t.getNet() else None for t in i.getITerms()})
def fixed_data(db):
    block=db.getChip().getBlock();rows=[]
    for n in block.getNets():
        rule=n.getNonDefaultRule()
        if rule:rows.append(('ndr',n.getName(),rule.getName(),rule.getHardSpacing(),[(l.getName(),rule.getLayerRule(l).getWidth(),rule.getLayerRule(l).getSpacing()) for l in db.getTech().getLayers() if rule.getLayerRule(l)]))
        if str(n.getSigType()) in ('POWER','GROUND'):
            rows.append(('power',n.getName(),[(b.isVia(),b.getTechVia().getName() if b.isVia() and b.getTechVia() else None,b.getBlockVia().getName() if b.isVia() and b.getBlockVia() else None,b.getTechLayer().getName() if not b.isVia() else None,b.xMin(),b.yMin(),b.xMax(),b.yMax()) for w in n.getSWires() for b in w.getWires()]))
    rows += [('port',p.getName(),str(p.getIoType()),str(p.getSigType()),[(b.getTechLayer().getName(),b.xMin(),b.yMin(),b.xMax(),b.yMax()) for pin in p.getBPins() for b in pin.getBoxes()]) for p in block.getBTerms()]
    return hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()
def load(path):
    d=odb.dbDatabase.create();odb.read_db(d,str(path));return d

def prepare():
    assert sha(SOURCE)==PARENT_ODB_SHA
    db=load(SOURCE);b=db.getChip().getBlock();assert len(b.getInsts())==113841 and len(b.getNets())==113913
    original={i.getName():signature(i) for i in b.getInsts()};fixed=fixed_data(db);changes=[]
    for i in b.getInsts():i.setPlacementStatus('FIRM')
    master=db.findMaster('sg13g2_dlygate4sd3_1');assert master
    for index,row in enumerate(TARGETS):
        mapping=row['native_pin'];sink=b.findInst(mapping['instance'])
        assert sink and sink.getMaster().getName()=='RM_IHPSG13_2P_256x16_c2_bm_bist'
        pin=sink.findITerm(mapping['pin']);assert pin and str(pin.getIoType())=='INPUT'
        net=pin.getNet();assert net and str(net.getSigType())=='SIGNAL' and not net.getNonDefaultRule() and not net.getBTerms()
        outputs=[t for t in net.getITerms() if str(t.getIoType())=='OUTPUT'];assert len(outputs)==1
        driver=outputs[0].getInst();assert driver.getMaster().getName().startswith('sg13g2_')
        count=len(net.getITerms());added='nssoc_measured_hold_delay_'+str(index);local='nssoc_measured_hold_branch_'+str(index)
        local_net=odb.dbNet.create(b,local);delay=odb.dbInst.create(b,master,added);assert local_net and delay
        delay.setOrient(driver.getOrient());x,y=driver.getLocation();delay.setLocation(x+driver.getMaster().getWidth(),y);delay.setPlacementStatus('PLACED')
        pin.disconnect();pin.connect(local_net);delay.findITerm('A').connect(net);delay.findITerm('X').connect(local_net)
        for p in delay.getITerms():
            kind=str(p.getSigType())
            if kind in ('POWER','GROUND'):
                peers=[t for t in driver.getITerms() if str(t.getSigType())==kind];assert len(peers)==1 and peers[0].getNet();p.connect(peers[0].getNet())
        changes.append(dict(sink=sink.getName(),sink_pin=pin.getMTerm().getName(),source_endpoint=row['endpoint'],original_net=net.getName(),local_net=local,original_terminal_count=count,buffer=added,buffer_master=master.getName(),initial_buffer_location_dbu=list(delay.getLocation())))
    assert len(changes)==4
    for n in b.getNets():
        if str(n.getSigType()) in ('POWER','GROUND'):continue
        assert not n.getSWires() and n.getRSegCount()==n.getCapNodeCount()==0
        w,g=n.getWire(),n.getGlobalWire()
        if g and (not w or g.getId()!=w.getId()):odb.dbWire.destroy(g)
        if w:odb.dbWire.destroy(w)
        n.clearGuides();n.clearTracks()
    assert fixed_data(db)==fixed
    (OUT/'preparation.json').write_text(json.dumps(dict(original=original,fixed_data_sha256=fixed,changes=changes,accepted=False),indent=2)+'\n')
    odb.write_db(db,str(OUT/'proposed.odb'))

def check_parent(b,old,restore):
    changes={(r['sink'],r['sink_pin']):r for r in old['changes']};assert len(changes)==4
    for name,sig in old['original'].items():
        i=b.findInst(name);assert i
        expected=dict(sig,pins=dict(sig['pins']))
        for (sink,pin),row in changes.items():
            if name==sink:expected['pins'][pin]=row['local_net']
        if restore:assert i.isFixed();expected['status']='FIRM'
        assert signature(i)==expected,('Parent cell geometry or undeclared pin changed',name)
        if restore:i.setPlacementStatus(sig['status'])
    for r in old['changes']:
        i=b.findInst(r['buffer']);assert i and i.getMaster().getName()=='sg13g2_dlygate4sd3_1'
        assert i.findITerm('A').getNet().getName()==r['original_net'] and i.findITerm('X').getNet().getName()==r['local_net']
        assert len(b.findNet(r['local_net']).getITerms())==2 and len(b.findNet(r['original_net']).getITerms())==r['original_terminal_count']

def audit():
    old=json.loads((OUT/'preparation.json').read_text());db=load(OUT/'legalized.odb');b=db.getChip().getBlock()
    assert len(b.getInsts())==113845 and len(b.getNets())==113917
    check_parent(b,old,True);additions=[]
    for r in old['changes']:
        i=b.findInst(r['buffer']);additions.append(dict(name=i.getName(),signature=signature(i),initial_buffer_location_dbu=r['initial_buffer_location_dbu'],displacement_dbu=[abs(a-b) for a,b in zip(i.getLocation(),r['initial_buffer_location_dbu'])]))
    for n in b.getNets():
        if str(n.getSigType()) not in ('POWER','GROUND'):assert not n.getWire() and not n.getGuides() and not n.getGlobalWire()
    assert fixed_data(db)==old['fixed_data_sha256']
    parent=json.loads((OUT/'parent/geometry-proof.json').read_text());assert len(parent['added'])==len(parent['changes'])==50
    for row in parent['added']:assert signature(b.findInst(row['name']))==row['signature']
    odb.write_db(db,str(OUT/'candidate.odb'))
    proof=dict(status='PASS_PARENT_CELLS_PRESERVED_WITH_FOUR_DECLARED_SINK_DELAY_CONNECTIONS',profile=PROFILE,accepted=False,original_instances=113791,stage_original_instances=113841,stage_changes=old['changes'],stage_added=additions,added=parent['added']+additions,changes=parent['changes']+old['changes'],scope='All113841parentcells preserve masters/geometry/PG/NDR and all pins except four explicitly recorded SRAM input branches through positive delay cells. Fifty prior additions are source-bound and unchanged. No routed timing acceptance.')
    (OUT/'geometry-proof.json').write_text(json.dumps(proof,indent=2)+'\n')

def audit_routed():
    old=json.loads((OUT/'preparation.json').read_text());db=load(OUT/'routed.odb');b=db.getChip().getBlock()
    assert len(b.getInsts())==113845 and len(b.getNets())==113917
    check_parent(b,old,False);assert fixed_data(db)==old['fixed_data_sha256']
    proof=json.loads((OUT/'geometry-proof.json').read_text())
    for row in proof['added']:assert signature(b.findInst(row['name']))==row['signature']
    for row in old['changes']:assert b.findNet(row['local_net']).getWire() and b.findNet(row['original_net']).getWire()
    result=dict(status='PASS_PARENT_CELLS_AND_DECLARED_DELAY_BRANCHES_AFTER_ROUTE',accepted=False,parent_instances=113841,stage_added_cells=4,instances=113845,nets=113917,parent_odb_sha256=PARENT_ODB_SHA,scope='All parent and added cell geometry/pins, PG and NDR unchanged through routing; declared four SRAM input branches preserved. Does not establish cross-net geometry, antenna, LVS or timing.')
    (OUT/'post-route-geometry.json').write_text(json.dumps(result,indent=2)+'\n')
mode=os.environ.get('NSSOC_CRITICAL_ECO_MODE')
if mode=='audit':audit()
elif mode=='audit-routed':audit_routed()
else:prepare()
