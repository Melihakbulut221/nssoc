#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind selector4 physical extraction without weakening native MIM checks."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_selector_v19_extraction_sources import check as current
    from check_cdr_retime_bands_v18_mim_capture_sources import check as prior
    current();prior()
    for d in json.loads((ROOT/'scripts/cdr-selector-v19-mim-capture-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count']
            s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    spec=json.loads((ROOT/'docs/evidence/cdr-selector-v19-mim-capture-input-20261020.json').read_text())
    assert spec['run']==39396626134 and spec['source_head']=='8789725da417537488b307aa0f76c08624822ac2'
    assert spec['workflow_path']=='.github/workflows/cdr-selector-v19-extraction-cloud.yml'
    assert spec['stages']==['planes','wire-inputs','binding','rc']
    assert spec['parent_summary_sha256']=='8bd5a68094ea63cfab23f5e09b31e3ebeb1f8798f981458666507cad1d1b4361'
    print('PASS_V19_FRESH_PHYSICAL_MIM_CAPTURE_ORIGINAL_MASK_AND_TERMINAL_GATES')
if __name__=='__main__':check()
