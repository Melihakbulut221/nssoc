#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Add positive native buffers near measured data drivers; preserve every old cell."""
import copy,hashlib,json,os
from pathlib import Path
import odb
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-onehot-coverage-data-prepare'
SOURCE=OUT/'source/run/2-openroad-detailedrouting/soc_top.odb'
EXPECTED='782c6fb2990e35dd422f817eaab7a5aa7a98bab35b8da1ee2c15dcc2f8bc3d90'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==EXPECTED
TARGETS=json.loads((OUT/'targets.json').read_text())['targets'];COUNT=len(TARGETS)
assert 1<=COUNT<=128

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


def topology(b):
    return {n.getName():dict(kind=str(n.getSigType()),ndr=n.getNonDefaultRule().getName()if n.getNonDefaultRule()else None,pins=sorted([t.getInst().getName(),t.getMTerm().getName()]for t in n.getITerms()),ports=sorted(p.getName()for p in n.getBTerms()))for n in b.getNets()}
def point(t):
    v=t.getAvgXY();assert len(v)==3 and v[0]
    return v[1],v[2]
def prepare():
    db=load(SOURCE);b=db.getChip().getBlock();assert len(b.getInsts())==150291
    targets=TARGETS
    assert len({(t['instance'],t['pin'])for t in targets})==COUNT
    original={i.getName():signature(i)for i in b.getInsts()}
    expected=topology(b);fixed=fixed_data(db);changes=[]
    for i in b.getInsts():i.setPlacementStatus('FIRM')
    master=db.findMaster('sg13g2_buf_16');assert master
    assert {p.getName():str(p.getIoType())for p in master.getMTerms()if str(p.getSigType())=='SIGNAL'}=={'A':'INPUT','X':'OUTPUT'}
    for index,t in enumerate(targets):
        driver=b.findInst(t['instance']);assert driver and driver.getMaster().getName()==t['master']
        term=driver.findITerm(t['pin']);assert term and str(term.getIoType())=='OUTPUT'
        net=term.getNet();assert net and str(net.getSigType())=='SIGNAL'and not net.getNonDefaultRule()
        assert all(str(p.getIoType())=='OUTPUT'for p in net.getBTerms())
        assert len(net.getITerms())+len(net.getBTerms())==t['reported_fanout']+1
        outputs=[(p.getInst().getName(),p.getMTerm().getName())for p in net.getITerms()if str(p.getIoType())=='OUTPUT']
        assert outputs==[(t['instance'],t['pin'])]
        assert all(str(p.getIoType())in ('INPUT','OUTPUT')for p in net.getITerms())
        added='nssoc_coverage_data_buffer_'+str(index);local='nssoc_coverage_data_local_'+str(index)
        assert not b.findInst(added)and not b.findNet(local)
        # Derive expected topology before applying the edit.
        expected[net.getName()]['pins'].remove([t['instance'],t['pin']])
        expected[net.getName()]['pins'].append([added,'X']);expected[net.getName()]['pins'].sort()
        expected[local]=dict(kind='SIGNAL',ndr=None,pins=sorted([[t['instance'],t['pin']],[added,'A']]),ports=[])
        local_net=odb.dbNet.create(b,local);buffer=odb.dbInst.create(b,master,added);assert buffer and local_net
        buffer.setOrient(driver.getOrient());x,y=driver.getLocation()
        buffer.setLocation(x+driver.getMaster().getWidth(),y);buffer.setPlacementStatus('PLACED')
        term.disconnect();term.connect(local_net);buffer.findITerm('A').connect(local_net);buffer.findITerm('X').connect(net)
        for p in buffer.getITerms():
            kind=str(p.getSigType())
            if kind in ('POWER','GROUND'):
                peers=[q for q in driver.getITerms()if str(q.getSigType())==kind]
                assert len(peers)==1 and peers[0].getNet()
                p.connect(peers[0].getNet())
                expected[peers[0].getNet().getName()]['pins'].append([added,p.getMTerm().getName()])
                expected[peers[0].getNet().getName()]['pins'].sort()
        changes.append(dict(driver=t['instance'],driver_pin=t['pin'],original_net=net.getName(),local_net=local,buffer=added,buffer_master=master.getName(),initial_buffer_location_dbu=list(buffer.getLocation()),original_terminal_count=t['reported_fanout']+1))
    assert topology(b)==expected and fixed_data(db)==fixed
    for n in b.getNets():
        if str(n.getSigType())in ('POWER','GROUND'):continue
        assert not n.getSWires()and n.getRSegCount()==n.getCapNodeCount()==0
        w,g=n.getWire(),n.getGlobalWire()
        if g and(not w or g.getId()!=w.getId()):odb.dbWire.destroy(g)
        if w:odb.dbWire.destroy(w)
        n.clearGuides();n.clearTracks()
    (OUT/'preparation.json').write_text(json.dumps(dict(original=original,expected_topology=expected,fixed_data_sha256=fixed,changes=changes),indent=2)+'\n')
    odb.write_db(db,str(OUT/'proposed.odb'))
