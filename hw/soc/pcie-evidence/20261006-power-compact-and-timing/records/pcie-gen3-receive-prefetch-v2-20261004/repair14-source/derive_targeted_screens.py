# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Add exactly targeted endpoint reports to two isolated fresh GRT screens."""
from pathlib import Path
import ast,hashlib,json
S=Path(__file__).resolve().parent;B=S.parent
pin=lambda p:dict(bytes=Path(p).stat().st_size,sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())
freeze=json.loads((S/'source-freeze.json').read_text());rows={}
for version in ['14a','14b']:
 old=B/f'postroute_repair{version}.py';before=old.read_text();assert pin(old)=={k:freeze['alternatives'][version]['candidate'][k] for k in ['bytes','sha256']}
 oldroot=f'/dev/shm/nssoc-rx-prefetch-v2-postroute-repair-{version}';newroot=oldroot+'-targeted-01';assert before.count(oldroot)==1
 after=before.replace(oldroot,newroot)
 needle=' return z\n'
 add=''' for endpoint in ('_26191_','_26187_','_26189_'):
  for c in ('slow','typical','fast'):
   for d in ('max','min'):
    z.extend([f'puts {tag}_TARGET_{endpoint}_{c}_{d}',f'report_checks -corner {c} -to [get_pins {endpoint}/D] -path_delay {d} -group_path_count 1 -fields {{slew cap fanout}} -digits 6'])
'''
 assert after.count(needle)==1;after=after.replace(needle,add+needle)
 assert after.replace(add,'').replace(newroot,oldroot)==before
 beforedefs={x.name:ast.dump(x) for x in ast.parse(before).body if isinstance(x,ast.FunctionDef)};afterdefs={x.name:ast.dump(x) for x in ast.parse(after).body if isinstance(x,ast.FunctionDef)}
 assert [n for n in beforedefs if beforedefs[n]!=afterdefs[n]]==['report']
 new=B/f'postroute_repair{version}_targeted01.py';assert not new.exists();new.write_text(after)
 rows[version]=dict(before=dict(path=str(old),**pin(old)),after=dict(path=str(new),**pin(new)),whole_source_substitutions=[dict(before=oldroot,after=newroot),dict(before=needle,after=add+needle)],unchanged_functions=[n for n in beforedefs if n!='report'],new_output=newroot)
r=dict(status='SOURCE_ONLY_TARGETED_REPORT_ADDITION_TO_FROZEN_RX14_SCREENS',method=pin(__file__),base_freeze=pin(S/'source-freeze.json'),base_peer=pin(S/'source-only-peer-root.json'),variants=rows,reason='Closed original GRT global worst path is unchanged endpoint25721, which hides changed actual-RC critical endpoints26191/26187/26189. Add18 endpoint checks to each before/after report; otherwise same exact native candidate recipe. This bounded fresh GRT run resolves the unmeasured alternative ranking; no proof/DRT/nativegold rerun.',constraints_unchanged=True,physical_acceptance=False)
p=S/'targeted-source-freeze.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n');print(pin(p))
