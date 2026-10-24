#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import ast,hashlib,json
from pathlib import Path
r=Path(__file__).resolve().parents[1];d=json.loads((r/'scripts/native-btrfs-source-delta.json').read_text())
sha=lambda b:hashlib.sha256(b).hexdigest()
raw=(r/d['baseline_path']).read_bytes();assert sha(raw)==d['baseline_sha256'];text=raw.decode()
for e in d['edits']:
    assert text.count(e['before'])==e['count'];text=text.replace(e['before'],e['after'])
assert text.encode()==(r/d['candidate_path']).read_bytes()
for p,h in d['pins'].items():
    b=(r/p).read_bytes();assert sha(b)==h
    if p.endswith('.py'):ast.parse(b)
print('PASS_EXACT_STORAGE_PROBE_DELTA_ORIGINAL_NATIVE_TRAJECTORY_GATES_RETAINED')
