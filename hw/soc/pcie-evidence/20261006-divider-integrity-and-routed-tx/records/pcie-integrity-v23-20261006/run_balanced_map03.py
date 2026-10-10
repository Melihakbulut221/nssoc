# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent structural map; preserve the concurrent optimizing ABC run."""
from pathlib import Path
from native_lifecycle02 import OwnedNative,free_floor
import hashlib,json,os,resource,signal,subprocess,time,shutil
R=Path.cwd();B=Path('/dev/shm/nssoc-integrity-v23-balanced-map-01');B.mkdir()
OLD=Path('/dev/shm/nssoc-integrity-v2-balanced-map-01/map.ys');TOOLS=R/'hw/soc/tools/oss-cad-suite/bin'
def pin(p):
 with p.open('rb') as f:return {'bytes':p.stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}
FREEZE=R/'hw/soc/out/pcie-integrity-v23-20261006/source-freeze03.json'
assert pin(FREEZE)['sha256']=='81b39160001de5717fa414371ec18b62772e367e7625e7aaab3af3b0f3af0540'
for name,value in json.loads(FREEZE.read_text())['sources'].items():assert pin(R/name)==value
CORE=FREEZE.parent/'pcie-integrity-v23-composite-controls-validation-20261006.json'
validation=json.loads(CORE.read_text())
assert validation['status']=='PASS_V23_ADJACENT_HEADER_COMPOSITE_CONTROLS'
assert validation['source_freeze']==pin(FREEZE)
assert [(x['passed'],x['failed'],x['skipped'])for x in validation['campaigns']]==[(28,7,0),(6,3,0),(3,0,0)]
assert validation['pytest_executions']==47 and validation['passed_executions']==37 and validation['historical_failed_executions']==10
assert validation['public_positive_composite']==dict(original_unchanged_cases=17,targeted_corrected_case=1,complete_direct_profile_rerun=False,complete_cycle_miter_profile_rerun=False,prior_full_cases=18)
assert validation['cache_fault_write_epochs']==8
obs=validation['adjacent_witness'];assert len(obs['positions'])==16 and min(obs['positions'])>0 and obs['cross_block']>0 and obs['minimum_same_beat']>0 and obs['missing_old_predecessor']>=16
assert len(validation['meaningful_miter_mutants'])==11 and len(validation['promotion_burst'])==2 and len(validation['literal_controls'])==6 and validation['observer_negative']
PEER=FREEZE.parent/'source-only-peer-vco03.json';assert pin(PEER)==validation['source_peer']
assert not json.loads(PEER.read_text())['findings']
SAVED_PEER=FREEZE.parent/'saved-controls-peer-vco03.json';saved_peer=json.loads(SAVED_PEER.read_text())
assert saved_peer['status']=='PASS_INDEPENDENT_SAVED_V23_COMPOSITE_FUNCTIONAL_CONTROLS'and not saved_peer['findings']and saved_peer['validation']==pin(CORE)
CONTROL_ROWS=validation['campaigns']+validation['helper_receipts']
CONTROL_RECEIPTS=[Path(row['path'])for row in CONTROL_ROWS]
for p,row in zip(CONTROL_RECEIPTS,CONTROL_ROWS):assert pin(p)=={k:row[k]for k in ('bytes','sha256')}
assert shutil.disk_usage('/dev/shm').free>=1024**3
def interrupted(signum,frame):raise InterruptedError(f'Signal{signum}')
for sig in (signal.SIGINT,signal.SIGTERM):signal.signal(sig,interrupted)
script='strash; balance -x; &get -n; &nf; &put\n';(B/'abc-structural.script').write_text(script)
s=OLD.read_text().replace(str(OLD.parent),str(B)).replace('integrity_v2','integrity_v23').replace('soc_pcie_gen3_ingress.v','soc_pcie_gen3_ingress_integrity_v11.v')
assert s.count('; abc -script ')==1
assert (OLD.parent/'abc-structural.script').read_text()==script
(B/'map.ys').write_text(s)
files=CONTROL_RECEIPTS+[CORE,PEER,SAVED_PEER,Path(__file__),Path(__file__).with_name('native_lifecycle02.py'),FREEZE,OLD,B/'map.ys',B/'abc-structural.script',R/'hw/soc/out/pcie-loop-wide-delivery-20261004/yosys-abc-help.txt',TOOLS/'yosys',TOOLS/'yosys-abc',Path('/home/hasanmelih/.ciel/ciel/ihp-sg13g2/versions/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib')]+[R/'hw/soc/rtl/pcie'/f'{n}.v' for n in ('soc_pcie_gen3_ingress_integrity_v11','soc_pcie_gen3_data_descrambler','soc_pcie_gen3_framer_rx_integrity_v23','soc_pcie_gen3_continuous_rx_integrity_v23')]
r={'status':'RUNNING','inputs':{str(p):pin(p) for p in files},'command':[str(TOOLS/'yosys'),'-Q','-T','-s',str(B/'map.ys')],'scope':'Separate V23 registered accepted adjacent header relation from frozen V22. Same public latency, strict 18-case public and cycle miter, declared literal557056/XZ1440 and actual predecessor/cache fault witnesses. Exact balancedABC script and150-byte v2 mapping profile. Full native proof/replay and timing acceptance remain separate; frozen v1/v2/v3/v4/v5/v6/v7/v8/v9 unchanged.','elapsed_watchdog_seconds':None,'minimum_shared_free':shutil.disk_usage('/dev/shm').free,'controller_allowed_cpus':sorted(os.sched_getaffinity(0)),'native_cpu_limit':1}
def save():(B/'result.json').write_text(json.dumps(r,indent=2)+'\n')
def limit():
 resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3));resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});signal.pthread_sigmask(signal.SIG_UNBLOCK,{signal.SIGINT,signal.SIGTERM})
