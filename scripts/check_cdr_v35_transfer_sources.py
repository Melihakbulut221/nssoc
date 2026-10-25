#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import ast,hashlib,json,runpy
from pathlib import Path
runpy.run_path('scripts/check_cdr_v33_transfer_sources.py')
m=json.loads(Path('scripts/cdr-v35-transfer-source-adaptation.json').read_text())
b=Path(m['baseline_path']).read_bytes();assert hashlib.sha256(b).hexdigest()==m['baseline_sha256']
s=b.decode();pieces=[];cursor=0
for e in m['changes']:
 assert cursor<=e['start']<=e['end']<=len(s)
 pieces.extend([s[cursor:e['start']],e['replacement']]);cursor=e['end']
pieces.append(s[cursor:]);candidate=Path(m['candidate_path']).read_bytes()
assert ''.join(pieces).encode()==candidate and hashlib.sha256(candidate).hexdigest()==m['candidate_sha256']
for p,h in m['protected'].items():
 b=Path(p).read_bytes();assert hashlib.sha256(b).hexdigest()==h,p
 if p.endswith('.py'):ast.parse(b.decode(),filename=p)
print('PASS_V35_COMPLETE_REJECTED_CAPTURE_AND_UNCHANGED_ORIGINAL_CHECKS')
