#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    for d in json.loads((ROOT/'scripts/onehot-load-resume-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256'];text=raw.decode()
        for e in d['edits']:
            assert text.count(e['before'])==e['count'];text=text.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes();assert actual==text.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    print('PASS_EXACT_SAVED_CHECKPOINT_CONTINUATION_ORIGINAL_PHYSICAL_AND_THREE_CORNER_TIMING_GATES_RETAINED')
if __name__=='__main__':check()
