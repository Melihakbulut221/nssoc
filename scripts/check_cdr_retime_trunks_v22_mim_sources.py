#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Check exact new physical census; preserve native raw R/C/MIM conservation."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_collector_trunks_v21_mim_sources import check as prior
    from check_cdr_retime_trunks_v22_mim_capture_sources import check as capture
    prior();capture()
    for d in json.loads((ROOT/'scripts/cdr-retime-trunks-v22-mim-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count']
            s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    pin=json.loads((ROOT/'docs/evidence/cdr-retime-trunks-v22-mim-parent-capture-pass-20261020.json').read_text())
    assert pin['run']==39456445937 and pin['source_head']=='7f458f0c6cc7cf330214a56bba36a1a0c441984b'
    assert pin['summary_sha256']=='c425b1cd54e2426848910d3261edd3fd7d60f596e95511cb072569dec3e8ed32'
    assert pin['parts_sha256']=='2460dcd82c02605172052c74c58728535aac77c5a080e5a7a0062a543d8d6102'
    got=pin['report']['intrinsic_capture_binding']
    assert got['R']==17674 and got['C']==12700 and len(got['native_mim_devices'])==11
    binding=json.loads((ROOT/'docs/evidence/cdr-retime-trunks-v22-binding-pass-20261020.json').read_text())
    assert binding['run']==39455570367 and binding['source_head']=='8d7d27c06bfd1d69bbc4a916aecf0028f44ebf33'
    assert binding['summary_sha256']==pin['report']['model_binding_source']['summary_sha256']
    print('PASS_V22_ACTUAL17674R12700C_ELEVEN_MIM_BINDING_WITH_UNCHANGED_RAW_AUDIT_AND_COMPOSITION_GATES')
if __name__=='__main__':check()
