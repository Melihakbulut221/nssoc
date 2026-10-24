# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Seal exact physical prototype, independent replay and retained failed revisions."""
from pathlib import Path
import hashlib,json,tarfile
R=Path.cwd();B=Path(__file__).resolve().parent

def pin(p):
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
source=json.loads((B/'native-schema-source-freeze01.json').read_text());assert len(source)==7 and source=={n:pin(R/n) for n in source}
peer=json.loads((B/'native02-peer-rx/review.json').read_text());assert peer['status']=='PASS_INDEPENDENT_SAVED_DIVIDER_V7_NATIVE02_FINITE_PHYSICAL_REVIEW'
assert peer['source_pins']==source and peer['full_member_readback']==434
releases={}
for n in ('native01','native02'):
 p=B/f'release-{n}.json';release=json.loads(p.read_text());assert release['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS'
 assert len(release['assets'])==1 and all(a['authenticated_roundtrip'] and a['anonymous_roundtrip'] for a in release['assets'])
 a=release['assets'][0];assert pin(B/a['name'])=={k:a[k] for k in ('bytes','sha256')};releases[n]=dict(receipt=dict(path=str(p),**pin(p)),asset=a)
ready=dict(status='FINITE_STANDALONE_DIVIDER_V7_NATIVE_PHYSICAL_PROTOTYPE_READY',source_pins=source,native_summary=json.loads((B/'native02-summary.json').read_text()),independent_peer=dict(path=str(B/'native02-peer-rx/review.json'),**pin(B/'native02-peer-rx/review.json')),public_captures=releases,source_controls=42,native_schema_controls=18,original_source_boundary_findings_and_native_parser_failure_preserved=True,independent_peer_initial_XML_selector_error_preserved=True,no_dut_change_between_native01_and02=True,qualification={'wire_RC':False,'loaded_postlayout_division':False,'clockbank_integration':False,'full_PHY_or_manufacturing':False})
(B/'finite-ready.json').write_text(json.dumps(ready,indent=2)+'\n')
files={'project/'+n:R/n for n in source}
excluded={'continuation.json','next-wire-plan.json','preflight-inputs01.json'}
for p in sorted(B.rglob('*')):
 if p.is_file() and not p.is_symlink() and not p.name.endswith('.tar.xz') and p.name not in excluded:
  assert p.stat().st_size <= 3*1024**2
  files['review/'+str(p.relative_to(B))]=p
for name in ('Apache-2.0','CERN-OHL-W-2.0','CC-BY-4.0'):
 files['licenses/'+name+'.txt']=R/'LICENSES'/(name+'.txt')
members={n:pin(p) for n,p in files.items()};cap=B/'pcie-divider-v7-finite-native-peers.tar.xz';assert not cap.exists()
with tarfile.open(cap,'w:xz',preset=1) as arc:
 for n,p in files.items():arc.add(p,arcname=n,recursive=False)
seen={}
with tarfile.open(cap,'r|xz') as arc:
 for item in arc:
  assert item.isfile() and item.name not in seen;seen[item.name]=dict(bytes=item.size,sha256=hashlib.file_digest(arc.extractfile(item),'sha256').hexdigest())
assert seen==members and all(pin(p)==members[n] for n,p in files.items())
(B/'finite-peer-members.json').write_text(json.dumps(members,indent=2)+'\n')
receipt=dict(status='SEALED_INDEPENDENT_PHYSICAL_PROTOTYPE_AND_FAILURE_HISTORY',archive=dict(path=str(cap),**pin(cap)),members=len(members),finite_ready=pin(B/'finite-ready.json'),source_pins=source,no_product_acceptance=True)
(B/'finite-peer-validation.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
