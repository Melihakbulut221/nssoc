#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind eight actual data/hold Nx4->3 changes and retain native physical gates."""
import hashlib,json,re,runpy
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
runpy.run_path(str(root/'scripts/check_cdr_sampler_selector_small_v24_sources.py'),run_name='__main__')
m=json.loads((root/'scripts/cdr-sampler-data3-v25-source-delta.json').read_text())
for p,h in m['protected'].items():assert sha((root/p).read_bytes())==h
for e in m['files']:
    old=(root/e['baseline']).read_bytes();assert sha(old)==e['baseline_sha256']
    text=old.decode();parts=[];cursor=0
    for change in e['changes']:
        lo,hi=change['start'],change['end'];assert cursor<=lo<=hi<=len(text)
        parts.extend([text[cursor:lo],change['replacement']]);cursor=hi
    parts.append(text[cursor:]);candidate=(root/e['candidate']).read_bytes()
    assert candidate==''.join(parts).encode()and sha(candidate)==e['candidate_sha256']
old=(root/'hw/soc/analog/pcie/rx_sampler_selector_small_v24.spice').read_text()
new=(root/'hw/soc/analog/pcie/rx_sampler_data3_v25.spice').read_text()
def statements(s):return [l.strip()for l in s.splitlines()if l.strip()and not l.lstrip().startswith('*')]
a,b=statements(old),statements(new);assert len(a)==len(b);count=0
for before,after in zip(a,b,strict=True):
    renamed=before.replace('selector_small_v24','data3_v25')
    if re.match(r'^X(?:DP|DN|LP|LN) ',renamed):
        assert renamed.endswith('Nx=4')and after==renamed[:-4]+'Nx=3';count+=1
    else:assert after==renamed
assert count==8
# Exercise the actual schematic flattener before restoring native CAD.
prior=runpy.run_path(str(root/'hw/soc/flow/make_pcie_sampler_selector_small_v24.py'))
nextgen=runpy.run_path(str(root/'hw/soc/flow/make_pcie_sampler_data3_v25.py'))
rows0=prior['devices'](old);rows1=nextgen['devices'](new)
assert len(rows0)==len(rows1)==37
changed=0
for a,b in zip(rows0,rows1,strict=True):
    expected=dict(a)
    if a['kind']=='hbt'and a['name'] in {stage+'_'+side for stage in ('M','S')for side in ('DP','DN','LP','LN')}:
        assert a['nx']==4;expected['nx']=3;changed+=1
    assert b==expected,(a['name'],'Unexpected flattened native device change')
assert changed==8
reference=nextgen['physical_reference'](new)
assert '.subckt '+nextgen['TOP']+' ' in reference
assert len([line for line in reference.splitlines()if line.startswith(('Q','M','R'))])==54
assert reference.count('npn13G2 Nx=3 ')==reference.count('npn13G2 Nx=2 ')==8
print('PASS_EXACT_EIGHT_DATA_HOLD_NX4_TO3_CHANGES_AND_BOUND_PHYSICAL_METHODS_AND_NATIVE_FLATTENER')
