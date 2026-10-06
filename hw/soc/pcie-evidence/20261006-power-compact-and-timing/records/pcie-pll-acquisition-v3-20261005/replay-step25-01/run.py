"""One detached, owned replay of already completed native data; never starts SPICE."""
from pathlib import Path
import datetime, hashlib, json, os, resource, sys, time
R=Path.cwd(); B=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'scripts'))
import characterize_pcie_clock_trim_stream_v2 as life

def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def atomic(p,v):life.atomic(p,v)
def main():
 policy=json.loads((B/'policy.json').read_text())
 for p,v in policy['pins'].items():assert pin(p)==v,p
 peer=json.loads((B/'source-peer-vco.json').read_text())
 assert peer['status']=='PASS_SOURCE_ONLY_DETACHED_PLL_REPLAY' and not peer['findings']
 assert peer['policy']==pin(B/'policy.json')
 assert os.sched_getaffinity(0)=={12}
 assert not (B/'result.json').exists() and not (B/'execution.json').exists()
 assert json.loads(Path(policy['capture'],'result.json').read_text())['status']=='PASS_NATIVE_STREAM_FINITE_SCREEN'
 resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
 command=[str(R/'hw/soc/tools/cocotb-venv/bin/python'),str(R/'scripts/review_pcie_pll_acquisition_v1.py'),'--capture',policy['capture'],'--result-sha',policy['native_result_sha256'],'--out',str(B/'result.json')]
 begin=time.monotonic(); outcome=dict(status='RUNNING',utc=datetime.datetime.now(datetime.UTC).isoformat(),command=command,policy=pin(B/'policy.json'),peer=pin(B/'source-peer-vco.json'),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),parent=life.process_identity(os.getpid()),native_restarted=False,healthy_timeout_seconds=None,rlimit_as_bytes=2*1024**3)
 atomic(B/'active-status.json',outcome)
 owner=life.ProcessOwner(B/'owned-processes.json')
 try:
  with owner:
   with (B/'review.log').open('x') as log:
    process=owner.launch('native',command,cwd=R,stdin=-3,stdout=log,stderr=-2,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    outcome['child']=life.process_identity(process.pid);atomic(B/'active-status.json',outcome)
    code=owner.wait(process);owner.check()
    assert code==0,f'Replay exited {code}; preserve log and do not promote native result'
  owner.check()
  record=json.loads((B/'result.json').read_text())
  assert record['status']=='PASS_LOSSLESS_AUTHOR_REPLAY_AND_INDEPENDENT_ACQUISITION_ARITHMETIC'
  assert record['parts']==159 and record['rows']==401607 and record['values']==331727382
  assert record['native_result']==policy['pins'][str(Path(policy['capture'],'result.json'))]
  assert record['native_authoritative_status']=='PASS_NATIVE_STREAM_FINITE_SCREEN'
  assert record['independent']['passed'] and record['all539_author_safety_records_exact'] and record['no_new_native']
  for p,v in policy['pins'].items():assert pin(p)==v,p
  outcome.update(status='PASS_COMPLETED_PUBLIC_REPLAY',result=pin(B/'result.json'),returncode=code)
 except BaseException as e:
  outcome.update(status='INTERRUPTED' if owner.reason and owner.reason.startswith('Parent received SIG') else 'FAILED_REPLAY_RETAINED',error=repr(e),returncode=process.poll() if 'process' in locals() else None)
  raise
 finally:
  outcome.update(elapsed_seconds=time.monotonic()-begin,owner=pin(B/'owned-processes.json') if (B/'owned-processes.json').exists() else None,log=pin(B/'review.log') if (B/'review.log').exists() else None)
  atomic(B/'execution.json',outcome);atomic(B/'active-status.json',outcome)
if __name__=='__main__':main()
