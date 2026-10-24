# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read every closed capture; current native execution excluded from finite cut."""
from pathlib import Path
import hashlib,json,tarfile,datetime
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

for base_name in ['pcie-integrity-v22-20261006','npu-eco-physical-readiness-20261006']:
 p=R/'hw/soc/out'/base_name;d=load(p/'ready-finite.json');addfile(p/'ready-finite.json')
 ss=d['source_allowlist']
 if isinstance(ss,list):ss={r['repository_path']:r for r in ss}
 for n,h in ss.items():
  q=Path(n);q=q if q.is_absolute() else R/q;check(q,h);sources[str(q.relative_to(R))]={k:h[k] for k in ('bytes','sha256')}
 for n,h in d.get('evidence',d.get('compact_evidence',{})).items():
  q=Path(n);q=q if q.is_absolute() else R/q;addfile(q,h)
 for a in d.get('assets',d.get('public_assets',[])):
  found=list(p.rglob(a['name']));assert len(found)==1,a['name'];check(found[0],a);assets.append(a)
  if a['name'].endswith('.tar.xz'):addarchive(found[0],a)
assert len(archives)==4 and len(assets)==10
for a in assets:assert a['authenticated_roundtrip'] and a['anonymous_roundtrip']
for a in archives:
 a['public_asset']=next(x for x in assets if {k:x[k] for k in ('bytes','sha256')}==a['pin'])
assert sum(x['members'] for x in archives)==874
result=dict(status='PASS_FOUR_FINITE_CAPSULES_ALL_MEMBERS',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),sources=sources,compact=compact,archives=archives,public_assets=assets,members=874,full_phy_acceptance=False,full_chip_final_timing_accepted=False,production_acceptance=False,scope='V22 cache experiment retains actualsetupFAILand historicaltest failures; sourcebound NPU readiness remainsBLOCKED awaitingstrictboot. No activeV23/Cap24/TX/RX/PLL/MAXornewchipphysicalresults inthiscut.')
(B/'closed-review01.json').write_text(json.dumps(result,indent=2)+'\n');print(dict(sources=len(sources),compact=len(compact),members=874))
