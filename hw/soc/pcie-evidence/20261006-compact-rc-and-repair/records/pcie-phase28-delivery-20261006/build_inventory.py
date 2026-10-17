# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Copy explicit closed evidence and retain upstream license attribution."""
from pathlib import Path
import hashlib,json
R=Path.cwd();B=Path(__file__).absolute().parent;C=R/'hw/soc/pcie-evidence/20261006-compact-rc-and-repair'
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def check(p,h):assert pin(p)=={k:h[k] for k in ('bytes','sha256')},str(p)
d=json.loads((B/'closed-review01.json').read_text());assert d['status']=='PASS_FIVE_FINITE_CAPSULES_ALL_MEMBERS' and d['members']==592
compact=dict(d['compact']);L=R/'hw/soc/out/pcie-pll-acquisition-v3-20261005/numerical-convergence-plan01';lic=json.loads((L/'ngspice47-license-receipt.json').read_text())
for name,h in lic['files'].items():check(R/name,h);compact[name]=h
for p in [L/'ngspice47-license-receipt.json',B/'inspect_closed.py',B/'closed-review01.json',B/'closed-review01.log',Path(__file__)]:compact[str(p.relative_to(R))]=pin(p)
assert not C.exists();C.mkdir(parents=True);copies={};sidecars=[]
for name,h in sorted(compact.items()):
 p=R/name;check(p,h)
 if name.startswith('LICENSES/'):continue  # Original texts already tracked; also intact inside public capsule.
 rel=p.relative_to(R/'hw/soc/out') if p.is_relative_to(R/'hw/soc/out') else Path('repository')/p.relative_to(R)
 dest=C/'records'/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes());check(dest,h)
 copies[str(dest.relative_to(C))]=dict(source=name,**h)
 copyright='2026 Hasan Melih Akbulut'
 license='CERN-OHL-W-2.0' if dest.suffix in ('.v','.sv','.spice','.sdc','.tcl','.ys','.cir') else 'Apache-2.0' if dest.suffix in ('.py','.sh') or dest.name.startswith('Makefile') else 'CC-BY-4.0'
 if dest.name in ('dctran.c','traninit.c','ngspice47-Modified-BSD.txt'):
  copyright='1990 Regents of the University of California';license='BSD-3-Clause'
 elif dest.name=='ngspice47-COPYING.txt':copyright='2026 ngspice team';license='CC-BY-SA-4.0'
 side=Path(str(dest)+'.license');side.write_text('SPDX-FileCopyrightText: '+copyright+'\nSPDX-License-Identifier: '+license+'\n');sidecars.append(str(side.relative_to(C)))
inv=dict(status='PASS_FINITE_COMPACT_RC_REPAIR_PROOF_AND_PLL_METHODS',sources=d['sources'],files=copies,sidecars=sidecars,archives=[{k:v for k,v in a.items() if k!='member_pins'} for a in d['archives']],public_assets=d['public_assets'],members=d['members'],full_phy_acceptance=False,full_chip_final_timing_accepted=False,production_acceptance=False,scope=d['scope'])
p=C/'delivery-inventory.json';p.write_text(json.dumps(inv,indent=2)+'\n');Path(str(p)+'.license').write_text('SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut\nSPDX-License-Identifier: CC-BY-4.0\n')
(B/'source-allowlist.json').write_text(json.dumps(d['sources'],indent=2)+'\n');(B/'evidence-allowlist.json').write_text(json.dumps({str(p.relative_to(R)):pin(p) for p in C.rglob('*') if p.is_file()},indent=2)+'\n');print(dict(sources=len(d['sources']),compact=len(copies),members=d['members']))
