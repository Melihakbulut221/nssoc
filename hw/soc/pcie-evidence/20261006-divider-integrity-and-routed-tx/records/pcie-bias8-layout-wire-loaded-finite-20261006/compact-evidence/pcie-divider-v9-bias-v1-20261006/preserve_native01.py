from pathlib import Path
import hashlib,json,os,tarfile
B=Path(__file__).resolve().parent;R=B.parents[3]
roots=[Path('/dev/shm/nssoc-div4-v9-bias-v1-layout-01'),Path('/dev/shm/nssoc-div4-v9-bias-v1-checks-01')]
def pin(p):
 with Path(p).open('rb') as f:return dict(bytes=Path(p).stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
native=json.loads((roots[1]/'result.json').read_text());assert native['status']=='PASS_DIV4_V9_BIAS_V1_STANDALONE_MAIN_DRC_STRICT_DEEP_FLAT_LVS_LEF_NEGATIVE_CONTROLS_ONLY' and len(native['steps'])==21
for p in roots[1].rglob('*.owned.json'):
 d=json.loads(p.read_text());assert d['status']=='HEALTHY' and d['cleanup'] is None
 for process in d['processes']:
  assert process['status']=='REAPED_NO_LIVE_MEMBERS' and process['members_at_leader_exit']==[]
  pstat=Path('/proc')/str(process['identity']['pid'])/'stat'
  if pstat.exists():
   f=pstat.read_text().rsplit(')',1)[1].split();assert f[19]!=process['identity']['start_ticks'] or f[0]=='Z'
closed={str(p):pin(p) for root in roots for p in root.rglob('*') if p.is_file()}
f=json.loads((B/'source-freeze01.json').read_text());assert f['inputs']=={p:pin(p) for p in f['inputs']}
ready=dict(status='COMPLETE_BIAS8_V1_21_NATIVE_CHECKS_REQUIRES_INDEPENDENT_SAVED_REVIEW',closed_native_files=closed,source_freeze=pin(B/'source-freeze01.json'),source_peer=pin(B/'source-only-peer01-rx.json'),layout=str(roots[0]),checks=str(roots[1]),fresh_wire_RC_pending=True,loaded455_pending=True,qualified_pex=False)
p=B/'native-finite-review-ready01.json';assert not p.exists();p.write_text(json.dumps(ready,indent=2)+'\n')
files={}
for root in roots+[Path('/dev/shm/nssoc-div4-v8-cap-v1-layout-01')]:
 for p in root.rglob('*'):
  if p.is_file():assert not p.is_symlink();files['native/'+root.name+'/'+str(p.relative_to(root))]=p
for root in [B]:
 for p in root.rglob('*'):
  if p.is_file() and not p.is_symlink() and '__pycache__' not in p.parts and p.suffix in ['.json','.py','.txt','.log','.xml','.spice','.cir','.bin'] and 'preservation-active' not in p.name:files['method/'+root.name+'/'+str(p.relative_to(root))]=p
for name in f['inputs']:
 p=Path(name)
 if p.is_relative_to(R):
  rel=p.relative_to(R)
  if str(rel).startswith(('scripts/','sw/tests/','hw/soc/flow/','hw/soc/analog/')):files['project/'+str(rel)]=p
for p in (R/'LICENSES').glob('*.txt'):files['project/'+str(p.relative_to(R))]=p
members={n:dict(restore_path=str(p),**pin(p)) for n,p in files.items()};a=B/'pcie-divider-v9-bias-v1-native01.tar.xz';assert not a.exists()
with tarfile.open(a,'x:xz',preset=3) as tf:
 for n,p in files.items():tf.add(p,arcname=n,recursive=False)
assert members=={n:dict(restore_path=str(p),**pin(p)) for n,p in files.items()}
seen=set()
with tarfile.open(a,'r|xz') as tf:
 for item in tf:
  assert item.isfile() and item.name not in seen;seen.add(item.name);x=members[item.name];assert item.size==x['bytes'] and hashlib.file_digest(tf.extractfile(item),'sha256').hexdigest()==x['sha256']
assert seen==set(members)
r=dict(status='PASS_CLOSED_BIAS8_NATIVE_SOURCE_AND_PARENT_FAILURE_HISTORY_FULL_READBACK',archive=dict(path=str(a),**pin(a)),members=members,member_count=len(members),native_ready=pin(B/'native-finite-review-ready01.json'),independent_saved_peer_pending=True,qualified_pex=False)
p=B/'native-archive01.json';p.write_text(json.dumps(r,indent=2)+'\n');print(r['archive'],len(members),len(closed))
