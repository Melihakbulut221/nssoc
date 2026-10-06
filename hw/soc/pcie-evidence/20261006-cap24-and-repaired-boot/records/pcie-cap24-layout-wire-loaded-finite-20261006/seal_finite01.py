# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import hashlib,io,json,shutil,tarfile
R=Path.cwd();F=Path(__file__).resolve().parent;O=R/'hw/soc/out';B=O/'pcie-divider-v8-cap-v1-20261006';G=O/'pcie-divider-v8-cap-v1-wire-v1-20261006';C=O/'pcie-divider-v8-cap-v1-wire-rc-v1-20261006';L=O/'pcie-vco-v6-divider-cap24-v1-wire-v1-20261006';W=O/'pcie-cap24-wave-root-20261006'
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def verify_archive(path,members):
 seen={}
 with tarfile.open(path,'r|xz')as t:
  for m in t:
   assert m.isfile()and m.name not in seen;seen[m.name]=dict(bytes=m.size,sha256=hashlib.file_digest(t.extractfile(m),'sha256').hexdigest())
 assert seen=={n:{k:v[k]for k in ('bytes','sha256')}for n,v in members.items()}
 return len(seen)
assert not (F/'finite-snapshot01.json').exists()
sources=dict(json.loads((B/'source-freeze01.json').read_text())['product_sources'])
for p,v in json.loads((L/'source-freeze01.json').read_text())['new_sources'].items():sources[str(R/p)]=v
assert len(sources)==26 and sources=={p:pin(p)for p in sources}
components=[(B,'native-archive01.json','pcie-divider-v8-cap-v1-native01.tar.xz','release-native01.json'),(C,'closed-native-backup01.json','pcie-divider-v8-cap-v1-wire-native01.tar.xz','release-native01.json'),(L,'members-06-01.json','pcie-vco-v6-divider-cap24-v1-wire-06-01.tar.xz','release-06-01.json')]
archives=[];assets=[];public={}
for root,manifest,cap,release in components:
 j=json.loads((root/manifest).read_text());members=j if root==L else j['members'];a=root/cap;n=verify_archive(a,members);pub=json.loads((root/release).read_text());assert pub['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS';asset=next(x for x in pub['assets']if x['name']==cap);assert {k:asset[k]for k in ('bytes','sha256')}==pin(a)and asset['authenticated_roundtrip']and asset['anonymous_roundtrip'];archives.append(dict(path=str(a),**pin(a),members=n,manifest=str(root/manifest),manifest_pin=pin(root/manifest),public_receipt=str(root/release)));assets.append(asset);public[str(root/release)]=pin(root/release)
assert json.loads((B/'native-saved-peer-rx.json').read_text())['findings']==[]
assert json.loads((G/'saved-geometry-peer.json').read_text())['findings']==[]
assert json.loads((C/'saved-rc-peer-pll.json').read_text())['findings']==[]
assert json.loads((L/'native06-controller.json').read_text())['status']=='CLOSED_FINITE_NATIVE_RESULT'
assert json.loads((L/'validation-06-01.json').read_text())['native_status']=='FAIL_NATIVE_LOADED_FEEDBACK_SCREEN'
rootwave=json.loads((W/'result.json').read_text())
# Exact independent root result and plot are preserved, not reinterpreted by this packer.
allowed={'.json','.py','.log','.xml','.txt','.md','.lvs','.spice','.cir','.license','.png'};paths=[]
for root in (B,G,C,L,W):
 for p in root.rglob('*'):
  if p.is_file()and p.suffix in allowed and '__pycache__'not in p.parts:paths.append((root.name+'/'+str(p.relative_to(root)),p))
compact={};originals={};files={}
for rel,p in sorted(paths):
 target=F/'compact-evidence'/rel;target.parent.mkdir(parents=True,exist_ok=True);assert not target.exists();shutil.copyfile(p,target);assert pin(p)==pin(target);compact[str(target)]=pin(target);originals[str(p)]=pin(p);files['compact-evidence/'+rel]=target
for p,v in sources.items():files['project/'+str(Path(p).relative_to(R))]=Path(p)
for name in ('Apache-2.0','CERN-OHL-W-2.0','CC-BY-4.0'):files['licenses/'+name+'.txt']=R/'LICENSES'/(name+'.txt')
notice=F/'NOTICES.txt';notice.write_text('Project methods Apache-2.0; circuit sources CERN-OHL-W-2.0; generated native evidence and waveforms CC-BY-4.0. Copyright2026HasanMelihAkbulut. Upstream PDK model source implementations and compiled runtimes are not redistributed; their exact hashes remain in receipts. Cap24 is only a finite standalone divider prerequisite: full34ns loaded455 division fails despite all455 declared electrical screens passing. Early~2.029GHz division loses stability near20.6ns; no early-window acceptance. Explicit ideal body/RC-reference boundaries remain, no qualified RF/substrate/PVT/ESD/PLL/fullPHY/main-chip closure. Physical21gates+6geometry faults, seven extraction stages, five binding controls, native wire RC+13corruptions, source28+4controls and every prior failure retained. No older V7 WIP is included as a new product.\n');files['NOTICES.txt']=notice;files['seal_finite01.py']=Path(__file__)
members={n:pin(p)for n,p in files.items()};cap=F/'pcie-cap24-layout-wire-loaded-additive01.tar.xz'
with tarfile.open(cap,'w:xz',preset=1)as t:
 for n,p in sorted(files.items()):
  data=p.read_bytes();i=tarfile.TarInfo(n);i.size=len(data);i.mtime=0;i.mode=0o644;t.addfile(i,io.BytesIO(data))
assert verify_archive(cap,members)==len(members)
(F/'additive-members01.json').write_text(json.dumps(members,indent=2)+'\n')
snapshot=dict(status='SEALED_FINITE_CAP24_LAYOUT_WIRE_AND_LOADED_FAILURE_PENDING_ADDITIVE_PUBLICATION',sources=sources,compact_evidence=compact,original_evidence=originals,archives=archives,additive_archive=dict(path=str(cap),**pin(cap),members=len(members),manifest=str(F/'additive-members01.json')),source_files=len(sources),compact_files=len(compact),public_receipts=public,assets=assets,root_owns_git_delivery=True,explicit_limits=['Full34ns division FAIL retained; early-time improvement is descriptive only','All455 electrical screens pass; same limits and model inventory','Wire-only RC with85 intrinsic body terminals separately retained; not qualified substrate/RF PEX','Standalone divider and schematic302-deviceCMOS feedback; no fullPHY/main-chip integration'],root_wave_inputs={str(p):pin(p)for p in W.iterdir()if p.is_file()},future_bias_experiment_excluded=True)
assert sources=={p:pin(p)for p in sources}and originals=={p:pin(p)for p in originals}
(F/'finite-snapshot01.json').write_text(json.dumps(snapshot,indent=2)+'\n');print(len(sources),len(compact),len(members),pin(cap))
