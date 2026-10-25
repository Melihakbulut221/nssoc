#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import hashlib,json,runpy
from pathlib import Path
runpy.run_path('scripts/check_cdr_v29_latch_sources.py')
m=json.loads(Path('scripts/cdr-v29-transfer-source-adaptation.json').read_text())
b=Path(m['baseline_path']).read_bytes();assert hashlib.sha256(b).hexdigest()==m['baseline_sha256']
s=b.decode()
for e in m['edits']:
 assert s.count(e['before'])==e['count'];s=s.replace(e['before'],e['after'])
c=Path(m['candidate_path']).read_bytes();assert c==s.encode()and hashlib.sha256(c).hexdigest()==m['candidate_sha256']
print('PASS_ONLY_ADDED_NATIVE_FOLLOWER_OBSERVATIONS_ORIGINAL_LATCH_AND_ELECTRICAL_GATES_UNCHANGED')
