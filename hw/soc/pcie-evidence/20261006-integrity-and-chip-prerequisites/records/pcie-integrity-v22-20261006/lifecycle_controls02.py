"""Short real-process controls only; no hardware tool invoked."""
from pathlib import Path
import hashlib,json,os,signal,subprocess,sys,time
import native_lifecycle02 as guard
B=Path(__file__).resolve().parent;rows=[]
def spawn(code):
 old=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGINT,signal.SIGTERM})
 try:
  p=subprocess.Popen([sys.executable,'-c',code],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True,preexec_fn=lambda:signal.pthread_sigmask(signal.SIG_UNBLOCK,{signal.SIGINT,signal.SIGTERM}))
  own=guard.OwnedNative(p)
 finally:signal.pthread_sigmask(signal.SIG_SETMASK,old)
 return p,own
p,o=spawn('pass');assert p.wait()==0;guard.free_floor(528*1024**2);r=o.kill_and_reap();assert r['status']=='ALREADY_REAPED_NO_SIGNAL';rows.append(dict(case='clean_completion_already_reaped_no_signal',receipt=r))
p,o=spawn('pass');assert p.wait()==0
try:guard.free_floor(528*1024**2-1);raise AssertionError('Terminal floor missed')
except RuntimeError:r=o.kill_and_reap()
assert r['status']=='ALREADY_REAPED_NO_SIGNAL';rows.append(dict(case='actual_completed_child_terminal_floor_rejected_no_signal',receipt=r))
p,o=spawn('import time;time.sleep(30)');wrong=dict(o.birth,start_ticks=str(int(o.birth['start_ticks'])+1));right=o.birth;o.birth=wrong
try:o.kill_and_reap();raise AssertionError('Wrong birth accepted')
except RuntimeError:assert p.poll()is None;rows.append(dict(case='actual_live_wrong_birth_refused_child_alive',receipt=o.cleanup))
o.birth=right;rows.append(dict(case='actual_live_exact_birth_failure_cleanup',receipt=o.kill_and_reap()));assert p.returncode==-signal.SIGKILL
p,o=spawn('import time;time.sleep(30)');right=o.birth;o.birth=dict(right,process_group=right['process_group']+1)
try:o.kill_and_reap();raise AssertionError('Wrong group accepted')
except RuntimeError:assert p.poll()is None;rows.append(dict(case='actual_live_wrong_group_refused_child_alive',receipt=o.cleanup))
o.birth=right;o.kill_and_reap()
# Run the same owner in a real SIGTERM-receiving wrapper, with a native sleeper.
worker=B/'lifecycle-signal-worker02.py';worker.write_text('from pathlib import Path\nimport json,os,signal,subprocess,sys,time\nfrom native_lifecycle02 import OwnedNative\nB=Path(__file__).resolve().parent\ndef stop(s,f):raise InterruptedError(s)\nsignal.signal(signal.SIGTERM,stop)\np=subprocess.Popen([sys.executable,"-c","import time;time.sleep(30)"],start_new_session=True)\no=OwnedNative(p)\n(B/"lifecycle-signal-birth02.json").write_text(json.dumps(dict(wrapper=os.getpid(),native=o.birth)))\ntry:\n while p.poll()is None:time.sleep(.01)\nexcept InterruptedError:\n r=o.kill_and_reap();(B/"lifecycle-signal-receipt02.json").write_text(json.dumps(r));raise SystemExit(7)\n')
p=subprocess.Popen([sys.executable,str(worker)],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
for _ in range(500):
 if(B/'lifecycle-signal-birth02.json').exists():break
 time.sleep(.01)
else:raise AssertionError('Signal worker not ready')
a=json.loads((B/'lifecycle-signal-birth02.json').read_text());assert a['wrapper']==p.pid;os.kill(p.pid,signal.SIGTERM);assert p.wait(timeout=5)==7
r=json.loads((B/'lifecycle-signal-receipt02.json').read_text());assert r['returncode']==-signal.SIGKILL and guard.identity(a['native']['pid'])is None;rows.append(dict(case='actual_sigterm_wrapper_native_group_cleanup',receipt=r))
for row in rows:assert row['receipt']['status']in['ALREADY_REAPED_NO_SIGNAL','REFUSED_BIRTH_OR_GROUP_MISMATCH_NO_SIGNAL','EXACT_OWNED_GROUP_KILLED_AND_REAPED']
pin=lambda p:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
q=dict(status='PASS_SIX_ACTUAL_NATIVE_LIFECYCLE_CONTROLS',controls=rows,method=pin(B/'native_lifecycle02.py'),harness=pin(Path(__file__)),scope='No native tools. Real completed/live/signaled children; terminal floor failure, exact birth/group refusal, real wrapperSIGTERM cleanup, reaped group never signaled. Synchronous owned native group contract; no orphan-adoption expansion.')
(B/'lifecycle-controls02.json').write_text(json.dumps(q,indent=2)+'\n');print(q['status'],len(rows))
