#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_hybrid_v2_parent_sources import check as original_check
    original_check()
    for row in json.loads((ROOT/'scripts/cdr-parallel-v3-parent-source-delta.json').read_text())['files']:
        b=(ROOT/row['baseline_path']).read_bytes();assert hashlib.sha256(b).hexdigest()==row['baseline_sha256'];s=b.decode()
        for e in row['edits']:
            assert s.count(e['before'])==e['count'];s=s.replace(e['before'],e['after'])
        b=(ROOT/row['candidate_path']).read_bytes();assert b==s.encode()and hashlib.sha256(b).hexdigest()==row['candidate_sha256']
    import cdr_retimed_parallel_v3_parent_plan as plan
    r=plan.controls();assert r['plan']['expected_devices']==484 and len(r['rejected'])==6
    assert r['plan']['primitive_census']==dict(npn13g2=116,sg13_lv_nmos=46,rppd=102,cap_cmim=11,ptap1=209)
    print('PASS_EXACT_PARALLEL484_PARENT_DELTAS_AND_SIX_SOURCE_CONTROLS')
if __name__=='__main__':check()
