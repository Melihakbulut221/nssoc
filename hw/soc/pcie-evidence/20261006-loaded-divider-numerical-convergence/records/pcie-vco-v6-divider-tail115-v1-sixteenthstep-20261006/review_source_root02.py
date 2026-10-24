# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent full-source and saved-test review before fresh .3125ps native."""
import ast,hashlib,json,sys,xml.etree.ElementTree as ET
from pathlib import Path
R=Path.cwd();B=Path(__file__).resolve().parent;E=B.parent/'pcie-vco-v6-divider-tail115-v1-eighthstep-20261006';S=B.parent/'pcie-tail115-streaming-replay-v1-20261006'
sys.path[:0]=[str(B),str(E),str(R/'scripts')]
import characterize_sixteenthstep01 as new
import characterize_eighthstep01 as old

def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def exact(p,h):assert pin(p)=={k:h[k]for k in('bytes','sha256')},str(p)
f=B/'source-freeze01.json';j=json.loads(f.read_text());assert len(j['pins'])==842 and len(j['new_sources'])==5
for p,h in j['pins'].items():exact(p,h)
for name in ['characterize_sixteenthstep01.py','launch_probe01.py','seal_probe01.py','compare_saved_steps01.py']:
 d=json.loads((B/(name+'.source-bridge.json')).read_text())
 for key in ['parent','child']:exact(d[key]['path'],d[key])
 a=Path(d['parent']['path']).read_text();b=Path(d['child']['path']).read_text()
 assert ''.join(x['before']for x in d['opcodes'])==a and ''.join(x['after']for x in d['opcodes'])==b
# Characterizer changes are fully enumerated, not a sampling of declarations.
a=Path(old.__file__).read_text();b=Path(new.__file__).read_text()
expected=a.replace('512 * 1024**2','1024 * 1024**2').replace('c["step_s"] = 6.25e-13','c["step_s"] = 3.125e-13').replace('nssoc-vco-v6-divider-tail115-v1-eighthstep-*','nssoc-vco-v6-divider-tail115-v1-sixteenthstep-*').replace('Own512MiB','Own1024MiB')
assert expected==b
controls=json.loads((B/'derivative-controls01.json').read_text());assert controls['status']=='PASS_SIXTEENTHSTEP_EXACT_RECIPE_DECK_AND_RESOURCE_CONTROLS'and len(controls['checks'])==7
for p,h in controls['source_pins'].items():exact(p,h)
exact(B/'recipes01.json',controls['recipes']);recipes=json.loads((B/'recipes01.json').read_text());assert len(recipes)==4
for r in recipes:
 a,ar,at=old.config(r['bias'],r['fault']);z,zr,zt=new.config(r['bias'],r['fault']);assert ar==zr==r['devices']and len(ar)==455 and at==zt
 expected=dict(a,step_s=3.125e-13,sources=[str(B/'characterize_sixteenthstep01.py')if p==old.__file__ else p for p in a['sources']]);assert z==expected and json.loads(json.dumps(z))==r['config']
 da=old.deck(a,ar,at);dz=new.deck(z,zr,zt);assert dz==da.replace('.tran 6.25e-13 3.4e-08 0 6.25e-13','.tran 3.125e-13 3.4e-08 0 3.125e-13')and hashlib.sha256(dz.encode()).hexdigest()==r['deck_sha256']
 assert a['window_s']==z['window_s']==[4e-9,34e-9]
for name in ['capture','measurement','native_limit']:
 a=old._scope[name];b=new._scope[name];assert a.__code__==b.__code__ and a.__defaults__==b.__defaults__ and a.__closure__==b.__closure__
