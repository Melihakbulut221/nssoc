#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Verify only immutable source binding changed; original diagnostic gates remain."""
import hashlib,json,runpy
from pathlib import Path
runpy.run_path('scripts/check_cdr_v31_transfer_sources.py')
m=json.loads(Path('scripts/cdr-v32-transfer-source-adaptation.json').read_text())
b=Path(m['baseline_path']).read_bytes();assert hashlib.sha256(b).hexdigest()==m['baseline_sha256']
s=b.decode()
for e in m['edits']:
 assert s.count(e['before'])==e['count'];s=s.replace(e['before'],e['after'])
c=Path(m['candidate_path']).read_bytes();assert c==s.encode()and hashlib.sha256(c).hexdigest()==m['candidate_sha256']
for p,h in m['protected'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
print('PASS_V32_NATIVE_SOURCE_BINDING_PRESERVES_ORIGINAL_FAILURES_AND_GATES')
