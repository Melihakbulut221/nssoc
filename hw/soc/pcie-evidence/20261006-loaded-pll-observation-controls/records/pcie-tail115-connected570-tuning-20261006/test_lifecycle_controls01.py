# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Real owned short children/FIFO/signals, no SPICE solver or circuit results."""
from pathlib import Path
import copy,gzip,json,os,resource,signal,subprocess,sys
from unittest.mock import patch
B=Path(__file__).resolve().parent;sys.path.insert(0,str(B))
import characterize_clamped570_01 as m
import launch_three01 as launcher
D=B/'lifecycle-controls01'

def main():
 resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3));resource.setrlimit(resource.RLIMIT_CORE,(0,0));assert os.sched_getaffinity(0)=={10}
 assert not D.exists();D.mkdir();cases=[]
 for signum in (signal.SIGTERM,signal.SIGINT):
  original={s:signal.getsignal(s)for s in(signal.SIGINT,signal.SIGTERM)};attempts=[]
  def before(*args):os.kill(os.getpid(),signum);attempts.append('should not launch')
  with patch.object(m,'run',before):
   try:launcher.boundary_run(D,.6)
   except RuntimeError as e:assert signal.Signals(signum).name in str(e)
   else:raise AssertionError('Lost signal before inner owner')
  assert not attempts and all(signal.getsignal(s)==h for s,h in original.items())
  cases.append(dict(case='real_'+signal.Signals(signum).name+'_before_inner_owner',passed=True,attempts=attempts))
  owned=D/(signal.Signals(signum).name+'-completed-owner.json')
  def after(*args):
   with m.life.ProcessOwner(owned)as owner:
    child=owner.launch('native',[sys.executable,'-c','print("closed child")'],stdout=subprocess.DEVNULL);owner.wait(child);owner.check()
   owner.check();os.kill(os.getpid(),signum)
  with patch.object(m,'run',after):
   try:launcher.boundary_run(D,.6)
   except RuntimeError as e:assert signal.Signals(signum).name in str(e)
   else:raise AssertionError('Lost signal after inner owner')
  saved=json.loads(owned.read_text());assert saved['processes'][0]['status']=='REAPED_NO_LIVE_MEMBERS'
  assert all(signal.getsignal(s)==h for s,h in original.items());cases.append(dict(case='real_'+signal.Signals(signum).name+'_after_inner_owner',passed=True,owner=m.pin(owned)))
 # Call complete production run_native with a finite FIFO-writing executable.
 # The executable is a declared stand-in; it is not the pinned ngspice binary.
 c,rows,_=m.config(.6);c=copy.deepcopy(c);c.update(stop_s=3*c['step_s'],window_s=[0,3*c['step_s']]);fixture=(B/'finite-controls01/positive.raw').resolve();body=fixture.read_bytes()
 oldroot=m.NATIVE_ROOT;oldng=m.n.NG;oldmeasurement=m.measurement;m.NATIVE_ROOT=D/'native';m.NATIVE_ROOT.mkdir();m.measurement=lambda data,c:dict(passed=False,finite_transport_fixture_only=True)
 try:
  for label in ('clean','term','interrupt'):
   folder=m.NATIVE_ROOT/label;folder.mkdir();writer=D/(label+'-writer.py')
   code='#!'+sys.executable+'\nimport os,signal,time\nfrom pathlib import Path\nbody=Path('+repr(str(fixture))+').read_bytes()\nwith open("stream.fifo","wb",buffering=0) as f:\n left=body\n while left:\n  n=f.write(left);assert n>0;left=left[n:]\n'
   if label!='clean':code+=' os.kill(os.getppid(),signal.'+('SIGTERM'if label=='term'else'SIGINT')+')\n while True:time.sleep(.05)\n'
   writer.write_text(code);writer.chmod(0o755);m.n.NG=writer
   try:result=m.run_native(folder,rows,c)
   except m.life.Cancelled as e:assert label!='clean'and('SIGTERM'if label=='term'else'SIGINT')in str(e)
   else:assert label=='clean'and result['rows']==4 and result['safety']['passed']
   saved=json.loads((folder/'owned-processes.json').read_text());assert len(saved['processes'])==1
   p=saved['processes'][0];assert m.life.process_identity(p['identity']['pid'])is None and not any(x['state']!='Z'for x in m.life.group_members(p['process_group']))
   assert p['status']==('REAPED_NO_LIVE_MEMBERS'if label=='clean'else'FAILURE_REAPED')
   execution=json.loads((folder/'execution.json').read_text());assert execution['actual_affinity']==[10]and execution['address_space_limit_bytes']==2*1024**3 and execution['elapsed_watchdog_seconds']is None
   assert gzip.decompress((folder/'wave.raw.gz').read_bytes())==body
   cases.append(dict(case='actual_full_run_native_finite_FIFO_'+label,passed=True,writer=m.pin(writer),owner=m.pin(folder/'owned-processes.json'),execution=m.pin(folder/'execution.json'),raw=m.pin(folder/'wave.raw.gz'),birth=p['identity'],child_absent=True))
 finally:m.NATIVE_ROOT=oldroot;m.n.NG=oldng;m.measurement=oldmeasurement
 report=dict(status='PASS_ACTUAL570_BOUNDARY_SIGNALS_AND_FULL_NATIVE_OWNER_FINITE_FIFO',cases=len(cases),outcomes=cases,method=m.pin(__file__),driver=m.pin(m.__file__),launcher=m.pin(launcher.__file__),fixture=m.pin(fixture),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),scope='Seven actual short-process/signal controls using exact production boundary and run_native bodies. Three FIFO-writing children stand in for ngspice; no circuit/model run and no physical acceptance. All exact recorded births/groups are closed. All capture bytes read back.')
 (D/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(result=m.pin(D/'result.json'),cases=len(cases))))
if __name__=='__main__':main()
