# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Seal closed numerical evidence and bounded-reader controls only."""
from pathlib import Path
import hashlib,io,json,shutil,tarfile
R=Path.cwd();F=Path(__file__).resolve().parent
B=R/'hw/soc/out/pcie-vco-v6-divider-tail115-v1-sixteenthstep-20261006'
W=R/'hw/soc/out/pcie-tail115-sixteenthstep-wave-peer-rx-20261006'
S=R/'hw/soc/out/pcie-tail115-streaming-replay-v1-20261006'
D=R/'hw/soc/out/pcie-tail115-sixteenthstep-multipart-20261006'
PLOT=R/'hw/soc/out/pcie-tail115-five-step-plot-20261006'
PARENT=F.parent/'pcie-tail115-eighthstep-finite-20261006/ready-finite01.json'
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def archive_members(p):
 seen={}
 with tarfile.open(p,'r|xz')as t:
  for m in t:
   assert m.isfile()and m.name not in seen
   seen[m.name]=dict(bytes=m.size,sha256=hashlib.file_digest(t.extractfile(m),'sha256').hexdigest())
 return seen
assert not(F/'finite-snapshot01.json').exists()
assert json.loads((B/'native06-controller.json').read_text())['status']=='CLOSED_FINITE_NATIVE_RESULT'
v=json.loads((B/'validation-06-01.json').read_text());assert v['native_status']=='PASS_NATIVE_LOADED_FEEDBACK_SCREEN'
native=Path(v['archive']['path']);assert pin(native)=={k:v['archive'][k]for k in ['bytes','sha256']}
members=json.loads((B/'members-06-01.json').read_text());assert archive_members(native)==members and len(members)==v['members']
num=json.loads((B/'numerical-convergence01.json').read_text());assert num['status']=='PASS_FINITE_OPEN_LOOP_NUMERICAL_SCREEN'and all(num['checks'].values())
assert pin(B/'numerical-convergence01.json')==dict(bytes=9837,sha256='f239033476fb46b72a073f050b2c6d4c19a93c34cff331d25a5cfdee282ddc3f')
pub=json.loads((D/'release-parts01.json').read_text());assert pub['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS'
launch=json.loads((D/'publication-launch01.json').read_text())
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();proc=Path('/proc')/str(launch['pid'])/'stat'
if boot==launch['boot'] and proc.exists():
 try:fields=proc.read_text().rsplit(') ',1)[1].split()
 except FileNotFoundError:fields=None
 assert fields is None or fields[19]!=launch['start_ticks'],'Publisher must be closed before finite journal capture'
assert pin(D/'source-freeze01.json')==launch['freeze'] and pin(D/'source-only-peer01-root.json')==launch['peer']
manifest_path=D/'pcie-tail115-sixteenthstep-multipart-manifest01.json';manifest=json.loads(manifest_path.read_text());assert {k:manifest['archive'][k]for k in ['bytes','sha256']}==pin(native)
assets={a['name']:a for a in pub['assets']};assert len(assets)==25
whole=hashlib.sha256();offset=0
for i,row in enumerate(manifest['parts']):
 assert row['name']==native.name+f'.part{i:04d}' and row['offset']==offset and row['bytes']<=32*1024**2
 part=D/'parts01'/row['name'];expected={k:row[k]for k in ['bytes','sha256']};assert pin(part)==expected
 a=assets[row['name']];assert {k:a[k]for k in ['bytes','sha256']}==expected and a['authenticated_roundtrip']and a['anonymous_roundtrip']
 with part.open('rb')as stream:
  while block:=stream.read(1024**2):whole.update(block);offset+=len(block)
assert dict(bytes=offset,sha256=whole.hexdigest())==pin(native)
a=assets[manifest_path.name];assert {k:a[k]for k in ['bytes','sha256']}==pin(manifest_path)and a['authenticated_roundtrip']and a['anonymous_roundtrip']
freeze=json.loads((B/'source-freeze01.json').read_text());assert all(pin(p)==x for p,x in freeze['pins'].items())
methods=dict(freeze['new_sources']);methods.update({str(S/p):pin(S/p)for p in ['raw_table01.py','test_reader01.py']})
assert all(pin(p)==x for p,x in methods.items())
# Exact independent peer binding is added after its own read-only run closes.
peer_binding=json.loads((F/'independent-peer-binding01.json').read_text());assert all(pin(p)==v for p,v in peer_binding['files'].items());assert peer_binding['findings']==[]
files={};compact={};originals={}
for root in [B,W,S,D]:
 for p in root.rglob('*'):
  if not p.is_file()or'__pycache__'in p.parts or (root==D and'parts01'in p.relative_to(D).parts):continue
  if not(p.suffix in {'.json','.py','.log','.txt','.xml','.license'}or'.attempt'in p.name or any(x.endswith('.transport')for x in p.parts)or(root==D and'control-fixture01'in p.parts)):continue
  rel=root.name+'/'+str(p.relative_to(root));q=F/'compact-evidence'/rel;q.parent.mkdir(parents=True,exist_ok=True);assert not q.exists();shutil.copyfile(p,q);assert pin(q)==pin(p)
  compact[str(q)]=pin(q);originals[str(p)]=pin(p);files['compact-evidence/'+rel]=q
qa=json.loads((PLOT/'visual-qa01.json').read_text());assert qa['findings']==[] and all(pin(R/p)==v for p,v in qa['selected_inputs'].items())
for p in [*(R/p for p in qa['selected_inputs']),PLOT/'visual-qa01.json']:
 rel=PLOT.name+'/'+p.name;q=F/'compact-evidence'/rel;q.parent.mkdir(parents=True,exist_ok=True);assert not q.exists();shutil.copyfile(p,q);assert pin(q)==pin(p);compact[str(q)]=pin(q);originals[str(p)]=pin(p);files['compact-evidence/'+rel]=q
for n in ['Apache-2.0','CC-BY-4.0','CERN-OHL-W-2.0']:files['licenses/'+n+'.txt']=R/'LICENSES'/(n+'.txt')
files['seal_finite01.py']=Path(__file__);files['complete_finite01.py']=F/'complete_finite01.py';files['independent-peer-binding01.json']=F/'independent-peer-binding01.json'
notice=F/'NOTICES.txt';notice.write_text('Copyright 2026 Hasan Melih Akbulut. Methods Apache-2.0; circuit CERN-OHL-W-2.0; generated evidence CC-BY-4.0. Same455 devices, full34ns at0.3125ps output/maxstep, bounded1GiB native scratch and unchanged2GiB address-space ceiling. Native finite nominal functional/electrical predicates allPASS:60count4 intervals and2count80 intervals. Separate predeclared100ppm/50ps fixed-anchor adjacent numerical screenPASS:67.487262733ppm VCO/67.334078980ppm feedback; maximum unaligned timestamp differences2.223825407ps VCO/2.202400484ps CML/1.858685780ps feedback, no offset fitting. Earlier5ps/2.5ps functionalFAIL and0.625ps-versus1.25ps numericalFAIL remain unchanged. Bounded anonymousSSD reader plus20 saved controls and exact former replay equivalence included. Full104137869-value independent reader and root visually checked five-step scientific plot included. Finite nominal openloop result is not extended-time, qualifiedPEX, RF/PVT/ESD, PLL/acquisition/CDR/fullPHY or mainchip qualification. Exact runtime/PDK hashes retained without redistribution. Original774MB monolithic upload timeout is preserved; public byte-identical representation uses24ordered32MiB-or-smaller pieces plus full-offset/hash manifest, authenticated and anonymous roundtrips for all25assets, and streamed exact original-archive reconstruction. No smaller-step or future closedloop integration included.\n')
files['NOTICES.txt']=notice
m={n:pin(p)for n,p in files.items()};cap=F/'pcie-tail115-sixteenthstep-numerical-additive01.tar.xz';assert not cap.exists()
with tarfile.open(cap,'w:xz',preset=1)as t:
 for n,p in files.items():
  data=p.read_bytes();i=tarfile.TarInfo(n);i.size=len(data);i.mtime=0;i.mode=0o644;t.addfile(i,io.BytesIO(data))
assert archive_members(cap)==m;(F/'additive-members01.json').write_text(json.dumps(m,indent=2)+'\n')
r=dict(status='SEALED_SIXTEENTHSTEP_FINITE_FUNCTIONAL_AND_NUMERICAL_PASS_PENDING_ADDITIVE_PUBLICATION',sources={},method_allowlist=methods,compact_evidence=compact,original_evidence=originals,source_files=0,method_files=len(methods),compact_files=len(compact),archives=[dict(path=str(native),**pin(native),members=len(members),manifest=str(B/'members-06-01.json'),manifest_pin=pin(B/'members-06-01.json'),public_receipt=str(D/'release-parts01.json'),public_representation=dict(kind='ordered_byte_parts',manifest=str(manifest_path),manifest_pin=pin(manifest_path),parts=24,reconstructed_archive=pin(native)))],assets=list(assets.values()),public_receipts={str(D/'release-parts01.json'):pin(D/'release-parts01.json')},additive_archive=dict(path=str(cap),**pin(cap),members=len(m),manifest=str(F/'additive-members01.json')),parent_eighthstep_ready=dict(path=str(PARENT),**pin(PARENT)),independent_postnative_peer_pending=False,physical_acceptance=False,product_physics_unchanged=True,numerical_convergence=True,numerical_scope=num['scope'],future_integration_excluded=True,root_owns_git_delivery=True)
assert all(pin(p)==x for p,x in originals.items());(F/'finite-snapshot01.json').write_text(json.dumps(r,indent=2)+'\n');print(len(compact),len(m),pin(cap))
