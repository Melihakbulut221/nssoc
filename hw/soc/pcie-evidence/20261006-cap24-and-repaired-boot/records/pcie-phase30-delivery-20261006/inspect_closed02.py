# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read every closed capture; current native execution excluded from finite cut."""
from pathlib import Path
import hashlib,json,tarfile,datetime,zipfile
R=Path.cwd();B=Path(__file__).absolute().parent
load=lambda p:json.loads(Path(p).read_text())
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def check(p,h):assert pin(p)=={k:h[k] for k in ('bytes','sha256')},str(p)
sources={};compact={};assets=[];archives=[]
def addfile(p,h=None):
 p=Path(p);h=h or pin(p);check(p,h);compact[str(p.relative_to(R))]={k:h[k] for k in ('bytes','sha256')}
def addarchive(path,h,expected=None):
 path=Path(path);check(path,h);seen={}
 with tarfile.open(path,'r:xz') as tar:
  for m in tar:
   assert m.isfile() and not m.issparse() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts and m.name not in seen
   with tar.extractfile(m) as f:
    digest=hashlib.sha256();n=0
    while c:=f.read(1024**2):digest.update(c);n+=len(c)
   assert n==m.size;v=dict(bytes=n,sha256=digest.hexdigest());seen[m.name]=v
   if expected and m.name in expected:assert v=={k:expected[m.name][k] for k in v},m.name
 assert not expected or set(expected)<=set(seen)
 archives.append(dict(path=str(path),pin=pin(path),members=len(seen),member_pins=seen));print(path.name,len(seen),flush=True)
a=R/'hw/soc/out/pcie-cap24-layout-wire-loaded-finite-20261006';d=load(a/'ready-finite01.json');assert d['future_bias_experiment_excluded']
for n,h in d['sources'].items():check(n,h);sources[str(Path(n).relative_to(R))]={k:h[k] for k in ('bytes','sha256')}
for name,row in d['compact_evidence'].items():addfile(name,row)
for n in ['finite-snapshot01.json','ready-finite01.json','release01.json','seal_finite01.py']:
 if (a/n).exists():addfile(a/n)
for name,row in d['public_receipts'].items():addfile(name,row)
for row in d['archives']:addarchive(row['path'],row)
addarchive(d['additive_archive']['path'],d['additive_archive']);assets+=d['assets']
p=R/'hw/soc/out/npu-eco-boot-final-20261006';d=load(p/'nssoc-npu-eco-full-boot-validation-20261006.json');assert d['member_count']==211 and d['firmware_checks']==28
archive=Path(d['archive']['path']);check(archive,d['archive']);seen={}
with zipfile.ZipFile(archive) as z:
 for m in z.infolist():
  if m.is_dir():continue
  assert m.filename not in seen and not Path(m.filename).is_absolute() and '..' not in Path(m.filename).parts
  with z.open(m) as stream:v=dict(bytes=m.file_size,sha256=hashlib.file_digest(stream,'sha256').hexdigest())
  assert v==d['members'][m.filename];seen[m.filename]=v
assert seen==d['members']
archives.append(dict(path=str(archive),pin=pin(archive),members=len(seen),member_pins=seen))
for f in p.rglob('*'):
 if f.is_file() and f.suffix not in ['.zip','.xz','.pyc'] and '__pycache__' not in f.parts:addfile(f)
assets+=load(p/'release01.json')['assets']
for x in assets:assert x['authenticated_roundtrip'] and x['anonymous_roundtrip']
for a in archives:a['public_asset']=next(x for x in assets if {k:x[k] for k in ('bytes','sha256')}==a['pin'])
assert len(sources)==26 and len(archives)==5 and len(assets)==6 and sum(a['members'] for a in archives)==1294
x=dict(status='PASS_FINITE_CAP24_FAILURE_AND_REAL_NPU_BOOT_ALL_MEMBERS',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),sources=sources,compact=compact,archives=archives,public_assets=assets,members=1294,full_phy_acceptance=False,full_chip_final_timing_accepted=False,production_acceptance=False,scope='Closed actualCap24geometry/RCand34nsloadedfunctionFAIL retained; realstrictrepairedNPUbootall28/MBISTPASS. No futureV9/V23/ongoingrouteorPLLclosure included.')
(B/'closed-review01.json').write_text(json.dumps(x,indent=2)+'\n');print(dict(sources=len(sources),compact=len(compact),members=1294))
