# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""One detached, finite RX16one proof/port pipeline; no native elapsed timeout."""
from pathlib import Path
import hashlib,json,os,resource,signal,shutil,subprocess,sys,time
S=Path(__file__).resolve().parent;B=S.parent;R=Path.cwd();C=S/'proof16one-pipeline01'
sys.path.insert(0,str(B))
from owned_lifecycle16 import owned_popen,stop_failed_group
PYTHON=R/'hw/soc/tools/cocotb-venv/bin/python'
E=Path('/dev/shm/nssoc-rx-prefetch-v2-repair16one-equivalence');P=Path('/dev/shm/nssoc-rx-prefetch-v2-repair16one-physical-replay-01')
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def gate():
 fpath=S/'proof-source-freeze16one.json';f=json.loads(fpath.read_text());assert pin(fpath)==dict(bytes=4087,sha256='f07f4355d5e677df9903cac07fd900b72925dc6efe0611d5e47c06c5d8b066bb')
 p=S/'proof-source-only-peer-root16one.json';peer=json.loads(p.read_text());assert peer['status']=='PASS_SOURCE_ONLY_RX16ONE_PROOF_PORTS' and peer['findings']==[] and peer['freeze']==pin(fpath)
 for k in ('sources','inputs'):assert f[k]=={p:pin(p)for p in f[k]}
 assert shutil.disk_usage('/dev/shm').free>=528*1024**2
 return {'freeze':pin(fpath),'peer':pin(p),'method':pin(__file__),'helper':pin(B/'owned_lifecycle16.py'),'python':pin(PYTHON)}
def stop(number,_):raise InterruptedError(f'Parent signal {number}')
def limits():
 resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.sched_setaffinity(0,{8});signal.pthread_sigmask(signal.SIG_UNBLOCK,{signal.SIGINT,signal.SIGTERM})
def save(record):
 p=C/'status.tmp';p.write_text(json.dumps(record,indent=2)+'\n');p.replace(C/'status.json')
def clean_env():
 return {k:v for k,v in os.environ.items() if k not in ('PYTHONPATH','PYTHONHOME','PYTHONEXECUTABLE')}
def run_owned_stage(command, log_path, row, record, original):
 assert gate()==original;p=None;complete=False
 with log_path.open('x')as log:
  try:
   p=owned_popen(command,cwd=R,env=clean_env(),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,preexec_fn=limits)
   row['identity']=p.nssoc_owned_identity;save(record)
   while p.poll()is None:
    assert shutil.disk_usage('/dev/shm').free>=528*1024**2;time.sleep(.25)
   row['returncode']=p.wait();assert row['returncode']==0
   assert shutil.disk_usage('/dev/shm').free>=528*1024**2;assert gate()==original;complete=True;save(record)
  finally:
   if p is not None and not complete:stop_failed_group(p,grace_seconds=15)
def run():
 assert os.sched_getaffinity(0)=={8};assert not E.exists() and not P.exists();assert shutil.disk_usage('/dev/shm').free>=1024**3
 original=gate();C.mkdir(exist_ok=False);record={'status':'RUNNING_PROOF_PORTS','pins':original,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'stages':[],'healthy_elapsed_timeout':None,'scope':'Exact existing canonical proof/ten actual faults/six native ports; no route or timing acceptance'}
 for s in (signal.SIGTERM,signal.SIGINT):signal.signal(s,stop)
 save(record)
 try:
  for index,name in enumerate(('normalize_repair16one.py','proof_gate_repair16one.py','replay_repair16one.py')):
   row={'method':name,'returncode':None};record['stages'].append(row)
   run_owned_stage([str(PYTHON),'-u',str(B/name)],C/f'{index+1}-{name}.log',row,record,original)
   save(record)
  from proof_gate_repair16one import verify_binding
  verify_binding();assert json.loads((P/'result.json').read_text())['tests']=={'passed':6,'failed':0,'skipped':0}
  record.update(status='COMPLETE_BOUND_PROOF_TEN_FAULTS_SIX_PORTS_NO_ROUTE',proof_binding=pin(E/'proof-execution-binding.json'),ports=pin(P/'result.json'),port_owner=pin(P/'owned-driver.json'));save(record)
 except BaseException as error:
  record.update(status='FAILED_RETAINED',error=repr(error));save(record);raise
if __name__=='__main__':
 if sys.argv[1:]==['--run']:run()
 else:
  assert not sys.argv[1:]and not C.exists()and not E.exists()and not P.exists();g=gate();assert shutil.disk_usage('/dev/shm').free>=1024**3
  with (S/'proof16one-detached.log').open('x')as log:
   p=subprocess.Popen(['taskset','-c','8',str(PYTHON),'-u',str(Path(__file__).resolve()),'--run'],cwd=R,env=clean_env(),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  stat=Path(f'/proc/{p.pid}/stat').read_text().rsplit(')',1)[1].split();receipt={'pid':p.pid,'start_ticks':stat[19],'group':int(stat[2]),'pins':g,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()};(S/'proof16one-detached.json').write_text(json.dumps(receipt,indent=2)+'\n');print(receipt)
