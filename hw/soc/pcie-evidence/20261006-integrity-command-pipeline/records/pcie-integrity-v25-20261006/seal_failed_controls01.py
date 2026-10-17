"""Preserve actual 40-pass/two-failure V25 campaign before any repair."""
from pathlib import Path
import hashlib,json,tarfile,io,xml.etree.ElementTree as ET
R=Path.cwd();B=Path(__file__).resolve().parent;D=Path('/dev/shm/nssoc-integrity-v25-full-controls01');O=B/'failed-controls01'
O.mkdir(exist_ok=False)
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
f=json.loads((B/'source-freeze03.json').read_text())
for n,v in f['sources'].items():assert pin(R/n)==v,n
s=json.loads((B/'status01.json').read_text());assert s['status']=='FAILED_CONTROLS_RETAINED' and s['returncode']==1 and not s['stop_reason']
for i in(s['controller'],s['pytest']):
 p=Path('/proc')/str(i['pid'])/'stat';assert not p.exists() or p.read_text().rsplit(') ',1)[1].split()[19]!=i['start_ticks']
cases=list(ET.parse(B/'controls01.xml').getroot().iter('testcase'));assert len(cases)==42
failed=[c for c in cases if c.find('failure') is not None]
assert {c.get('name') for c in failed}=={'test_actual_pending_badblock_fault_edge_and_capacity_quarantine','test_actual_command_temporal_relation[positive]'}
assert all(c.find('error') is None and c.find('skipped') is None for c in cases)
paths={}
for p in sorted(D.iterdir()):
 if p.is_dir() and not p.is_symlink():
  for q in p.rglob('*'):
   assert not q.is_symlink(),q
   if q.is_file():paths['native/'+str(q.relative_to(D))]=q
for p in B.rglob('*'):
 if O in p.parents or not p.is_file() or p.is_symlink() or p.name=='seal-failed-controls01.log':continue
 if p.suffix in('.json','.py','.log','.xml','.v','.vh'):paths['evidence/'+str(p.relative_to(B))]=p
for n in f['product_sources']:paths['sources/'+n]=R/n
members={n:dict(original=str(p.resolve()),**pin(p)) for n,p in sorted(paths.items())}
archive=O/'pcie-integrity-v25-failed-controls01-20261006.tar.xz'
manifest=json.dumps(members,indent=2).encode()+b'\n'
with tarfile.open(archive,'w:xz') as t:
 for n,p in sorted(paths.items()):
  assert pin(p)=={k:members[n][k] for k in('bytes','sha256')};t.add(p,arcname=n,recursive=False)
 i=tarfile.TarInfo('members.json');i.size=len(manifest);t.addfile(i,io.BytesIO(manifest))
seen=set()
with tarfile.open(archive,'r:xz') as t:
 for m in t:
  assert m.isfile() and m.name not in seen;seen.add(m.name);data=t.extractfile(m).read()
  if m.name=='members.json':assert data==manifest
  else:assert dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())=={k:members[m.name][k] for k in('bytes','sha256')}
assert seen==set(members)|{'members.json'}
(O/'members.json').write_bytes(manifest)
result=dict(status='RETAINED_V25_40_PASS_2_ACTUAL_POSITIVE_FAILURES',pytest=dict(passed=40,failed=2,deselected=1,cases=[c.attrib for c in cases]),source_freeze=pin(B/'source-freeze03.json'),controller=pin(B/'status01.json'),xml=pin(B/'controls01.xml'),method=pin(__file__),archive=dict(path=str(archive),**pin(archive),members=len(seen)),member_manifest=pin(O/'members.json'),failures=[dict(test=c.get('name'),detail=c.find('failure').text) for c in failed],classification='Actual positive failures retained; cause not yet accepted or waived.',native_mapping_started=False)
(O/'validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['archive']),flush=True)
