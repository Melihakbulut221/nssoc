#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Retain original whole-parent MIM mask, intrinsic model and terminal checks."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_retime_bands_v18_extraction_sources import check as current
    from check_cdr_retime_data_v16_mim_capture_sources import check as prior
    current();prior()
    for d in json.loads((ROOT/'scripts/cdr-retime-bands-v18-mim-capture-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count']
            s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    spec=json.loads((ROOT/'docs/evidence/cdr-retime-bands-v18-mim-capture-input-20261020.json').read_text())
    assert spec['run']==39379894690 and spec['source_head']=='a18a9c6c672df04a852ea620052013c488fbc846'
    assert spec['workflow_path']=='.github/workflows/cdr-retime-bands-v18-extraction-cloud.yml'
    assert spec['stages']==['planes','wire-inputs','binding','rc']
    assert spec['parent_summary_sha256']=='9d7300c3965d2a9487882e1a569cf17c5328acc130bbf2dc0ee9c993e0c210d3'
    print('PASS_V18_FRESH_PHYSICAL_MIM_CAPTURE_ORIGINAL_MASK_AND_TERMINAL_GATES')
if __name__=='__main__':check()
