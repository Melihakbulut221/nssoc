#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Audit the candidate geometry independently of timing/Boolean equation proof."""
import copy,hashlib,json,os
from pathlib import Path
import odb
OUT=Path(os.environ['NSSOC_RESIZER_OUT'])
def sha(p):
    with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def load(path):
    db=odb.dbDatabase.create();odb.read_db(db,str(path));return db
def cell(i):
    return dict(master=i.getMaster().getName(),location=list(i.getLocation()),origin=list(i.getOrigin()),
        orientation=str(i.getOrient()),status=str(i.getPlacementStatus()),dont_touch=i.isDoNotTouch(),
        pins={t.getMTerm().getName():t.getNet().getName()if t.getNet()else None for t in i.getITerms()})
def protected(i):
    return i.getMaster().isBlock()or any(str(t.getMTerm().getSigType())=='CLOCK'or
        (t.getNet()and str(t.getNet().getSigType())=='CLOCK')for t in i.getITerms())
def boundary(db):
    b=db.getChip().getBlock()
    rows=[]
    for n in b.getNets():
        rule=n.getNonDefaultRule()
        if rule:rows.append(('ndr',n.getName(),rule.getName(),rule.getHardSpacing(),
            [(l.getName(),rule.getLayerRule(l).getWidth(),rule.getLayerRule(l).getSpacing())
             for l in db.getTech().getLayers()if rule.getLayerRule(l)]))
        if str(n.getSigType())in ('POWER','GROUND'):
            rows.append(('pg',n.getName(),[(w.isVia(),
                w.getTechVia().getName()if w.isVia()and w.getTechVia()else None,
                w.getBlockVia().getName()if w.isVia()and w.getBlockVia()else None,
                w.getTechLayer().getName()if not w.isVia()else None,
                w.xMin(),w.yMin(),w.xMax(),w.yMax())for s in n.getSWires()for w in s.getWires()]))
    rows += [('port',p.getName(),str(p.getIoType()),str(p.getSigType()),
        [(r.getTechLayer().getName(),r.xMin(),r.yMin(),r.xMax(),r.yMax())for pin in p.getBPins()for r in pin.getBoxes()])
        for p in b.getBTerms()]
    return sorted(rows,key=repr)
def validate(a,b,guarded):
    assert set(a)<=set(b),'Original instance removed'
    for name,old in a.items():
        new=b[name]
        assert old['dont_touch']==new['dont_touch'],'Original dont-touch flag changed'
        assert old['pins'].keys()==new['pins'].keys(),'Pin interface changed'
        if name in guarded:
            # Data inputs may acquire a positive hold buffer; clock pin nets
            # and all geometry/master must remain exact. Equations checked separately.
            assert {k:v for k,v in old.items()if k!='pins'}=={k:v for k,v in new.items()if k!='pins'},('Clock/SRAM geometry changed',name)
        elif old['master']==new['master']:
            assert {k:v for k,v in old.items()if k!='pins'}=={k:v for k,v in new.items()if k!='pins'},('Unresized source geometry changed',name)
    return True
def main():
    source=OUT/'source/run/1-openroad-detailedrouting/soc_top.odb';candidate=OUT/'candidate.odb'
    assert sha(source)=='bde963927da325e3f66c1c62d6f78f5db4c60b1344670ebabd04d3339c1a5850'
    a=load(source);b=load(candidate);ab=a.getChip().getBlock();bb=b.getChip().getBlock()
    old={i.getName():cell(i)for i in ab.getInsts()};new={i.getName():cell(i)for i in bb.getInsts()}
    guarded={i.getName()for i in ab.getInsts()if protected(i)}
    assert len(old)==151022 and sum(i.getMaster().isBlock()for i in ab.getInsts())==20
    validate(old,new,guarded);assert boundary(a)==boundary(b),'PG/NDR/port geometry changed'
    for i in ab.getInsts():
        for t in i.getITerms():
            if str(t.getMTerm().getSigType())=='CLOCK'or (t.getNet()and str(t.getNet().getSigType())=='CLOCK'):
                assert new[i.getName()]['pins'][t.getMTerm().getName()]==old[i.getName()]['pins'][t.getMTerm().getName()]
    # Negative controls on actual observed snapshots, not synthetic candidate reports.
    rejects=[]
    bad=copy.deepcopy(new);bad.pop(next(iter(old)))
    try:validate(old,bad,guarded)
    except AssertionError:rejects.append('removed-original')
    g=next(iter(guarded));bad=copy.deepcopy(new);bad[g]['location'][0]+=1
    try:validate(old,bad,guarded)
    except AssertionError:rejects.append('moved-clock-or-sram')
    assert len(rejects)==2
    changes=[dict(instance=n,before=old[n],after=new[n])for n in old if old[n]!=new[n]]
    added={n:new[n]for n in new.keys()-old.keys()}
    # Hold repair may only add positive standard buffers. Liberty proof is mandatory.
    assert all(r['master'].startswith('sg13g2_buf_')for r in added.values()),'Unexpected added function'
    r=dict(status='PASS_SCOPED_CANDIDATE_GEOMETRY_NOT_ROUTE_OR_LVS',original_instances=len(old),
        guarded_instances=len(guarded),added=added,changes=changes,rejected=rejects,
        pg_ndr_ports_preserved=True,clock_pins_and_clock_sram_geometry_preserved=True,
        source_sha256=sha(source),candidate_sha256=sha(candidate),accepted=False)
    (OUT/'geometry.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
