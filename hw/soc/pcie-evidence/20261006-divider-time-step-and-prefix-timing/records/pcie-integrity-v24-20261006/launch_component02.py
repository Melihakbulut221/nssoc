"""Owned CPU6/2GiB frozen V24 controls; native map remains separately gated."""
from pathlib import Path
import datetime,hashlib,json,os,resource,subprocess,sys,shutil
R=Path.cwd();B=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'scripts'))
import characterize_pcie_clock_trim_stream_v2 as life

def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
assert pin(life.__file__)['sha256']=='39312e364fa2a788784d88f3a63845f64db25bb420e2ee5d58c07a8c805bc886'
assert os.sched_getaffinity(0)=={6}
freeze=B/'component-source-freeze02.json';assert pin(freeze)['sha256']=='5bac8dc9531a542919b05ebd76cd397a33a64a31d69c03e9754d92626f6f84c9'
f=json.loads(freeze.read_text())
for p,v in f['sources'].items():assert pin(R/p)==v
for name,expected in f['selected_tools'].items():
 selected=Path(shutil.which(name)).absolute()
 assert str(selected)==expected['path'] and pin(selected)=={k:expected[k] for k in ('bytes','sha256')},'Selected native runtime differs'
def shared_floor(minimum):
 free=shutil.disk_usage('/dev/shm').free
 assert free>=minimum,('Shared scratch floor breached',free,minimum)
 return free
entry_free=shared_floor(1024**3)
peer=B/'component-source-peer-vco02.json';j=json.loads(peer.read_text());assert j['status']=='PASS_SOURCE_ONLY_V24_MATRIX_COMPONENT_CONTROLS' and not j['findings']
assert j['freeze']==pin(freeze) and j['launcher']==pin(Path(__file__))
D=Path('/dev/shm/nssoc-integrity-v24-matrix-controls01');assert not D.exists() and not (B/'component-status01.json').exists()
command=[sys.executable,'-m','pytest','-q','-p','no:cacheprovider',str(B/'test_matrix_relation01.py'),'--basetemp='+str(D),'--junitxml='+str(B/'component-controls01.xml')]
owner=life.ProcessOwner(B/'component-owner01.json')
r=dict(status='STARTING',controller=life.process_identity(os.getpid()),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),command=command,source_freeze=pin(freeze),source_peer=pin(peer),pytest_AS_bytes=2*1024**3,CPU6=True,elapsed_watchdog_seconds=None,entry_shared_free=entry_free,selected_tools=f['selected_tools'])
def save():
 r['utc']=datetime.datetime.now(datetime.UTC).isoformat();life.atomic(B/'component-status01.json',r)
 life.atomic(B/'active-checkpoint.json',dict(status=r['status'],controls=str(B/'component-status01.json'),controller=r['controller'],boot_id=r['boot_id'],source_freeze=dict(path=str(freeze),**pin(freeze)),native_map_started=False,scope='Standalone V24 finite matrix relation and four actual mutants only; product RTL remains V23. No native mapping or public-cycle acceptance from this component proof. Existing PLL untouched.'))
def limits():
 resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
save()
try:
 with owner:
  with (B/'component-controls01.log').open('x') as log:
   p=owner.launch('native',command,stdout=log,stderr=subprocess.STDOUT,preexec_fn=limits,env={**{k:v for k,v in os.environ.items()if k not in ('PYTHONPATH','PYTHONHOME','PYTHONEXECUTABLE')},'TMPDIR':'/dev/shm','PYTHONDONTWRITEBYTECODE':'1','OMP_NUM_THREADS':'1','YOSYS_MAX_THREADS':'1'})
   r.update(status='RUNNING_FROZEN_V24_CONTROLS',pytest=life.process_identity(p.pid));save()
   while p.poll() is None:
    owner.check();shared_floor(528*1024**2);owner.cancelled.wait(0.05)
   owner.check();code=owner.complete(p);owner.check()
   r['terminal_shared_free']=shared_floor(528*1024**2)
  r.update(returncode=code,status='COMPLETE_PENDING_INDEPENDENT_CONTROL_RECOUNT' if code==0 else 'FAILED_CONTROLS_RETAINED',log=pin(B/'component-controls01.log'))
  for p,v in f['sources'].items():assert pin(R/p)==v
  assert pin(peer)==r['source_peer'];owner.check()
 owner.check()
except BaseException as error:
 r.update(status='CANCELLED_OR_FAILED_CONTROLS_RETAINED',error=repr(error));raise
finally:
 r['stop_reason']=owner.reason
 if owner.reason and owner.reason.startswith('Parent received SIG'):r['status']='CANCELLED_CONTROLS_RETAINED'
 save()
