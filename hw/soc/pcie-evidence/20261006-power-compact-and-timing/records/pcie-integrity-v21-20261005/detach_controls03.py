"""Launch one peer-gated V21 functional campaign detached from tool lifetime."""
from pathlib import Path
import json,hashlib,subprocess,os
R=Path.cwd();B=Path(__file__).resolve().parent
def pin(p):return dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
assert pin(B/'launch_controls03.py')=={'bytes': 3426, 'sha256': '4580c8c5e8a794c6092a1b3548134481743613bdd58750b2253fb6beec8a3115'}
freeze=B/'source-freeze03.json';assert pin(freeze)=={'bytes': 2837, 'sha256': 'c7ff40ed5045e9265a40fe8aa27fc073b335649f9fd65579372f22b3eaaa4e97'}
for n,v in json.loads(freeze.read_text())['sources'].items():assert pin(R/n)==v
peer=B/'source-only-peer-rx03.json';j=json.loads(peer.read_text());assert j['status']=='PASS_SOURCE_ONLY_V21_REGISTERED_RETIRE' and j['freeze']==pin(freeze) and not j['findings']
assert not Path('/dev/shm/nssoc-integrity-v21-public-controls01').exists()and not(B/'controls-status01.json').exists()
with(B/'controls-detached-once01.json').open('x')as f:json.dump(dict(source_freeze=pin(freeze),peer=pin(peer)),f)
command=['taskset','-c','6',str(R/'.venv/bin/python'),str(B/'launch_controls03.py')]
with(B/'controls-launch01.log').open('x')as f:c=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,cwd=R,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
a=Path(f'/proc/{c.pid}/stat').read_text().split(') ',1)[1].split()
r=dict(status='DETACHED_CONTROL_LAUNCH_ACTUAL_PROGRESS_REQUIRED',controller=dict(pid=c.pid,start_ticks=a[19],process_group=int(a[2])),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),command=command,launcher=pin(Path(__file__)),source_freeze=pin(freeze),peer=pin(peer))
with(B/'controls-detached-receipt01.json').open('x')as f:json.dump(r,f,indent=2);f.write('\n')
print(json.dumps(r))
