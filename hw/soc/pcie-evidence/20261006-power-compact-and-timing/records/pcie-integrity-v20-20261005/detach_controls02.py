"""Launch one peer-gated V20 functional campaign detached from tool lifetime."""
from pathlib import Path
import json,hashlib,subprocess,os
R=Path.cwd();B=Path(__file__).resolve().parent
def pin(p):return dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
assert pin(B/'launch_controls02.py')=={'bytes': 3341, 'sha256': 'de8bb874e27f7b1dbaa0e9095d1e0a2c22b11696e59714d499603a0a2864e942'}
freeze=B/'source-freeze02.json';assert pin(freeze)=={'bytes': 2039, 'sha256': '7fb52e60ab21027b156c3804c8a6de0aef50fb30ef5ed6fe5446b67346e7abc0'}
for n,v in json.loads(freeze.read_text())['files'].items():assert pin(R/n)==v
peer=B/'source-only-peer-rx.json';j=json.loads(peer.read_text());assert j['status']=='PASS_SOURCE_ONLY_V20_ELIGIBLE_RETIRE' and j['freeze']==pin(freeze) and not j['findings']
assert not Path('/dev/shm/nssoc-integrity-v20-public-controls01').exists()and not(B/'controls-status01.json').exists()
with(B/'controls-detached-once01.json').open('x')as f:json.dump(dict(source_freeze=pin(freeze),peer=pin(peer)),f)
command=['taskset','-c','6',str(R/'.venv/bin/python'),str(B/'launch_controls02.py')]
with(B/'controls-launch01.log').open('x')as f:c=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,cwd=R,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
a=Path(f'/proc/{c.pid}/stat').read_text().split(') ',1)[1].split()
r=dict(status='DETACHED_CONTROL_LAUNCH_ACTUAL_PROGRESS_REQUIRED',controller=dict(pid=c.pid,start_ticks=a[19],process_group=int(a[2])),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),command=command,launcher=pin(Path(__file__)),source_freeze=pin(freeze),peer=pin(peer))
with(B/'controls-detached-receipt01.json').open('x')as f:json.dump(r,f,indent=2);f.write('\n')
print(json.dumps(r))
