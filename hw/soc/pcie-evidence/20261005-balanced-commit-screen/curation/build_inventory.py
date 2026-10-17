# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Verify closed V18 captures and stage no live maximum-packet experiments."""
from pathlib import Path
import json,hashlib,tarfile,datetime
R=Path.cwd();B=R/'hw/soc/out/pcie-phase24-delivery-20261005';S=R/'hw/soc/out/pcie-integrity-v18-20261005';C=R/'hw/soc/pcie-evidence/20261005-balanced-commit-screen'
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def check(p,h):assert pin(p)=={k:h[k] for k in ('bytes','sha256')},p
ready=json.loads((S/'ready-finite.json').read_text());assert not ready['adopted'] and not ready['physical_acceptance']
assert not C.exists();C.mkdir(parents=True)
sources={row['repository_path']:{k:row[k] for k in ('bytes','sha256')} for row in ready['source_allowlist']}
for p,h in sources.items():check(R/p,h)
assert len(sources)==9
members_by_name={'pcie-integrity-v18-public-controls-20261005.tar.xz':'public-controls-members01.json','pcie-integrity-v18-combined-functional-controls-20261005.tar.xz':'functional-controls-members.json','pcie-integrity-v18-native-preplacement-20261005.tar.xz':'native-members.json'}
archives=[]
for a in ready['assets']:
 assert a['authenticated_roundtrip'] and a['anonymous_roundtrip']
 p=S/a['name'];check(p,a)
 if a['name'] not in members_by_name:continue
 expected=json.loads((S/members_by_name[a['name']]).read_text());seen=set()
 assert 'members.json' not in expected
 expected['members.json']={'original_path':str(S/members_by_name[a['name']]),**pin(S/members_by_name[a['name']])}
 with tarfile.open(p,'r:xz') as t:
  for m in t:
   if not m.isfile():continue
   assert m.name not in seen and m.name in expected
   h=hashlib.sha256();size=0
   with t.extractfile(m) as f:
    while data:=f.read(1024**2):h.update(data);size+=len(data)
   assert set(expected[m.name])=={'original_path','bytes','sha256'} and Path(expected[m.name]['original_path']).is_absolute()
   assert {'bytes':size,'sha256':h.hexdigest()}=={k:expected[m.name][k] for k in ('bytes','sha256')},m.name
   seen.add(m.name)
 assert seen==set(expected)
 archives.append(dict(asset=a,members_full_readback=len(seen),member_manifest=members_by_name[a['name']]))
assert len(archives)==3 and sum(x['members_full_readback'] for x in archives)==391
copies={};sidecars=[]
def copy(p,rel,expected):
 p=Path(p);check(p,expected);dest=C/rel;assert not dest.exists();dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes());check(dest,expected)
 copies[str(rel)]=dict(source=str(p.relative_to(R)),**pin(dest))
 lic='CERN-OHL-W-2.0' if dest.suffix in ('.v','.sv','.sdc','.tcl','.ys','.spice') else 'Apache-2.0' if dest.suffix in ('.py','.sh') or dest.name.startswith('Makefile') else 'CC-BY-4.0'
 side=Path(str(dest)+'.license');side.write_text('SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut\nSPDX-License-Identifier: '+lic+'\n');sidecars.append(str(side.relative_to(C)))
for name,h in ready['evidence'].items():
 p=R/name;check(p,h)
 if p.name.endswith('.tar.xz'):continue
 assert 'max4118-01' not in p.parts
 copy(p,Path('records')/p.relative_to(S),h)
copy(S/'ready-finite.json',Path('ready-finite.json'),pin(S/'ready-finite.json'))
copy(Path(__file__),Path('curation/build_inventory.py'),pin(Path(__file__)))
inventory=dict(status='PASS_ROOT_CLOSED_V18_SOURCE_AND_THREE_FULL_PUBLIC_CAPSULES',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),sources=sources,files=copies,sidecars=sidecars,archives=archives,public_assets=ready['assets'],scope='21selectedfunctionalexecutions/20distinct; MAX4118subtreeexcluded/live. Real79.384psSSregressionvsV17; noadoption/physicalclosure. Originalstimulusdefectcampaignpreserved.',source_ready=pin(S/'ready-finite.json'))
p=C/'delivery-inventory.json';p.write_text(json.dumps(inventory,indent=2)+'\n');Path(str(p)+'.license').write_text('SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut\nSPDX-License-Identifier: CC-BY-4.0\n')
(B/'source-allowlist.json').write_text(json.dumps(sources,indent=2)+'\n');(B/'evidence-allowlist.json').write_text(json.dumps({str(p.relative_to(R)):pin(p) for p in C.rglob('*') if p.is_file()},indent=2)+'\n')
print(json.dumps(dict(sources=len(sources),copied_evidence=len(copies),sidecars=len(sidecars),capsules=3,members=391,assets=len(ready['assets']))))
