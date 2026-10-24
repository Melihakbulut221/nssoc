# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent source-only builder change restricted to input pins/top names."""
import ast,hashlib,json
from pathlib import Path
B=Path(__file__).resolve().parent;R=Path.cwd()
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def exact(p,h):assert pin(p)=={k:h[k] for k in ('bytes','sha256')},str(p)
f=B/'builder-source-freeze.json';j=json.loads(f.read_text());exact(j['method']['path'],j['method'])
for p,h in j['inputs'].items():exact(p,h)
br=json.loads((B/'builder-source-bridge.json').read_text())
for k in ['before','after']:
 exact(br[k]['path'],br[k]);assert ''.join(x[k] for x in br['opcodes'])==Path(br[k]['path']).read_text()
a=Path(br['before']['path']).read_text();b=Path(br['after']['path']).read_text()
def pins(text):
 return next(ast.literal_eval(n.value) for n in ast.parse(text).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PINS' for t in n.targets))
x,y=pins(a),pins(b);assert x.keys()==y.keys()==j['native_input_files'].keys() and len(x)==5
for k,p in j['native_input_files'].items():assert pin(p)['sha256']==y[k]
for k in x:assert a.count(x[k])==1;a=a.replace(x[k],y[k])
old='nssoc_clock_div4_v9_bias8_v1_hybrid_open_v1';new='nssoc_clock_div4_v10_tail115_v1_hybrid_open_v1';assert a.count(old)==2;a=a.replace(old,new);assert a==b
assert j['body_and_wire_reference_distinct'] and j['models_and_exact_conversion_logic_unchanged'] and not j['generated_model'] and j['independent_saved_rc_peer_required_before_generation']
assert [j[k] for k in ['source_devices','contacts','body_terminals','anchors','wire_resistors','wire_capacitors']]==[91,18,85,205,382,649]
result=dict(status='PASS_SOURCE_ONLY_TAIL115_V1_DIVIDER_HYBRID_BUILDER',freeze=pin(f),findings=[],method=pin(__file__),inputs_checked=len(j['inputs']),exact_changes='Five actual native input hashes and two top subcircuit names only; every conversion/model/body-boundary byte otherwise unchanged.',scope='Source review only. Independent saved RC peer remains mandatory before composition. Model is an explicitly open substrate/wire-reference pilot; no qualified PEX, loaded waveform or PHY acceptance.',full_phy_acceptance=False)
(B/'builder-source-only-peer-root.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
