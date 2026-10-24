#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_sampler_input_drive_sources import check as baseline
    baseline()
    spec=json.loads((ROOT/'scripts/cdr-sampler-folded-source-delta.json').read_text())
    for d in spec['files']:
        raw=(ROOT/d['baseline_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256'];text=raw.decode()
        for e in d['edits']:
            assert text.count(e['before'])==e['count'];text=text.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes();assert actual==text.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    print('PASS_EXACT_FOLDED_PLACEMENT_ONLY_SOURCE_CHANGES_NATIVE_GATES_UNCHANGED')
if __name__=='__main__':check()
