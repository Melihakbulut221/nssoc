"""Launch one peer-gated V23 functional campaign detached from tool lifetime."""
from pathlib import Path
import json,hashlib,subprocess,os
R=Path.cwd();B=Path(__file__).resolve().parent
def pin(p):return dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
assert pin(B/'launch_controls01.py')=={'bytes': 3392, 'sha256': '9fc2609ea1bf53b3e3d6cb3e5bb9fee64b29aea8b930c9e19b0717581d0c3cd3'}
freeze=B/'source-freeze01.json';assert pin(freeze)=={'bytes': 3778, 'sha256': '446efb90f07eb3b2fe960498c55079afb385c3a89f8e2dad6dc02f028372b630'}
for n,v in json.loads(freeze.read_text())['sources'].items():assert pin(R/n)==v
peer=B/'source-only-peer-rx01.json';j=json.loads(peer.read_text());assert j['status']=='PASS_SOURCE_ONLY_V23_ADJACENT_HEADER_RELATION' and j['freeze']==pin(freeze) and not j['findings']
assert not Path('/dev/shm/nssoc-integrity-v23-public-controls01').exists()and not(B/'controls-status01.json').exists()
with(B/'controls-detached-once01.json').open('x')as f:json.dump(dict(source_freeze=pin(freeze),peer=pin(peer)),f)
command=['taskset','-c','6',str(R/'.venv/bin/python'),str(B/'launch_controls01.py')]
with(B/'controls-launch01.log').open('x')as f:c=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,cwd=R,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
a=Path(f'/proc/{c.pid}/stat').read_text().split(') ',1)[1].split()
r=dict(status='DETACHED_CONTROL_LAUNCH_ACTUAL_PROGRESS_REQUIRED',controller=dict(pid=c.pid,start_ticks=a[19],process_group=int(a[2])),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),command=command,launcher=pin(Path(__file__)),source_freeze=pin(freeze),peer=pin(peer))
with(B/'controls-detached-receipt01.json').open('x')as f:json.dump(r,f,indent=2);f.write('\n')
print(json.dumps(r))