assert new._scope['OWN_LIMIT']==1024*1024**2 and old._scope['OWN_LIMIT']==512*1024**2
assert new.FLOOR==old.FLOOR==512*1024**2 and new.RECEIPT_RESERVE==old.RECEIPT_RESERVE==2*1024**2
sf=json.loads((S/'source-freeze01.json').read_text());sp=json.loads((S/'source-only-peer-pll01.json').read_text());assert sp['status']=='PASS_SOURCE_ONLY_BOUNDED_SAVED_RAW_MEMMAP_READER'and sp['findings']==[]and sp['freeze']==pin(S/'source-freeze01.json')
for p,h in sf['pins'].items():exact(p,h)
sc=json.loads((S/'controls01.json').read_text());assert sc['status']=='PASS_SAVED_STREAMING_READER_EQUIVALENCE_AND_CORRUPTION_CONTROLS'and len(sc['checks'])==20
saved=json.loads((B/'saved-replay-controls01.json').read_text());assert saved['status']=='PASS_EXACT_STREAMED_COMPARISON_AND_SEALER_SAVED_AST_CONTROLS'and len(saved['checks'])==2 and saved['peak_rss_kib']==456512
for p,h in saved['inputs'].items():exact(p,h)
t=ast.parse((B/'compare_saved_steps01.py').read_text());loop=next(n for n in t.body if isinstance(n,ast.For)and isinstance(n.target,ast.Tuple)and [x.id for x in n.target.elts]==['root','step']);assert hashlib.sha256(ast.dump(loop,include_attributes=False).encode()).hexdigest()==saved['production_loop_ast_sha256']
t=ast.parse((B/'seal_probe01.py').read_text());block=next(n for n in t.body if isinstance(n,ast.With)and isinstance(n.items[0].context_expr,ast.Call)and isinstance(n.items[0].context_expr.func,ast.Name)and n.items[0].context_expr.func.id=='open_table');assert hashlib.sha256(ast.dump(block,include_attributes=False).encode()).hexdigest()==saved['production_sealer_context_ast_sha256']
assert (B/'convergence_policy01.py').read_bytes()==(E/'convergence_policy01.py').read_bytes()
p=json.loads((B/'numerical-policy01.json').read_text());assert p['reference_step_s']==6.25e-13 and p['candidate_step_s']==3.125e-13 and p['frequency_limit_ppm']==100 and p['phase_limit_ps']==50 and p['first_cml_global_vco']==31 and p['feedback_global_vco']==[86,166,246]and p['vco_before_window']==30
n=json.loads((B/'numerical-controls01.json').read_text());assert len(n['checks'])==12 and n['status']=='PASS_ACTUAL_ADDITIONAL_NUMERICAL_GATE_CONTROLS'
for p,h in n['inputs'].items():exact(p,h)
parent=R/'hw/soc/out/pcie-vco-v6-divider-tail115-v1-wire-v1-20261006'
for name,count in [('source-controls01.xml',32),('handoff-controls01.xml',4)]:
 cases=ET.parse(parent/name).findall('.//testcase');assert len(cases)==count and all(not list(x)for x in cases)
runtime=json.loads((B/'launch-runtime-freeze01.json').read_text())
for p,h in runtime['pins'].items():exact(p,h)
assert not Path('/dev/shm/nssoc-vco-v6-divider-tail115-v1-sixteenthstep-06-01').exists()and not(B/'launch-once.json').exists()
x=dict(status='PASS_SOURCE_ONLY_LOADED455_SIXTEENTHSTEP_CONVERGENCE',freeze=pin(f),findings=[],method=pin(__file__),pins_rechecked=842,whole_source_bridges=4,complete_recipe_deck_comparisons=4,saved_resource_controls=7,reader_controls=20,saved_full_record_comparison=4,saved_full_eighth455_sealer_replay=True,saved_numerical_controls=12,reader_peer=pin(S/'source-only-peer-pll01.json'),saved_replay=pin(B/'saved-replay-controls01.json'),scope='Same455devices1271R1414C/full34ns/windows/safety/strictfunctional gates. Nativecap1GiB, same2GiBAS/shared512MiB; streamed savedreader1GiBSSDpayload plus1GiBfloor. Fullfourrecord and455sealer AST replay exact at456512KiB. Fixed31+4k CMLanchor and original100ppm/50ps nooffset policy unchanged, adjacent0.625/.3125 pair declared before native. Previous numericalFAIL retained; no new result or PHY acceptance.',physical_acceptance=False)
(B/'source-only-peer01-root.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps(x,indent=2))
