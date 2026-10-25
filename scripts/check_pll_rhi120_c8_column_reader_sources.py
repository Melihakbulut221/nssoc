#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import ast,hashlib,json
from pathlib import Path
m=json.loads(Path('scripts/pll-rhi120-c8-column-reader-delta.json').read_text())
raw=Path(m['baseline']).read_bytes()
assert hashlib.sha256(raw).hexdigest()==m['baseline_sha256']
s=raw.decode()
for e in m['edits']:
    assert s.count(e['before'])==e['count']
    s=s.replace(e['before'],e['after'])
actual=Path(m['candidate']).read_bytes()
assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==m['candidate_sha256']
ast.parse(s)
for p,h in m['protected'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
print('PASS_RHI120_EXACT_TABLE_PROVENANCE_CHANGE_ONLY_ORIGINAL_FULL_CAPTURE_GATES')
