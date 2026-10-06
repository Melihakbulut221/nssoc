"""Launch one peer-gated V20 functional campaign detached from tool lifetime."""
from pathlib import Path
import json,hashlib,subprocess,os
R=Path.cwd();B=Path(__file__).resolve().parent
def pin(p):return dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
assert pin(B/'launch_controls04.py')=={'bytes': 3421, 'sha256': '1b3cf42108f8c78f7b90931cf4059e617e72d768635d68b5965088dbcb6182e1'}
freeze=B/'source-freeze04.json';assert pin(freeze)=={'bytes': 2024, 'sha256': 'd90ec259ca0a524005dafc838feec3ef93598e056372b88bc9199e1c13e029db'}
for n,v in json.loads(freeze.read_text())['files'].items():assert pin(R/n)==v
peer=B/'source-only-peer-rx04.json';j=json.loads(peer.read_text());assert j['status']=='PASS_SOURCE_ONLY_V20_ELIGIBLE_RETIRE' and j['freeze']==pin(freeze) and not j['findings']
assert not Path('/dev/shm/nssoc-integrity-v20-public-controls04').exists()and not(B/'controls-status04.json').exists()
with(B/'controls-detached-once04.json').open('x')as f:json.dump(dict(source_freeze=pin(freeze),peer=pin(peer)),f)
command=['taskset','-c','6',str(R/'.venv/bin/python'),str(B/'launch_controls04.py')]
with(B/'controls-launch04.log').open('x')as f:c=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,cwd=R,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
a=Path(f'/proc/{c.pid}/stat').read_text().split(') ',1)[1].split()
r=dict(status='DETACHED_CONTROL_LAUNCH_ACTUAL_PROGRESS_REQUIRED',controller=dict(pid=c.pid,start_ticks=a[19],process_group=int(a[2])),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),command=command,launcher=pin(Path(__file__)),source_freeze=pin(freeze),peer=pin(peer))
with(B/'controls-detached-receipt04.json').open('x')as f:json.dump(r,f,indent=2);f.write('\n')
print(json.dumps(r))
