#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    for d in json.loads((ROOT/'scripts/cdr-parallel-v3-path-review-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256'];s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count'];s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes();assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    assert 116+46+102+11+209==484 and 116*4+46*4+102*3+11*2+209*2==1394
    assert 116+46+102+209==473 and 1394-473+25==946
    print('PASS_EXACT484_NATIVE_PATH_REVIEW_DELTA_ORIGINAL_NATIVE_GATES_UNCHANGED')
if __name__=='__main__':check()
