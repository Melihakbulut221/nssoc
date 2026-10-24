#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind the original native process continuation to its explicit full-terminal changes."""
import hashlib,json
from pathlib import Path
d=json.loads(Path('scripts/pll845-native-acquisition-source-deltas.json').read_text())
raw=Path(d['baseline_path']).read_bytes()
assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
text=raw.decode()
for e in d['edits']:
    assert text.count(e['before'])==e['count']
    text=text.replace(e['before'],e['after'])
candidate=Path(d['candidate_path']).read_bytes()
assert candidate==text.encode()and hashlib.sha256(candidate).hexdigest()==d['candidate_sha256']
print('PASS_EXACT_FULL_TERMINAL_NATIVE_CONTINUATION_SOURCE_DELTAS')
