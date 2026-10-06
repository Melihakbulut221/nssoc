# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import ast,hashlib,json
B=Path(__file__).resolve().parent
pin=lambda p:dict(bytes=Path(p).stat().st_size,sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())
fpath=B/'source-freeze.json';f=json.loads(fpath.read_text());assert pin(fpath)==dict(bytes=2466,sha256='aef947a4e3cac31debcef65b1c4a58d8f2a7b6cf87e6ac58fc8ee7dea026f0ce');assert f['inputs']=={p:pin(p)for p in f['inputs']}
b=json.loads((B/'source-bridge.json').read_text());a=Path(b['parent']).read_text();z=Path(b['candidate']).read_text();forward=a
for row in b['substitutions']:
 assert forward.count(row['before'])==row['count'];forward=forward.replace(row['before'],row['after'])
assert forward==z
reverse=z
for row in reversed(b['substitutions']):
 assert reverse.count(row['after'])==row['count'];reverse=reverse.replace(row['after'],row['before'])
assert reverse==a
fun=lambda s:{n.name:ast.dump(n,include_attributes=False)for n in ast.parse(s).body if isinstance(n,ast.FunctionDef)}
assert fun(a)==fun(z)
anchors={}
for d in map(Path,('/dev/shm/nssoc-tx-path-v4-repair03-drt-01','/dev/shm/nssoc-tx-path-v4-repair03-detailed-rc-01')):
 j=json.loads((d/'result.json').read_text());assert j['status'].startswith('COMPLETE_')and j['returncode']==0
 for p,q in j['inputs'].items():assert pin(p)==q;anchors[p]=q
 for p,q in j['outputs'].items():assert pin(d/p)==q;anchors[str(d/p)]=q
assert z.count('read_spef -corner')==2
assert z.index('EXACT_ACTUAL_BASELINE_RC_RESTORED_BEFORE_REPAIR')<z.index("lines += ['repair_timing -setup")
assert 'worst slack max -0.601762'in z and '-setup_margin 0.25'in z and '-hold_margin 0.05'in z
rx=Path(b['final_grt_source']).read_text();start=lambda s:s[s.index("          f'global_route -end_incremental"):s.index("lines += report(",s.index("          f'global_route -end_incremental"))]
assert start(rx).replace('RX15V3','TX05')==start(z)
assert not Path('/dev/shm/nssoc-tx-path-v4-postroute-repair-05').exists()
r=dict(status='PASS_SOURCE_ONLY_TX05_ACTUAL_SPEF_FIRST_REPAIR',freeze=pin(fpath),findings=[],method=pin(__file__),candidate=pin(b['candidate']),all_function_ASTs_exact=True,whole_source_inverse=True,verified_freeze_inputs=len(f['inputs']),closed_baseline_rehash_count=len(anchors),final_full_GRT_source_exact=True,scope='Initialized complete GRT context then reloads exact originalTX03 SPEF all3corners; native6digit WNS must reproduce−.601762 before setup. Same4ns/IO constraints, .25setup/.05hold margins and CPU4/2.5GiB/lifecycle. All later modified-net parasitics explicitly mixed estimates, final fullGRT only. Exact finalnetlist/no missing-route checks. No native or reviewed producer executed by peer.',native_result_check='Inspect optimizer firstiteration WNS as well as pre-call exactreport: source alone cannot guarantee resizer does not refresh parasitics on entry. Prior originalTX04 initial detailedplacement measured0.0um total/max displacement. Fresh proof/faults/3ports/DRT/actualRC required before acceptedtiming.')
(B/'source-only-peer-rx.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
