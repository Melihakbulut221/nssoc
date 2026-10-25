"""One bounded continuation of frozen V18 controls/map/import/original4ns STA."""
from pathlib import Path
import datetime,hashlib,json,os,shutil,subprocess,sys,time
R=Path.cwd();B=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'scripts'))
import characterize_pcie_clock_trim_stream_v2 as life

def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())

assert pin(life.__file__)['sha256']=='39312e364fa2a788784d88f3a63845f64db25bb420e2ee5d58c07a8c805bc886'
assert os.sched_getaffinity(0)=={6}
assert not (B/'continuation-status01.json').exists(),'Fresh continuation required'
policy=json.loads((B/'continuation-policy01.json').read_text())
for p,v in policy['method_pins'].items():assert pin(p)==v
for p,v in policy['source_pins'].items():assert pin(R/p)==v
assert pin(B/'source-freeze.json')['sha256']=='5b09e04a09709043074263ca9af866d38fe9067379ef11ffec0b2ad1ca6e1143'
record=dict(status='VALIDATING_COMPLETED_FROZEN_CONTROLS',controller=life.process_identity(os.getpid()),affinity=[6],policy=pin(B/'continuation-policy01.json'),stages=[],elapsed_watchdog_seconds=None,physical_acceptance=False)
owner=life.ProcessOwner(B/'continuation-owner01.json')

def explicit_stop():
 return bool(owner.reason and owner.reason.startswith('Parent received SIG'))

def save():
 record['utc']=datetime.datetime.now(datetime.UTC).isoformat()
 life.atomic(B/'continuation-status01.json',record)
 # Operational checkpoint is deliberately mutable; all evidence pins it points
 # to are immutable. It is the single root-monitor entry for these owned jobs.
 active=dict(status=record['status'],utc=record['utc'],continuation=dict(path=str(B/'continuation-status01.json'),controller=record['controller'],owner=str(B/'continuation-owner01.json')),V18_source_freeze=dict(path=str(B/'source-freeze.json'),**pin(B/'source-freeze.json')),completed_controls=policy['completed_controls'],PLL=policy['PLL'],next='Owned same2GiB CPU6 map, measured native read depth, literal-tie import+allpin graph proof and original4ns three-corner preplacement. All21 functional predicates complete; no PLL duplicate and no constraints relaxed.')
 life.atomic(B/'active-checkpoint.json',active)

def verify_sources():
 for p,v in policy['source_pins'].items():assert pin(R/p)==v
 for p,v in policy['method_pins'].items():assert pin(p)==v

def stage(name,command):
 owner.check();verify_sources();assert shutil.disk_usage('/dev/shm').free>=1024**3
 row=dict(name=name,command=command,started_utc=datetime.datetime.now(datetime.UTC).isoformat(),status='RUNNING');record['stages'].append(row);record['status']='RUNNING_'+name;save()
 with (B/(name+'.controller.log')).open('x') as log:
  process=owner.launch('native',command,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'TMPDIR':'/dev/shm','PYTHONDONTWRITEBYTECODE':'1','YOSYS_MAX_THREADS':'1','OMP_NUM_THREADS':'1'})
  row['identity']=life.process_identity(process.pid);save()
  code=owner.wait(process);owner.check()
 row.update(returncode=code,status='COMPLETE' if code==0 else 'FAILED_RETAINED',finished_utc=datetime.datetime.now(datetime.UTC).isoformat(),log=pin(B/(name+'.controller.log')));save()
 assert code==0,(name,code)
 verify_sources()

save()
try:
 with owner:
  for gate in policy['completed_controls']:
   p=Path(gate['path']);assert pin(p)=={k:gate[k] for k in ('bytes','sha256')}
   assert json.loads(p.read_text())['status']==gate['status']
  assert pin(B/'source-only-peer-pll02.json')==policy['peer_pin']
  assert json.loads((B/'source-only-peer-pll02.json').read_text())['status']=='PASS_V18_FINAL_SOURCE_AND_CORRECTED_FOCUSED_HARNESS_PEER'
  stage('map',[sys.executable,str(B/'run_balanced_map.py')])
  mapped=Path('/dev/shm/nssoc-integrity-v18-balanced-map-01/mapped.json')
  stage('read_depth',[sys.executable,str(B/'measure_native_read_depth.py'),'--candidate',str(mapped),'--rejected','/dev/shm/nssoc-integrity-v14-balanced-map-01/mapped.json','--out',str(B/'native-read-depth-comparison.json')])
  module=json.loads(mapped.read_text())['modules']['soc_pcie_gen3_continuous_rx_integrity_v18']
  census=dict(source=pin(mapped),signed={n:v['bits'] for n,v in module['netnames'].items() if v.get('signed')},scope='Only mapped native wire-label signedness, not cell/port graph, is normalized for OpenSTA. All pin-driver relations proved after literal ties.')
  assert not (B/'signed-wire-census.json').exists();life.atomic(B/'signed-wire-census.json',census)
  stage('import',[sys.executable,str(B/'balanced_import.py')])
  stage('import_graph_proof',[sys.executable,str(B/'prove_balanced_import.py')])
  stage('preplacement',[sys.executable,str(B/'balanced_preplacement.py')])
  stage('timing_review',[sys.executable,str(B/'review_timing.py')])
  stage('critical_path',[sys.executable,str(B/'analyze_critical_path.py')])
  owner.check();record['status']='COMPLETE_NATIVE_SCREEN_FINITE_REVIEW_AND_PUBLICATION_REQUIRED'
 owner.check()
except BaseException as error:
 record.update(status='CANCELLED_RETAINED' if explicit_stop() else 'FAILED_RETAINED',error=repr(error))
 raise
finally:
 record['explicit_stop']=explicit_stop();record['stop_reason']=owner.reason
 if explicit_stop():record.update(status='CANCELLED_RETAINED',cancellation_reason=owner.reason)
 save()
