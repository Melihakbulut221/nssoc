"""Retain the exact 41-pass/one host-diagnostic-failure campaign before correction."""
from pathlib import Path
import hashlib, json, tarfile, io, xml.etree.ElementTree as ET
R=Path.cwd();B=Path(__file__).resolve().parent;D=Path('/dev/shm/nssoc-integrity-v24-full-controls01')
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
f=json.loads((B/'source-freeze02.json').read_text())
for n,v in f['sources'].items():assert pin(R/n)==v,n
s=json.loads((B/'status01.json').read_text());assert s['status']=='FAILED_CONTROLS_RETAINED' and s['returncode']==1 and not s['stop_reason']
for i in(s['controller'],s['pytest']):
 p=Path('/proc')/str(i['pid'])/'stat';assert not p.exists() or p.read_text().rsplit(') ',1)[1].split()[19]!=i['start_ticks']
cases=list(ET.parse(B/'controls01.xml').getroot().iter('testcase'));assert len(cases)==42
failed=[c for c in cases if c.find('failure') is not None];assert len(failed)==1 and failed[0].get('name')=='test_actual_miter_fault_is_observed[header_carried_always_bad]'
assert all(c.find('error') is None and c.find('skipped') is None for c in cases)
native=D/'test_actual_miter_fault_is_obs11/capture';log=(native/'simulation.log').read_text()
assert 'V24_CONTEXT_CONSUMED_MODE word=1' in log and 'Time: 50000' in log
assert (native/'sim/sim.vvp').is_file()
paths={}
for p in sorted(D.iterdir()):
 if p.is_dir() and not p.is_symlink():
  for q in p.rglob('*'):
   assert not q.is_symlink(),q
   if q.is_file():paths['native/'+str(q.relative_to(D))]=q
for p in B.iterdir():
 if p.is_file() and p.suffix in('.json','.py','.log','.xml','.vh') and p.name not in('component-members01.json',):paths['evidence/'+p.name]=p
for n in f['product_sources']:
 p=R/n;paths['sources/'+n]=p
members={n:dict(original=str(p),**pin(p)) for n,p in sorted(paths.items())}
archive=B/'pcie-integrity-v24-controls01-retained-20261006.tar.xz';assert not archive.exists()
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
(B/'controls01-members.json').write_bytes(manifest)
result=dict(status='RETAINED_V24_41_PASS_1_HOST_DIAGNOSTIC_FAILURE',pytest=dict(passed=41,failed=1,deselected=2,cases=[c.attrib for c in cases]),source_freeze=pin(B/'source-freeze02.json'),controller=pin(B/'status01.json'),xml=pin(B/'controls01.xml'),method=pin(__file__),archive=dict(path=str(archive),**pin(archive),members=len(seen)),member_manifest=pin(B/'controls01-members.json'),failure=dict(test=failed[0].get('name'),actual_native_diagnostic='V24_CONTEXT_CONSUMED_MODE word=1',actual_time_ns=50,log=pin(native/'simulation.log'),result=pin(native/'result.json'),classification='Actual mutated DUT rejected by the new independent consumed-mode observer; inherited host diagnostic whitelist did not accept that exact diagnostic. Historical host test remains FAILED.'),native_mapping_started=False)
(B/'controls01-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['archive']),flush=True)
