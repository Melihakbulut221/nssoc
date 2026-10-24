# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Finite closed RX14A delivery; preserve all previous checkpoints immutably."""
from pathlib import Path
import datetime,hashlib,json,tarfile
O=Path(__file__).resolve().parent;B=O.parent;R=B.parents[3]
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def j(p):return json.loads(Path(p).read_text())
def write(p,x):
 assert not p.exists();p.write_text(json.dumps(x,indent=2)+'\n')
review=j(B/'repair14a-peer/publication-review.json');controller=j(B/'repair14a-continuation01/result.json')
assert review['status']=='PASS_RX14A_COMPLETED_CAPTURE_AND_THREE_IMMUTABLE_PUBLIC_ASSETS_REVIEW'
assert pin(B/'repair14a-continuation01/result.json')==review['controller']
assert controller['status']=='COMPLETE_RX14A_FINITE_ROUTE_RC_REVIEW_PUBLICATION'
assert pin(B/'repair14a-peer/release.json')==review['release']
assert pin(B/'repair14a-peer/review_delivery.py')==review['method']
oldcp=B/'repair14-source/active-checkpoint03.json';old=j(oldcp)
identities=[controller['controller_identity'],*[x['identity']for x in controller['stages']],old['route_owner'],old['route_native']]
for i in identities:
 p=Path('/proc')/str(i['pid'])/'stat'
 if p.exists():
  f=p.read_text().rsplit(') ',1)[1].split();assert f[19]!=str(i['start_ticks'])or f[0]=='Z',i
archives=[]
for name,packagefile in [('repair14a-peer','package.json'),('repair14a-preroute-preservation','pcie-rx-repair14a-preroute-package-20261005.json')]:
 d=B/name;p=j(d/packagefile);rv=j(d/'publication-review.json');assert pin(d/packagefile)==rv['package'] and pin(d/'release.json')==rv['release']
 a=Path(p['archive']['path']);assert pin(a)=={k:p['archive'][k]for k in ['bytes','sha256']};seen=set()
 with tarfile.open(a,'r:xz')as tar:
  for m in tar:
   assert m.isfile()and m.name in p['members']and m.name not in seen;seen.add(m.name)
   with tar.extractfile(m)as stream:x=dict(bytes=m.size,sha256=hashlib.file_digest(stream,'sha256').hexdigest())
   assert x=={k:p['members'][m.name][k]for k in ['bytes','sha256']},m.name
 assert seen==set(p['members']);r=j(d/'release.json');assert len(r['assets'])==3 and all(a['authenticated_roundtrip']and a['anonymous_roundtrip']for a in r['assets'])
 archives.append(dict(archive=p['archive'],members=len(seen),manifest=dict(path=str((d/packagefile).relative_to(R)),**pin(d/packagefile)),saved_review=dict(path=str((d/'publication-review.json').relative_to(R)),**pin(d/'publication-review.json')),public_assets=r['assets']))
newcp={'status':'CLOSED_RX14A_ZERO_ROUTER_DRC_PUBLIC_CAPTURE_SETUP_STILL_FAILS','utc':datetime.datetime.now(datetime.UTC).isoformat(),'previous_immutable_checkpoint':dict(path=str(oldcp.relative_to(R)),**pin(oldcp)),'terminal_controller':dict(path=str((B/'repair14a-continuation01/result.json').relative_to(R)),**pin(B/'repair14a-continuation01/result.json')),'independent_review':dict(path=str((B/'repair14a-peer/publication-review.json').relative_to(R)),**pin(B/'repair14a-peer/publication-review.json')),'all_exact_prior_owner_births_closed':True,'archives':archives,'measured_nominal_corner_slacks_ns':review['nominal_cell_corner_slacks_ns'],'physical_acceptance':False,'qualified_rc':False,'resume':['Do not rerun completed RX14A candidate/proof/ports/route/RC.','Restore only exact public assets and full member maps; retain all earlier checkpoint snapshots.','SS setup remains−0.402478ns and hold+.049182ns. Next RX15 work is separately named; read-only wide100-path screen under repair15-source guides actual same4ns repair. New proof/ports/DRT/RC remain required.'],'scope':'Standalone default150 receiver, same nominal RC reused across cell corners. No main-chip/qualifiedRC/fullPHY acceptance.'}
write(B/'repair14-source/active-checkpoint04-complete.json',newcp)
files={}
for folder in ['repair14-source','repair14a-peer','repair14a-continuation01','repair14a-preroute-preservation']:
 for p in sorted((B/folder).rglob('*')):
  if p.is_file()and'__pycache__'not in p.parts:
   assert not p.is_symlink();files[str(p.relative_to(R))]=pin(p)
for n in ['postroute_repair14a.py','postroute_repair14b.py','normalize_repair14a.py','proof_gate_repair14a.py','replay_repair14a.py','drt_repair14a.py','detailed_rc_repair14a.py']:
 p=B/n;files[str(p.relative_to(R))]=pin(p)
files[str(Path(__file__).relative_to(R))]=pin(__file__)
r=dict(status='READY_FINITE_RX14A_ROUTE_RC_PROOF_AND_DUAL_PUBLIC_CAPTURE',utc=datetime.datetime.now(datetime.UTC).isoformat(),new_product_source_allowlist={},compact_files=files,compact_file_count=len(files),compact_bytes=sum(x['bytes']for x in files.values()),archives=archives,full_member_readbacks_this_delivery=sum(x['members']for x in archives),measured_nominal_corner_slacks_ns=review['nominal_cell_corner_slacks_ns'],delta_vs_RX13_ns=review['delta_vs_RX13_ns'],saved_proof_states=1804,saved_proof_targets=5443,saved_fault_controls=10,saved_port_cases=6,retained_publication_failure=review['retained_actual_failed_transport'],checkpoint_preserved_and_updated=True,physical_acceptance=False,qualified_rc=False,limitations=['SSsetup−0.402478ns still fails despite39.125ps improvement; hold49.182ps positive.','Nominal RC reused across three cell corners, not qualified independent RC corners.','Zero router DRC/exact saved functional proof/six native ports cover default150 standalone receiver only.','Full160-member final and151-member prereoute capsules preserved, including complete source/method binding and failed preparations.','One real anonymous120s transport deadline failure retained with32,636,928-byte matching prefix; bounded retry and both public roundtrips passed.'],scope='Finite RX14A closed evidence. Root owns combined documentation/licensing/staging/push. Live MAX4118, new RX15 and analog campaigns excluded.')
write(O/'ready-finite.json',r);print(json.dumps(dict(path=str(O/'ready-finite.json'),**pin(O/'ready-finite.json'),compact_files=len(files),compact_bytes=r['compact_bytes'],archive_members=r['full_member_readbacks_this_delivery'])))
