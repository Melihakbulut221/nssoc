"""Publish only closed V25 source/functional/negative timing evidence."""
from pathlib import Path
import hashlib,json
R=Path.cwd();O=R/'hw/soc/out';B=Path(__file__).resolve().parent;F=O/'pcie-integrity-v25-20261006';C=R/'hw/soc/pcie-evidence/20261006-integrity-command-pipeline'
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def read(p):return json.loads(Path(p).read_text())
def exact(p,w):assert pin(p)=={k:w[k]for k in('bytes','sha256')},str(p)
j=read(F/'ready-finite.json');assert j['status']=='READY_V25_CURRENT43_NATIVE_TIMING_REJECTED_NOT_ADOPTED'
assert not j['adopted'] and not j['physical_acceptance']
assert j['controls']['current']==dict(passed=43,failed=0,excluded_MAX4118=1)
assert j['controls']['historical']==dict(passed=40,failed=2)
assert j['native']['setup_ns']['slow']==-3.421986
assert len(j['source_allowlist'])==10 and len(j['evidence'])==309
paths={R/p:w for p,w in j['evidence'].items()}
for p,w in j['source_allowlist'].items():exact(R/p,w)
for p,w in paths.items():exact(p,w)
paths[F/'ready-finite.json']=pin(F/'ready-finite.json')
for name in ['build_inventory01.py']:paths[B/name]=pin(B/name)
P=O/'pcie-integrity-v25-finite-peer-rx-20261006';peer=read(P/'ready-peer01.json');assert peer['status'].startswith('PASS')
for p in P.iterdir():
 if p.is_file():paths[p]=pin(p)
for a in j['archives'].values():exact(a['path'],a)
assert j['archive_total_members']==sum(a['member_count']for a in j['archives'].values())==1562
assert len(j['assets'])==5 and all(a['authenticated_roundtrip']and a['anonymous_roundtrip']for a in j['assets'])
assert not C.exists();C.mkdir(parents=True);files={};sidecars=[]
for p,w in sorted(paths.items()):
 exact(p,w);target=C/'records'/p.relative_to(O);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(p.read_bytes());exact(target,w)
 files[str(target.relative_to(C))]=dict(source=str(p.relative_to(R)),**w)
 lic='CERN-OHL-W-2.0' if p.suffix=='.v' else 'Apache-2.0' if p.suffix=='.py' or p.name.startswith('Makefile') else 'CC-BY-4.0'
 side=Path(str(target)+'.license');side.write_text('SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut\nSPDX-License-Identifier: '+lic+'\n');sidecars.append(str(side.relative_to(C)))
data=dict(status='PASS_FINITE_V25_FUNCTIONAL43_NATIVE_REJECTED_DELIVERY',sources=j['source_allowlist'],files=files,sidecars=sidecars,archives=j['archives'],public_assets=j['assets'],members=1562,current_functional_tests=43,historical_pass=40,historical_fail=2,excluded_MAX4118=1,preplacement=j['native'],active_journals_excluded=True,adoption=False,full_phy_acceptance=False,full_chip_final_timing_accepted=False,production_acceptance=False)
p=C/'delivery-inventory.json';p.write_text(json.dumps(data,indent=2)+'\n');Path(str(p)+'.license').write_text('SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut\nSPDX-License-Identifier: CC-BY-4.0\n')
(B/'source-allowlist.json').write_text(json.dumps(j['source_allowlist'],indent=2)+'\n');(B/'evidence-allowlist.json').write_text(json.dumps({str(p.relative_to(R)):pin(p)for p in C.rglob('*')if p.is_file()},indent=2)+'\n')
print(dict(status=data['status'],sources=len(data['sources']),compact=len(files),members=1562,assets=5))
