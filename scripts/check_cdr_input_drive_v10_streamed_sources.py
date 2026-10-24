#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_data_cm_v9_streamed_sources import check as baseline
    from check_cdr_input_drive_v10_mim_sources import check as physical
    baseline();physical()
    spec=json.loads((ROOT/'scripts/cdr-input-drive-v10-streamed-source-delta.json').read_text())
    for d in spec['files']:
        raw=(ROOT/d['baseline_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256'];s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count'];s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes();assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    for path,h in spec['unchanged_dependencies'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==h
    print('PASS_INPUT_DRIVE_MODEL_ORIGINAL_FULL_LOADED_BIT_PHASE_AND_DEVICE_GATES_UNCHANGED')
if __name__=='__main__':check()
