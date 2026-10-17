"""Fresh time-zero1us; retainedTSTEP2.5ps, onlyTMAX1.25ps, unchanged539devices."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,xml.etree.ElementTree as ET
import numpy as np
import numpy._core._multiarray_umath as compiled
R=Path.cwd();B=Path(__file__).resolve().parent;P=B.parent
sys.path.insert(0,str(R/'scripts'))
import characterize_pcie_pll_acquisition_v4 as m

def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
assert sys.version_info[:3]==(3,12,3)and np.__version__=='2.5.3'and callable(np.trapezoid)
assert os.sched_getaffinity(0)=={12}
policy=json.loads((B/'policy.json').read_text())
for p,v in policy['pins'].items():assert pin(p)==v,p
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==policy['boot_id']
peer=json.loads((B/'source-peer-rx01.json').read_text());assert peer['status']=='PASS_SOURCE_ONLY_DETACHED_PLL_MAXSTEP125'and not peer['findings']and peer['policy']==pin(B/'policy.json')
method_peer=json.loads((P/'source-only-peer-rx01.json').read_text());assert method_peer['status']=='PASS_SOURCE_ONLY_PLL_RETAINED_TSTEP_MAXSTEP125'and not method_peer['findings']and method_peer['freeze']==pin(P/'source-freeze01.json')
freeze=json.loads((P/'source-freeze01.json').read_text())
for p,v in(freeze['sources']|freeze['parent_methods']).items():assert pin(R/p)==v,p
assert pin(P/'method-controls03.xml')==freeze['controls']['xml']
cases=ET.parse(P/'method-controls03.xml').findall('.//testcase');assert len(cases)==43 and all(not any(c.find(k)is not None for k in ['failure','error','skipped'])for c in cases)
gate=B/'prerequisites.json';validated=m.prerequisites(gate,m.sha(gate),m.TSTEP,m.verify_parent())
offline=json.loads((B/'offline-prerequisites.json').read_text());assert offline['status']=='PASS_OFFLINE_MAXSTEP125_PREREQUISITES'and offline['prerequisites']==pin(gate)and offline['declaration']==pin(B/'declaration.json')and offline['devices']==539
assert set(validated['paths'])==set(offline['inputs'])
for p,v in offline['inputs'].items():assert pin(p)==v,p
original=Path(m.namespace['ORIGINAL'])/'bench.cir';deck=m.stream_deck(original.read_text(),m.TSTEP,m.STOP)
assert hashlib.sha256(deck.encode()).hexdigest()==offline['exact_candidate_deck_sha256']
ref=Path('/dev/shm/nssoc-pll-loop-stream-v1-evidence/original-public-replay-v2.json');assert m.sha(ref)=='27bd5f99f3ee3660ce567e4bcc4af4eaa018cfa44193975713ff8e13854acb35'
for proc in Path('/proc').iterdir():
 if proc.name.isdigit()and int(proc.name)!=os.getpid():
  try:argv=(proc/'cmdline').read_bytes().split(b'\0')
  except(FileNotFoundError,ProcessLookupError):continue
  for version in (1,2,3,4):assert os.fsencode(str(R/f'scripts/characterize_pcie_pll_acquisition_v{version}.py'))not in argv,'No duplicate PLL producer'
release=json.loads(subprocess.check_output(['gh','api',f'repos/{m.publication.REPO}/releases/tags/{m.RELEASE_TAG}'],timeout=120))
assert release['tag_name']==m.RELEASE_TAG and len(release['assets'])+400<=1000,'400 new immutable asset slots required'
free=shutil.disk_usage('/dev/shm').free;assert free>=562*1024**2
out=Path('/dev/shm/nssoc-pll-acquisition-v4-max125-01');assert not out.exists()
command=[sys.executable,str(R/'scripts/characterize_pcie_pll_acquisition_v4.py'),'--out',str(out),'--prefix','pcie-pll-acquisition-v4-max125-01-20261006','--step-ps','2.5','--reference',str(ref),'--reference-sha',m.sha(ref),'--prerequisites',str(gate),'--prerequisites-sha',m.sha(gate)]
record=dict(command=command,python=sys.executable,python_version=sys.version,numpy_version=np.__version__,numpy_extension=dict(path=compiled.__file__,**pin(compiled.__file__)),launcher=pin(__file__),policy=pin(B/'policy.json'),source_peer=pin(B/'source-peer-rx01.json'),method_peer=pin(P/'source-only-peer-rx01.json'),prerequisites=pin(gate),declaration=pin(B/'declaration.json'),offline=pin(B/'offline-prerequisites.json'),validated_prerequisite_paths=len(validated['paths']),producer=pin(m.__file__),publisher=pin(m.publication.__file__),release_tag=m.RELEASE_TAG,release_asset_count_at_launch=len(release['assets']),reserved_part_count=400,free_at_launch=free,controller_affinity=[12],boot_id=policy['boot_id'],scope='Distinct numerical convergence experiment from time0: retain2.5psTSTEP, reduce onlyTMAXto1.25ps, unchanged539devices/1us/100ppm/50ps/windows/nooffsetremoval. Original1GiBnative/50MiBcapture/backpressure/512MiBfloor/nohealthytimeout. Completed159parts and historical5ps/2.5ps phaseFAIL immutable. This launch does not demonstrate numerical or physical closure.')
(B/'command-runtime.json').write_text(json.dumps(record,indent=2)+'\n')
fd=os.open(B/'launch.log',os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.dup2(fd,1);os.dup2(fd,2);os.close(fd);os.execv(command[0],command)
