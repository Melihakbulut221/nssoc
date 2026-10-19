#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_parent_avdd_v13_streamed_sources import check as baseline
    from check_cdr_source_access_v14_mim_sources import check as physical
    baseline();physical()
    spec=json.loads((ROOT/'scripts/cdr-source-access-v14-streamed-source-delta.json').read_text())
    for d in spec['files']:
        raw=(ROOT/d['baseline_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256'];s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count'];s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes();assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
        assert re.findall(r'[0-9a-f]{64}',raw.decode())==re.findall(r'[0-9a-f]{64}',actual.decode()),'Original dependency hashes changed'
    print('PASS_SOURCE_ACCESS_NATIVE_MODEL_ORIGINAL_BIT_PHASE_LOAD_DEVICE_CURRENT_GATES')
if __name__=='__main__':check()
