"""Launch one peer-gated V25 functional campaign detached from tool lifetime."""
from pathlib import Path
import json,hashlib,subprocess,os
R=Path.cwd();B=Path(__file__).resolve().parent
def pin(p):return dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
assert pin(B/'launch_controls04.py')=={'bytes': 4319, 'sha256': '6462be21f1e80c72e49c754a37575db4f517792f12b6fdd0a3b57f16e3ef978f'}
freeze=B/'source-freeze04.json';assert pin(freeze)=={'bytes': 75168, 'sha256': 'a1c125fdb02559a5c3269351c2a918c731327c538cef8b6a4c70101a453c591f'}
for n,v in json.loads(freeze.read_text())['sources'].items():assert pin(R/n)==v
peer=B/'source-only-peer-rx04.json';j=json.loads(peer.read_text());assert j['status']=='PASS_SOURCE_ONLY_V25_REGISTERED_COMMAND_IMPLEMENTATION' and j['freeze']==pin(freeze) and not j['findings']
assert j['launcher']==pin(B/'launch_controls04.py') and j['detacher']==pin(Path(__file__))
assert not Path('/dev/shm/nssoc-integrity-v25-full-controls02').exists()and not(B/'status02.json').exists()
with(B/'detached-once02.json').open('x')as f:json.dump(dict(source_freeze=pin(freeze),peer=pin(peer)),f)
command=['taskset','-c','6',str(R/'.venv/bin/python'),str(B/'launch_controls04.py')]
with(B/'launch02.log').open('x')as f:c=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,cwd=R,env={**{k:v for k,v in os.environ.items()if k not in ('PYTHONPATH','PYTHONHOME','PYTHONEXECUTABLE')},'PYTHONDONTWRITEBYTECODE':'1'})
a=Path(f'/proc/{c.pid}/stat').read_text().split(') ',1)[1].split()
r=dict(status='DETACHED_CONTROL_LAUNCH_ACTUAL_PROGRESS_REQUIRED',controller=dict(pid=c.pid,start_ticks=a[19],process_group=int(a[2])),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),command=command,launcher=pin(Path(__file__)),source_freeze=pin(freeze),peer=pin(peer))
with(B/'detached-receipt02.json').open('x')as f:json.dump(r,f,indent=2);f.write('\n')
print(json.dumps(r))
