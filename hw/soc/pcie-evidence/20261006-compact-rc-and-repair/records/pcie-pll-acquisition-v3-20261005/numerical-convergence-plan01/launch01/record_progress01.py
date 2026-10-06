"""Observe existing owned processes after detached launch; never launch native."""
from pathlib import Path
import datetime,hashlib,json,os,re,time
B=Path(__file__).resolve().parent;D=Path('/dev/shm/nssoc-pll-acquisition-v4-max125-01')
def pin(p):
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def read(birth):
 p=Path('/proc')/str(birth['pid']);s=(p/'stat').read_text().rsplit(') ',1)[1].split();assert s[19]==birth['start_ticks']and int(s[2])==birth['process_group'];return dict(**birth,cmdline=(p/'cmdline').read_bytes().decode().split('\0')[:-1],affinity=sorted(os.sched_getaffinity(birth['pid'])))
r=json.loads((B/'detached-launch-receipt.json').read_text());assert r['boot_id']==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
controller=read(r['controller']);owner=json.loads((D/'owned-processes.json').read_text());native=read(next(x['identity']for x in owner['processes']if x['kind']=='native'))
assert controller['affinity']==native['affinity']==[12]
limits=(Path('/proc')/str(native['pid'])/'limits').read_text();assert re.search(r'Max address space\s+1073741824\s+1073741824',limits)
first=float(re.findall(r'Reference value\s*:\s*([\deE+.-]+)',(D/'run.log').read_text())[-1]);time.sleep(1)
second=float(re.findall(r'Reference value\s*:\s*([\deE+.-]+)',(D/'run.log').read_text())[-1]);assert second>first
old=Path('/dev/shm/nssoc-pll-acquisition-v3-step25-detached-02/bench.cir').read_text();new=(D/'bench.cir').read_text();assert old.replace('.tran 2.5e-12 1e-06 0 2.5e-12','.tran 2.5e-12 1e-06 0 1.25e-12')==new
q=dict(status='RUNNING_ACTUAL_NATIVE_POST_TOOL_PROGRESS_VERIFIED',utc=datetime.datetime.now(datetime.UTC).isoformat(),boot_id=r['boot_id'],controller=controller,native=native,simulation_seconds_before=first,simulation_seconds_after=second,native_AS_bytes=1073741824,healthy_timeout=None,deck=pin(D/'bench.cir'),policy=pin(B/'policy.json'),source_peer=pin(B/'source-peer-rx01.json'),declaration=pin(B/'declaration.json'),capture_result=str(D/'result.json'),owned_processes=str(D/'owned-processes.json'),scope='Fresh time0 onlyTMAX refinement now actually progressing; completedold159parts and failedphasepair preserved. Resource/gain/convergence/1us completion not inferred.')
(B/'post-tool-progress01.json').write_text(json.dumps(q,indent=2)+'\n');(B/'active-checkpoint.json').write_text(json.dumps(q,indent=2)+'\n');print(q['status'],first,second,controller['pid'],native['pid'])
