#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_parallel_v3_mim_sources import check as prior
    prior()
    for d in json.loads((ROOT/'scripts/cdr-power-v4-mim-capture-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count']
            s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==s.encode() and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    print('PASS_EXACT_POWER484_MIM_CAPTURE_DELTA_ORIGINAL_GATES_RETAINED')
if __name__=='__main__':check()
