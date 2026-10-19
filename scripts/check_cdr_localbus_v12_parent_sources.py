#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind only the native local-bus leaf change; retain all parent circuit/gates."""
import copy,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_folded_v11_parent_sources import check as prior
    from check_cdr_sampler_localbus_sources import check as leaf
    prior();leaf()
    for d in json.loads((ROOT/'scripts/cdr-localbus-v12-parent-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256'];s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count'];s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes();assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    import cdr_retimed_folded_v11_parent_plan as old
    import cdr_retimed_localbus_v12_parent_plan as new
    a=copy.deepcopy(old.build());a['types']['sampler']['top']='nssoc_rx_sampler_localbus_layout_v15'
    assert a==new.build()and len(new.controls()['rejected'])==6
    before=json.loads((ROOT/'docs/evidence/cdr-retimed-folded-v11-parent-children-20261019.json').read_text())['children']
    after=json.loads((ROOT/'docs/evidence/cdr-retimed-localbus-v12-parent-children-20261019.json').read_text())['children']
    assert set(before)==set(after)and all(before[k]==after[k]for k in before if k!='sampler')
    assert after['sampler']['run']==39247903547 and after['sampler']['source_head']=='d9ed1af569fafda42ee686fdede28f2a5c263628'
    print('PASS_ONLY_LOCALBUS_SAMPLER_VIEW_CHANGED_ALL_CIRCUITS_AND_PARENT_GATES_UNCHANGED')
if __name__=='__main__':check()
