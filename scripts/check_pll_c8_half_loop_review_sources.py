#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    d=json.loads((ROOT/'scripts/pll-c8-half-loop-review-source-delta.json').read_text())
    raw=(ROOT/d['baseline_path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
    s=raw.decode()
    for e in d['edits']:
        assert s.count(e['before'])==e['count'];s=s.replace(e['before'],e['after'])
    actual=(ROOT/d['candidate_path']).read_bytes()
    assert s.encode()==actual and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    assert hashlib.sha256((ROOT/d['helper_path']).read_bytes()).hexdigest()==d['helper_sha256']
    print('PASS_IMMUTABLE_HALF_STEP_CAPTURE_AND_ORIGINAL_ACQUISITION_REPRODUCTION_METHODS')
if __name__=='__main__':check()
