# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import ast, hashlib, json
from pathlib import Path
B=Path(__file__).resolve().parent

def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
f=json.loads((B/'source-freeze.json').read_text())
assert pin(B/'source-freeze.json')==dict(bytes=309855,sha256='4578c0ae6e6c31f4ae14f9ae34bed15a7721ea8c1eff0543f1f9c72e5de590e3')
assert len(f['inputs'])==1357
for p,e in f['inputs'].items():assert pin(p)==e,p
bridge=json.loads((B/'source-bridge.json').read_text())
assert pin(bridge['parent'])==bridge['parent_pin'] and pin(bridge['new'])==bridge['new_pin']
a=Path(bridge['parent']).read_text();b=Path(bridge['new']).read_text()
inverse=b.replace('v8-cap-v1','v7-compact-v2').replace('V8_CAP24','V7')
assert inverse==a
assert ast.dump(ast.parse(inverse),include_attributes=False)==ast.dump(ast.parse(a),include_attributes=False)
g=json.loads((B.parent/'geometry-execution.json').read_text())
assert g['status']=='PASS_DIVIDER_V8_CAP24_SAVED_NATIVE_GEOMETRY_AND_SOURCE_BIJECTION_ONLY'
for p,e in g['outputs'].items():assert pin(p)==e,p
assert not (B/'result.json').exists()
assert not Path('/dev/shm/nssoc-div4-v8-cap-v1-binding-controls-01').exists()
r=dict(status='PASS_SOURCE_ONLY_DIVIDER_V8_CAP24_BINDING_CONTROLS',freeze=pin(B/'source-freeze.json'),findings=[],method=pin(__file__),producer=pin(B/'run.py'),bridge=pin(B/'source-bridge.json'),verified_inputs=1357,full_source_read=True,independent_full_body_inverse=True,geometry_execution=pin(B.parent/'geometry-execution.json'),scope='Full 8,608-byte source read. Only G/T roots, exact copied-source root literal and new geometry status change from reviewed CompactV2. Five cases preserve production binder except fixture root; exactly zero or one input edit, complete positive comparison, specific traceback assertions, no-result negative guards, full before/after pin checks. Exact seven owned execution/resource functions, same CPU10/2GiB/80MiB/reserve/floors/terminal guards. No producer, control, native or EDA executed; actual controls remain required. No physical mutation or electrical-fault claim.')
p=B/'source-only-peer-rx.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(path=str(p),**pin(p))))
