#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Verify exact declared selector-only schematic and physical-method source deltas."""
import hashlib,json,re
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
m=json.loads((root/'scripts/cdr-sampler-selector-v19-source-delta.json').read_text())
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
old=(root/'hw/soc/analog/pcie/rx_sampler_input_drive_v13.spice').read_text()
new=(root/'hw/soc/analog/pcie/rx_sampler_selector_drive_v19.spice').read_text()
def statements(s):
    return [l.strip()for l in s.splitlines()if l.strip()and not l.lstrip().startswith('*')]
a=statements(old);b=statements(new)
assert len(a)==len(b)
count=0
for before,after in zip(a,b,strict=True):
    renamed=before.replace('input_drive_v13','selector_drive_v19')
    if re.match(r'^X(?:CS|CH)[01] ',renamed):
        assert renamed.endswith('Nx=8')and after==renamed[:-4]+'Nx=4';count+=1
    else:assert after==renamed
assert count==8
print('PASS_EXACT_EIGHT_SELECTOR_NX_DELTAS_AND_BOUND_NATIVE_PHYSICAL_METHODS')
