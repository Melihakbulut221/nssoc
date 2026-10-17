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
a=R/'hw/soc/out/pcie-compact-rc-loaded-finite-20261006';d=load(a/'ready-finite01.json');assert d['status'].startswith('READY_FINITE_') and d['active_cap24_excluded']
for n,h in d['sources'].items():check(n,h);sources[str(Path(n).relative_to(R))]={k:h[k] for k in ('bytes','sha256')}
for row in d['compact_evidence'].values():addfile(row['snapshot'],row)
for n in ['finite-snapshot01.json','ready-finite01.json','release01.json','seal_finite01.py']:addfile(a/n)
for row in d['public_receipts']:addfile(row['path'],row)
for row in d['archives']:
 m=Path(row['member_manifest']);check(m,row['member_manifest_pin']);md=load(m);addfile(m);addarchive(row['path'],row,md.get('members',md.get('files',{})))
addarchive(d['additive_archive']['path'],d['additive_archive']);assets+=d['assets']
p=R/'hw/soc/out/pcie-pll-acquisition-v3-20261005/numerical-convergence-plan01';d=load(p/'ready-initial.json')
assert d['actual_controls_passed']==43 and d['previous_pair_status']=='FAIL_FINITE_NOMINAL_TIMESTEP_SCREEN'
for row in d['source_allowlist']:
 n=row['repository_path'];check(R/n,row);sources[n]={k:row[k] for k in ('bytes','sha256')}
for row in d['evidence_allowlist']:addfile(R/row['repository_path'],row)
addfile(p/'ready-initial.json');assets+=d['assets'];addarchive(d['archive']['path'],d['archive'])
t=R/'hw/soc/out/pcie-gen3-transmit-v4-repair-20261005';p=t/'repair05-preroute-preservation';d=load(p/'package.json');assert d['status']=='PASS_CLOSED_TX05_FULL_MEMBER_READBACK';addarchive(d['archive']['path'],d['archive'],d['members'])
for n in ['seal.py','package.json','release01.json','pcie-tx-repair05-preroute-validation-20261006.json']:addfile(p/n)
for row in d['members'].values():
 q=Path(row['restore_path'])
 if q.is_relative_to(R) and 'tools' not in q.parts: addfile(q,row)
# Immutable originals are in the capsule. Active DRT logs/output never enter this cut.
assets+=load(p/'release01.json')['assets']
for x in assets:assert x['authenticated_roundtrip'] and x['anonymous_roundtrip']
for a in archives:
 matches=[x for x in assets if {k:x[k] for k in ('bytes','sha256')}==a['pin']];assert len(matches)==1;a['public_asset']=matches[0]
assert len(archives)==5 and len(assets)==7
result=dict(status='PASS_FIVE_FINITE_CAPSULES_ALL_MEMBERS',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),sources=sources,compact=compact,archives=archives,public_assets=assets,members=sum(a['members'] for a in archives),full_phy_acceptance=False,full_chip_final_timing_accepted=False,production_acceptance=False,scope='Actual compact wireRC/loaded455functionFAIL plus root savedwave comparison; fixedTSTEP/tighterTMAX methods43controls and launchonly, completedTX05proof/ports before activeDRT. No active cap24/V22/RX16one/TX05route/PLLfinal/NPUboot result included.')
(B/'closed-review01.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(sources=len(sources),compact=len(compact),archives=len(archives),assets=len(assets),members=result['members'])))
