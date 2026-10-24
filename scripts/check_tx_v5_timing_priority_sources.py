#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Declared geometry-planning changes; retain every original native physical gate."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_tx_v5_minimax_sources import check as baseline
    baseline()
    for d in json.loads((ROOT/'scripts/tx-v5-timing-priority-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256'];s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count'];s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes();assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    print('PASS_TIMING_PRIORITY_LAYOUT_DELTA_ORIGINAL_NATIVE_DRC_LVS_FAULT_GATES')
if __name__=='__main__':check()
