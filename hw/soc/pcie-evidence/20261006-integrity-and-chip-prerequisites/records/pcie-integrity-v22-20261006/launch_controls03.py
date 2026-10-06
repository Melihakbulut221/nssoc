"""Owned CPU6/2GiB frozen V22 controls; native map remains separately gated."""
from pathlib import Path
import datetime,hashlib,json,os,resource,subprocess,sys
R=Path.cwd();B=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'scripts'))
import characterize_pcie_clock_trim_stream_v2 as life

def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
assert pin(life.__file__)['sha256']=='39312e364fa2a788784d88f3a63845f64db25bb420e2ee5d58c07a8c805bc886'
assert os.sched_getaffinity(0)=={6}
freeze=B/'source-freeze03.json';assert pin(freeze)['sha256']=='46d599c89a5a19fee6e87dd9fbfa006a7d29f81922530256ab348685ea50e21c'
f=json.loads(freeze.read_text())
for p,v in f['sources'].items():assert pin(R/p)==v
peer=B/'source-only-peer-vco03.json';j=json.loads(peer.read_text());assert j['status']=='PASS_SOURCE_ONLY_V22_QUARANTINED_CACHE' and not j['findings']
assert j['freeze']==pin(freeze)
assert j['targeted_helper']==pin(B/'targeted_controls03.py')
D=Path('/dev/shm/nssoc-integrity-v22-public-controls03');assert not D.exists() and not (B/'controls-status03.json').exists()
command=[sys.executable,'-m','pytest','-q','-p','no:cacheprovider','sw/tests/test_pcie_gen3_integrity_v22_miter.py',str(B/'targeted_controls03.py'),'-k','not 4118','--basetemp='+str(D),'--junitxml='+str(B/'controls03.xml')]
owner=life.ProcessOwner(B/'controls-owner03.json')
r=dict(status='STARTING',controller=life.process_identity(os.getpid()),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),command=command,source_freeze=pin(freeze),source_peer=pin(peer),pytest_AS_bytes=2*1024**3,CPU6=True,elapsed_watchdog_seconds=None)
def save():
 r['utc']=datetime.datetime.now(datetime.UTC).isoformat();life.atomic(B/'controls-status03.json',r)
 life.atomic(B/'active-checkpoint.json',dict(status=r['status'],controls=str(B/'controls-status03.json'),controller=r['controller'],boot_id=r['boot_id'],source_freeze=dict(path=str(freeze),**pin(freeze)),native_map_started=False,scope='Separate V22 cache writer qualification fromV21; same latency, allpublic cyclemiter and cachefault quarantine; original4ns and2GiB fixed. Full functional controls plus independentpeer mustpass before any native mapping. ExistingPLL untouched.'))
def limits():
 resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
save()
try:
 with owner:
  with (B/'controls03.log').open('x') as log:
   p=owner.launch('native',command,stdout=log,stderr=subprocess.STDOUT,preexec_fn=limits,env={**os.environ,'TMPDIR':'/dev/shm','PYTHONDONTWRITEBYTECODE':'1','OMP_NUM_THREADS':'1','YOSYS_MAX_THREADS':'1'})
   r.update(status='RUNNING_FROZEN_V22_CONTROLS',pytest=life.process_identity(p.pid));save()
   code=owner.wait(p);owner.check()
  r.update(returncode=code,status='COMPLETE_PENDING_INDEPENDENT_CONTROL_RECOUNT' if code==0 else 'FAILED_CONTROLS_RETAINED',log=pin(B/'controls03.log'))
  for p,v in f['sources'].items():assert pin(R/p)==v
  assert pin(peer)==r['source_peer'];owner.check()
 owner.check()
except BaseException as error:
 r.update(status='CANCELLED_OR_FAILED_CONTROLS_RETAINED',error=repr(error));raise
finally:
 r['stop_reason']=owner.reason
 if owner.reason and owner.reason.startswith('Parent received SIG'):r['status']='CANCELLED_CONTROLS_RETAINED'
 save()
