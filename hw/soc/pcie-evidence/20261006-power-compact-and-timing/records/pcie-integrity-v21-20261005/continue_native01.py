"""One bounded continuation of frozen V21 controls/map/import/original4ns STA."""
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
assert pin(B/'source-freeze04.json')['sha256']=='48be11f969876f9738a70f993e31eea6ff63a425a3b26227dfcdc2e55a33d6df'
record=dict(status='VALIDATED_MERGED_V21_CONTROLS_READY_NATIVE',controller=life.process_identity(os.getpid()),affinity=[6],policy=pin(B/'continuation-policy01.json'),stages=[],elapsed_watchdog_seconds=None,physical_acceptance=False)
owner=life.ProcessOwner(B/'continuation-owner01.json')

def explicit_stop():
 return bool(owner.reason and owner.reason.startswith('Parent received SIG'))

def save():
 record['utc']=datetime.datetime.now(datetime.UTC).isoformat()
 life.atomic(B/'continuation-status01.json',record)
 # Operational checkpoint is deliberately mutable; all evidence pins it points
 # to are immutable. It is the single root-monitor entry for these owned jobs.
 active=dict(status=record['status'],utc=record['utc'],continuation=dict(path=str(B/'continuation-status01.json'),controller=record['controller'],owner=str(B/'continuation-owner01.json')),V21_source_freeze=dict(path=str(B/'source-freeze04.json'),**pin(B/'source-freeze04.json')),controls=policy['controls'],PLL=policy['PLL'],next='Owned same2GiB CPU6 map, measured native read depth, literal-tie import+allpin graph proof and original4ns three-corner preplacement. Composite16 public cases, descriptor4096+14literal and meaningful faults, explicit ready1+one-cycle relation; initial failed witness and unqualified negative retained. Actual32passed/1failed executions across33tests; no PLL duplicate and no constraints relaxed.')
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
  core=Path(policy['controls']['validation']['path']);assert pin(core)=={k:policy['controls']['validation'][k]for k in ['bytes','sha256']}
  result=json.loads(core.read_text());assert result['status']=='PASS_REGISTERED_RETIRE_COMPOSITE_PUBLIC_AND_LITERAL_CONTROLS' and result['historical_failed_executions']==1 and result['pytest_passed_executions']==32
  assert result['source_freeze']==pin(B/'source-freeze04.json') and result['source_peer']==pin(B/'source-only-peer-rx04.json')
  peer_path=B/'native-source-only-peer01.json';peer=json.loads(peer_path.read_text());assert peer['status']=='PASS_SOURCE_ONLY_V21_MERGED_NATIVE_CONTINUATION' and peer['policy']==pin(B/'continuation-policy01.json') and not peer['findings']
  stage('map',[sys.executable,str(B/'run_balanced_map.py')])
  mapped=Path('/dev/shm/nssoc-integrity-v21-balanced-map-01/mapped.json')
  stage('registered_boundary',[sys.executable,str(B/'measure_registered_boundary.py')])
  module=json.loads(mapped.read_text())['modules']['soc_pcie_gen3_continuous_rx_integrity_v21']
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
