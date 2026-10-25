#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Keep original full-wave stimuli, phases, loads and device gates byte-identical."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_selector_v19_streamed_sources import check as original
    from check_cdr_data_v20_mim_sources import check as physical
    original();physical()
    for d in json.loads((ROOT/'scripts/cdr-data-v20-streamed-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count']
            s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
        assert re.findall(r'[0-9a-f]{64}',raw.decode())==re.findall(r'[0-9a-f]{64}',actual.decode()),'Original tool/model dependency hashes changed'
    spec=json.loads((ROOT/'docs/evidence/cdr-data-v20-fullwave-input-20261020.json').read_text())
    assert spec['run']==39425717815 and spec['source_head']=='271d7849a81ae07c89f18e96cf17e938deeab90e'
    assert spec['workflow_path']=='.github/workflows/cdr-data-v20-mim-validation-cloud.yml'
    assert spec['capture_summary_sha256']=='928261bc7efd065100b19687d8ede3008dd1e086ae89ebee3296d89a981dd740'
    planes=json.loads((ROOT/'docs/evidence/cdr-data-v20-planes-pass-20261020.json').read_text())
    assert planes['run']==39423976647 and planes['summary_sha256']=='491eb2d5e23cedad1469c3006f507a25478395a3396bf3ca839fa25954560073'
    assert planes['report']['physical_source']['summary_sha256']=='e00f439f650c884950ccc232bca90a26958cce39e93606316834a991e945e463'
    print('PASS_V20_FRESH_GEOMETRY_ORIGINAL_FULL_BITS_PHASES_LOADS_AND_DEVICE_GATES')
if __name__=='__main__':check()
