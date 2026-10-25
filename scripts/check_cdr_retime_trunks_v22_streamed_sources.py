#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Keep original full-wave stimuli, phases, loads and device gates byte-identical."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_collector_trunks_v21_streamed_sources import check as original
    from check_cdr_retime_trunks_v22_mim_sources import check as physical
    original();physical()
    for d in json.loads((ROOT/'scripts/cdr-retime-trunks-v22-streamed-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count']
            s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
        assert re.findall(r'[0-9a-f]{64}',raw.decode())==re.findall(r'[0-9a-f]{64}',actual.decode()),'Original tool/model dependency hashes changed'
    spec=json.loads((ROOT/'docs/evidence/cdr-retime-trunks-v22-fullwave-input-20261020.json').read_text())
    assert spec['run']==39457813038 and spec['source_head']=='2892d7566320445591863f83f022527795fb8cb5'
    assert spec['workflow_path']=='.github/workflows/cdr-retime-trunks-v22-mim-validation-cloud.yml'
    assert spec['capture_summary_sha256']=='c425b1cd54e2426848910d3261edd3fd7d60f596e95511cb072569dec3e8ed32'
    planes=json.loads((ROOT/'docs/evidence/cdr-retime-trunks-v22-planes-pass-20261020.json').read_text())
    assert planes['run']==39455570367 and planes['summary_sha256']=='84cc3c29300d2483a3bc24035fbddc42f5da3c95d619d697f06397ea93000854'
    assert planes['report']['physical_source']['summary_sha256']=='0425f0b6cbfdae35240d2e99a0faea3f75b114f2e4974639d804556a36ccb266'
    print('PASS_V22_FRESH_GEOMETRY_ORIGINAL_FULL_BITS_PHASES_LOADS_AND_DEVICE_GATES')
if __name__=='__main__':check()
