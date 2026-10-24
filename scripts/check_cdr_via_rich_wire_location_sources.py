#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
m=json.loads((root/'scripts/cdr-via-rich-wire-location-source-delta.json').read_text())
s=(root/m['baseline_path']).read_text();assert hashlib.sha256(s.encode()).hexdigest()==m['baseline_sha256']
for e in m['edits']:
    assert s.count(e['before'])==e['count'];s=s.replace(e['before'],e['after'])
a=(root/m['candidate_path']).read_bytes();assert a==s.encode()and hashlib.sha256(a).hexdigest()==m['candidate_sha256']
print('PASS_EXACT_NATIVE_COORDINATE_DIAGNOSTIC_ADAPTATION')
