#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import copy,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_data_cm_v9_parent_sources import check as prior
    from check_cdr_retime_drive_sources import check as leaves
    prior();leaves()
    for d in json.loads((ROOT/'scripts/cdr-input-drive-v10-parent-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256'];s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count'];s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes();assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    import cdr_retimed_data_cm_v9_parent_plan as old
    import cdr_retimed_input_drive_v10_parent_plan as new
    a=copy.deepcopy(old.build());b=new.build()
    a['types']['sampler']['top']='nssoc_rx_sampler_input_drive_layout_v13'
    a['types']['rc_retime']['top']='nssoc_cdr_retime_drive_feedforward_layout_v2'
    for before,after in [('cdr_retimed_data_cm_pd_vi_v9.spice','cdr_retimed_input_drive_pd_vi_v10.spice'),('rx_sampler_parallel_drive_v8.spice','rx_sampler_input_drive_v13.spice')]:
        del a['source_sha256'][before]
        a['source_sha256'][after]=hashlib.sha256((ROOT/'hw/soc/analog/pcie'/after).read_bytes()).hexdigest()
    assert a==b and len(new.controls()['rejected'])==6
    before=json.loads((ROOT/'docs/evidence/cdr-retimed-data-cm-v9-parent-children-20261019.json').read_text())['children']
    after=json.loads((ROOT/'docs/evidence/cdr-retimed-input-drive-v10-parent-children-20261019.json').read_text())['children']
    assert set(before)==set(after)and all(before[k]==after[k]for k in before if k not in ('sampler','rc_retime'))
    assert after['sampler']['run']==39210361374 and after['rc_retime']['run']==39209600711
    print('PASS_ONLY_INPUT_DRIVE_LEAVES_CHANGED_ORIGINAL_PARENT_GATES_AND_THREE_NEW_FAULTS')
if __name__=='__main__':check()
