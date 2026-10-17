from pathlib import Path
import hashlib,json,tarfile,sys
R=Path.cwd();B=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'scripts'))
import publish_pcie_native_capture_v3 as publisher

def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
freeze=json.loads((B/'publisher-v3-source-freeze04.json').read_text())
for p,v in freeze['files'].items():assert pin(p)==v
peer=json.loads((B/'publisher-v3-source-only-peer04.json').read_text())
files={};dependencies={}
for module in list(sys.modules.values()):
 name=getattr(module,'__file__',None)
 if name:
  p=Path(name).resolve()
  if p.is_file() and p.is_relative_to(R/'scripts') and p.suffix=='.py':dependencies[str(p.relative_to(R))]=pin(p);files['dependency/'+str(p.relative_to(R))]=p
for p in sorted(B.glob('publisher-v3*')):
 if p.is_file():files['method/'+p.name]=p
 elif p.is_dir():
  for q in sorted(p.rglob('*')):
   if q.is_file() and not q.is_symlink():files['method/'+str(q.relative_to(B))]=q
for n in ['seal_publisher_v3.py','pll-publication-failure-diagnosis.json','pll-publication-failure-redacted.txt','restore-receipt.json']:
 files['method/'+n]=B/n
for n in freeze['files']:files['source/'+n]=R/n
roots=['controls01','controls02','controls03','main04','final05','signal-counterexample06','final07']
for name in roots:
 root=Path('/dev/shm')/('nssoc-native-publisher-v3-'+name)
 for p in sorted(root.rglob('*')):
  if p.is_file() and not p.is_symlink():files['controls/'+name+'/'+str(p.relative_to(root))]=p
manifest={n:{'original_path':str(p),**pin(p)} for n,p in sorted(files.items())}
mp=B/'publisher-v3-controls-members.json';assert not mp.exists();mp.write_text(json.dumps(manifest,indent=2)+'\n')
a=Path('/dev/shm/pcie-native-publisher-v3-controls-20261005.tar.xz');assert not a.exists()
with tarfile.open(a,'w:xz',preset=3) as t:
 for n,p in sorted(files.items()):t.add(p,arcname=n,recursive=False)
 t.add(mp,arcname='members.json',recursive=False)
with tarfile.open(a,'r:xz') as t:
 assert set(t.getnames())==set(manifest)|{'members.json'}
 for member in t.getmembers():
  v=pin(mp) if member.name=='members.json' else manifest[member.name]
  assert member.isfile() and member.size==v['bytes']
  with t.extractfile(member) as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==v['sha256']
r={'status':'SEALED_FINAL31_TRANSPORT_CONTROLS_AND_PRESERVED_PEER_COUNTEREXAMPLE','archive':{'path':str(a),**pin(a),'members':len(manifest)+1},'source_freeze':pin(B/'publisher-v3-source-freeze04.json'),'source_peer':pin(B/'publisher-v3-source-only-peer04.json'),'final_pytest_passed':31,'final_pytest_skipped':0,'previous_runs_not_additional_distinct_tests':True,'actual_expected_counterexample':'freeze03 completion SIGTERM on nonzero TLS exit caused4 retries; preserved as expected failing diagnostic and fixed in finalsource','source_dependencies':dependencies,'full_member_readback':True,'scope':'Actual local gh-shim subprocesses/localHTTP workers, typed network faults, prefix reconstruction, metadata/byte refusal, resource/deadline/realSIGTERM control tests. No native PLL restart, analog result, network endurance or physical acceptance.','resource_scope':'50MiB native capture ceiling and512MiB shared free floor are unchanged outside this standalone publisher; production integration remains separate. Current controls retained at most69736 bytes per-client evidence for2MiB payload fixtures. Full final received stderr chunk is retained up to320KiB and marked incomplete/fatal on the256KiB bound.'}
p=B/'pcie-native-publisher-v3-controls-validation-20261005.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'archive':r['archive'],'validation':pin(p),'dependencies':len(dependencies)}))
