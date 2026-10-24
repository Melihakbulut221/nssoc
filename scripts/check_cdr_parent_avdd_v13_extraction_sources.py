#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_localbus_v12_parent_sources import check as parent
    from check_cdr_localbus_v12_extraction_sources import check as baseline
    parent();baseline()
    for d in json.loads((ROOT/'scripts/cdr-parent-avdd-v13-extraction-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256'];s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count'];s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes();assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    print('PASS_NATIVE_AVDD_PARENT_SOURCE_ORIGINAL_PLANES_TERMINALS_BINDING_AND_RC_FAULT_GATES')
if __name__=='__main__':check()
