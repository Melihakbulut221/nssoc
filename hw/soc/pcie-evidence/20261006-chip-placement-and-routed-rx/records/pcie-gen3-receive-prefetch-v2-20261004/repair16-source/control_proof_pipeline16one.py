# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual two-level failure cleanup of production run_owned_stage; toy child only."""
from pathlib import Path
import hashlib,importlib.util,json,os,signal,subprocess,sys,time
S=Path(__file__).resolve().parent;R=Path.cwd();O=Path('/dev/shm/nssoc-rx16one-pipeline-lifecycle01')
spec=importlib.util.spec_from_file_location('pipeline16one',S/'run_proof_ports16one.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def pin(p):return {'bytes':Path(p).stat().st_size,'sha256':hashlib.sha256(Path(p).read_bytes()).hexdigest()}
def who():
 s=Path(f'/proc/{os.getpid()}/stat').read_text().rsplit(')',1)[1].split();return dict(pid=os.getpid(),start_ticks=s[19],group=int(s[2]))
def same(i):
 try:s=Path(f"/proc/{i['pid']}/stat").read_text().rsplit(')',1)[1].split();return s[19]==i['start_ticks']and s[0]!='Z'
 except FileNotFoundError:return False
mode=sys.argv[1:] or ['test']
if mode==['native']:
 assert not any(k in os.environ for k in ('PYTHONHOME','PYTHONPATH','PYTHONEXECUTABLE'));signal.signal(signal.SIGTERM,signal.SIG_IGN);(O/'native.json').write_text(json.dumps(who()))
 while True:time.sleep(.1)
elif mode==['stage']:
 for sig in (signal.SIGINT,signal.SIGTERM):signal.signal(sig,m.stop)
 (O/'stage.json').write_text(json.dumps(who()));p=None;done=False
 try:
  with (O/'native.log').open('x')as log:
   p=m.owned_popen([str(m.PYTHON),'-u',str(Path(__file__).resolve()),'native'],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,preexec_fn=m.limits,env=m.clean_env())
   while p.poll()is None:time.sleep(.05)
   assert p.wait()==0;done=True
 finally:
  if p is not None and not done:m.stop_failed_group(p)
elif mode==['controller']:
 m.C=O/'controller';m.C.mkdir();m.gate=lambda:{'fixed':'toy'}
 for sig in (signal.SIGINT,signal.SIGTERM):signal.signal(sig,m.stop)
 for k in ('PYTHONHOME','PYTHONPATH','PYTHONEXECUTABLE'):os.environ[k]='deliberately-invalid-control'
 r={'status':'RUNNING','stages':[]};row={'method':'toy-stage','returncode':None};r['stages'].append(row)
 try:m.run_owned_stage([str(m.PYTHON),'-u',str(Path(__file__).resolve()),'stage'],O/'stage.log',row,r,{'fixed':'toy'})
 except InterruptedError as error:r.update(status='EXPECTED_SIGNAL_FAILURE_RETAINED',error=repr(error));m.save(r);raise
else:
 assert mode==['test'];O.mkdir();p=None;ids=[];start=time.monotonic()
 try:
  with (O/'controller.log').open('x')as log:p=m.owned_popen(['taskset','-c','8',str(m.PYTHON),'-u',str(Path(__file__).resolve()),'controller'],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env=m.clean_env())
  deadline=time.monotonic()+10
  while not (O/'native.json').exists():
   assert p.poll()is None and time.monotonic()<deadline,'Toy native readiness failure';time.sleep(.02)
  ids=[p.nssoc_owned_identity,json.loads((O/'stage.json').read_text()),json.loads((O/'native.json').read_text())];assert all(same(i)for i in ids)
  p.anchored();os.kill(p.pid,signal.SIGTERM)
  deadline=time.monotonic()+18
  while p.poll()is None:assert time.monotonic()<deadline,'Toy cleanup deadline';time.sleep(.02)
  code=p.wait();assert code!=0 and all(not same(i)for i in ids)
  assert all(not m.owned_popen.__globals__['live_members'](i.get('group',i.get('process_group')))for i in ids)
  record=json.loads((O/'controller/status.json').read_text());assert record['status']=='EXPECTED_SIGNAL_FAILURE_RETAINED'
  receipt={'status':'PASS_ACTUAL_NESTED_STAGE_NATIVE_SIGNAL_CLEANUP','identities':ids,'controller_returncode':code,'elapsed_seconds':time.monotonic()-start,'all_three_groups_no_live_members':True,'native_ignored_SIGTERM':True,'production_stage_function_used':True,'production_outer_failure_grace_seconds':15,'actual_stage_env_sanitized':True,'method':pin(__file__),'production':pin(S/'run_proof_ports16one.py'),'helper':pin(S.parent/'owned_lifecycle16.py'),'raw':{str(x.relative_to(O)):pin(x)for x in O.rglob('*')if x.is_file()}}
  (S/'proof16one-lifecycle-control.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
 finally:
  if p is not None and p.returncode is None:m.stop_failed_group(p,grace_seconds=15)
