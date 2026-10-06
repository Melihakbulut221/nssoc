"""Launch once; Python process returns while a separate owned replay continues."""
from pathlib import Path
import datetime,hashlib,json,os,subprocess
R=Path.cwd();B=Path(__file__).resolve().parent

def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
policy=json.loads((B/'policy.json').read_text())
for p,v in policy['pins'].items():assert pin(p)==v,p
peer=json.loads((B/'source-peer-vco.json').read_text())
assert peer['status']=='PASS_SOURCE_ONLY_DETACHED_PLL_REPLAY' and not peer['findings']
assert peer['policy']==pin(B/'policy.json')
assert not (B/'result.json').exists() and not (B/'execution.json').exists()
with (B/'launch-once.json').open('x') as f:json.dump(dict(utc=datetime.datetime.now(datetime.UTC).isoformat(),policy=pin(B/'policy.json'),peer=pin(B/'source-peer-vco.json')),f)
command=['taskset','-c','12',str(R/'hw/soc/tools/cocotb-venv/bin/python'),str(B/'run.py')]
environment={k:v for k,v in os.environ.items() if k not in ['PYTHONPATH','PYTHONHOME','PYTHONEXECUTABLE']}
environment['PYTHONDONTWRITEBYTECODE']='1'
with (B/'supervisor.log').open('x') as log:
 process=subprocess.Popen(command,cwd=R,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,env=environment)
 fields=(Path('/proc')/str(process.pid)/'stat').read_text().rsplit(') ',1)[1].split()
r=dict(status='DETACHED_REPLAY_LAUNCHED_PROGRESS_REQUIRED',controller=dict(pid=process.pid,start_ticks=fields[19],process_group=int(fields[2])),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),command=command,policy=pin(B/'policy.json'),peer=pin(B/'source-peer-vco.json'),launcher=pin(Path(__file__)))
(B/'detached-launch-receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
