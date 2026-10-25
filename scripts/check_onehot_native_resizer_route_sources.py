#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind the routed candidate handoff and unchanged native topology comparison."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
m=json.loads((root/'scripts/onehot-native-resizer-route-source-delta.json').read_text())
for row in m['files']:
    text=(root/row['baseline']).read_text()
    assert sha(text.encode())==row['baseline_sha256']
    cursor=0;parts=[]
    for e in row['changes']:
        assert cursor<=e['start']<=e['end']<=len(text)
        parts.extend([text[cursor:e['start']],e['replacement']]);cursor=e['end']
    parts.append(text[cursor:]);candidate=(root/row['candidate']).read_bytes()
    assert candidate==''.join(parts).encode()and sha(candidate)==row['candidate_sha256']
assert all(sha((root/p).read_bytes())==v for p,v in m['unchanged_physical_methods'].items())
print('PASS_EXACT_NATIVE_RESIZER_ROUTE_HANDOFF_AND_UNCHANGED_PHYSICAL_TIMING_GATES')
