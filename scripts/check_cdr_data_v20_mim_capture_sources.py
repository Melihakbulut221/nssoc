#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind data4 physical extraction without weakening native MIM checks."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_data_v20_extraction_sources import check as current
    from check_cdr_selector_v19_mim_capture_sources import check as prior
    current();prior()
    for d in json.loads((ROOT/'scripts/cdr-data-v20-mim-capture-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count']
            s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    spec=json.loads((ROOT/'docs/evidence/cdr-data-v20-mim-capture-input-20261020.json').read_text())
    assert spec['run']==39422106468 and spec['source_head']=='63bb44ee4ae7a5b841126ab3253a6975c5c35775'
    assert spec['workflow_path']=='.github/workflows/cdr-data-v20-extraction-cloud.yml'
    assert spec['stages']==['planes','wire-inputs','binding','rc']
    assert spec['parent_summary_sha256']=='e00f439f650c884950ccc232bca90a26958cce39e93606316834a991e945e463'
    print('PASS_V20_FRESH_PHYSICAL_MIM_CAPTURE_ORIGINAL_MASK_AND_TERMINAL_GATES')
if __name__=='__main__':check()
