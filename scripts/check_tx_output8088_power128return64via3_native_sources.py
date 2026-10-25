#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Freeze native process lifecycle and original full electrical review sources."""
import ast,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p,h in json.loads((ROOT/'scripts/tx-output8088-power128return64via3-native-methods.json').read_text()).items():
    raw=(ROOT/p).read_bytes();assert hashlib.sha256(raw).hexdigest()==h,p
    if p.endswith('.py'):ast.parse(raw.decode(),filename=p)
d=json.loads((ROOT/'scripts/tx-output8088-power128return64via3-native-source-delta.json').read_text())
raw=(ROOT/d['baseline_path']).read_bytes()
assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
text=raw.decode()
for e in d['edits']:
    assert text.count(e['before'])==e['count']
    text=text.replace(e['before'],e['after'])
assert text==(ROOT/d['candidate_path']).read_text()
assert hashlib.sha256(text.encode()).hexdigest()==d['candidate_sha256']
print('PASS_EXACT_ACTUAL8088_POWER128RETURN64VIA3_CHECKPOINT_AND_UNCHANGED_FULL_ELECTRICAL_REVIEW_SOURCES')
