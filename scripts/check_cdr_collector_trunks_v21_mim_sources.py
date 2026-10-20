#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Check exact new physical census; preserve native raw R/C/MIM conservation."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_data_v20_mim_sources import check as prior
    from check_cdr_collector_trunks_v21_mim_capture_sources import check as capture
    prior();capture()
    for d in json.loads((ROOT/'scripts/cdr-collector-trunks-v21-mim-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count']
            s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    pin=json.loads((ROOT/'docs/evidence/cdr-collector-trunks-v21-mim-parent-capture-pass-20261020.json').read_text())
    assert pin['run']==39443205735 and pin['source_head']=='01b1874ac35f0c020bc315fa65f67645b3d15790'
    assert pin['summary_sha256']=='b243896419af537caa7c0b08a5f162fff7e42cab3c1430a6e8bf328aeb6446f9'
    assert pin['parts_sha256']=='f7e08050e817e0265582515dbedeb13530a332ba4753e30dd02940cd6c84d1b7'
    got=pin['report']['intrinsic_capture_binding']
    assert got['R']==17674 and got['C']==12704 and len(got['native_mim_devices'])==11
    binding=json.loads((ROOT/'docs/evidence/cdr-collector-trunks-v21-binding-pass-20261020.json').read_text())
    assert binding['run']==39441534722 and binding['source_head']=='f3076e80db3ee4740244583ec37217eddb4ebdc9'
    assert binding['summary_sha256']==pin['report']['model_binding_source']['summary_sha256']
    print('PASS_V21_ACTUAL17674R12704C_ELEVEN_MIM_BINDING_WITH_UNCHANGED_RAW_AUDIT_AND_COMPOSITION_GATES')
if __name__=='__main__':check()
