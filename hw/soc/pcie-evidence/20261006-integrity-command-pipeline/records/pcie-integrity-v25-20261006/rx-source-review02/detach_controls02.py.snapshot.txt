"""Launch one peer-gated V25 functional campaign detached from tool lifetime."""
from pathlib import Path
import json,hashlib,subprocess,os
R=Path.cwd();B=Path(__file__).resolve().parent
def pin(p):return dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
assert pin(B/'launch_controls02.py')=={'bytes': 4296, 'sha256': '8c7180ce1f25bba3fb22b97e370baa2e8c9d3c1fcdb23ef9fe75fffac2aa538c'}
freeze=B/'source-freeze02.json';assert pin(freeze)=={'bytes': 59234, 'sha256': 'd94d31c2140eed462124ebdf8156a8b3572e7c87f8020b8a5d2361fb6b5fec7b'}
for n,v in json.loads(freeze.read_text())['sources'].items():assert pin(R/n)==v
peer=B/'source-only-peer-rx02.json';j=json.loads(peer.read_text());assert j['status']=='PASS_SOURCE_ONLY_V25_REGISTERED_COMMAND_IMPLEMENTATION' and j['freeze']==pin(freeze) and not j['findings']
assert j['launcher']==pin(B/'launch_controls02.py') and j['detacher']==pin(Path(__file__))
assert not Path('/dev/shm/nssoc-integrity-v25-full-controls01').exists()and not(B/'status01.json').exists()
with(B/'detached-once01.json').open('x')as f:json.dump(dict(source_freeze=pin(freeze),peer=pin(peer)),f)
command=['taskset','-c','6',str(R/'.venv/bin/python'),str(B/'launch_controls02.py')]
with(B/'launch01.log').open('x')as f:c=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,cwd=R,env={**{k:v for k,v in os.environ.items()if k not in ('PYTHONPATH','PYTHONHOME','PYTHONEXECUTABLE')},'PYTHONDONTWRITEBYTECODE':'1'})
a=Path(f'/proc/{c.pid}/stat').read_text().split(') ',1)[1].split()
r=dict(status='DETACHED_CONTROL_LAUNCH_ACTUAL_PROGRESS_REQUIRED',controller=dict(pid=c.pid,start_ticks=a[19],process_group=int(a[2])),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),command=command,launcher=pin(Path(__file__)),source_freeze=pin(freeze),peer=pin(peer))
with(B/'detached-receipt01.json').open('x')as f:json.dump(r,f,indent=2);f.write('\n')
print(json.dumps(r))
