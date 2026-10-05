from pathlib import Path
import ast,hashlib,json
R=Path.cwd();B=R/'hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004';OLD=B/'repair11-peer02';O=B/'repair12-peer';O.mkdir(exist_ok=True)
def pin(p):
 with p.open('rb') as f:return {'bytes':p.stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}
def patch(text,a,z,mode,changes):
 positions=[];start=0
 while True:
  at=text.find(a,start)
  if at<0:break
  positions.append(at);start=at+len(a)
 assert positions and (mode!='once' or len(positions)==1),(a,len(positions))
 after_offsets=[p+i*(len(z)-len(a)) for i,p in enumerate(positions)]
 changes.append((a,z,mode,after_offsets))
 return text.replace(a,z)

versions=[('repair11','repair12'),('repair-11','repair-12'),('RX11','RX12'),('rx11_','rx12_'),('repair12-drt-02','repair12-drt-01'),('repair12-detailed-rc-02','repair12-detailed-rc-01')]
bridge={}
for name in ['review.py','seal.py']:
 source=(OLD/name).read_text();text=source;changes=[]
 for a,z in versions:
  if a in text:text=patch(text,a,z,'all',changes)
 if name=='review.py':
  subs=[("old = B / 'repair10-peer/review.json'","old = B / 'repair11-peer02/review.json'"),("'SS_setup_improvement_vs10_ns'","'SS_setup_improvement_vs11_ns'")]
 else:
  roots_start=text.index('roots = [');roots_end=text.index('\nfor name in roots:',roots_start)
  roots="roots = [\n    '/dev/shm/nssoc-rx-prefetch-v2-postroute-repair-12',\n    '/dev/shm/nssoc-rx-prefetch-v2-repair12-equivalence',\n    '/dev/shm/nssoc-rx-prefetch-v2-repair12-physical-replay-01',\n    '/dev/shm/nssoc-rx-prefetch-v2-repair12-drt-01',\n    '/dev/shm/nssoc-rx-prefetch-v2-repair12-detailed-rc-01',\n]"
  methodsline=next(l for l in text.splitlines() if l.startswith("for name in ['postroute_repair12.py'"))
  methods="for name in ['postroute_repair12.py', 'normalize_repair12.py', 'proof_gate_repair12.py', 'replay_repair12.py', 'drt_repair12.py', 'detailed_rc_repair12.py', 'newtool-readonly-comparison.json', 'eco-proof/compare.py', 'eco-proof/mutations.py']:"
  preserve_start=text.index("for dirname in ('repair12-source'")
  preserve_end=text.index("for path in review['inputs_rehashed']:",preserve_start)
  preserve="""for p in sorted((B / 'repair12-source').glob('*')):
    if p.is_file() and p.suffix in ('.py', '.json', '.log', '.txt', '.diff'):
        files['preservation/repair12-source/' + p.name] = p
# Controller's live status/owner files are not static capsule inputs. Its final
# dependent-stage binding is published after this seal completes.
for name in ('run.py', 'manifest.json'):
    files['controller/' + name] = B / 'repair12-continuation01' / name
for path in review['inputs_rehashed']:
    p = Path(path)
    if p.is_relative_to(Path('/dev/shm')) and p not in files.values():
        assert p.is_file() and not p.is_symlink()
        files['bound-input/' + str(p.relative_to('/dev/shm'))] = p
"""
  subs=[('pcie-rx-repair12-route-nominal-rc-and-peer02-20261005.tar.xz','pcie-rx-repair12-route-nominal-rc-and-peer-20261005.tar.xz'),("'SS_setup_improvement_vs_published10_ns': review['SS_setup_improvement_vs10_ns']","'SS_setup_improvement_vs_published11_ns': review['SS_setup_improvement_vs11_ns']"),('Earlier routed10 inputs are bound through their prior public capsule manifest/release.','Earlier routed11 inputs are bound through their prior public capsule manifest/release.'),('New DRT02 and RC02 native executions completed;','New DRT01 and RC01 native executions completed; originalgold expansion reused exactly from completedRX11;'),(text[roots_start:roots_end],roots),('    directory = Path(name)\n    for p in sorted(directory.rglob', '    directory = Path(name)\n    assert directory.is_dir(), f"Missing required completed native capture: {directory}"\n    for p in sorted(directory.rglob'),(methodsline,methods),(text[preserve_start:preserve_end],preserve),("for name in ['pcie-rx-repair10-finite-physical-validation-20261005.json', 'package.json', 'release.json', 'review.json']:\n    files['prior-published/repair10/' + name] = B / 'repair10-peer' / name", "for name in ['pcie-rx-repair11-finite-physical-validation-20261005.json', 'package.json', 'release.json', 'review.json']:\n    files['prior-published/repair11/' + name] = B / 'repair11-peer02' / name")]
 for a,z in subs:text=patch(text,a,z,'once',changes)
 # Inverse replay applies literal changes in reverse order; this includes path
 # substitutions inside the separately replaced root/method lists.
 inverse=text
 for a,z,_,positions in reversed(changes):
  for at in reversed(positions):
   assert inverse[at:at+len(z)]==z
   inverse=inverse[:at]+a+inverse[at+len(z):]
 assert inverse==source,name
 compile(text,str(O/name),'exec')
 if (O/name).exists():assert (O/name).read_text()==text
 else:(O/name).write_text(text)
 bridge[name]={'source':{'path':str(OLD/name),**pin(OLD/name)},'new':{'path':str(O/name),**pin(O/name)},'changes':[{'before':a,'after':z,'mode':mode,'after_offsets':positions} for a,z,mode,positions in changes],'inverse_byte_exact':True}
(O/'source-bridge.json').write_text(json.dumps({'status':'RX12_SAVED_OUTPUT_METHODS_READY_FOR_SOURCE_PEER','files':bridge,'native_route_pending':True,'no_method_execution':True},indent=2)+'\n')
freeze={'status':'FROZEN_BEFORE_RX12_ROUTE_RC_REVIEW','files':{str(O/n):pin(O/n) for n in ['review.py','seal.py','source-bridge.json']}}
(O/'source-freeze.json').write_text(json.dumps(freeze,indent=2)+'\n');print(json.dumps({'freeze':pin(O/'source-freeze.json'),'methods':freeze['files']},indent=2))
