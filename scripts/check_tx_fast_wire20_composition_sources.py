#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind exact fresh wire20 RC to unchanged native model/composition checks."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_tx_fast_wire24_composition_sources import check as prior
    from check_tx_fast_wire20_extraction_sources import check as extraction
    prior();extraction()
    for d in json.loads((ROOT/'scripts/tx-fast-wire20-composition-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count']
            s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    print('PASS_WIRE20_NEW_RC_ORIGINAL_DEVICE_BINDING_COMPOSITION_AND_INTERFACES')
if __name__=='__main__':check()
