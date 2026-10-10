# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Publish only local finite metadata copies/allowlists for root review."""
from pathlib import Path
import hashlib,json
R=Path.cwd();B=Path(__file__).resolve().parent;D=R/'hw/soc/pcie-evidence/20261005-integrity-read-timing'
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def exact_copy(source,target):
 target.parent.mkdir(parents=True,exist_ok=True)
 if target.exists():assert pin(target)==pin(source)
 else:
  with target.open('xb') as out:out.write(source.read_bytes())
 assert pin(target)==pin(source)
 if b'SPDX-License-Identifier:' not in source.read_bytes()[:4096]:
  sp=target.with_name(target.name+'.license');data=b'SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut\nSPDX-License-Identifier: CC-BY-4.0\n'
  if sp.exists():assert sp.read_bytes()==data
  else:
   with sp.open('xb') as out:out.write(data)
record=json.loads((B/'inventory-final.json').read_text());assert record['full_capsule_member_count']==728
for filename,key in [('active-source-allowlist.json','active_source_allowlist'),('historical-source-allowlist.json','historical_source_copies')]:
 p=B/filename;assert not p.exists();p.write_text(json.dumps(record[key],indent=2)+'\n')
exact_copy(B/'inventory-final.json',D/'delivery-inventory.json')
for n in ['build_inventory.py','configuration.json','build.log','active-source-allowlist.json','historical-source-allowlist.json',Path(__file__).name]:exact_copy(B/n,D/'curation'/n)
all_files={str(p.relative_to(R)):pin(p) for p in sorted(D.rglob('*')) if p.is_file()}
for path,h in record['evidence'].items():assert pin(R/path)=={k:h[k] for k in ('bytes','sha256')}
for path,h in record['license_sidecars'].items():assert pin(R/path)==h
for path,h in record['active_source_allowlist'].items():assert pin(R/path)==h
source=B/'ready-source-allowlist.json';source.write_text(json.dumps(record['active_source_allowlist'],indent=2)+'\n')
evidence=B/'final-evidence-allowlist.json';evidence.write_text(json.dumps(all_files,indent=2)+'\n')
docs={str(p):pin(p) for p in [Path('docs/132-pcie-integrity-read-timing.md'),Path('docs/00-index.md')]}
ready=dict(status='READY_FOR_ROOT_REVIEW_STAGE_DOCS_LICENSE_AND_PUSH',source_allowlist=dict(path=str(source),**pin(source)),evidence_allowlist=dict(path=str(evidence),**pin(evidence)),delivery_inventory=dict(path=str(D/'delivery-inventory.json'),**pin(D/'delivery-inventory.json')),active_source_count=9,historical_source_count=18,evidence_files_including_sidecars_and_curation=len(all_files),evidence_bytes=sum(x['bytes'] for x in all_files.values()),docs=docs,full_capsule_readbacks=6,full_capsule_members=728,public_assets=12,transport_attempts=60,gzip_transport_streams=120,git_staged=False,git_committed=False,git_pushed=False,native_executed=False,tests_rerun=False,physical_acceptance=False,notes='Frozen V15/V16 originals untouched; historical exact copies under evidence original relative paths. Only V17 is active source allowlist. Large six raw capsules stay at exact verified public assets, not staged as git blobs. Parent owns final docs/license checks and commit/push.')
p=B/'ready-finite.json';p.write_text(json.dumps(ready,indent=2)+'\n');print(json.dumps(dict(path=str(p),**pin(p),**{k:ready[k] for k in ['active_source_count','historical_source_count','evidence_files_including_sidecars_and_curation','evidence_bytes']})))
