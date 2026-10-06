# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent source review of bounded V10 copied-input binder controls."""
from pathlib import Path
import ast,hashlib,json
B=Path(__file__).resolve().parent;W=B.parent;R=Path.cwd()
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def exact(p,h):assert pin(p)==h,str(p)
f=B/'source-freeze.json';j=json.loads(f.read_text());assert len(j['inputs'])==1939
for p,h in j['inputs'].items():exact(p,h)
br=json.loads((B/'source-bridge.json').read_text());exact(br['parent'],br['parent_pin']);exact(br['child'],br['child_pin'])
text=Path(br['parent']).read_text()
for r in br['replacements']:assert text.count(r['old'])==r['count'];text=text.replace(r['old'],r['new'])
assert text==(B/'run.py').read_text();ast.parse(text)
g=json.loads((W/'geometry-execution.json').read_text());assert g['status']=='PASS_DIVIDER_V10_TAIL115_SAVED_NATIVE_GEOMETRY_AND_SOURCE_BIJECTION_ONLY'
for p,h in g['outputs'].items():exact(p,h)
assert len(g['steps'])==7
for row in g['steps']:
 assert row['returncode']==0
assert g['qualified_pex'] is False and g['main_chip_integrated'] is False
p=R/'hw/soc/flow/check_pcie_clock_div4_v7_v2.py';assert pin(p)['sha256']=='24c89628c6d61226344214e077b5fa535c5570e4a7853fbd109e8cb1b1fcd163'
for clause in ["assert sum(map(len, edits.values())) == (0 if name == 'positive' else 1)","assert execution['returncode'] == 1 and not output.exists()","assert expected in log", "assert inputs == {p: pin(p) for p in inputs}","assert freeze['inputs'] == {p: pin(p) for p in freeze['inputs']}","method.replace(replacement, old_root) == source"]:assert clause in text
assert not Path('/dev/shm/nssoc-div4-v10-tail-v1-binding-controls-01').exists() and not (B/'result.json').exists()
result=dict(status='PASS_SOURCE_ONLY_DIVIDER_V7_BINDING_CONTROLS',reviewer='root independent source review',freeze=pin(f),findings=[],inputs_checked=1939,geometry_steps=7,source_bridge=pin(B/'source-bridge.json'),method=pin(__file__),scope='Authorize exactly five copied-input binder runs; baseline identical and four single-edit reference/native faults must reject at their original assertions. No circuit mutation, new extraction, electrical result or production acceptance. Same inherited process ownership and resource guards retained.',full_phy_acceptance=False)
(B/'source-only-peer-rx.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
