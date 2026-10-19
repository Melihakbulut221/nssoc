#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_sampler_input_drive_sources import check as sampler
    from check_cdr_data_cm_v9_parent_sources import check as parent
    sampler();parent()
    for d in json.loads((ROOT/'scripts/cdr-retime-drive-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256'];s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count'];s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes();assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    print('PASS_NATIVE_RETIME_IMPEDANCE_SCALING_ORIGINAL_PHYSICAL_GATES_PLUS_OLD_GEOMETRY_FAULTS')
if __name__=='__main__':check()
