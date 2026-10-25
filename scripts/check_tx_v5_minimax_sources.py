#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    for d in json.loads((ROOT/'scripts/tx-v5-minimax-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256'];s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count'];s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes();assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    for p,h in json.loads((ROOT/'scripts/tx-v5-minimax-source-delta.json').read_text())['helpers'].items():
        assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
    print('PASS_EXACT_SOURCE_ADAPTATION_WITH_ORIGINAL_GATES')
if __name__=='__main__':check()
