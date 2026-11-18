#!/usr/bin/env python3
"""Read back exported boundary against native source ODB, without modifying it."""
import json,os,hashlib
from pathlib import Path
import odb
spec=json.loads(Path(os.environ['NSSOC_BOUNDARY_INPUTS']).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
for k in ['odb','lef','contract']:assert sha(spec[k]['path'])==spec[k]['sha256']
db=odb.dbDatabase.create();odb.read_db(db,spec['odb']['path']);block=db.getChip().getBlock()
lib=odb.read_lef(db,spec['lef']['path']);assert lib
master=lib.findMaster(block.getName());assert master
area=block.getDieArea();assert area.xMin()==area.yMin()==0
assert master.getWidth()==area.xMax() and master.getHeight()==area.yMax()
original={t.getName():t for t in block.getBTerms()};exported={t.getName():t for t in master.getMTerms()}
assert set(original)==set(exported),dict(missing=sorted(set(original)-set(exported)),extra=sorted(set(exported)-set(original)))
contract=json.loads(Path(spec['contract']['path']).read_text())
expected=set()
for n,p in contract['core_ports'].items():
    expected.update([n] if p['width']==1 else [f'{n}[{i}]' for i in range(p['width'])])
signals={n for n,t in original.items() if str(t.getSigType())not in ('POWER','GROUND')}
assert signals==expected,dict(missing=sorted(expected-signals),extra=sorted(signals-expected))
def box(b):return (b.getTechLayer().getName(),b.xMin(),b.yMin(),b.xMax(),b.yMax())
rows=[]
for n,t in sorted(original.items()):
    m=exported[n]
    assert str(t.getIoType())==str(m.getIoType()) and str(t.getSigType())==str(m.getSigType()),n
    old={box(b)for p in t.getBPins()for b in p.getBoxes()}
    new={box(b)for p in m.getMPins()for b in p.getGeometry()}
    assert old==new,(n,sorted(old-new),sorted(new-old))
    assert old,('Pin has no geometry',n)
    rows.append(dict(name=n,direction=str(t.getIoType()),signal_type=str(t.getSigType()),rectangles=sorted(old)))
for k in ['odb','lef','contract']:assert sha(spec[k]['path'])==spec[k]['sha256']
result=dict(status='PASS_PROVISIONAL_NATIVE_BOUNDARY_READBACK_NOT_FINAL_ROUTE',
    accepted=False,final_routed_core=False,source_unchanged=True,dbu_per_um=block.getDbUnitsPerMicron(),
    size_dbu=[master.getWidth(),master.getHeight()],signal_pins=len(signals),
    supply_pins=[n for n in original if n not in signals],pins=rows)
Path(spec['output']).write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items()if k!='pins'}))
