#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Preserve original loaded stimuli/gates and match independent follower geometry."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_retime_trunks_v22_streamed_sources import check as original
    from check_cdr_follower_v23_mim_sources import check as physical
    original();physical()
    for d in json.loads((ROOT/'scripts/cdr-follower-v23-streamed-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        text=raw.decode()
        for e in d['edits']:
            assert text.count(e['before'])==e['count']
            text=text.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==text.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
        assert re.findall(r'[0-9a-f]{64}',raw.decode())==re.findall(r'[0-9a-f]{64}',actual.decode())
    spec=json.loads((ROOT/'docs/evidence/cdr-follower-v23-fullwave-input-20261020.json').read_text())
    assert spec==dict(run=39478830833,source_head='96b626896b0e85c0d9946f633f96de3bd81e0cfe',workflow_path='.github/workflows/cdr-follower-v23-mim-validation-cloud.yml',capture_summary_sha256='c976da9b66f9236dc7cdfb3797d0d7e1d887f2791a326fabb1c02e02148ecd9e')
    planes=json.loads((ROOT/'docs/evidence/cdr-follower-v23-planes-pass-20261020.json').read_text())
    assert planes['run']==39476228473 and planes['summary_sha256']=='e5d641dad96e228bc6725ba633844e158a9b58232f48dc603f22feb39d0191e1'
    assert planes['report']['physical_source']['summary_sha256']=='e9d565ba3bb36c335392f57cb8845c8a6677f04769e56217eec8a7b1e5ff1c56'
    assert len(planes['report']['native_planes']['anchors'])==160
    print('PASS_FOLLOWER476_ORIGINAL_LOADED_STIMULI_AND_GATES_NEW_NATIVE_CENSUS')
if __name__=='__main__':check()
