# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Add explicit metadata licenses when embedded source SPDX text was ambiguous."""
from pathlib import Path
import hashlib,json
R=Path.cwd();B=Path(__file__).resolve().parent;D=R/'hw/soc/pcie-evidence/20261005-integrity-read-timing'
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
prior=json.loads((B/'final-evidence-allowlist.json').read_text())
for p,h in prior.items():assert pin(R/p)==h
added={};data=b'SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut\nSPDX-License-Identifier: CC-BY-4.0\n'
for path in sorted(prior):
 p=R/path
 if p.suffix not in ('.json','.log','.diff','.txt','.gz'):continue
 q=p.with_name(p.name+'.license')
 if q.exists():assert q.read_bytes()==data
 else:
  with q.open('xb') as out:out.write(data)
  added[str(q.relative_to(R))]=pin(q)
method=D/'curation'/Path(__file__).name;assert not method.exists();method.write_bytes(Path(__file__).read_bytes())
r=dict(status='PASS_ADDITIVE_METADATA_LICENSE_COMPLETION_NO_CAPTURE_BYTES_CHANGED',method=pin(__file__),previous_allowlist=pin(B/'final-evidence-allowlist.json'),new_sidecars=added,prior_all663_files_rehashed_unchanged=True,reason='JSON/patch/log metadata can contain embedded SPDX strings from serialized source. Every metadata file now receives its own CC-BY-4.0 sidecar; original code headers remain unchanged.',capsules_repeated=False)
p=D/'curation/metadata-license-supplement.json';p.write_text(json.dumps(r,indent=2)+'\n');p.with_name(p.name+'.license').write_bytes(data)
files={str(p.relative_to(R)):pin(p) for p in sorted(D.rglob('*')) if p.is_file()}
for p,h in prior.items():assert pin(R/p)==h
out=B/'final-evidence-allowlist02.json';assert not out.exists();out.write_text(json.dumps(files,indent=2)+'\n')
ready=json.loads((B/'ready-finite.json').read_text());ready.update(evidence_allowlist=dict(path=str(out),**pin(out)),evidence_files_including_sidecars_and_curation=len(files),evidence_bytes=sum(x['bytes'] for x in files.values()),license_supplement=dict(path=str(p),**pin(p)),previous_ready_immutable=dict(path=str(B/'ready-finite.json'),**pin(B/'ready-finite.json')))
ready['license_supplement']=dict(path=str(D/'curation/metadata-license-supplement.json'),**pin(D/'curation/metadata-license-supplement.json'))
q=B/'ready-finite02.json';assert not q.exists();q.write_text(json.dumps(ready,indent=2)+'\n');print(json.dumps(dict(path=str(q),**pin(q),new_sidecars=len(added),files=len(files),bytes=ready['evidence_bytes'])))
