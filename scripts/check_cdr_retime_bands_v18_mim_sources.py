#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Check exact new physical census; preserve native raw R/C/MIM conservation."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_retime_data_v16_mim_sources import check as prior
    from check_cdr_retime_bands_v18_mim_capture_sources import check as capture
    prior();capture()
    for d in json.loads((ROOT/'scripts/cdr-retime-bands-v18-mim-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count']
            s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    pin=json.loads((ROOT/'docs/evidence/cdr-retime-bands-v18-mim-parent-capture-pass-20261020.json').read_text())
    assert pin['run']==39380388968 and pin['source_head']=='f1448bef22859409498128965891c8fff3910bff'
    assert pin['summary_sha256']=='c915132994984d86ca8d28609e7ff3fc86a6891203ce8906e9dc2e567bc01602'
    assert pin['parts_sha256']=='b171acef20a1da00cdb6cff389274d0c6bbcdace0e7c6418ec67ee5b0abac274'
    got=pin['report']['intrinsic_capture_binding']
    assert got['R']==17674 and got['C']==12712 and len(got['native_mim_devices'])==11
    binding=json.loads((ROOT/'docs/evidence/cdr-retime-bands-v18-binding-pass-20261020.json').read_text())
    assert binding['run']==39379894690 and binding['source_head']=='a18a9c6c672df04a852ea620052013c488fbc846'
    assert binding['summary_sha256']==pin['report']['model_binding_source']['summary_sha256']
    print('PASS_V18_ACTUAL17674R12712C_ELEVEN_MIM_BINDING_WITH_UNCHANGED_RAW_AUDIT_AND_COMPOSITION_GATES')
if __name__=='__main__':check()
