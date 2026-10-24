#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import hashlib,json
from pathlib import Path
m=json.loads(Path('scripts/tx-wire24-g234-bridge-source-deltas.json').read_text())
for path,digest in m['protected'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest
d=m['wave'];raw=Path(d['baseline_path']).read_bytes()
assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
text=raw.decode()
for e in d['edits']:
    assert text.count(e['before'])==e['count'];text=text.replace(e['before'],e['after'])
candidate=Path(d['candidate_path']).read_bytes()
assert candidate==text.encode()and hashlib.sha256(candidate).hexdigest()==d['candidate_sha256']
print('PASS_EXACT_FINAL_BRIDGE_ADDITION_UNCHANGED_NATIVE_GATES')
