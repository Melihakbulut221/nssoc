#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_input_drive_v10_mim_capture_sources import check as current
    from check_cdr_data_cm_v9_mim_composition_sources import check as baseline
    current();baseline()
    for d in json.loads((ROOT/'scripts/cdr-input-drive-v10-mim-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256'];s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count'];s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes();assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    pin=json.loads((ROOT/'docs/evidence/cdr-input-drive-v10-mim-parent-capture-pass-20261019.json').read_text())
    assert pin['run']==39212674566 and pin['summary_asset']==655491881
    assert pin['report']['intrinsic_capture_binding']['R']==15482 and pin['report']['intrinsic_capture_binding']['C']==11527
    print('PASS_NEW_CAPTURE_BOUND_CENSUS_ORIGINAL_22_RAW_AND19_COMPOSITION_GATES')
if __name__=='__main__':check()
