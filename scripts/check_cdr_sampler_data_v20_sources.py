#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind v20 physical methods and allow only eight explicit data/hold Nx changes."""
import hashlib,json,re,runpy
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
runpy.run_path(str(root/'scripts/check_cdr_sampler_selector_v19_sources.py'),run_name='__main__')
m=json.loads((root/'scripts/cdr-sampler-data-v20-source-delta.json').read_text())
for e in m['files']:
    old=(root/e['baseline']).read_bytes()
    assert sha(old)==e['baseline_sha256']
    text=old.decode();parts=[];cursor=0
    for change in e['changes']:
        lo,hi=change['start'],change['end']
        assert cursor<=lo<=hi<=len(text)
        parts.extend([text[cursor:lo],change['replacement']]);cursor=hi
    parts.append(text[cursor:]);candidate=(root/e['candidate']).read_bytes()
    assert candidate==''.join(parts).encode()and sha(candidate)==e['candidate_sha256']
old=(root/'hw/soc/analog/pcie/rx_sampler_selector_drive_v19.spice').read_text()
new=(root/'hw/soc/analog/pcie/rx_sampler_data_drive_v20.spice').read_text()
def statements(s):
    return [l.strip()for l in s.splitlines()if l.strip()and not l.lstrip().startswith('*')]
a=statements(old);b=statements(new);assert len(a)==len(b)
count=0
for before,after in zip(a,b,strict=True):
    renamed=before.replace('selector_drive_v19','data_drive_v20')
    if re.match(r'^X(?:DP|DN|LP|LN) ',renamed):
        assert renamed.endswith('Nx=8')and after==renamed[:-4]+'Nx=4';count+=1
    else:assert after==renamed
assert count==8
print('PASS_EXACT_EIGHT_DATA_HOLD_NX_DELTAS_AND_BOUND_NATIVE_PHYSICAL_METHODS')
