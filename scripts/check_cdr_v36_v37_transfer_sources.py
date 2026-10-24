#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import ast,hashlib,json,runpy
from pathlib import Path
runpy.run_path('scripts/check_cdr_v35_input_bias_sources.py')
m=json.loads(Path('scripts/cdr-v36-v37-transfer-source-adaptation.json').read_text())
for item in m['adaptations']:
 b=Path(item['baseline_path']).read_bytes();assert hashlib.sha256(b).hexdigest()==item['baseline_sha256']
 s=b.decode();pieces=[];cursor=0
 for e in item['changes']:
  assert cursor<=e['start']<=e['end']<=len(s)
  pieces.extend([s[cursor:e['start']],e['replacement']]);cursor=e['end']
 pieces.append(s[cursor:]);candidate=Path(item['candidate_path']).read_bytes()
 assert ''.join(pieces).encode()==candidate and hashlib.sha256(candidate).hexdigest()==item['candidate_sha256']
 ast.parse(candidate.decode(),filename=item['candidate_path'])
for p,h in m['protected'].items():
 b=Path(p).read_bytes();assert hashlib.sha256(b).hexdigest()==h,p
print('PASS_SOURCE_BOUND_V36_V37_FULL_NATIVE_TRANSFER_DIAGNOSIS')
