#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import hashlib,json
from pathlib import Path
for d in json.loads(Path('scripts/onehot-clock-restore-route-source-deltas.json').read_text()):
    raw=Path(d['baseline_path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
    text=raw.decode()
    for edit in d['edits']:
        assert text.count(edit['before'])==edit['count']
        text=text.replace(edit['before'],edit['after'])
    candidate=Path(d['candidate_path']).read_bytes()
    assert candidate==text.encode() and hashlib.sha256(candidate).hexdigest()==d['candidate_sha256']
print('PASS_EXACT_CLOCK_RESTORE_ROUTE_SOURCE_DELTAS')
