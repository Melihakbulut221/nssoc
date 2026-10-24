#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_tx_v5_timing_priority_sources import check as baseline
    baseline()
    spec=json.loads((ROOT/'scripts/tx-fast-wire24-source-pins.json').read_text())
    for path,digest in spec['files'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest
    p=json.loads((ROOT/'docs/evidence/tx-v5-timing-priority-physical-pass-20261019.json').read_text())
    assert p['run']==spec['baseline_run']and p['summary_sha256']==spec['baseline_summary_sha256']
    assert p['outputs']['verify-tree32.py']=='264de4e33d7617dd1f4da674577c6297b17f8da634b80357137c10fde9a5ff23'
    print('PASS_NATIVE_FAST_WIRE24_SOURCE_PINS_ORIGINAL_PHYSICAL_GATES')
if __name__=='__main__':check()
