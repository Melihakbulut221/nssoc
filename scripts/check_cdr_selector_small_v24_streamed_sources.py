#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Preserve original loaded stimuli/gates and match actual smaller-selector geometry."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_follower_v23_streamed_sources import check as original
    from check_cdr_selector_small_v24_mim_sources import check as physical
    original();physical()
    for d in json.loads((ROOT/'scripts/cdr-selector-small-v24-streamed-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        text=raw.decode()
        for e in d['edits']:
            assert text.count(e['before'])==e['count']
            text=text.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==text.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
        assert re.findall(r'[0-9a-f]{64}',raw.decode())==re.findall(r'[0-9a-f]{64}',actual.decode())
    spec=json.loads((ROOT/'docs/evidence/cdr-selector-small-v24-fullwave-input-20261020.json').read_text())
    assert spec=={'run': 39495976408, 'source_head': 'f61558dc1c125b20caa5b3c6d2d1ad82619e3998', 'workflow_path': '.github/workflows/cdr-selector-small-v24-mim-validation-cloud.yml', 'capture_summary_sha256': '717fafe89cbf9bac0492628a8b33b888a85223804e6e7b0cf8cc492362766aba'}
    planes=json.loads((ROOT/'docs/evidence/cdr-selector-small-v24-planes-pass-20261020.json').read_text())
    assert planes['run']==39493004118 and planes['summary_sha256']=='11c8c4e269854eea146ee484672ed9117d745b6b46cbefc6da375109f1306836'
    assert planes['report']['physical_source']['summary_sha256']=='f6575268cb8ff39408803e747b63788d15d67f639ea8f207a13e4c4140e9205b'
    assert len(planes['report']['native_planes']['anchors'])==160
    print('PASS_SELECTOR_V24_476_ORIGINAL_LOADED_STIMULI_AND_GATES_NEW_NATIVE_CENSUS')
if __name__=='__main__':check()
