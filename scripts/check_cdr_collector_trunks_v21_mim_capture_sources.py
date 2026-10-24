#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind collector-trunk physical extraction without weakening native MIM checks."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_collector_trunks_v21_extraction_sources import check as current
    from check_cdr_data_v20_mim_capture_sources import check as prior
    current();prior()
    for d in json.loads((ROOT/'scripts/cdr-collector-trunks-v21-mim-capture-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count']
            s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    spec=json.loads((ROOT/'docs/evidence/cdr-collector-trunks-v21-mim-capture-input-20261020.json').read_text())
    assert spec['run']==39441534722 and spec['source_head']=='f3076e80db3ee4740244583ec37217eddb4ebdc9'
    assert spec['workflow_path']=='.github/workflows/cdr-collector-trunks-v21-extraction-cloud.yml'
    assert spec['stages']==['planes','wire-inputs','binding','rc']
    assert spec['parent_summary_sha256']=='ae578b3ecf11a68193c310a0a496d47c959d30a411f7c6803aeb04f1e5dfff0d'
    print('PASS_V21_FRESH_PHYSICAL_MIM_CAPTURE_ORIGINAL_MASK_AND_TERMINAL_GATES')
if __name__=='__main__':check()
