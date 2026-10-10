# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import hashlib,json,tarfile
F=Path(__file__).resolve().parent

def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
s=json.loads((F/'finite-snapshot01.json').read_text());q=F/'release-additive01.json';pub=json.loads(q.read_text());assert pub['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS';arc=s['additive_archive'];a=next(x for x in pub['assets']if x['name']==Path(arc['path']).name);assert {k:a[k]for k in ['bytes','sha256']}==pin(arc['path'])=={k:arc[k]for k in ['bytes','sha256']};assert a['authenticated_roundtrip']and a['anonymous_roundtrip']
seen={}
with tarfile.open(arc['path'],'r|xz')as t:
 for m in t:assert m.isfile();seen[m.name]=dict(bytes=m.size,sha256=hashlib.file_digest(t.extractfile(m),'sha256').hexdigest())
assert seen==json.loads(Path(arc['manifest']).read_text())
for field in ['method_allowlist','compact_evidence','original_evidence','public_receipts']:assert all(pin(p)==v for p,v in s[field].items())
s['archives'].append(dict(arc,manifest_pin=pin(arc['manifest']),public_receipt=str(q)));s['assets'].append(a);s['public_receipts'][str(q)]=pin(q)
s.update(status='READY_FINITE_SIXTEENTHSTEP_FUNCTIONAL_AND_NUMERICAL_PASS_PUBLIC',all_archive_members=sum(x['members']for x in s['archives']),snapshot=pin(F/'finite-snapshot01.json'),completion_method=pin(__file__),scope='Full34ns0.3125ps native455/all13PASS and separately predeclared adjacent100ppm/50ps numericalPASS. All104M values independently read; unchanged fixed absolute correspondence/nooffset phase metrics. Original5ps/2.5ps functionalFAIL and preceding269.85ppm numericalFAIL remain. Bounded streaming methods/control evidence included; no longer-duration/PLL/CDR/PVT/fullPHY qualification.')
assert len(s['archives'])==2 and s['archives'][-1]['members']==s['additive_archive']['members']
(F/'ready-finite01.json').write_text(json.dumps(s,indent=2)+'\n');print(pin(F/'ready-finite01.json'))
