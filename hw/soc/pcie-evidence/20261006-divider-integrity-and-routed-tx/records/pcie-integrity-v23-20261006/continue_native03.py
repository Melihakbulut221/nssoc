"""One bounded continuation of frozen V23 controls/map/import/original4ns STA."""
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
assert pin(B/'source-freeze03.json')['sha256']=='81b39160001de5717fa414371ec18b62772e367e7625e7aaab3af3b0f3af0540'
record=dict(status='VALIDATED_V23_CONTROLS_READY_NATIVE',controller=life.process_identity(os.getpid()),affinity=[6],policy=pin(B/'continuation-policy01.json'),stages=[],elapsed_watchdog_seconds=None,physical_acceptance=False)
owner=life.ProcessOwner(B/'continuation-owner01.json')

def explicit_stop():
 return bool(owner.reason and owner.reason.startswith('Parent received SIG'))

def save():
 record['utc']=datetime.datetime.now(datetime.UTC).isoformat()
 life.atomic(B/'continuation-status01.json',record)
 # Operational checkpoint is deliberately mutable; all evidence pins it points
 # to are immutable. It is the single root-monitor entry for these owned jobs.
 active=dict(status=record['status'],utc=record['utc'],continuation=dict(path=str(B/'continuation-status01.json'),controller=record['controller'],owner=str(B/'continuation-owner01.json')),V23_source_freeze=dict(path=str(B/'source-freeze03.json'),**pin(B/'source-freeze03.json')),controls=policy['controls'],PLL=policy['PLL'],next='Owned same2GiB CPU6 freshmap, actual registeredboundary, literal-tieimport/fullpin graph and original4ns three-corner preplacement. Composite47executions with10retainedhistorical failures; original18case pluscorrected18th direct/miter and meaningful realblock promotioncontrol required. Full independent saved-byte peer required. No PLLduplicate or acceptance relaxation.')
 life.atomic(B/'active-checkpoint.json',active)

def verify_sources():
 for p,v in policy['source_pins'].items():assert pin(R/p)==v
 for p,v in policy['method_pins'].items():assert pin(p)==v

def stage(name,command):
 owner.check();verify_sources();assert shutil.disk_usage('/dev/shm').free>=1024**3
 row=dict(name=name,command=command,started_utc=datetime.datetime.now(datetime.UTC).isoformat(),status='RUNNING');record['stages'].append(row);record['status']='RUNNING_'+name;save()
 with (B/(name+'.controller.log')).open('x') as log:
  process=owner.launch('native',command,stdout=log,stderr=subprocess.STDOUT,env={**{k:v for k,v in os.environ.items()if k not in ('PYTHONPATH','PYTHONHOME','PYTHONEXECUTABLE')},'TMPDIR':'/dev/shm','PYTHONDONTWRITEBYTECODE':'1','YOSYS_MAX_THREADS':'1','OMP_NUM_THREADS':'1'})
  row['identity']=life.process_identity(process.pid);save()
  code=owner.wait(process);owner.check()
 row.update(returncode=code,status='COMPLETE' if code==0 else 'FAILED_RETAINED',finished_utc=datetime.datetime.now(datetime.UTC).isoformat(),log=pin(B/(name+'.controller.log')));save()
 assert code==0,(name,code)
 verify_sources()

save()
try:
 with owner:
  core=Path(policy['controls']['validation']['path']);assert pin(core)=={k:policy['controls']['validation'][k]for k in ['bytes','sha256']}
  result=json.loads(core.read_text());assert result['status']=='PASS_V23_ADJACENT_HEADER_COMPOSITE_CONTROLS'
  assert [(x['passed'],x['failed'],x['skipped'])for x in result['campaigns']]==[(28,7,0),(6,3,0),(3,0,0)]
  assert result['source_freeze']==pin(B/'source-freeze03.json') and result['source_peer']==pin(B/'source-only-peer-vco03.json')
  controls_peer=Path(policy['controls']['independent_peer']['path']);assert pin(controls_peer)=={k:policy['controls']['independent_peer'][k]for k in ['bytes','sha256']}
  controls_review=json.loads(controls_peer.read_text());assert controls_review['status']=='PASS_INDEPENDENT_SAVED_V23_COMPOSITE_FUNCTIONAL_CONTROLS'and not controls_review['findings']and controls_review['validation']==pin(core)
  peer_path=B/'native-source-only-peer01.json';peer=json.loads(peer_path.read_text());assert peer['status']=='PASS_SOURCE_ONLY_V23_NATIVE_CONTINUATION' and peer['policy']==pin(B/'continuation-policy01.json') and not peer['findings']
  stage('map',[sys.executable,str(B/'run_balanced_map03.py')])
  mapped=Path('/dev/shm/nssoc-integrity-v23-balanced-map-01/mapped.json')
  stage('registered_boundary',[sys.executable,str(B/'measure_registered_boundary.py')])
  module=json.loads(mapped.read_text())['modules']['soc_pcie_gen3_continuous_rx_integrity_v23']
  census=dict(source=pin(mapped),signed={n:v['bits'] for n,v in module['netnames'].items() if v.get('signed')},scope='Only mapped native wire-label signedness, not cell/port graph, is normalized for OpenSTA. All pin-driver relations proved after literal ties.')
  assert not (B/'signed-wire-census.json').exists();life.atomic(B/'signed-wire-census.json',census)
  stage('import',[sys.executable,str(B/'balanced_import02.py')])
  stage('import_graph_proof',[sys.executable,str(B/'prove_balanced_import.py')])
  stage('preplacement',[sys.executable,str(B/'balanced_preplacement02.py')])
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
