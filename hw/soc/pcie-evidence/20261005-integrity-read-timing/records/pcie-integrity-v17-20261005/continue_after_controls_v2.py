"""One bounded continuation of frozen V17 controls/map/import/original4ns STA."""
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
assert not (B/'continuation-status02.json').exists(),'Fresh continuation required'
policy=json.loads((B/'continuation-policy02.json').read_text())
for p,v in policy['method_pins'].items():assert pin(p)==v
for p,v in policy['source_pins'].items():assert pin(R/p)==v
assert pin(B/'source-freeze.json')['sha256']=='48a78275df28c51417f5e318750ccc77d933ccf34fd7188cdc3158445e101dcd'
record=dict(status='WAITING_EXISTING_FROZEN_CONTROLS',controller=life.process_identity(os.getpid()),affinity=[6],policy=pin(B/'continuation-policy02.json'),stages=[],elapsed_watchdog_seconds=None,physical_acceptance=False)
owner=life.ProcessOwner(B/'continuation-owner02.json')

def explicit_stop():
 return bool(owner.reason and owner.reason.startswith('Parent received SIG'))

def save():
 record['utc']=datetime.datetime.now(datetime.UTC).isoformat()
 life.atomic(B/'continuation-status02.json',record)
 # Operational checkpoint is deliberately mutable; all evidence pins it points
 # to are immutable. It is the single root-monitor entry for these owned jobs.
 active=dict(status=record['status'],utc=record['utc'],continuation=dict(path=str(B/'continuation-status02.json'),controller=record['controller'],owner=str(B/'continuation-owner02.json')),V15_ready=policy['V15_ready'],V17_source_freeze=dict(path=str(B/'source-freeze.json'),**pin(B/'source-freeze.json')),controls=policy['controls'],predecessor_V16=policy['predecessor_V16'],PLL=policy['PLL'],next='Wait for exact existing39controls, then same2GiB CPU6 map, measured native read depth, literal-tie import+allpin graph proof and original4ns three-corner preplacement. No PLL duplicate, no constraints relaxed.')
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
  expected=policy['controls']['pytest_identity']
  while True:
   owner.check();current=life.process_identity(expected['pid'])
   if current is None or current['start_ticks']!=expected['start_ticks'] or current['state']=='Z':break
   owner.cancelled.wait(10)
  assert '39 passed, 2 deselected' in (B/'controls01.log').read_text(),'Existing full frozen controls did not pass'
  assert pin(B/'source-only-peer-rx.json')==policy['peer_pin']
  assert json.loads((B/'source-only-peer-rx.json').read_text())['status'].startswith('PASS_V17_')
  lifecycle=policy['lifecycle_peer'];lifecycle_path=Path(lifecycle['path'])
  assert pin(lifecycle_path)=={k:lifecycle[k] for k in ['bytes','sha256']}
  assert json.loads(lifecycle_path.read_text())['status'].startswith('PASS_V17_')
  assert json.loads((B/'lifecycle-peer-pin02.json').read_text())==lifecycle
  stage('supersede_v16',[sys.executable,str(B/'supersede_v16_after_validation_v2.py')])
  stage('seal_controls',[sys.executable,str(B/'seal_controls.py')])
  stage('map',[sys.executable,str(B/'run_balanced_map.py')])
  mapped=Path('/dev/shm/nssoc-integrity-v17-balanced-map-01/mapped.json')
  stage('read_depth',[sys.executable,str(B/'measure_native_read_depth.py'),'--candidate',str(mapped),'--rejected','/dev/shm/nssoc-integrity-v14-balanced-map-01/mapped.json','--out',str(B/'native-read-depth-comparison.json')])
  module=json.loads(mapped.read_text())['modules']['soc_pcie_gen3_continuous_rx_integrity_v17']
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
