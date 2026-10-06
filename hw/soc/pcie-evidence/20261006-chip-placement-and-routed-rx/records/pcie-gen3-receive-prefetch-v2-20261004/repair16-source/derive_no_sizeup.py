# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import ast,hashlib,json,difflib
B=Path(__file__).resolve().parents[1];S=Path(__file__).resolve().parent;D=Path('/dev/shm/nssoc-rx-prefetch-v2-postroute-repair-16-mixed-01')
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
r=json.loads((D/'result.json').read_text());assert r['status']=='FAILED_RETAINED' and r['returncode']==-11
assert r['inputs']=={p:pin(p) for p in r['inputs']};assert r['outputs']=={n:pin(D/n) for n in r['outputs']}
t=(D/'native.log').read_text();assert 'SizeUpGenerator::loadStageContext' in t and 'Signal 11 received' in t
assert 'worst slack max -0.402478' in (D/'reloaded-actual-worst.rpt').read_text()
a=(B/'postroute_repair16_mixed.py').read_text();z=a.replace('postroute-repair-16-mixed-01','postroute-repair-16-mixed-02').replace('RX16MIXED','RX16MIXED02').replace('{clone sizeup buffer split}','{clone buffer split}').replace('clone,sizeup,buffer,split','clone,buffer,split')
basis={str(p):pin(p) for p in [D/'result.json',D/'native.log',S/'source-only-peer-vco.json']}
z=z.replace('inputs.update(MIXED_RC_BASIS)','inputs.update(MIXED_RC_BASIS)\nSIZEUP_FAILURE_BASIS = '+repr(basis)+'\nassert SIZEUP_FAILURE_BASIS == {p: pin(p) for p in SIZEUP_FAILURE_BASIS}\ninputs.update(SIZEUP_FAILURE_BASIS)')
for n in ('pin','interrupted','limits','identity','report','save'):
 def fn(t):return ast.dump(next(x for x in ast.parse(t).body if isinstance(x,ast.FunctionDef) and x.name==n),include_attributes=False)
 assert fn(a)==fn(z)
p=B/'postroute_repair16_mixed02.py';assert not p.exists();p.write_text(z)
b=S/'source-bridge02.json';b.write_text(json.dumps(dict(before=dict(path=str(B/'postroute_repair16_mixed.py'),**pin(B/'postroute_repair16_mixed.py')),after=dict(path=str(p),**pin(p)),opcodes=[dict(tag=t,before=a[i:j],after=z[k:l]) for t,i,j,k,l in difflib.SequenceMatcher(None,a,z,autojunk=False).get_opcodes()],failure_scope='Native tool SIGSEGV in SizeUpGenerator after actual baseline restored; not a DUT failure. Omit only automatic sizeup move, same other moves/resources/4ns/hold constraints.'),indent=2)+'\n')
paths=[p,b,Path(__file__),B/'postroute_repair16_mixed.py',S/'source-freeze.json',*[Path(k) for k in basis]]
f=dict(status='FROZEN_RX16_MIXED_RC_WITHOUT_CRASHING_SIZEUP',candidate=str(p),sources={str(q):pin(q) for q in paths},scope='Original actualRX14A SPEF and exact−.402478 pre-repair gate. Sequence clone,buffer,split omits native crashing sizeup. Same setupmargin0.25/hold0.05/4ns/CPU8/2.5GiB/floors. Final freshGRT only; proof10faults6portsDRTactualRC still required.')
(S/'source-freeze02.json').write_text(json.dumps(f,indent=2)+'\n');print(json.dumps(f,indent=2))
