# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import ast,json,hashlib,difflib
S=Path(__file__).resolve().parent;B=S.parent;R=Path.cwd();TX=R/'hw/soc/out/pcie-gen3-transmit-v4-repair-20261005'
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
C=Path('/dev/shm/nssoc-rx-prefetch-v2-postroute-repair-16-one-repair-04/repaired.v');P=pin(C)
oldpin={'bytes':2094864,'sha256':'cc489bb50c225189126b36d173cf786a7837f1e9a0cebc8a200c2d7b7a191f91'}
helper=B/'owned_lifecycle16.py';assert not helper.exists();helper.write_bytes((TX/'owned_lifecycle05.py').read_bytes())
rows=[]
for base in ('normalize','proof_gate','replay'):
 a=B/(base+'_repair14a.py');z=B/(base+'_repair16one.py');assert not z.exists();old=a.read_text();new=old.replace('repair14a','repair16one').replace('RX14A','RX16ONE').replace('rx14a','rx16one').replace('/postroute-repair-14a/','/postroute-repair-16-one-repair-04/')
 new=new.replace('nssoc-rx-prefetch-v2-postroute-repair-14a','nssoc-rx-prefetch-v2-postroute-repair-16-one-repair-04').replace("postroute_repair16one.py","postroute_repair16_one04.py").replace(str(oldpin),str(P))
 if base=='normalize':
  new=new.replace('import hashlib,json,os,pathlib,resource,subprocess,time,signal,gzip,shutil','import hashlib,json,os,pathlib,resource,subprocess,time,signal,gzip,shutil\nfrom owned_lifecycle16 import owned_popen, stop_failed_group')
  fn=next(n for n in ast.parse(new).body if isinstance(n,ast.FunctionDef)and n.name=='stop_failed_group');lines=new.splitlines(True);new=''.join(lines[:fn.lineno-1]+lines[fn.end_lineno:])
  new=new.replace('subprocess.Popen(', 'owned_popen(')
  new=new.replace('inputs=[pathlib.Path(__file__).resolve(),','inputs=[pathlib.Path(__file__).resolve(),pathlib.Path(__file__).resolve().parent/\'owned_lifecycle16.py\',')
 else:
  new=new.replace('import shutil\n','import shutil\nfrom owned_lifecycle16 import owned_popen, stop_failed_group\n') if base=='proof_gate' else new.replace('import time\n','import time\nfrom owned_lifecycle16 import owned_popen, stop_failed_group\n')
  if base=='proof_gate':
   start=new.index('    tree = ast.parse(');end=new.index('\n\n    def stop_signal',start);new=new[:start]+"    ns = {'stop_failed_group': stop_failed_group}"+new[end:]
   new=new.replace("B / 'postroute_repair16_one04.py', NET", "B / 'postroute_repair16_one04.py', B / 'owned_lifecycle16.py', NET")
  else:
   start=new.index('# Reuse the exact tested helper body');end=new.index('\n\ndef owned_execute',start);new=new[:start]+new[end:]
   new=new.replace("dependencies = [Path(__file__),", "dependencies = [Path(__file__), B / 'owned_lifecycle16.py',")
   new=new.replace("B / 'repair14-source/port-prelaunch-failure.json'", "B / 'repair16-source/port16one-prelaunch-failure.json'")
  new=new.replace('subprocess.Popen(', 'owned_popen(')
 ast.parse(new);z.write_text(new)
 al=old.splitlines(True);zl=new.splitlines(True);ops=[dict(tag=t,before=''.join(al[i:j]),after=''.join(zl[k:l]))for t,i,j,k,l in difflib.SequenceMatcher(None,al,zl,autojunk=False).get_opcodes()]
 assert ''.join(x['before']for x in ops)==old and ''.join(x['after']for x in ops)==new
 rows.append(dict(before={'path':str(a),**pin(a)},after={'path':str(z),**pin(z)},opcodes=ops))
(S/'proof-source-bridge16one.json').write_text(json.dumps(rows,indent=2)+'\n')
files=[B/(n+'_repair16one.py')for n in ('normalize','proof_gate','replay')]+[helper]
inputs=[C,C.parent/'result.json',C.parent/'native.log',S/'one04-rejection-review.json',S/'source-only-peer04-vco.json',TX/'owned_lifecycle05.py',TX/'repair05-source/proof-source-only-peer-rx02.json',B/'eco-proof/compare.py',B/'eco-proof/mutations.py',S/'proof-source-bridge16one.json',Path(__file__)]
f=dict(status='FROZEN_RX16ONE_PROOF_PORTS_SOURCE_BEFORE_NATIVE',sources={str(p):pin(p)for p in files},inputs={str(p):pin(p)for p in inputs},candidate={'path':str(C),**P},scope='Same canonical original-gold graph/proof ten faults/six RX native port cases; new exact candidate only. Actual WNOWAIT ownership helper byte-equal reviewed TX05; original gold native expansion reused by full decompressed hash. No physical acceptance.')
(S/'proof-source-freeze16one.json').write_text(json.dumps(f,indent=2)+'\n');print(json.dumps({'candidate':P,'sources':f['sources'],'freeze':pin(S/'proof-source-freeze16one.json')},indent=2))
