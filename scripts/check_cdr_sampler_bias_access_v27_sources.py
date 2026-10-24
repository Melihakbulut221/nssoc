#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind only two bias resistor length changes to the actual v26 baseline."""
import hashlib,json,runpy
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
m=json.loads((root/'scripts/cdr-sampler-bias-access-v27-source-delta.json').read_text())
for p,h in m['protected'].items():assert sha((root/p).read_bytes())==h,p
for e in m['files']:
    original=(root/e['baseline']).read_bytes();assert sha(original)==e['baseline_sha256']
    text=original.decode();parts=[];cursor=0
    for change in e['changes']:
        lo,hi=change['start'],change['end'];assert cursor<=lo<=hi<=len(text)
        parts.extend([text[cursor:lo],change['replacement']]);cursor=hi
    parts.append(text[cursor:]);candidate=(root/e['candidate']).read_bytes()
    assert candidate==''.join(parts).encode()and sha(candidate)==e['candidate_sha256']
old=(root/'hw/soc/analog/pcie/rx_sampler_input_access_v26.spice').read_text()
new=(root/'hw/soc/analog/pcie/rx_sampler_bias_access_v27.spice').read_text()
def statements(s):return [l.strip()for l in s.splitlines()if l.strip()and not l.lstrip().startswith('*')]
a,b=statements(old),statements(new);assert len(a)==len(b);count=0
for before,after in zip(a,b,strict=True):
    renamed=before.replace('input_access_v26','bias_access_v27')
    if renamed.startswith(('XBP ','XBN ')):
        assert ' w=4u l=2.4u 'in renamed and after==renamed.replace(' l=2.4u ',' l=.9u ');count+=1
    else:assert after==renamed
assert count==2
prior=runpy.run_path(str(root/'hw/soc/flow/make_pcie_sampler_input_access_v26.py'))
candidate=runpy.run_path(str(root/'hw/soc/flow/make_pcie_sampler_bias_access_v27.py'))
a=prior['devices'](old);b=candidate['devices'](new);assert len(a)==len(b)==37
changed=[]
for x,y in zip(a,b,strict=True):
    expected=dict(x)
    if x['name']in ('BP','BN'):
        assert x['kind']=='resistor'and x['width_um']==4 and x['length_um']==2.4
        expected['length_um']=.9;changed.append(x['name'])
    assert y==expected,(x['name'],'Unrelated primitive changed')
assert sorted(changed)==['BN','BP']
reference=candidate['physical_reference'](new)
assert len([l for l in reference.splitlines()if l.startswith(('Q','M','R'))])==54
assert reference.count('npn13G2 Nx=4 ')==reference.count('npn13G2 Nx=2 ')==8
assert reference.count('rppd w=4u l=0.9u ')==4
print('PASS_EXACT_TWO_BIAS_RESISTOR_LENGTH_CHANGES_UNCHANGED52_PRIMITIVES_AND_ORIGINAL_PHYSICAL_GATES')
