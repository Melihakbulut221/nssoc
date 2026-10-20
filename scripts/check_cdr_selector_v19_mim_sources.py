#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Check exact new physical census; preserve native raw R/C/MIM conservation."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_retime_bands_v18_mim_sources import check as prior
    from check_cdr_selector_v19_mim_capture_sources import check as capture
    prior();capture()
    for d in json.loads((ROOT/'scripts/cdr-selector-v19-mim-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count']
            s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    pin=json.loads((ROOT/'docs/evidence/cdr-selector-v19-mim-parent-capture-pass-20261020.json').read_text())
    assert pin['run']==39397118280 and pin['source_head']=='0c06e3e9c600006fdd9b7ac7639ce617d3f93ae1'
    assert pin['summary_sha256']=='d3ecd598c271fa0b7771b5287267cf33c088d2a328c374931dac793dc84362a8'
    assert pin['parts_sha256']=='dee5a1e10311a7c6633305fc22f556d38922b8bd0165403b49c0485deec72a40'
    got=pin['report']['intrinsic_capture_binding']
    assert got['R']==17674 and got['C']==12712 and len(got['native_mim_devices'])==11
    binding=json.loads((ROOT/'docs/evidence/cdr-selector-v19-binding-pass-20261020.json').read_text())
    assert binding['run']==39396626134 and binding['source_head']=='8789725da417537488b307aa0f76c08624822ac2'
    assert binding['summary_sha256']==pin['report']['model_binding_source']['summary_sha256']
    print('PASS_V19_ACTUAL17674R12712C_ELEVEN_MIM_BINDING_WITH_UNCHANGED_RAW_AUDIT_AND_COMPOSITION_GATES')
if __name__=='__main__':check()
