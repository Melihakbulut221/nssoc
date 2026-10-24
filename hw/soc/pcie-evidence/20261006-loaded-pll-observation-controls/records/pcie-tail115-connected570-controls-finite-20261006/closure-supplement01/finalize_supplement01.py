# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Add closed packaging/roundtrip evidence to ready02; never rewrite ready01."""
from pathlib import Path
import hashlib,json,shutil
F=Path(__file__).resolve().parent
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
old=F/'ready-finite01.json';record=json.loads(old.read_text());assert record['status']=='READY_FINITE570_SOURCE_AND_CONTROL_EVIDENCE_PUBLIC'
assert not(F/'ready-finite02.json').exists()
for mode in ['seal','complete']:
 r=json.loads((F/f'{mode}-execution01.json').read_text());assert r['status']=='PASS_CLOSED_FINITE_RESOURCE_WRAPPER'
 for child in json.loads((F/f'{mode}-owned01.json').read_text())['processes']:
  assert child['returncode']==0 and child['status']=='REAPED_NO_LIVE_MEMBERS'and not Path('/proc',str(child['identity']['pid'])).exists()
launch=json.loads((F/'publication-launch01.json').read_text());assert not Path('/proc',str(launch['pid'])).exists();assert json.loads((F/'release01.json').read_text())['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS'
paths=[p for p in F.iterdir()if p.is_file()and p.suffix in ('.json','.py','.log','.txt')and p.name not in ('ready-finite01.json','ready-finite02.json')]
paths += [p for p in(F/'release01.transport').rglob('*')if p.is_file()and p.suffix=='.json']
paths += [F.parent/n for n in ['pcie-570-finite-seal01.log','pcie-570-finite-seal-wrapper01.log','pcie-570-finite-complete01.log','pcie-570-finite-complete-wrapper01.log','pcie-570-finite-publication01.log']]
for p in paths:
 rel=str(p.relative_to(F))if p.is_relative_to(F)else p.name
 q=F/'closure-supplement01'/rel;q.parent.mkdir(parents=True,exist_ok=True);assert not q.exists();shutil.copyfile(p,q);assert pin(q)==pin(p)
 record['compact_evidence'][str(q)]=pin(q);record['original_evidence'][str(p)]=pin(p)
 if p.suffix=='.py':record['method_allowlist'][str(p)]=pin(p)
record.update(parent_ready=dict(path=str(old),**pin(old)),method_files=len(record['method_allowlist']),compact_files=len(record['compact_evidence']),packaging_supplement_scope='Closed sealer/completer actual owned execution and V4 authenticated/anonymous roundtrip metadata; immutable original380-member archive unchanged. Raw publisher payload logs remain local and peer-readable; no active570native data is included.',independent_saved_peer_pending=True)
(F/'ready-finite02.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(dict(ready=pin(F/'ready-finite02.json'),methods=record['method_files'],compact=record['compact_files'],members=record['all_archive_members'],assets=len(record['assets']))))
