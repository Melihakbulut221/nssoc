#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import hashlib,json,runpy
from pathlib import Path
root=Path(__file__).resolve().parents[1]
runpy.run_path(str(root/'scripts/check_cdr_follower_v31_parent_sources.py'))
runpy.run_path(str(root/'scripts/check_cdr_sampler_settling_v32_sources.py'))
m=json.loads((root/'scripts/cdr-sampler-settling-v32-parent-source-delta.json').read_text())
for p,h in m['protected'].items():assert hashlib.sha256((root/p).read_bytes()).hexdigest()==h,p
for e in m['files']:
 raw=(root/e['baseline']).read_bytes();assert hashlib.sha256(raw).hexdigest()==e['baseline_sha256']
 s=raw.decode();parts=[];cursor=0
 for c in e['changes']:
  a,b=c['start'],c['end'];assert cursor<=a<=b<=len(s)
  parts.extend([s[cursor:a],c['replacement']]);cursor=b
 parts.append(s[cursor:]);candidate=(root/e['candidate']).read_bytes()
 assert candidate==''.join(parts).encode()and hashlib.sha256(candidate).hexdigest()==e['candidate_sha256']
print('PASS_EXACT_V32_SAMPLER_REPLACEMENT_SOURCE_RETAINS_V31_FOLLOWER_AND_ALL_PARENT_PHYSICAL_GATES')
