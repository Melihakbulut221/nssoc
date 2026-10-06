"""Detach one independent worker after local spool configuration exists."""
from pathlib import Path
import datetime,hashlib,json,os,subprocess
R=Path.cwd();B=Path(__file__).resolve().parent

def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
policy=json.loads((B/'policy.json').read_text())
for p,v in policy['pins'].items():assert pin(p)==v,p
peer=json.loads((B/'source-peer-vco01.json').read_text())
assert peer['status']=='PASS_SOURCE_ONLY_DETACHED_LOCAL_PLL_V5_LAUNCH'and not peer['findings']and peer['policy']==pin(B/'policy.json')
assert (Path(policy['spool_out'])/'configuration.json').is_file()and not Path(policy['publisher_out']).exists()
for proc in Path('/proc').iterdir():
 if proc.name.isdigit()and int(proc.name)!=os.getpid():
  try:argv=(proc/'cmdline').read_bytes().split(b'\0')
  except(FileNotFoundError,ProcessLookupError):continue
  assert not(os.fsencode(str(R/'scripts/publish_pcie_local_spool_v1.py'))in argv and os.fsencode(policy['spool_out'])in argv),'No duplicate spool worker'
with (B/'publication-launch-once.json').open('x')as f:json.dump(dict(utc=datetime.datetime.now(datetime.UTC).isoformat(),policy=pin(B/'policy.json'),peer=pin(B/'source-peer-vco01.json')),f)
command=['taskset','-c','14',str(R/'hw/soc/tools/cocotb-venv/bin/python'),str(B/'launch_publisher.py')]
environment={k:v for k,v in os.environ.items()if k not in ['PYTHONPATH','PYTHONHOME','PYTHONEXECUTABLE']};environment['PYTHONDONTWRITEBYTECODE']='1'
with (B/'publication-supervisor.log').open('x')as log:
 process=subprocess.Popen(command,cwd=R,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,env=environment)
 fields=(Path('/proc')/str(process.pid)/'stat').read_text().rsplit(') ',1)[1].split()
r=dict(status='DETACHED_INDEPENDENT_PUBLISHER_LAUNCHED_ACTUAL_PROGRESS_REQUIRED',controller=dict(pid=process.pid,start_ticks=fields[19],process_group=int(fields[2])),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),command=command,policy=pin(B/'policy.json'),peer=pin(B/'source-peer-vco01.json'),launcher=pin(__file__),native_signals_or_adoption=False)
(B/'publication-detached-receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
