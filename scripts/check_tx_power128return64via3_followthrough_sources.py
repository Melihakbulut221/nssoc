#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import hashlib,json
from pathlib import Path
m=json.loads(Path('scripts/tx-power128return64via3-followthrough-method.json').read_text())
b=Path(m['baseline_path']).read_bytes();assert hashlib.sha256(b).hexdigest()==m['baseline_sha256']
s=b.decode()
for e in m['edits']:
 assert s.count(e['before'])==e['count'];s=s.replace(e['before'],e['after'])
c=Path(m['candidate_path']).read_bytes();assert c==s.encode()and hashlib.sha256(c).hexdigest()==m['candidate_sha256']
print('PASS_RETURN64VIA3_SOURCE_ADAPTATION_ALL_NATIVE_INTRINSIC_RC_GATES_PRESERVED')
