#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_retime_data_v16_mim_capture_sources import check as current
    from check_cdr_xor_collector_v15_mim_sources import check as baseline
    current();baseline()
    for d in json.loads((ROOT/'scripts/cdr-retime-data-v16-mim-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256'];s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count'];s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes();assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    pin=json.loads((ROOT/'docs/evidence/cdr-retime-data-v16-mim-parent-capture-pass-20261020.json').read_text())
    assert pin['run']==39336054657 and pin['summary_asset']==657627080
    assert pin['summary_sha256']=='d167fa8f639970a85cf810f4f2b2e182f40731e31eecb9bae5a59ba9c72859ee'
    assert pin['report']['intrinsic_capture_binding']['R']==17674 and pin['report']['intrinsic_capture_binding']['C']==12709
    print('PASS_RETIME_DATA_V16_CAPTURE_CENSUS_ORIGINAL22_RAW_AND19_COMPOSITION_GATES')
if __name__=='__main__':check()
