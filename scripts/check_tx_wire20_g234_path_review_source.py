#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Reproduce rejected wire20 native capture with the original full gate reader."""
import hashlib,json,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
 runpy.run_path(str(ROOT/'scripts/check_tx_wire24_g234_path_review_source.py'),run_name='__main__')
 d=json.loads((ROOT/'scripts/tx-wire20-g234-path-review-source-delta.json').read_text())
 raw=(ROOT/d['baseline_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
 text=raw.decode()
 for e in d['edits']:
  assert text.count(e['before'])==e['count'];text=text.replace(e['before'],e['after'])
 got=(ROOT/d['candidate_path']).read_bytes()
 assert got==text.encode()and hashlib.sha256(got).hexdigest()==d['candidate_sha256']
 p=json.loads((ROOT/'docs/evidence/tx-wire20-g234-nominal-rejected-20261020.json').read_text())
 assert p['run']==39409002976 and p['source_head']=='858f0b77b57389335ffd802e9366d789d636a56d'
 assert p['summary_sha256']=='4a388293d6dec1f037a4b3cfe6009e0035d0e4ec9b5cf21afd345c9d73c2aad9'
 assert p['parts_sha256']=='5268273237de28625e0237d1f9f7c81e15b9914bd8ed82d49feef8bca7fcd8a2'
 assert p['returncode']==0 and p['source_unchanged']and not p['full_phy_accepted']
 assert p['signal_gate']['wrong_sign_samples']==79 and p['signal_gate']['below_100mv_samples']==97
 assert len(p['failed_hbts'])==6 and not p['failed_mos']
 print('PASS_EXACT_WIRE20_CAPTURE_REPLAY_WITH_ORIGINAL_FULL_ENGINEERING_GATES')
if __name__=='__main__':check()
