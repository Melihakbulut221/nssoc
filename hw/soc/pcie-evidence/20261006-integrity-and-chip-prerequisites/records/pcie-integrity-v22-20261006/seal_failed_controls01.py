"""Preserve actual26PASS/3FAIL controls and exact source before harness repair."""
from pathlib import Path
import hashlib,io,json,tarfile,xml.etree.ElementTree as ET
B=Path(__file__).resolve().parent
R=Path.cwd();D=Path('/dev/shm/nssoc-integrity-v22-public-controls01')
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
f=json.loads((B/'source-freeze02.json').read_text())
for p,v in f['sources'].items():assert pin(R/p)==v
j=json.loads((B/'controls-status01.json').read_text());assert j['status']=='FAILED_CONTROLS_RETAINED'and j['returncode']==1
cases=ET.parse(B/'controls01.xml').findall('.//testcase');assert len(cases)==29
failed=[c.attrib['name']for c in cases if c.find('failure')is not None];assert len(failed)==3
for birth in [j['controller'],j['pytest']]:
 p=Path(f"/proc/{birth['pid']}/stat")
 if p.exists():assert p.read_text().rsplit(') ',1)[1].split()[19]!=birth['start_ticks']
paths={Path(p).resolve()for p in f['sources']}
paths.update(p for p in B.rglob('*')if p.is_file()and not p.is_symlink()and p.name!='active-checkpoint.json'and not p.name.endswith('.log'))
paths.update(p for p in B.glob('*.log')if p.name!='seal-failed-controls01.log')
paths.update(p for p in D.rglob('*')if p.is_file()and not p.is_symlink())
inventory={str(p):pin(p)for p in sorted(paths)}
out=B/'pcie-integrity-v22-failed-functional01-20261006.tar.xz';assert not out.exists()
with tarfile.open(out,'w:xz',preset=1)as tar:
 for p,v in inventory.items():tar.add(p,arcname=p.lstrip('/'),recursive=False)
 raw=(json.dumps(inventory,indent=2)+'\n').encode();info=tarfile.TarInfo('members.json');info.size=len(raw);tar.addfile(info,io.BytesIO(raw))
with tarfile.open(out,'r:xz')as tar:
 assert len(tar.getmembers())==len(inventory)+1
 for p,v in inventory.items():
  data=tar.extractfile(p.lstrip('/')).read();assert dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())==v
 assert json.loads(tar.extractfile('members.json').read())==inventory
for p,v in inventory.items():assert pin(p)==v
receipt=dict(status='PRESERVED_ACTUAL_V22_26PASS3FAIL_NO_NATIVE_MAP',source_freeze=pin(B/'source-freeze02.json'),
 pytest_passed=26,pytest_failed=3,MAX4118_deselected=2,failed=failed,archive=dict(path=str(out),**pin(out)),
 members=len(inventory)+1,full_member_readback=True,all_originals_unchanged=True,files=inventory,
 diagnosis='Positive new17th witness observed before followingnegedge counter update; staleowner/faultowner negatives not meaningful yet. ProductRTL unchanged; preserve source/raw before additiveobserver/stimulus repair. No native mapping.')
(B/'failed-controls01-validation.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(receipt['status'],receipt['archive'],receipt['members'])
