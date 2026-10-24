#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Verify the declared source/capture adaptation without changing observations."""
import ast,hashlib,json,runpy
from pathlib import Path
runpy.run_path('scripts/check_cdr_v39_transfer_sources.py')
m=json.loads(Path('scripts/cdr-v40-transfer-source-adaptation.json').read_text())
raw=Path(m['baseline_path']).read_bytes()
assert hashlib.sha256(raw).hexdigest()==m['baseline_sha256']
source=raw.decode()
for edit in m['edits']:
    assert source.count(edit['before'])==edit['count'],edit['before']
    source=source.replace(edit['before'],edit['after'])
candidate=Path(m['candidate_path']).read_bytes()
assert source.encode()==candidate and hashlib.sha256(candidate).hexdigest()==m['candidate_sha256']
ast.parse(source,filename=m['candidate_path'])
for p,h in m['protected'].items():
    assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
assert m['native_simulation_started'] is False and m['original_observation_equations_unchanged']
print('PASS_SOURCE_BOUND_V40_FULL_NATIVE_SELECTOR_AND_LATCH_DIAGNOSIS')
