#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact native selector-v24 census and scope-only audit/composition adaptation."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_follower_v23_mim_sources import check as prior
    from check_cdr_selector_small_v24_mim_capture_sources import check as capture
    prior();capture()
    for d in json.loads((ROOT/'scripts/cdr-selector-small-v24-mim-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        text=raw.decode()
        for e in d['edits']:
            assert text.count(e['before'])==e['count']
            text=text.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==text.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    pin=json.loads((ROOT/'docs/evidence/cdr-selector-small-v24-mim-parent-capture-pass-20261020.json').read_text())
    assert pin['run']==39494983590 and pin['source_head']=='b70e7dfd55449c452669843c7a047f1e97170383'
    assert pin['summary_sha256']=='717fafe89cbf9bac0492628a8b33b888a85223804e6e7b0cf8cc492362766aba'
    assert pin['parts_sha256']=='a1ae0409f07eae4be3a15b0daef0cb54f1b8087e24a148b1033172efe09b4e4b'
    r=pin['report'];got=r['intrinsic_capture_binding']
    assert got['R']==17654 and got['C']==12682 and len(got['native_mim_devices'])==7
    for stage,p in r['extraction_prerequisites'].items():
        b=json.loads((ROOT/('docs/evidence/cdr-selector-small-v24-'+stage+'-pass-20261020.json')).read_text())
        assert b['run']==39493004118 and b['source_head']=='8fa3cac1e15cae9ce307fa53f9642a3474ce24c5'
        assert all(b[k]==p[k]for k in ('summary_sha256','parts_sha256','summary_asset','parts_asset','status'))
        assert b['report']['sources_unchanged']
    binding=json.loads((ROOT/'docs/evidence/cdr-selector-small-v24-binding-pass-20261020.json').read_text())
    assert binding['summary_sha256']==r['model_binding_source']['summary_sha256']
    print('PASS_SELECTOR_V24_476_EXACT17654R12682C_SEVEN_MIM_INPUTS_ORIGINAL_ACCEPTANCE_GATES')
if __name__=='__main__':check()
