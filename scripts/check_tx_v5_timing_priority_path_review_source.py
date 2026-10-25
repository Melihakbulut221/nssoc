#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_tx_v5_minimax_path_review_source import check as baseline
    baseline()
    from check_tx_v5_timing_priority_wave_sources import check as wave_sources
    wave_sources()
    for d in json.loads((ROOT/'scripts/tx-v5-timing-priority-path-review-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256'];s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count'];s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes();assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    print('PASS_TIMING_PRIORITY_SOURCE_ADAPTATION_UNCHANGED_NATIVE_WAVEFORM_REVIEW')
if __name__=='__main__':check()
