#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import copy,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_local_v5_parent_sources import check as prior
    from check_cdr_sampler_strapped_sources import check as sampler
    prior();sampler()
    for d in json.loads((ROOT/'scripts/cdr-strapped-v6-parent-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256'];s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count'];s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes();assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    import cdr_retimed_local_v5_parent_plan as old
    import cdr_retimed_strapped_v6_parent_plan as new
    a=copy.deepcopy(old.build());a['types']['sampler']['top']='nssoc_rx_sampler_strapped_layout_v10';assert a==new.build()
    assert len(new.controls()['rejected'])==6
    before=json.loads((ROOT/'docs/evidence/cdr-retimed-local-v5-parent-children-20261018.json').read_text())['children']
    after=json.loads((ROOT/'docs/evidence/cdr-retimed-strapped-v6-parent-children-20261018.json').read_text())['children']
    assert set(before)==set(after)and all(before[k]==after[k]for k in before if k!='sampler')
    assert after['sampler']['run']==39151562771
    print('PASS_FOUR_NATIVE_STRAPPED_SAMPLERS_AND_ORIGINAL_FULL484_PHYSICAL_GATES')
if __name__=='__main__':check()
