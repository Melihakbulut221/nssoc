"""Fresh exact1us native; local SSD capture only, no network prerequisite."""
from pathlib import Path
import hashlib,json,os,shutil,sys
import numpy as np
import numpy._core._multiarray_umath as compiled
R=Path.cwd();B=Path(__file__).resolve().parent;P=B.parent
sys.path.insert(0,str(R/'scripts'))
import characterize_pcie_pll_acquisition_v5 as m

def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
assert sys.version_info[:3]==(3,12,3)and np.__version__=='2.5.3'and callable(np.trapezoid)
assert os.sched_getaffinity(0)=={12}
policy=json.loads((B/'policy.json').read_text())
for p,v in policy['pins'].items():assert pin(p)==v,p
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==policy['boot_id']
peer=json.loads((B/'source-peer-vco01.json').read_text());assert peer['status']=='PASS_SOURCE_ONLY_DETACHED_LOCAL_PLL_V5_LAUNCH'and not peer['findings']and peer['policy']==pin(B/'policy.json')
method_peer=json.loads((P/'source-saved-peer-root02.json').read_text());assert method_peer['status']=='PASS_SOURCE_AND_SAVED_LOCAL_PLL_CAPTURE_AND_PUBLISHER'and not method_peer['findings']and method_peer['freeze']==pin(P/'source-freeze02.json')
freeze=json.loads((P/'source-freeze02.json').read_text())
for v in freeze['sources']+list(freeze['dependencies'].values()):assert pin(v['path'])=={k:v[k]for k in ['bytes','sha256']},v['path']
old=R/'hw/soc/out/pcie-pll-acquisition-v3-20261005/numerical-convergence-plan01/launch01'
gate=old/'prerequisites.json';validated=m.prerequisites(gate,m.sha(gate),m.TSTEP,m.verify_parent())
offline=json.loads((old/'offline-prerequisites.json').read_text());assert offline['status']=='PASS_OFFLINE_MAXSTEP125_PREREQUISITES'and offline['prerequisites']==pin(gate)and offline['declaration']==pin(old/'declaration.json')and offline['devices']==539
assert set(validated['paths'])==set(offline['inputs'])
for p,v in offline['inputs'].items():assert pin(p)==v,p
original=Path(m.namespace['ORIGINAL'])/'bench.cir';deck=m.stream_deck(original.read_text(),m.TSTEP,m.STOP)
assert hashlib.sha256(deck.encode()).hexdigest()==offline['exact_candidate_deck_sha256']
ref=Path('/dev/shm/nssoc-pll-loop-stream-v1-evidence/original-public-replay-v2.json');assert m.sha(ref)=='27bd5f99f3ee3660ce567e4bcc4af4eaa018cfa44193975713ff8e13854acb35'
for proc in Path('/proc').iterdir():
 if proc.name.isdigit()and int(proc.name)!=os.getpid():
  try:argv=(proc/'cmdline').read_bytes().split(b'\0')
  except(FileNotFoundError,ProcessLookupError):continue
  for version in (1,2,3,4,5):assert os.fsencode(str(R/f'scripts/characterize_pcie_pll_acquisition_v{version}.py'))not in argv,'No duplicate PLL producer'
free=shutil.disk_usage('/dev/shm').free;assert free>=562*1024**2
out=Path(policy['native_out']);spool=Path(policy['spool_out']);assert not out.exists()and not spool.exists()
assert not spool.resolve().is_relative_to('/dev/shm')and spool.parent.stat().st_dev!=Path('/dev/shm').stat().st_dev
limits=m.local.Limits();ssd_free=shutil.disk_usage(spool.parent).free
assert ssd_free>=limits.reserve+limits.payload+limits.floor
command=[sys.executable,str(R/'scripts/characterize_pcie_pll_acquisition_v5.py'),'--out',str(out),'--spool',str(spool),'--prefix',policy['prefix'],'--step-ps','2.5','--reference',str(ref),'--reference-sha',m.sha(ref),'--prerequisites',str(gate),'--prerequisites-sha',m.sha(gate)]
record=dict(command=command,python=sys.executable,python_version=sys.version,numpy_version=np.__version__,numpy_extension=dict(path=compiled.__file__,**pin(compiled.__file__)),launcher=pin(__file__),policy=pin(B/'policy.json'),source_peer=pin(B/'source-peer-vco01.json'),method_peer=pin(P/'source-saved-peer-root02.json'),prerequisites=pin(gate),declaration=pin(old/'declaration.json'),offline=pin(old/'offline-prerequisites.json'),validated_prerequisite_paths=len(validated['paths']),producer=pin(m.__file__),queue=pin(m.local.__file__),network_in_native_capture=False,publication_is_independent=True,spool=str(spool),spool_limits=vars(limits),SSD_free_at_launch=ssd_free,RAM_free_at_launch=free,controller_affinity=[12],boot_id=policy['boot_id'],scope='Fresh time0 unchanged539devices/1us/2.5psTSTEP/1.25psTMAX/100ppm/50ps/windows/nooffsetremoval. Original1GiBnative/50MiBcapture/512MiBfloor/nohealthytimeout. SSD10GiBphysicalreservation separate8GiBpayload,1GiBfloor; bounded local commit only. Original383.288nsERROR retained. Local completion/publication/replay/physical qualification are distinct.')
(B/'command-runtime.json').write_text(json.dumps(record,indent=2)+'\n')
fd=os.open(B/'launch.log',os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.dup2(fd,1);os.dup2(fd,2);os.close(fd);os.execv(command[0],command)
