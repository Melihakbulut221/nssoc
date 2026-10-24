#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import hashlib,json
from pathlib import Path
m=json.loads(Path('scripts/cdr-v16-latch-source-deltas.json').read_text())
for path,digest in m['protected'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest
d=m['diagnostic'];raw=Path(d['baseline_path']).read_bytes()
assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
text=raw.decode()
for e in d['edits']:
    assert text.count(e['before'])==e['count'];text=text.replace(e['before'],e['after'])
candidate=Path(d['candidate_path']).read_bytes()
assert candidate==text.encode()and hashlib.sha256(candidate).hexdigest()==d['candidate_sha256']
print('PASS_EXACT_V16_NATIVE_SOURCE_BINDING_UNCHANGED_LATCH_AND_WAVEFORM_GATES')
