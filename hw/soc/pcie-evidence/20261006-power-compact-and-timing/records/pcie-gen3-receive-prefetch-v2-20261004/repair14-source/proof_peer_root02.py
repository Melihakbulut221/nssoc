import ast,gzip,hashlib,json
from pathlib import Path
B=Path('hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004').resolve()
S=B/'repair14-source'
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return {'bytes':p.stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}
def check(p,v):
 assert pin(p)=={k:v[k] for k in ('bytes','sha256')},p
 return pin(p)
f=json.loads((S/'proof-source-freeze02.json').read_text())
pins={p:check(p,v) for p,v in f['files'].items()}
bridge=json.loads(Path(f['bridge_path']).read_text());check(f['bridge_path'],f['bridge'])
rows=[]
for r in bridge:
 for side in ('before','after'):
  p=Path(r[side]['path']); check(p,r[side]);assert ''.join(o[side] for o in r['opcodes']).encode()==p.read_bytes()
 before=Path(r['before']['path']).read_text();after=Path(r['after']['path']).read_text()
 expected=before.replace('repair13','repair14a').replace('repair-13','repair-14a').replace('RX13','RX14A').replace('rx13','rx14a').replace('2093617','2094864').replace('533ecba38bc02e0f08cf96e9aef1e71682141de26dd772bc965abe9619c6ab34','cc489bb50c225189126b36d173cf786a7837f1e9a0cebc8a200c2d7b7a191f91').replace("repair14a-source/port-prelaunch-failure.json","repair14-source/port-prelaunch-failure.json")
 assert expected==after,r['after']['path']
 oldtree=ast.parse(before);newtree=ast.parse(after)
 pure_helpers=['pin','limits','stop_failed_group','interrupted']
 for name in pure_helpers:
  old=[x for x in oldtree.body if isinstance(x,ast.FunctionDef) and x.name==name]
  new=[x for x in newtree.body if isinstance(x,ast.FunctionDef) and x.name==name]
  assert [ast.dump(x) for x in old]==[ast.dump(x) for x in new],name
 rows.append({'before':r['before'],'after':r['after'],'whole_byte_ledger_and_restricted_substitution':'PASS'})
check(f['candidate']['path'],f['candidate'])
check('/dev/shm/nssoc-rx-prefetch-v2-postroute-repair-14a/result.json',f['candidate_result'])
gp=Path(f['reused_original_gold']['path']);check(gp,f['reused_original_gold']);g=json.loads(gp.read_text())
for p,v in g['inputs'].items():check(p,v)
gold=g['runs'][0];assert gold['name']=='gold' and gold['returncode']==0
for ext,key in [('.ys','script_sha256'),('.log','log_sha256')]:assert pin(gp.parent/('gold'+ext))['sha256']==gold[key]
z=gp.parent/'gold.json.gz';assert pin(z)['sha256']==gold['expanded_json']['lossless_gzip_sha256']
with gzip.open(z,'rb') as stream:
 h=hashlib.sha256();n=0
 while data:=stream.read(1024**2):h.update(data);n+=len(data)
assert {'bytes':n,'sha256':h.hexdigest()}=={k:gold['expanded_json'][k] for k in ('bytes','sha256')}
assert not Path('/dev/shm/nssoc-rx-prefetch-v2-repair14a-equivalence').exists()
assert not Path('/dev/shm/nssoc-rx-prefetch-v2-repair14a-physical-replay-01').exists()
r={'status':'PASS_RX14A_PROOF_PORT_SOURCE_ONLY_ROOT_PEER','method':pin(__file__),'freeze':pin(S/'proof-source-freeze02.json'),'bridge':pin(f['bridge_path']),'sources':pins,'derivations':rows,'candidate':f['candidate'],'original_gold_full_decompressed':{'bytes':n,'sha256':h.hexdigest()},'scope':'Read full three sources; whole-byte derivation only labels, exact candidate pin, fresh paths and corrected fallback; unchanged lifecycle helpers and proof gates. Revalidated original gold native inputs and full gzip. Authorizes fresh normalization, actual canonical proof plus ten mutations, then six native ports only on pass. No proof outcome, timing or fullPHY claim.'}
(S/'proof-source-peer-root02.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status']);print(pin(S/'proof-source-peer-root02.json'))
