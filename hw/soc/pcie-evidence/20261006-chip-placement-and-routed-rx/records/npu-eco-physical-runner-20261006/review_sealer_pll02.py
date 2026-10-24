"""Independent source-only comparison, no producer/native/sealer execution."""
from pathlib import Path
import ast,hashlib,json
B=Path(__file__).resolve().parent;R=B.parents[3]
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
p=B/'seal_pair02.py';s=p.read_text();ast.parse(s)
old="assert peer['status'].startswith('PASS') and not peer.get('findings')\n"
new="""assert peer['status'] == 'PASS_INDEPENDENT_SAVED_NPU_TEMPLATE_CONTROL06' and peer['findings'] == []
assert peer['control'] == state['native_template_control'] == pin(B / 'template-control06/control.json')
assert peer['freeze'] == pin(B / 'source-freeze06.json')
assert peer['source_peer'] == pin(B / 'source-only-peer-pll06.json')
for variant in ('original', 'factored'):
    assert state['completed'][variant]['result'] == pin(B / ('pair02-' + variant) / 'result.json')
    assert state['completed'][variant]['status'] == 'FRESH_NPU_PHYSICAL_COMPLETE_ESTIMATE_ONLY'
assert state['comparison'] == pin(B / 'pair02-comparison.json')
"""
assert s.count(new)==1
prior=s.replace(new,old);finding=json.loads((B/'sealer-source-peer-pll01-findings.json').read_text())
assert dict(bytes=len(prior.encode()),sha256=hashlib.sha256(prior.encode()).hexdigest())==finding['method']
q=B/'sealer-source01-reconstructed-exact.py';assert not q.exists();q.write_text(prior)
freeze=json.loads((B/'source-freeze06.json').read_text());runner=R/'scripts/run_npu_eco_physical.py';assert pin(runner)==freeze['sources'][str(runner)]
# Literal complete reviewed body retained. The sealer only calls compare(), which
# rechecks terminal arm status, all raw metrics/geometry/readiness and sources.
tree=ast.parse(runner.read_text());compare=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='compare')
body=ast.get_source_segment(runner.read_text(),compare)
for expected in ['FRESH_NPU_PHYSICAL_COMPLETE_ESTIMATE_ONLY','readiness.check(','verify_saved_geometry(','physical.audit_check(','Unmatched physical configuration','Actual pin/macro geometry differs','MATCHED_NPU_FRESH_GLOBAL_ROUTE_COMPARISON_ONLY']:
 assert expected in body
assert "state['status'] == 'COMPLETE_MATCHED_ESTIMATES_ONLY'"in s and "fields[19] != str(identity['start_ticks']) or fields[0] == 'Z'"in s
assert "assert comparison == load(B / 'pair02-comparison.json')"in s
assert "assert path.is_file() and not path.is_symlink()"in s and "'..' not in Path(name).parts"in s
assert "assert set(seen) == set(pins)"in s and "assert pin(path) == seen[name]"in s
assert "tarfile.open(archive, 'w:xz'"in s and "assert not archive.exists()"in s
control=json.loads((B/'template-control06/control.json').read_text());peer=json.loads((B/'saved-template-peer-rx01.json').read_text())
assert peer['control']==pin(B/'template-control06/control.json')and peer['freeze']==pin(B/'source-freeze06.json')and peer['source_peer']==pin(B/'source-only-peer-pll06.json')
assert len(control['inputs'])==13
for n,v in control['inputs'].items():
 assert pin(n)==v
 if not n.endswith('.AppImage'):Path(n).relative_to(R)
inputs={str(q):pin(q)for q in [p,runner,B/'source-freeze06.json',B/'source-only-peer-pll06.json',B/'saved-template-peer-rx01.json',B/'template-control06/control.json',B/'sealer-source-peer-pll01-findings.json',B/'sealer-source01-reconstructed-exact.py']}
r=dict(status='PASS_SOURCE_ONLY_NPU_CLOSED_PAIR_SEALER',findings=[],method=pin(p),review_method=pin(__file__),inputs=inputs,whole_source_inverse_matches_initial_reviewed_pin=True,original_source_reconstructed_exact=True,template_inputs_rehashed=13,only_large_runtime_external=True,native_or_sealer_executed=False,scope='Additive metadata gates close previous finding. Original complete body unchanged otherwise: terminal/dead-controller guard, exact saved peer/freeze/control/arm/result/comparison bindings, complete raw compare(), botharm and failedpredecessor/fulltemplate preservation, original notices, allmember readback and original rehash. Permission to seal only after actual terminal closure, not a native result or signoff acceptance.')
out=B/'sealer-source-peer-pll02.json';assert not out.exists();out.write_text(json.dumps(r,indent=2)+'\n');print(pin(out))
