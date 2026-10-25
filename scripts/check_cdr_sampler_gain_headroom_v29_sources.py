#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind six real collector/bias resistor changes while retaining original physical gates."""
import hashlib,json,runpy,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
m=json.loads((root/'scripts/cdr-sampler-gain-headroom-v29-source-delta.json').read_text())
for p,h in m['protected'].items():assert sha((root/p).read_bytes())==h,p
for e in m['files']:
    original=(root/e['baseline']).read_bytes();assert sha(original)==e['baseline_sha256']
    text=original.decode();parts=[];cursor=0
    for change in e['changes']:
        lo,hi=change['start'],change['end'];assert cursor<=lo<=hi<=len(text)
        parts.extend([text[cursor:lo],change['replacement']]);cursor=hi
    parts.append(text[cursor:]);candidate=(root/e['candidate']).read_bytes()
    assert candidate==''.join(parts).encode()and sha(candidate)==e['candidate_sha256']
old=(root/'hw/soc/analog/pcie/rx_sampler_input_loading_v28.spice').read_text()
new=(root/'hw/soc/analog/pcie/rx_sampler_gain_headroom_v29.spice').read_text()
def statements(s):return [l.strip()for l in s.splitlines()if l.strip()and not l.lstrip().startswith('*')]
a,b=statements(old),statements(new);assert len(a)==len(b);count=0
for before,after in zip(a,b,strict=True):
    renamed=before.replace('input_loading_v28','gain_headroom_v29')
    if renamed.startswith(('XRP ','XRN ')):
        assert ' w=32u l=2.12u 'in renamed and after==renamed.replace(' l=2.12u ',' l=2.6u ');count+=1
    elif renamed.startswith(('XBP ','XBN ')):
        assert ' w=4u l=2.4u 'in renamed and after==renamed.replace(' l=2.4u ',' l=2.2u ');count+=1
    else:assert after==renamed
assert count==6
prior=runpy.run_path(str(root/'hw/soc/flow/make_pcie_sampler_input_loading_v28.py'))
candidate=runpy.run_path(str(root/'hw/soc/flow/make_pcie_sampler_gain_headroom_v29.py'))
a=prior['devices'](old);b=candidate['devices'](new);assert len(a)==len(b)==37
changes={'BP':(4,2.4,2.2),'BN':(4,2.4,2.2),**{n:(32,2.12,2.6)for n in ('M_RP','M_RN','S_RP','S_RN')}}
changed=[]
for x,y in zip(a,b,strict=True):
    expected=dict(x)
    if x['name']in changes:
        width,before,after=changes[x['name']]
        assert x['kind']=='resistor'and x['width_um']==width and x['length_um']==before
        expected['length_um']=after;changed.append(x['name'])
    assert y==expected,(x['name'],'Unrelated primitive changed')
assert set(changed)==set(changes)
reference=candidate['physical_reference'](new)
assert len([l for l in reference.splitlines()if l.startswith(('Q','M','R'))])==54
assert reference.count('npn13G2 Nx=4 ')==reference.count('npn13G2 Nx=2 ')==8
assert reference.count('rppd w=4u l=2.4u ')==2
assert reference.count('rppd w=4u l=2.2u ')==2
assert reference.count('rppd w=32u l=2.6u ')==4
sys.path.insert(0,str(root/'hw/soc/flow'))
physical=runpy.run_path(str(root/'hw/soc/flow/check_pcie_sampler_gain_headroom_v29.py'))
prior_physical=runpy.run_path(str(root/'hw/soc/flow/check_pcie_sampler_input_loading_v28.py'))
assert physical['REFERENCE_FAULTS']==prior_physical['REFERENCE_FAULTS']
assert physical['PHYSICAL_FAULTS']==prior_physical['PHYSICAL_FAULTS']
for fault in physical['REFERENCE_FAULTS']:
    mutated=physical['fault_reference'](reference,fault)
    assert mutated!=reference,fault
print('PASS_EXACT_SIX_GAIN_BIAS_LENGTH_CHANGES_UNCHANGED48_PRIMITIVES_AND_ORIGINAL_PHYSICAL_GATES')
