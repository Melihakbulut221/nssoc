#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import copy,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_via_rich_v7_parent_sources import check as prior
    from check_cdr_sampler_collector_access_sources import check as sampler
    prior();sampler()
    for d in json.loads((ROOT/'scripts/cdr-collector-v8-parent-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256'];s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count'];s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes();assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    import cdr_retimed_via_rich_v7_parent_plan as old
    import cdr_retimed_collector_v8_parent_plan as new
    a=copy.deepcopy(old.build());a['types']['sampler']['top']='nssoc_rx_sampler_collector_access_layout_v12';assert a==new.build()
    assert len(new.controls()['rejected'])==6
    before=json.loads((ROOT/'docs/evidence/cdr-retimed-via-rich-v7-parent-children-20261018.json').read_text())['children']
    after=json.loads((ROOT/'docs/evidence/cdr-retimed-collector-v8-parent-children-20261019.json').read_text())['children']
    assert set(before)==set(after)and all(before[k]==after[k]for k in before if k!='sampler')
    assert after['sampler']['run']==39170920428
    print('PASS_FOUR_COLLECTOR_ACCESS_SAMPLERS_UNCHANGED_FULL484_PHYSICAL_GATES')
if __name__=='__main__':check()
