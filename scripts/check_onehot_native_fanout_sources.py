#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind exact fresh routed baseline and explicit native optimizer changes."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    for d in json.loads((ROOT/'scripts/onehot-native-fanout-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        text=raw.decode();cursor=0;parts=[]
        for e in d['changes']:
            assert cursor<=e['start']<=e['end']<=len(text)
            parts.extend([text[cursor:e['start']],e['replacement']]);cursor=e['end']
        parts.append(text[cursor:])
        got=(ROOT/d['candidate_path']).read_bytes()
        assert got==''.join(parts).encode()and hashlib.sha256(got).hexdigest()==d['candidate_sha256']
    pin=json.loads((ROOT/'docs/evidence/onehot-native-resizer-routed-result-20261020.json').read_text())
    assert pin['run']==39392483151 and pin['routed_instance_count']==151078
    assert pin['summary_sha256']=='b45ac042386d5a8fb09eb74090f8db1ccf63addb2693d0558a8c9ab4e1f6f480'
    assert pin['routed_odb_sha256']=='df3f0fe0bc20b3f6b31e990b488b467b1d0b445847e13eec2fd3a978cda71f0f'
    assert not pin['final_timing_complete']and pin['native_physical_gates_met']
    print('PASS_FRESH_ROUTED_NATIVE_FANOUT_REPAIR_SOURCE_ORIGINAL_TIMING_AND_LOGIC_GATES')
if __name__=='__main__':check()