assert os.sched_getaffinity(0)=={6},'Launch this independently scheduled one-CPU job with taskset -c 6'
save();t=time.monotonic()
try:
 with (B/'map.log').open('x') as log:
  p=None;native_owner=None
  try:
   previous_mask=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGINT,signal.SIGTERM})
   try:
    p=subprocess.Popen(r['command'],stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'TMPDIR':'/dev/shm','YOSYS_MAX_THREADS':'1','OMP_NUM_THREADS':'1'},preexec_fn=limit,start_new_session=True)
    native_owner=OwnedNative(p);r['native_birth']=native_owner.birth
   finally:signal.pthread_sigmask(signal.SIG_SETMASK,previous_mask)
   r['pid']=p.pid;r['native_allowed_cpus']=sorted(os.sched_getaffinity(p.pid));assert r['native_allowed_cpus']==[6];save()
   while p.poll() is None:
    free=shutil.disk_usage('/dev/shm').free;r['minimum_shared_free']=min(free,r['minimum_shared_free'])
    if free<528*1024**2:raise RuntimeError('Shared scratch floor breached')
    time.sleep(.2)
   r['returncode']=p.wait()
   r['terminal_shared_free']=shutil.disk_usage('/dev/shm').free;free_floor(r['terminal_shared_free'])
  except BaseException:
   if native_owner is not None:
    try:native_owner.kill_and_reap()
    finally:r['cleanup']=native_owner.cleanup
   raise
 assert r['returncode']==0
 assert r['inputs']=={str(p):pin(p) for p in files}
 cells=json.loads((B/'mapped.json').read_text())['modules']['soc_pcie_gen3_continuous_rx_integrity_v23']['cells'];assert cells and all(c['type'].startswith('sg13g2_') for c in cells.values())
 r.update(status='COMPLETE_NATIVE_MAP_FUNCTIONAL_REPLAY_REQUIRED',cells=len(cells))
except BaseException as e:r.update(status='FAILED_RETAINED',error=repr(e));raise
finally:
 r['elapsed_seconds']=time.monotonic()-t;r['outputs']={p.name:pin(p) for p in B.iterdir() if p.is_file() and p.name!='result.json'};save()
