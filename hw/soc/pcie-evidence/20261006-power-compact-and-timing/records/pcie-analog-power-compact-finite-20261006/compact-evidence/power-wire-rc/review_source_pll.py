"""Read-only full pin/source-bridge validation; never imports producer or runs RC."""
from pathlib import Path
import ast,hashlib,json
B=Path(__file__).resolve().parent

def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
freeze=B/'source-freeze.json'; assert pin(freeze)['sha256']=='d84e336d75a2578cd0e41967ba4dd1b924c885a502314179186c5123bed95f69'
f=json.loads(freeze.read_text());assert len(f['inputs'])==1419
for p,v in f['inputs'].items():assert pin(p)==v,p
bridges=json.loads((B/'draft-source-bridge.json').read_text());assert len(bridges)==3
summary=[]
for row in bridges:
 for key in ('before','after'):
  p=Path(row[key]['path']);assert pin(p)=={k:row[key][k] for k in ('bytes','sha256')}
  assert ''.join(e[key] for e in row['opcodes'])==p.read_text()
 summary.append(dict(before=row['before'],after=row['after'],edits=[{k:e[k] for k in ('tag','before','after')} for e in row['opcodes'] if e['tag']!='equal']))
audit=(B/'audit_wire_rc.py').read_text();prior=Path(bridges[1]['before']['path']).read_text()
assert audit.replace('pcie-divider-v7-power-v2-wire-v2-20261006','pcie-divider-v7-wire-v5-20261005')==prior
source=(B/'run_native_rc.py').read_text();base=Path(bridges[0]['before']['path']).read_text()
for new,old in [('pcie-divider-v7-power-v2-wire-v2-20261006','pcie-divider-v7-wire-v5-20261005'),('nssoc-div4-v7-power-v2-wire-rc-01','nssoc-div4-v7-wire-rc-01'),('nssoc-div4-v7-power-v2-wire-geometry-02','nssoc-div4-v7-wire-geometry-05'),('check_native_mutations_v2.py','check_native_mutations.py'),('native-mutations-v2.json','native-mutations.json')]:source=source.replace(new,old)
assert source==base
# Compare actual explicit case names and diagnostics, including three anchor cases.
def predicates(s):
 tree=ast.parse(s);names=[]
 for node in ast.walk(tree):
  if isinstance(node,ast.Tuple) and len(node.elts)==3 and isinstance(node.elts[0],ast.Constant) and isinstance(node.elts[2],ast.Constant) and isinstance(node.elts[0].value,str) and isinstance(node.elts[2].value,str):names.append((node.elts[0].value,node.elts[2].value))
 return names
mutation=(B/'check_native_mutations_v2.py').read_text();old=Path(bridges[2]['before']['path']).read_text()
assert predicates(mutation)==predicates(old) and len(predicates(mutation))==13
# Explicit extraction and positive-audit behavior are unchanged, only actual mutation targets improved.
assert 'assert nx.number_connected_components(graph)==37' in mutation
assert 'assert nx.number_connected_components(trial)==38' in mutation
assert 'left&set(anchor) and right&set(anchor)' in mutation
assert "assert anchor['P004']!=anchor['P005']" in mutation
assert "assert owner[cf[1]]!=owner[cf[2]]" in mutation
geo=B.parent/'pcie-divider-v7-power-v2-wire-v2-20261006'
peer=json.loads((geo/'saved-geometry-peer.json').read_text())
assert peer['status']=='PASS_DIVIDER_V7_SAVED_GEOMETRY_AND_BINDING_CONTROLS' and not peer['findings']
assert peer['geometry_execution']==pin(geo/'geometry-execution.json')
assert peer['binding_controls']==pin(geo/'binding-controls01/result.json')
assert not (B/'native-execution.json').exists()
r=dict(status='PASS_SOURCE_ONLY_DIVIDER_V7_WIRE_RC',freeze=pin(freeze),findings=[],source_pins_rehashed=1419,full_inverse_bridges=summary,unchanged13_expected_diagnostics=predicates(mutation),saved_geometry_peer=pin(geo/'saved-geometry-peer.json'),scope='Source-only independent review. Entire runner/auditor/control harness read, all1419pins and3whole-source inverses verified. Existing Tcl AST/owned resource helper/runtime unchanged; fresh205anchor geometry gate and source bijection retained. New resistor control chooses unique physical bridge separating actual probes,37to38components; C controls target actual mutualC, short crosses distinct conductors. No RC extraction, HDL, SPICE or negative-control execution performed; actual native positive+13control pass still required. Not qualified fullPEX or PHY signoff.')
(B/'source-only-peer.json').write_text(json.dumps(r,indent=2)+'\n')
print(r['status'],pin(B/'source-only-peer.json'))
