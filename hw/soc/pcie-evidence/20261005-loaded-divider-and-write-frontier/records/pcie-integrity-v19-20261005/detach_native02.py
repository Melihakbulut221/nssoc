"""Start exactly one reviewed V19 native chain outside the tool-session tree."""
from pathlib import Path
import hashlib,json,os,subprocess
R=Path.cwd();B=Path(__file__).resolve().parent

def pin(p):
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
p=B/'continuation-policy02.json';assert pin(p)==dict(bytes=7292,sha256='c9ff48ba6b9a874c5a88299963e42806b992540eb5a3f2f2cef1a2f2cc26d4c8')
policy=json.loads(p.read_text())
for name,value in policy['method_pins'].items():assert pin(Path(name))==value
for name,value in policy['source_pins'].items():assert pin(R/name)==value
peer=B/'native-source-only-peer02.json';pr=json.loads(peer.read_text());assert pr['status']=='PASS_SOURCE_ONLY_V19_MERGED_NATIVE_CONTINUATION' and pr['policy']==pin(p) and not pr['findings']
assert not (B/'continuation-status02.json').exists()
assert not Path('/dev/shm/nssoc-integrity-v19-balanced-map-01').exists()
with (B/'detached-native02-once.json').open('x')as f:json.dump(dict(policy=pin(p),peer=pin(peer),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip()),f)
command=['taskset','-c','6',str(R/'.venv/bin/python'),str(B/'continue_native02.py')]
with (B/'detached-native02-supervisor.log').open('x')as f:
 child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,cwd=R,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
s=Path(f'/proc/{child.pid}/stat').read_text().split(') ',1)[1].split()
r=dict(status='DETACHED_LAUNCHED_POST_TOOL_NATIVE_PROGRESS_REQUIRED',controller=dict(pid=child.pid,start_ticks=s[19],process_group=int(s[2])),command=command,boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),policy=pin(p),peer=pin(peer),launcher=pin(Path(__file__)),elapsed_watchdog_seconds=None)
with (B/'detached-native02-receipt.json').open('x')as f:json.dump(r,f,indent=2);f.write('\n')
print(json.dumps(r))
