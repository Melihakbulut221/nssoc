from pathlib import Path
import ast,hashlib,json,difflib
R=Path.cwd();B=Path(__file__).resolve().parent;F=B/'source-freeze04.json'
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
j=json.loads(F.read_text());assert j['sources']=={p:pin(p) for p in j['sources']}
br=json.loads((B/'source-bridge04.json').read_text());a=Path(br['before']['path']).read_text();b=Path(br['after']['path']).read_text();assert ''.join(o['before'] for o in br['opcodes'])==a and ''.join(o['after'] for o in br['opcodes'])==b
old=B.parent/'postroute_repair16_mixed.py';base=old.read_text();ta,tb=ast.parse(base),ast.parse(b)
func=lambda t:{n.name:ast.dump(n,include_attributes=False) for n in t.body if isinstance(n,ast.FunctionDef)};assert func(ta)==func(tb)
# Reconstruct exact approved first source from current by removing only pinned history blocks,
# observational debug, fresh labels/root and per-pass budget change.
x=b
for label in ['DEBUG_FAILURE_BASIS','ONE_REPAIR_BASIS']:
 nodes=[n for n in ast.parse(x).body if (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==label for t in n.targets)) or (isinstance(n,ast.Assert) and label in ast.unparse(n)) or (isinstance(n,ast.Expr) and ast.unparse(n)==f'inputs.update({label})')];assert len(nodes)==3
 lines=x.splitlines(True)
 for n in sorted(nodes,key=lambda n:n.lineno,reverse=True):del lines[n.lineno-1:n.end_lineno]
 x=''.join(lines)
x=x.replace('nssoc-rx-prefetch-v2-postroute-repair-16-one-repair-04','nssoc-rx-prefetch-v2-postroute-repair-16-mixed-01').replace('RX16ONE04','RX16MIXED').replace("'set_debug_level RSZ repair_setup 3', ",'').replace('-max_repairs_per_pass 1','-max_repairs_per_pass 4');assert x==base
basis={}
for n in tb.body:
 if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id.endswith('_BASIS'):
  v=ast.literal_eval(n.value);assert v=={p:pin(p) for p in v};basis.update(v)
# Rehash exact original completed DRT/RC baseline maps; no EDA/model execution.
basepins={}
for name in ['nssoc-rx-prefetch-v2-repair14a-drt-01','nssoc-rx-prefetch-v2-repair14a-detailed-rc-01']:
 d=Path('/dev/shm')/name;r=json.loads((d/'result.json').read_text());assert r['status'].startswith('COMPLETE_') and r['returncode']==0
 for p,v in r['inputs'].items():assert pin(p)==v;basepins[p]=v
 for p,v in r['outputs'].items():assert pin(d/p)==v;basepins[str(d/p)]=v
r=dict(status='PASS_SOURCE_ONLY_RX16_MIXED_RC_CANDIDATE',freeze=pin(F),findings=[],sources=j['sources'],method=pin(__file__),entire_bridge_forward_inverse=True,independent_inverse_to_approved_original=pin(old),unchanged_functions=list(func(tb)),baseline_rehashed_files=len(basepins),history_basis_rehashed=len(basis),review=['Only proposed optimization change against debug03 is max_repairs_per_pass4to1; source baselines and fresh output labels retained. Compared directly with fully reviewed original mixed01, all other changes are pinned prior-run evidence plus observational debug3.','Full clone/sizeup/buffer/split sequence, actual threecorner baseline SPEF reload and exact minus0.402478 guard, setup0.25/hold0.05 and original4ns constraints intact.','Exact inherited birth/group/signal-mask handoff,1GiB entry and528MiB continuous+terminal floor,2.5GiB AS/CPU8, no healthy timeout, only still-live identity checked cleanup intact.','Final fullGRT clears copied signal wires/guides only and requires equal logical netlist plus no missing-route/restoration warning. Estimates never qualify actualRC or physical closure.','Prior debug03 completed but final estimate worsened; first mixed01 SIGSEGV preserved. Changing repair budget is a bounded experiment, not a proven engine crash fix.'],native_or_reviewed_method_executed=False)
(B/'source-only-peer04-vco.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],pin(B/'source-only-peer04-vco.json'))
