# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent source/full saved-input review; no EDA or tests executed."""
from pathlib import Path
import ast,gzip,hashlib,json
S=Path(__file__).resolve().parent;B=S.parent
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
fpath=S/'proof-source-freeze02.json';f=json.loads(fpath.read_text());assert pin(fpath)==dict(bytes=3700,sha256='47c1c9294f80442e1121ed5ac79a5094850afd61267f0ba56d2cc2d0d4cea286')
assert f['files']=={p:pin(p) for p in f['files']};assert f['lifecycle_revision']['controls']=={p:pin(p) for p in f['lifecycle_revision']['controls']}
bpath=S/'proof-source-bridge.json';assert pin(bpath)==f['bridge'];bridges=json.loads(bpath.read_text())
for row in bridges:
 a=Path(row['before']['path']);z=Path(row['after']['path']);assert pin(a)=={k:row['before'][k] for k in ('bytes','sha256')};assert pin(z)=={k:row['after'][k] for k in ('bytes','sha256')}
 assert a.read_text()==''.join(x['before'] for x in row['opcodes']);assert z.read_text()==''.join(x['after'] for x in row['opcodes']);ast.parse(z.read_text())
for n in ('compare.py','mutations.py'):assert (B/'proof03'/n).read_text().replace('repair03','repair05')==(B/'proof05'/n).read_text()
C=Path(f['candidate']['path']).parent;r=json.loads((C/'result.json').read_text());assert pin(C/'result.json')==f['candidate_result'];assert r['returncode']==0 and r['status'].startswith('COMPLETE_');assert r['inputs']=={p:pin(p) for p in r['inputs']};assert r['outputs']=={n:pin(C/n) for n in r['outputs']}
E=Path('/dev/shm/nssoc-tx-path-v4-repair02-equivalence');n=json.loads((E/'normalization.json').read_text());assert n['inputs']=={p:pin(p) for p in n['inputs']};g=n['runs'][0];assert g['name']=='gold' and g['returncode']==0
assert pin(E/'gold.ys')['sha256']==g['script_sha256'];assert pin(E/'gold.log')['sha256']==g['log_sha256'];assert pin(E/'gold.json.gz')['sha256']==g['expanded_json']['lossless_gzip_sha256']
with gzip.open(E/'gold.json.gz','rb') as q:
 h=hashlib.sha256();sz=0
 while b:=q.read(1024**2):h.update(b);sz+=len(b)
assert {'bytes':sz,'sha256':h.hexdigest()}=={k:g['expanded_json'][k] for k in ('bytes','sha256')}
assert '8 passed' in (S/'lifecycle-controls02.log').read_text()
for name in ('normalize_repair05.py','proof_gate_repair05.py','replay_repair05.py'):
 text=(B/name).read_text();assert 'from owned_lifecycle05 import owned_popen, stop_failed_group' in text and 'owned_popen(' in text and 'subprocess.Popen(' not in text and 'owned_lifecycle05.py' in text
helper=(B/'owned_lifecycle05.py').read_text();assert 'os.WEXITED | os.WNOHANG | os.WNOWAIT' in helper and 'class OwnedProcess:' in helper
result=dict(status='PASS_SOURCE_ONLY_TX05_PROOF_PORTS_AND_BIRTH_BOUND_GROUP_OWNERSHIP',findings=[],freeze=pin(fpath),method=pin(__file__),source_pins=f['files'],whole_source_inverse_bridges=len(bridges),canonical_kernels_byte_exact=True,candidate_result=pin(C/'result.json'),candidate_inputs_rehashed=len(r['inputs']),candidate_outputs_rehashed=len(r['outputs']),reused_gold=dict(compressed=pin(E/'gold.json.gz'),expanded=dict(bytes=sz,sha256=h.hexdigest())),lifecycle_controls=f['lifecycle_revision']['controls'],resolved_finding='Initial poll/wait reaped leader too early, allowing a surviving descendant. All callers now use OwnedProcess poll/wait; WNOWAIT preserves direct-child birth/PGID anchor until group live-member census is empty. Nonzero/zero early leader exits with descendants cause cleanup and failure. Both group signals occur while exact leader remains unreaped; parent registration/cleanup signals masked and child mask/limits restored.',reviewed_control_scope='Eight actual saved process controls: normal0/7; leader exits0/9 before poll with ignoring child; TERM leader/ignoring child; unrelated group survives; forged start refused; preexec/parent mask preserved. Ten saved file-binding controls retain same proof semantics. Controls inspected, not rerun.',limits='Only descendants staying in the explicitly owned native process group are covered; current Yosys/compare/make-Icarus calls use that group. No native proof/port/physical execution by reviewer, no closure claim.')
p=S/'proof-source-only-peer-rx02.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(path=str(p),**pin(p))))
