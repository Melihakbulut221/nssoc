# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Copy only completed, independently reviewed finite numerical and RTL evidence."""
import hashlib,json
from pathlib import Path
R=Path.cwd();B=Path(__file__).resolve().parent;C=R/'hw/soc/pcie-evidence/20261006-divider-time-step-and-prefix-timing';O=R/'hw/soc/out'
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def exact(p,h):assert pin(p)=={k:h[k] for k in ('bytes','sha256')},str(p)
sources={};records={};archives=[];assets=[];ready=[]
def add(p,h=None):
 p=Path(p);h=pin(p) if h is None else {k:h[k]for k in ('bytes','sha256')};exact(p,h)
 if str(p)in records:assert records[str(p)]==h
 records[str(p)]=h
for name,review in [('pcie-tail115-layout-wire-loaded-finite-20261006','tail115-review01.json'),('pcie-tail115-halfstep-finite-20261006','numerical-finite-review01.json'),('pcie-tail115-quarterstep-finite-20261006','numerical-finite-review01.json')]:
 f=O/name/'ready-finite01.json';j=json.loads(f.read_text());peer=json.loads((B/review).read_text());assert peer['status'].startswith('PASS_')and peer['findings']==[]
 if review=='tail115-review01.json':assert peer['ready']==pin(f)
 else:assert next(x for x in peer['captures']if x['ready']['path']==str(f))['ready']==dict(path=str(f),**pin(f))
 ready.append(dict(path=str(f.relative_to(R)),**pin(f)));add(f)
 for p,h in j['sources'].items():exact(p,h);sources[str(Path(p).relative_to(R))]=h
 for p,h in j.get('method_allowlist',{}).items():add(p,h)
 for p,h in j['compact_evidence'].items():add(p,h)
 for p,h in j['public_receipts'].items():add(p,h)
 archives+=j['archives'];assets+=j['assets']
 for a in j['archives']:exact(a['path'],a);add(a['manifest'],a['manifest_pin'])
v=O/'pcie-integrity-v24-20261006';f=v/'ready-finite.json';j=json.loads(f.read_text());peer=json.loads((B/'v24-review01.json').read_text());assert peer['status'].startswith('PASS_')and peer['findings']==[]and peer['ready']==pin(f)
ready.append(dict(path=str(f.relative_to(R)),**pin(f)));add(f)
for p,h in j['source_allowlist'].items():exact(R/p,h);assert p not in sources;sources[p]=h
for p,h in j['evidence'].items():add(R/p,h)
for p,h in j['releases'].items():add(v/p,h)
archives+=peer['archives'];assets+=j['assets']
for name in ['pcie-tail115-wave-peer-rx-20261006','pcie-tail115-halfstep-wave-peer-rx-20261006','pcie-tail115-quarterstep-wave-peer-rx-20261006']:
 for p in (O/name).iterdir():
  if p.is_file():add(p)
# Closed methods/reviews only. No mutable active job journal is selected.
for p in B.iterdir():
 if p.is_file()and p.suffix in('.json','.py','.log')and not p.name.startswith(('source-allowlist','evidence-allowlist','build-inventory','precommit','delivery','docs-tests','reuse','ruff','spdx','licence')):add(p)
assert len(sources)==36 and sum(x['members']for x in archives)==2455 and len(archives)==12 and len(assets)==13
assert len({x['asset_id']for x in assets})==13
assert not C.exists();C.mkdir(parents=True);copies={};sidecars=[]
for src,h in records.items():
 p=Path(src);dest=C/'records'/p.relative_to(O);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes());exact(dest,h);copies[str(dest.relative_to(C))]=dict(source=str(p.relative_to(R)),**h)
 lic='Apache-2.0'if p.suffix=='.py'else'CC-BY-4.0';side=Path(str(dest)+'.license');side.write_text('SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut\nSPDX-License-Identifier: '+lic+'\n');sidecars.append(str(side.relative_to(C)))
inv=dict(status='PASS_FINITE_LOADED_DIVIDER_POINT_AND_REJECTED_PREFIX_TIMING_DELIVERY',sources=sources,files=copies,sidecars=sidecars,ready=ready,archives=archives,public_assets=assets,members=2455,loaded_functional={'5ps':'FAIL','2.5ps':'FAIL','1.25ps':'PASS'},numerical_convergence=False,quarterstep_vco_frequency_change_ppm=1079.469,v24_adopted=False,v24_native=j['native'],v24_control_history=j['controls'],full_phy_acceptance=False,full_chip_final_timing_accepted=False,production_acceptance=False,scope='Finite26Tail115+10V24sources, three complete34ns raw captures and independent reviews. Prior5ps/2.5psFAIL retained,1.25pspointPASS stillnumericallyunconverged. V24functionalcovered butSS/TTtimingfail, notadopted. Eighthstep, activePLLspooling, RX/TXrouting and mainchiprepair excluded.')
p=C/'delivery-inventory.json';p.write_text(json.dumps(inv,indent=2)+'\n');Path(str(p)+'.license').write_text('SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut\nSPDX-License-Identifier: CC-BY-4.0\n')
(B/'source-allowlist.json').write_text(json.dumps(sources,indent=2)+'\n');(B/'evidence-allowlist.json').write_text(json.dumps({str(p.relative_to(R)):pin(p)for p in C.rglob('*')if p.is_file()},indent=2)+'\n');print(dict(status=inv['status'],sources=len(sources),records=len(copies),archives=len(archives),members=2455,assets=13))
