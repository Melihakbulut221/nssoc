# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent structural map; preserve the concurrent optimizing ABC run."""
from pathlib import Path
import hashlib,json,os,resource,signal,subprocess,time,shutil
R=Path.cwd();B=Path('/dev/shm/nssoc-integrity-v20-balanced-map-01');B.mkdir()
OLD=Path('/dev/shm/nssoc-integrity-v2-balanced-map-01/map.ys');TOOLS=R/'hw/soc/tools/oss-cad-suite/bin'
def pin(p):
 with p.open('rb') as f:return {'bytes':p.stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}
FREEZE=R/'hw/soc/out/pcie-integrity-v20-20261005/source-freeze04.json'
assert pin(FREEZE)['sha256']=='d90ec259ca0a524005dafc838feec3ef93598e056372b88bc9199e1c13e029db'
for name,value in json.loads(FREEZE.read_text())['files'].items():assert pin(R/name)==value
CORE=FREEZE.parent/'pcie-integrity-v20-core-controls-validation-20261005.json'
assert pin(CORE)==dict(bytes=14549,sha256='648b9b461aa4fce056cd6054dd61fdb48817b31fe0d614a756bc0c720316b916')
validation=json.loads(CORE.read_text());assert validation['status']=='PASS_ELIGIBLE_ROOT_RETIRE_AND_ACTUAL_PUBLIC_FAULT_CONTROLS'and validation['pytest_executions']==43 and validation['pytest_passed_executions']==40 and validation['historical_failed_executions']==3 and validation['source_freeze']==pin(FREEZE)
PEER=FREEZE.parent/'source-only-peer-rx04.json';assert pin(PEER)==validation['source_peer']
assert json.loads(PEER.read_text())['status']=='PASS_SOURCE_ONLY_V20_ELIGIBLE_RETIRE'
CONTROL_RECEIPTS=[Path(row['path']) for row in validation['xml_recount']]
for p,row in zip(CONTROL_RECEIPTS,validation['xml_recount']):assert pin(p)=={k:row[k]for k in ['bytes','sha256']}
assert validation['stalled_zero_keep_witnesses'][1]['actual_reference_retires']==55
assert shutil.disk_usage('/dev/shm').free>=1024**3
def interrupted(signum,frame):raise InterruptedError(f'Signal{signum}')
for sig in (signal.SIGINT,signal.SIGTERM):signal.signal(sig,interrupted)
script='strash; balance -x; &get -n; &nf; &put\n';(B/'abc-structural.script').write_text(script)
s=OLD.read_text().replace(str(OLD.parent),str(B)).replace('integrity_v2','integrity_v20').replace('soc_pcie_gen3_ingress.v','soc_pcie_gen3_ingress_integrity_v11.v')
assert s.count('; abc -script ')==1
assert (OLD.parent/'abc-structural.script').read_text()==script
(B/'map.ys').write_text(s)
files=CONTROL_RECEIPTS+[CORE,PEER,Path(__file__),FREEZE,OLD,B/'map.ys',B/'abc-structural.script',R/'hw/soc/out/pcie-loop-wide-delivery-20261004/yosys-abc-help.txt',TOOLS/'yosys',TOOLS/'yosys-abc',Path('/home/hasanmelih/.ciel/ciel/ihp-sg13g2/versions/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib')]+[R/'hw/soc/rtl/pcie'/f'{n}.v' for n in ('soc_pcie_gen3_ingress_integrity_v11','soc_pcie_gen3_data_descrambler','soc_pcie_gen3_framer_rx_integrity_v20','soc_pcie_gen3_continuous_rx_integrity_v20')]
r={'status':'RUNNING','inputs':{str(p):pin(p) for p in files},'command':[str(TOOLS/'yosys'),'-Q','-T','-s',str(B/'map.ys')],'scope':'Separate V20 knowneligible-rootretirecontrol fromfrozenV19; payload/parser/writers/cyclelatency exact. Actualfourstate/readcontrolfaultandpublicmiter gates required. Exact balancedABC script and150-byte v2 mapping profile. Full native proof/replay and timing acceptance remain separate; frozen v1/v2/v3/v4/v5/v6/v7/v8/v9 unchanged.','elapsed_watchdog_seconds':None,'minimum_shared_free':shutil.disk_usage('/dev/shm').free,'controller_allowed_cpus':sorted(os.sched_getaffinity(0)),'native_cpu_limit':1}
def save():(B/'result.json').write_text(json.dumps(r,indent=2)+'\n')
def limit():
 resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3));resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});signal.pthread_sigmask(signal.SIG_UNBLOCK,{signal.SIGINT,signal.SIGTERM})
assert os.sched_getaffinity(0)=={6},'Launch this independently scheduled one-CPU job with taskset -c 6'
save();t=time.monotonic()
try:
 with (B/'map.log').open('x') as log:
  p=None
  try:
   previous_mask=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGINT,signal.SIGTERM})
   try:p=subprocess.Popen(r['command'],stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'TMPDIR':'/dev/shm','YOSYS_MAX_THREADS':'1','OMP_NUM_THREADS':'1'},preexec_fn=limit,start_new_session=True)
   finally:signal.pthread_sigmask(signal.SIG_SETMASK,previous_mask)
   r['pid']=p.pid;r['native_allowed_cpus']=sorted(os.sched_getaffinity(p.pid));assert r['native_allowed_cpus']==[6];save()
   while p.poll() is None:
    free=shutil.disk_usage('/dev/shm').free;r['minimum_shared_free']=min(free,r['minimum_shared_free'])
    if free<528*1024**2:raise RuntimeError('Shared scratch floor breached')
    time.sleep(.2)
   r['returncode']=p.wait()
  except BaseException:
   if p is not None:
    try:os.killpg(p.pid,signal.SIGKILL)
    except ProcessLookupError:pass
    p.wait()
   raise
 assert r['returncode']==0
 assert r['inputs']=={str(p):pin(p) for p in files}
 cells=json.loads((B/'mapped.json').read_text())['modules']['soc_pcie_gen3_continuous_rx_integrity_v20']['cells'];assert cells and all(c['type'].startswith('sg13g2_') for c in cells.values())
 r.update(status='COMPLETE_NATIVE_MAP_FUNCTIONAL_REPLAY_REQUIRED',cells=len(cells))
except BaseException as e:r.update(status='FAILED_RETAINED',error=repr(e));raise
finally:
 r['elapsed_seconds']=time.monotonic()-t;r['outputs']={p.name:pin(p) for p in B.iterdir() if p.is_file() and p.name!='result.json'};save()
