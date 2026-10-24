#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_parent_avdd_v13_mim_capture_sources import check as current
    from check_cdr_localbus_v12_mim_sources import check as baseline
    current();baseline()
    for d in json.loads((ROOT/'scripts/cdr-parent-avdd-v13-mim-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256'];s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count'];s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes();assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    pin=json.loads((ROOT/'docs/evidence/cdr-parent-avdd-v13-mim-parent-capture-pass-20261019.json').read_text())
    assert pin['run']==39275348623 and pin['summary_asset']==656614341
    assert pin['report']['intrinsic_capture_binding']['R']==16010 and pin['report']['intrinsic_capture_binding']['C']==11677
    print('PASS_FRESH_AVDD_CAPTURE_CENSUS_ORIGINAL22_RAW_AND19_COMPOSITION_GATES')
if __name__=='__main__':check()
