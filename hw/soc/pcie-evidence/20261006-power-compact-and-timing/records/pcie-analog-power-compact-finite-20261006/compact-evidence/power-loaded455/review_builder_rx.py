# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import ast, hashlib, json
from collections import Counter
B=Path(__file__).resolve().parent
def pin(p):
 p=Path(p);return dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
fpath=B/'builder-source-freeze.json';f=json.loads(fpath.read_text())
assert pin(fpath)==dict(bytes=4484,sha256='a250fcc4a050b83055573d64d49e8702b9defd1a6c8180b6945dc722ab9845bf')
assert f['inputs']=={p:pin(p)for p in f['inputs']}
b=json.loads((B/'builder-source-bridge.json').read_text())
a=Path(b['before']['path']).read_text();z=Path(b['after']['path']).read_text()
assert a==''.join(x['before']for x in b['opcodes']) and z==''.join(x['after']for x in b['opcodes'])
old=ast.parse(a);new=ast.parse(z)
def assign(t,k):
 return next(n for n in t.body if isinstance(n,ast.Assign) and any(isinstance(v,ast.Name)and v.id==k for v in n.targets))
oldpins=ast.literal_eval(assign(old,'PINS').value);newpins=ast.literal_eval(assign(new,'PINS').value)
assert set(oldpins)==set(newpins)==set(f['native_input_files'])
expected=a
for k in oldpins:
 assert newpins[k]==pin(f['native_input_files'][k])['sha256']
 assert expected.count(oldpins[k])==1
 expected=expected.replace(oldpins[k],newpins[k])
assert expected.count('{"R": 312, "C": 618}')==1
expected=expected.replace('{"R": 312, "C": 618}','{"R": 384, "C": 657}')
expected=expected.replace('nssoc_clock_div4_v7_hybrid_open_v1','nssoc_clock_div4_v7_power_v2_hybrid_open_v1')
assert expected==z
olddefs={n.name:ast.dump(n,include_attributes=False)for n in old.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
newdefs={n.name:ast.dump(n,include_attributes=False)for n in new.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
assert set(olddefs)==set(newdefs)
changed=[k for k in olddefs if olddefs[k]!=newdefs[k]]
assert set(changed)=={'wire_records','compose'}
a=json.loads(Path(f['native_input_files']['anchors']).read_text())
assert len(a['anchors'])==205 and len(a['unmodeled_body_well_terminals'])==85
assert Counter(x['native_cluster']for x in a['unmodeled_body_well_terminals'])=={1:85}
rows=[s.split()for s in Path(f['native_input_files']['wires']).read_text().splitlines() if s.startswith(('R','C'))]
assert Counter(r[0][0]for r in rows)=={'R':384,'C':657}
assert 'BODY_SUBSTRATE' in z and 'WIRE_CREF' in z
r=dict(status='PASS_SOURCE_ONLY_POWER_V2_DIVIDER_HYBRID_BUILDER',freeze=pin(fpath),findings=[],method=pin(__file__),verified_input_count=len(f['inputs']),whole_byte_forward_inverse=True,independent_exact_delta='Five new native input SHA values, measured384R/657C census, distinct hybrid subcircuit name only. All converter/device/body logic byte-exact.',changed_functions=changed,actual_body_cluster_count={1:85},actual_wire_elements=dict(Counter(r[0][0]for r in rows)),scope='Source-only peer; no builder composition or native model generation executed. Independent saved-RC peer remains a separate prerequisite. Open body and capacitance reference are distinct; not qualified PEX or full PHY.',source=pin(f['method']['path']))
(B/'builder-source-only-peer-rx.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r,indent=2))
