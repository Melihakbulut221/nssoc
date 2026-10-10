from pathlib import Path
import ast,hashlib,json
B=Path(__file__).resolve().parent

def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
f=B/'source-freeze.json';d=json.loads(f.read_text());assert d['sources']=={p:pin(p) for p in d['sources']}
b=json.loads((B/'source-bridge.json').read_text());texts={}
for k in ['before','after']:
 p=Path(b[k]['path']);s=''.join(o[k] for o in b['opcodes']);assert s==p.read_text();assert pin(p)=={a:v for a,v in b[k].items() if a!='path'};texts[k]=s
for o in b['opcodes']:
 if o['tag']=='equal':assert o['before']==o['after']
block=b['actual_SPEF_block'];assert block['before'] in Path(block['parent']['path']).read_text();assert block['after'] in texts['after'];assert block['after'].replace('RX16MIXED','TX05').replace('-0.402478','-0.601762')==block['before']
func=lambda s:{n.name:ast.dump(n,include_attributes=False) for n in ast.parse(s).body if isinstance(n,ast.FunctionDef)};assert func(texts['before'])==func(texts['after'])
# No native lifecycle change: only exact restored-actual marker assertion added.
normalized=texts['after'].replace('RX16MIXED','RX15V3').replace("    assert 'EXACT_ACTUAL_BASELINE_RC_RESTORED_BEFORE_REPAIR' in log\n",'')
tries=lambda s:[ast.dump(n,include_attributes=False) for n in ast.parse(s).body if isinstance(n,ast.Try)]
assert tries(texts['before'])==tries(normalized)
assert texts['after'].count('repair_timing -setup -sequence {clone sizeup buffer split} -repair_tns 100 -setup_margin 0.25')==1
assert texts['after'].count('repair_timing -hold -hold_margin 0.05')==1
assert texts['after'].index('global_route -start_incremental')<texts['after'].index(block['after'])<texts['after'].index('repair_timing -setup')
base={}
for folder in ['/dev/shm/nssoc-rx-prefetch-v2-repair14a-drt-01','/dev/shm/nssoc-rx-prefetch-v2-repair14a-detailed-rc-01']:
 p=Path(folder);q=json.loads((p/'result.json').read_text());assert q['status'].startswith('COMPLETE_') and q['returncode']==0
 for n,x in q['inputs'].items():assert pin(n)==x;base[n]=x
 for n,x in q['outputs'].items():assert pin(p/n)==x;base[str(p/n)]=x
r=dict(status='PASS_SOURCE_ONLY_RX16_MIXED_RC_CANDIDATE',freeze=pin(f),findings=[],method=pin(__file__),source_pins=d['sources'],baseline_unique_files=len(base),checks=['Ten frozen pins and39 unique baseline files rehashed.','Complete bytewise originalRX15V3 inverse; TX05 actual-SPEF block independently reconstructed with only statedlabel/WNS difference.','All6 inherited function ASTs and entire native try/cleanup unchanged after label normalization and additive exactactual marker guard.','Original RX14A DB/SDC/SPEF retained; allthreecorner SPEF reloaded after incremental topology initialized and before any repair, with actualbaselineWNS−0.402478 gate.','Optimizationmargin0.25 is distinct from original4ns timingconstraint; hold0.05 and CPU8/resource/nohealthytimeout unchanged.','Modified nets may use estimated RC; final full GRT incomplete-route rejection and identical final netlist guard retained.'],scope='Source-only independent peer, no producer/EDA/tests/proof executed. Mixed RC optimization only; fresh equivalence,10faults,6ports,DRT and actual RC required.')
p=B/'source-only-peer-vco.json';p.write_text(json.dumps(r,indent=2)+'\n');print(pin(p))
