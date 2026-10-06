"""Lossless failed functional campaign; record observed counts, never mask witness failure."""
from pathlib import Path
import hashlib,io,json,tarfile,xml.etree.ElementTree as E
R=Path.cwd();B=Path(__file__).resolve().parent;D=Path('/dev/shm/nssoc-integrity-v21-public-controls01')
def pin(p):
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
freeze=json.loads((B/'source-freeze03.json').read_text())
for p,v in freeze['sources'].items():assert pin(R/p)==v
status=json.loads((B/'controls-status01.json').read_text());assert status['status']=='FAILED_CONTROLS_RETAINED' and status['returncode']==1
cases=list(E.parse(B/'controls01.xml').getroot().iter('testcase'));assert len(cases)==27 and sum(c.find('failure') is not None for c in cases)==1
native=list(E.parse(D/'test_actual_wide_rx_full_posit0/capture/results.xml').getroot().iter('testcase'));assert len(native)==16 and sum(c.find('failure') is not None for c in native)==1
entries={}
for p in D.rglob('*'):
 if p.is_file() and not p.is_symlink() and not any(q.is_symlink() for q in p.parents if q!=D.parent):entries['raw/'+str(p.relative_to(D))]=p
for name in freeze['sources']:entries['sources/'+name]=R/name
for p in B.rglob('*'):
 if p.is_file() and not p.is_symlink() and p.suffix not in ('.xz','.gz'):entries['evidence/'+str(p.relative_to(B))]=p
manifest={name:dict(original=str(p),**pin(p)) for name,p in sorted(entries.items())}
archive=B/'pcie-integrity-v21-failed-witness01-20261006.tar.xz';assert not archive.exists()
with tarfile.open(archive,'w:xz',preset=3) as tar:
 for name,p in sorted(entries.items()):tar.add(p,arcname=name,recursive=False)
 payload=(json.dumps(manifest,indent=2)+'\n').encode();info=tarfile.TarInfo('members.json');info.size=len(payload);tar.addfile(info,io.BytesIO(payload))
seen=set()
with tarfile.open(archive,'r:xz') as tar:
 for member in tar:
  assert member.isfile() and member.name not in seen;seen.add(member.name);raw=tar.extractfile(member).read()
  if member.name=='members.json':assert json.loads(raw)==manifest
  else:assert len(raw)==manifest[member.name]['bytes'] and hashlib.sha256(raw).hexdigest()==manifest[member.name]['sha256']
assert len(seen)==len(manifest)+1
for name,p in entries.items():assert pin(p)=={k:manifest[name][k] for k in ('bytes','sha256')}
r=dict(status='PRESERVED_FAILED_V21_STAGE_WITNESS_CAMPAIGN',archive=dict(path=str(archive),**pin(archive)),members=len(seen),full_member_readback=True,all_original_pins_rechecked=True,source_freeze=pin(B/'source-freeze03.json'),pytest_observed_pass=26,pytest_observed_fail=1,public_actual_pass=15,public_actual_fail=1,unqualified_negative='fault_descriptor_survives: pytest saw an assertion, but same48ns stage-witness failed in positive; not counted meaningful',actual_failure='kind0 expected empty descriptor, actual retire_valid1/retire_has_data1 at malformed-token fault48ns. Preserve strict witness and correct stimulus only; RTLunchanged.',native_map_started=False)
(B/'failed-witness01-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],pin(archive),len(seen))