def audit():
    old=json.loads((OUT/'preparation.json').read_text());db=load(OUT/'legalized.odb');b=db.getChip().getBlock()
    changes={r['driver']:r for r in old['changes']};assert len(changes)==COUNT
    assert len(b.getInsts())==(150291+COUNT)
    assert {i.getName()for i in b.getInsts()}==set(old['original'])|{r['buffer']for r in old['changes']}
    for name,sig in old['original'].items():
        i=b.findInst(name);assert i and i.isFixed()
        expected=dict(sig,pins=dict(sig['pins']),status='FIRM')
        if name in changes:expected['pins'][changes[name]['driver_pin']]=changes[name]['local_net']
        assert signature(i)==expected,('Original cell geometry/master/pins changed',name)
        i.setPlacementStatus(sig['status'])
    assert topology(b)==old['expected_topology']
    assert fixed_data(db)==old['fixed_data_sha256']
    additions=[];scale=b.getDbUnitsPerMicron();assert scale>0
    for r in old['changes']:
        i=b.findInst(r['buffer']);driver=b.findInst(r['driver'])
        assert i and i.getMaster().getName()=='sg13g2_buf_16'and i.isPlaced()
        assert i.findITerm('A').getNet().getName()==r['local_net']and i.findITerm('X').getNet().getName()==r['original_net']
        distance=sum(abs(a-c)for a,c in zip(point(driver.findITerm(r['driver_pin'])),point(i.findITerm('A'))))/scale
        box=i.getBBox();rows=[]
        for row in b.getRows():
            rb=row.getBBox()
            if rb.xMin()<=box.xMin()and box.xMax()<=rb.xMax()and rb.yMin()==box.yMin()and rb.yMax()==box.yMax():
                rows.append(dict(name=row.getName(),orientation=str(row.getOrient()),site=row.getSite().getName()))
        obs=dict(name=i.getName(),signature=signature(i),driver_to_buffer_manhattan_um=distance,containing_rows=rows)
        additions.append(obs)
        (OUT/'buffer-placement-observations.json').write_text(json.dumps(additions,indent=2)+'\n')
        assert distance<=80,('Buffer too far from actual driver',r['driver'],distance)
        assert any(row['orientation']==str(i.getOrient())and row['site']==i.getMaster().getSite().getName()for row in rows)
    for n in b.getNets():
        if str(n.getSigType())not in ('POWER','GROUND'):assert not n.getWire()and not n.getGlobalWire()and not n.getGuides()
    odb.write_db(db,str(OUT/'candidate.odb'))
    (OUT/'geometry-proof.json').write_text(json.dumps(dict(status='PASS_NATIVE_NEAR_DRIVER_BUFFERS_ORIGINAL_GEOMETRY_AND_EXACT_EXPECTED_TOPOLOGY',accepted=False,original_instances=150291,added=additions,changes=old['changes'],maximum_driver_to_buffer_um=max(a['driver_to_buffer_manhattan_um']for a in additions),all_original_cells_geometry_preserved=True,all_expected_net_memberships_preserved=True,pg_ports_ndr_unchanged=True,scope='Positive native buffers on measured high-delay weak data drivers. All original150291cells including666latest route diodes retained. Original ports retained on original nets. Buffers placed <=80um from driver pin. No route, extracted timing, antenna, LVS or PHY acceptance.'),indent=2)+'\n')
if os.environ.get('NSSOC_CRITICAL_ECO_MODE')=='audit':audit()
else:prepare()
