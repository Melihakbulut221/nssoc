# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent finite Tail115 full archive and exact source/record readback."""
import hashlib,json,tarfile
from pathlib import Path
R=Path.cwd();B=Path(__file__).resolve().parent
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def exact(p,h):assert pin(p)=={k:h[k] for k in ('bytes','sha256')},str(p)
results=[]
for label,count,expected in [('halfstep',47,277),('quarterstep',58,310)]:
 F=R/('hw/soc/out/pcie-tail115-'+label+'-finite-20261006');P=F/'ready-finite01.json'
 j=json.loads(P.read_text());assert len(j['sources'])==0 and len(j['compact_evidence'])==count and j['all_archive_members']==expected
 for col in ('sources','compact_evidence','original_evidence','public_receipts'):
  for p,h in j[col].items():exact(p,h)
 assert len(j['archives'])==len(j['assets'])==2;total=0
 for a in j['archives']:
  exact(a['path'],a);exact(a['manifest'],a['manifest_pin']);m=json.loads(Path(a['manifest']).read_text());members=m.get('members',m);seen={}
  with tarfile.open(a['path'],'r|xz') as tf:
   for f in tf:
    assert f.isfile() and f.name not in seen
    h=dict(bytes=f.size,sha256=hashlib.file_digest(tf.extractfile(f),'sha256').hexdigest());assert h=={k:members[f.name][k] for k in ('bytes','sha256')};seen[f.name]=h
  assert seen.keys()==members.keys() and len(seen)==a['members'];total+=len(seen)
  q=json.loads(Path(a['public_receipt']).read_text());assert q['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS';asset=next(x for x in q['assets'] if x['name']==Path(a['path']).name);assert asset['authenticated_roundtrip'] and asset['anonymous_roundtrip'];exact(a['path'],asset)
 assert total==expected
 for p,h in j['method_allowlist'].items():exact(p,h)
 results.append(dict(label=label,ready=dict(path=str(P),**pin(P)),archives=j['archives'],assets=j['assets'],members=total,compact=count,methods=j['method_allowlist']))
x=dict(status='PASS_ROOT_HALF_AND_QUARTER_FINITE587MEMBERS',captures=results,members=sum(x['members']for x in results),findings=[],method=pin(__file__),original_verdicts=['FAIL','PASS'],numerical_convergence=False)
(B/'numerical-finite-review01.json').write_text(json.dumps(x,indent=2)+'\n');print(dict(status=x['status'],members=x['members']))
