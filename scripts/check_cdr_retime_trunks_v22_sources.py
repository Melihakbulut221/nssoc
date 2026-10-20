#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind v22 retime route delta and preserve the full original native gates."""
import hashlib,json,runpy
from pathlib import Path
root=Path(__file__).resolve().parents[1]
runpy.run_path(str(root/'scripts/check_cdr_collector_trunks_v21_sources.py'),run_name='__main__')
m=json.loads((root/'scripts/cdr-retime-trunks-v22-source-delta.json').read_text())
assert m['baseline_run']==39440691879 and m['passive_measurement_run']==39451162827
for d in m['files']:
    raw=(root/d['baseline_path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
    s=raw.decode()
    for e in d['edits']:
        assert s.count(e['before'])==e['count']
        s=s.replace(e['before'],e['after'])
    actual=(root/d['candidate_path']).read_bytes()
    assert actual==s.encode() and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
for path,digest in m['protected'].items():
    assert hashlib.sha256((root/path).read_bytes()).hexdigest()==digest,path
print('PASS_EXACT_FOUR_RETIME_TRUNKS_V22_UNCHANGED_NATIVE_FULL484_PHYSICAL_GATES')
