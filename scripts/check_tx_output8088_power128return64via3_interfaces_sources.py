#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import hashlib,json
from pathlib import Path
m=json.loads(Path('scripts/tx-output8088-power128return64via3-interface-controller-delta.json').read_text())
raw=Path(m['baseline_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==m['baseline_sha256']
s=raw.decode()
for e in m['edits']:
 assert s.count(e['before'])==e['count'];s=s.replace(e['before'],e['after'])
b=Path(m['candidate_path']).read_bytes();assert b==s.encode()and hashlib.sha256(b).hexdigest()==m['candidate_sha256']
print('PASS_VIA3_SOURCE_PINS_ONLY_ORIGINAL_PHYSICAL_ENDPOINT_GATES_PRESERVED')
