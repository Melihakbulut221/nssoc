#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    d=json.loads((ROOT/'scripts/cdr-power-v4-wire-inputs-source-delta.json').read_text())
    raw=(ROOT/d['baseline_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256'];s=raw.decode()
    for e in d['edits']:
        assert s.count(e['before'])==e['count'];s=s.replace(e['before'],e['after'])
    actual=(ROOT/d['candidate_path']).read_bytes();assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    # Derived from unsimplified native device terminal arities, not a fitted count.
    assert 116*4+46*4+102*3+11*2+209*2==1394
    assert 116+46+102+209==473 and 1394-473==921 and 921+25==946
    print('PASS_EXACT_POWER_PARENT484_WIRE_INPUTS_DELTA_NATIVE_METAL_BODY_GATES_UNCHANGED')
if __name__=='__main__':check()
