# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read-only independent exact-physics numerical halfstep source review."""
import ast,hashlib,json,sys,xml.etree.ElementTree as ET
from pathlib import Path
R=Path.cwd();B=Path(__file__).resolve().parent
sys.path[:0]=[str(B),str(R/'scripts')]
import characterize_halfstep01 as new
import characterize_pcie_vco_v6_divider_tail115_v1_wire_v1 as old

def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def exact(p,h):assert pin(p)=={k:h[k] for k in ('bytes','sha256')},str(p)
f=B/'source-freeze01.json';j=json.loads(f.read_text());assert len(j['pins'])==232 and len(j['new_sources'])==4
for p,h in j['pins'].items():exact(p,h)
for name in ['characterizer','launcher','sealer']:
 d=json.loads((B/(name+'-source-bridge01.json')).read_text())
 for key in ['parent','child']:exact(d[key]['path'],d[key])
 a=Path(d['parent']['path']).read_text();b=Path(d['child']['path']).read_text();expected=a
 for before,after in d['substitutions']:assert before in expected;expected=expected.replace(before,after)
 assert expected==b
 assert ''.join(x['before'] for x in d['opcodes'])==a and ''.join(x['after'] for x in d['opcodes'])==b
controls=json.loads((B/'derivative-controls01.json').read_text());assert controls['status']=='PASS_HALFSTEP_EXACT_RECIPE_DECK_AND_RESOURCE_CONTROLS' and len(controls['checks'])==7
for p,h in controls['source_pins'].items():exact(p,h)
exact(B/'recipes01.json',controls['recipes']);recipes=json.loads((B/'recipes01.json').read_text());assert len(recipes)==4
for r in recipes:
 a,ar,at=old.config(r['bias'],r['fault']);z,zr,zt=new.config(r['bias'],r['fault']);assert ar==zr==r['devices'] and len(ar)==455 and at==zt
 expected=dict(a,step_s=2.5e-12,sources=[str(B/'characterize_halfstep01.py') if p==old.__file__ else p for p in a['sources']]);assert z==expected and json.loads(json.dumps(z))==r['config']
 da=old.deck(a,ar,at);dz=new.deck(z,zr,zt);assert dz==da.replace('.tran 5e-12 3.4e-08 0 5e-12','.tran 2.5e-12 3.4e-08 0 2.5e-12') and hashlib.sha256(dz.encode()).hexdigest()==r['deck_sha256']
 assert a['window_s']==z['window_s']==[4e-9,34e-9]
for name in ['capture','measurement','native_limit']:
 a=old._scope[name];b=new._scope[name];assert a.__code__==b.__code__ and a.__defaults__==b.__defaults__ and a.__closure__==b.__closure__
assert new._scope['OWN_LIMIT']==128*1024**2 and old._scope['OWN_LIMIT']==80*1024**2
assert new.FLOOR==old.FLOOR==512*1024**2 and new.RECEIPT_RESERVE==old.RECEIPT_RESERVE==2*1024**2
parent=R/'hw/soc/out/pcie-vco-v6-divider-tail115-v1-wire-v1-20261006'
for name,count in [('source-controls01.xml',32),('handoff-controls01.xml',4)]:
 cases=ET.parse(parent/name).findall('.//testcase');assert len(cases)==count and all(not list(x) for x in cases)
runtime=json.loads((B/'launch-runtime-freeze01.json').read_text())
for p,h in runtime['pins'].items():exact(p,h)
assert not Path('/dev/shm/nssoc-vco-v6-divider-tail115-v1-halfstep-06-01').exists() and not (B/'launch-once.json').exists()
x=dict(status='PASS_SOURCE_ONLY_LOADED455_HALFSTEP_CONVERGENCE',freeze=pin(f),findings=[],method=pin(__file__),pins_rechecked=232,whole_source_bridges=3,independent_complete_recipe_and_deck_comparisons=4,saved_resource_controls=7,inherited_source_tests=32,inherited_handoff_tests=4,runtime=pin(B/'launch-runtime-freeze01.json'),scope='Exact455intrinsics1271R1414C and four physical recipes unchanged, complete34ns from0 and4–34ns criteria unchanged. Only output/maxstep5ps→2.5ps, new namespace, explicit128MiB cap and accurate raw estimate. Same Meter/capture/native lifecycle; prior5psFAIL preserved. This is source review, not a new analog result or acceptance.',physical_acceptance=False)
(B/'source-only-peer01-root.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps(x,indent=2))
