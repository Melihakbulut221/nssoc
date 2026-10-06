from pathlib import Path
import hashlib,json,tarfile
B=Path(__file__).resolve().parent;R=B.parents[3];A=B/'power-v2-native-closed-backup02.tar.xz'
def pin(p):
 with Path(p).open('rb') as f:return {'bytes':Path(p).stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}
ready=json.loads((B/'native03-finite-review-ready.json').read_text());assert ready['closed_native_files']=={p:pin(p) for p in ready['closed_native_files']}
files={}
for root in [Path('/dev/shm/nssoc-div4-v7-power-v2-layout-01'),Path('/dev/shm/nssoc-div4-v7-power-v2-checks-01'),Path('/dev/shm/nssoc-div4-v7-power-v2-checks-02'),Path('/dev/shm/nssoc-div4-v7-layout-01')]:
 for p in root.rglob('*'):
  if p.is_file():assert not p.is_symlink();files['native/'+root.name+'/'+str(p.relative_to(root))]=p
for p in B.rglob('*'):
 if p.is_file() and not p.is_symlink() and p.suffix in ['.json','.py','.log','.txt'] and '__pycache__' not in p.parts and not p.name.startswith('seal-native-closed02'):
  files['method/'+str(p.relative_to(B))]=p
f=json.loads((B/'source-freeze03.json').read_text())
for name in f['inputs']:
 p=Path(name)
 if p.is_relative_to(R):
  relative=p.relative_to(R)
  if str(relative).startswith(('scripts/','sw/tests/','hw/soc/flow/','hw/soc/analog/')):files['project/'+str(relative)]=p
for p in (R/'LICENSES').glob('*.txt'):files['project/'+str(p.relative_to(R))]=p
members={n:{'restore_path':str(p),**pin(p)} for n,p in files.items()};assert not A.exists()
with tarfile.open(A,'x:xz',preset=3) as tar:
 for n,p in files.items():tar.add(p,arcname=n,recursive=False)
assert members=={n:{'restore_path':str(p),**pin(p)} for n,p in files.items()}
seen=set()
with tarfile.open(A,'r|xz') as tar:
 for item in tar:
  assert item.isfile() and item.name not in seen;seen.add(item.name);want=members[item.name];assert {'bytes':item.size,'sha256':hashlib.file_digest(tar.extractfile(item),'sha256').hexdigest()}=={k:want[k] for k in ('bytes','sha256')}
assert seen==set(members)
r={'status':'PASS_CLOSED_UNIQUE_NATIVE_AND_FAILED_AUDIT_SSD_FULL_MEMBER_READBACK','archive':{'path':str(A),**pin(A)},'member_count':len(members),'members':members,'native_ready':pin(B/'native03-finite-review-ready.json'),'independent_saved_native_peer_pending':True,'previous_snapshot_01':{'note':'Prior333member backup included its own then-active method packaging log/owner snapshot. This02 capture includes the completed01 packaging receipt and excludes its own active02 packaging files. All native payloads in both are exactly closed.'},'public_release_not_attempted':True,'qualified_pex':False}
p=B/'native-closed-backup02.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n');print(r['archive'],len(members))
