# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Rehash closed divider RC and RX13 captures without adopting unfinished work."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,tarfile
R=Path.cwd();B=R/'hw/soc/out/pcie-phase25-delivery-20261005';C=R/'hw/soc/pcie-evidence/20261005-divider-wire-and-rx13-timing'
D=R/'hw/soc/out/pcie-divider-v7-wire-rc-v1-20261005';X=R/'hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004/repair13-delivery'
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def check(p,h):assert pin(p)=={k:h[k] for k in ('bytes','sha256')},p
assert not C.exists()
d=json.loads((D/'delivery-ready.json').read_text());x=json.loads((X/'ready-finite.json').read_text())
assert not d['new_source_pins'] and not x['new_product_source_allowlist'] and not x['physical_acceptance'] and not x['qualified_rc']
compact={**d['compact_allowlist'],**x['compact_files']};assert len(compact)==450
for name,h in compact.items():check(R/name,h)
archives=[];assets=[]
for group in d['public_captures'].values():
 a=group['asset'];p=next(R/n for n in d['capsules'] if Path(n).name==a['name']);manifest=R/group['manifest']['path'];check(manifest,group['manifest'])
 archives.append(dict(path=str(p),pin={k:a[k] for k in ('bytes','sha256')},manifest=str(manifest),members=group['members']));assets.append(a)
for group in x['archives']:
 a=group['archive'];manifest=R/group['manifest']['path'];check(manifest,group['manifest'])
 archives.append(dict(path=a['path'],pin={k:a[k] for k in ('bytes','sha256')},manifest=str(manifest),members=group['members']));assets.extend(group['public_assets'])
assert len(archives)==4 and len(assets)==8
for a in assets:assert a['authenticated_roundtrip'] and a['anonymous_roundtrip']
for record in archives:
 p=Path(record['path']);check(p,record['pin']);md=json.loads(Path(record['manifest']).read_text());expected=md.get('members',md);seen=set()
 with tarfile.open(p,'r:xz') as archive:
  for member in archive:
   if not member.isfile():continue
   assert member.name not in seen and member.name in expected,member.name
   with archive.extractfile(member) as f:
    digest=hashlib.sha256();size=0
    while data:=f.read(1024**2):digest.update(data);size+=len(data)
   assert dict(bytes=size,sha256=digest.hexdigest())=={k:expected[member.name][k] for k in ('bytes','sha256')},member.name
   seen.add(member.name)
 assert seen==set(expected) and len(seen)==record['members'];record['members_full_readback']=len(seen)
assert sum(a['members'] for a in archives)==484
C.mkdir(parents=True);copies={};sidecars=[]
def copy(p,relative):
 dest=C/relative;assert not dest.exists();dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes());assert pin(dest)==pin(p)
 copies[str(relative)]={'source':str(p.relative_to(R)),**pin(dest)}
 licence='Apache-2.0' if dest.suffix in ('.py','.sh') or dest.name.startswith('Makefile') else 'CERN-OHL-W-2.0' if dest.suffix in ('.v','.sv','.spice','.sdc','.tcl','.ys') else 'CC-BY-4.0'
 side=Path(str(dest)+'.license');side.write_text('SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut\nSPDX-License-Identifier: '+licence+'\n');sidecars.append(str(side.relative_to(C)))
for p in sorted(compact):copy(R/p,Path('records')/Path(p).relative_to('hw/soc/out'))
copy(D/'delivery-ready.json',Path('divider-ready.json'));copy(X/'ready-finite.json',Path('rx13-ready.json'));copy(Path(__file__),Path('curation/build_inventory.py'))
inv={'status':'PASS_ROOT_FOUR_FULL_CLOSED_CAPSULES_DIVIDER_RC_AND_RX13','utc':datetime.now(timezone.utc).isoformat(),'sources':{},'files':copies,'sidecars':sidecars,'archives':archives,'public_assets':assets,'native_product_change_claimed':False,'scope':'Divider wire-only native graph312R618C37conductors205anchors and13faults; RX13 routerDRC0 nominalSSsetup-.441603 hold+.021680ns. NoqualifiedPEX/fullPHY/mainchip acceptance; interruptedPLL/MAXandfutureRX14/V19 excluded.'}
p=C/'delivery-inventory.json';p.write_text(json.dumps(inv,indent=2)+'\n');Path(str(p)+'.license').write_text('SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut\nSPDX-License-Identifier: CC-BY-4.0\n')
(B/'evidence-allowlist.json').write_text(json.dumps({str(p.relative_to(R)):pin(p) for p in C.rglob('*') if p.is_file()},indent=2)+'\n')
print(json.dumps({'copied':len(copies),'archive_members':484,'archives':4,'assets':8}))
