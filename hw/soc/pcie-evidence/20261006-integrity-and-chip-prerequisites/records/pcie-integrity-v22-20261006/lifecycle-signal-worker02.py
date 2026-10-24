from pathlib import Path
import json,os,signal,subprocess,sys,time
from native_lifecycle02 import OwnedNative
B=Path(__file__).resolve().parent
def stop(s,f):raise InterruptedError(s)
signal.signal(signal.SIGTERM,stop)
p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(30)"],start_new_session=True)
o=OwnedNative(p)
(B/"lifecycle-signal-birth02.json").write_text(json.dumps(dict(wrapper=os.getpid(),native=o.birth)))
try:
 while p.poll()is None:time.sleep(.01)
except InterruptedError:
 r=o.kill_and_reap();(B/"lifecycle-signal-receipt02.json").write_text(json.dumps(r));raise SystemExit(7)
