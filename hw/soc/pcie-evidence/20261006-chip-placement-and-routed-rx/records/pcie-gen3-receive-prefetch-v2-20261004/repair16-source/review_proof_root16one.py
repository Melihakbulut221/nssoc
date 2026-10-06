# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent source/pin/gold readback; does not execute native producers."""
from pathlib import Path
import hashlib,json,gzip,ast
S=Path(__file__).resolve().parent;B=S.parent

def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
fpath=S/'proof-source-freeze16one.json';f=json.loads(fpath.read_text())
for k in ['sources','inputs']:assert f[k]=={n:pin(n) for n in f[k]}
bridges=json.loads((S/'proof-source-bridge16one.json').read_text());assert len(bridges)==3
for b in bridges:
 for end in ['before','after']:
  p=Path(b[end]['path']);assert pin(p)=={k:b[end][k] for k in ['bytes','sha256']}
  text=''.join(op[end] for op in b['opcodes']);assert text==p.read_text();ast.parse(text)
  if end=='after':assert 'subprocess.Popen(' not in text and 'ast.parse(' not in text and 'owned_lifecycle16' in text
assert (B/'owned_lifecycle16.py').read_bytes()==Path('hw/soc/out/pcie-gen3-transmit-v4-repair-20261005/owned_lifecycle05.py').read_bytes()
g=Path('/dev/shm/nssoc-rx-prefetch-v2-repair11-equivalence');n=json.loads((g/'normalization.json').read_text());assert n['inputs']=={p:pin(p) for p in n['inputs']};row=n['runs'][0];assert row['name']=='gold' and row['returncode']==0
for suffix,key in [('.ys','script_sha256'),('.log','log_sha256')]:assert pin(g/('gold'+suffix))['sha256']==row[key]
assert pin(g/'gold.json.gz')['sha256']==row['expanded_json']['lossless_gzip_sha256']
with gzip.open(g/'gold.json.gz','rb') as stream:
 h=hashlib.sha256();size=0
 while data:=stream.read(1024**2):h.update(data);size+=len(data)
assert dict(bytes=size,sha256=h.hexdigest())=={k:row['expanded_json'][k] for k in ['bytes','sha256']}
c=Path(f['candidate']['path']).parent;r=json.loads((c/'result.json').read_text());assert r['status']=='COMPLETE_CANDIDATE_REQUIRES_EQUIVALENCE_ROUTE_RC';assert r['inputs']=={n:pin(n) for n in r['inputs']};assert r['outputs']=={n:pin(c/n) for n in r['outputs']}
record=dict(status='PASS_SOURCE_ONLY_RX16ONE_PROOF_PORTS',freeze=pin(fpath),findings=[],sources=f['sources'],candidate=f['candidate'],whole_source_inverse_bridges=3,original_gold_expanded=dict(bytes=size,sha256=h.hexdigest()),canonical_kernels={n:pin(B/n) for n in ['eco-proof/compare.py','eco-proof/mutations.py']},helper=pin(B/'owned_lifecycle16.py'),method=pin(__file__),checks=['Only candidate paths/pins/status and reviewed ownership import changed; canonical originalgold/proof10faults/6nativeports unchanged.','All frozen sources, inputs and completedcandidate outputs rehashed. Fullnative-expandedoriginalgold readback verified.','WNOWAIT ownership helper isbyteequal independentlyreviewed andactual8process-controls-tested TX05. Newhelper included allnative inputpin sets.','No new pathdelay/period/resource/functionaloracle relaxations. New gate expansion required; originalgold reusedexactly.'],supplemental_launcher='Separate source-only review requested envsanitization andactual nested-session cleanup control beforecontrollerlaunch. This receipt approves core3drivers, not unconstrainednewlaunchercode.',native_executed=False,physical_acceptance=False)
(S/'proof-source-only-peer-root16one.json').write_text(json.dumps(record,indent=2)+'\n');print(record['status'],record['original_gold_expanded'])
