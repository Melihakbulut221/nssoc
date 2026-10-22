#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Require exact sparse native replay gates plus the lossless archive roundtrips."""
import ast,hashlib,json,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def check():
    runpy.run_path(str(ROOT/'scripts/check_native_sparse_btrfs_sources.py'),run_name='__main__')
    pins=json.loads((ROOT/'scripts/native-logical-btrfs-pins.json').read_text())
    for p,h in pins.items():
        assert sha(ROOT/p)==h,p
        if p.endswith('.py'):ast.parse((ROOT/p).read_text())
    d=json.loads((ROOT/'scripts/native-logical-btrfs-delta.json').read_text())
    raw=(ROOT/d['baseline_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
    text=raw.decode()
    for e in d['edits']:
        assert text.count(e['before'])==e['count']
        text=text.replace(e['before'],e['after'])
    actual=(ROOT/d['candidate_path']).read_text();assert actual==text
    assert hashlib.sha256(actual.encode()).hexdigest()==d['candidate_sha256']
    pin=json.loads((ROOT/'docs/evidence/logical-native-archive-qualified-20261022.json').read_text())
    assert pin['status']=='PASS_LOGICAL_ARCHIVE_AND_NATIVE_PREFIX_NOT_NATIVE_ACTIVATION'
    assert len(pin['controls']['report']['new_negative_controls'])==16
    bad={x['name']:x for x in pin['controls']['report']['new_negative_controls']}
    assert bad['bad-upload-receipt']['reason']=='Hosted asset identity/size/digest mismatch'
    assert bad['failed-upload']['reason']=='Injected failed upload'
    assert bad['bad-upload-receipt']['upload_calls']==bad['failed-upload']['upload_calls']==1
    assert pin['native-prefix']['report']['all5106_column_bytes_preserved']
    assert pin['native-prefix']['report']['columns']==5106
    assert len(pin['native-prefix']['report']['reader_controls']['controls'])==16
    print('PASS_ORIGINAL_NATIVE845_REPLAY_GATES_AND_LOSSLESS_LOGICAL_ARCHIVE_PROVENANCE')
if __name__=='__main__':check()
