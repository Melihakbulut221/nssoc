# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import hashlib,json,tarfile
F=Path(__file__).resolve().parent
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
s=json.loads((F/'finite-snapshot01.json').read_text());q=F/'release01.json';pub=json.loads(q.read_text());assert pub['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS'and len(pub['assets'])==1
arc=s['archives'][0];a=pub['assets'][0];assert a['name']==Path(arc['path']).name and {k:a[k]for k in ['bytes','sha256']}==pin(arc['path'])=={k:arc[k]for k in ['bytes','sha256']};assert a['authenticated_roundtrip']and a['anonymous_roundtrip']
seen={}
with tarfile.open(arc['path'],'r|xz')as t:
 for m in t:
  assert m.isfile()and m.name not in seen
  seen[m.name]=dict(bytes=m.size,sha256=hashlib.file_digest(t.extractfile(m),'sha256').hexdigest())
assert seen==json.loads(Path(arc['manifest']).read_text())and len(seen)==arc['members']
for field in ['method_allowlist','compact_evidence','original_evidence']:assert all(pin(p)==v for p,v in s[field].items())
s['assets']=[a];s['public_receipts']={str(q):pin(q)};s['archives'][0]['public_receipt']=str(q)
s.update(status='READY_FINITE570_SOURCE_AND_CONTROL_EVIDENCE_PUBLIC',all_archive_members=len(seen),snapshot=pin(F/'finite-snapshot01.json'),completion_method=pin(__file__),scope=s['scope'])
assert not(F/'ready-finite01.json').exists();(F/'ready-finite01.json').write_text(json.dumps(s,indent=2)+'\n');print(pin(F/'ready-finite01.json'))
