# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Resume only a lost waiting observer, independently of the app tool session."""
import hashlib,json,os,subprocess,time
from pathlib import Path
from datetime import datetime,timezone
B=Path(__file__).resolve().parent
ROOT=B.parents[4]
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return {'bytes':p.stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}
def identity(pid):
 p=Path('/proc')/str(pid)
 if not p.exists():return None
 try:s=(p/'stat').read_text().rsplit(')',1)[1].split();cmd=(p/'cmdline').read_bytes()
 except FileNotFoundError:return None
 return {'pid':pid,'start_ticks':s[19],'state':s[0],'process_group':int(s[2]),'argv':cmd.split(b'\0')[:-1],'affinity':sorted(os.sched_getaffinity(pid))}
def serial(i):return dict(i,argv=[s.decode() for s in i['argv']])
assert ROOT==Path('/home/hasanmelih/Documents/ChatGPT/nnsoc')
assert not (B/'active-controller.json').exists()
f=json.loads((B/'source-freeze.json').read_text());assert f['inputs']=={p:pin(p) for p in f['inputs']}
p=json.loads((B/'source-only-peer.json').read_text());assert p['status']=='PASS_EXACT_TX03_OBSERVER_RESUME_SOURCE' and p['freeze']==pin(B/'source-freeze.json') and not p['findings']
m=json.loads((B/'manifest.json').read_text());assert m['inputs']=={p:pin(p) for p in m['inputs']}
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==m['boot_id']
old=identity(82234);assert old is None or old['start_ticks']!='957118'
observed={}
for name in ('route_owner','route_native'):
 expected=m[name];i=identity(expected['pid']);assert i and i['state']!='Z' and i['start_ticks']==expected['start_ticks'] and i['affinity']==[4]
 assert b' '.join(i['argv']).decode()+' '==expected['command'];observed[name]=serial(i)
assert not Path('/dev/shm/nssoc-tx-path-v4-repair03-detailed-rc-01').exists()
cmd=['/usr/bin/taskset','-c','4',m['python'],'-u',str(B/'run.py')]
env={k:v for k,v in os.environ.items() if k not in ('PYTHONPATH','PYTHONHOME','PYTHONEXECUTABLE')}
with (B/'controller.log').open('xb') as log:
 child=subprocess.Popen(cmd,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True)
 deadline=time.monotonic()+5
 while True:
  current=identity(child.pid)
  if current and current['argv']==[s.encode() for s in cmd[3:]] and current['affinity']==[4]:break
  assert child.poll() is None and time.monotonic()<deadline,'Launch did not reach exact interpreter'
  time.sleep(.02)
 record={'status':'DETACHED_EXACT_WAITING_CONTROLLER_LAUNCHED','utc':datetime.now(timezone.utc).isoformat(),'boot_id':m['boot_id'],'controller':serial(current),'launcher':pin(Path(__file__)),'freeze':pin(B/'source-freeze.json'),'peer':pin(B/'source-only-peer.json'),'manifest':pin(B/'manifest.json'),'observed_existing_route':observed,'tool_session_required':False,'no_native_duplicate':True,'healthy_elapsed_watchdog_seconds':None}
 temp=B/'active-controller.tmp';temp.write_text(json.dumps(record,indent=2)+'\n');temp.replace(B/'active-controller.json')
 print(json.dumps(record))
