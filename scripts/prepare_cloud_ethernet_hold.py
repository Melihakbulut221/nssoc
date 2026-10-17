#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Source-bound identity delay chains at ten GMII output ports, native OpenDB."""
import hashlib
import json
import os
from pathlib import Path
import odb

OUT=Path('cloud-ethernet-hold')
SOURCE=OUT/'source/cloud-newer-postcts/inputs/postcts.odb'
TARGETS={f'eth_txd_o[{i}]' for i in range(8)} | {'eth_tx_en_o','eth_tx_er_o'}


def row(inst):
    return dict(master=inst.getMaster().getName(),location=list(inst.getLocation()),
        orient=str(inst.getOrient()),pins={t.getMTerm().getName():t.getNet().getName() if t.getNet() else None for t in inst.getITerms()})


def power(block):
    result={}
    for net in block.getNets():
        if str(net.getSigType()) not in ('POWER','GROUND'):continue
        shapes=[]
        for wire in net.getSWires():
            for box in wire.getWires():
                via=box.getTechVia() if box.isVia() else None
                blockvia=box.getBlockVia() if box.isVia() else None
                shapes.append([str(box.getTechLayer().getName()) if not box.isVia() else 'VIA',
                    via.getName() if via else None,blockvia.getName() if blockvia else None,
                    box.xMin(),box.yMin(),box.xMax(),box.yMax()])
        result[net.getName()]=hashlib.sha256(json.dumps(sorted(shapes)).encode()).hexdigest()
    return result


def prepare():
    depth=int(os.environ['NSSOC_HOLD_DEPTH']);assert depth in (1,2)
    db=odb.dbDatabase.create();odb.read_db(db,str(SOURCE));block=db.getChip().getBlock()
    ports={p.getName().replace('\\',''):p for p in block.getBTerms()}
    assert TARGETS<=ports.keys()
    before=dict(instances={i.getName():row(i) for i in block.getInsts()},
        statuses={i.getName():str(i.getPlacementStatus()) for i in block.getInsts()},
        boundary={p.getName():p.getNet().getName() if p.getNet() else None for p in block.getBTerms()},
        net_names=sorted(n.getName() for n in block.getNets()),power=power(block),added={},outputs={},net_renames={},depth=depth)
    master=db.findMaster('sg13g2_dlygate4sd3_1');assert master
    assert {t.getName() for t in master.getMTerms() if str(t.getSigType()) not in ('POWER','GROUND')}=={'A','X'}
    for inst in block.getInsts():
        if str(inst.getPlacementStatus())=='PLACED':inst.setPlacementStatus('FIRM')
    for number,name in enumerate(sorted(TARGETS)):
        port=ports[name];assert str(port.getIoType())=='OUTPUT'
        original=port.getNet();drivers=[t for t in original.getITerms() if str(t.getIoType())=='OUTPUT']
        assert len(drivers)==1 and not drivers[0].getInst().getMaster().isBlock()
        # After moving the BTerm, its former net must not retain the port name.
        # Otherwise write_verilog aliases the internal input back to the output
        # through its generated port assignment, shorting the new delay cell.
        old_name=original.getName()
        assert old_name.replace('\\','')==name and len(list(original.getBTerms()))==1
        internal_name=f'nssoc_eth_hold_{number}_input'
        assert not block.findNet(internal_name) and original.rename(internal_name)
        before['net_renames'][old_name]=internal_name
        driver=drivers[0].getInst();x,y=driver.getLocation();previous=original
        for stage in range(depth):
            inst_name=f'nssoc_eth_hold_{number}_{stage}'
            net_name=inst_name+'_out';assert not block.findInst(inst_name) and not block.findNet(net_name)
            net=odb.dbNet.create(block,net_name);inst=odb.dbInst.create(block,master,inst_name)
            inst.setOrient(driver.getOrient());inst.setLocation(x+(stage+1)*master.getWidth(),y);inst.setPlacementStatus('PLACED')
            inst.findITerm('A').connect(previous);inst.findITerm('X').connect(net)
            for term in inst.getITerms():
                kind=str(term.getSigType())
                if kind in ('POWER','GROUND'):
                    peers=[t for t in driver.getITerms() if str(t.getSigType())==kind]
                    assert len(peers)==1 and peers[0].getNet();term.connect(peers[0].getNet())
            before['added'][inst_name]=row(inst);previous=net
        port.disconnect();port.connect(previous)
        before['outputs'][port.getName()]=dict(original=old_name,internal=original.getName(),delayed=previous.getName(),driver=driver.getName())
    # Source has no signal routing/parasitics to accidentally reuse after ECO.
    for net in block.getNets():
        if str(net.getSigType()) not in ('POWER','GROUND'):
            assert not net.getWire() and not net.getGlobalWire() and net.getRSegCount()==net.getCapNodeCount()==0
    assert power(block)==before['power']
    (OUT/'preparation.json').write_text(json.dumps(before,separators=(',',':'))+'\n')
    odb.write_db(db,str(OUT/'proposed.odb'))


def audit():
    before=json.loads((OUT/'preparation.json').read_text())
    db=odb.dbDatabase.create();odb.read_db(db,str(OUT/'placed.odb'));block=db.getChip().getBlock()
    actual={i.getName():i for i in block.getInsts()}
    assert set(actual)==set(before['instances'])|set(before['added'])
    reverse={new:old for old,new in before['net_renames'].items()}
    assert len(reverse)==len(TARGETS)==len(before['net_renames'])
    for name,expected in before['instances'].items():
        value=row(actual[name])
        value['pins']={pin:reverse.get(net,net) for pin,net in value['pins'].items()}
        assert value==expected,('Original cell changed',name)
        actual[name].setPlacementStatus(before['statuses'][name])
    for name,expected in before['added'].items():
        value=row(actual[name]);assert value['master']==expected['master'] and value['pins']==expected['pins']
        assert str(actual[name].getPlacementStatus())=='PLACED'
    for port in block.getBTerms():
        expected=before['outputs'].get(port.getName(),{}).get('delayed',before['boundary'][port.getName()])
        assert (port.getNet().getName() if port.getNet() else None)==expected
    assert set(n.getName() for n in block.getNets())=={before['net_renames'].get(n,n) for n in before['net_names']}|{n+'_out' for n in before['added']}
    assert power(block)==before['power']
    odb.write_db(db,str(OUT/'candidate.odb'))
    (OUT/'geometry-audit.json').write_text(json.dumps(dict(status='PASS_ONLY_GMII_OUTPUT_IDENTITY_DELAY_CHAINS',
        retained_instances=len(before['instances']),added_instances=len(before['added']),outputs=before['outputs'],
        internal_net_renames=before['net_renames'],
        added={n:row(actual[n]) for n in before['added']},power_geometry_unchanged=True,
        original_cells_geometry_and_connectivity_unchanged=True),indent=2)+'\n')


if __name__=='__main__':
    prepare() if os.environ['NSSOC_HOLD_MODE']=='prepare' else audit()
