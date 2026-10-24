#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import hashlib,json,runpy
from pathlib import Path
runpy.run_path('scripts/check_cdr_v39_intrinsic_screen_sources.py')
m=json.loads(Path('scripts/cdr-v40-intrinsic-screen-method.json').read_text())
for key,row in m['files'].items():
 b=Path(row['baseline']).read_bytes();assert hashlib.sha256(b).hexdigest()==row['baseline_sha256']
 s=b.decode()
 for edit in m['edits']:
  if edit['target']!=key:continue
  assert s.count(edit['before'])==edit['count'];s=s.replace(edit['before'],edit['after'])
 c=Path(row['candidate']).read_bytes()
 assert c==s.encode() and hashlib.sha256(c).hexdigest()==row['candidate_sha256']
for p,h in m['protected'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
print('PASS_EXPLORATORY_INTRINSIC_DIMENSIONS_ONLY_ORIGINAL_STIMULUS_AND_GATES_PRESERVED')
