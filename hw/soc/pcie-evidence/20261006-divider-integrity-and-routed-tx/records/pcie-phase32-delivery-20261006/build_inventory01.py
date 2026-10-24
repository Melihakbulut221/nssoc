# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Copy explicit closed evidence and retain upstream license attribution."""
from pathlib import Path
import hashlib,json
R=Path.cwd();B=Path(__file__).absolute().parent;C=R/'hw/soc/pcie-evidence/20261006-divider-integrity-and-routed-tx'
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def check(p,h):assert pin(p)=={k:h[k] for k in ('bytes','sha256')},str(p)
d=json.loads((B/'closed-review02.json').read_text());assert d['status']=='PASS_CLOSED_PCIE_FUNCTIONAL_AND_PHYSICAL_CAPTURES_2543_MEMBERS' and d['members']==2543
compact=dict(d['compact'])
for n in ['inspect_closed01.py','inspect_closed02.py','closed-review02.json','closed-review01.log','closed-review02.log']:
 p=B/n
 if p.exists():compact[str(p.relative_to(R))]=pin(p)
compact[str(Path(__file__).relative_to(R))]=pin(__file__)
assert len(d['sources'])==36
assert not C.exists();C.mkdir(parents=True);copies={};sidecars=[]
for name,h in sorted(compact.items()):
 p=Path(h.get('copy', str(R/name)));check(p,h);dest=C/'records'/Path(name).relative_to('hw/soc/out');dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes());check(dest,h)
 copies[str(dest.relative_to(C))]=dict(source=name,**{k:h[k] for k in ('bytes','sha256')})
 license='CERN-OHL-W-2.0' if dest.suffix in ('.v','.sv','.spice','.sdc','.tcl','.ys','.cir') else 'Apache-2.0' if dest.suffix in ('.py','.sh') or dest.name.startswith('Makefile') else 'CC-BY-4.0'
 side=Path(str(dest)+'.license');side.write_text('SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut\nSPDX-License-Identifier: '+license+'\n');sidecars.append(str(side.relative_to(C)))
inv=dict(status='PASS_FINITE_DIVIDER_INTEGRITY_MAX4118_AND_ROUTED_TX_TIMING_OPEN',sources=d['sources'],files=copies,sidecars=sidecars,archives=[{k:v for k,v in a.items() if k!='member_pins'} for a in d['archives']],public_assets=d['public_assets'],members=d['members'],full_phy_acceptance=False,full_chip_final_timing_accepted=False,production_acceptance=False,native_chip_physical_evidence_included=False,scope=d['scope'])
p=C/'delivery-inventory.json';p.write_text(json.dumps(inv,indent=2)+'\n');Path(str(p)+'.license').write_text('SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut\nSPDX-License-Identifier: CC-BY-4.0\n')
(B/'source-allowlist.json').write_text(json.dumps(d['sources'],indent=2)+'\n');(B/'evidence-allowlist.json').write_text(json.dumps({str(p.relative_to(R)):pin(p) for p in C.rglob('*') if p.is_file()},indent=2)+'\n');print(dict(sources=len(d['sources']),compact=len(copies),members=d['members']))
