# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Root readback of closed V24 rejected timing and exact finite evidence."""
import hashlib,json,tarfile
from pathlib import Path
R=Path.cwd();O=Path(__file__).resolve().parent;B=R/'hw/soc/out/pcie-integrity-v24-20261006';P=B/'ready-finite.json'
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def exact(p,h):assert pin(p)=={k:h[k] for k in ('bytes','sha256')},str(p)
j=json.loads(P.read_text());assert len(j['source_allowlist'])==10 and len(j['evidence'])==177 and len(j['archives'])==4 and j['archive_total_members']==877
for col in ['source_allowlist','evidence']:
 for p,h in j[col].items():exact(R/p,h)
archives=[];total=0
for name,a in j['archives'].items():
 exact(a['path'],a);seen={};members=None
 with tarfile.open(a['path'],'r|xz') as tf:
  for f in tf:
   assert f.isfile() and f.name not in seen
   if f.name=='members.json':
    data=tf.extractfile(f).read();seen[f.name]=dict(bytes=f.size,sha256=hashlib.sha256(data).hexdigest());members=json.loads(data)
   else:seen[f.name]=dict(bytes=f.size,sha256=hashlib.file_digest(tf.extractfile(f),'sha256').hexdigest())
 assert len(seen)==a['member_count'] and members is not None
 assert set(seen)-{'members.json'}==set(members)
 for key,h in members.items():assert seen[key]=={k:h[k]for k in ('bytes','sha256')}
 total+=len(seen);archives.append(dict(a,members=len(seen)))
assert total==877
assert len(j['assets'])==5 and all(x['authenticated_roundtrip'] and x['anonymous_roundtrip'] for x in j['assets'])
for a in j['assets']:
 path=B/a['name'];exact(path,a)
for p,h in j['releases'].items():exact(B/p,h);assert json.loads((B/p).read_text())['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS'
assert not j['adopted'] and not j['physical_acceptance'] and j['native']['setup_ns']==dict(slow=-3.634856,typical=-.827638,fast=.823255)
assert j['controls']['pytest_executions']==44 and j['controls']['passed_executions']==43 and j['controls']['historical_failed_executions']==1
x=dict(status='PASS_ROOT_V24_877_COMPLETE_MEMBERS_REJECTED_TIMING_RETAINED',ready=pin(P),sources=j['source_allowlist'],compact=j['evidence'],archives=archives,public_assets=j['assets'],members=total,findings=[],method=pin(__file__),native=j['native'],controls=j['controls'],scope='Ten source and177currentevidence pins, all877fullmembers and five dualreadbackassets verified. Historicaloriginchanges explicitlybound in prior peer supplement; no claimof44cleanPASS. SS/TT stillnegative; V24notadopted, stableV11 unchanged.',physical_acceptance=False)
(O/'v24-review01.json').write_text(json.dumps(x,indent=2)+'\n');print(dict(status=x['status'],sources=10,compact=177,members=total,assets=5))
