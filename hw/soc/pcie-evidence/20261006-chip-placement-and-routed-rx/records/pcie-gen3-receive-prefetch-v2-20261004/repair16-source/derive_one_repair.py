# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import ast,difflib,hashlib,json
B=Path(__file__).resolve().parents[1];S=Path(__file__).resolve().parent;D=Path('/dev/shm/nssoc-rx-prefetch-v2-postroute-repair-16-debug-03')
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
r=json.loads((D/'result.json').read_text());assert r['status']=='COMPLETE_CANDIDATE_REQUIRES_EQUIVALENCE_ROUTE_RC' and r['returncode']==0
assert r['inputs']=={p:pin(p) for p in r['inputs']};assert r['outputs']=={n:pin(D/n) for n in r['outputs']}
a=(B/'postroute_repair16_debug03.py').read_text();z=a.replace('postroute-repair-16-debug-03','postroute-repair-16-one-repair-04').replace('RX16DEBUG03','RX16ONE04').replace('-max_repairs_per_pass 4','-max_repairs_per_pass 1');assert a.count('-max_repairs_per_pass 4')==1
basis={str(p):pin(p) for p in [D/'result.json',D/'native.log',S/'debug03-rejection-review.json']};z=z.replace('inputs.update(DEBUG_FAILURE_BASIS)','inputs.update(DEBUG_FAILURE_BASIS)\nONE_REPAIR_BASIS = '+repr(basis)+'\nassert ONE_REPAIR_BASIS == {p: pin(p) for p in ONE_REPAIR_BASIS}\ninputs.update(ONE_REPAIR_BASIS)')
for n in ('pin','interrupted','limits','identity','report','save'):
 get=lambda t:ast.dump(next(x for x in ast.parse(t).body if isinstance(x,ast.FunctionDef) and x.name==n),include_attributes=False)
 assert get(a)==get(z)
p=B/'postroute_repair16_one04.py';assert not p.exists();p.write_text(z)
b=S/'source-bridge04.json';b.write_text(json.dumps(dict(before=dict(path=str(B/'postroute_repair16_debug03.py'),**pin(B/'postroute_repair16_debug03.py')),after=dict(path=str(p),**pin(p)),opcodes=[dict(tag=t,before=a[i:j],after=z[k:l]) for t,i,j,k,l in difflib.SequenceMatcher(None,a,z,autojunk=False).get_opcodes()]),indent=2)+'\n')
f=dict(status='FROZEN_RX16_ONE_REPAIR_PER_PASS_SOURCE',candidate=str(p),sources={str(q):pin(q) for q in [p,b,Path(__file__),B/'postroute_repair16_debug03.py',S/'source-freeze03-debug.json',S/'source-only-peer-vco.json',*[Path(k) for k in basis]]},scope='Only optimizer per-path repair budget4→1 to limit multiple edits on stale path context; cause not proven, no toolfix claim. Same actualSPEF/assert−.402478, setup.25/hold.05/4ns/sequence/debug3/resources. New output. FinalGRT only; actualproof/10faults/6ports/DRT/RC required if selected.')
(S/'source-freeze04.json').write_text(json.dumps(f,indent=2)+'\n');print(json.dumps(f,indent=2))
