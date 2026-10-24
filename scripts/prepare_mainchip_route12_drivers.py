#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Resize only measured non-clock positive buffers; preserve all pin equations."""
import hashlib,json,os
from pathlib import Path
import odb
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-mainchip-route12-resize'
SOURCE=OUT/'source/geometry/routed/work/detailed-route.odb'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()=='8becfa04b073ed577014f8fb157ae89dd7f824efe16fb7b092348175192fee1a'
def signature(i):
    return dict(master=i.getMaster().getName(),location=list(i.getLocation()),origin=list(i.getOrigin()),orientation=str(i.getOrient()),status=str(i.getPlacementStatus()),dont_touch=i.isDoNotTouch(),pins={t.getMTerm().getName():t.getNet().getName() if t.getNet() else None for t in i.getITerms()})
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


def topology(block):
    return {n.getName():dict(kind=str(n.getSigType()),pins=sorted([t.getInst().getName(),t.getMTerm().getName()]for t in n.getITerms()),ports=sorted(p.getName()for p in n.getBTerms()))for n in block.getNets()}
def prepare():
    db=load(SOURCE);block=db.getChip().getBlock();targets=json.loads((OUT/'targets.json').read_text())['targets']
    original={i.getName():signature(i)for i in block.getInsts()};fixed=fixed_data(db);nets=topology(block);changes=[]
    assert len(original)==153130 and 1<=len(targets)<=128
    clock_nets={n.getName()for n in block.getNets()if str(n.getSigType())=='CLOCK' or any(str(p.getMTerm().getSigType())=='CLOCK'for p in n.getITerms())}
    from prepare_onehot_clock_restore import NET
    assert block.findNet(NET);clock_nets.add(NET)
    for i in block.getInsts():i.setPlacementStatus('FIRM')
    for t in targets:
        i=block.findInst(t['instance']);assert i and i.getMaster().getName()==t['master']
        assert t['master']in ('sg13g2_buf_1','sg13g2_buf_2')and not i.getName().startswith('clkbuf')
        assert not i.isDoNotTouch()
        assert all(not p.getNet()or p.getNet().getName()not in clock_nets for p in i.getITerms())
        pin=i.findITerm(t['pin']);assert pin and t['pin']=='X'and str(pin.getIoType())=='OUTPUT'
        net=pin.getNet();assert net and str(net.getSigType())=='SIGNAL'and not net.getNonDefaultRule()
        assert len(net.getITerms())==t['reported_fanout']+1 and not net.getBTerms()
        assert sum(str(p.getIoType())=='OUTPUT'for p in net.getITerms())==1
        assert t['new_master']in ('sg13g2_buf_8','sg13g2_buf_16')
        master=db.findMaster(t['new_master']);assert master
        assert i.swapMaster(master),('Native swap failed',i.getName())
        assert signature(i)['pins']==original[i.getName()]['pins']
        i.setPlacementStatus('PLACED');changes.append(dict(instance=i.getName(),old_master=t['master'],new_master=t['new_master']))
    assert topology(block)==nets and fixed_data(db)==fixed
    # Changed pin locations invalidate old signal routes. Fresh routing/RC is required.
    for n in block.getNets():
        if str(n.getSigType())in ('POWER','GROUND')or n.getName()in clock_nets:continue
        assert not n.getSWires()and n.getRSegCount()==n.getCapNodeCount()==0
        w,g=n.getWire(),n.getGlobalWire()
        if g and(not w or g.getId()!=w.getId()):odb.dbWire.destroy(g)
        if w:odb.dbWire.destroy(w)
        n.clearGuides();n.clearTracks()
    (OUT/'preparation.json').write_text(json.dumps(dict(original=original,topology=nets,fixed=fixed,changes=changes,clock_nets=sorted(clock_nets)),indent=2)+'\n')
    odb.write_db(db,str(OUT/'proposed.odb'))
def audit():
    old=json.loads((OUT/'preparation.json').read_text());db=load(OUT/'legalized.odb');block=db.getChip().getBlock()
    changes={r['instance']:r for r in old['changes']};observed=[]
    assert {i.getName()for i in block.getInsts()}==old['original'].keys()
    for name,before in old['original'].items():
        i=block.findInst(name);now=signature(i)
        if name in changes:
            assert now['master']==changes[name]['new_master']and now['pins']==before['pins']
            # A larger cell may move to a neighboring row. Its orientation must
            # follow that actual row, not the orientation of its abandoned site.
            box=i.getBBox();rows=[]
            for row in block.getRows():
                rb=row.getBBox()
                if rb.xMin()<=box.xMin() and box.xMax()<=rb.xMax() and rb.yMin()==box.yMin() and rb.yMax()==box.yMax():
                    rows.append(dict(name=row.getName(),orientation=str(row.getOrient()),site=row.getSite().getName()))
            observed.append(dict(instance=name,before=before,after=now,containing_rows=rows))
            (OUT/'target-placement-observation.json').write_text(json.dumps(observed,indent=2)+'\n')
            assert i.isPlaced(),('Unplaced resized instance',name,now)
            assert any(row['orientation']==now['orientation'] and row['site']==i.getMaster().getSite().getName() for row in rows),('Resized instance not aligned to native row orientation/site',name,now,rows)
        else:assert now==dict(before,status='FIRM'),('Untargeted instance changed',name)
        i.setPlacementStatus(before['status'])
    assert topology(block)==old['topology']and fixed_data(db)==old['fixed']
    for n in block.getNets():
        if str(n.getSigType())not in ('POWER','GROUND')and n.getName()not in old['clock_nets']:assert not n.getWire()and not n.getGlobalWire()and not n.getGuides()
    odb.write_db(db,str(OUT/'candidate.odb'))
    (OUT/'geometry-proof.json').write_text(json.dumps(dict(status='PASS_NATIVE_SELECTED_BUFFER_RESIZING_UNCHANGED_CONNECTIVITY',instances=len(old['original']),changes=observed,all_net_memberships_unchanged=True,all_other_instances_unchanged=True,pg_ports_ndr_unchanged=True,accepted=False,routed=False),indent=2)+'\n')
if os.environ.get('NSSOC_RESIZE_MODE')=='audit':audit()
else:prepare()
