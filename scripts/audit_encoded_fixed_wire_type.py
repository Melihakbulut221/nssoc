#!/usr/bin/env python3
"""Assert the native encoded wire type actually consumed by DRT."""
import os,json,hashlib
from pathlib import Path
import odb
p=Path(os.environ['NSSOC_FIXED_VERIFY_ODB']);before=hashlib.sha256(p.read_bytes()).hexdigest()
d=odb.dbDatabase.create();odb.read_db(d,str(p));b=d.getChip().getBlock()
names=json.loads(Path(os.environ['NSSOC_FIXED_VERIFY_NAMES']).read_text());assert len(names)==len(set(names))and len(names)>90000
expected=os.environ['NSSOC_FIXED_VERIFY_TYPE'];assert expected in ['FIXED','ROUTED']
def wiretype(net):
 wire=net.getWire();assert wire
 dec=odb.dbWireDecoder();dec.begin(wire);assert dec.next()==dec.PATH
 return str(dec.getWireType())
# Independent encoder fixtures reject metadata-only fixation.
name='__nssoc_encoded_wire_type_fixture';assert not b.findNet(name)
n=odb.dbNet.create(b,name);layer=b.getTech().findLayer('Metal2');assert layer
try:
 w=odb.dbWire.create(n);e=odb.dbWireEncoder();e.begin(w);e.newPath(layer,'ROUTED');e.addPoint(10000,10000);e.addPoint(20000,10000);e.end()
 n.setWireType('FIXED');assert wiretype(n)=='ROUTED'
 odb.dbWire.destroy(w);w=odb.dbWire.create(n);e.begin(w);e.newPath(layer,'FIXED');e.addPoint(10000,10000);e.addPoint(20000,10000);e.end();assert wiretype(n)=='FIXED'
finally:odb.dbNet.destroy(n)
bad=[]
for name in names:
 n=b.findNet(name);assert n
 actual=wiretype(n)
 if actual!=expected:bad.append(dict(net=name,actual=actual))
assert hashlib.sha256(p.read_bytes()).hexdigest()==before
Path(os.environ['NSSOC_FIXED_VERIFY_REPORT']).write_text(json.dumps(dict(accepted=False,expected_encoded_type=expected,checked_nets=len(names),wrong_types=bad,source_unchanged=True,source_sha256=before,controls=dict(metadata_only_fix_rejected=True,encoded_fixed_accepted=True)),indent=2)+'\n')
assert not bad,('wrong_native_wire_type',len(bad),bad[:10])
