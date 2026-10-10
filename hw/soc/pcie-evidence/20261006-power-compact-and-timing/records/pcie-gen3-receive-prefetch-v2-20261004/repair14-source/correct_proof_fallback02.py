# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Correct only early-failure receipt path before any native proof/port launch."""
from pathlib import Path
import difflib,hashlib,json
S=Path(__file__).resolve().parent;B=S.parent;D=S/'proof-source-candidate01'
pin=lambda p:dict(bytes=Path(p).stat().st_size,sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())
p=B/'replay_repair14a.py';a=p.read_text();assert pin(p)==pin(D/p.name)
old="'repair14a-source/port-prelaunch-failure.json'";new="'repair14-source/port-prelaunch-failure.json'";assert a.count(old)==1;p.write_text(a.replace(old,new))
bridge=json.loads((S/'proof-source-bridge.json').read_text())
for row in bridge:
 original=Path(row['before']['path']).read_text();updated=Path(row['after']['path']).read_text();row['after'].update(pin(row['after']['path']));ops=[];aa=original.splitlines(True);zz=updated.splitlines(True)
 for tag,i,j,k,l in difflib.SequenceMatcher(None,aa,zz,autojunk=False).get_opcodes():ops.append(dict(tag=tag,before=''.join(aa[i:j]),after=''.join(zz[k:l])))
 row['opcodes']=ops
(S/'proof-source-bridge02.json').write_text(json.dumps(bridge,indent=2)+'\n')
f=json.loads((S/'proof-source-freeze.json').read_text());f['files'][str(p)]=pin(p);f['bridge']=pin(S/'proof-source-bridge02.json');f['bridge_path']=str(S/'proof-source-bridge02.json');f['prior_freeze']=pin(D/'proof-source-freeze.json');f['correction_method']=pin(__file__);f['supplemental_correction']='Only fallback early-failure receipt uses real repair14-source directory; all old sources and original derivation retained. The original derivation method generated the prior candidate; additive correction is explicit.'
(S/'proof-source-freeze02.json').write_text(json.dumps(f,indent=2)+'\n')
(S/'proof-fallback-correction02.json').write_text(json.dumps(dict(prior=pin(D/p.name),current=pin(p),change=dict(before=old,after=new),full_inverse=p.read_text().replace(new,old)==a,initial_correction_preflight='Exact quoted directory-only predicate did not match actual full filepath; assertion failed before source mutation. Full filepath predicate used here.',scope='Only prelaunch-failure capture path; no native/data/constraints/test change.'),indent=2)+'\n')
for p in [p,S/'proof-source-bridge02.json',S/'proof-source-freeze02.json']:print(p.name,pin(p))
