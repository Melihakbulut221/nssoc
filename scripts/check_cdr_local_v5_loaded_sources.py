#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_power_v4_loaded_sources import check as prior
    prior()
    for d in json.loads((ROOT/'scripts/cdr-local-v5-loaded-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count']
            s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==s.encode() and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
        pins=lambda text: sorted(re.findall(r'(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])',text))
        assert pins(raw.decode())==pins(actual.decode()), 'An unchanged dependency SHA256 was accidentally rewritten'
        xor=ROOT/'scripts/cloud_cdr_xor.py'
        assert hashlib.sha256(xor.read_bytes()).hexdigest() in pins(actual.decode())
    print('PASS_EXACT_LOCAL484_LOADED_DELTA_ALL_ORIGINAL_WAVEFORM_GATES_RETAINED')
if __name__=='__main__':check()
