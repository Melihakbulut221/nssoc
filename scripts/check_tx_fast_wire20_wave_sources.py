#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Limit the wire20 test change to exact fresh model identities and source paths."""
import hashlib,json,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_tx_fast_wire24_wave_sources import check as original
    from check_tx_fast_wire20_composition_sources import check as composition
    original();composition()
    runpy.run_path(str(ROOT/'scripts/check_tx_wire24_g234_sources.py'),run_name='__main__')
    for d in json.loads((ROOT/'scripts/tx-fast-wire20-wave-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count']
            s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    print('PASS_WIRE20_EXACT_FRESH_MODELS_ORIGINAL_LOADED_SIGNAL_DEVICE_SOLVER_CLOCK_GATES')
if __name__=='__main__':check()
