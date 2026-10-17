# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bind closed V24 public byte receipts and exact finite delivery allowlists."""
import json,hashlib
from pathlib import Path
from datetime import datetime,timezone
R=Path('/home/hasanmelih/Documents/ChatGPT/nnsoc');B=Path(__file__).resolve().parent
j=lambda p:json.loads(p.read_text())
def pin(p):
 with Path(p).open('rb')as f:return dict(bytes=Path(p).stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
package=j(B/'pcie-integrity-v24-finite-package-20261006.json');release=j(B/'publication-release01.json')
assert release['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS'and release['publisher_revision']==4 and release['tag']=='evidence-20261006-pcie-closure'
assert len(release['files'])==len(release['assets'])==5
for row,asset in zip(release['files'],release['assets']):
 h={k:row[k]for k in('bytes','sha256')};assert pin(row['path'])==h
 assert row['name']==asset['name']and {k:asset[k]for k in h}==h
 assert asset['authenticated_roundtrip']is True and asset['anonymous_roundtrip']is True
birth=j(B/'publication-detached01.json');proc=Path('/proc')/str(birth['pid'])/'stat'
if proc.exists():
 fields=proc.read_text().rsplit(')',1)[1].split();assert int(fields[19])!=birth['start_ticks']or fields[0]=='Z'
for collection in ('source_allowlist','evidence'):
 for p,h in package[collection].items():assert pin(R/p)==h,p
peer=j(B/'delivery02/saved-delivery-peer-rx02.json')
evidence=package['evidence'].copy()
for n in ['delivery-supplement-members01.json','pcie-integrity-v24-finite-package-20261006.json','detach_publication_rx01.py','publication-once01.json','publication-detached01.json','publication-release01.json','publication01.log','finalize_delivery_rx01.py']:
 evidence[str((B/n).relative_to(R))]=pin(B/n)
record=dict(status='READY_V24_PREFIX_CONTEXT_NATIVE_SETUP_REJECTED_NOT_ADOPTED',utc=datetime.now(timezone.utc).isoformat(),
 source_freeze=package['source_freeze'],source_allowlist=package['source_allowlist'],controls=package['product_controls'],component_controls_separate=package['component_controls_separate'],
 archives={**package['primary_archives'],'peer_supplement':package['supplement']},archive_total_members=sum(x['member_count']for x in package['primary_archives'].values())+package['supplement']['member_count'],
 historical_archives={k:{n:v[n]for n in('path','bytes','sha256','member_count')}for k,v in peer['archives'].items()if k.startswith('history_')},historical_archive_coverage=package['historical_archive_coverage'],
 finite_package=pin(B/'pcie-integrity-v24-finite-package-20261006.json'),saved_delivery_peer=package['saved_delivery_peer'],functional_source_peer=pin(B/'source-only-peer-vco03.json'),saved_controls_peer=pin(B/'saved-controls-peer-vco03.json'),native_source_peer=pin(B/'native-source-only-peer01.json'),native_saved_peer=pin(B/'native-saved-peer-vco.json'),
 releases={'publication-release01.json':pin(B/'publication-release01.json')},assets=release['assets'],native=package['native'],evidence=evidence,evidence_original_relative_paths=True,
 adopted=False,stable_baseline='V11',physical_acceptance=False,scope=package['scope'])
with (B/'ready-finite.json').open('x')as f:json.dump(record,f,indent=2);f.write('\n')
print(json.dumps(dict(ready=pin(B/'ready-finite.json'),source_count=len(record['source_allowlist']),evidence_count=len(evidence),archive_members=record['archive_total_members'],public_assets=len(record['assets']),setup=record['native']['setup_ns'])))
