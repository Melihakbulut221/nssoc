#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact four native resistor changes; retain all original physical fault gates."""
import hashlib,json,runpy,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
runpy.run_path(str(root/'scripts/check_cdr_sampler_input_impedance_v30_sources.py'))
m=json.loads((root/'scripts/cdr-sampler-settling-v32-source-delta.json').read_text())
for p,h in m['protected'].items():assert sha((root/p).read_bytes())==h,p
for e in m['files']:
    original=(root/e['baseline']).read_bytes();assert sha(original)==e['baseline_sha256']
    text=original.decode();parts=[];cursor=0
    for change in e['changes']:
        lo,hi=change['start'],change['end'];assert cursor<=lo<=hi<=len(text)
        parts.extend([text[cursor:lo],change['replacement']]);cursor=hi
    parts.append(text[cursor:]);candidate=(root/e['candidate']).read_bytes()
    assert candidate==''.join(parts).encode()and sha(candidate)==e['candidate_sha256']
old=(root/'hw/soc/analog/pcie/rx_sampler_input_impedance_v30.spice').read_text()
new=(root/'hw/soc/analog/pcie/rx_sampler_settling_v32.spice').read_text()
def statements(s):return [l.strip()for l in s.splitlines()if l.strip()and not l.lstrip().startswith('*')]
a,b=statements(old),statements(new);assert len(a)==len(b);count=0
for before,after in zip(a,b,strict=True):
    renamed=before.replace('input_impedance_v30','settling_v32')
    if renamed.startswith(('XBP ','XBN ')):
        assert ' w=4u l=1.1u 'in renamed and after==renamed.replace(' l=1.1u ',' l=.9u ');count+=1
    elif renamed.startswith('XBS ')and ' l=12.8u 'in renamed:
        assert after==renamed.replace(' l=12.8u ',' l=6.4u ');count+=1
    elif renamed.startswith('XBH ')and ' l=9.6u 'in renamed:
        assert after==renamed.replace(' l=9.6u ',' l=4.8u ');count+=1
    else:assert after==renamed
assert count==4
prior=runpy.run_path(str(root/'hw/soc/flow/make_pcie_sampler_input_impedance_v30.py'))
candidate=runpy.run_path(str(root/'hw/soc/flow/make_pcie_sampler_settling_v32.py'))
a=prior['devices'](old);b=candidate['devices'](new);assert len(a)==len(b)==37
changes={'BP':(4,1.1,.9),'BN':(4,1.1,.9),'S_BS':(1,12.8,6.4),'S_BH':(1,9.6,4.8)}
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
assert reference.count('rppd w=4u l=1.2u ')==2
assert reference.count('rppd w=4u l=0.9u ')==2
assert reference.count('rppd w=32u l=2.6u ')==4
assert reference.count('rppd w=1u l=6.4u ')==reference.count('rppd w=1u l=4.8u ')==1
sys.path.insert(0,str(root/'hw/soc/flow'))
physical=runpy.run_path(str(root/'hw/soc/flow/check_pcie_sampler_settling_v32.py'))
prior_physical=runpy.run_path(str(root/'hw/soc/flow/check_pcie_sampler_input_impedance_v30.py'))
assert physical['REFERENCE_FAULTS']==prior_physical['REFERENCE_FAULTS']+('wrong_slave_data_bleed','wrong_slave_hold_bleed')
assert physical['PHYSICAL_FAULTS']==prior_physical['PHYSICAL_FAULTS']
for fault in physical['REFERENCE_FAULTS']:
    mutated=physical['fault_reference'](reference,fault)
    assert mutated!=reference,fault
print('PASS_FOUR_V32_NATIVE_RESISTOR_CHANGES_AND_ORIGINAL_PHYSICAL_GATES_PLUS_TWO_BLEED_FAULTS')
