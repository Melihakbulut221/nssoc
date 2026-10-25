#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import ast,hashlib,json,runpy
from pathlib import Path
runpy.run_path('scripts/check_cdr_v44_l39_observation_sources.py')
m=json.loads(Path('scripts/cdr-v47-drive-load-observation-source-adaptation.json').read_text())
raw=Path(m['baseline_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==m['baseline_sha256']
source=raw.decode()
for e in m['edits']:
    assert source.count(e['before'])==e['count']
    source=source.replace(e['before'],e['after'])
candidate=Path(m['candidate_path']).read_bytes()
assert candidate==source.encode()and hashlib.sha256(candidate).hexdigest()==m['candidate_sha256']
ast.parse(source)
for p,h in m['protected'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
assert m['native_simulation_started']is False and m['original_observation_equations_unchanged']
print('PASS_SOURCE_BOUND_SELECTOR_TERMINAL_OBSERVATIONS_NO_NEW_NATIVE_OR_ACCEPTANCE_GATE')
