# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Finite tested local PLL capture delivery, excluding all active run journals."""
import hashlib,json
from pathlib import Path
R=Path.cwd();B=Path(__file__).resolve().parent;S=R/'hw/soc/out/pcie-pll-local-spool-v1-20261006';C=R/'hw/soc/pcie-evidence/20261006-local-pll-capture'
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def exact(p,h):assert pin(p)=={k:h[k]for k in('bytes','sha256')},str(p)
f=S/'ready-finite.json';exact(f,dict(bytes=30056,sha256='6e6d8ab24579f5336b54e55f2b0c2954350aab4678e84fbf426aea550c85ef71'));j=json.loads(f.read_text());assert len(j['source_allowlist'])==6 and len(j['evidence'])==125 and not j['native_completion']and not j['numerical_convergence']
for p,h in j['source_allowlist'].items():exact(R/p,h)
for key in['finite_package','saved_delivery_peer']:exact(j[key]['path'],j[key])
peer=json.loads(Path(j['saved_delivery_peer']['path']).read_text());assert peer['status'].startswith('PASS_')
assert j['controls']==dict(current_predicates=69,groups=dict(capture=18,core=30,publisher=21),historical_executions=303,historical_failed_executions=2)
for a in j['archives'].values():exact(a['path'],a)
assert j['archive_total_members']==3967 and len(j['assets'])==3
for p,h in j['releases'].items():
 p=Path(p);p=p if p.is_absolute()else R/p;exact(p,h);q=json.loads(p.read_text());assert q['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS'and q['publisher_revision']==4
for a in j['assets']:
 assert a['authenticated_roundtrip']and a['anonymous_roundtrip'];exact(S/'finite01'/a['name'],a)
records={str(R/p):h for p,h in j['evidence'].items()};records[str(f)]=pin(f)
# The factual peer and document must be complete before invoking this builder.
p=B/'saved-finite-peer-rx01.json';assert p.is_file();a=json.loads(p.read_text());assert a['status'].startswith('PASS_')and a['findings']==[]
for p in B.iterdir():
 if p.is_file()and p.suffix in('.py','.log','.json')and not p.name.startswith(('build-inventory','source-allowlist','evidence-allowlist','staged-allowlist','docs-tests','metadata-tests','precommit','delivery','spdx','ruff','reuse','licence')):records[str(p)]=pin(p)
assert not C.exists();C.mkdir(parents=True);copies={};sidecars=[]
for src,h in records.items():
 p=Path(src);exact(p,h);dest=C/'records'/p.relative_to(R/'hw/soc/out');dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes());exact(dest,h);copies[str(dest.relative_to(C))]=dict(source=str(p.relative_to(R)),**h);side=Path(str(dest)+'.license');side.write_text('SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut\nSPDX-License-Identifier: '+('Apache-2.0'if p.suffix=='.py'else'CC-BY-4.0')+'\n');sidecars.append(str(side.relative_to(C)))
inv=dict(status='PASS_FINITE_LOCAL_PLL_CAPTURE_CONTROLS_NATIVE_STILL_OPEN',sources=j['source_allowlist'],files=copies,sidecars=sidecars,archives=j['archives'],public_assets=j['assets'],members=3967,full_logical_data_bytes=j['full_logical_data_bytes'],controls=j['controls'],native_completion=False,numerical_convergence=False,full_phy_acceptance=False,full_chip_final_timing_accepted=False,production_acceptance=False,scope='Six tested localspool/capture/publisher sources, closed actualcontrols and launch source reviews only. Rawimmutable data and publication independent; active native/spool/publication journals excluded. Prior383.288nsERROR retained; current1us acquisition incomplete.')
p=C/'delivery-inventory.json';p.write_text(json.dumps(inv,indent=2)+'\n');Path(str(p)+'.license').write_text('SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut\nSPDX-License-Identifier: CC-BY-4.0\n');(B/'source-allowlist.json').write_text(json.dumps(j['source_allowlist'],indent=2)+'\n');(B/'evidence-allowlist.json').write_text(json.dumps({str(p.relative_to(R)):pin(p)for p in C.rglob('*')if p.is_file()},indent=2)+'\n');print(dict(status=inv['status'],sources=6,compact=len(copies),members=3967,assets=3))
