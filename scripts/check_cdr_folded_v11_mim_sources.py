#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_folded_v11_mim_capture_sources import check as current
    from check_cdr_input_drive_v10_mim_sources import check as baseline
    current();baseline()
    for d in json.loads((ROOT/'scripts/cdr-folded-v11-mim-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256'];s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count'];s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes();assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    pin=json.loads((ROOT/'docs/evidence/cdr-folded-v11-mim-parent-capture-pass-20261019.json').read_text())
    assert pin['run']==39236131141 and pin['summary_asset']==655932597
    assert pin['report']['intrinsic_capture_binding']['R']==15482 and pin['report']['intrinsic_capture_binding']['C']==11590
    print('PASS_FRESH_FOLDED_CAPTURE_CENSUS_ORIGINAL22_RAW_AND19_COMPOSITION_GATES')
if __name__=='__main__':check()
