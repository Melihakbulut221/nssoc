# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent exact converter inverse; no model composition or native work."""
from pathlib import Path
import ast,hashlib,json
B=Path(__file__).absolute().parent

def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def load(p):return json.loads(Path(p).read_text())
f=load(B/'builder-source-freeze.json');bridge=load(B/'builder-source-bridge.json')
for p,h in f['inputs'].items():assert pin(p)==h,p
old=Path(bridge['before']['path']).read_text();new=Path(bridge['after']['path']).read_text()
for key in ['before','after']:assert pin(bridge[key]['path'])=={k:bridge[key][k] for k in ['bytes','sha256']}
assert ''.join(o['before'] for o in bridge['opcodes'])==old and ''.join(o['after'] for o in bridge['opcodes'])==new
getpins=lambda s:ast.literal_eval(next(n.value for n in ast.parse(s).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PINS' for t in n.targets)))
a,b=getpins(old),getpins(new);assert set(a)==set(b)==set(f['native_input_files'])
transformed=old
for n,p in f['native_input_files'].items():
 assert pin(p)['sha256']==b[n]
 assert old.count(a[n])==new.count(b[n])==1
 transformed=transformed.replace(a[n],b[n])
assert transformed.count('nssoc_clock_div4_v8_cap24_v1_hybrid_open_v1')==2
transformed=transformed.replace('nssoc_clock_div4_v8_cap24_v1_hybrid_open_v1','nssoc_clock_div4_v9_bias8_v1_hybrid_open_v1')
assert transformed==new
assert f['independent_saved_rc_peer_required_before_generation'] and not f['generated_model']
assert (f['source_devices'],f['body_terminals'],f['anchors'],f['wire_resistors'],f['wire_capacitors'])==(91,85,205,382,649)
r=dict(status='PASS_SOURCE_ONLY_BIAS8_V1_DIVIDER_HYBRID_BUILDER',freeze=pin(B/'builder-source-freeze.json'),findings=[],method=pin(__file__),inputs_rehashed=len(f['inputs']),full_byte_inverse=True,only_changed_input_pins=b,only_changed_top_name='nssoc_clock_div4_v9_bias8_v1_hybrid_open_v1',scope='Exact complete published Cap24 converter with five actual input hashes and two matching subckt/ends names replaced. All conversion/body/contact/RC logic unchanged. Independent saved RC peer still required before composition; no generation or native acceptance.')
p=B/'builder-source-only-peer-root.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n');print(pin(p))
