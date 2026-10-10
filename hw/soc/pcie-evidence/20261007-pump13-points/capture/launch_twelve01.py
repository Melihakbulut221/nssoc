# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""One detached sequential twelve-case campaign after full source/control peer."""
from pathlib import Path
import datetime,hashlib,json,os,resource,signal,shutil,subprocess,sys
R=Path.cwd();B=Path(__file__).resolve().parent
sys.path.insert(0,str(B));sys.path.insert(0,str(R/'scripts'))
import characterize_pump13_02 as m

def pin(path):
 path=Path(path)
 with path.open('rb')as f:return dict(bytes=path.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())

def verify(*,initial):
 freeze=B/'source-freeze01.json';f=json.loads(freeze.read_text())
 for path,value in f['pins'].items():assert pin(path)==value,path
 peer=B/'source-only-peer-root01.json';p=json.loads(peer.read_text())
 assert p['status']=='PASS_SOURCE_ONLY_PUMP13_EXECUTABLE_AND_CONTROLS'and p['findings']==[]and p['freeze']==pin(freeze)
 sign=m.NATIVE_ROOT/'sign-control01/result.json';s=json.loads(sign.read_text())
 assert s['status']=='PASS_ACTUAL_IDEAL_CURRENT_SOURCE_CLAMP_SIGN_CONTROLS' and s['source_freeze']==pin(freeze) and s['source_peer']==pin(peer)
 assert s['cases']==6 and all(x['passed']for x in s['outcomes'])
 for name,value in s['outputs'].items():assert pin(sign.parent/name)==value,name
 assert os.sched_getaffinity(0)=={10}
 assert shutil.disk_usage('/dev/shm').free>=1024**3
 assert B.stat().st_dev!=Path('/dev/shm').stat().st_dev
 used=m.sampled_bytes(m.NATIVE_ROOT)
 assert shutil.disk_usage(B).free>=m.AGGREGATE_LIMIT-used+m.SSD_FLOOR
 for value in m.CASES:
  c,rows,texts=m.config(value)
  assert len(rows)==13 and len(m.n.vectors(rows,c['extra_vectors']))==27
  folder=m.NATIVE_ROOT/(value+'-01')
  if initial:assert not folder.exists()
  m.guard(folder)
 return dict(freeze=pin(freeze),peer=pin(peer),shared_free=shutil.disk_usage('/dev/shm').free,ssd_free=shutil.disk_usage(B).free,aggregate_bytes=used,boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),utc=datetime.datetime.now(datetime.UTC).isoformat())

def boundary_run(out,value):
 def stop(signum,frame):raise RuntimeError('Controller received '+signal.Signals(signum).name)
 old={s:signal.getsignal(s)for s in (signal.SIGINT,signal.SIGTERM)}
 try:
  for s in old:signal.signal(s,stop)
  return m.run(out,value,'')
 finally:
  for s,h in old.items():signal.signal(s,h)

def controller():
 resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 preflight=verify(initial=True)
 result=dict(status='RUNNING_TWELVE_PUMP13_DIAGNOSTICS',preflight=preflight,controller=m.life.process_identity(os.getpid()),points=[],polarity_selected=False,connected_loop_acceptance=False)
 m.n.common.atomic(B/'campaign01.json',result)
 try:
  for value in m.CASES:
   before=verify(initial=False);out=m.NATIVE_ROOT/(value+'-01');assert not out.exists()
   result['active_case']=value;m.n.common.atomic(B/'campaign01.json',result)
   native=boundary_run(out,value)
   m.guard(out);after=verify(initial=False)
   assert before['boot_id']==after['boot_id']==preflight['boot_id']
   result['points'].append(dict(case=value,status=native['status'],result_path=str(out/'result.json'),result_pin=pin(out/'result.json'),execution=pin(out/'execution.json'),owned_processes=pin(out/'owned-processes.json'),preflight=before,terminal=after))
   m.n.common.atomic(B/'campaign01.json',result)
  assert len(result['points'])==12
  result['status']='CLOSED_TWELVE_PUMP13_DIAGNOSTICS_NOT_LOADED_FORCE_ACCEPTANCE'
  result.pop('active_case',None)
  result['all_twelve_cases_passed']=all(x['status']=='PASS_NATIVE_PUMP13_IDEAL_COMMAND_POINT'for x in result['points'])
  return 0
 except BaseException as error:
  result.update(status='ERROR_OR_INTERRUPTION_RETAINED',error=repr(error));raise
 finally:
  result['utc']=datetime.datetime.now(datetime.UTC).isoformat();m.n.common.atomic(B/'campaign01.json',result)

def launch():
 preflight=verify(initial=True)
 assert not(B/'campaign01.json').exists()
 with(B/'launch-once01.json').open('x')as f:json.dump(preflight,f,indent=2)
 command=['taskset','-c','10',str(R/'hw/soc/tools/cocotb-venv/bin/python'),str(Path(__file__).resolve()),'--controller']
 env={k:v for k,v in os.environ.items()if k not in ('PYTHONPATH','PYTHONHOME','PYTHONEXECUTABLE','PYTHONOPTIMIZE','GH_TOKEN','GITHUB_TOKEN','LD_PRELOAD')}
 env.update(PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
 with(B/'controller01.log').open('x')as log:
  p=subprocess.Popen(command,cwd=R,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,env=env)
  identity=m.life.process_identity(p.pid)
 receipt=dict(status='DETACHED_CONTROLLER_STARTED_NATIVE_PROGRESS_REQUIRED',controller=identity,command=command,preflight=preflight,launcher=pin(Path(__file__)))
 m.n.common.atomic(B/'detached-launch01.json',receipt);print(json.dumps(receipt))

if __name__=='__main__':
 if sys.argv[1:]==['--controller']:raise SystemExit(controller())
 assert not sys.argv[1:];launch()
