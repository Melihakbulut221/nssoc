#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import copy,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_input_drive_v10_parent_sources import check as prior
    from check_cdr_sampler_folded_sources import check as leaf
    prior();leaf()
    for d in json.loads((ROOT/'scripts/cdr-folded-v11-parent-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256'];s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count'];s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes();assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    import cdr_retimed_input_drive_v10_parent_plan as old
    import cdr_retimed_folded_v11_parent_plan as new
    a=copy.deepcopy(old.build());a['types']['sampler']['top']='nssoc_rx_sampler_folded_layout_v14'
    assert a==new.build()and len(new.controls()['rejected'])==6
    before=json.loads((ROOT/'docs/evidence/cdr-retimed-input-drive-v10-parent-children-20261019.json').read_text())['children']
    after=json.loads((ROOT/'docs/evidence/cdr-retimed-folded-v11-parent-children-20261019.json').read_text())['children']
    assert set(before)==set(after)and all(before[k]==after[k]for k in before if k!='sampler')
    assert after['sampler']['run']==39232996365 and after['sampler']['source_head']=='6fe7a218daeb5d059a00dfe82f4211d34afadcd2'
    print('PASS_ONLY_FOLDED_SAMPLER_PHYSICAL_VIEW_CHANGED_ALL_CIRCUITS_AND_PARENT_GATES_UNCHANGED')
if __name__=='__main__':check()
