# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Add closed current-source V23 regression and independent document peers."""
import hashlib,json,tarfile
from pathlib import Path
R=Path.cwd();B=Path(__file__).resolve().parent;C=R/'hw/soc/pcie-evidence/20261006-divider-integrity-and-routed-tx'
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def exact(p,h):assert pin(p)=={k:h[k] for k in ('bytes','sha256')},str(p)
invp=C/'delivery-inventory.json';inv=json.loads(invp.read_text());assert inv['members']==2543 and len(inv['archives'])==10
(B/'base-delivery-inventory01.json').write_bytes(invp.read_bytes())
vpath=B/'pcie-integrity-v23-current-full-controls04-validation-20261006.json';v=json.loads(vpath.read_text())
peerpath=B/'doc143-review-pll02.json';peer=json.loads(peerpath.read_text());assert peer['findings']==[] and peer['status']=='PASS_INDEPENDENT_DOC143_ADDITIVE_AND_CURRENT_V23_36_CONTROLS_SAVED_REVIEW'
assert v['passed']==36 and v['failed']==v['skipped']==0 and len(v['members'])==316
exact(vpath,peer['validation']);exact(R/'docs/143-pcie-divider-and-routed-transmitter.md',peer['document']);exact(R/'docs/img/pcie-bias8-latch-loss-20261006.png',peer['plot'])
exact(B/'v23-final-controls01/result.json',peer['result']);exact(B/'v23-final-controls01/tests.xml',peer['pytest'])
for p,h in v['sources'].items():exact(R/p,h);assert inv['sources'][p]==h
ap=Path(v['archive']['path']);exact(ap,v['archive']);seen={}
with tarfile.open(ap,'r|xz') as tf:
 for m in tf:
  assert m.isfile() and m.name not in seen
  seen[m.name]={'bytes':m.size,'sha256':hashlib.file_digest(tf.extractfile(m),'sha256').hexdigest()}
  assert seen[m.name]=={k:v['members'][m.name][k] for k in ('bytes','sha256')}
assert seen.keys()==v['members'].keys()
pubpath=B/'v23-final-release01.json';pub=json.loads(pubpath.read_text());exact(pubpath,peer['release']);assert pub['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS' and pub['tag']=='evidence-20261006-pcie-closure'
assets=pub['assets'];assert len(assets)==2
for a in assets:
 assert a['authenticated_roundtrip'] and a['anonymous_roundtrip'];exact(B/a['name'],a)
assert len({a['asset_id'] for a in inv['public_assets']+assets})==21
names=['base-delivery-inventory01.json','add_current_controls02.py','run_v23_final_controls01.py','seal_v23_final_controls01.py','v23-final-launch01.json','v23-final-controller01.log','v23-final-seal01.log','v23-final-publish01.log','v23-final-release01.json','pcie-integrity-v23-current-full-controls04-validation-20261006.json','v23-final-controls01/owned-processes.json','v23-final-controls01/result.json','v23-final-controls01/tests.xml','v23-final-controls01/tests.log','doc143-review-pll01.py','doc143-review-pll01.log','doc143-review-pll01.json','doc143-review-pll02.py','doc143-review-pll02.log','doc143-review-pll02.json','doc143-peer02-attempt01/doc143-review-pll02.py','doc143-peer02-attempt01/doc143-review-pll02.log','v23-final-release01.transport/attempts.json','new-evidence-release-notes.md','new-evidence-release-create01.log','new-evidence-release-readback01.json']
for name in names:
 p=B/name;assert p.is_file();dest=C/'records'/B.name/name;assert not dest.exists();dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes());h=pin(p);exact(dest,h)
 inv['files'][str(dest.relative_to(C))]=dict(source=str(p.relative_to(R)),**h)
 license='Apache-2.0' if dest.suffix=='.py' else 'CC-BY-4.0';side=Path(str(dest)+'.license');side.write_text('SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut\nSPDX-License-Identifier: '+license+'\n');inv['sidecars'].append(str(side.relative_to(C)))
inv['archives'].append(dict(**v['archive'],members=316,public_asset=next(a for a in assets if a['name']==ap.name)))
inv['public_assets']+=assets;inv['members']=2859
inv['current_v23_regression']={'passed':36,'failed':0,'deselected_MAX4118':2,'earlier_47_execution_history_preserved':True,'validation':pin(vpath),'independent_peer':pin(peerpath)}
inv['scope']+=' Additive current final V23 source regression passes36/36 with2 MAX4118 cases deselected; historical47 executions remain unmodified.'
invp.write_text(json.dumps(inv,indent=2)+'\n')
for rel,h in inv['files'].items():exact(C/rel,h)
(B/'evidence-allowlist.json').write_text(json.dumps({str(p.relative_to(R)):pin(p) for p in C.rglob('*') if p.is_file()},indent=2)+'\n')
print(dict(status='PASS_PHASE32_CLOSED_ADDITIVE',sources=len(inv['sources']),compact=len(inv['files']),archives=len(inv['archives']),members=inv['members'],public_assets=len(inv['public_assets'])))
