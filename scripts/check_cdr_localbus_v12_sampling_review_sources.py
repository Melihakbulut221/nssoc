#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_collector_v8_sampling_review_sources import check as prior
    from check_cdr_input_drive_v10_streamed_sources import check as native
    prior();native()
    for d in json.loads((ROOT/'scripts/cdr-localbus-v12-sampling-review-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256'];s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count'];s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes();assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    print('PASS_CURRENT_INPUT_DRIVE_RAW_WAVES_FIXED_ORIGINAL_PHASES_NO_NEW_ACCEPTANCE')
if __name__=='__main__':check()
