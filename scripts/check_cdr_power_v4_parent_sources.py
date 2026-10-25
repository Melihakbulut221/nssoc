#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import hashlib,json,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_parallel_v3_parent_sources import check as prior
    prior()
    for d in json.loads((ROOT/'scripts/cdr-power-v4-parent-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256'];s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count'];s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes();assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    import cdr_retimed_parallel_v3_parent_plan as old
    import cdr_retimed_power_v4_parent_plan as new
    a=copy.deepcopy(old.build());b=new.build();a['types']['xor']['top']='nssoc_cdr_xor_power_access_layout_v4';assert a==b
    c=new.controls();assert c['plan']['expected_devices']==484 and len(c['rejected'])==6
    before=json.loads((ROOT/'docs/evidence/cdr-retimed-parallel-v3-parent-children-20261018.json').read_text())['children']
    after=json.loads((ROOT/'docs/evidence/cdr-retimed-power-v4-parent-children-20261018.json').read_text())['children']
    assert set(before)==set(after) and all(before[k]==after[k]for k in before if k!='xor')
    assert after['xor']['run']==39137767974
    print('PASS_ONLY_VERIFIED_XOR_POWER_ACCESS_MASTER_CHANGED_IN_PD484')
if __name__=='__main__':check()
