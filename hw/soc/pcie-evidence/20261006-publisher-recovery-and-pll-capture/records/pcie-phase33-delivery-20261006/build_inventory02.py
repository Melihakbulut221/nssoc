# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Finite exact publisher fix and preserved incomplete PLL capture delivery."""
import hashlib,json,tarfile
from pathlib import Path
R=Path.cwd();B=Path(__file__).resolve().parent;P=R/'hw/soc/out/publisher-reconciliation-20261006';C=R/'hw/soc/pcie-evidence/20261006-publisher-recovery-and-pll-capture';L=R/'hw/soc/out/pcie-pll-acquisition-v3-20261005/numerical-convergence-plan01/launch01'
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def exact(p,h):assert pin(p)=={k:h[k] for k in ('bytes','sha256')},str(p)
v=json.loads((P/'pcie-publisher-v4-native-controls-validation-20261006.json').read_text());w=json.loads((P/'pcie-pll-max125-publication120-failure-validation-20261006.json').read_text())
peer=json.loads((P/'source-saved-peer-pll01.json').read_text());assert peer['status']=='PASS_PUBLISHER_V4_SOURCE_AND_15_ACTUAL_CONTROLS' and peer['findings']==[]
assert w['status']=='PASS_INDEPENDENT_FULL_FAILED_PLL_CAPSULE_READBACK' and w['original_result_unmodified']
archives=[];total=0
for item in (v,w):
 a=item['archive'];p=Path(a['path']);exact(p,a)
 if item is v: members=item['members']
 else:
  mp=Path(item['member_manifest']['path']);exact(mp,item['member_manifest']);m=json.loads(mp.read_text());members=dict(m);members['members.json']=pin(mp)
 seen={}
 with tarfile.open(p,'r|xz') as tf:
  for m in tf:
   assert m.isfile() and m.name not in seen
   seen[m.name]=dict(bytes=m.size,sha256=hashlib.file_digest(tf.extractfile(m),'sha256').hexdigest());assert seen[m.name]=={k:members[m.name][k] for k in ('bytes','sha256')}
 assert seen.keys()==members.keys() and len(seen)==a['members'];total+=len(seen);archives.append(a)
assert total==2704
pub=json.loads((P/'closed-captures-release01.json').read_text());recovery=json.loads((P/'recovered-part120-release01.json').read_text())
assets=[]
for rec in (pub,recovery):
 assert rec['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS'
 assert rec['publisher_revision']==4
 for a in rec['assets']:
  assert a['authenticated_roundtrip'] and a['anonymous_roundtrip']
  f=next(x for x in rec['files'] if x['name']==a['name']);exact(f['path'],a);assets.append(a)
assert len(assets)==5 and len({x['asset_id'] for x in assets})==5
sources=v['sources'];assert len(sources)==2
for name,h in sources.items():exact(R/name,h)
names=['diagnosis01.json','source-freeze01.json','source-saved-peer-pll01.json','source-saved-peer-pll01.log','review_source_saved_pll01.py','controls01.log','controls01.xml','controls02.log','controls02.xml','ruff01.log','saved-metadata-summary01.json','seal_closed01.py','seal-closed01.log','control-seal01.json','review_pll_failure01.py','review_pll_failure02.py','review-pll-failure01.log','review-pll-failure02.log','recovered-part120-publish01.log','recovered-part120-release01.json','recovered-part120-release01.transport/attempts.json','recovered-part120-release01.transport/reconciliation.json','closed-captures-publish01.log','closed-captures-release01.json','closed-captures-release01.transport/attempts.json','closed-captures-release01.transport/reconciliation.json','pcie-publisher-v4-native-controls-validation-20261006.json','pcie-pll-max125-publication120-failure-validation-20261006.json']
paths=[P/n for n in names]+[x for x in (P/'peer-pll-attempt01').rglob('*') if x.is_file()]+[L/'terminal-preservation09.json',L/'terminal-members09.json',Path(__file__),B/'build_inventory01.py',B/'build-inventory01.log']
assert not C.exists();C.mkdir(parents=True);copies={};sidecars=[]
for p in paths:
 assert p.is_file(),str(p);dest=C/'records'/p.relative_to(R/'hw/soc/out');dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes());h=pin(p);exact(dest,h)
 copies[str(dest.relative_to(C))]=dict(source=str(p.relative_to(R)),**h)
 lic='Apache-2.0' if p.suffix=='.py' else 'CC-BY-4.0';side=Path(str(dest)+'.license');side.write_text('SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut\nSPDX-License-Identifier: '+lic+'\n');sidecars.append(str(side.relative_to(C)))
inv=dict(status='PASS_PUBLISHER_V4_RECOVERY_PRESERVED_PLL_INCOMPLETE',sources=sources,files=copies,sidecars=sidecars,archives=archives,public_assets=assets,members=total,actual_publisher_controls=15,last_PLL_simulation_ns=383.288,original_PLL_result='ERROR_NATIVE_OR_STREAM_CAPTURE',full_phy_acceptance=False,full_chip_final_timing_accepted=False,production_acceptance=False,scope='Publisher transport correction and preserved failed numerical run only. Original383.288ns result remains ERROR; recovery uploads exact existingpart120 without native restart. Fifteen actual owned-child controls PASS, two full archives2704members rehashed and public full dual byte readbacks. Ongoing new spooling, new numerical runs, main chip, RX/TX routes, V10/V24 are excluded.')
p=C/'delivery-inventory.json';p.write_text(json.dumps(inv,indent=2)+'\n');Path(str(p)+'.license').write_text('SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut\nSPDX-License-Identifier: CC-BY-4.0\n')
(B/'source-allowlist.json').write_text(json.dumps(sources,indent=2)+'\n');(B/'evidence-allowlist.json').write_text(json.dumps({str(p.relative_to(R)):pin(p) for p in C.rglob('*') if p.is_file()},indent=2)+'\n');print(dict(status=inv['status'],sources=len(sources),records=len(copies),members=total,assets=len(assets)))
