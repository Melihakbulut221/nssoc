"""Preserve incomplete V16 controls and the actual stop-observation failure."""
from pathlib import Path
import hashlib,json,tarfile,sys
R=Path.cwd();B=Path(__file__).resolve().parent;A=B.parent/'pcie-integrity-v16-20261005'
sys.path.insert(0,str(R/'scripts'))
import characterize_pcie_clock_trim_stream_v2 as life

def pin(p):
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
assert json.loads((B/'V16-supersession-receipt03.json').read_text())['status']=='AUTHOR_SUPERSEDED_V16_INCOMPLETE_CAPTURE_RETAINED'
assert json.loads((A/'continuation-status02.json').read_text())['stages']==[]
assert 'passed' not in (A/'controls01.log').read_text()
old= json.loads((B/'V16-supersession-receipt02.json').read_text())
remaining=json.loads((B/'V16-supersession-receipt03.json').read_text())
for record in [old,remaining]:
 for row in record['stops']:
  for expected in row['members_before']:
   actual=life.process_identity(expected['pid']);assert actual is None or actual['start_ticks']!=expected['start_ticks'] or actual['state']=='Z'
f=json.loads((A/'source-freeze.json').read_text());files={}
for n,v in f['files'].items():assert pin(R/n)==v;files['source/'+n]=R/n
for p in A.iterdir():
 if p.is_file():files['method/V16/'+p.name]=p
for root in [Path('/dev/shm/nssoc-integrity-v16-controls01'),Path('/dev/shm/nssoc-integrity-v16-icarus14-probe01')]:
 for p in root.rglob('*'):
  if p.is_file() and not p.is_symlink() and not any(d.is_symlink() for d in p.parents if d!=root):files['incomplete/'+root.name+'/'+str(p.relative_to(root))]=p
for name in ['V16-supersession-receipt02.json','V16-supersession-receipt03.json','supersession-identity-guards02.json','supersede_v16_after_validation_v2.py','complete_v16_supersession_v3.py','continuation-status02.json','continuation02.log','supersede_v16.controller.log','continuation-source-only-peer-root02.json','continuation-source-only-peer-root03.json','continuation-review-freeze02.json','continuation-review-freeze03.json','identity-guard-controls02.json','supersession-v3-bridge-observation.json','seal_superseded_v16.py']:
 files['method/V17/'+name]=B/name
manifest={n:dict(original_path=str(p),**pin(p)) for n,p in sorted(files.items())};mp=B/'superseded-v16-members.json';assert not mp.exists();mp.write_text(json.dumps(manifest,indent=2)+'\n')
a=B/'pcie-integrity-v16-incomplete-supersession-20261005.tar.xz';assert not a.exists()
with tarfile.open(a,'w:xz',preset=3) as t:
 for n,p in sorted(files.items()):t.add(p,arcname=n,recursive=False)
 t.add(mp,arcname='members.json',recursive=False)
with tarfile.open(a,'r:xz') as t:
 assert set(t.getnames())==set(manifest)|{'members.json'}
 for m in t.getmembers():
  expected=pin(mp) if m.name=='members.json' else manifest[m.name];assert m.isfile() and m.size==expected['bytes']
  with t.extractfile(m) as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==expected['sha256']
r=dict(status='INCOMPLETE_V16_SUPERSEDED_CAPTURE_DURABLY_RETAINED',archive=dict(path=str(a),**pin(a),members=len(manifest)+1),full_member_readback=True,source_freeze=pin(A/'source-freeze.json'),scope='V16 full suite did NOT complete; ring16/64 literalcases passed butring128Icarus12/14 nevercompleted. Author superseded onlyafterfull39V17controls+independentsource/lifecyclepeers. No nativeV16map launched. ActualV2observerteardownrace retained asfailure; V3completed remainingprobe withstrictsignalguards. No oldPASS claim andPLLuntouched.')
p=B/'superseded-v16-validation.json';p.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
