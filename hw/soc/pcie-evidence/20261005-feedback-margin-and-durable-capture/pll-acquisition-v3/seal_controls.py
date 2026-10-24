from pathlib import Path
import hashlib,json,tarfile,sys
R=Path.cwd();B=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'scripts'))
import characterize_pcie_pll_acquisition_v3 as producer

def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())

freeze=json.loads((B/'source-freeze02.json').read_text())
for p,v in freeze['files'].items():assert pin(R/p)==v
for p,v in freeze['frozen_dependencies'].items():assert pin(R/p)==v
peer=json.loads((B/'source-only-peer02-portable.json').read_text())
assert peer['status'].startswith('PASS'),peer['status']
files={};dependencies={}
for module in list(sys.modules.values()):
 name=getattr(module,'__file__',None)
 if name:
  p=Path(name).resolve()
  if p.is_file() and p.is_relative_to(R/'scripts') and p.suffix=='.py':
   dependencies[str(p.relative_to(R))]=pin(p);files['dependency/'+str(p.relative_to(R))]=p
for p in sorted(B.iterdir()):
 if p.is_file() and p.name not in {'controls-members.json','pcie-pll-acquisition-v3-controls-validation-20261005.json','release01.json','ready-finite.json'}:
  files['method/'+p.name]=p
for n in freeze['files']:files['source/'+n]=R/n
for name in ['controls01','portable02']:
 root=Path('/dev/shm')/('nssoc-pll-acquisition-v3-'+name)
 for p in sorted(root.rglob('*')):
  if p.is_file() and not p.is_symlink():files['controls/'+name+'/'+str(p.relative_to(root))]=p
manifest={n:{'original_path':str(p),**pin(p)} for n,p in sorted(files.items())}
mp=B/'controls-members.json';assert not mp.exists();mp.write_text(json.dumps(manifest,indent=2)+'\n')
a=Path('/dev/shm/pcie-pll-acquisition-v3-controls-20261005.tar.xz');assert not a.exists()
with tarfile.open(a,'w:xz',preset=3) as t:
 for n,p in sorted(files.items()):t.add(p,arcname=n,recursive=False)
 t.add(mp,arcname='members.json',recursive=False)
with tarfile.open(a,'r:xz') as t:
 assert set(t.getnames())==set(manifest)|{'members.json'}
 for member in t.getmembers():
  v=pin(mp) if member.name=='members.json' else manifest[member.name]
  assert member.isfile() and member.size==v['bytes']
  with t.extractfile(member) as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==v['sha256']
r={'status':'SEALED_PUBLICATION_ONLY_PRODUCER_BRIDGE_CONTROLS','archive':{'path':str(a),**pin(a),'members':len(manifest)+1},'source_freeze':pin(B/'source-freeze02.json'),'source_peer':pin(B/'source-only-peer.json'),'portable_peer':pin(B/'source-only-peer02-portable.json'),'initial_pytest_passed':15,'portable_affected_cases_passed':2,'distinct_controls':15,'unchanged_cases_not_repeated':13,'skipped':0,'source_dependencies':dependencies,'full_member_readback':True,'scope':'Exact inherited source bridge, unchanged electrical/numerical/acquisition/resource criteria. Real nested subprocess/localHTTP PartQueue integration controls for transient-prefix recovery, terminal byte mismatch and outer SIGTERM with native sleeper substitute. No SPICE acquisition or physical acceptance from these controls.','resource_scope':'50MiB capture ceiling,512MiB shared free floor,5s native owner grace unchanged; nested publisher1s cleanup and bounded120s transport attempts.','physical_acceptance':False}
p=B/'pcie-pll-acquisition-v3-controls-validation-20261005.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'archive':r['archive'],'validation':pin(p),'dependencies':len(dependencies)}))
