#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import ast,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
def check():
 m=json.loads((ROOT/'scripts/pll-rhi120-c8-sparse-storage-delta.json').read_text())
 raw=(ROOT/m['baseline']).read_bytes();assert sha(raw)==m['baseline_sha256']
 text=raw.decode()
 for e in m['edits']:
  assert text.count(e['before'])==e['count']
  text=text.replace(e['before'],e['after'])
 candidate=(ROOT/m['candidate']).read_bytes()
 assert candidate==text.encode()and sha(candidate)==m['candidate_sha256']
 for p,h in m['protected'].items():
  b=(ROOT/p).read_bytes();assert sha(b)==h,p
  if p.endswith('.py'):ast.parse(b,filename=p)
 import cloud_pll_rhi120_c8_sparse_io as storage
 for stage in ('initial','recovery','sparse'):
  spec=dict(run=1,attempt=1,stage=stage,summary_sha256='1'*64,parts_sha256='2'*64)
  url,stem=storage.source_url(spec)
  assert stem=='pll-rhi120-c8-native-'+stage+'-1-1'
  assert url.endswith('cloud-results-1-1-pll-rhi120-c8-native-'+stage+'/')
 try:storage.source_url(dict(run=1,attempt=1,stage='continuation',summary_sha256='1'*64,parts_sha256='2'*64))
 except AssertionError:pass
 else:raise AssertionError('Legacy namespace accepted')
 return dict(m['protected'],**{m['baseline']:m['baseline_sha256'],m['candidate']:m['candidate_sha256']})
if __name__=='__main__':
 print(json.dumps(dict(status='PASS_RHI120_SPARSE_NAMESPACE_SOURCE_ONLY',methods=check(),native_activation_performed=False)))
