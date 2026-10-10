"""Finite E8/N16 closure only; excludes live acquisition and new570 source work."""
from pathlib import Path
import hashlib,json
R=Path.cwd();B=Path(__file__).resolve().parent;O=R/'hw/soc/out';C=R/'hw/soc/pcie-evidence/20261006-loaded-divider-numerical-convergence'
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def read(p):return json.loads(Path(p).read_text())
def exact(p,w):assert pin(p)=={k:w[k]for k in ('bytes','sha256')},str(p)
assert not C.exists();paths={};archives=[];assets=[];methods={}
for label in ['eighthstep','sixteenthstep']:
 F=O/f'pcie-tail115-{label}-finite-20261006';rp=F/'ready-finite01.json';j=read(rp)
 assert j['status'].startswith('READY_FINITE') and not j['physical_acceptance']
 for col in ['compact_evidence','original_evidence','public_receipts','method_allowlist']:
  for name,w in j[col].items():exact(name,w)
 for name,w in j['original_evidence'].items():paths[Path(name)]=w
 methods.update(j['method_allowlist'])
 for name in j['method_allowlist']:paths[Path(name)]=pin(name)
 paths[rp]=pin(rp)
 for name in j['public_receipts']:paths[Path(name)]=pin(name)
 for a in j['archives']:
  exact(a['path'],a);exact(a['manifest'],a['manifest_pin']);archives.append(a);paths[Path(a['manifest'])]=pin(a['manifest'])
 for a in j['assets']:
  assert a['authenticated_roundtrip'] and a['anonymous_roundtrip'];assets.append(a)
 assert j['all_archive_members']==sum(a['members']for a in j['archives'])
 if label=='eighthstep':
  p=B/'eighth-finite-review01.json';assert read(p)['status']=='PASS_ROOT_EIGHTH_FINITE343MEMBERS';paths[p]=pin(p)
 else:
  p=F/'saved-delivery-peer-pll01.json';peer=read(p);assert peer['status'].startswith('PASS') and not peer['findings'];paths[p]=pin(p)
  for name in ['sealer-source-peer-rx01.json','seal_finite01.py','complete_finite01.py']:
   p=F/name;paths[p]=pin(p)
  for p in F.glob('*delivery*pll*.py'):paths[p]=pin(p)
  for p in F.glob('*delivery*pll*.log'):paths[p]=pin(p)
assert sum(a['members']for a in archives)==1311 and len(assets)==28
assert len({a['name']for a in assets})==28
for name in ['review_eighth_finite_root01.py','build_inventory01.py']:
 p=B/name;paths[p]=pin(p)
C.mkdir(parents=True);files={};sidecars=[]
for p,w in sorted(paths.items()):
 exact(p,w);target=C/'records'/p.relative_to(O);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(p.read_bytes());exact(target,w)
 files[str(target.relative_to(C))]=dict(source=str(p.relative_to(R)),**w)
 lic='Apache-2.0' if p.suffix=='.py' else 'CC-BY-4.0';side=Path(str(target)+'.license');side.write_text('SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut\nSPDX-License-Identifier: '+lic+'\n');sidecars.append(str(side.relative_to(C)))
j=dict(status='PASS_FINITE_LOADED_DIVIDER_FIXED_ADJACENT_STEP_DELIVERY',sources={},methods=methods,files=files,sidecars=sidecars,archives=archives,public_assets=assets,members=1311,finite_functional_acceptance=True,numerical_convergence=True,numerical_scope='Only declared nominal34ns openloop0.625/0.3125ps adjacent pair,100ppm50psfixededge/nooffset. Not accuracy against8GHz or qualified models.',active_journals_excluded=True,connected570_native_results=False,PLL_lock=False,full_phy_acceptance=False,full_chip_final_timing_accepted=False,production_acceptance=False)
p=C/'delivery-inventory.json';p.write_text(json.dumps(j,indent=2)+'\n');Path(str(p)+'.license').write_text('SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut\nSPDX-License-Identifier: CC-BY-4.0\n')
(B/'source-allowlist.json').write_text('{}\n');(B/'evidence-allowlist.json').write_text(json.dumps({str(p.relative_to(R)):pin(p)for p in C.rglob('*')if p.is_file()},indent=2)+'\n');print(dict(status=j['status'],compact=len(files),methods=len(methods),members=1311,assets=28))
