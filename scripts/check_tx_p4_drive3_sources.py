#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Pin physical source and preserve original native DRC/LVS/fault controller."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_tx_fast_wire20_sources import check as prior
    prior()
    m=json.loads((ROOT/'scripts/tx-p4-drive3-source-delta.json').read_text())
    for p,h in m['exact_sources'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
    assert hashlib.sha256((ROOT/'scripts/generate_tx_p4_drive3.py').read_bytes()).hexdigest()==m['generator_sha256']
    for d in m['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count']
            s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    p=json.loads((ROOT/'docs/evidence/tx-fast-wire20-physical-pass-20261020.json').read_text())
    assert p['run']==39401920232 and p['source_head']=='d8e768c22fd7c1caec0db12239387238dbfdc5db'
    assert p['outputs']['source/verify-tree32.py']=='264de4e33d7617dd1f4da674577c6297b17f8da634b80357137c10fde9a5ff23'
    print('PASS_PINNED_FOUR_P4_DRIVE3_SOURCE_ORIGINAL_FULL_PHYSICAL_GATES')
if __name__=='__main__':check()
