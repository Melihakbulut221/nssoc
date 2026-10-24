#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Check exact new physical census; preserve native raw R/C/MIM conservation."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_selector_v19_mim_sources import check as prior
    from check_cdr_data_v20_mim_capture_sources import check as capture
    prior();capture()
    for d in json.loads((ROOT/'scripts/cdr-data-v20-mim-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count']
            s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    pin=json.loads((ROOT/'docs/evidence/cdr-data-v20-mim-parent-capture-pass-20261020.json').read_text())
    assert pin['run']==39424942579 and pin['source_head']=='a1d92377ce17f2589e2c42eea729e4015203b681'
    assert pin['summary_sha256']=='928261bc7efd065100b19687d8ede3008dd1e086ae89ebee3296d89a981dd740'
    assert pin['parts_sha256']=='8f703f2dc8b410341b74258be0cee26fe7a2cd5ff1a17a09388c5b07a96f9a0f'
    got=pin['report']['intrinsic_capture_binding']
    assert got['R']==17674 and got['C']==12712 and len(got['native_mim_devices'])==11
    binding=json.loads((ROOT/'docs/evidence/cdr-data-v20-binding-pass-20261020.json').read_text())
    assert binding['run']==39423976647 and binding['source_head']=='12dff65a6dfcf2c6b6df044f8e6ef9718398c8e2'
    assert binding['summary_sha256']==pin['report']['model_binding_source']['summary_sha256']
    print('PASS_V20_ACTUAL17674R12712C_ELEVEN_MIM_BINDING_WITH_UNCHANGED_RAW_AUDIT_AND_COMPOSITION_GATES')
if __name__=='__main__':check()
