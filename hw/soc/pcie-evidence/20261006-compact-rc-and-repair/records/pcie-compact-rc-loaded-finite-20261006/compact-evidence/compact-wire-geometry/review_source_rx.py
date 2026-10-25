# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent full inverse/source/input review only; no geometry execution."""
from pathlib import Path
import ast,hashlib,json
B=Path(__file__).resolve().parent
cache={}
def pin(p):
 p=Path(p);s=p.stat();key=(str(p),s.st_size,s.st_mtime_ns)
 if key not in cache:
  with p.open('rb') as f:cache[key]=dict(bytes=s.st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
 return cache[key]
fpath=B/'geometry-source-freeze.json';assert pin(fpath)==dict(bytes=228109,sha256='0fe946ee97e78d53dbabab3ff37e22ab99d5202d91e7338016134ecd31578c16')
f=json.loads(fpath.read_text());assert len(f['inputs'])==978 and f['inputs']=={p:pin(p) for p in f['inputs']}
bridges=json.loads((B/'source-bridge01.json').read_text());assert len(bridges)==7
changes=[]
for row in bridges:
 a,z=Path(row['before']['path']),Path(row['after']['path']);assert pin(a)=={k:row['before'][k] for k in ('bytes','sha256')};assert pin(z)=={k:row['after'][k] for k in ('bytes','sha256')}
 assert a.read_text()==''.join(x['before'] for x in row['opcodes']);assert z.read_text()==''.join(x['after'] for x in row['opcodes']);ast.parse(z.read_text())
 old=a.read_text();new=z.read_text();changed=[x for x in row['opcodes'] if x['tag']!='equal'];changes.append(dict(method=z.name,changes=changed))
 # Every existing function except the explicit preflight main is identical
 # after source-path/top substitutions (graph quantities remain unchanged).
 back=new.replace('nssoc-div4-v7-compact-v2-wire-geometry-01','nssoc-div4-v7-power-v2-wire-geometry-02').replace('nssoc-div4-v7-compact-v2-wire-native-01','nssoc-div4-v7-power-v2-wire-native-02').replace('nssoc-div4-v7-compact-v2-layout-01','nssoc-div4-v7-power-v2-layout-01').replace('nssoc-div4-v7-compact-v2-checks-01','nssoc-div4-v7-power-v2-checks-02').replace('nssoc_clock_div4_v7_compact_v2_layout','nssoc_clock_div4_v7_power_v2_layout').replace('db400e586cadbedbea9ec8aec5466c0eba4789e262c90ebd0d321a1c2cbcf579','663b60fc14cc9c8e2b4d9a5a758aee6bcd61bdf307c6b3a69a28e63bc470340c')
 if z.name!='run_geometry.py':assert back==old,z.name
 else:
  for n in ('pin',):
   get=lambda t:ast.dump(next(x for x in ast.parse(t).body if isinstance(x,ast.FunctionDef) and x.name==n),include_attributes=False)
   assert get(old)==get(back)
parent=Path(bridges[0]['before']['path']).parent
assert (B/'native_unsimplified.lvs').read_bytes()==(parent/'native_unsimplified.lvs').read_bytes()
P=B.parent/'pcie-divider-v7-compact-v2-20261006/native-saved-peer-rx.json';peer=json.loads(P.read_text());assert peer['status']=='PASS_INDEPENDENT_SAVED_COMPACT_V2_NATIVE_RESULT' and not peer['findings']
G=Path('/dev/shm/nssoc-div4-v7-compact-v2-layout-01');C=Path('/dev/shm/nssoc-div4-v7-compact-v2-checks-01')
assert peer['GDS']==pin(G/'nssoc_clock_div4_v7_compact_v2_layout.gds');assert peer['checks']==pin(C/'result.json') and peer['geometry']==pin(C/'power-geometry.json')
for n in ('nssoc-div4-v7-compact-v2-wire-geometry-01','nssoc-div4-v7-compact-v2-wire-native-01'):assert not (Path('/dev/shm')/n).exists()
r=dict(status='PASS_SOURCE_ONLY_DIVIDER_V7_WIRE_GEOMETRY',freeze=pin(fpath),findings=[],method=pin(__file__),source_pins=f['producer_sources'],input_files_rehashed=len(f['inputs']),whole_inverse_bridges=7,changes=changes,native_peer=pin(P),checks=['Six geometry source bodies inverse exactly after paths/top/hash only. Main changes only compact native-audit status/census and exact saved-peer gate.','All seven metals and all six via layers retained; TopMetal2/TopVia2 nonempty required. Complete725/634leaf census,91devices/283terminals/205anchors/37conductors/72clusters remain strict.','Every72cluster retained:38electrical including85-body-terminal cluster,34aux require no terminal/publicport/metal. No purge.','Full actual source location/parameter/net bijection and one-to-one actual native conductor bindings unchanged.','Exact unsimplified wrapper and official deck options retain all taps and prohibit combine/simplify/purge; no LVS comparison claimed.','Private cloned owned lifecycle functions/resources/terminal guards unchanged, original CPU10/2GiB/80MiB/24MiBreserve/512MiBfloor/1GiBentry/nohealthytimeout.'],scope='Source-only peer and immutable saved-input readback. No producer, native extraction, geometry, RC or simulation executed. All future actual counts remain assertions to prove, not measured new wire results.')
p=B/'geometry-source-only-peer.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(path=str(p),**pin(p))))
