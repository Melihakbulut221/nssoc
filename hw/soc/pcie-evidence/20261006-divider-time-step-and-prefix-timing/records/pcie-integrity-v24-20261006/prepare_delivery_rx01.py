# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Seal explicit finite V24 evidence supplement; no EDA or publication."""
import hashlib,json,tarfile,io
from pathlib import Path
R=Path('/home/hasanmelih/Documents/ChatGPT/nnsoc');B=Path(__file__).resolve().parent

def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def save(p,x):
 with p.open('x')as f:json.dump(x,f,indent=2);f.write('\n')
j=lambda p:json.loads(p.read_text())
peer=j(B/'delivery02/saved-delivery-peer-rx02.json');assert peer['findings']==[] and peer['all_five_archive_members_readback']
# All producer/native/control jobs are closed; publishing artifacts are created later.
paths=[p for p in sorted(B.rglob('*'))if p.is_file()and '__pycache__'not in p.parts and p.suffix not in('.xz','.gz','.pyc')]
assert not any('publication' in p.name for p in paths)
evidence={str(p.relative_to(R)):pin(p)for p in paths}
products=peer['source_allowlist']
for p,h in products.items():assert pin(R/p)==h
members={('evidence/'+str(Path(p).relative_to(B.relative_to(R)))):dict(original=str(R/p),**h)for p,h in evidence.items()}
members.update({('sources/'+p):dict(original=str(R/p),**h)for p,h in products.items()})
name='pcie-integrity-v24-finite-peer-supplement-20261006.tar.xz';archive=B/name
with archive.open('xb')as sink:
 with tarfile.open(fileobj=sink,mode='w:xz',preset=6)as t:
  for n,h in members.items():t.add(h['original'],arcname=n,recursive=False)
  data=(json.dumps(members,indent=2)+'\n').encode();entry=tarfile.TarInfo('members.json');entry.size=len(data);entry.mode=0o644;t.addfile(entry,io.BytesIO(data))
seen=set()
with tarfile.open(archive,'r|xz')as t:
 for m in t:
  assert m.isfile()and m.name not in seen;seen.add(m.name)
  data=t.extractfile(m).read()
  if m.name!='members.json':assert dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())=={k:members[m.name][k]for k in('bytes','sha256')}
assert seen==set(members)|{'members.json'}
for p,h in evidence.items():assert pin(R/p)==h
save(B/'delivery-supplement-members01.json',members)
primary={k:{key:v[key]for key in('path','bytes','sha256','member_count')}for k,v in peer['archives'].items()if k in('component','controls','native')}
record=dict(status='SEALED_V24_FINITE_EVIDENCE_TIMING_REJECTED',source_freeze=pin(B/'source-freeze03.json'),source_allowlist=products,
 primary_archives=primary,supplement=dict(path=str(archive),**pin(archive),member_count=len(seen)),
 saved_delivery_peer=dict(path=str(B/'delivery02/saved-delivery-peer-rx02.json'),**pin(B/'delivery02/saved-delivery-peer-rx02.json')),
 evidence=evidence,historical_archive_coverage='Both419-member histories fully checked; all bytes covered by primary archives except exact807-byte checkpoint now included in supplement. Original tar compression bytes stay local and hash-bound.',
 product_controls=dict(executions=44,passed=43,historical_host_failed=1,current_predicates_covered=42,excluded_MAX4118=2,initial=dict(passed=41,failed=1),corrected_targeted=dict(passed=2,failed=0)),
 component_controls_separate=dict(passed=5,failed=0,matrices=140608,comparisons=3796416,actual_faults=4),native=j(B/'candidate-decision.json'),adopted=False,physical_acceptance=False,
 scope='Finite functional/native preplacement evidence only. V24 is rejected at unchanged4ns SS/TT; slow setup -3.634856ns regresses443.174ps againstV23. No mappedfunctional/placement/CTS/routeRC/PHY claim. Historical failures and helper versions remain explicit.')
save(B/'pcie-integrity-v24-finite-package-20261006.json',record)
print(json.dumps(dict(primary_members=sum(x['member_count']for x in primary.values()),supplement_members=len(seen),supplement=pin(archive),evidence_files=len(evidence),products=len(products))))
