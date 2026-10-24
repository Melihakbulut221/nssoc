#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Explicit positive buffers on source-measured slow-corner PCIe loads."""
import hashlib,json,os,struct
from pathlib import Path
import odb
from critical_load_targets import TARGETS,COUNT,DIRECTORY,PROFILE
from cloud_contact_release import configured_nets,REVIEW_SHA
RELEASED=configured_nets()
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/DIRECTORY
assert PROFILE=='protected_load_batch' and COUNT==50
SOURCE=OUT/'fixed-source/fixed.odb'
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

def protected_wires(block,excluded):
    rows={}
    for n in block.getNets():
        if n.getName() in excluded or str(n.getSigType()) in ('POWER','GROUND'):continue
        wire=n.getWire()
        if not wire:rows[n.getName()]=None;continue
        d=odb.dbWireDecoder();d.begin(wire);op=d.next()
        assert op in (d.PATH,d.SHORT,d.VWIRE) and str(d.getWireType())=='FIXED',('Unprotected wire',n.getName())
        h=hashlib.sha256()
        for i in range(wire.length()):
            code=wire.getOpcode(i);code=ord(code) if isinstance(code,str) else int(code)
            h.update(struct.pack('<Bq',code,int(wire.getData(i))))
        rows[n.getName()]=dict(length=wire.length(),sha256=h.hexdigest())
    assert sum(v is not None for v in rows.values())==113556-COUNT-len(RELEASED)
    return rows

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
    excluded={r[k] for r in changes for k in ('original_net','local_net')}
    assert not (set(RELEASED)&excluded)
    for name in RELEASED:
        net=b.findNet(name)
        assert net and net.getWire() and str(net.getSigType())=='SIGNAL' and not net.getNonDefaultRule()
    excluded.update(RELEASED)
    protected=protected_wires(b,excluded)
    for n in b.getNets():
        if str(n.getSigType()) in ('POWER','GROUND'):continue
        assert not n.getSWires() and n.getRSegCount()==n.getCapNodeCount()==0
        w,g=n.getWire(),n.getGlobalWire()
        if g and (not w or g.getId()!=w.getId()):odb.dbWire.destroy(g)
        if w and n.getName() in excluded:odb.dbWire.destroy(w)
        n.clearGuides();n.clearTracks()
    assert protected_wires(b,excluded)==protected
    assert fixed_data(db)==fixed
    (OUT/'preparation.json').write_text(json.dumps(dict(original=original,fixed_data_sha256=fixed,changes=changes,protected_wires=protected,released_contact_nets=RELEASED,accepted=False),indent=2)+'\n')
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
    excluded={r[k] for r in old['changes'] for k in ('original_net','local_net')}|set(RELEASED)
    assert old.get('released_contact_nets',[])==RELEASED
    for n in b.getNets():
        if str(n.getSigType()) not in ('POWER','GROUND'):
            if n.getName() in excluded:assert not n.getWire()
            assert not n.getGuides() and not n.getGlobalWire()
    assert protected_wires(b,excluded)==old['protected_wires'],'Unchanged fixed wire altered during placement'
    assert fixed_data(db)==old['fixed_data_sha256']
    odb.write_db(db,str(OUT/'candidate.odb'))
    (OUT/'geometry-proof.json').write_text(json.dumps(dict(status='PASS_EXPLICIT_BUFFERS_ORIGINAL_GEOMETRY_PINS_NDR_POWER_PRESERVED',profile=PROFILE,accepted=False,original_instances=len(old['original']),added=additions,changes=old['changes'],scope='Original113791cells/masters/geometry and all input pins unchanged; selected driver outputs pass through positive buffers. No routed or timing acceptance.'),indent=2)+'\n')

def audit_routed():
    old=json.loads((OUT/'preparation.json').read_text());db=load(OUT/'routed.odb');b=db.getChip().getBlock()
    assert len(b.getInsts())==113791+COUNT and len(b.getNets())==113863+COUNT
    excluded={r[k] for r in old['changes'] for k in ('original_net','local_net')}|set(RELEASED)
    assert old.get('released_contact_nets',[])==RELEASED
    current=protected_wires(b,excluded)
    assert current==old['protected_wires'],'Detailed router changed protected wire encoding'
    assert all(b.findNet(name).getWire() for name in excluded),'Selected route missing'
    assert fixed_data(db)==old['fixed_data_sha256'],'PG/ports/NDR changed after route'
    geometry=json.loads((OUT/'geometry-proof.json').read_text())
    changes={r['driver']:r for r in old['changes']}
    for name,original in old['original'].items():
        expected=dict(original,pins=dict(original['pins']))
        if name in changes:expected['pins'][changes[name]['driver_pin']]=changes[name]['local_net']
        assert signature(b.findInst(name))==expected,('Original cell changed after route',name)
    for row in geometry['added']:assert signature(b.findInst(row['name']))==row['signature']
    result=dict(status='PASS_UNCHANGED_NATIVE_FIXED_WIRES_AFTER_DETAILED_ROUTE',accepted=False,protected_wired_nets=113556-COUNT-len(RELEASED),selected_routed_nets=len(excluded),released_contact_nets=RELEASED,contact_diagnosis_sha256=REVIEW_SHA if RELEASED else None,wire_signatures_sha256=hashlib.sha256(json.dumps(current,sort_keys=True).encode()).hexdigest(),scope='Exact raw encoded native wires including every opcode/data index, all original cell/input connections and all added buffer geometry. Does not prove inter-net/ESD/antenna/qualifiedRC or timing closure.')
    (OUT/'protected-route-proof.json').write_text(json.dumps(result,indent=2)+'\n')

mode=os.environ.get('NSSOC_CRITICAL_ECO_MODE')
if mode=='audit':audit()
elif mode=='audit-routed':audit_routed()
else:prepare()
