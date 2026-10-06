"""Launch one peer-gated V24 functional campaign detached from tool lifetime."""
from pathlib import Path
import json,hashlib,subprocess,os
R=Path.cwd();B=Path(__file__).resolve().parent
def pin(p):return dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
assert pin(B/'launch_component01.py')=={'bytes': 3367, 'sha256': 'e055b82fb787c87348e918970264d8cd2753a0ccd6807562bea17461a5f9dcd7'}
freeze=B/'component-source-freeze01.json';assert pin(freeze)=={'bytes': 9800, 'sha256': 'df7f2750ada7b0d97011f46316f3d113a1632e67812369a4c4dca51c6b54a43b'}
for n,v in json.loads(freeze.read_text())['sources'].items():assert pin(R/n)==v
peer=B/'component-source-peer-vco01.json';j=json.loads(peer.read_text());assert j['status']=='PASS_SOURCE_ONLY_V24_MATRIX_COMPONENT_CONTROLS' and j['freeze']==pin(freeze) and not j['findings']
assert j['launcher']==pin(B/'launch_component01.py') and j['detacher']==pin(Path(__file__))
assert not Path('/dev/shm/nssoc-integrity-v24-matrix-controls01').exists()and not(B/'component-status01.json').exists()
with(B/'component-detached-once01.json').open('x')as f:json.dump(dict(source_freeze=pin(freeze),peer=pin(peer)),f)
command=['taskset','-c','6',str(R/'.venv/bin/python'),str(B/'launch_component01.py')]
with(B/'component-launch01.log').open('x')as f:c=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,cwd=R,env={**{k:v for k,v in os.environ.items()if k not in ('PYTHONPATH','PYTHONHOME','PYTHONEXECUTABLE')},'PYTHONDONTWRITEBYTECODE':'1'})
a=Path(f'/proc/{c.pid}/stat').read_text().split(') ',1)[1].split()
r=dict(status='DETACHED_CONTROL_LAUNCH_ACTUAL_PROGRESS_REQUIRED',controller=dict(pid=c.pid,start_ticks=a[19],process_group=int(a[2])),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),command=command,launcher=pin(Path(__file__)),source_freeze=pin(freeze),peer=pin(peer))
with(B/'component-detached-receipt01.json').open('x')as f:json.dump(r,f,indent=2);f.write('\n')
print(json.dumps(r))
