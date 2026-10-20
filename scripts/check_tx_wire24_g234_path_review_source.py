#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact replay of the failed g234 waveform, retaining original gate definitions."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    import runpy
    runpy.run_path(str(ROOT/'scripts/check_tx_fast_wire24_path_review_source.py'),run_name='__main__')
    d=json.loads((ROOT/'scripts/tx-wire24-g234-path-review-source-delta.json').read_text())
    raw=(ROOT/d['baseline_path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
    text=raw.decode()
    for edit in d['edits']:
        assert text.count(edit['before'])==edit['count']
        text=text.replace(edit['before'],edit['after'])
    got=(ROOT/d['candidate_path']).read_bytes()
    assert got==text.encode()and hashlib.sha256(got).hexdigest()==d['candidate_sha256']
    p=json.loads((ROOT/'docs/evidence/tx-wire24-g234-nominal-rejected-20261020.json').read_text())
    assert p['run']==39372036289 and p['source_head']=='32087469b74c95b18189650efc422550690ef7e3'
    assert p['summary_sha256']=='e7fd5bd90ee9e4f69233be4a560fe79b4d9ecf75e2d3451104460714a77f3981'
    assert p['parts_sha256']=='0397b23a13452d12bcc605e042f9797187acab7a914de9fb6bf37ab278e66322'
    assert p['returncode']==0 and not p['full_phy_accepted'] and p['source_unchanged']
    assert p['signal_gate']['wrong_sign_samples']==83 and p['signal_gate']['below_100mv_samples']==104
    assert len(p['failed_hbts'])==6 and not p['failed_mos']
    print('PASS_EXACT_G234_FULL_CAPTURE_REPLAY_ORIGINAL_REJECTION_RETAINED')
if __name__=='__main__':check()
