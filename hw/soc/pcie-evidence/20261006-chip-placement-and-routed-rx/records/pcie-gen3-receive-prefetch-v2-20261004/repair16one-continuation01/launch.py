# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Detach the source-reviewed observer once; never relaunch native routing."""
import datetime, hashlib, json, os, shutil, subprocess
from pathlib import Path
R=Path('/home/hasanmelih/Documents/ChatGPT/nnsoc')
C=Path(__file__).resolve().parent
M=C/'manifest.json';P=C/'source-only-peer-pll.json'
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def identity(pid):
 a=(Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()
 return dict(pid=pid,start_ticks=int(a[19]),process_group=int(a[2]),ppid=int(a[1]),state=a[0])
m=json.loads(M.read_text());p=json.loads(P.read_text())
assert p['status']=='PASS_SOURCE_ONLY_RX16ONE_ROUTE_RC_CONTINUATION' and p['findings']==[] and p['manifest']==pin(M)
assert p['launcher']==pin(Path(__file__))
assert m['inputs']=={p:pin(p) for p in m['inputs']}
assert m['route_inputs']=={p:pin(p) for p in m['route_inputs']}
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==m['boot_id']
for key in ['route_owner','route_native']:
 expected=m[key];actual=identity(expected['pid']);assert actual['start_ticks']==int(expected['start_ticks']) and actual['process_group']==expected['process_group'] and actual['state']!='Z'
assert shutil.disk_usage('/dev/shm').free>=1024**3 and 8 in os.sched_getaffinity(0)
assert not (C/'result.json').exists() and not Path('/dev/shm/nssoc-rx-prefetch-v2-repair16one-detailed-rc-01').exists()
env={k:v for k,v in os.environ.items() if k not in ('PYTHONPATH','PYTHONHOME','PYTHONEXECUTABLE')}
with (C/'launch.json').open('x') as f:
 json.dump(dict(status='PREFLIGHT_PASSED_BEFORE_POPEN',manifest=pin(M),peer=pin(P)),f);f.write('\n');f.flush();os.fsync(f.fileno())
with (C/'controller.log').open('x') as log:
 child=subprocess.Popen([m['python'],str(C/'run.py')],cwd=R,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,preexec_fn=lambda:os.sched_setaffinity(0,{8}))
 receipt=dict(status='DETACHED_REVIEWED_CONTINUATION_LAUNCHED',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),boot_id=m['boot_id'],controller=identity(child.pid),manifest=pin(M),peer=pin(P),launcher=pin(Path(__file__)),cpu=8,healthy_elapsed_watchdog=None)
 (C/'launch.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
