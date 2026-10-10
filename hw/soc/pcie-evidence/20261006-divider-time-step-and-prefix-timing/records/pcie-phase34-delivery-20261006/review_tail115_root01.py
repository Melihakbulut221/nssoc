# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent finite Tail115 full archive and exact source/record readback."""
import hashlib,json,tarfile
from pathlib import Path
R=Path.cwd();B=Path(__file__).resolve().parent;F=R/'hw/soc/out/pcie-tail115-layout-wire-loaded-finite-20261006';P=F/'ready-finite01.json'
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def exact(p,h):assert pin(p)=={k:h[k] for k in ('bytes','sha256')},str(p)
j=json.loads(P.read_text());assert len(j['sources'])==26 and len(j['compact_evidence'])==312 and j['all_archive_members']==991
for col in ('sources','compact_evidence','original_evidence','public_receipts'):
 for p,h in j[col].items():exact(p,h)
assert len(j['archives'])==len(j['assets'])==4;total=0
for a in j['archives']:
 exact(a['path'],a);exact(a['manifest'],a['manifest_pin']);m=json.loads(Path(a['manifest']).read_text());members=m.get('members',m);seen={}
 with tarfile.open(a['path'],'r|xz') as tf:
  for f in tf:
   assert f.isfile() and f.name not in seen
   h=dict(bytes=f.size,sha256=hashlib.file_digest(tf.extractfile(f),'sha256').hexdigest());assert h=={k:members[f.name][k] for k in ('bytes','sha256')};seen[f.name]=h
 assert seen.keys()==members.keys() and len(seen)==a['members'];total+=len(seen)
 q=json.loads(Path(a['public_receipt']).read_text());assert q['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS';asset=next(x for x in q['assets'] if x['name']==Path(a['path']).name);assert asset['authenticated_roundtrip'] and asset['anonymous_roundtrip'];exact(a['path'],asset)
assert total==991
W=R/'hw/soc/out/pcie-tail115-wave-peer-rx-20261006';wave=json.loads((W/'result.json').read_text());assert wave['status'].startswith('PASS_')
extra={str(p):pin(p) for p in W.iterdir() if p.is_file()};x=dict(status='PASS_ROOT_TAIL115_FINITE991MEMBERS_AND_INDEPENDENT_RAW_PEER',ready=pin(P),sources={str(Path(p).relative_to(R)):h for p,h in j['sources'].items()},compact=j['compact_evidence'],extra=extra,archives=j['archives'],public_assets=j['assets'],members=991,independent_wave_peer=dict(path=str(W/'result.json'),**pin(W/'result.json')),findings=[],method=pin(__file__),scope='Exact26sources312compact plus independentrawpeer; all991archive members read completely. Original full34ns strictFAIL remains. Halfstep/quarterstep or future numerical convergence excluded.',full_phy_acceptance=False)
(B/'tail115-review01.json').write_text(json.dumps(x,indent=2)+'\n');print(dict(status=x['status'],members=total,sources=26,compact=312,extra=len(extra)))
