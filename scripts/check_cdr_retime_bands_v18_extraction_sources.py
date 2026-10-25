#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind fresh physical-band geometry; conserve original full native extraction gates."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_retime_data_v16_extraction_sources import check as original
    original()
    delta=json.loads((ROOT/'scripts/cdr-retime-bands-v18-extraction-source-delta.json').read_text())
    for d in delta['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count'],d['candidate_path']
            s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    pin=json.loads((ROOT/'docs/evidence/cdr-retime-bands-v18-physical-pass-20261020.json').read_text())
    assert pin['run']==39379285294
    assert pin['summary_sha256']=='9d7300c3965d2a9487882e1a569cf17c5328acc130bbf2dc0ee9c993e0c210d3'
    assert pin['parts_sha256']=='b58458f2193418c85cfb1ea89a1716749f5028b2b5ce58558524b1b097f1bdb3'
    assert pin['report']['geometry']['candidate_gds_sha256']=='27321a65507bccd81228e05933676158794b3c099186535fd4f9b892afacb37e'
    print('PASS_FRESH_V18_PHYSICAL_IDENTITY_ORIGINAL_NATIVE_BINDING_RC_GATES_UNCHANGED')
if __name__=='__main__':check()
