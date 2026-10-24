#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Keep original full-wave stimuli, phases, loads and device gates byte-identical."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_retime_bands_v18_streamed_sources import check as original
    from check_cdr_selector_v19_mim_sources import check as physical
    original();physical()
    for d in json.loads((ROOT/'scripts/cdr-selector-v19-streamed-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count']
            s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
        assert re.findall(r'[0-9a-f]{64}',raw.decode())==re.findall(r'[0-9a-f]{64}',actual.decode()),'Original tool/model dependency hashes changed'
    spec=json.loads((ROOT/'docs/evidence/cdr-selector-v19-fullwave-input-20261020.json').read_text())
    assert spec['run']==39399444981 and spec['source_head']=='7b452101d3d64572a1a9b58a0f1f1e1844f11084'
    assert spec['workflow_path']=='.github/workflows/cdr-selector-v19-mim-validation-cloud.yml'
    assert spec['capture_summary_sha256']=='d3ecd598c271fa0b7771b5287267cf33c088d2a328c374931dac793dc84362a8'
    planes=json.loads((ROOT/'docs/evidence/cdr-selector-v19-planes-pass-20261020.json').read_text())
    assert planes['run']==39396626134 and planes['summary_sha256']=='14af74bce3e95756d289c7c1e82a81bd89e9fb8631a28ca71630792e928cbd83'
    assert planes['report']['physical_source']['summary_sha256']=='8bd5a68094ea63cfab23f5e09b31e3ebeb1f8798f981458666507cad1d1b4361'
    print('PASS_V19_FRESH_GEOMETRY_ORIGINAL_FULL_BITS_PHASES_LOADS_AND_DEVICE_GATES')
if __name__=='__main__':check()
