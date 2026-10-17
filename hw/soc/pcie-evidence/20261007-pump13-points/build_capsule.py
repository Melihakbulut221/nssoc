from pathlib import Path
import tarfile,hashlib,json,shutil
B=Path('hw/soc/out/pcie-tail115-pump13-characterization-20261007');P=Path(__file__).resolve().parent
assert json.loads((B/'closed-review.json').read_text())['status']=='PASS_ALL_TWELVE_SAVED_RAW_REPLAYS_AND_CURRENT_INTEGRALS'
(B/'CAPSULE-NOTICE.txt').write_text('NSSOC pump/filter thirteen-device finite experiment, 7 October 2026.\nNo full PLL, PHY or manufacturing acceptance. Sources carry their original SPDX licences.\nGenerated measurements/records are Copyright 2026 Hasan Melih Akbulut, Apache-2.0.\nSPICE circuit sources retain CERN-OHL-W-2.0.\nExternal model/runtime dependencies are pinned in source-freeze01.json and native result inputs; they are not bundled here.\nThe initial reader failed on normalized device current names; review_closed02.py corrects name mapping only.\n')
for lic in ['Apache-2.0','CERN-OHL-W-2.0']:shutil.copyfile(Path('LICENSES')/(lic+'.txt'),B/(lic+'.txt'))
def pin(p):
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
files=sorted(p for p in B.rglob('*')if p.is_file() and '__pycache__'not in p.parts)
assert all(not p.is_symlink()for p in files)
manifest={str(p.relative_to(B)):pin(p)for p in files};(P/'members.json').write_text(json.dumps(manifest,indent=2)+'\n')
A=P/'pcie-pump13-twelve-points-20261007.tar.gz'
with tarfile.open(A,'x:gz',compresslevel=1)as tar:
 for p in files:tar.add(p,arcname=str(p.relative_to(B)),recursive=False)
 tar.add(P/'members.json',arcname='CAPSULE-MEMBERS.json')
seen=set()
with tarfile.open(A,'r|gz')as tar:
 for member in tar:
  assert member.isfile() and member.name not in seen;seen.add(member.name)
  with tar.extractfile(member)as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
  expected=pin(P/'members.json')if member.name=='CAPSULE-MEMBERS.json'else manifest[member.name]
  assert member.size==expected['bytes']and actual==expected['sha256']
assert seen==set(manifest)|{'CAPSULE-MEMBERS.json'}
result=dict(status='PASS_FULL_CAPSULE_MEMBER_READBACK',archive=str(A),**pin(A),members=len(seen),physical_acceptance=False)
(P/'capsule.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
