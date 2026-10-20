#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import hashlib,json
from pathlib import Path
d=json.loads(Path('scripts/tx-fast-wire24-path-review-source-delta.json').read_text())
raw=Path(d['baseline_path']).read_bytes()
assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
text=raw.decode()
for e in d['edits']:
    assert text.count(e['before'])==e['count']
    text=text.replace(e['before'],e['after'])
assert text==Path(d['candidate_path']).read_text()
assert hashlib.sha256(text.encode()).hexdigest()==d['candidate_sha256']
print('PASS_EXACT_NEW_CAPTURE_BINDING_UNCHANGED_TX_REVIEW_GATES')
