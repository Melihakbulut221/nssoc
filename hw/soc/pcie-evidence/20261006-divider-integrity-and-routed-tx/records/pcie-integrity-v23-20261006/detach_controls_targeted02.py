"""Launch one peer-gated V23 functional campaign detached from tool lifetime."""
from pathlib import Path
import json,hashlib,subprocess,os
R=Path.cwd();B=Path(__file__).resolve().parent
def pin(p):return dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
assert pin(B/'launch_controls_targeted02.py')=={'bytes': 4233, 'sha256': '8e6cc415b1a94368051a20261984cb5006500c26112eebeb894372c92cb977a0'}
freeze=B/'source-freeze02.json';assert pin(freeze)=={'bytes': 4137, 'sha256': 'dd3132d1b9ba5d585bb66fcdabbd07450d86f7e217736cccb88cebc6f6a9c934'}
for n,v in json.loads(freeze.read_text())['sources'].items():assert pin(R/n)==v
peer=B/'source-only-peer-rx02.json';j=json.loads(peer.read_text());assert j['status']=='PASS_SOURCE_ONLY_V23_ADJACENT_HEADER_RELATION' and j['freeze']==pin(freeze) and not j['findings']
assert not Path('/dev/shm/nssoc-integrity-v23-public-controls02').exists()and not(B/'controls-status02.json').exists()
with(B/'controls-detached-once02.json').open('x')as f:json.dump(dict(source_freeze=pin(freeze),peer=pin(peer)),f)
command=['taskset','-c','6',str(R/'.venv/bin/python'),str(B/'launch_controls_targeted02.py')]
with(B/'controls-launch02.log').open('x')as f:c=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,cwd=R,env={**{k:v for k,v in os.environ.items()if k not in ('PYTHONPATH','PYTHONHOME','PYTHONEXECUTABLE')},'PYTHONDONTWRITEBYTECODE':'1'})
a=Path(f'/proc/{c.pid}/stat').read_text().split(') ',1)[1].split()
r=dict(status='DETACHED_CONTROL_LAUNCH_ACTUAL_PROGRESS_REQUIRED',controller=dict(pid=c.pid,start_ticks=a[19],process_group=int(a[2])),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),command=command,launcher=pin(Path(__file__)),source_freeze=pin(freeze),peer=pin(peer))
with(B/'controls-detached-receipt02.json').open('x')as f:json.dump(r,f,indent=2);f.write('\n')
print(json.dumps(r))
