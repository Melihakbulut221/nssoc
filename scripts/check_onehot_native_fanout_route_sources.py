#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Preserve the entire proven route ancestry and original physical/timing gates."""
import hashlib,json,runpy
from pathlib import Path
root=Path(__file__).resolve().parents[1]
runpy.run_path(str(root/'scripts/check_onehot_native_resizer_route_sources.py'),run_name='__main__')
for row in json.loads((root/'scripts/onehot-native-fanout-route-source-delta.json').read_text())['files']:
    raw=(root/row['baseline_path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==row['baseline_sha256']
    text=raw.decode()
    for e in row['edits']:
        assert text.count(e['before'])==e['count']
        text=text.replace(e['before'],e['after'])
    actual=(root/row['candidate_path']).read_bytes()
    assert actual==text.encode()and hashlib.sha256(actual).hexdigest()==row['candidate_sha256']
print('PASS_EXACT_FANOUT_ROUTE_HANDOFF_UNCHANGED_CLOCK_ROUTE_RC_STA_GATES')

m=json.loads((root/'scripts/onehot-native-fanout-route-source-delta.json').read_text())
for path,digest in m['fresh_route_support'].items():
    assert hashlib.sha256((root/path).read_bytes()).hexdigest()==digest
print('PASS_EXACT_FRESH_ROUTE_PREPARATION_AND_NATIVE_GUIDE_REBUILD_SOURCES')
