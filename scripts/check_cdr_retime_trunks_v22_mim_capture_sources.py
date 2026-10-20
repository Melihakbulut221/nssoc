#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind retime-input physical extraction without weakening native MIM checks."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_retime_trunks_v22_extraction_sources import check as current
    from check_cdr_collector_trunks_v21_mim_capture_sources import check as prior
    current();prior()
    for d in json.loads((ROOT/'scripts/cdr-retime-trunks-v22-mim-capture-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count']
            s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    spec=json.loads((ROOT/'docs/evidence/cdr-retime-trunks-v22-mim-capture-input-20261020.json').read_text())
    assert spec['run']==39455570367 and spec['source_head']=='8d7d27c06bfd1d69bbc4a916aecf0028f44ebf33'
    assert spec['workflow_path']=='.github/workflows/cdr-retime-trunks-v22-extraction-cloud.yml'
    assert spec['stages']==['planes','wire-inputs','binding','rc']
    assert spec['parent_summary_sha256']=='0425f0b6cbfdae35240d2e99a0faea3f75b114f2e4974639d804556a36ccb266'
    print('PASS_V22_FRESH_PHYSICAL_MIM_CAPTURE_ORIGINAL_MASK_AND_TERMINAL_GATES')
if __name__=='__main__':check()
