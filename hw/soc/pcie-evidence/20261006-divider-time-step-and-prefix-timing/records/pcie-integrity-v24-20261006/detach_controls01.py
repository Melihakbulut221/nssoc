"""Launch one peer-gated V24 functional campaign detached from tool lifetime."""
from pathlib import Path
import json,hashlib,subprocess,os
R=Path.cwd();B=Path(__file__).resolve().parent
def pin(p):return dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
assert pin(B/'launch_controls01.py')=={'bytes': 4167, 'sha256': '47e3d4c8d3ee9d7471c9828ec04e5952afb2a2ff8a55a2ce08423d4c847bcee5'}
freeze=B/'source-freeze01.json';assert pin(freeze)=={'bytes': 16885, 'sha256': '9e0f9271fdc43e8301293521bee04edfdc75d23fd668f81a437703b16d38ad9d'}
for n,v in json.loads(freeze.read_text())['sources'].items():assert pin(R/n)==v
peer=B/'source-only-peer-vco01.json';j=json.loads(peer.read_text());assert j['status']=='PASS_SOURCE_ONLY_V24_PREFIX_CONTEXT_IMPLEMENTATION' and j['freeze']==pin(freeze) and not j['findings']
assert j['launcher']==pin(B/'launch_controls01.py') and j['detacher']==pin(Path(__file__))
assert not Path('/dev/shm/nssoc-integrity-v24-full-controls01').exists()and not(B/'status01.json').exists()
with(B/'detached-once01.json').open('x')as f:json.dump(dict(source_freeze=pin(freeze),peer=pin(peer)),f)
command=['taskset','-c','6',str(R/'.venv/bin/python'),str(B/'launch_controls01.py')]
with(B/'launch01.log').open('x')as f:c=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,cwd=R,env={**{k:v for k,v in os.environ.items()if k not in ('PYTHONPATH','PYTHONHOME','PYTHONEXECUTABLE')},'PYTHONDONTWRITEBYTECODE':'1'})
a=Path(f'/proc/{c.pid}/stat').read_text().split(') ',1)[1].split()
r=dict(status='DETACHED_CONTROL_LAUNCH_ACTUAL_PROGRESS_REQUIRED',controller=dict(pid=c.pid,start_ticks=a[19],process_group=int(a[2])),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),command=command,launcher=pin(Path(__file__)),source_freeze=pin(freeze),peer=pin(peer))
with(B/'detached-receipt01.json').open('x')as f:json.dump(r,f,indent=2);f.write('\n')
print(json.dumps(r))
