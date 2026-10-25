#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import ast,hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
for p,h in json.loads((root/'scripts/cdr-follower-v31-parent-pins.json').read_text()).items():
 raw=(root/p).read_bytes();assert hashlib.sha256(raw).hexdigest()==h,p
 if p.endswith('.py'):ast.parse(raw)
d=json.loads((root/'scripts/cdr-follower-v31-parent-source-adaptation.json').read_text())
raw=(root/d['baseline_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
s=raw.decode()
for e in d['edits']:
 assert s.count(e['before'])==e['count'];s=s.replace(e['before'],e['after'])
raw=(root/d['candidate_path']).read_bytes()
assert raw==s.encode()and hashlib.sha256(raw).hexdigest()==d['candidate_sha256']
print('PASS_EXACT_V31_FOLLOWER_PARENT_SOURCE_ORIGINAL_NATIVE_GATES')
