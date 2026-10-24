# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Publish finite reviewed bytes only; active native work is kept out of this cut."""
from pathlib import Path
import hashlib,json,datetime
R=Path.cwd();B=Path(__file__).resolve().parent;C=R/'hw/soc/pcie-evidence/20261006-power-compact-and-timing'
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def check(p,h):assert pin(p)=={k:h[k] for k in ['bytes','sha256']},str(p)
r=json.loads((B/'closed-inputs-review.json').read_text());assert r['status']=='PASS_FINITE_SOURCES_AND_ALL_CAPSULE_MEMBERS' and r['archive_count']==17
for n,h in r['sources'].items():check(R/n,h)
compact=dict(r['compact'])
for n in ['inspect_closed_archives.py','inspect_closed_archives01.py','inspect_closed_archives02.py','closed-inputs-review01.json','closed-inputs-review01.log','closed-inputs-review02.log','closed-inputs-review03.log','closed-inputs-review.json','finite-input-probe01.json','build_inventory.py']:
 p=B/n;compact[str(p.relative_to(R))]=pin(p)
assert not C.exists();C.mkdir(parents=True);copies={};sidecars=[]
for name,h in sorted(compact.items()):
 p=R/name;check(p,h);rel=p.relative_to(R/'hw/soc/out');dest=C/'records'/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes());check(dest,h)
 copies[str(dest.relative_to(C))]=dict(source=name,**pin(dest))
 lic='CERN-OHL-W-2.0' if dest.suffix in ('.v','.sv','.spice','.sdc','.tcl','.ys') else 'Apache-2.0' if dest.suffix in ('.py','.sh') or dest.name.startswith('Makefile') else 'CC-BY-4.0'
 side=Path(str(dest)+'.license');side.write_text('SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut\nSPDX-License-Identifier: '+lic+'\n');sidecars.append(str(side.relative_to(C)))
inv=dict(status='PASS_SEVENTEEN_FINITE_CAPSULES_EXPLICIT_RESIDUAL_FAILURES',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),sources=r['sources'],files=copies,sidecars=sidecars,archives=[{k:v for k,v in a.items() if k!='member_pins'} for a in r['archives']],public_assets=r['public_assets'],members=r['members'],full_phy_acceptance=False,full_chip_final_timing_accepted=False,production_acceptance=False,scope='PowerV2 loaded455 electricalPASS/functionFAIL; CompactV2 strictnativegeometryPASS; PLLcompletedfinitewindows andactualtimestepconvergenceFAIL; V20/V21preplacementtimingregressions; RX14A/TX03actualnominalRCrouteevidence. ActiveTX05/RXrepair/V22/compactwire/loaded andNPUcloudboot outcome excluded. Firstrootinventory omittedRXarchivefromtop-levelassetlookup; additive03includesbothRXarchives/all311members. Previous01partialrecordand02inventorycountassertionpreserved; no DUTfailureinferred.')
p=C/'delivery-inventory.json';p.write_text(json.dumps(inv,indent=2)+'\n');Path(str(p)+'.license').write_text('SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut\nSPDX-License-Identifier: CC-BY-4.0\n')
(B/'source-allowlist.json').write_text(json.dumps(r['sources'],indent=2)+'\n');(B/'evidence-allowlist.json').write_text(json.dumps({str(p.relative_to(R)):pin(p) for p in C.rglob('*') if p.is_file()},indent=2)+'\n')
print(json.dumps(dict(sources=len(r['sources']),compact_files=len(copies),assets=len(r['public_assets']),archives=r['archive_count'],members=r['members'])))
