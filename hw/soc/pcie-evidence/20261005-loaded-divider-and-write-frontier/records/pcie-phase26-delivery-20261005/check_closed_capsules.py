from pathlib import Path
import hashlib,json,tarfile
R=Path.cwd();B=R/'hw/soc/out/pcie-phase26-delivery-20261005';V=R/'hw/soc/out/pcie-integrity-v19-20261005';P=R/'hw/soc/out/pcie-pll-acquisition-v3-20261005'
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def check(p,h):assert pin(p)=={k:h[k] for k in ('bytes','sha256')},p
v=json.loads((V/'ready-finite.json').read_text());p=json.loads((P/'restart02-ready-finite.json').read_text());assert not v['adopted'] and not v['physical_acceptance']
for n,h in v['evidence'].items():check(R/n,h)
for n,h in p['evidence_files'].items():check(R/n,h)
sources={s['repository_path']:{k:s[k] for k in ('bytes','sha256')} for s in v['source_allowlist']}
for n,h in sources.items():check(R/n,h)
assets=v['assets']+p['public_assets']
names={
 'pcie-integrity-v19-initial-witness-failure-20261005.tar.xz':V/'controls01-failure-members.json',
 'pcie-integrity-v19-functional-controls-20261005.tar.xz':V/'controls-members.json',
 'pcie-integrity-v19-native-preplacement-20261005.tar.xz':V/'native-members.json',
 'pcie-pll-acquisition-v3-abrupt-stop-20261005.tar.xz':P/'abrupt-stop-20261005/members.json'}
archives=[]
for a in assets:
 assert a['authenticated_roundtrip'] and a['anonymous_roundtrip']
 path=(P/'abrupt-stop-20261005' if a['name'].startswith('pcie-pll') else V)/a['name'];check(path,a)
 if a['name'] not in names:continue
 manifest=names[a['name']];expected=json.loads(manifest.read_text());expected=expected.get('members',expected);seen=set()
 if 'members.json' not in expected:expected['members.json']=pin(manifest)
 with tarfile.open(path,'r:xz') as t:
  for member in t:
   if not member.isfile():continue
   assert member.name not in seen and member.name in expected,member.name
   with t.extractfile(member) as f:
    h=hashlib.sha256();n=0
    while data:=f.read(1024**2):h.update(data);n+=len(data)
   assert dict(bytes=n,sha256=h.hexdigest())=={k:expected[member.name][k] for k in ('bytes','sha256')},member.name
   seen.add(member.name)
 assert seen==set(expected)
 archives.append(dict(path=str(path),pin=pin(path),manifest=str(manifest),manifest_pin=pin(manifest),members_full_readback=len(seen),asset=a))
result=dict(status='PASS_ROOT_FOUR_FINITE_CAPSULES_V19_AND_PLL_INTERRUPTION',method=pin(__file__),sources=sources,assets=assets,archives=archives,scope='NoV20ornewPLLresult; V19measuredregressionandinterruptedPLLprovenanceonly.')
(B/'closed-capsule-review.json').write_text(json.dumps(result,indent=2)+'\n');print([(Path(x['path']).name,x['members_full_readback']) for x in archives])
