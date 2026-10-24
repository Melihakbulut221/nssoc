#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Only source-selection/continuation orchestration changes; exact native DRT retained."""
import hashlib,json
from pathlib import Path
def check():
    root=Path(__file__).resolve().parents[1]
    sha=lambda b:hashlib.sha256(b).hexdigest()
    m=json.loads((root/'scripts/mainchip-route12-drt-continuation-delta.json').read_text())
    for p,h in m['protected'].items():assert sha((root/p).read_bytes())==h,p
    old=(root/m['baseline_path']).read_bytes();assert sha(old)==m['baseline_sha256']
    text=old.decode();parts=[];cursor=0
    for change in m['changes']:
        lo,hi=change['start'],change['end'];assert cursor<=lo<=hi<=len(text)
        parts.extend([text[cursor:lo],change['replacement']]);cursor=hi
    parts.append(text[cursor:]);new=(root/m['candidate_path']).read_bytes()
    assert new==''.join(parts).encode()and sha(new)==m['candidate_sha256']
    print('PASS_BOUND_CONTINUATION_ORCHESTRATION_EXACT_NATIVE_ROUTER_IMAGE_TCL_AND_GATES')
if __name__=='__main__':check()
