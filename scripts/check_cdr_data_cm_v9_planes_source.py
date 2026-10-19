#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_data_cm_v9_parent_sources import check as parent
    from check_cdr_collector_v8_planes_source import check as baseline
    parent();baseline()
    for d in json.loads((ROOT/'scripts/cdr-data-cm-v9-planes-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256'];s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count'];s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes();assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    print('PASS_NEW_NATIVE_PARENT_BINDING_UNCHANGED_158_PLANES_AND_19_FAULTS')
if __name__=='__main__':check()
