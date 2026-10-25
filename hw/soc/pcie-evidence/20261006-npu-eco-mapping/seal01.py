# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Seal completed native SRAM mapping and independently checked graph bridge."""
from pathlib import Path
import json,hashlib,tarfile
R=Path.cwd();B=Path(__file__).absolute().parent;N=B/'native01';A=B/'nssoc-npu-eco-sram-mapping-20261006.tar.xz'
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
r=json.loads((N/'result.json').read_text());assert r['status']=='PASS_MATCHED32SRAM_MAPPING_AND_EXACT_ECO_BRIDGE_BOOT_PHYSICAL_PENDING'
peer=json.loads((B/'saved-native-peer-pll.json').read_text());assert peer['status'].startswith('PASS') and not peer.get('findings')
files={}
for p in sorted(N.rglob('*')):
 if p.is_file():assert not p.is_symlink();files['native/'+str(p.relative_to(N))]=p
for p in sorted(B.iterdir()):
 if p.is_file() and p.suffix in ('.py','.json','.log') and p.name not in ('package01.json',):files['review/'+p.name]=p
f=json.loads((B/'source-freeze01.json').read_text())
for path,h in f['inputs'].items():
 p=Path(path);assert pin(p)==h
 if 'tools' not in p.parts:files['source/'+str(p.relative_to(R))]=p
for name in ['sw/tests/test_npu_physical_eco_mapping.py','LICENSES/Apache-2.0.txt','LICENSES/CERN-OHL-W-2.0.txt','LICENSES/CC-BY-4.0.txt']:files['source/'+name]=R/name
pins={name:dict(restore_path=str(p),**pin(p)) for name,p in files.items()};assert not A.exists()
with tarfile.open(A,'w:xz',preset=3) as tar:
 for name,p in files.items():tar.add(p,arcname=name,recursive=False)
seen={}
with tarfile.open(A,'r:xz') as tar:
 for m in tar:
  assert m.isfile() and m.name not in seen and m.name in pins
  with tar.extractfile(m) as stream:h=hashlib.file_digest(stream,'sha256').hexdigest()
  assert dict(bytes=m.size,sha256=h)=={k:pins[m.name][k] for k in ('bytes','sha256')};seen[m.name]=True
assert set(seen)==set(pins)
for name,p in files.items():assert pin(p)=={k:pins[name][k] for k in ('bytes','sha256')}
result=dict(status='PASS_COMPLETE_NPU_ECO_MAPPING_ARCHIVE_MEMBER_READBACK',archive=dict(path=str(A),**pin(A)),members=pins,native_result=pin(N/'result.json'),peer=pin(B/'saved-native-peer-pll.json'),mapping_bridge=r['exact_combinational_bridge'],scope='Three actual same-recipe maps and exact nativegraph bridge. Boot/fullphysical/timing/manufacturing remain unaccepted.')
(B/'package01.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(status=result['status'],archive=result['archive'],members=len(pins))))
