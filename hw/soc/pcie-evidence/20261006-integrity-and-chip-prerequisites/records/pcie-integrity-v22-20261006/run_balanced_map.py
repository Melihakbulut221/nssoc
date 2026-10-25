# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent structural map; preserve the concurrent optimizing ABC run."""
from pathlib import Path
import hashlib,json,os,resource,signal,subprocess,time,shutil
R=Path.cwd();B=Path('/dev/shm/nssoc-integrity-v22-balanced-map-01');B.mkdir()
OLD=Path('/dev/shm/nssoc-integrity-v2-balanced-map-01/map.ys');TOOLS=R/'hw/soc/tools/oss-cad-suite/bin'
def pin(p):
 with p.open('rb') as f:return {'bytes':p.stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}
FREEZE=R/'hw/soc/out/pcie-integrity-v22-20261006/source-freeze03.json'
assert pin(FREEZE)['sha256']=='46d599c89a5a19fee6e87dd9fbfa006a7d29f81922530256ab348685ea50e21c'
for name,value in json.loads(FREEZE.read_text())['sources'].items():assert pin(R/name)==value
CORE=FREEZE.parent/'pcie-integrity-v22-controls-validation-20261006.json'
validation=json.loads(CORE.read_text())
assert validation['status']=='PASS_V22_CACHE_QUARANTINE_COMPOSITE_CONTROLS'
assert validation['pytest_executions']==38 and validation['pytest_passed_executions']==35 and validation['historical_failed_executions']==3
assert validation['source_freeze']==pin(FREEZE) and validation['public_positive_composite']==dict(original_unchanged_cases=16,targeted_corrected_case=1,complete_direct_profile_rerun=False,complete_cycle_miter_cases=17)
assert validation['actual_cache_witness']==dict(epochs=8,fault_steps=8,invalid_cache_changes=8)and len(validation['meaningful_miter_mutants'])==6
PEER=FREEZE.parent/'source-only-peer-vco03.json';assert pin(PEER)==validation['source_peer']
assert not json.loads(PEER.read_text())['findings']
CONTROL_RECEIPTS=[Path(row['path'])for row in validation['xml_recount']]
for p,row in zip(CONTROL_RECEIPTS,validation['xml_recount']):assert pin(p)=={k:row[k]for k in ['bytes','sha256']}
assert shutil.disk_usage('/dev/shm').free>=1024**3
def interrupted(signum,frame):raise InterruptedError(f'Signal{signum}')
for sig in (signal.SIGINT,signal.SIGTERM):signal.signal(sig,interrupted)
script='strash; balance -x; &get -n; &nf; &put\n';(B/'abc-structural.script').write_text(script)
s=OLD.read_text().replace(str(OLD.parent),str(B)).replace('integrity_v2','integrity_v22').replace('soc_pcie_gen3_ingress.v','soc_pcie_gen3_ingress_integrity_v11.v')
assert s.count('; abc -script ')==1
assert (OLD.parent/'abc-structural.script').read_text()==script
(B/'map.ys').write_text(s)
files=CONTROL_RECEIPTS+[CORE,PEER,Path(__file__),FREEZE,OLD,B/'map.ys',B/'abc-structural.script',R/'hw/soc/out/pcie-loop-wide-delivery-20261004/yosys-abc-help.txt',TOOLS/'yosys',TOOLS/'yosys-abc',Path('/home/hasanmelih/.ciel/ciel/ihp-sg13g2/versions/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib')]+[R/'hw/soc/rtl/pcie'/f'{n}.v' for n in ('soc_pcie_gen3_ingress_integrity_v11','soc_pcie_gen3_data_descrambler','soc_pcie_gen3_framer_rx_integrity_v22','soc_pcie_gen3_continuous_rx_integrity_v22')]
r={'status':'RUNNING','inputs':{str(p):pin(p) for p in files},'command':[str(TOOLS/'yosys'),'-Q','-T','-s',str(B/'map.ys')],'scope':'Separate V22 cache fault-write qualification from frozen V21; same registered retirement and public latency. Exact inverse, literal4096, cycle-exact17case miter and eight actual cache fault/reuse epochs required. Exact balancedABC script and150-byte v2 mapping profile. Full native proof/replay and timing acceptance remain separate; frozen v1/v2/v3/v4/v5/v6/v7/v8/v9 unchanged.','elapsed_watchdog_seconds':None,'minimum_shared_free':shutil.disk_usage('/dev/shm').free,'controller_allowed_cpus':sorted(os.sched_getaffinity(0)),'native_cpu_limit':1}
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
 cells=json.loads((B/'mapped.json').read_text())['modules']['soc_pcie_gen3_continuous_rx_integrity_v22']['cells'];assert cells and all(c['type'].startswith('sg13g2_') for c in cells.values())
 r.update(status='COMPLETE_NATIVE_MAP_FUNCTIONAL_REPLAY_REQUIRED',cells=len(cells))
except BaseException as e:r.update(status='FAILED_RETAINED',error=repr(e));raise
finally:
 r['elapsed_seconds']=time.monotonic()-t;r['outputs']={p.name:pin(p) for p in B.iterdir() if p.is_file() and p.name!='result.json'};save()
