#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_via_rich_v7_mim_audit_sources import check as prior
    prior()
    from check_cdr_collector_v8_mim_capture_sources import check as capture
    capture()
    for d in json.loads((ROOT/'scripts/cdr-collector-v8-mim-audit-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count']
            s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==s.encode() and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    print('PASS_EXACT_LOCAL484_MIM_AUDIT_DELTA_ORIGINAL22_FAULT_GATES_RETAINED')
if __name__=='__main__':check()
