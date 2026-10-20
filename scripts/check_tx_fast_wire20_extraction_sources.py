#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind wire20 extraction to exact original methods and new physical evidence."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_tx_fast_wire24_extraction_sources import check as baseline
    from check_tx_fast_wire20_sources import check as physical
    baseline();physical()
    for d in json.loads((ROOT/'scripts/tx-fast-wire20-extraction-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count']
            s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    pin=json.loads((ROOT/'docs/evidence/tx-fast-wire20-physical-pass-20261020.json').read_text())
    assert pin['run']==39401920232 and pin['summary_sha256']=='8a9da85ef2508a72a0f26722d9e5b5f9a5c8bfb3d88e5f69e4ae2d36c6a17e7a'
    assert pin['report']['layout']['total_devices']==1674
    print('PASS_WIRE20_FRESH_EXTRACTION_EXACT_SOURCE_DELTA_ORIGINAL_13_FAULTS')
if __name__=='__main__':check()
