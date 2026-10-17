"""Seal all actual frozen V23 targeted control bytes; failures remain failures."""
from pathlib import Path
import hashlib,io,json,re,tarfile,xml.etree.ElementTree as ET
R=Path.cwd();B=Path(__file__).resolve().parent;D=Path('/dev/shm/nssoc-integrity-v23-public-controls02')
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def counts(p):
 cs=list(ET.parse(p).getroot().iter('testcase'))
 return cs,dict(passed=sum(not any(c.find(k)is not None for k in ('failure','error','skipped'))for c in cs),failed=sum(any(c.find(k)is not None for k in ('failure','error'))for c in cs),skipped=sum(c.find('skipped')is not None for c in cs))
f=json.loads((B/'source-freeze02.json').read_text())
for n,v in f['sources'].items():assert pin(R/n)==v and pin(B/'sources02'/n)==v,n
peer=json.loads((B/'source-only-peer-rx02.json').read_text());assert peer['freeze']==pin(B/'source-freeze02.json')and not peer['findings']
state=json.loads((B/'controls-status01.json').read_text());assert state['status']in ('COMPLETE_PENDING_INDEPENDENT_CONTROL_RECOUNT','FAILED_CONTROLS_RETAINED')and state['returncode']in(0,1)
cs,c=counts(B/'controls02.xml');assert len(cs)==9 and c['skipped']==0
assert (state['returncode']==0)==(c==dict(passed=9,failed=0,skipped=0))
helpers=[]
for p in sorted(D.glob('*/*/result.json')):
 if p.parent.parent.is_symlink():continue
 r=json.loads(p.read_text())
 if 'inputs'not in r or 'outputs'not in r:continue
 assert r['status']!='RUNNING'
 for n,v in r['inputs'].items():assert pin(n)==v,n
 for n,v in r['outputs'].items():assert pin(p.parent/n)==v,str(p.parent/n)
 x=p.parent/'results.xml'
 helpers.append(dict(path=str(p),**pin(p),status=r['status'],counts=counts(x)[1]if x.is_file()else None))
observations={'classification': 'Actual6PASS3FAIL preserved. Both direct/miter native positives pass canonical1/0/17; two host assertions expected wrong schema. Five new product mutants plus old-predecessor observer are caught; header_promote_stale survives unchanged wrapper cadence and requires a real block-port burst witness before mapping.'}
assert c==dict(passed=6,failed=3,skipped=0)
entries={}
for p in D.rglob('*'):
 if p.is_file()and not p.is_symlink()and not any(q.is_symlink()for q in p.parents if q!=D.parent):entries['raw/'+str(p.relative_to(D))]=p
for n in f['sources']:entries['sources/'+n]=R/n
for p in B.rglob('*'):
 if p.is_file()and not p.is_symlink()and p.suffix not in('.xz','.gz')and p.name not in ['active-checkpoint.json','seal-controls02.log']:
  entries['evidence/'+str(p.relative_to(B))]=p
manifest={n:dict(original=str(p),**pin(p))for n,p in sorted(entries.items())}
archive=B/'pcie-integrity-v23-controls02-20261006.tar.xz';assert not archive.exists()
with tarfile.open(archive,'w:xz',preset=1)as t:
 for n,p in sorted(entries.items()):t.add(p,arcname=n,recursive=False)
 raw=(json.dumps(manifest,indent=2)+'\n').encode();info=tarfile.TarInfo('members.json');info.size=len(raw);t.addfile(info,io.BytesIO(raw))
seen=set()
with tarfile.open(archive,'r:xz')as t:
 for i in t:
  assert i.isfile()and i.name not in seen;seen.add(i.name);raw=t.extractfile(i).read()
  if i.name=='members.json':assert json.loads(raw)==manifest
  else:assert len(raw)==manifest[i.name]['bytes']and hashlib.sha256(raw).hexdigest()==manifest[i.name]['sha256']
assert len(seen)==len(manifest)+1
for n,p in entries.items():assert pin(p)=={k:manifest[n][k]for k in ('bytes','sha256')}
r=dict(status='PASS_V23_ADJACENT_HEADER_CONTROLS'if c['failed']==0 else 'FAILED_V23_CONTROLS_RETAINED',source_freeze=pin(B/'source-freeze02.json'),source_peer=pin(B/'source-only-peer-rx02.json'),pytest=dict(path=str(B/'controls02.xml'),**pin(B/'controls02.xml'),**c),cases=[dict(name=x.get('name'),failed=any(x.find(k)is not None for k in ('failure','error')))for x in cs],observations=observations,helper_receipts=helpers,archive=dict(path=str(archive),**pin(archive)),members=len(seen),full_member_readback=True,all_original_pins_rechecked=True,MAX4118_profile_excluded=True,physical_acceptance=False,scope='Actual targeted9-control execution and complete native captures. Failure count retained without waiver; mapping still blocked until corrected schema readers and meaningful promotion control PASS plus independently reviewed actual witness evidence. Existing4ns/150byte/2GiB profile unchanged, no fullPHY or signoff claim.')
p=B/'pcie-integrity-v23-controls02-validation-20261006.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n');print(r['status'],pin(archive),len(seen),pin(p))
