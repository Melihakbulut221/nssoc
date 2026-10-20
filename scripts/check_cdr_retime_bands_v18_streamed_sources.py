#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Keep original full-wave stimuli, phases, loads and device gates byte-identical."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_retime_data_v16_streamed_sources import check as original
    from check_cdr_retime_bands_v18_mim_sources import check as physical
    original();physical()
    for d in json.loads((ROOT/'scripts/cdr-retime-bands-v18-streamed-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count']
            s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
        assert re.findall(r'[0-9a-f]{64}',raw.decode())==re.findall(r'[0-9a-f]{64}',actual.decode()),'Original tool/model dependency hashes changed'
    spec=json.loads((ROOT/'docs/evidence/cdr-retime-bands-v18-fullwave-input-20261020.json').read_text())
    assert spec['run']==39380893611 and spec['source_head']=='762861b4b1b13b5baf6c9634a87a731ab6e613fa'
    assert spec['workflow_path']=='.github/workflows/cdr-retime-bands-v18-mim-validation-cloud.yml'
    assert spec['capture_summary_sha256']=='c915132994984d86ca8d28609e7ff3fc86a6891203ce8906e9dc2e567bc01602'
    planes=json.loads((ROOT/'docs/evidence/cdr-retime-bands-v18-planes-pass-20261020.json').read_text())
    assert planes['run']==39379894690 and planes['summary_sha256']=='76f407c5fac881f144d09198eef031ce0672275f9992c9b8453731f0e8728a76'
    assert planes['report']['physical_source']['summary_sha256']=='9d7300c3965d2a9487882e1a569cf17c5328acc130bbf2dc0ee9c993e0c210d3'
    print('PASS_V18_FRESH_GEOMETRY_ORIGINAL_FULL_BITS_PHASES_LOADS_AND_DEVICE_GATES')
if __name__=='__main__':check()
