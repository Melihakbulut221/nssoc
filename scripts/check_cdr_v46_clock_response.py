#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import ast,hashlib,json,runpy
from pathlib import Path
m=json.loads(Path('scripts/cdr-v46-clock-response-delta.json').read_text())
raw=Path(m['baseline_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==m['baseline_file_sha256']
s=raw.decode();f=s[s.index('def clock_response('):s.index('\ndef apply(',s.index('def clock_response('))]
assert hashlib.sha256(f.encode()).hexdigest()==m['baseline_function_sha256']
e=m['edit'];assert f.count(e['before'])==e['count'];f=f.replace(e['before'],e['after'])
candidate=Path(m['candidate_path']).read_bytes();assert hashlib.sha256(candidate).hexdigest()==m['candidate_sha256']
tree=ast.parse(candidate);found=[n for n in tree.body if isinstance(n,ast.FunctionDef)]
assert len(found)==1 and ast.dump(found[0],include_attributes=False)==ast.dump(ast.parse(f).body[0],include_attributes=False)
runpy.run_path('scripts/check_cdr_v46_intrinsic_screen_sources.py')
from cdr_selector_headroom import controls
print(json.dumps(dict(source_equations_unchanged=True,clock_observation_controls=controls(),native_simulation_started=False)))
