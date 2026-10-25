#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import ast,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
 m=json.loads((ROOT/'scripts/cdr-follower-v31-source-deltas.json').read_text())
 for p,h in m['protected'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,p
 for d in m['candidates']:
  raw=(ROOT/d['baseline_path']).read_bytes()
  assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
  s=raw.decode()
  for e in d['edits']:
   assert s.count(e['before'])==e['count'];s=s.replace(e['before'],e['after'])
  raw=(ROOT/d['candidate_path']).read_bytes()
  assert raw==s.encode()and hashlib.sha256(raw).hexdigest()==d['candidate_sha256']
  if d['candidate_path'].endswith('.py'):ast.parse(raw)
 print('PASS_EXACT_V31_FOLLOWER_PULLDOWN_LENGTH_CHANGE_ORIGINAL_PHYSICAL_GATES')
if __name__=='__main__':check()
