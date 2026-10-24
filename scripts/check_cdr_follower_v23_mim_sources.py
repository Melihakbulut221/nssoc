#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact native follower census and scope-only audit/composition adaptation."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_retime_trunks_v22_mim_sources import check as prior
    from check_cdr_follower_v23_mim_capture_sources import check as capture
    prior();capture()
    for d in json.loads((ROOT/'scripts/cdr-follower-v23-mim-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        text=raw.decode()
        for e in d['edits']:
            assert text.count(e['before'])==e['count']
            text=text.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==text.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    pin=json.loads((ROOT/'docs/evidence/cdr-follower-v23-mim-parent-capture-pass-20261020.json').read_text())
    assert pin['run']==39477040744 and pin['source_head']=='b66dcdb3d72b5fcbc1055b2f05247ca2a6e791c3'
    assert pin['summary_sha256']=='c976da9b66f9236dc7cdfb3797d0d7e1d887f2791a326fabb1c02e02148ecd9e'
    assert pin['parts_sha256']=='99c49f6cd70b99b1260703fdd5e95a1e861ab1c11f14627b08b48a9ce201ef9d'
    r=pin['report'];got=r['intrinsic_capture_binding']
    assert got['R']==17654 and got['C']==12682 and len(got['native_mim_devices'])==7
    for stage,p in r['extraction_prerequisites'].items():
        b=json.loads((ROOT/('docs/evidence/cdr-follower-v23-'+stage+'-pass-20261020.json')).read_text())
        assert b['run']==39476228473 and b['source_head']=='bd0fb138cc52ac6fd95d10c0a8ef9b971077044e'
        assert all(b[k]==p[k]for k in ('summary_sha256','parts_sha256','summary_asset','parts_asset','status'))
        assert b['report']['sources_unchanged']
    binding=json.loads((ROOT/'docs/evidence/cdr-follower-v23-binding-pass-20261020.json').read_text())
    assert binding['summary_sha256']==r['model_binding_source']['summary_sha256']
    print('PASS_FOLLOWER476_EXACT17654R12682C_SEVEN_MIM_INPUTS_ORIGINAL_ACCEPTANCE_GATES')
if __name__=='__main__':check()
