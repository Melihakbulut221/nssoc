#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_retime_data_v16_streamed_sources import check as baseline
    from check_cdr_retime_data_v16_mim_sources import check as physical
    baseline();physical()
    spec=json.loads((ROOT/'scripts/cdr-retime-rebalance-v17-source-delta.json').read_text())
    for d in spec['files']:
        raw=(ROOT/d['baseline_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256'];s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count'];s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes();assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
        assert re.findall(r'[0-9a-f]{64}',raw.decode())==re.findall(r'[0-9a-f]{64}',actual.decode()),'Original dependency hashes changed'
    for path,digest in spec['pinned_sources'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest
    print('PASS_CDR_REBALANCE_DIAGNOSTIC_ONLY_ORIGINAL_BIT_PHASE_LOAD_DEVICE_CURRENT_GATES')
if __name__=='__main__':check()
