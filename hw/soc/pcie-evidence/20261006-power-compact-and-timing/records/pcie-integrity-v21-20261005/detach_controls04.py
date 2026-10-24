"""Launch one peer-gated V21 functional campaign detached from tool lifetime."""
from pathlib import Path
import json,hashlib,subprocess,os
R=Path.cwd();B=Path(__file__).resolve().parent
def pin(p):return dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
assert pin(B/'launch_controls04.py')=={'bytes': 3726, 'sha256': 'bdd412d5946641489d615be43f1b3495460c610399cc153516c17f1445041a74'}
freeze=B/'source-freeze04.json';assert pin(freeze)=={'bytes': 3341, 'sha256': '48be11f969876f9738a70f993e31eea6ff63a425a3b26227dfcdc2e55a33d6df'}
for n,v in json.loads(freeze.read_text())['sources'].items():assert pin(R/n)==v
peer=B/'source-only-peer-rx04.json';j=json.loads(peer.read_text());assert j['status']=='PASS_SOURCE_ONLY_V21_REGISTERED_RETIRE' and j['freeze']==pin(freeze) and not j['findings']
assert not Path('/dev/shm/nssoc-integrity-v21-public-controls02').exists()and not(B/'controls-status02.json').exists()
with(B/'controls-detached-once02.json').open('x')as f:json.dump(dict(source_freeze=pin(freeze),peer=pin(peer)),f)
command=['taskset','-c','6',str(R/'.venv/bin/python'),str(B/'launch_controls04.py')]
with(B/'controls-launch02.log').open('x')as f:c=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,cwd=R,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
a=Path(f'/proc/{c.pid}/stat').read_text().split(') ',1)[1].split()
r=dict(status='DETACHED_CONTROL_LAUNCH_ACTUAL_PROGRESS_REQUIRED',controller=dict(pid=c.pid,start_ticks=a[19],process_group=int(a[2])),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),command=command,launcher=pin(Path(__file__)),source_freeze=pin(freeze),peer=pin(peer))
with(B/'controls-detached-receipt02.json').open('x')as f:json.dump(r,f,indent=2);f.write('\n')
print(json.dumps(r))
