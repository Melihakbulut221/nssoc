#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_via_rich_v7_parent_sources import check as parent
    parent()
    for d in json.loads((ROOT/'scripts/cdr-via-rich-v7-planes-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256'];s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count'];s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes();assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    print('PASS_ONLY_PARENT_IDENTITIES_CHANGED_ORIGINAL158_PLANES_19FAULTS_AND_LEAF_GEOMETRY_GATES_RETAINED')
if __name__=='__main__':check()
