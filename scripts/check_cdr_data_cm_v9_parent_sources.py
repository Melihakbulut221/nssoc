#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import copy,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_collector_v8_parent_sources import check as prior
    from check_cdr_data_cm_v5_sources import check as data
    prior();data()
    for d in json.loads((ROOT/'scripts/cdr-data-cm-v9-parent-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256'];s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count'];s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes();assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    import cdr_retimed_collector_v8_parent_plan as old
    import cdr_retimed_data_cm_v9_parent_plan as new
    a=copy.deepcopy(old.build());b=new.build()
    a['types']['data']['top']='nssoc_cdr_data_buffer_cm_layout_v5'
    for before,after in [('cdr_retimed_parallel_pd_vi_v3.spice','cdr_retimed_data_cm_pd_vi_v9.spice'),('cdr_sampled_compare_buffered_v4.spice','cdr_sampled_compare_data_cm_v5.spice')]:
        del a['source_sha256'][before]
        a['source_sha256'][after]=hashlib.sha256((ROOT/'hw/soc/analog/pcie'/after).read_bytes()).hexdigest()
    assert a==b
    assert len(new.controls()['rejected'])==6
    before=json.loads((ROOT/'docs/evidence/cdr-retimed-collector-v8-parent-children-20261019.json').read_text())['children']
    after=json.loads((ROOT/'docs/evidence/cdr-retimed-data-cm-v9-parent-children-20261019.json').read_text())['children']
    assert set(before)==set(after)and all(before[k]==after[k]for k in before if k!='data')
    assert after['data']['run']==39204220474
    print('PASS_ONLY_TWO_PHYSICAL_DATA_HEADERS_CHANGED_UNCHANGED_484_DEVICE_PARENT_GATES')
if __name__=='__main__':check()
