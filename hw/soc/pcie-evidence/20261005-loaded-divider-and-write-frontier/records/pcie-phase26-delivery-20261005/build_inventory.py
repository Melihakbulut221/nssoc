# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import hashlib,json,tarfile,datetime
R=Path.cwd();B=R/'hw/soc/out/pcie-phase26-delivery-20261005';C=R/'hw/soc/pcie-evidence/20261005-loaded-divider-and-write-frontier'
V=R/'hw/soc/out/pcie-integrity-v19-20261005';P=R/'hw/soc/out/pcie-pll-acquisition-v3-20261005';L=R/'hw/soc/out/pcie-vco-v6-divider-wire-v1-20261005';X=R/'hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004/repair14a-preroute-preservation';E=R/'hw/soc/out/chip-closure-resume-20261005-1900';F=E/'finite-capture01'
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def check(p,h):assert pin(p)=={k:h[k] for k in ('bytes','sha256')},p
load=lambda p:json.loads(Path(p).read_text())
v=load(V/'ready-finite.json');p=load(P/'restart02-ready-finite.json');l=load(L/'delivery-ready.json');x=load(X/'ready-finite.json');er=load(F/'release01.json');prior=load(B/'closed-capsule-review.json')
assert er['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS' and l['actual_source_status']=='FAIL' and not x['physical_acceptance'] and not v['adopted']
sources={**prior['sources'],**l['sources']};assert len(sources)==29
for name,h in sources.items():check(R/name,h)
assets=[*prior['assets'],*l['public_assets'],*x['public_assets'],*er['assets']]
assert len(assets)==13 and all(a['authenticated_roundtrip'] and a['anonymous_roundtrip'] for a in assets)
archives=list(prior['archives'])
la=l['public_assets'][0];lp=L/la['name'];lm=Path(l['capsule_member_manifest']['path']);check(lm,l['capsule_member_manifest'])
new=[(lp,la,lm,190),(Path(x['archive']['path']),x['archive'],X/'pcie-rx-repair14a-preroute-package-20261005.json',151),(F/'npu-evq-write-frontier-review-20261005.tar.xz',er['assets'][0],F/'members.json',339)]
for path,h,mp,count in new:
 check(path,h);md=load(mp);expected=md.get('members',md)
 with tarfile.open(path,'r:xz') as t:
  actual_names=[m.name for m in t if m.isfile()]
 # Only an exact embedded copy of the external inventory may add its own row.
 for name in set(actual_names)-set(expected):
  assert name=='members.json',name
  expected[name]=pin(mp)
 seen=set()
 with tarfile.open(path,'r:xz') as t:
  for member in t:
   assert member.isfile() and member.name not in seen and member.name in expected
   with t.extractfile(member) as f:
    digest=hashlib.sha256();size=0
    while data:=f.read(1024**2):digest.update(data);size+=len(data)
   assert dict(bytes=size,sha256=digest.hexdigest())=={k:expected[member.name][k] for k in ('bytes','sha256')},member.name
   seen.add(member.name)
 assert seen==set(expected) and len(seen)==count
 archives.append(dict(path=str(path),pin=pin(path),manifest=str(mp),manifest_pin=pin(mp),members_full_readback=len(seen),asset=next(a for a in assets if a['name']==path.name)))
assert len(archives)==7 and sum(a['members_full_readback'] for a in archives)==3778
compact={**v['evidence'],**p['evidence_files'],**x['compact_files']}
for row in l['compact_evidence'].values():compact[row['source_path']]={k:row[k] for k in ('bytes','sha256')}
root_names=['review_saved_evq.py','review-saved-evq02.log','observer-source-only-peer-rx.json','write-source-only-peer-rx.json','observer-tests01.log','write-trace-tests01.log','write-native-controls01.json','docs-tests01.log','docs-tests02.log','reuse.log','reuse02.log','spdx.log','spdx02.log','precommit-verification.json','prepare_write_trace_sources.py','build_write_lock.py','seal_evq_review01.py','seal-evq-review01.log','evq37187157260/root-review02.json','evq37187157260/artifacts-api.json','evq37187157260/run-api.json','finite-capture01/members.json','finite-capture01/npu-evq-write-frontier-validation-20261005.json','finite-capture01/release01.json','finite-capture01/publication-launch01.json']
for n in root_names:compact[str((E/n).relative_to(R))]=pin(E/n)
for z in [V/'ready-finite.json',P/'restart02-ready-finite.json',L/'delivery-ready.json',X/'ready-finite.json',B/'closed-capsule-review.json',B/'check_closed_capsules.py',Path(__file__).resolve()]:compact[str(z.relative_to(R))]=pin(z)
assert not C.exists();C.mkdir(parents=True);copies={};sidecars=[]
for name,h in sorted(compact.items()):
 source=R/name;check(source,h)
 if source.name.endswith('.tar.xz'):continue
 relative=source.relative_to(R/'hw/soc/out') if source.is_relative_to(R/'hw/soc/out') else Path('native-scratch')/source.relative_to('/dev/shm')
 dest=C/'records'/relative;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(source.read_bytes());check(dest,h)
 rel=str(dest.relative_to(C));copies[rel]=dict(source=name,**pin(dest))
 lic='CERN-OHL-W-2.0' if dest.suffix in ('.v','.sv','.spice','.sdc','.tcl','.ys') else 'Apache-2.0' if dest.suffix in ('.py','.sh') or dest.name.startswith('Makefile') else 'CC-BY-4.0'
 side=Path(str(dest)+'.license');side.write_text('SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut\nSPDX-License-Identifier: '+lic+'\n');sidecars.append(str(side.relative_to(C)))
inv=dict(status='PASS_SEVEN_CLOSED_CAPSULES_AND_EXPLICIT_FAILED_RESULTS',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),sources=sources,files=copies,sidecars=sidecars,archives=archives,public_assets=assets,scope='V19preplacementregression, interruptedPLLrestartprovenance, actualloaded455dividerFAIL, RX14aproof/prerouteonly, and correctedNPUcapture/newwritepreflight. ActiveV20,PLL,TX03,RX14route andnewdividerpoweroverlay excluded. NofullPHY/qualifiedRC/mainchipfinaltiming/manufacturing acceptance.')
out=C/'delivery-inventory.json';out.write_text(json.dumps(inv,indent=2)+'\n');Path(str(out)+'.license').write_text('SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut\nSPDX-License-Identifier: CC-BY-4.0\n')
(B/'source-allowlist.json').write_text(json.dumps(sources,indent=2)+'\n');(B/'evidence-allowlist.json').write_text(json.dumps({str(p.relative_to(R)):pin(p) for p in C.rglob('*') if p.is_file()},indent=2)+'\n')
print(json.dumps(dict(source_files=len(sources),compact_copies=len(copies),capsules=len(archives),full_members=3778,assets=len(assets))))
