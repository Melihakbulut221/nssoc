#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import ast,hashlib,json
from pathlib import Path
m=json.loads(Path('scripts/native-sparse-btrfs-cross-job-delta.json').read_text())
for p,h in m['protected'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
d=m['diagnostic'];raw=Path(d['baseline_path']).read_bytes()
assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
s=raw.decode()
for e in d['edits']:
 assert s.count(e['before'])==e['count'];s=s.replace(e['before'],e['after'])
candidate=Path(d['candidate_path']).read_bytes()
assert s.encode()==candidate and hashlib.sha256(candidate).hexdigest()==d['candidate_sha256']
ast.parse(candidate)
print('PASS_EXACT_CROSS_HOST_BTRFS_SPARSE_STORAGE_DELTA_ORIGINAL_NATIVE_GATES')
