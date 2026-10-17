# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Stream every finite capsule member, preserve exact source/evidence inventory."""
from pathlib import Path
import hashlib,json,tarfile,datetime
R=Path.cwd();B=Path(__file__).resolve().parent
load=lambda p:json.loads(Path(p).read_text())
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def check(p,h):assert pin(p)=={k:h[k] for k in ['bytes','sha256']},str(p)
ready=[R/'hw/soc/out'/s for s in ['pcie-integrity-v20-20261005/ready-finite.json','pcie-integrity-v21-20261005/ready-finite.json','pcie-pll-acquisition-v3-20261005/replay-step25-01/ready-finite.json','pcie-gen3-receive-prefetch-v2-20261004/repair14a-delivery/ready-finite.json']]
sources={};compact={};assets=[];local=[];maps={}
for p in ready:
 r=load(p);compact[str(p.relative_to(R))]=pin(p)
 for s in r.get('source_allowlist',[]):
  name=s['repository_path'];h={k:s[k] for k in ['bytes','sha256']};check(R/name,h);sources[name]=h
 compact.update(r.get('evidence',r.get('compact_files',{})))
 assets+=r.get('assets',r.get('public_assets',[]))
 local += list(p.parent.rglob('*.tar.xz'))
 if 'archives' in r:
  for a in r['archives']:
   assets += a['public_assets']
   path=Path(a['archive']['path']);local.append(path);mp=Path(a['manifest']['path']);check(mp,a['manifest']);maps[str(path)]=load(mp).get('members',{})
# PLL completed capsule lies alongside replay directory.
local+=list((R/'hw/soc/out/pcie-pll-acquisition-v3-20261005/completed-step25-20261006').glob('*.tar.xz'))
a=R/'hw/soc/out/pcie-analog-power-compact-finite-20261006';analog=load(a/'finite-snapshot01.json')
for name,h in analog['sources'].items():check(name,h);sources[str(Path(name).relative_to(R))]=h
for name,row in analog['compact_evidence'].items():compact[str(Path(row['snapshot']).relative_to(R))]={k:row[k] for k in ['bytes','sha256']}
for archive in analog['archives']:
 path=Path(archive['path']);local.append(path);check(path,archive)
 mp=Path(archive['member_manifest']);check(mp,archive['member_manifest_pin']);md=load(mp);maps[str(path)]=md.get('members',md.get('files',{}))
local.append(Path(analog['additive_archive']['path']))
for p in [a/'finite-snapshot01.json',a/'release01.json',R/'hw/soc/out/pcie-divider-power-and-compact-public-20261006/release01.json',R/'hw/soc/out/pcie-vco-v6-divider-power-v2-wire-v1-20261006/release-06-01.json']:
 r=load(p);compact[str(p.relative_to(R))]=pin(p)
 if 'assets' in r:
  assert r['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS';assets+=r['assets']
# TX03 actual route+RC; TX05 is deliberately excluded while work continues.
t=R/'hw/soc/out/pcie-gen3-transmit-v4-repair-20261005';tx=load(t/'repair03-peer/package.json');tp=Path(tx['archive']['path']);check(tp,tx['archive']);local.append(tp);maps[str(tp)]=tx['members'];assets+=load(t/'repair03-peer/release.json')['assets']
for sub in ['repair03-source','repair03-peer','repair03-continuation02']:
 for p in (t/sub).rglob('*'):
  if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ['.pyc','.xz']:compact[str(p.relative_to(R))]=pin(p)
for name in ['postroute_repair03.py','normalize_repair03.py','proof_gate_repair03.py','replay_repair03.py','drt_repair03.py','detailed_rc_repair03.py']:
 p=t/name;compact[str(p.relative_to(R))]=pin(p)
for name,h in compact.items():check(R/name,h)
unique={}
for a in assets:
 assert a['authenticated_roundtrip'] and a['anonymous_roundtrip']
 if a['name'] in unique:assert unique[a['name']]==a
 unique[a['name']]=a
assets=list(unique.values());archives=[]
for asset in assets:
 if not asset['name'].endswith('.tar.xz'):continue
 matches=[p for p in local if p.is_file() and p.stat().st_size==asset['bytes']]
 exact=[]
 for p in matches:
  if pin(p)=={k:asset[k] for k in ['bytes','sha256']}:exact.append(p)
 assert exact,asset['name'];p=exact[0];expected=maps.get(str(p),{});seen={}
 with tarfile.open(p,'r:xz') as tar:
  for m in tar:
   assert m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts and m.name not in seen
   with tar.extractfile(m) as f:
    h=hashlib.sha256();size=0
    while data:=f.read(1024**2):h.update(data);size+=len(data)
   assert size==m.size;row=dict(bytes=size,sha256=h.hexdigest())
   if m.name in expected:assert row=={k:expected[m.name][k] for k in row},m.name
   seen[m.name]=row
 assert not expected or set(expected)<=set(seen),(p,'external manifest has missing members')
 rec=dict(path=str(p),pin=pin(p),asset=asset,members=len(seen),matched_external_members=len(set(expected)&set(seen)),member_pins=seen)
 archives.append(rec);print(asset['name'],len(seen),flush=True)
assert any('pcie-rx-repair14a-route' in a['asset']['name'] for a in archives), 'RX archive must be included'
assert len(archives)==17
result=dict(status='PASS_FINITE_SOURCES_AND_ALL_CAPSULE_MEMBERS',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),sources=sources,compact=compact,public_assets=assets,archives=archives,archive_count=len(archives),members=sum(x['members'] for x in archives),method=pin(__file__),physical_acceptance=False,full_phy_acceptance=False,full_chip_final_timing_accepted=False,scope='Finite V20/V21,PLLstep25 replay+failedtimestep pair,actualRX14A/TX03nominalroutes,PowerV2electricalPASS/functionFAIL andCompactV2nativegeometry. ActiveTX05,RXrepair,V22,compactwire/loaded not included. No new native run.')
(B/'closed-inputs-review.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['status','archive_count','members']}))
