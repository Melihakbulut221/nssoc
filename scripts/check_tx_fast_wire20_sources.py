#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Require only exact parent route width deltas, retaining all native gates."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_tx_fast_wire24_sources import check as prior
    prior()
    for d in json.loads((ROOT/'scripts/tx-fast-wire20-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count']
            s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    pin=json.loads((ROOT/'docs/evidence/tx-v5-timing-priority-physical-pass-20261019.json').read_text())
    assert pin['outputs']['verify-tree32.py']=='264de4e33d7617dd1f4da674577c6297b17f8da634b80357137c10fde9a5ff23'
    print('PASS_EXACT_TX28_WIRE20_CANDIDATE_UNCHANGED_NATIVE_PHYSICAL_GATES')
if __name__=='__main__':check()
