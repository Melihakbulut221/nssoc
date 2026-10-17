# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Freeze new RX13 gate/proof/ports after completed candidate; never rerun gold."""
from pathlib import Path
import ast,json,hashlib,difflib
S=Path(__file__).resolve().parent;B=S.parent;N=Path('/dev/shm/nssoc-rx-prefetch-v2-postroute-repair-13')
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
r=json.loads((N/'result.json').read_text());assert r['status']=='COMPLETE_CANDIDATE_REQUIRES_EQUIVALENCE_ROUTE_RC' and r['returncode']==0
for n,p in r['inputs'].items():assert pin(n)==p
for n,p in r['outputs'].items():assert pin(N/n)==p
oldfreeze=json.loads((B/'repair12-source/proof-source-freeze.json').read_text());prior={k:oldfreeze['candidate'][k] for k in ['bytes','sha256']};newpin=pin(N/'repaired.v');files={};bridges=[]
for name in ['normalize','proof_gate','replay']:
 old=B/(name+'_repair12.py');new=B/(name+'_repair13.py');original=old.read_text();assert pin(old)==oldfreeze['files'][str(old)]
 text=original.replace('repair12','repair13').replace('repair-12','repair-13').replace('RX12','RX13').replace('rx12_','rx13_')
 assert text.count(repr(prior))==1;text=text.replace(repr(prior),repr(newpin));ast.parse(text);assert not new.exists();new.write_text(text);files[str(new)]=pin(new)
 inverse=text.replace(repr(newpin),repr(prior)).replace('repair13','repair12').replace('repair-13','repair-12').replace('RX13','RX12').replace('rx13_','rx12_');assert inverse==original
 for f in ['limits','stop_failed_group','owned_execute']:
  a=[n for n in ast.walk(ast.parse(original)) if isinstance(n,ast.FunctionDef) and n.name==f];z=[n for n in ast.walk(ast.parse(text)) if isinstance(n,ast.FunctionDef) and n.name==f]
  if a:assert len(a)==len(z)==1 and ast.dump(a[0])==ast.dump(z[0])
 changes=[];a=original.splitlines(True);z=text.splitlines(True)
 for tag,i,j,k,l in difflib.SequenceMatcher(None,a,z,autojunk=False).get_opcodes():changes.append(dict(tag=tag,before=''.join(a[i:j]),after=''.join(z[k:l])))
 bridges.append(dict(before=dict(path=str(old),**pin(old)),after=dict(path=str(new),**pin(new)),opcodes=changes))
bridge=S/'proof-source-bridge.json';bridge.write_text(json.dumps(bridges,indent=2)+'\n')
gold=Path('/dev/shm/nssoc-rx-prefetch-v2-repair11-equivalence/normalization.json')
f=dict(status='FROZEN_RX13_NEW_GATE_PROOF_PORT_SOURCES_NO_NATIVE_STARTED',method=pin(__file__),candidate=dict(path=str(N/'repaired.v'),**newpin),candidate_result=pin(N/'result.json'),files=files,bridge=pin(bridge),reused_original_gold=dict(path=str(gold),**pin(gold)),scope='Version/path/new candidate pin changes only from frozenRX12. Identical completed originalgold fromRX11 is reused with native source and full gzip-byte revalidation; new gate native normalization, actual complete canonical compare/10mutations and6physicalportcases required. No new simulation/DRT/RC acceptance.')
p=S/'proof-source-freeze.json';assert not p.exists();p.write_text(json.dumps(f,indent=2)+'\n');print(json.dumps(f))
