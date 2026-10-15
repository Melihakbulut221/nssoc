#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Explicit positive buffers on source-measured slow-corner PCIe loads."""
import hashlib,json,os
from pathlib import Path
import odb
from critical_load_targets import TARGETS,COUNT,DIRECTORY,PROFILE
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/DIRECTORY
SOURCE=ROOT/'cloud-routed-extraction/source/routed.odb'
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
    db=load(SOURCE);b=db.getChip().getBlock();assert len(b.getInsts())==113791
    original={i.getName():signature(i) for i in b.getInsts()};fixed=fixed_data(db);changes=[]
    for i in b.getInsts():i.setPlacementStatus('FIRM')
    master=db.findMaster('sg13g2_buf_16');assert master
    for index,(name,expected,driver_pin,terminal_count) in enumerate(TARGETS):
        driver=b.findInst(name);assert driver and driver.getMaster().getName()==expected
        term=driver.findITerm(driver_pin);assert term and str(term.getIoType())=='OUTPUT';net=term.getNet();assert net and not net.getNonDefaultRule() and str(net.getSigType())=='SIGNAL'
        assert len(net.getITerms())==terminal_count and len(net.getBTerms())==0,'Measured fanout changed'
        assert sum(str(t.getIoType())=='OUTPUT' for t in net.getITerms())==1
        assert all(str(t.getIoType()) in ('INPUT','OUTPUT') for t in net.getITerms())
        outputs=[t for t in net.getITerms() if str(t.getIoType())=='OUTPUT']
        assert [(t.getInst().getName(),t.getMTerm().getName()) for t in outputs]==[(name,driver_pin)]
        added='nssoc_critical_load_buffer_'+str(index);local='nssoc_critical_load_local_'+str(index)
        local_net=odb.dbNet.create(b,local);buffer=odb.dbInst.create(b,master,added);assert buffer and local_net
        buffer.setOrient(driver.getOrient());x,y=driver.getLocation();buffer.setLocation(x+driver.getMaster().getWidth(),y);buffer.setPlacementStatus('PLACED')
        term.disconnect();term.connect(local_net);buffer.findITerm('A').connect(local_net);buffer.findITerm('X').connect(net)
        for p in buffer.getITerms():
            kind=str(p.getSigType())
            if kind in ('POWER','GROUND'):
                peers=[t for t in driver.getITerms() if str(t.getSigType())==kind];assert len(peers)==1 and peers[0].getNet();p.connect(peers[0].getNet())
        changes.append(dict(driver=name,driver_pin=driver_pin,original_terminal_count=terminal_count,initial_buffer_location_dbu=list(buffer.getLocation()),original_net=net.getName(),local_net=local,buffer=added,buffer_master=master.getName()))
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

def audit():
    old=json.loads((OUT/'preparation.json').read_text());db=load(OUT/'legalized.odb');b=db.getChip().getBlock()
    assert len(b.getInsts())==len(old['original'])+COUNT and len(b.getNets())==113863+COUNT
    assert len(old['changes'])==COUNT
    changes={r['driver']:r for r in old['changes']}
    for name,sig in old['original'].items():
        i=b.findInst(name);assert i and i.isFixed()
        current=signature(i);expected=dict(sig,pins=dict(sig['pins']),status='FIRM')
        if name in changes:expected['pins'][changes[name]['driver_pin']]=changes[name]['local_net']
        assert current==expected,('Original cell geometry/function/connection changed',name)
        i.setPlacementStatus(sig['status'])
    additions=[]
    for r in old['changes']:
        i=b.findInst(r['buffer']);assert i.getMaster().getName()=='sg13g2_buf_16'
        assert i.findITerm('A').getNet().getName()==r['local_net'] and i.findITerm('X').getNet().getName()==r['original_net']
        assert len(b.findNet(r['local_net']).getITerms())==2 and len(b.findNet(r['original_net']).getITerms())==r['original_terminal_count']
        additions.append(dict(name=i.getName(),signature=signature(i),initial_buffer_location_dbu=r['initial_buffer_location_dbu'],displacement_dbu=[abs(a-b) for a,b in zip(i.getLocation(),r['initial_buffer_location_dbu'])]))
    for n in b.getNets():
        if str(n.getSigType()) not in ('POWER','GROUND'):assert not n.getWire() and not n.getGuides() and not n.getGlobalWire()
    assert fixed_data(db)==old['fixed_data_sha256']
    odb.write_db(db,str(OUT/'candidate.odb'))
    (OUT/'geometry-proof.json').write_text(json.dumps(dict(status='PASS_EXPLICIT_BUFFERS_ORIGINAL_GEOMETRY_PINS_NDR_POWER_PRESERVED',profile=PROFILE,accepted=False,original_instances=len(old['original']),added=additions,changes=old['changes'],scope='Original113791cells/masters/geometry and all input pins unchanged; selected driver outputs pass through positive buffers. No routed or timing acceptance.'),indent=2)+'\n')

if os.environ.get('NSSOC_CRITICAL_ECO_MODE')=='audit':audit()
else:prepare()
