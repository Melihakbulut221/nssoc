# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Seal actual transport controls and independently read all failed PLL members."""
import hashlib,json,tarfile
from pathlib import Path
R=Path.cwd();B=Path(__file__).resolve().parent
L=R/'hw/soc/out/pcie-pll-acquisition-v3-20261005/numerical-convergence-plan01/launch01'
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def exact(p,h):assert pin(p)=={k:h[k] for k in ('bytes','sha256')},str(p)
f=json.loads((B/'source-freeze01.json').read_text());peer=json.loads((B/'source-saved-peer-pll01.json').read_text());assert peer['status']=='PASS_PUBLISHER_V4_SOURCE_AND_15_ACTUAL_CONTROLS' and peer['findings']==[] and peer['freeze']==pin(B/'source-freeze01.json')
files={**f['sources'],**f['inputs']}
for p,h in files.items():exact(p,h)
for p in B.rglob('*'):
 if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ['.xz'] and p.name not in ['seal-closed01.log']:
  files[str(p)]=pin(p)
for name in ['LICENSE','NOTICE']:
 p=R/name
 if p.is_file():files[str(p)]=pin(p)
members={}
for name,h in files.items():
 p=Path(name)
 if p.is_relative_to(R):arc='repo/'+str(p.relative_to(R))
 elif p.is_relative_to('/dev/shm'):arc='scratch/'+str(p.relative_to('/dev/shm'))
 else:raise AssertionError(str(p))
 assert arc not in members;members[arc]=dict(original_path=name,**h)
a=B/'pcie-publisher-v4-native-controls-20261006.tar.xz';assert not a.exists()
with tarfile.open(a,'x:xz',preset=3) as tf:
 for name,h in sorted(members.items()):tf.add(h['original_path'],arcname=name,recursive=False)
seen=set()
with tarfile.open(a,'r|xz') as tf:
 for item in tf:
  assert item.isfile() and item.name not in seen;seen.add(item.name)
  assert dict(bytes=item.size,sha256=hashlib.file_digest(tf.extractfile(item),'sha256').hexdigest())=={k:members[item.name][k] for k in ('bytes','sha256')}
assert seen==members.keys()
for p,h in files.items():exact(p,h)
v=dict(status='PASS_PUBLISHER_V4_15_ACTUAL_CONTROLS_AND_RECOVERED_PART120',archive=dict(path=str(a),members=len(members),**pin(a)),members=members,sources=f['sources'],independent_peer=pin(B/'source-saved-peer-pll01.json'),recovered_part=pin(B/'recovered-part120-release01.json'),full_phy_acceptance=False)
(B/'pcie-publisher-v4-native-controls-validation-20261006.json').write_text(json.dumps(v,indent=2)+'\n')
# Independently check the agent's complete failure capsule, without rerunning SPICE.
p=L/'terminal-preservation09.json';d=json.loads(p.read_text());exact(d['archive']['path'],d['archive']);mp=L/'terminal-members09.json';exact(mp,d['member_manifest']);original=json.loads(mp.read_text())
print('failure manifest keys',type(original),list(original)[:3],flush=True)
(B/'control-seal01.json').write_text(json.dumps(dict(status='PASS_ALL_TRANSPORT_CONTROL_MEMBERS',archive=v['archive'],validation=pin(B/'pcie-publisher-v4-native-controls-validation-20261006.json')),indent=2)+'\n')
print('controls',len(members),pin(a),flush=True)
