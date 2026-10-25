#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_hybrid_tail_source import check as original_check
    original=original_check()
    proofs=[]
    for name in ('cdr-sampler-load-drive-source-delta.json','cdr-sampler-load-drive-controller-delta.json'):
        d=json.loads((ROOT/'scripts'/name).read_text());raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        text=raw.decode()
        for e in d['edits']:
            assert text.count(e['before'])==e['count'];text=text.replace(e['before'],e['after'])
        text=d.get('prefix','')+text;actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==text.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
        proofs.append(dict(path=d['candidate_path'],sha256=d['candidate_sha256'],exact_declared_delta=True))
    return dict(status='PASS_DECLARED_LOAD_DRIVE_DELTAS_ORIGINAL_GATES_RETAINED',original_guard=original,files=proofs,physical_layout_matches=False,full_phy_accepted=False)
if __name__=='__main__':print(json.dumps(check(),sort_keys=True))
