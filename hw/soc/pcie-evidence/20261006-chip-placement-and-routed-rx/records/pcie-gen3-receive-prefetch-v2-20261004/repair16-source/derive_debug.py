# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import ast,difflib,hashlib,json
B=Path(__file__).resolve().parents[1];S=Path(__file__).resolve().parent
pin=lambda p:dict(bytes=Path(p).stat().st_size,sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())
a=(B/'postroute_repair16_mixed.py').read_text();z=a.replace('postroute-repair-16-mixed-01','postroute-repair-16-debug-03').replace('RX16MIXED','RX16DEBUG03')
needle="lines += ['repair_timing -setup -sequence {clone sizeup buffer split}"
assert z.count(needle)==1;z=z.replace(needle,"lines += ['set_debug_level RSZ repair_setup 3', 'repair_timing -setup -sequence {clone sizeup buffer split}")
paths=[Path('/dev/shm/nssoc-rx-prefetch-v2-postroute-repair-16-mixed-01')/n for n in ('result.json','native.log')]
basis={str(p):pin(p) for p in paths};z=z.replace('inputs.update(MIXED_RC_BASIS)','inputs.update(MIXED_RC_BASIS)\nDEBUG_FAILURE_BASIS = '+repr(basis)+'\nassert DEBUG_FAILURE_BASIS == {p: pin(p) for p in DEBUG_FAILURE_BASIS}\ninputs.update(DEBUG_FAILURE_BASIS)')
for n in ('pin','interrupted','limits','identity','report','save'):
 get=lambda t:ast.dump(next(x for x in ast.parse(t).body if isinstance(x,ast.FunctionDef) and x.name==n),include_attributes=False)
 assert get(a)==get(z)
p=B/'postroute_repair16_debug03.py';assert not p.exists();p.write_text(z)
b=S/'source-bridge03-debug.json';b.write_text(json.dumps(dict(before=dict(path=str(B/'postroute_repair16_mixed.py'),**pin(B/'postroute_repair16_mixed.py')),after=dict(path=str(p),**pin(p)),opcodes=[dict(tag=t,before=a[i:j],after=z[k:l]) for t,i,j,k,l in difflib.SequenceMatcher(None,a,z,autojunk=False).get_opcodes()]),indent=2)+'\n')
f=dict(status='FROZEN_RX16_NATIVE_SIZEUP_DIAGNOSTIC_SOURCE',candidate=str(p),sources={str(q):pin(q) for q in [p,b,Path(__file__),B/'postroute_repair16_mixed.py',S/'source-only-peer-vco.json',*paths]},scope='Only added repair_setup debug3 tracing to failed native experiment, fresh root and exactfailurepins. Original setup sequence/margins4ns/IO/CPU8/2.5GiB unchanged. No changed DUT, no new acceptance. Diagnostic producer may fail at same native bug; retain actual log/returncode.')
(S/'source-freeze03-debug.json').write_text(json.dumps(f,indent=2)+'\n');print(json.dumps(f,indent=2))
