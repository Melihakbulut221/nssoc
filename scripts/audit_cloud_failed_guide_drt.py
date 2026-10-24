#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native database invariants for full-chip failed-guide DRT diagnosis only."""
import hashlib
import json
import os
from pathlib import Path
import odb

OUT=Path(os.environ['NSSOC_DRT_OUT'])

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def load(path):
    db=odb.dbDatabase.create();odb.read_db(db,str(path));return db

def snapshot(db):
    block=db.getChip().getBlock();tech=db.getTech()
    cells=sorted((i.getName(),i.getMaster().getName(),list(i.getLocation()),str(i.getOrient()),str(i.getPlacementStatus())) for i in block.getInsts())
    nets=[];rules={};guides={};wires=[]
    for n in block.getNets():
        rule=n.getNonDefaultRule()
        rule_key=None
        if rule:
            rule_key=('block:' if rule.isBlockRule() else 'tech:')+rule.getName()
            if rule_key not in rules:
                layers={}
                for layer in tech.getLayers():
                    lr=rule.getLayerRule(layer)
                    if lr:layers[layer.getName()]=[lr.getWidth(),lr.getSpacing()]
                rules[rule_key]=dict(hard_spacing=bool(rule.getHardSpacing()),layers=layers)
        nets.append((n.getName(),str(n.getSigType()),rule_key,
            sorted((p.getInst().getName(),p.getMTerm().getName()) for p in n.getITerms()),
            sorted(p.getName() for p in n.getBTerms())))
        count=len(list(n.getGuides()))
        if count:guides[n.getName()]=count
        if n.getWire():wires.append(n.getName())
    ports=[]
    for p in block.getBTerms():
        shapes=[]
        for pin in p.getBPins():
            for box in pin.getBoxes():
                layer=box.getTechLayer()
                shapes.append((layer.getName() if layer else None,box.xMin(),box.yMin(),box.xMax(),box.yMax()))
        ports.append((p.getName(),str(p.getIoType()),str(p.getSigType()),sorted(shapes)))
    die=block.getDieArea()
    immutable=dict(instances=cells,nets=sorted(nets),ports=sorted(ports),ndr=rules,
        die=[die.xMin(),die.yMin(),die.xMax(),die.yMax()],dbu=block.getDbUnitsPerMicron())
    return dict(immutable_sha256=digest(immutable),instance_count=len(cells),net_count=len(nets),
        ndr=rules,ndr_nets={n[0]:n[2] for n in nets if n[2]},
        guides=guides,guide_rectangles=sum(guides.values()),wired_net_count=len(wires),
        multi_terminal_nets_without_guides=sorted(n[0] for n in nets if n[1] not in ('POWER','GROUND') and len(n[3])+len(n[4])>=2 and n[0] not in guides))

def main():
    mode=os.environ['NSSOC_DRT_MODE'];source=OUT/'inputs'
    base=load(source/'relocated-placement.odb');expected=snapshot(base)
    target=load(OUT/'routed.odb' if mode=='after' else (OUT/'guides-loaded.odb' if mode=='guides' else source/'failed-global.odb'))
    measured=snapshot(target)
    assert expected['immutable_sha256']==measured['immutable_sha256'],'Connectivity, placement, boundary pins or NDR changed'
    assert expected['instance_count']==113791 and expected['ndr_nets']
    controls=[]
    if mode=='before':
        block=target.getChip().getBlock()
        net=next(n for n in block.getNets() if n.getNonDefaultRule())
        rule=net.getNonDefaultRule();net.setNonDefaultRule(None)
        assert snapshot(target)['immutable_sha256']!=expected['immutable_sha256'];controls.append('removed_ndr_rejected')
        net.setNonDefaultRule(rule)
        term=next(p for n in block.getNets() for p in n.getITerms())
        net=term.getNet();term.disconnect()
        assert snapshot(target)['immutable_sha256']!=expected['immutable_sha256'];controls.append('disconnected_terminal_rejected')
        term.connect(net)
        inst=next(iter(block.getInsts()));x,y=inst.getLocation();inst.setLocation(x+1,y)
        assert snapshot(target)['immutable_sha256']!=expected['immutable_sha256'];controls.append('displaced_cell_rejected')
        inst.setLocation(x,y)
        assert snapshot(target)['immutable_sha256']==expected['immutable_sha256']
    if mode=='guides':
        parsed=json.loads((OUT/'guide-index.json').read_text())
        assert parsed==measured['guides'],'Native guide readback differs from complete original guide file'
    result=dict(status='PASS_NATIVE_INVARIANTS_NOT_PHYSICAL_SIGNOFF',mode=mode,accepted=False,
        source=expected,measured=measured,negative_controls=controls,
        scope='Exact original cell/master/location/orientation/status, pin connectivity, boundary pin shapes, die/units and per-net NDR name/width/spacing/hard-spacing flag. Wire existence is NOT connected-route proof, and NDR declarations are NOT routed spacing proof.')
    (OUT/('audit-'+mode+'.json')).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('source','measured')}))

if __name__=='__main__':main()
